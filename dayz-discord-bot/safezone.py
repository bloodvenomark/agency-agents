"""Safezone: erkennt Kills in der Zone und unterscheidet Angreifer von Notwehr.

Treffer werden nicht bestraft, aber gemerkt: Wer zuerst angeschossen wurde und den Angreifer
dann tötet, handelt in Notwehr."""

import math
import re

from adm import Ereignisse

NOTWEHR_SEKUNDEN = 120   # wer innerhalb dieser Zeit zuerst angegriffen wurde, darf zurückschießen
_ZEIT = re.compile(r"^(\d\d):(\d\d):(\d\d)")


def log_sekunden(zeile: str) -> int | None:
    """Uhrzeit am Zeilenanfang des ADM-Logs (HH:MM:SS) in Sekunden seit Mitternacht."""
    m = _ZEIT.match(zeile)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


class Safezone:
    def __init__(self):
        self._angriffe: dict[tuple[str, str], int] = {}   # (angreifer, opfer) -> Log-Sekunde

    def verstoss(self, e: Ereignisse, sekunde: int, x: float, z: float, radius: float) -> str | None:
        """Gibt den Gamertag des Täters zurück, wenn er in der Zone jemanden getötet hat."""
        if e.kill:
            angreifer, opfer = e.kill.taeter, e.kill.opfer
        elif e.treffer:
            angreifer, opfer = e.treffer.angreifer, e.treffer.opfer
        else:
            return None
        if e.treffer:
            self._angriffe[(angreifer.lower(), opfer.lower())] = sekunde
            return None   # nur Kills werden bestraft

        positionen = {p.gamertag.lower(): p for p in e.positionen}
        in_zone = any(
            (p := positionen.get(n.lower())) and math.dist((p.x, p.z), (x, z)) <= radius
            for n in (angreifer, opfer)
        )
        if not in_zone:
            return None
        # Notwehr: das Opfer hat den Täter kurz vorher selbst angeschossen
        gegenangriff = self._angriffe.get((opfer.lower(), angreifer.lower()))
        if gegenangriff is not None and 0 <= (sekunde - gegenangriff) % 86400 <= NOTWEHR_SEKUNDEN:
            return None
        return angreifer
