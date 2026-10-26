"""Parser für DayZ-Admin-Logs (.ADM): Spielerpositionen und Kills."""

import re
from dataclasses import dataclass

# Beispiel: Player "Gamertag" (id=ABC= pos=<4567.8, 10123.4, 320.1>)
# Im ADM-Log ist die Reihenfolge <x, z, höhe>.
_POS = re.compile(
    r'Player "([^"]+)"[^<\n]*?pos=<(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)>'
)
# Beispiel: Player "Opfer" (DEAD) (id=... pos=<...>) killed by Player "Täter" (id=... ) with M4A1 from 40 meters
_KILL = re.compile(r'Player "([^"]+)" \(DEAD\).*?killed by Player "([^"]+)"')


@dataclass
class Position:
    gamertag: str
    x: float       # Ost-West
    hoehe: float   # Höhe über Meer
    z: float       # Nord-Süd


@dataclass
class Kill:
    opfer: str
    taeter: str


def parse_zeile(zeile: str) -> tuple[list[Position], Kill | None]:
    positionen = [
        Position(m.group(1), float(m.group(2)), float(m.group(4)), float(m.group(3)))
        for m in _POS.finditer(zeile)
    ]
    kill = None
    m = _KILL.search(zeile)
    if m and m.group(1).lower() != m.group(2).lower():
        kill = Kill(opfer=m.group(1), taeter=m.group(2))
    return positionen, kill
