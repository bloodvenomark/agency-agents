"""Passt die Nasdara-Serverdateien an. Aufruf: python3 -I anpassen.py <original-ordner> <ziel-ordner>"""
import json
import math
import re
import sys
from pathlib import Path

SRC, DST = Path(sys.argv[1]), Path(sys.argv[2])
(DST / "db").mkdir(parents=True, exist_ok=True)
(DST / "custom").mkdir(parents=True, exist_ok=True)
bericht = []


def hoch(n: int, faktor: float) -> int:
    return int(math.floor(n * faktor + 0.5))


# --- types.xml: Loot +50 %, Tier-3-Freigaben, Füllstände -------------------
LOOT_FAKTOR = 1.5
# Tier-4-Items (Unique), die allgemein in Tier 3 (gelb) spawnen sollen
TIER3_ALLGEMEIN = ["PlateCarrierVest", "PlateCarrierHolster", "PlateCarrierPouches",
                   "NVGoggles", "NVGHeadstrap"]
# ca. 10 % der übrigen Tier-4-Items zusätzlich in Tier 3 möglich
TIER3_ZEHN_PROZENT = ["AK_Suppressor", "Mag_CMAG_40Rnd", "Mag_STANAG_60Rnd"]
VOLL = ["CanisterGasoline", "WaterBottle"]
# M4A1 fest pro Restart-Zyklus (Restart alle 2 h ab 00 Uhr = 7200 s): die normale M4A1 1x nur in
# Tier 3 (gelb), die schwarze Variante 2x nur in Tier 4 (lila). Eine Klasse kann nicht auf
# zwei Gebiete mit fester Stückzahl verteilt werden, daher zwei Klassen.
# lifetime: ungelootet verschwindet sie nach 2 h und spawnt woanders neu,
# restock: nach dem Looten kommt erst nach 2 h eine neue.
M4_ZYKLUS = 7200
FESTE_TYPEN = {
    "M4A1": ("Tier3", "Military", 1),
    "M4A1_Black": ("Unique", "ContaminatedArea", 2),
}
PRO_RESTART = {}
# Loot-Respawn höchstens 15 min (Items mit kürzerer Zeit bzw. 0 bleiben schneller)
MAX_RESTOCK = 900
restock_gekuerzt = 0
types = (SRC / "types.xml").read_text("utf-8")
summe_alt = summe_neu = geaendert = 0


def type_block(m: re.Match) -> str:
    global summe_alt, summe_neu, geaendert
    block = m.group(0)
    name = re.match(r'<type name="([^"]+)"', block).group(1)
    if name in PRO_RESTART:
        block = re.sub(r"<lifetime>\d+</lifetime>", f"<lifetime>{PRO_RESTART[name]}</lifetime>", block)
        block = re.sub(r"<restock>\d+</restock>", f"<restock>{PRO_RESTART[name]}</restock>", block)
    else:
        rs = re.search(r"<restock>(\d+)</restock>", block)
        if rs and int(rs.group(1)) > MAX_RESTOCK:
            global restock_gekuerzt
            restock_gekuerzt += 1
            block = block.replace(rs.group(0), f"<restock>{MAX_RESTOCK}</restock>", 1)
    if name in TIER3_ALLGEMEIN + TIER3_ZEHN_PROZENT + list(PRO_RESTART):
        einfuegen = ""
        if '<usage name="Military"/>' not in block:
            einfuegen += '<usage name="Military"/>\n        '
        if '<value name="Tier3"/>' not in block:
            einfuegen += '<value name="Tier3"/>\n        '
        block = block.replace('<value name="Unique"/>', einfuegen + '<value name="Unique"/>', 1)
        assert '<value name="Tier3"/>' in block, name
    qm = re.search(r"<quantmin>(-?\d+)</quantmin>", block)
    if name.startswith("Mag_") and qm and qm.group(1) != "-1":
        # Magazine mal fast leer, mal fast voll
        block = re.sub(r"<quantmin>-?\d+</quantmin>", "<quantmin>10</quantmin>", block)
        block = re.sub(r"<quantmax>-?\d+</quantmax>", "<quantmax>90</quantmax>", block)
    if name in VOLL:
        block = re.sub(r"<quantmin>-?\d+</quantmin>", "<quantmin>100</quantmin>", block)
        block = re.sub(r"<quantmax>-?\d+</quantmax>", "<quantmax>100</quantmax>", block)
    nm = re.search(r"<nominal>(\d+)</nominal>", block)
    mm = re.search(r"<min>(\d+)</min>", block)
    if not nm or int(nm.group(1)) == 0:
        return block
    nom = int(nm.group(1))
    # Einzelstücke bleiben einzeln, sonst gäbe es seltene Items doppelt so oft
    neu_nom = nom if nom == 1 else hoch(nom, LOOT_FAKTOR)
    summe_alt += nom
    summe_neu += neu_nom
    block = block.replace(nm.group(0), f"<nominal>{neu_nom}</nominal>", 1)
    if mm:
        neu_min = min(hoch(int(mm.group(1)), LOOT_FAKTOR), neu_nom)
        block = block.replace(mm.group(0), f"<min>{neu_min}</min>", 1)
    if neu_nom != nom:
        geaendert += 1
    return block


