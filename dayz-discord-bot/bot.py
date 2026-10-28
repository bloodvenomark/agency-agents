"""DayZ-Discord-Bot für Nitrado / PlayStation.

Funktionen: Shop mit Lieferung an Orte, Killfeed mit Belohnung, Hitfeed,
Kopfgeld-System (manuell + automatisch bei Killserien), Lootdrops/Airdrops.

Ablauf einer Lieferung bzw. eines Lootdrops:
  1. Der Bot schreibt alle wartenden Items in eine Object-Spawner-Datei
     (custom/shop_lieferungen.json im Missionsordner).
  2. Beim nächsten Server-Neustart spawnt DayZ die Items an den Koordinaten.
  3. Der Bot erkennt den Neustart, meldet die Lieferung bzw. den Airdrop
     und leert die Datei wieder (sonst würden sie bei jedem Neustart erneut spawnen).
"""

import asyncio
import json
import logging
import math
import os
import random
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import lootdrop
from adm import Kill, Treffer, parse_zeile
from db import DB
from nitrado import Nitrado, NitradoError

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dayzbot")


def _int(name: str, default: int) -> int:
    wert = os.getenv(name, "").strip()
    return int(wert) if wert else default


def _bool(name: str, default: bool) -> bool:
    wert = os.getenv(name, "").strip().lower()
    return wert == "true" if wert else default


BASIS = Path(__file__).parent
GUILD = discord.Object(id=int(os.environ["GUILD_ID"]))
ADMIN_ROLE = os.getenv("ADMIN_ROLE", "DayZ Admin")
MISSION = os.getenv("MISSION", "dayzOffline.chernarusplus")
START_GELD = _int("START_GELD", 500)
TAEGLICH_BONUS = _int("TAEGLICH_BONUS", 250)
KILL_BELOHNUNG = _int("KILL_BELOHNUNG", 100)
KILL_BONUS_PRO_100M = _int("KILL_BONUS_PRO_100M", 0)
WAEHRUNG = os.getenv("WAEHRUNG", "Rubel")
NEUSTART_NACH_KAUF = _bool("NEUSTART_NACH_KAUF", False)

# Schlüssel -> (Kanalname, .env-Variable, Spieler dürfen schreiben)
KANAELE = {
    "shop":     ("🛒│shop",     None,             True),
    "killfeed": ("💀│killfeed", "KILLFEED_KANAL", False),
    "hitfeed":  ("🎯│hitfeed",  "HITFEED_KANAL",  False),
    "kopfgeld": ("💰│kopfgeld", "KOPFGELD_KANAL", False),
    "airdrops": ("🪂│airdrops", "LOOTDROP_KANAL", False),
}
KATEGORIE = os.getenv("KATEGORIE", "🧟 DayZ")
KANAELE_AUTOMATISCH = _bool("KANAELE_AUTOMATISCH", True)
HITFEED_AN = _bool("HITFEED_AN", True)
if not HITFEED_AN:
    del KANAELE["hitfeed"]

KOPFGELD_MINIMUM = _int("KOPFGELD_MINIMUM", 100)
AUTO_KOPFGELD_AB_SERIE = _int("AUTO_KOPFGELD_AB_SERIE", 5)    # 0 = aus
AUTO_KOPFGELD_START = _int("AUTO_KOPFGELD_START", 500)
AUTO_KOPFGELD_PRO_KILL = _int("AUTO_KOPFGELD_PRO_KILL", 100)
KOPFGELD_STANDORT_ZEIGEN = _bool("KOPFGELD_STANDORT_ZEIGEN", True)

SPAWN_DATEI = "custom/shop_lieferungen.json"   # relativ zum Missionsordner
STANDORT = "Mein Standort"
ZUFALL = "🎲 Zufall"
STANDORT_MAX_ALTER = 15 * 60                    # Sekunden

SHOP: dict[str, list[dict]] = json.loads((BASIS / "shop.json").read_text("utf-8"))
ARTIKEL = {a["name"]: a for kat in SHOP.values() for a in kat}
ORTE: dict[str, list[float]] = {
    k: v for k, v in json.loads((BASIS / "orte.json").read_text("utf-8")).items()
    if not k.startswith("_")
}
LOOTDROPS: dict = json.loads((BASIS / "lootdrops.json").read_text("utf-8"))

