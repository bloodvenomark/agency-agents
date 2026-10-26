"""Lootdrops / Airdrops: Paket wählen, Loot auswürfeln, Items um den Abwurfpunkt verteilen."""

import math
import random


def paket_waehlen(pakete: dict, name: str | None = None) -> tuple[str, dict]:
    """Gibt das gewünschte Paket zurück oder wählt eines zufällig nach 'gewicht'."""
    if name:
        return name, pakete[name]
    namen = list(pakete)
    gewichte = [pakete[n].get("gewicht", 1) for n in namen]
    gewaehlt = random.choices(namen, weights=gewichte, k=1)[0]
    return gewaehlt, pakete[gewaehlt]


def ort_waehlen(orte: dict, name: str | None = None) -> tuple[str, list[float]]:
    if name:
        return name, orte[name]
    gewaehlt = random.choice(list(orte))
    return gewaehlt, orte[gewaehlt]


def loot_wuerfeln(paket: dict) -> list[str]:
    """Liste von Klassennamen: 'immer' komplett + zufällige Auswahl aus 'loot'."""
    klassen: list[str] = []
    for eintrag in paket.get("immer", []):
        klassen += [eintrag["klasse"]] * eintrag.get("menge", 1)

    pool = paket.get("loot", [])
    if pool:
        anzahl = random.randint(paket.get("anzahl_min", 3), paket.get("anzahl_max", 6))
        gezogen = random.choices(pool, weights=[e.get("gewicht", 1) for e in pool], k=anzahl)
        for eintrag in gezogen:
            klassen += [eintrag["klasse"]] * eintrag.get("menge", 1)
    return klassen


def objekte_verteilen(klassen: list[str], pos: list[float], radius: float,
                      markierung: str | None = None) -> list[list]:
    """Verteilt die Items gleichmäßig auf einem Kreis um den Abwurfpunkt.

    Rückgabe: [[klasse, x, y, z], ...] – die Markierung (z. B. ein Wrack) steht in der Mitte.
    """
    x, y, z = pos
    objekte = [[markierung, x, y, z]] if markierung else []
    for i, klasse in enumerate(klassen):
        winkel = 2 * math.pi * i / max(len(klassen), 1)
        r = radius * random.uniform(0.6, 1.0)
        objekte.append([klasse, round(x + r * math.cos(winkel), 2), y,
                        round(z + r * math.sin(winkel), 2)])
    return objekte


def erzeugen(config: dict, paket_name: str | None = None, ort_name: str | None = None):
    """Erzeugt einen kompletten Lootdrop. Rückgabe: (paket, ort, pos, objekte)."""
    paket_name, paket = paket_waehlen(config["pakete"], paket_name)
    ort_name, pos = ort_waehlen(config["orte"], ort_name)
    klassen = loot_wuerfeln(paket)
    objekte = objekte_verteilen(klassen, pos, paket.get("radius", 4.0),
                                paket.get("markierung") or None)
    return paket_name, ort_name, pos, objekte