types = re.sub(r"<type name=\"[^\"]+\">.*?</type>", type_block, types, flags=re.S)


def fester_typ(name, wert, usage, anzahl):
    return (f'<type name="{name}">\n'
            f'        <nominal>{anzahl}</nominal>\n'
            f'        <lifetime>{M4_ZYKLUS}</lifetime>\n'
            f'        <restock>{M4_ZYKLUS}</restock>\n'
            f'        <min>{anzahl}</min>\n'
            f'        <quantmin>30</quantmin>\n'
            f'        <quantmax>80</quantmax>\n'
            f'        <cost>100</cost>\n'
            f'        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" '
            f'count_in_player="0" crafted="0" deloot="0"/>\n'
            f'        <category name="weapons"/>\n'
            f'        <usage name="{usage}"/>\n'
            f'        <value name="{wert}"/>\n'
            f'    </type>')


for name, (wert, usage, anzahl) in FESTE_TYPEN.items():
    types, n = re.subn(rf'<type name="{name}">.*?</type>', lambda m: fester_typ(name, wert, usage, anzahl),
                       types, count=1, flags=re.S)
    assert n == 1, name
    bericht.append(f"types.xml: {name} fest {anzahl}x in {wert} ({usage}), alle {M4_ZYKLUS // 3600} h")
(DST / "db" / "types.xml").write_text(types, "utf-8")
bericht.append(f"types.xml: Loot-Gesamtmenge {summe_alt} -> {summe_neu} "
               f"(+{(summe_neu / summe_alt - 1) * 100:.1f} %), {geaendert} Items erhöht, "
               f"Respawn bei {restock_gekuerzt} Items auf {MAX_RESTOCK // 60} min verkürzt")

# --- events.xml: Fahrzeuge +50 %, Zombies +30 % ----------------------------
events = (SRC / "events.xml").read_text("utf-8")
spawns = (SRC / "cfgeventspawns.xml").read_text("utf-8")
positionen = {
    m.group(1): len(re.findall(r"<pos ", m.group(2)))
    for m in re.finditer(r"<event name=\"(\w+)\">(.*?)</event>", spawns, flags=re.S)
}
fahrzeug_typen = set()


def event_block(m: re.Match) -> str:
    block, name = m.group(0), m.group(1)
    if "<active>1</active>" not in block:
        return block
    if name.startswith("Vehicle"):
        faktor = 1.5
        fahrzeug_typen.update(re.findall(r'type="([^"]+)"', block))
    elif name.startswith("Infected"):
        faktor = 1.3
    else:
        return block
    werte = {}
    for feld in ("nominal", "min", "max"):
        alt = int(re.search(rf"<{feld}>(\d+)</{feld}>", block).group(1))
        werte[feld] = (alt, hoch(alt, faktor))
        block = re.sub(rf"<{feld}>\d+</{feld}>", f"<{feld}>{werte[feld][1]}</{feld}>", block, count=1)
    if name.startswith("Vehicle"):
        # Anzahl pro Fahrzeugtyp mitskalieren, sonst begrenzen die Kinder das Event
        def kind(k: re.Match) -> str:
            return (f'max="{hoch(int(k.group(1)), faktor)}" min="{hoch(int(k.group(2)), faktor)}"')
        block = re.sub(r'max="(\d+)" min="(\d+)"', kind, block)
        pos = positionen.get(name, 0)
        warnung = "" if pos >= werte["nominal"][1] else "  ⚠ zu wenige Spawnpunkte!"
        bericht.append(f"events.xml {name}: nominal {werte['nominal'][0]} -> {werte['nominal'][1]}, "
                       f"max {werte['max'][0]} -> {werte['max'][1]} (Spawnpunkte: {pos}){warnung}")
    return block


events = re.sub(r"<event name=\"(\w+)\">.*?</event>", event_block, events, flags=re.S)
(DST / "db" / "events.xml").write_text(events, "utf-8")
bericht.append("events.xml: aktive Infected-Events nominal/min/max +30 %")

