"""DayZ-Discord-Bot mit Shopsystem und Lieferung an Orte (Nitrado / PlayStation).

Ablauf einer Lieferung:
  1. Spieler kauft per /kaufen ein Item an einem Ort (fester Ort oder eigener Standort).
  2. Der Bot schreibt alle wartenden Bestellungen in eine Object-Spawner-Datei
     (custom/shop_lieferungen.json im Missionsordner).
  3. Beim nächsten Server-Neustart spawnt DayZ die Items an den Koordinaten.
  4. Der Bot erkennt den Neustart, markiert die Bestellungen als geliefert
     und leert die Datei wieder (sonst würden sie bei jedem Neustart erneut spawnen).
"""

import asyncio
import json
import logging
import math
import os
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from adm import parse_zeile
from db import DB
from nitrado import Nitrado, NitradoError

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dayzbot")

BASIS = Path(__file__).parent
GUILD = discord.Object(id=int(os.environ["GUILD_ID"]))
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "DayZ Admin")
MISSION = os.getenv("MISSION", "dayzOffline.chernarusplus")
START_GELD = int(os.getenv("START_GELD", "500"))
TAEGLICH_BONUS = int(os.getenv("TAEGLICH_BONUS", "250"))
KILL_BELOHNUNG = int(os.getenv("KILL_BELOHNUNG", "100"))
WAEHRUNG = os.getenv("WAEHRUNG", "Rubel")
NEUSTART_NACH_KAUF = os.getenv("NEUSTART_NACH_KAUF", "false").lower() == "true"

SPAWN_DATEI = "custom/shop_lieferungen.json"   # relativ zum Missionsordner
STANDORT = "Mein Standort"
STANDORT_MAX_ALTER = 15 * 60                    # Sekunden

SHOP: dict[str, list[dict]] = json.loads((BASIS / "shop.json").read_text("utf-8"))
ARTIKEL = {a["name"]: a for kat in SHOP.values() for a in kat}
ORTE: dict[str, list[float]] = {
    k: v for k, v in json.loads((BASIS / "orte.json").read_text("utf-8")).items()
    if not k.startswith("_")
}

db = DB(str(BASIS / "data" / "bot.db"))
nitrado = Nitrado(os.environ["NITRADO_TOKEN"], os.environ["NITRADO_SERVICE_ID"])
pfade: dict[str, str] = {}
datei_lock = asyncio.Lock()


def geld(betrag: int) -> str:
    return f"{betrag:,} {WAEHRUNG}".replace(",", ".")


async def pfade_ermitteln():
    gs = await nitrado.gameserver()
    basis = gs.get("game_specific", {}).get("path", "")
    pfade["mission"] = os.getenv("MISSION_DIR") or f"{basis}mpmissions/{MISSION}/"
    pfade["adm"] = os.getenv("ADM_LOG_DIR") or f"{basis}config/"
    log.info("Missionsordner: %s | ADM-Logs: %s", pfade["mission"], pfade["adm"])


# --- Lieferungen ----------------------------------------------------------

def spawn_objekte(bestellungen) -> dict:
    """Baut den Inhalt der Object-Spawner-Datei. Mehrere Items werden im Kreis verteilt."""
    objekte = []
    for b in bestellungen:
        for i in range(b["menge"]):
            winkel = 2 * math.pi * i / max(b["menge"], 1)
            radius = 0.6 if b["menge"] > 1 else 0.0
            objekte.append({
                "name": b["klasse"],
                "pos": [round(b["x"] + radius * math.cos(winkel), 2),
                        round(b["y"], 2),
                        round(b["z"] + radius * math.sin(winkel), 2)],
                "ypr": [0.0, 0.0, 0.0],
                "scale": 1.0,
                "enableCEPersistency": 0,
            })
    return {"Objects": objekte}


async def spawn_datei_schreiben():
    async with datei_lock:
        inhalt = json.dumps(spawn_objekte(db.wartende()), indent=2)
        await nitrado.upload(pfade["mission"] + SPAWN_DATEI, inhalt)


# --- Bot ------------------------------------------------------------------

class DayZBot(commands.Bot):
    async def setup_hook(self):
        await pfade_ermitteln()
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)
        status_schleife.start()
        log_schleife.start()

    async def close(self):
        await nitrado.close()
        await super().close()