KOERPERTEILE = {
    "Head": "Kopf", "Brain": "Kopf", "Torso": "Oberkörper", "Spine": "Oberkörper",
    "Pelvis": "Hüfte", "LeftArm": "linken Arm", "RightArm": "rechten Arm",
    "LeftHand": "linke Hand", "RightHand": "rechte Hand", "LeftLeg": "linkes Bein",
    "RightLeg": "rechtes Bein", "LeftFoot": "linken Fuß", "RightFoot": "rechten Fuß",
}

db = DB(str(BASIS / "data" / "bot.db"))
nitrado = Nitrado(os.environ["NITRADO_TOKEN"], os.environ["NITRADO_SERVICE_ID"])
pfade: dict[str, str] = {}
datei_lock = asyncio.Lock()


def geld(betrag: int) -> str:
    return f"{betrag:,} {WAEHRUNG}".replace(",", ".")


def koords(x: float, z: float, runden: int = 1) -> str:
    """Koordinaten wie auf izurvive.com (x / z), optional auf z. B. 100 m gerundet."""
    return f"{round(x / runden) * runden:.0f} / {round(z / runden) * runden:.0f}"


async def pfade_ermitteln():
    gs = await nitrado.gameserver()
    basis = gs.get("game_specific", {}).get("path", "")
    pfade["mission"] = os.getenv("MISSION_DIR") or f"{basis}mpmissions/{MISSION}/"
    pfade["adm"] = os.getenv("ADM_LOG_DIR") or f"{basis}config/"
    log.info("Missionsordner: %s | ADM-Logs: %s", pfade["mission"], pfade["adm"])


# --- Spawn-Datei (Lieferungen + Lootdrops) --------------------------------

def _objekt(klasse: str, x: float, y: float, z: float) -> dict:
    return {"name": klasse, "pos": [round(x, 2), round(y, 2), round(z, 2)],
            "ypr": [0.0, 0.0, 0.0], "scale": 1.0, "enableCEPersistency": 0}


def spawn_objekte(bestellungen, drops=()) -> dict:
    """Baut den Inhalt der Object-Spawner-Datei. Mehrere Items werden im Kreis verteilt."""
    objekte = []
    for b in bestellungen:
        for i in range(b["menge"]):
            winkel = 2 * math.pi * i / max(b["menge"], 1)
            radius = 0.6 if b["menge"] > 1 else 0.0
            objekte.append(_objekt(b["klasse"], b["x"] + radius * math.cos(winkel),
                                   b["y"], b["z"] + radius * math.sin(winkel)))
    for d in drops:
        objekte += [_objekt(*o) for o in json.loads(d["objekte"])]
    return {"Objects": objekte}


async def spawn_datei_schreiben():
    async with datei_lock:
        inhalt = json.dumps(spawn_objekte(db.wartende(), db.lootdrops_wartend()), indent=2)
        await nitrado.upload(pfade["mission"] + SPAWN_DATEI, inhalt)


async def datei_aktualisieren():
    """Schreibt die Datei nur, wenn der Server läuft – während eines Neustarts würde
    sonst neu Hinzugefügtes schon geladen und nach dem Neustart erneut gespawnt."""
    if db.get("server_status") == "started":
        try:
            await spawn_datei_schreiben()
        except NitradoError as e:
            log.error("Upload fehlgeschlagen: %s", e)


# --- Bot ------------------------------------------------------------------

class DayZBot(commands.Bot):
    async def setup_hook(self):
        await pfade_ermitteln()
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)
        status_schleife.start()
        log_schleife.start()

    async def on_ready(self):
        log.info("Eingeloggt als %s", self.user)
        if KANAELE_AUTOMATISCH and not db.get("kanaele_erstellt"):
            guild = self.get_guild(GUILD.id)
            if guild:
                try:
                    await kanaele_erstellen(guild)
                    db.set("kanaele_erstellt", "1")
                except discord.Forbidden:
                    log.error("Keine Rechte zum Erstellen der Kanäle/Rolle "
                              "(Kanäle verwalten + Rollen verwalten nötig).")

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


def kanal_id(schluessel: str) -> int:
    """Kanal-ID aus der .env, sonst die vom Bot selbst erstellte."""
    if schluessel not in KANAELE:
        return 0
    env = KANAELE[schluessel][1]
    return (_int(env, 0) if env else 0) or int(db.get(f"kanal_{schluessel}", "0") or 0)