# --- globals.xml: Zombie-Obergrenze +30 % -----------------------------------
glob = (SRC / "globals.xml").read_text("utf-8")
glob = glob.replace('<var name="ZombieMaxCount" type="0" value="1000"/>',
                    '<var name="ZombieMaxCount" type="0" value="1300"/>')
assert 'value="1300"' in glob
# Loot-Zustand nur "abgenutzt" (70-50 % Zustand) oder "beschädigt" (50-30 % Zustand):
# kein makelloser, kein stark beschädigter und kein ruinierter Loot
LOOT_SCHADEN = (0.30, 0.70)
glob = glob.replace('<var name="LootDamageMax" type="1" value="0.82"/>',
                    f'<var name="LootDamageMax" type="1" value="{LOOT_SCHADEN[1]}"/>')
glob = glob.replace('<var name="LootDamageMin" type="1" value="0.0"/>',
                    f'<var name="LootDamageMin" type="1" value="{LOOT_SCHADEN[0]}"/>')
assert f'value="{LOOT_SCHADEN[0]}"' in glob and f'value="{LOOT_SCHADEN[1]}"' in glob
(DST / "db" / "globals.xml").write_text(glob, "utf-8")
bericht.append(f"globals.xml: ZombieMaxCount 1000 -> 1300, Loot-Schaden {LOOT_SCHADEN[0]}-{LOOT_SCHADEN[1]}")

# --- env/zombie_territories.xml: Zombies +30 % -------------------------------
(DST / "env").mkdir(exist_ok=True)
zt = (SRC / "zombie_territories.xml").read_text("utf-8")
# Safezone (Moschee bei x 8700 / z 8264): keine Zombie-Zonen im Umkreis von 300 m
SAFEZONE, SAFEZONE_ZOMBIEFREI = (8699.5, 8263.6), 300
zonen_vorher = zt.count("<zone ")
zt = re.sub(r'\s*<zone [^>]*x="([\d.]+)" z="([\d.]+)"[^>]*/>',
            lambda m: "" if math.dist((float(m.group(1)), float(m.group(2))), SAFEZONE) < SAFEZONE_ZOMBIEFREI
            else m.group(0), zt)
bericht.append(f"zombie_territories.xml: {zonen_vorher - zt.count('<zone ')} Zombie-Zonen an der Safezone entfernt")
zz_alt = sum(int(x) for x in re.findall(r'dmax="(\d+)"', zt))
zt = re.sub(r'(smin|smax|dmin|dmax)="(\d+)"', lambda m: f'{m.group(1)}="{hoch(int(m.group(2)), 1.3)}"', zt)
zz_neu = sum(int(x) for x in re.findall(r'dmax="(\d+)"', zt))
(DST / "env" / "zombie_territories.xml").write_text(zt, "utf-8")
bericht.append(f"zombie_territories.xml: Zombies pro Zone +30 % (Summe dmax {zz_alt} -> {zz_neu})")

# --- cfgspawnabletypes.xml: Fahrzeuge voll ausgestattet ---------------------
spawnable = (SRC / "cfgspawnabletypes.xml").read_text("utf-8")
fahrzeug_typen.update(["Boat_01_Black", "Boat_01_Blue", "Boat_01_Orange"])
ausgestattet = []


def spawnable_block(m: re.Match) -> str:
    block, name = m.group(0), m.group(1)
    if name not in fahrzeug_typen:
        # Eigene Zustandswerte einzelner Items (Waffen, Optiken ...) an den Loot-Zustand angleichen;
        # Einträge mit max 0 (immer makellos, z. B. Event-Items) bleiben
        def zustand(d: re.Match) -> str:
            if float(d.group(2)) == 0:
                return d.group(0)
            return f'<damage min="{LOOT_SCHADEN[0]}" max="{LOOT_SCHADEN[1]}" />'
        return re.sub(r'<damage min="([\d.]+)" max="([\d.]+)" />', zustand, block)
    ausgestattet.append(name)
    # Nur Anbauteile (attachments), Ladung (cargo) bleibt wie sie ist
    def anbau(a: re.Match) -> str:
        teil = re.sub(r'chance="[\d.]+"', 'chance="1.00"', a.group(0))
        return teil
    block = re.sub(r"<attachments chance=\"[\d.]+\">.*?</attachments>", anbau, block, flags=re.S)
    if not name.startswith(("Motorbike", "Boat")):
        ladung = '\t\t<cargo chance="1.00">\n\t\t\t<item name="{}" chance="1.00" />\n\t\t</cargo>\n'
        zusatz = ladung.format("CanisterGasoline") + ladung.format("WaterBottle") * 5
        block = block.replace("\t</type>", zusatz + "\t</type>")
        beladen.append(name)
    return block