intents = discord.Intents.default()
bot = DayZBot(command_prefix="!", intents=intents)


def ist_admin(interaction: discord.Interaction) -> bool:
    m = interaction.user
    return isinstance(m, discord.Member) and (
        m.guild_permissions.administrator or any(r.name == ADMIN_ROLE for r in m.roles)
    )


async def benachrichtigen(discord_id: int, text: str):
    try:
        user = bot.get_user(discord_id) or await bot.fetch_user(discord_id)
        await user.send(text)
    except discord.HTTPException:
        pass  # DMs deaktiviert


@tasks.loop(seconds=30)
async def status_schleife():
    """Erkennt Server-Neustarts und schließt Lieferungen ab."""
    try:
        jetzt = await nitrado.status()
    except NitradoError as e:
        log.warning("Status nicht abrufbar: %s", e)
        return
    vorher = db.get("server_status")
    db.set("server_status", jetzt)

    if vorher == "started" and jetzt != "started":
        # Neustart beginnt: alles bis hierhin ist in der Datei und wird gespawnt.
        db.set("liefer_snapshot", str(db.letzte_bestell_id()))
        log.info("Neustart erkannt (%s)", jetzt)

    elif vorher not in (None, "started") and jetzt == "started":
        snapshot = int(db.get("liefer_snapshot", "0") or 0)
        db.set("liefer_snapshot", "0")
        geliefert = db.als_geliefert(snapshot) if snapshot else []
        await spawn_datei_schreiben()   # Datei leeren bzw. nur Neues behalten
        log.info("Server läuft wieder, %d Bestellungen geliefert", len(geliefert))
        for b in geliefert:
            await benachrichtigen(
                b["discord_id"],
                f"📦 Deine Lieferung **{b['artikel']}** liegt jetzt bei **{b['ort']}** bereit!",
            )


@tasks.loop(seconds=60)
async def log_schleife():
    """Liest neue Zeilen aus dem ADM-Log: Positionen merken, Kills belohnen."""
    try:
        eintraege = [e for e in await nitrado.list_dir(pfade["adm"])
                     if e.get("name", "").upper().endswith(".ADM")]
        if not eintraege:
            return
        neueste = max(eintraege, key=lambda e: (e.get("modified_at", 0), e["name"]))
        pfad = neueste["path"]
        zeilen = (await nitrado.download(pfad)).splitlines()
    except NitradoError as e:
        log.warning("ADM-Log nicht lesbar: %s", e)
        return

    if db.get("adm_datei") is None:
        # Erster Start: alte Einträge überspringen, damit keine alten Kills belohnt werden.
        db.set("adm_datei", pfad)
        db.set("adm_zeilen", str(len(zeilen)))
        return
    start = int(db.get("adm_zeilen", "0")) if db.get("adm_datei") == pfad else 0
    if start > len(zeilen):
        start = 0

    for zeile in zeilen[start:]:
        positionen, kill = parse_zeile(zeile)
        for p in positionen:
            db.position_setzen(p.gamertag, p.x, p.hoehe, p.z)
        if kill and KILL_BELOHNUNG:
            konto = db.konto_per_gamertag(kill.taeter)
            if konto:
                db.geld_aendern(konto["discord_id"], KILL_BELOHNUNG)
                await benachrichtigen(
                    konto["discord_id"],
                    f"💀 Kill an **{kill.opfer}**: +{geld(KILL_BELOHNUNG)}",
                )

    db.set("adm_datei", pfad)
    db.set("adm_zeilen", str(len(zeilen)))


@status_schleife.before_loop
@log_schleife.before_loop
async def warten():
    await bot.wait_until_ready()


# --- Spieler-Befehle -----------------------------------------------------

