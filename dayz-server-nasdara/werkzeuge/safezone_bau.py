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
# Gelände aus Messungen im Spiel (Karte im Spiel, "Höhe") an eindeutigen Stellen der vorher
# aufgebauten Moschee (Mitte x 8725 / z 8265, alte Ausrichtung). Das Gelände ist verdreht (vorne
# 14 m Gefälle, hinten 5 m), daher keine Ebene, sondern eine bilineare Fläche durch die Messpunkte:
# h = a + b*dx + c*dz + d*dx*dz. Weitere Messungen ergänzen -> Ausgleich nach kleinsten Quadraten.
MESSUNGEN = [
    ("innere Ecke links neben dem Hauptgebäude (Nordwest)", 8693.0, 8314.0, 279.0),
    ("innere Ecke rechts neben dem Hauptgebäude (Nordost)", 8772.0, 8299.0, 274.0),
    ("Mauer vorne links (Südwest)", 8678.0, 8233.0, 286.0),
    ("Mauer vorne rechts (Südost)", 8757.0, 8218.0, 272.0),
    # Messung in der neuen, zur Straße gedrehten Lage
    ("Sanitätszelt (neue Lage)", 8677.0, 8257.0, 284.0),
    ("Wasser-Tankwagen (neue Lage, schwebte ca. 2-3 m)", 8661.0, 8246.0, 285.0),
    ("Trader 6 vorne rechts (neue Lage)", 8716.0, 8226.0, 280.0),
    ("Trader 4 rechts vor dem Hauptgebäude (neue Lage)", 8722.0, 8277.0, 280.0),
    ("Trader 3 vor dem Hauptgebäude (neue Lage)", 8703.0, 8286.0, 282.0),
]
MESS_X, MESS_Z = 8725.0, 8265.0


KORREKTUR_RADIUS = 30.0   # Reichweite der örtlichen Korrektur um jeden Messpunkt (m)


def _loese(a, b):
    """Lineares Gleichungssystem a*x = b (Gauß-Elimination)."""
    n = len(b)
    a = [zeile[:] for zeile in a]
    b = b[:]
    for i in range(n):
        for k in range(i + 1, n):
            f = a[k][i] / a[i][i]
            a[k] = [a[k][j] - f * a[i][j] for j in range(n)]
            b[k] -= f * b[i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (b[i] - sum(a[i][j] * x[j] for j in range(i + 1, n))) / a[i][i]
    return x


def _flaeche(punkte):
    """Koeffizienten a, b, c, d der bilinearen Fläche (kleinste Quadrate)."""
    zeilen = [(1.0, x - MESS_X, z - MESS_Z, (x - MESS_X) * (z - MESS_Z), h) for _, x, z, h in punkte]
    a = [[sum(r[i] * r[j] for r in zeilen) for j in range(4)] for i in range(4)]
    return _loese(a, [sum(r[i] * r[4] for r in zeilen) for i in range(4)])


def _grundflaeche(x: float, z: float) -> float:
    a, b, c, d = FLAECHE
    dx, dz = x - MESS_X, z - MESS_Z
    return a + b * dx + c * dz + d * dx * dz


def _kern(x1, z1, x2, z2):
    return math.exp(-((x1 - x2) ** 2 + (z1 - z2) ** 2) / KORREKTUR_RADIUS ** 2)


FLAECHE = _flaeche(MESSUNGEN)
# Örtliche Korrektur (radiale Basisfunktionen), damit jeder Messpunkt genau getroffen wird
_RESTE = [h - _grundflaeche(x, z) for _, x, z, h in MESSUNGEN]
_GEWICHTE = _loese([[_kern(x1, z1, x2, z2) for _, x2, z2, _ in MESSUNGEN] for _, x1, z1, _ in MESSUNGEN],
                   _RESTE)
HOEHE_KORREKTUR = -0.8   # Gebäude lieber etwas einsinken lassen als schweben (Schätzung ±2 m)
ITEM_ZUSCHLAG = 0.5      # lose Items etwas höher, da die Karte auf ganze Meter rundet


def boden_bei(x: float, z: float) -> float:
    """Bodenhöhe an einer Stelle: Fläche durch alle Messungen plus örtliche Korrektur."""
    return _grundflaeche(x, z) + sum(w * _kern(x, z, mx, mz)
                                     for w, (_, mx, mz, _) in zip(_GEWICHTE, MESSUNGEN))

ORIGINAL_BODEN = 179.249  # Bodenhöhe der Original-Moschee (Mauern)
TISCH_HOEHE = 0.7        # Höhe der Tischplatte über dem Boden (0.85 war zu hoch, Spray schwebte)
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
        korrektur = 0.03
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