async def kanaele_erstellen(guild: discord.Guild) -> list[str]:
    """Legt Kategorie, Kanäle und Admin-Rolle an. Vorhandenes wird wiederverwendet."""
    erledigt = []
    if not discord.utils.get(guild.roles, name=ADMIN_ROLE):
        await guild.create_role(name=ADMIN_ROLE, reason="DayZ-Bot Einrichtung")
        erledigt.append(f"Rolle **{ADMIN_ROLE}** erstellt")

    kategorie = discord.utils.get(guild.categories, name=KATEGORIE)
    if not kategorie:
        kategorie = await guild.create_category(KATEGORIE, reason="DayZ-Bot Einrichtung")
        erledigt.append(f"Kategorie **{KATEGORIE}** erstellt")

    for schluessel, (name, _, schreiben) in KANAELE.items():
        vorhanden = guild.get_channel(kanal_id(schluessel)) or discord.utils.get(
            guild.text_channels, name=name)
        if vorhanden:
            db.set(f"kanal_{schluessel}", str(vorhanden.id))
            continue
        rechte = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=schreiben, add_reactions=True),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, embed_links=True),
        }
        kanal = await guild.create_text_channel(
            name, category=kategorie, overwrites=rechte, reason="DayZ-Bot Einrichtung")
        db.set(f"kanal_{schluessel}", str(kanal.id))
        erledigt.append(f"Kanal {kanal.mention} erstellt")
    log.info("Kanal-Einrichtung: %s", erledigt or "alles vorhanden")
    return erledigt


async def posten(schluessel: str, embed: discord.Embed):
    kanal_id_ = kanal_id(schluessel)
    if not kanal_id_:
        return
    kanal = bot.get_channel(kanal_id_)
    if kanal is None:
        log.warning("Kanal %s nicht gefunden", kanal_id_)
        return
    try:
        await kanal.send(embed=embed)
    except discord.HTTPException as e:
        log.warning("Posten in %s fehlgeschlagen: %s", kanal_id_, e)


# --- Killfeed, Hitfeed, Kopfgeld -------------------------------------------

