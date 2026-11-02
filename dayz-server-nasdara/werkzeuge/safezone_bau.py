"""Baut die Safezone: Kopie der großen Nasdara-Moschee an einem neuen Ort, mit Essen,
Trinken und Erster Hilfe im Innenhof (Object Spawner, kommt nach jedem Restart neu).

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
VORRAT = {
    "TacticalBaconCan": 4, "BakedBeansCan": 3, "PeachesCan": 3,           # 10x Essen
    "WaterBottle": 10,                                                     # 10x Trinken
    "BandageDressing": 5, "DisinfectantSpray": 2, "FirstAidKit": 1,       # Erste Hilfe
}

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

# Vorrat im Innenhof: zwei Reihen in der Hofmitte, leicht über dem Boden
items = [n for n, anzahl in VORRAT.items() for _ in range(anzahl)]
for i, name in enumerate(items):
    reihe, spalte = divmod(i, 15)
    objekte.append(objekt(name, MITTE_X - 7 + spalte, boden + 0.8, MITTE_Z - 1 + reihe * 2))

ziel = Path(sys.argv[2]) / "custom" / "safezone.json"
ziel.parent.mkdir(parents=True, exist_ok=True)
ziel.write_text(json.dumps({"Objects": objekte}, indent=2), "utf-8")
print(f"{ziel}: {len(teile)} Moschee-Teile + {len(items)} Items, Mitte x {MITTE_X} z {MITTE_Z}, "
      f"Boden {boden} (Ausdehnung "
      f"{max(t[1] for t in teile) - min(t[1] for t in teile):.0f} x "
      f"{max(t[3] for t in teile) - min(t[3] for t in teile):.0f} m)")