@bot.tree.command(name="verknuepfen", description="Verknüpfe deinen Discord mit deinem PSN-Gamertag")
@app_commands.describe(gamertag="Dein PSN-Name, genau wie im Spiel")
async def verknuepfen(interaction: discord.Interaction, gamertag: str):
    vorhanden = db.konto_per_gamertag(gamertag)
    if vorhanden and vorhanden["discord_id"] != interaction.user.id:
        await interaction.response.send_message(
            "❌ Dieser Gamertag ist schon mit einem anderen Discord verknüpft.", ephemeral=True)
        return
    neu = db.konto(interaction.user.id) is None
    db.verknuepfen(interaction.user.id, gamertag, START_GELD)
    text = f"✅ Verknüpft mit **{gamertag}**."
    if neu:
        text += f" Startguthaben: {geld(START_GELD)}"
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="konto", description="Zeigt dein Guthaben")
async def konto(interaction: discord.Interaction):
    k = db.konto(interaction.user.id)
    if not k:
        await interaction.response.send_message(
            "Du bist noch nicht verknüpft. Nutze `/verknuepfen`.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"💰 **{k['gamertag']}**: {geld(k['geld'])}", ephemeral=True)


@bot.tree.command(name="taeglich", description="Hole dir deinen täglichen Bonus")
async def taeglich(interaction: discord.Interaction):
    k = db.konto(interaction.user.id)
    if not k:
        await interaction.response.send_message("Nutze zuerst `/verknuepfen`.", ephemeral=True)
        return
    rest = k["letzter_bonus"] + 20 * 3600 - int(time.time())
    if rest > 0:
        await interaction.response.send_message(
            f"⏳ Nächster Bonus in {rest // 3600} h {rest % 3600 // 60} min.", ephemeral=True)
        return
    db.geld_aendern(interaction.user.id, TAEGLICH_BONUS)
    db.bonus_setzen(interaction.user.id)
    await interaction.response.send_message(f"🎁 +{geld(TAEGLICH_BONUS)}", ephemeral=True)


async def kategorie_auswahl(interaction: discord.Interaction, aktuell: str):
    return [app_commands.Choice(name=k, value=k) for k in SHOP
            if aktuell.lower() in k.lower()][:25]


@bot.tree.command(name="shop", description="Zeigt den Shop")
@app_commands.autocomplete(kategorie=kategorie_auswahl)
async def shop(interaction: discord.Interaction, kategorie: str | None = None):
    embed = discord.Embed(title="🛒 DayZ Shop", color=0x2F7D32)
    for kat, artikel in SHOP.items():
        if kategorie and kat != kategorie:
            continue
        embed.add_field(
            name=kat,
            value="\n".join(f"**{a['name']}** – {geld(a['preis'])}" for a in artikel),
            inline=False,
        )
    embed.set_footer(text="Kaufen mit /kaufen • Lieferung beim nächsten Server-Neustart")
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def artikel_auswahl(interaction: discord.Interaction, aktuell: str):
    return [app_commands.Choice(name=f"{n} ({geld(a['preis'])})", value=n)
            for n, a in ARTIKEL.items() if aktuell.lower() in n.lower()][:25]


async def ort_auswahl(interaction: discord.Interaction, aktuell: str):
    namen = [STANDORT, *ORTE]
    return [app_commands.Choice(name=n, value=n) for n in namen
            if aktuell.lower() in n.lower()][:25]


@bot.tree.command(name="kaufen", description="Kaufe ein Item und lass es an einen Ort liefern")
@app_commands.describe(artikel="Was du kaufen willst", ort="Wohin geliefert wird")
@app_commands.autocomplete(artikel=artikel_auswahl, ort=ort_auswahl)
async def kaufen(interaction: discord.Interaction, artikel: str, ort: str):
    k = db.konto(interaction.user.id)
    if not k:
        await interaction.response.send_message("Nutze zuerst `/verknuepfen`.", ephemeral=True)
        return
    a = ARTIKEL.get(artikel)
    if not a:
        await interaction.response.send_message("❌ Diesen Artikel gibt es nicht.", ephemeral=True)
        return

    if ort == STANDORT:
        p = db.position(k["gamertag"])
        if not p or time.time() - p["zeit"] > STANDORT_MAX_ALTER:
            await interaction.response.send_message(
                "❌ Kein aktueller Standort von dir bekannt. Du musst auf dem Server online sein "
                "(Position wird ca. alle 5 Minuten aus dem Admin-Log gelesen).", ephemeral=True)
            return
        x, y, z = p["x"] + 1.5, p["y"], p["z"] + 1.5   # etwas neben den Spieler
        ort_name = f"deinem Standort ({p['x']:.0f} / {p['z']:.0f})"
    elif ort in ORTE:
        x, y, z = ORTE[ort]
        ort_name = ort
    else:
        await interaction.response.send_message("❌ Unbekannter Ort.", ephemeral=True)
        return

    try:
        nr = db.kaufen(interaction.user.id, a["name"], a["klasse"], a["menge"],
                       a["preis"], ort_name, x, y, z)
    except ValueError:
        await interaction.response.send_message(
            f"❌ Nicht genug Geld. Preis: {geld(a['preis'])}, du hast {geld(k['geld'])}.",
            ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    # Während eines Neustarts nicht hochladen, sonst würde die Bestellung doppelt spawnen.
    # Die Datei wird nach dem Neustart ohnehin neu geschrieben.
    if db.get("server_status") == "started":
        try:
            await spawn_datei_schreiben()
            if NEUSTART_NACH_KAUF:
                await nitrado.restart("Shop-Lieferung")
        except NitradoError as e:
            log.error("Upload fehlgeschlagen: %s", e)

    wann = "nach dem Neustart in wenigen Minuten" if NEUSTART_NACH_KAUF else "beim nächsten Server-Neustart"
    await interaction.followup.send(
        f"✅ Bestellung #{nr}: **{a['name']}** für {geld(a['preis'])}.\n"
        f"📍 Lieferung an **{ort_name}** {wann}.", ephemeral=True)


@bot.tree.command(name="bestellungen", description="Deine letzten Bestellungen")
async def bestellungen(interaction: discord.Interaction):
    rows = db.bestellungen_von(interaction.user.id)
    if not rows:
        await interaction.response.send_message("Noch keine Bestellungen.", ephemeral=True)
        return
    symbol = {"wartend": "⏳", "geliefert": "✅", "erstattet": "↩️"}
    text = "\n".join(f"{symbol.get(r['status'], '?')} #{r['id']} {r['artikel']} → {r['ort']}"
                     for r in rows)
    await interaction.response.send_message(text, ephemeral=True)


# --- Admin-Befehle -------------------------------------------------------

@bot.tree.command(name="admin-geld", description="[Admin] Geld geben oder abziehen")
@app_commands.check(ist_admin)
async def admin_geld(interaction: discord.Interaction, spieler: discord.Member, betrag: int):
    if not db.konto(spieler.id):
        await interaction.response.send_message("Spieler ist nicht verknüpft.", ephemeral=True)
        return
    db.geld_aendern(spieler.id, betrag)
    await interaction.response.send_message(
        f"✅ {spieler.mention}: {'+' if betrag >= 0 else ''}{geld(betrag)}", ephemeral=True)


@bot.tree.command(name="admin-neustart", description="[Admin] Server neu starten (liefert alle Bestellungen)")
@app_commands.check(ist_admin)
async def admin_neustart(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await spawn_datei_schreiben()
    await nitrado.restart("Shop-Lieferung")
    await interaction.followup.send(
        f"🔄 Neustart ausgelöst, {len(db.wartende())} Bestellung(en) werden geliefert.",
        ephemeral=True)


@bot.tree.command(name="admin-einrichten", description="[Admin] Trägt die Shop-Datei in cfggameplay.json ein")
@app_commands.check(ist_admin)
async def admin_einrichten(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    pfad = pfade["mission"] + "cfggameplay.json"
    try:
        cfg = json.loads(await nitrado.download(pfad))
    except (NitradoError, json.JSONDecodeError) as e:
        await interaction.followup.send(f"❌ cfggameplay.json nicht lesbar: {e}", ephemeral=True)
        return
    liste = cfg.setdefault("WorldsData", {}).setdefault("objectSpawnersArr", [])
    if SPAWN_DATEI not in liste:
        liste.append(SPAWN_DATEI)
        await nitrado.upload(pfad, json.dumps(cfg, indent=4))
    await spawn_datei_schreiben()
    await interaction.followup.send(
        f"✅ `{SPAWN_DATEI}` ist in cfggameplay.json eingetragen.\n"
        "Wichtig: Im Nitrado-Webinterface unter *Einstellungen* muss "
        "**cfggameplay.json aktiviert** sein.", ephemeral=True)


@bot.tree.error
async def fehler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        text = "❌ Dafür brauchst du Admin-Rechte."
    else:
        log.exception("Befehlsfehler", exc_info=error)
        text = "❌ Da ist etwas schiefgelaufen. Bitte später erneut versuchen."
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