async def kill_verarbeiten(k: Kill):
    serie = db.stat_kill(k.taeter, k.distanz)
    db.stat_tod(k.opfer, durch_spieler=True)

    belohnung = KILL_BELOHNUNG + KILL_BONUS_PRO_100M * int((k.distanz or 0) // 100)
    konto = db.konto_per_gamertag(k.taeter)
    kopf = db.kopfgeld(k.opfer)
    kopfgeld = 0
    if kopf and konto:
        kopfgeld = kopf["betrag"] + kopf["auto_betrag"]
        db.kopfgeld_entfernen(k.opfer)
    else:
        db.kopfgeld_auto_zuruecksetzen(k.opfer)   # Serie des Opfers ist vorbei

    if konto:
        db.geld_aendern(konto["discord_id"], belohnung + kopfgeld)

    # Killfeed
    waffe = k.waffe or "unbekannt"
    distanz = f" aus **{k.distanz:.0f} m**" if k.distanz is not None else ""
    embed = discord.Embed(
        description=f"☠️ **{k.taeter}** hat **{k.opfer}** getötet\n🔫 {waffe}{distanz}",
        color=0xB71C1C,
    )
    if konto and belohnung:
        embed.add_field(name="Belohnung", value=f"+{geld(belohnung)}")
    if serie >= 3:
        embed.add_field(name="Killserie", value=f"🔥 {serie}")
    if kopfgeld:
        embed.add_field(name="Kopfgeld kassiert", value=f"💰 {geld(kopfgeld)}")
    await posten("killfeed", embed)

    if konto:
        text = f"💀 Kill an **{k.opfer}**: +{geld(belohnung)}"
        if kopfgeld:
            text += f"\n💰 Kopfgeld kassiert: +{geld(kopfgeld)}"
        await benachrichtigen(konto["discord_id"], text)

    if kopfgeld:
        await posten("kopfgeld", discord.Embed(
            title="💰 Kopfgeld kassiert!",
            description=f"**{k.taeter}** hat **{k.opfer}** erledigt und "
                        f"**{geld(kopfgeld)}** kassiert.",
            color=0xF9A825,
        ))

    # Automatisches Kopfgeld bei Killserie
    if AUTO_KOPFGELD_AB_SERIE and serie >= AUTO_KOPFGELD_AB_SERIE:
        plus = AUTO_KOPFGELD_START if serie == AUTO_KOPFGELD_AB_SERIE else AUTO_KOPFGELD_PRO_KILL
        db.kopfgeld_auto(k.taeter, plus)
        await kopfgeld_ankuendigen(
            k.taeter, f"🔥 **{k.taeter}** hat eine Killserie von **{serie}**!", automatisch=True)


async def kopfgeld_ankuendigen(gamertag: str, grund: str, automatisch: bool = False):
    kopf = db.kopfgeld(gamertag)
    if not kopf:
        return
    gesamt = kopf["betrag"] + kopf["auto_betrag"]
    embed = discord.Embed(
        title="🎯 Kopfgeld ausgesetzt" + (" (automatisch)" if automatisch else ""),
        description=f"{grund}\nAuf **{gamertag}** sind jetzt **{geld(gesamt)}** ausgesetzt.",
        color=0xF9A825,
    )
    p = db.position(gamertag)
    if KOPFGELD_STANDORT_ZEIGEN and p and time.time() - p["zeit"] < STANDORT_MAX_ALTER:
        embed.add_field(name="Zuletzt gesehen (± 100 m)", value=koords(p["x"], p["z"], 100))
    embed.set_footer(text="Wer ihn tötet, kassiert das Kopfgeld (Discord-Verknüpfung nötig).")
    await posten("kopfgeld", embed)


async def treffer_posten(t: Treffer):
    if not kanal_id("hitfeed"):
        return
    teil = KOERPERTEILE.get(t.koerperteil or "", t.koerperteil or "Körper")
    zeilen = [f"🎯 **{t.angreifer}** traf **{t.opfer}** am **{teil}**"]
    details = []
    if t.waffe:
        details.append(f"🔫 {t.waffe}")
    if t.distanz is not None:
        details.append(f"📏 {t.distanz:.0f} m")
    if t.schaden is not None:
        details.append(f"💥 {t.schaden:.0f} Schaden")
    details.append(f"❤️ {max(t.hp, 0):.0f} HP übrig")
    zeilen.append(" • ".join(details))
    farbe = 0xE65100 if t.koerperteil in ("Head", "Brain") else 0x546E7A
    await posten("hitfeed", discord.Embed(description="\n".join(zeilen), color=farbe))


# --- Lootdrops ---------------------------------------------------------------

async def lootdrop_planen(paket: str | None = None, ort: str | None = None) -> tuple:
    paket, ort, pos, objekte = lootdrop.erzeugen(LOOTDROPS, paket, ort)
    nr = db.lootdrop_anlegen(paket, ort, *pos, objekte)
    log.info("Lootdrop #%d geplant: %s bei %s (%d Objekte)", nr, paket, ort, len(objekte))
    return nr, paket, ort, pos


async def lootdrop_gelandet(d):
    anzahl = len(json.loads(d["objekte"]))
    embed = discord.Embed(
        title="🪂 Airdrop gelandet!",
        description=f"Ein **{d['paket']}**-Paket ist bei **{d['ort']}** gelandet.",
        color=0x1565C0,
    )
    embed.add_field(name="Koordinaten", value=koords(d["x"], d["z"]))
    embed.add_field(name="Items", value=str(anzahl))
    embed.set_footer(text="Wer zuerst kommt, mahlt zuerst. Vorsicht vor Campern!")
    await posten("airdrops", embed)


# --- Hintergrund-Schleifen -------------------------------------------------

@tasks.loop(seconds=30)
async def status_schleife():
    """Erkennt Server-Neustarts, schließt Lieferungen/Lootdrops ab, plant Airdrops."""
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
        db.set("drop_snapshot", str(db.letzte_lootdrop_id()))
        log.info("Neustart erkannt (%s)", jetzt)

    elif vorher not in (None, "started") and jetzt == "started":
        liefer = int(db.get("liefer_snapshot", "0") or 0)
        drops = int(db.get("drop_snapshot", "0") or 0)
        db.set("liefer_snapshot", "0")
        db.set("drop_snapshot", "0")
        geliefert = db.als_geliefert(liefer) if liefer else []
        gelandet = db.lootdrops_gelandet(drops) if drops else []
        log.info("Server läuft wieder: %d Lieferungen, %d Lootdrops",
                 len(geliefert), len(gelandet))

        for b in geliefert:
            await benachrichtigen(
                b["discord_id"],
                f"📦 Deine Lieferung **{b['artikel']}** liegt jetzt bei **{b['ort']}** bereit!",
            )
        for d in gelandet:
            await lootdrop_gelandet(d)

        # Automatischen Airdrop für den nächsten Neustart planen
        auto = LOOTDROPS.get("automatisch", {})
        if auto.get("aktiv") and random.uniform(0, 100) < auto.get("chance_pro_neustart", 0):
            _, paket, ort, _ = await lootdrop_planen()
            text = f"Beim nächsten Neustart wird ein **{paket}**-Paket abgeworfen"
            text += f" bei **{ort}**!" if auto.get("ort_vorher_ankuendigen") else ". Ort: geheim 🤫"
            await posten("airdrops", discord.Embed(
                title="✈️ Airdrop angekündigt", description=text, color=0x1565C0))

        try:
            await spawn_datei_schreiben()   # Geliefertes entfernen, Neues behalten
        except NitradoError as e:
            log.error("Upload fehlgeschlagen: %s", e)


@tasks.loop(seconds=60)
async def log_schleife():
    """Liest neue Zeilen aus dem ADM-Log: Positionen, Kills, Treffer, Tode."""
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
        e = parse_zeile(zeile)
        for p in e.positionen:
            db.position_setzen(p.gamertag, p.x, p.hoehe, p.z)
        try:
            if e.kill:
                await kill_verarbeiten(e.kill)
            elif e.treffer:
                await treffer_posten(e.treffer)
            elif e.tod:
                db.stat_tod(e.tod, durch_spieler=False)
                db.kopfgeld_auto_zuruecksetzen(e.tod)
        except Exception:
            log.exception("Fehler bei Logzeile: %s", zeile)

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
        ort_name = f"deinem Standort ({koords(p['x'], p['z'])})"
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
    await datei_aktualisieren()
    if NEUSTART_NACH_KAUF and db.get("server_status") == "started":
        try:
            await nitrado.restart("Shop-Lieferung")
        except NitradoError as e:
            log.error("Neustart fehlgeschlagen: %s", e)

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


async def spieler_auswahl(interaction: discord.Interaction, aktuell: str):
    return [app_commands.Choice(name=g, value=g) for g in db.bekannte_spieler(aktuell)]


@bot.tree.command(name="statistik", description="Kills, Tode und Killserie eines Spielers")
@app_commands.autocomplete(gamertag=spieler_auswahl)
async def statistik(interaction: discord.Interaction, gamertag: str | None = None):
    if not gamertag:
        k = db.konto(interaction.user.id)
        if not k:
            await interaction.response.send_message("Nutze zuerst `/verknuepfen`.", ephemeral=True)
            return
        gamertag = k["gamertag"]
    s = db.statistik(gamertag)
    if not s:
        await interaction.response.send_message(f"Keine Daten zu **{gamertag}**.", ephemeral=True)
        return
    kd = s["kills"] / s["tode"] if s["tode"] else s["kills"]
    embed = discord.Embed(title=f"📊 {s['gamertag']}", color=0x37474F)
    embed.add_field(name="Kills", value=str(s["kills"]))
    embed.add_field(name="Tode (PvP)", value=str(s["tode"]))
    embed.add_field(name="K/D", value=f"{kd:.2f}")
    embed.add_field(name="Aktuelle Serie", value=str(s["serie"]))
    embed.add_field(name="Beste Serie", value=str(s["beste_serie"]))
    embed.add_field(name="Weitester Kill", value=f"{s['weitester']:.0f} m")
    kopf = db.kopfgeld(gamertag)
    if kopf:
        embed.add_field(name="Kopfgeld", value=geld(kopf["betrag"] + kopf["auto_betrag"]))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="bestenliste", description="Die Top 10 nach Kills")
