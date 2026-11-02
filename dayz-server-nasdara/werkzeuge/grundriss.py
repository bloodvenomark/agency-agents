"""Zeichnet den Grundriss der Safezone-Moschee mit Einrichtung und Trader-Läden.

Aufruf: python3 -I grundriss.py <custom/safezone.json> <trader_laeden.json> <ausgabe.png>
"""
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

o = json.load(open(sys.argv[1]))["Objects"]
laeden = json.load(open(sys.argv[2]))["laeden"]
fig, ax = plt.subplots(figsize=(10, 10))
for x in o[:28]:
    t = x["name"].replace("Land_Mosque_Big_", "")
    c = {"Gate": "#ff8f00", "Main": "#3949ab", "Side": "#7986cb"}.get(t, "#5d4037" if "Minaret" in t else "#8d6e63")
    ax.scatter(x["pos"][0], x["pos"][2], s=300 if t == "Main" else 70, c=c, marker="s")
    if t in ("Main", "Gate"):
        ax.annotate({"Main": "Hauptgebäude", "Gate": "Tor"}[t], (x["pos"][0], x["pos"][2]),
                    fontsize=8, xytext=(5, 5), textcoords="offset points")
farbe = {"Trader 1": "#e53935", "Trader 2": "#43a047", "Trader 3": "#fb8c00",
         "Trader 4": "#e53935", "Trader 5": "#9e9e9e", "Trader 6": "#1e88e5"}
for l in laeden:
    b = math.radians(l["blick"])
    v, r = (math.sin(b), math.cos(b)), (math.cos(b), -math.sin(b))
    ecken = [(l["x"] + sv * l["tiefe"] / 2 * v[0] + sr * l["breite"] / 2 * r[0],
              l["z"] + sv * l["tiefe"] / 2 * v[1] + sr * l["breite"] / 2 * r[1])
             for sv, sr in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
    ax.add_patch(Polygon(ecken, closed=True, fc=farbe.get(l["name"], "#9e9e9e"), alpha=.25, ec="k"))
    fx, fz = l["x"] + v[0] * l["tiefe"] / 2, l["z"] + v[1] * l["tiefe"] / 2
    ax.annotate("", xy=(fx + v[0] * 4, fz + v[1] * 4), xytext=(fx, fz), arrowprops=dict(arrowstyle="->"))
    ax.text(l["x"], l["z"], l["name"], ha="center", va="center", fontsize=9, weight="bold")
gruppen = [
    ("Grill + Kisten + Essen", ("Fireplace", "CookingStand", "Land_Roadblock_WoodenCrate_DE", "Firewood",
                                "Matchbox", "TacticalBaconCan", "BakedBeansCan", "PeachesCan",
                                "GoatSteakMeat", "ChickenBreastMeat"), "#6d4c41", "o"),
    ("Wasser-Tankwagen + Flaschen", ("Land_Wreck_Truck01_Aban1_Cistern_DE", "WaterBottle"), "#0277bd", "P"),
    ("Sanitätszelt + Tische", ("Land_Medical_Tent_Big", "Land_Roadblock_Table_DE", "BandageDressing",
                               "DisinfectantSpray", "FirstAidKit"), "#c62828", "^"),
]
for label, klassen, c, m in gruppen:
    pts = [(x["pos"][0], x["pos"][2]) for x in o[28:] if x["name"] in klassen]
    ax.scatter(*zip(*pts), c=c, marker=m, s=40, label=label)
marker = {"StaticObj_Bucket_Red_DE": "roter Eimer", "StaticObj_Stretcher_Green_DE": "grüne Trage",
          "StaticObj_RoadCone_DE": "Leitkegel", "StaticObj_Sign_Roadblock_Stop_DE": "Stoppschild",
          "StaticObj_Sign_Roadblock_Arrow_DE": "Pfeilschild", "StaticObj_Furniture_PlasticBucket_DE": "Plastikeimer"}
for x in o[28:]:
    if x["name"] in marker:
        ax.scatter(x["pos"][0], x["pos"][2], c="k", marker="*", s=90)
        ax.annotate(marker[x["name"]], (x["pos"][0], x["pos"][2]), fontsize=7, xytext=(4, -10),
                    textcoords="offset points")
ax.scatter([], [], c="k", marker="*", s=90, label="Markierung über dem Fenster")
ax.set_aspect("equal")
ax.grid(alpha=.3)
ax.legend(loc="lower right", fontsize=8)
ax.set_title("Safezone-Moschee – Innenhof mit 6 Trader-Läden (Pfeil = Fenster/Front)")
fig.savefig(sys.argv[3], dpi=100, bbox_inches="tight")
