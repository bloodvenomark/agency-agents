"""Erzeugt custom/startgear.json (Spawn-Gear-Preset für cfggameplay.json).

Aufruf: python3 -I startgear.py <ziel-ordner>
Eine der Ausrüstungen in 'discreteUnsortedItemSets' wird pro Spawn zufällig gewählt.
Es gibt jede Kombination aus Pistole und Messer, dadurch bekommt jeder Spieler genau
eine zufällige Pistole und ein zufälliges Messer.
Kleidung ist kartentypisch für Nasdara (Kameez, Shalwar, Sandalen, Turban) in
zufälligen Farben. Aussehen (Gesicht, Körper) des eigenen Charakters bleibt erhalten.
"""
import json
import sys
from pathlib import Path

VOLL = {"healthMin": 1.0, "healthMax": 1.0, "quantityMin": 1.0, "quantityMax": 1.0}
GEBRAUCHT = {"healthMin": 0.6, "healthMax": 0.8, "quantityMin": 1.0, "quantityMax": 1.0}

CHARAKTERE = [
    "SurvivorM_Boris", "SurvivorM_Cyril", "SurvivorM_Denis", "SurvivorM_Elias",
    "SurvivorM_Francis", "SurvivorM_Guo", "SurvivorM_Hassan", "SurvivorM_Indar",
    "SurvivorM_Jose", "SurvivorM_Kaito", "SurvivorM_Lewis", "SurvivorM_Manua",
    "SurvivorM_Mirek", "SurvivorM_Niki", "SurvivorM_Oliver", "SurvivorM_Peter",
    "SurvivorM_Quinn", "SurvivorM_Rolf", "SurvivorM_Seth", "SurvivorM_Taiki",
    "SurvivorF_Eva", "SurvivorF_Frida", "SurvivorF_Gabi", "SurvivorF_Helga",
    "SurvivorF_Irena", "SurvivorF_Judy", "SurvivorF_Keiko", "SurvivorF_Linda",
    "SurvivorF_Maria", "SurvivorF_Naomi", "SurvivorF_Baty",
]

# Pistole -> (Munition, Anteil des Munitionsstapels). Ohne Magazin, ohne Revolver.
PISTOLEN = {
    "MakarovIJ70": ("Ammo_380", 0.3),
    "CZ75":        ("Ammo_9x19", 0.3),
    "Glock19":     ("Ammo_9x19", 0.3),
    "P1":          ("Ammo_9x19", 0.3),
    "FNX45":       ("Ammo_45ACP", 0.3),
    "Colt1911":    ("Ammo_45ACP", 0.3),
    "MKII":        ("Ammo_22", 0.2),
}


MESSER = ["KitchenKnife", "SteakKnife", "HuntingKnife", "CombatKnife",
          "KukriKnife", "FangeKnife", "DonerKnife"]

TURBANE = ["TurbanHat_Beige", "TurbanHat_Black", "TurbanHat_Brown", "TurbanHat_Green",
           "TurbanHat_Grey", "TurbanHat_NavyBlue", "TurbanHat_Pink", "TurbanHat_Purple",
           "TurbanHat_Red", "TurbanHat_Skyblue", "TurbanHat_White", "TurbanHat_Yellow"]


KAMEEZ = ["KameezShirt_Beige", "KameezShirt_Brown", "KameezShirt_Grey", "KameezShirt_Olive",
          "KameezShirt_White", "KameezShirt_Black", "KameezShirt_NavyBlue", "KameezShirt_SkyBlue"]

SHALWAR = ["MensShalwarPants_Beige", "MensShalwarPants_Black", "MensShalwarPants_Brown",
           "MensShalwarPants_Grey", "MensShalwarPants_NavyBlue", "MensShalwarPants_SkyBlue",
           "MensShalwarPants_White"]

SANDALEN = ["TraditionalSandalShoes_Black", "TraditionalSandalShoes_Brown",
            "TraditionalSandalShoes_LightBrown", "TraditionalSandalShoes_NavyBlue",
            "SandalsShoes_Black", "SandalsShoes_BlueNavy", "SandalsShoes_Brown", "SandalsShoes_Grey"]


def item(typ, attribute=VOLL, schnellleiste=-1):
    return {"itemType": typ, "attributes": attribute, "quickBarSlot": schnellleiste,
            "simpleChildrenUseDefaultAttributes": True, "simpleChildrenTypes": []}


def slot(name, typen, attribute=GEBRAUCHT):
    return {"slotName": name, "discreteItemSets": [
        {"itemType": t, "spawnWeight": 1, "attributes": attribute, "quickBarSlot": -1,
         "simpleChildrenUseDefaultAttributes": True, "simpleChildrenTypes": [],
         "complexChildrenTypes": []} for t in typen]}


def ausruestung(pistole, munition, anteil, messer):
    menge = {"healthMin": 1.0, "healthMax": 1.0, "quantityMin": anteil, "quantityMax": anteil + 0.1}
    return {
        "name": f"Start_{pistole}_{messer}",
        "spawnWeight": 1,
        "attributes": VOLL,
        "simpleChildrenUseDefaultAttributes": True,
        "simpleChildrenTypes": [],
        "complexChildrenTypes": [
            item("TacticalBaconCan"), item("TacticalBaconCan"),          # 2x Essen (Dosenspeck)
            item("WaterBottle"), item("SodaCan_Cola"), item("SodaCan_Pipsi"),  # 3x Trinken
            item("BandageDressing", schnellleiste=1),
            item("Splint"),
            item("Chemlight_White", schnellleiste=2),
            item("ChernarusMap"),
            item(pistole, GEBRAUCHT, schnellleiste=0),
            item(messer, GEBRAUCHT, schnellleiste=3),
            item(munition, menge),
        ],
    }


preset = {
    "spawnWeight": 1,
    "name": "Broken-LegZ Start",
    "characterTypes": CHARAKTERE,
    "attachmentSlotItemSets": [
        slot("Headgear", TURBANE),
        slot("Body", KAMEEZ),
        slot("Legs", SHALWAR),
        slot("Feet", SANDALEN),
        slot("Back", ["CourierBag"], VOLL),
    ],
    "discreteUnsortedItemSets": [ausruestung(p, *m, k) for p, m in PISTOLEN.items() for k in MESSER],
}

ziel = Path(sys.argv[1]) / "custom" / "startgear.json"
ziel.write_text(json.dumps(preset, indent=4, ensure_ascii=False), "utf-8")
print(f"{ziel}: {len(PISTOLEN)} Pistolen x {len(MESSER)} Messer = "
      f"{len(PISTOLEN) * len(MESSER)} Varianten")