async def bestenliste(interaction: discord.Interaction):
    rows = db.bestenliste()
    if not rows:
        await interaction.response.send_message("Noch keine Kills erfasst.")
        return
    medaillen = ["🥇", "🥈", "🥉"]
    text = "\n".join(
        f"{medaillen[i] if i < 3 else f'`{i + 1}.`'} **{r['gamertag']}** – "
        f"{r['kills']} Kills / {r['tode']} Tode (beste Serie {r['beste_serie']})"
        for i, r in enumerate(rows))
    await interaction.response.send_message(
        embed=discord.Embed(title="🏆 Bestenliste", description=text, color=0xF9A825))


kopfgeld_gruppe = app_commands.Group(name="kopfgeld", description="Kopfgeld-System")


@kopfgeld_gruppe.command(name="setzen", description="Setze ein Kopfgeld aus deinem Guthaben aus")
@app_commands.describe(gamertag="Auf wen?", betrag="Wie viel?")
@app_commands.autocomplete(gamertag=spieler_auswahl)
async def kopfgeld_setzen(interaction: discord.Interaction, gamertag: str, betrag: int):
    k = db.konto(interaction.user.id)
    if not k:
        await interaction.response.send_message("Nutze zuerst `/verknuepfen`.", ephemeral=True)
        return
    if betrag < KOPFGELD_MINIMUM:
        await interaction.response.send_message(
            f"❌ Mindestens {geld(KOPFGELD_MINIMUM)}.", ephemeral=True)
        return
    if gamertag.lower() == (k["gamertag"] or "").lower():
        await interaction.response.send_message("❌ Nicht auf dich selbst.", ephemeral=True)
        return
    if not db.position(gamertag):
        await interaction.response.send_message(
            f"❌ **{gamertag}** war noch nie auf dem Server. Bitte Schreibweise prüfen.",
            ephemeral=True)
        return
    try:
        db.kopfgeld_setzen(interaction.user.id, gamertag, betrag)
    except ValueError:
        await interaction.response.send_message(
            f"❌ Nicht genug Geld (du hast {geld(k['geld'])}).", ephemeral=True)
        return
    await interaction.response.send_message(
        f"✅ {geld(betrag)} Kopfgeld auf **{gamertag}** ausgesetzt.", ephemeral=True)
    await kopfgeld_ankuendigen(
        gamertag, f"Ein Spieler hat **{geld(betrag)}** auf **{gamertag}** ausgesetzt.")


