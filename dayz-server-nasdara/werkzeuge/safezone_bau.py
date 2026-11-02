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

# Lage: auf der Straße südlich von Bam-e Sabz (Markierung bei x 8689 / z 8305). Die Straße kommt
# im Südwesten von der Hauptstraße (Knick bei x 8652 / z 8193) und läuft gerade nach Nordosten
# (Peilung 33.8°). Die Moschee steht auf dieser Achse, das Haupttor (Südtor gegenüber dem
# Hauptgebäude) zeigt zur ankommenden Straße. Ca. 6 m Abstand zu den Häusern, ca. 2 % Bäume.
MITTE_X, MITTE_Z = 8699.5, 8263.6
STRASSE_PEILUNG = 33.8   # Richtung der Straße nach Nordosten; das Haupttor blickt entgegengesetzt
# Gelände als schräge Ebene: Gefälle aus den Höhen der Objekte im Umkreis von 150 m geschätzt,
# Höhe an einem im Spiel gemessenen Punkt verankert (Karte im Spiel: 281 m im Hof der alten Lage).
MESS_X, MESS_Z, MESS_HOEHE = 8725.0, 8275.0, 281.0
# Weitere Messungen (Karte im Spiel) an eindeutigen Stellen der bisher aufgebauten Moschee
# (Mitte x 8725 / z 8265, alte Ausrichtung). Ab drei genauen Punkten wird daraus die Ebene berechnet.
MESSUNGEN = [
    ("innere Ecke rechts neben dem Hauptgebäude (Nordost)", 8772.0, 8299.0, 274.0),
]
GEFAELLE_OST, GEFAELLE_NORD = -0.066, 0.017
HOEHE_KORREKTUR = -0.8   # Gebäude lieber etwas einsinken lassen als schweben (Schätzung ±2 m)
ITEM_ZUSCHLAG = 0.5      # lose Items etwas höher, da die Karte auf ganze Meter rundet


def boden_bei(x: float, z: float) -> float:
    """Geschätzte Bodenhöhe an einer Stelle (Ebene durch den gemessenen Punkt)."""
    return MESS_HOEHE + GEFAELLE_OST * (x - MESS_X) + GEFAELLE_NORD * (z - MESS_Z)

