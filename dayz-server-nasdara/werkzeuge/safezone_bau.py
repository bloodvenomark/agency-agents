"""Baut die Safezone: Kopie der großen Nasdara-Moschee an einem neuen Ort, mit eingerichtetem
Innenhof (Object Spawner, kommt nach jedem Restart neu):
Grillplatz, Kisten mit Holz/Streichhölzern und mit Essen/Fleisch, Wasser-Tankwagen mit Flaschen,
Sanitätszelt mit Erster Hilfe auf Tischen.

Aufruf: python3 -I safezone_bau.py <mapgrouppos.xml> <ziel-ordner>
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
# (u, v, Höhe über Boden, Klasse, Drehung relativ zur Moschee in Grad)
EINRICHTUNG = [
    # Grillplatz: Feuerstelle mit Grillrost
    (12, -4, 0.0, "Fireplace", 0), (13.5, -4, 0.3, "CookingStand", 0),
    # Kisten mit Holz und Streichhölzern
    (17, -8, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0), (18.5, -8, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0),
    *[(16 + i * 0.6, -9.6, 0.3, "Firewood", 0) for i in range(6)],
    *[(16 + i * 0.6, -10.4, 0.3, "Matchbox", 0) for i in range(4)],
    # Kiste mit Essen und Fleisch
    (17, -1, 0.0, "Land_Misc_WoodenCrate_Spawn_DE", 0),
    *[(15.5 + i * 0.6, -2.6, 0.3, n, 0) for i, n in enumerate(
        ["TacticalBaconCan"] * 3 + ["BakedBeansCan"] * 2 + ["PeachesCan"] * 2)],
    *[(15.5 + i * 0.6, -3.4, 0.3, n, 0) for i, n in enumerate(
        ["GoatSteakMeat"] * 3 + ["ChickenBreastMeat"] * 3)],
    # Wasser-Tankwagen mit leeren Flaschen daneben (keine Getränke)
    (-22, -14, 0.0, "Land_Wreck_Truck01_Aban1_Cistern_DE", 90),
    *[(-16 + (i % 5) * 0.6, -20 - (i // 5) * 0.8, 0.3, "WaterBottle", 0) for i in range(10)],
    # Sanitätszelt mit zwei Tischen, Erste Hilfe auf den Tischen
    (-20, 12, 0.0, "Land_Medical_Tent_Big", 0),
    (-22, 12, 0.0, "Land_Roadblock_Table_DE", 0), (-18, 12, 0.0, "Land_Roadblock_Table_DE", 0),
    *[(-22.6 + i * 0.4, 12, TISCH_HOEHE, n, 0) for i, n in enumerate(
        ["BandageDressing"] * 3 + ["DisinfectantSpray"])],
    *[(-18.6 + i * 0.4, 12, TISCH_HOEHE, n, 0) for i, n in enumerate(
        ["BandageDressing"] * 2 + ["DisinfectantSpray", "FirstAidKit"])],
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
for u, v, hoehe, name, gier in EINRICHTUNG:
    x = MITTE_X + u * ost[0] + v * nord[0]
    z = MITTE_Z + u * ost[1] + v * nord[1]
    objekte.append(objekt(name, x, boden + 0.5 + hoehe, z, drehung + gier))
    items.append(name)

ziel = Path(sys.argv[2]) / "custom" / "safezone.json"
ziel.parent.mkdir(parents=True, exist_ok=True)
ziel.write_text(json.dumps({"Objects": objekte}, indent=2), "utf-8")
print(f"{ziel}: {len(teile)} Moschee-Teile + {len(items)} Items, Mitte x {MITTE_X} z {MITTE_Z}, "
      f"Boden {boden} (Ausdehnung "
      f"{max(t[1] for t in teile) - min(t[1] for t in teile):.0f} x "
      f"{max(t[3] for t in teile) - min(t[3] for t in teile):.0f} m)")