@kopfgeld_gruppe.command(name="liste", description="Alle offenen Kopfgelder")
async def kopfgeld_liste(interaction: discord.Interaction):
    rows = db.kopfgelder()
    if not rows:
        await interaction.response.send_message("Keine offenen Kopfgelder. 🕊️")
        return
    text = "\n".join(
        f"🎯 **{r['gamertag']}** – {geld(r['gesamt'])}"
        + (" 🔥" if r["auto_betrag"] else "") for r in rows[:25])
    await interaction.response.send_message(embed=discord.Embed(
        title="🎯 Offene Kopfgelder", description=text, color=0xF9A825)
        .set_footer(text="🔥 = enthält automatisches Kopfgeld durch Killserie"))


bot.tree.add_command(kopfgeld_gruppe)


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


@bot.tree.command(name="admin-kopfgeld-entfernen", description="[Admin] Kopfgeld löschen")
@app_commands.check(ist_admin)
@app_commands.autocomplete(gamertag=spieler_auswahl)
async def admin_kopfgeld_entfernen(interaction: discord.Interaction, gamertag: str):
    db.kopfgeld_entfernen(gamertag)
    await interaction.response.send_message(f"✅ Kopfgeld auf **{gamertag}** entfernt.",
                                            ephemeral=True)


async def paket_auswahl(interaction: discord.Interaction, aktuell: str):
    namen = [ZUFALL, *LOOTDROPS["pakete"]]
    return [app_commands.Choice(name=n, value=n) for n in namen
            if aktuell.lower() in n.lower()][:25]


async def drop_ort_auswahl(interaction: discord.Interaction, aktuell: str):
    namen = [ZUFALL, *LOOTDROPS["orte"]]
    return [app_commands.Choice(name=n, value=n) for n in namen
            if aktuell.lower() in n.lower()][:25]


@bot.tree.command(name="admin-lootdrop", description="[Admin] Airdrop für den nächsten Neustart planen")
@app_commands.check(ist_admin)
@app_commands.describe(paket="Loot-Paket (oder Zufall)", ort="Abwurfort (oder Zufall)",
                       sofort="Server sofort neu starten", ankuendigen="Ort öffentlich ankündigen")
