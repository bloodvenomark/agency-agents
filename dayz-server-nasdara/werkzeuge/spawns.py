"""Berechnet 50 Spieler-Spawnpunkte außerhalb von Ortschaften.

Aufruf: python3 -I spawns.py <mapgrouppos.xml> <cfgEffectArea.json> <cfgplayerspawnpoints.xml>
        <ausgabe.json> [<vorschau.png>]
"""
import json
import math
import re
import sys

ANZAHL = 50
ABSTAND_ORT = 400        # m zu Ortschaften
ABSTAND_MILITAER = 700   # m zu Militär/Bunkern
MAX_ABSTAND_ORT = 900   # im Umland einer Ortschaft bleiben, nicht im Niemandsland am Kartenrand
ABSTAND_GIFTGAS = 500
UMGEBUNG_RADIUS, UMGEBUNG_MIN = 1500, 30   # belebte Gegend: >= 30 Ortschafts-Gebäude im Umkreis
RASTER = 100
ORT_RADIUS, ORT_MIN_GEBAEUDE = 150, 5   # ab 5 Gebäuden im Umkreis von 150 m = Ortschaft
MILITAER = ("Land_Mil", "Land_Bunker", "Land_RocketBase", "Land_HBarrierTower",
            "Land_Guardhouse", "Land_Airfield", "Land_Border")

gebaeude, militaer = [], []
for m in re.finditer(r'<group name="([^"]+)" pos="([-\d.]+) [-\d.]+ ([-\d.]+)"', open(sys.argv[1]).read()):
    name, x, z = m.group(1), float(m.group(2)), float(m.group(3))
    if name.lower().startswith("land_wreck"):
        continue
    (militaer if name.startswith(MILITAER) else gebaeude).append((x, z))


class Gitter:
    """Räumlicher Index für schnelle Abstandsabfragen."""
    def __init__(self, punkte, zelle=250):
        self.zelle, self.felder = zelle, {}
        for p in punkte:
            self.felder.setdefault((int(p[0] // zelle), int(p[1] // zelle)), []).append(p)

    def nachbarn(self, x, z, r):
        k = int(math.ceil(r / self.zelle))
        cx, cz = int(x // self.zelle), int(z // self.zelle)
        for i in range(cx - k, cx + k + 1):
            for j in range(cz - k, cz + k + 1):
                for p in self.felder.get((i, j), ()):
                    if (p[0] - x) ** 2 + (p[1] - z) ** 2 <= r * r:
                        yield p


alle = Gitter(gebaeude + militaer)
orte = [p for p in gebaeude
        if sum(1 for _ in Gitter.nachbarn(alle, p[0], p[1], ORT_RADIUS)) >= ORT_MIN_GEBAEUDE]
orte_idx, mil_idx = Gitter(orte), Gitter(militaer)
giftgas = [(a["Data"]["Pos"][0], a["Data"]["Pos"][2], a["Data"]["Radius"])
           for a in json.load(open(sys.argv[2]))["Areas"] if "Contaminated" in a["Type"]]
alt = [(float(x), float(z)) for x, z in
       re.findall(r'<pos x="([\d.]+)" z="([\d.]+)"', open(sys.argv[3]).read().split("</fresh>")[0])]

xs = [p[0] for p in gebaeude]
zs = [p[1] for p in gebaeude]
kandidaten = []
for x in range(int(min(xs)), int(max(xs)) + 1, RASTER):
    for z in range(int(min(zs)), int(max(zs)) + 1, RASTER):
        if next(orte_idx.nachbarn(x, z, ABSTAND_ORT), None):
            continue
        if next(mil_idx.nachbarn(x, z, ABSTAND_MILITAER), None):
            continue
        if not next(orte_idx.nachbarn(x, z, MAX_ABSTAND_ORT), None):
            continue
        if any(math.dist((x, z), g[:2]) < g[2] + ABSTAND_GIFTGAS for g in giftgas):
            continue
        if sum(1 for _ in orte_idx.nachbarn(x, z, UMGEBUNG_RADIUS)) < UMGEBUNG_MIN:
            continue
        kandidaten.append((x, z))

# Gleichmäßig verteilen: immer den Kandidaten nehmen, der am weitesten von den bisherigen entfernt ist
mitte = (sum(xs) / len(xs), sum(zs) / len(zs))
gewaehlt = [min(kandidaten, key=lambda p: (p[0] - mitte[0]) ** 2 + (p[1] - mitte[1]) ** 2)]
abst = [(p[0] - gewaehlt[0][0]) ** 2 + (p[1] - gewaehlt[0][1]) ** 2 for p in kandidaten]
while len(gewaehlt) < ANZAHL:
    i = max(range(len(kandidaten)), key=abst.__getitem__)
    gewaehlt.append(kandidaten[i])
    for j, p in enumerate(kandidaten):
        abst[j] = min(abst[j], (p[0] - kandidaten[i][0]) ** 2 + (p[1] - kandidaten[i][1]) ** 2)

json.dump({"punkte": gewaehlt}, open(sys.argv[4], "w"))
print(f"Gebäude {len(gebaeude)}, Ortschafts-Gebäude {len(orte)}, Militär {len(militaer)}, "
      f"Kandidaten {len(kandidaten)}, gewählt {len(gewaehlt)}, "
      f"min. Abstand zwischen Spawns {min(math.dist(a, b) for i, a in enumerate(gewaehlt) for b in gewaehlt[i + 1:]):.0f} m")

if len(sys.argv) > 5:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(*zip(*gebaeude), s=0.3, c="#9e9e9e", label="Gebäude")
    ax.scatter(*zip(*orte), s=0.6, c="#455a64", label="Ortschaften")
    ax.scatter(*zip(*militaer), s=1.5, c="#c62828", label="Militär")
    ax.scatter(*zip(*alt), s=40, c="#1565c0", marker="x", label="Spawn (bisher)")
    for g in giftgas:
        ax.add_patch(plt.Circle(g[:2], g[2] + ABSTAND_GIFTGAS, color="#8e24aa", alpha=0.25))
    ax.scatter(*zip(*gewaehlt), s=60, c="#2e7d32", marker="*", label="Spawn (neu)")
    for n, (x, z) in enumerate(gewaehlt, 1):
        ax.annotate(str(n), (x, z), fontsize=7, xytext=(4, 4), textcoords="offset points")
    ax.set_aspect("equal")
    ax.set_xlim(0, 16384)
    ax.set_ylim(0, 16384)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")
    ax.set_title("Nasdara – neue Spieler-Spawns (x / z in Metern)")
    fig.savefig(sys.argv[5], dpi=110, bbox_inches="tight")