beladen = []


def magazin_block(m: re.Match) -> str:
    """Waffen spawnen nur noch zu 50 % mit Magazin."""
    if 'item name="Mag_' not in m.group(0):
        return m.group(0)
    return re.sub(r'<attachments chance="[\d.]+">', '<attachments chance="0.50">', m.group(0), count=1)


spawnable = re.sub(r"<type name=\"([^\"]+)\">.*?</type>", spawnable_block, spawnable, flags=re.S)
m4 = re.search(r'\t<type name="M4A1">.*?</type>\n', spawnable, flags=re.S).group(0)
assert '<type name="M4A1_Black">' not in spawnable
spawnable = spawnable.replace(m4, m4 + m4.replace('"M4A1"', '"M4A1_Black"'), 1)
mags_vorher = spawnable.count('item name="Mag_')
spawnable = re.sub(r"<attachments chance=\"[\d.]+\">(?:\s*<item name=\"Mag_[^/]*/>)+\s*</attachments>",
                   magazin_block, spawnable)
bericht.append(f"cfgspawnabletypes.xml: {mags_vorher} Magazin-Slots an Waffen auf 50 %")
(DST / "cfgspawnabletypes.xml").write_text(spawnable, "utf-8")
fehlend = sorted(fahrzeug_typen - set(ausgestattet))
bericht.append(f"cfgspawnabletypes.xml: {len(ausgestattet)} Fahrzeugtypen voll ausgestattet"
               + (f" (nicht in Datei: {', '.join(fehlend)})" if fehlend else "")
               + f", {len(beladen)} davon mit Kanister + 5 Wasserflaschen")

# --- cfggameplay.json -------------------------------------------------------
gp = (SRC / "cfggameplay.json").read_text("utf-8")
ersetzungen = [
    ('"displayPlayerPosition": false', '"displayPlayerPosition": true'),
    # Positionspunkt ohne Kompass/GPS anzeigen
    ('"ignoreNavItemsOwnership": false', '"ignoreNavItemsOwnership": true'),
    ('"disableItemFalling": false', '"disableItemFalling": true'),
    # Safezone-Moschee mit Vorrat (Object Spawner)
    ('"objectSpawnersArr": []', '"objectSpawnersArr": ["custom/safezone.json", "custom/teleport_dixi.json"]'),
    # Relog-Teleporter: wer sich in einem Dixi-Klo ausloggt, landet beim Einloggen in der Safezone
    ('"wetnessWeightModifiers": [1.0, 1.0, 1.33, 1.66, 2.0]',
     '"wetnessWeightModifiers": [1.0, 1.0, 1.33, 1.66, 2.0],\n    '
     '"playerRestrictedAreaFiles": ["custom/teleport_safezone.json"]'),
    # Ausdauer nur noch beim Springen/Klettern (obstacleTraversal bleibt 1.0)
    ('"sprintStaminaModifierErc": 1.0', '"sprintStaminaModifierErc": 0.0'),
    ('"sprintStaminaModifierCro": 1.0', '"sprintStaminaModifierCro": 0.0'),
    ('"staminaKgToStaminaPercentPenalty": 1.75', '"staminaKgToStaminaPercentPenalty": 0.0'),
    ('"sprintSwimmingStaminaModifier": 1.0', '"sprintSwimmingStaminaModifier": 0.0'),
    ('"sprintLadderStaminaModifier": 1.0', '"sprintLadderStaminaModifier": 0.0'),
    ('"meleeStaminaModifier": 1.0', '"meleeStaminaModifier": 0.0'),
    ('"holdBreathStaminaModifier": 1.0', '"holdBreathStaminaModifier": 0.0'),
    ('"disablePersonalLight": true,',
     '"disablePersonalLight": true,\n    "spawnGearPresetFiles": ["custom/startgear.json"],'),
]
for alt, neu in ersetzungen:
    assert gp.count(alt) == 1, alt
    gp = gp.replace(alt, neu)
json.loads(gp)  # muss gültiges JSON bleiben
(DST / "cfggameplay.json").write_text(gp, "utf-8")
bericht.append("cfggameplay.json: Spielerposition auf Karte an, Startausrüstung eingebunden, "
               "disableItemFalling = true, Ausdauer nur beim Springen/Klettern")

print("\n".join(bericht))
