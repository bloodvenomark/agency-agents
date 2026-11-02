"""Baut die Safezone: Kopie der großen Nasdara-Moschee an einem neuen Ort, mit eingerichtetem
Innenhof (Object Spawner, kommt nach jedem Restart neu):
Grillplatz, Kisten mit Holz/Streichhölzern und mit Essen/Fleisch, Wasser-Tankwagen mit Flaschen,
Sanitätszelt mit Erster Hilfe auf Tischen.

Aufruf: python3 -I safezone_bau.py <mapgrouppos.xml> <ziel-ordner> [<trader_laeden.json für den Bot>]
Ergebnis: <ziel-ordner>/custom/safezone.json
"""
import json
import math
import re
import sys
from pathlib import Path

# Neuer Mittelpunkt (30 m westlich der Markierung südlich von Bam-e Sabz, frei von Objekten)
MITTE_X, MITTE_Z = 8610.0, 8354.0
# Geschätzte Bodenhöhe aus den Objekten ringsum. Schwebt die Moschee, Wert verkleinern;
# steckt sie zu tief im Boden, Wert vergrößern (in Metern).
BODEN = 279.0
HOEHE_KORREKTUR = -0.5   # lieber etwas einsinken lassen als schweben

ORIGINAL_BODEN = 179.249  # Bodenhöhe der Original-Moschee (Mauern)
TISCH_HOEHE = 0.85       # Höhe der Tischplatte über dem Boden (geschätzt)