@app_commands.autocomplete(paket=paket_auswahl, ort=drop_ort_auswahl)
async def admin_lootdrop(interaction: discord.Interaction, paket: str = ZUFALL,
                         ort: str = ZUFALL, sofort: bool = False, ankuendigen: bool = False):
    paket = None if paket == ZUFALL else paket
    ort = None if ort == ZUFALL else ort
    if (paket and paket not in LOOTDROPS["pakete"]) or (ort and ort not in LOOTDROPS["orte"]):
        await interaction.response.send_message("❌ Unbekanntes Paket oder unbekannter Ort.",
                                                ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    nr, paket, ort, pos = await lootdrop_planen(paket, ort)
    await datei_aktualisieren()
    if sofort:
        await nitrado.restart("Airdrop")

    text = f"Beim {'gleich folgenden' if sofort else 'nächsten'} Neustart wird ein **{paket}**-Paket abgeworfen"
    text += f" bei **{ort}**!" if ankuendigen else ". Ort: geheim 🤫"
    await posten("airdrops", discord.Embed(
        title="✈️ Airdrop angekündigt", description=text, color=0x1565C0))
    await interaction.followup.send(
        f"✅ Lootdrop #{nr}: **{paket}** bei **{ort}** ({koords(pos[0], pos[2])}).",
        ephemeral=True)


@bot.tree.command(name="admin-neustart", description="[Admin] Server neu starten (liefert alles aus)")
@app_commands.check(ist_admin)
async def admin_neustart(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await spawn_datei_schreiben()
    await nitrado.restart("Shop-Lieferung")
    await interaction.followup.send(
        f"🔄 Neustart ausgelöst: {len(db.wartende())} Lieferung(en), "
        f"{len(db.lootdrops_wartend())} Lootdrop(s).", ephemeral=True)


@bot.tree.command(name="admin-kanaele", description="[Admin] Erstellt alle Bot-Kanäle und die Admin-Rolle")
@app_commands.check(ist_admin)
async def admin_kanaele(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        erledigt = await kanaele_erstellen(interaction.guild)
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Mir fehlen Rechte: **Kanäle verwalten** und **Rollen verwalten**.", ephemeral=True)
        return
    db.set("kanaele_erstellt", "1")
    await interaction.followup.send(
        "✅ " + ("\n✅ ".join(erledigt) if erledigt else "Alle Kanäle sind schon vorhanden."),
        ephemeral=True)


@bot.tree.command(name="admin-einrichten", description="[Admin] Trägt die Spawn-Datei in cfggameplay.json ein")
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


@bot.tree.command(name="admin-basisschaden",
                  description="[Admin] Schaden an Basen/Containern in cfggameplay.json ein- oder ausschalten")
@app_commands.check(ist_admin)
@app_commands.describe(basis_schaden="Dürfen Zäune und Wachtürme beschädigt werden?",
                       container_schaden="Dürfen Zelte, Fässer und Kisten beschädigt werden?")
async def admin_basisschaden(interaction: discord.Interaction, basis_schaden: bool,
                             container_schaden: bool | None = None):
    """Ist cfggameplay.json aktiv, gelten deren GeneralData-Werte statt der Schalter
    im Nitrado-Webinterface. Deshalb wird der Wert hier direkt in der Datei gesetzt."""
    await interaction.response.defer(ephemeral=True)
    pfad = pfade["mission"] + "cfggameplay.json"
    try:
        cfg = json.loads(await nitrado.download(pfad))
    except (NitradoError, json.JSONDecodeError) as e:
        await interaction.followup.send(f"❌ cfggameplay.json nicht lesbar: {e}", ephemeral=True)
        return
    general = cfg.setdefault("GeneralData", {})
    general["disableBaseDamage"] = not basis_schaden
    if container_schaden is not None:
        general["disableContainerDamage"] = not container_schaden
    await nitrado.upload(pfad, json.dumps(cfg, indent=4))
    await interaction.followup.send(
        f"✅ cfggameplay.json gespeichert:\n"
        f"• `disableBaseDamage`: **{str(general['disableBaseDamage']).lower()}**\n"
        f"• `disableContainerDamage`: **{str(general.get('disableContainerDamage', False)).lower()}**\n"
        "Wirksam nach dem nächsten Server-Neustart.", ephemeral=True)


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