ORIGINAL_BODEN = 179.249  # Bodenhöhe der Original-Moschee (Mauern)
TISCH_HOEHE = 0.85       # Höhe der Tischplatte über dem Boden (geschätzt)
KISTEN_HOEHE = 0.8       # Höhe der Holzkisten (Land_Misc_WoodenCrate_Spawn_DE), geschätzt

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
    # Zwei Kisten mit Essen obendrauf: links Dosen, rechts Fleisch
    (11.5, -15, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0), (13.5, -15, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0),
    *[(11.5 + (i % 4 - 1.5) * 0.2, -15 + (i // 4 - 0.5) * 0.25, KISTEN_HOEHE, n, 0) for i, n in enumerate(
        ["TacticalBaconCan"] * 3 + ["BakedBeansCan"] * 2 + ["PeachesCan"] * 2)],
    *[(13.5 + (i % 3 - 1) * 0.25, -15 + (i // 3 - 0.5) * 0.25, KISTEN_HOEHE, n, 0) for i, n in enumerate(
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
# Markierung über dem Fenster: statische Objekte (nicht aufhebbar), an der Front in dieser Höhe.
MARKER_HOEHE = 3.0
# (Name, u, v, Blickrichtung des Fensters relativ zur Moschee in Grad: 0 = Norden, 90 = Osten,
#  Markierung über dem Fenster)
TRADER = [
    ("Trader 1", -35, -22, 90, ["StaticObj_Bucket_Red_DE"]),                 # roter Eimer
    ("Trader 2", -35, 18, 90, ["StaticObj_Stretcher_Green_DE"]),             # grüne Trage
    ("Trader 3", -11, 24, 180, ["StaticObj_RoadCone_DE"]),                   # orange Leitkegel
    ("Trader 4", 11, 24, 180, ["StaticObj_Sign_Roadblock_Stop_DE"]),         # rot-weißes Stoppschild
    ("Trader 5", 35, 18, -90, ["StaticObj_Sign_Roadblock_Arrow_DE"]),        # Pfeilschild
    ("Trader 6", 35, -22, -90, ["StaticObj_Furniture_PlasticBucket_DE"]),    # Plastikeimer
]

text = Path(sys.argv[1]).read_text("utf-8")
teile = [(m.group(1), *map(float, m.group(2).split()), *map(float, m.group(3).split()))
         for m in re.finditer(r'<group name="(Land_Mosque_Big[^"]*)" pos="([^"]+)" rpy="([^"]+)"', text)]
assert len(teile) == 28, len(teile)
cx = sum(t[1] for t in teile) / len(teile)
cz = sum(t[3] for t in teile) / len(teile)


def objekt(name, x, y, z, gier=0.0, nicken=0.0, rollen=0.0):
    return {"name": name, "pos": [round(x, 3), round(y, 3), round(z, 3)],
            "ypr": [round(gier, 4), round(nicken, 4), round(rollen, 4)],
            "scale": 1.0, "enableCEPersistency": 0}


# Ausrichtung der Original-Moschee aus der Südmauer (Gierwinkel -169.5° => um 10.5° gedreht).
# Die Kopie wird zusätzlich so gedreht, dass ihre Nordachse der Straße folgt (Haupttor zur Straße).
sued = next(t for t in teile if t[0] == "Land_Mosque_Big_Wall" and abs(t[6] + 169.52) < 0.01)
zusatz = STRASSE_PEILUNG - (sued[6] + 180.0)
zr = math.radians(zusatz)

objekte = []
for n, x, y, z, rollen, nicken, gier in teile:
    dx, dz = x - cx, z - cz
    nx = MITTE_X + dx * math.cos(zr) + dz * math.sin(zr)    # im Uhrzeigersinn um zusatz drehen
    nz = MITTE_Z - dx * math.sin(zr) + dz * math.cos(zr)
    objekte.append(objekt(n, nx, y - ORIGINAL_BODEN + boden_bei(nx, nz) + HOEHE_KORREKTUR, nz,
                          gier + zusatz, nicken, rollen))

drehung = STRASSE_PEILUNG
rad = math.radians(drehung)
ost = (math.cos(rad), -math.sin(rad))      # u-Achse in Weltkoordinaten (x, z)
nord = (math.sin(rad), math.cos(rad))      # v-Achse
items = []
laeden = []
for name, u, v, blick, marker in TRADER:
    EINRICHTUNG.append((u, v, 0.0, "Land_Store_Street1", blick + LADEN_FRONT_KORREKTUR))
    laeden.append({"name": name, "rolle": name, "x": round(MITTE_X + u * ost[0] + v * nord[0], 2),
                   "z": round(MITTE_Z + u * ost[1] + v * nord[1], 2),
                   "blick": round(drehung + blick, 2), "breite": LADEN_BREITE, "tiefe": LADEN_TIEFE})
    # Markierung mittig über dem Fenster, knapp vor der Fassade, zur Hofmitte gedreht
    b = math.radians(blick)
    vorne = (math.sin(b), math.cos(b))
    for objekt_name in marker:
        abstand_vorne = LADEN_TIEFE / 2 + 0.3
        EINRICHTUNG.append((u + vorne[0] * abstand_vorne, v + vorne[1] * abstand_vorne,
                            MARKER_HOEHE, objekt_name, blick))

for u, v, hoehe, name, gier in EINRICHTUNG:
    x = MITTE_X + u * ost[0] + v * nord[0]
    z = MITTE_Z + u * ost[1] + v * nord[1]
    # Gebäude (Land_) leicht einsinken lassen, Tische und Kisten nicht (sonst stimmt die Höhe der
    # Ablagefläche nicht); lose Items am Boden etwas höher, auf Tischen/Kisten knapp über der Fläche
    if name in ("Land_Roadblock_Table_DE", "Land_Misc_WoodenCrate_Spawn_DE"):
        korrektur = 0.0
    elif name.startswith("Land_"):
        korrektur = HOEHE_KORREKTUR
    elif hoehe < 0.5:
        korrektur = ITEM_ZUSCHLAG
    elif hoehe < 2:
        korrektur = 0.1
    else:
        korrektur = 0.0
    objekte.append(objekt(name, x, boden_bei(x, z) + hoehe + korrektur, z, drehung + gier))
    items.append(name)

ziel = Path(sys.argv[2]) / "custom" / "safezone.json"
ziel.parent.mkdir(parents=True, exist_ok=True)
ziel.write_text(json.dumps({"Objects": objekte}, indent=2), "utf-8")
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps({"laeden": laeden}, indent=2, ensure_ascii=False), "utf-8")
    print(f"{sys.argv[3]}: {len(laeden)} Läden für den Bot")
print(f"{ziel}: {len(teile)} Moschee-Teile + {len(items)} Items, Mitte x {MITTE_X} z {MITTE_Z}, "
      f"Boden {boden_bei(MITTE_X, MITTE_Z):.1f} in der Mitte (Ausdehnung "
      f"{max(t[1] for t in teile) - min(t[1] for t in teile):.0f} x "
      f"{max(t[3] for t in teile) - min(t[3] for t in teile):.0f} m)")
