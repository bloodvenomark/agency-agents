"""Relog-Teleporter: in jedem Ort ein Dixi-Klo. Wer sich darin ausloggt, landet beim nächsten
Einloggen in der Safezone-Moschee.

Technik: "playerRestrictedAreaFiles" in cfggameplay.json (eigentlich für den Bunker auf Sakhal
gedacht, seit 1.26). Ein Kasten (PRABox) um jedes Klo; wer beim Einloggen in einem Kasten steht,
wird an eine der "safePositions3D" gesetzt.

Aufruf: python3 -I teleporter_bau.py <mapgrouppos.xml> <ziel-ordner> [<vorschau.png>]
Ergebnis: <ziel-ordner>/custom/teleport_dixi.json (Klos, Object Spawner)
          <ziel-ordner>/custom/teleport_safezone.json (Teleport-Zonen)
          <ziel-ordner>/TELEPORTER.md (Liste der Orte mit Koordinaten)
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

KLO = "Land_Misc_Toilet_Mobile"
MIN_GEBAEUDE = 25          # ab so vielen Gebäuden im Umkreis von DICHTE_RADIUS gilt eine Stelle als Ort
DICHTE_RADIUS = 200
ABSTAND = 700              # Mindestabstand zwischen zwei Teleportern (große Städte bekommen mehrere)
FREIRAUM = 8.0             # m Abstand des Klos zum nächsten Gebäude
KASTEN = [4.0, 14.0, 4.0]  # Teleport-Zone: Breite, Höhe, Tiefe in m (großzügig wegen Höhenschätzung)
SAFEZONE = (8699.5, 8263.6)
SAFEZONE_ABSTAND = 600     # Orte so nah an der Safezone brauchen keinen Teleporter
# Die Höhe aus den Gebäudedaten lag beim Vergleich mit den Messungen an der Moschee im Schnitt
# 1-3 m zu tief (bis 4 m). Das Klo daher etwas höher setzen: lieber leicht schweben als unsichtbar
# im Boden stecken. Die Teleport-Zone reicht 5 m unter bis 9 m über die Schätzung.
KLO_ZUSCHLAG = 1.5
# Im Spiel gemessene Bodenhöhe einzelner Teleporter (Nr. aus TELEPORTER.md -> Höhe in m)
KORREKTUREN: dict[int, float] = {}
# Ankunft in der Safezone: Hofmitte der Moschee, Höhe aus den Messungen (safezone_bau.py)
ANKUNFT = [
    [8696.7, 283.6, 8259.4], [8690.9, 283.8, 8259.7], [8699.2, 283.5, 8254.2],
    [8692.8, 284.0, 8253.6], [8697.3, 283.2, 8267.5], [8703.9, 283.2, 8263.0],
]

objekte = [(m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4)))
           for m in re.finditer(r'<group name="([^"]+)" pos="([-\d.]+) ([-\d.]+) ([-\d.]+)"',
                                Path(sys.argv[1]).read_text("utf-8"))]
gebaeude = [o for o in objekte if "reck" not in o[0]]

objekt_gitter = defaultdict(list)
for o in objekte:
    objekt_gitter[(int(o[1] // 20), int(o[3] // 20))].append(o)
gebaeude_gitter = defaultdict(list)
for g in gebaeude:
    gebaeude_gitter[(int(g[1] // 100), int(g[3] // 100))].append(g)


def frei(x, z):
    """Kein Objekt (auch kein Wrack) näher als FREIRAUM."""
    gx, gz = int(x // 20), int(z // 20)
    return all(math.dist((x, z), (o[1], o[3])) >= FREIRAUM
               for dx in (-1, 0, 1) for dz in (-1, 0, 1) for o in objekt_gitter.get((gx + dx, gz + dz), []))


def dichte(x, z, r=DICHTE_RADIUS):
    gx, gz = int(x // 100), int(z // 100)
    k = int(r // 100) + 1
    return sum(1 for dx in range(-k, k + 1) for dz in range(-k, k + 1)
               for g in gebaeude_gitter.get((gx + dx, gz + dz), []) if math.dist((x, z), (g[1], g[3])) < r)


# Orte finden: Stellen mit dichter Bebauung, die dichtesten zuerst, mindestens ABSTAND auseinander.
# So bekommt jeder Ort einen Teleporter und große Städte mehrere.
xs = [g[1] for g in gebaeude]
zs = [g[3] for g in gebaeude]
kandidaten = []
for x in range(int(min(xs)), int(max(xs)), 50):
    for z in range(int(min(zs)), int(max(zs)), 50):
        d = dichte(x, z)
        if d >= MIN_GEBAEUDE and math.dist((x, z), SAFEZONE) >= SAFEZONE_ABSTAND:
            kandidaten.append((d, x, z))
kandidaten.sort(reverse=True)

orte = []
for d, cx, cz in kandidaten:
    if any(math.dist((cx, cz), (o["x"], o["z"])) < ABSTAND for o in orte):
        continue
    # freie Stelle möglichst nah an der dichten Stelle suchen; ohne freie Stelle zählt sie nicht
    beste = next(((cx + r * math.cos(math.radians(w)), cz + r * math.sin(math.radians(w)))
                  for r in range(0, 121, 4) for w in range(0, 360, 15 if r else 360)
                  if frei(cx + r * math.cos(math.radians(w)), cz + r * math.sin(math.radians(w)))), None)
    if not beste:
        continue
    x, z = beste
    # Bodenhöhe: Median der Objekthöhen im Umkreis von 40 m (Schätzung, siehe KLO_ZUSCHLAG)
    hoehen = sorted(o[2] for o in objekte if math.dist((x, z), (o[1], o[3])) < 40)
    if not hoehen:
        continue
    orte.append({"x": round(x, 1), "z": round(z, 1), "boden": round(hoehen[len(hoehen) // 2], 1),
                 "gebaeude": d})

orte.sort(key=lambda o: (-o["z"], o["x"]))   # von Norden nach Süden
for nr, hoehe in KORREKTUREN.items():
    orte[nr - 1]["boden"] = hoehe
    orte[nr - 1]["gemessen"] = True
ziel = Path(sys.argv[2])
(ziel / "custom").mkdir(parents=True, exist_ok=True)
klos = {"Objects": [{"name": KLO, "pos": [o["x"], round(o["boden"] + (0 if o.get("gemessen") else KLO_ZUSCHLAG), 2), o["z"]],
                     "ypr": [0.0, 0.0, 0.0], "scale": 1.0, "enableCEPersistency": 0} for o in orte]}
(ziel / "custom" / "teleport_dixi.json").write_text(json.dumps(klos, indent=2), "utf-8")
zonen = {
    "areaName": "RelogTeleporterSafezone",
    "PRABoxes": [[KASTEN, [0.0, 0.0, 0.0], [o["x"], round(o["boden"] + 2.0, 2), o["z"]]]
                 for o in orte],
    "safePositions3D": ANKUNFT,
}
(ziel / "custom" / "teleport_safezone.json").write_text(json.dumps(zonen, indent=2), "utf-8")

zeilen = ["# Relog-Teleporter (Dixi-Klos)", "",
          "Wer sich im Dixi-Klo ausloggt, landet beim nächsten Einloggen in der Safezone-Moschee.", "",
          "Schwebt ein Klo oder steckt es im Boden: Kartenwert (Höhe) am Klo messen und mit der Nr.",
          "in `werkzeuge/teleporter_bau.py` unter KORREKTUREN eintragen (bzw. mir schicken).", "",
          "| Nr. | x | z | Bodenhöhe | Gebäude im Umkreis 200 m |", "|---|---|---|---|---|"]
zeilen += [f"| {i} | {o['x']:.0f} | {o['z']:.0f} | {o['boden']:.1f} m "
           f"({'gemessen' if o.get('gemessen') else 'geschätzt'}) | {o['gebaeude']} |"
           for i, o in enumerate(orte, 1)]
(ziel / "TELEPORTER.md").write_text("\n".join(zeilen) + "\n", "utf-8")
print(f"{len(orte)} Teleporter (mind. {MIN_GEBAEUDE} Gebäude im Umkreis von {DICHTE_RADIUS} m, {ABSTAND} m Abstand)")

if len(sys.argv) > 3:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter([g[1] for g in gebaeude], [g[3] for g in gebaeude], s=0.3, c="#9e9e9e")
    ax.scatter([o["x"] for o in orte], [o["z"] for o in orte], s=50, c="#1565c0", marker="s",
               label="Dixi-Klo (Relog-Teleporter)")
    for i, o in enumerate(orte, 1):
        ax.annotate(str(i), (o["x"], o["z"]), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.scatter([SAFEZONE[0]], [SAFEZONE[1]], s=200, c="#c62828", marker="*", label="Safezone (Ziel)")
    ax.set_aspect("equal")
    ax.set_xlim(0, 16384)
    ax.set_ylim(0, 16384)
    ax.grid(alpha=.3)
    ax.legend(loc="upper right")
    ax.set_title("Nasdara – Relog-Teleporter zur Safezone (x / z in Metern)")
    fig.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