# Einrichtung im Innenhof. Koordinaten relativ zur Hofmitte, ausgerichtet an den Mauern:
# u = entlang der Südmauer nach Osten, v = nach Norden (Richtung Hauptgebäude), in Metern.
# Tore liegen bei (u -43, v 0), (u 0, v -43) und (u 43, v 0); die Wege dorthin bleiben frei.
# (u, v, Höhe über Boden, Klasse, Drehung relativ zur Moschee in Grad)
EINRICHTUNG = [
    # Grillplatz (Südost): Feuerstelle mit Grillrost
    (8, -18, 0.0, "Fireplace", 0), (9.5, -18, 0.3, "CookingStand", 0),
    # Kisten mit Holz und Streichhölzern
    (13, -22, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0), (14.5, -22, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0),
    *[(12 + i * 0.6, -23.6, 0.3, "Firewood", 0) for i in range(6)],
    *[(12 + i * 0.6, -24.4, 0.3, "Matchbox", 0) for i in range(4)],
    # Kiste mit Essen und Fleisch
    (13, -15, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0),
    *[(11.5 + i * 0.6, -16.6, 0.3, n, 0) for i, n in enumerate(
        ["TacticalBaconCan"] * 3 + ["BakedBeansCan"] * 2 + ["PeachesCan"] * 2)],
    *[(11.5 + i * 0.6, -17.4, 0.3, n, 0) for i, n in enumerate(
        ["GoatSteakMeat"] * 3 + ["ChickenBreastMeat"] * 3)],
    # Wasser-Tankwagen (an der Südmauer) mit leeren Flaschen daneben (keine Getränke)
    (-22, -36, 0.0, "Land_Wreck_Truck01_Aban1_Cistern_DE", 90),
    *[(-13 + (i % 5) * 0.6, -33 - (i // 5) * 0.8, 0.3, "WaterBottle", 0) for i in range(10)],
    # Sanitätszelt (Südwest) mit zwei Tischen, Erste Hilfe auf den Tischen
    (-15, -18, 0.0, "Land_Medical_Tent_Big", 0),
    (-17, -18, 0.0, "Land_Roadblock_Table_DE", 0), (-13, -18, 0.0, "Land_Roadblock_Table_DE", 0),
    *[(-17.6 + i * 0.4, -18, TISCH_HOEHE, n, 0) for i, n in enumerate(
        ["BandageDressing"] * 3 + ["DisinfectantSpray"])],
    *[(-13.6 + i * 0.4, -18, TISCH_HOEHE, n, 0) for i, n in enumerate(
        ["BandageDressing"] * 2 + ["DisinfectantSpray", "FirstAidKit"])],
]

# Traderbereich: 6 Ladengeschäfte, Fenster zur Hofmitte. Breite aus den Ladenreihen in den
# Städten abgeleitet (18 m Abstand), Tiefe geschätzt.
LADEN_BREITE, LADEN_TIEFE = 18.0, 12.0
# Zeigt das Schaufenster im Spiel zur Mauer statt zur Hofmitte, hier 180 eintragen.
LADEN_FRONT_KORREKTUR = 0
# (Name, u, v, Blickrichtung des Fensters relativ zur Moschee in Grad: 0 = Norden, 90 = Osten,
#  Farbmarkierung als farbige Fässer vor dem Laden)
TRADER = [
    ("Trader 1", -35, -22, 90, ["Barrel_Blue"]),
    ("Trader 2", -35, 18, 90, ["Barrel_Green"]),
    ("Trader 3", -11, 24, 180, ["Barrel_Red"]),
    ("Trader 4", 11, 24, 180, ["Barrel_Yellow"]),
    ("Trader 5", 35, 18, -90, ["Barrel_Blue", "Barrel_Yellow"]),
    ("Trader 6", 35, -22, -90, ["Barrel_Red", "Barrel_Green"]),
]

text = Path(sys.argv[1]).read_text("utf-8")
teile = [(m.group(1), *map(float, m.group(2).split()), *map(float, m.group(3).split()))
         for m in re.finditer(r'<group name="(Land_Mosque_Big[^"]*)" pos="([^"]+)" rpy="([^"]+)"', text)]
assert len(teile) == 28, len(teile)
cx = sum(t[1] for t in teile) / len(teile)
cz = sum(t[3] for t in teile) / len(teile)
boden = BODEN + HOEHE_KORREKTUR


def objekt(name, x, y, z, gier=0.0, nicken=0.0, rollen=0.0):
    return {"name": name, "pos": [round(x, 3), round(y, 3), round(z, 3)],
            "ypr": [round(gier, 4), round(nicken, 4), round(rollen, 4)],
            "scale": 1.0, "enableCEPersistency": 0}


objekte = [objekt(n, x - cx + MITTE_X, y - ORIGINAL_BODEN + boden, z - cz + MITTE_Z, gier, nicken, rollen)
           for n, x, y, z, rollen, nicken, gier in teile]

# Ausrichtung der Moschee aus der Südmauer (Gierwinkel -169.5° => um 10.5° gedreht)
sued = next(t for t in teile if t[0] == "Land_Mosque_Big_Wall" and abs(t[6] + 169.52) < 0.01)
drehung = sued[6] + 180.0
rad = math.radians(drehung)
ost = (math.cos(rad), -math.sin(rad))      # u-Achse in Weltkoordinaten (x, z)
nord = (math.sin(rad), math.cos(rad))      # v-Achse
items = []
laeden = []
for name, u, v, blick, faesser in TRADER:
    EINRICHTUNG.append((u, v, 0.0, "Land_Store_Street1", blick + LADEN_FRONT_KORREKTUR))
    laeden.append({"name": name, "rolle": name, "x": round(MITTE_X + u * ost[0] + v * nord[0], 2),
                   "z": round(MITTE_Z + u * ost[1] + v * nord[1], 2),
                   "blick": round(drehung + blick, 2), "breite": LADEN_BREITE, "tiefe": LADEN_TIEFE})
    # Fässer vorne rechts neben dem Fenster
    b = math.radians(blick)
    vorne, rechts = (math.sin(b), math.cos(b)), (math.cos(b), -math.sin(b))
    for i, fass in enumerate(faesser):
        abstand_vorne = LADEN_TIEFE / 2 + 1.5
        seitlich = LADEN_BREITE / 2 - 1.5 - i * 1.2
        EINRICHTUNG.append((u + vorne[0] * abstand_vorne + rechts[0] * seitlich,
                            v + vorne[1] * abstand_vorne + rechts[1] * seitlich, 0.0, fass, 0))

for u, v, hoehe, name, gier in EINRICHTUNG:
    x = MITTE_X + u * ost[0] + v * nord[0]
    z = MITTE_Z + u * ost[1] + v * nord[1]
    objekte.append(objekt(name, x, boden + 0.5 + hoehe, z, drehung + gier))
    items.append(name)

ziel = Path(sys.argv[2]) / "custom" / "safezone.json"
ziel.parent.mkdir(parents=True, exist_ok=True)
ziel.write_text(json.dumps({"Objects": objekte}, indent=2), "utf-8")
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps({"laeden": laeden}, indent=2, ensure_ascii=False), "utf-8")
    print(f"{sys.argv[3]}: {len(laeden)} Läden für den Bot")
print(f"{ziel}: {len(teile)} Moschee-Teile + {len(items)} Items, Mitte x {MITTE_X} z {MITTE_Z}, "
      f"Boden {boden} (Ausdehnung "
      f"{max(t[1] for t in teile) - min(t[1] for t in teile):.0f} x "
      f"{max(t[3] for t in teile) - min(t[3] for t in teile):.0f} m)")
