"""Parser für DayZ-Admin-Logs (.ADM): Positionen, Kills, Treffer und Tode."""

import re
from dataclasses import dataclass, field

# Beispiel: Player "Gamertag" (id=ABC= pos=<4567.8, 10123.4, 320.1>)
# Im ADM-Log ist die Reihenfolge <x, z, höhe>.
_POS = re.compile(
    r'Player "([^"]+)"[^<\n]*?pos=<(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)>'
)
# Player "Opfer" (DEAD) (id=... pos=<...>) killed by Player "Täter" (id=... pos=<...>) with M4A1 from 40.2 meters
_KILL = re.compile(r'Player "([^"]+)" \(DEAD\).*?killed by Player "([^"]+)"')
# Player "Opfer" (id=... pos=<...>)[HP: 85.3] hit by Player "Angreifer" (id=... pos=<...>)
#   into Head(0) for 15.2 damage (Bullet_556x45) with M4A1 from 40.2 meters
_HIT = re.compile(r'Player "([^"]+)"[^\[\n]*\[HP: (-?[\d.]+)\] hit by Player "([^"]+)"')
_HIT_DETAIL = re.compile(r'into (\w+)\(\d+\) for (-?[\d.]+) damage(?: \(([^)]+)\))?')
_WAFFE = re.compile(r'\) with (.+?)(?: from (-?[\d.]+) meters)?\s*$')
_TOD = re.compile(r'Player "([^"]+)" \(DEAD\)')


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
    waffe: str | None = None
    distanz: float | None = None


@dataclass
class Treffer:
    opfer: str
    angreifer: str
    hp: float
    koerperteil: str | None = None
    schaden: float | None = None
    waffe: str | None = None
    distanz: float | None = None


@dataclass
class Ereignisse:
    positionen: list[Position] = field(default_factory=list)
    kill: Kill | None = None
    treffer: Treffer | None = None
    tod: str | None = None   # Gamertag bei Tod ohne Spieler-Täter (Zombie, Hunger ...)


def _waffe(rest: str) -> tuple[str | None, float | None]:
    m = _WAFFE.search(rest)
    if not m:
        return None, None
    return m.group(1), float(m.group(2)) if m.group(2) else None


def parse_zeile(zeile: str) -> Ereignisse:
    e = Ereignisse(positionen=[
        Position(m.group(1), float(m.group(2)), float(m.group(4)), float(m.group(3)))
        for m in _POS.finditer(zeile)
    ])

    m = _KILL.search(zeile)
    if m:
        if m.group(1).lower() != m.group(2).lower():
            waffe, distanz = _waffe(zeile[m.end():])
            e.kill = Kill(m.group(1), m.group(2), waffe, distanz)
        else:
            e.tod = m.group(1)   # Selbstmord
        return e

    m = _HIT.search(zeile)
    if m:
        if m.group(1).lower() != m.group(3).lower():
            rest = zeile[m.end():]
            t = Treffer(m.group(1), m.group(3), float(m.group(2)))
            d = _HIT_DETAIL.search(rest)
            if d:
                t.koerperteil, t.schaden = d.group(1), float(d.group(2))
                t.waffe = d.group(3)
            waffe, t.distanz = _waffe(rest)
            t.waffe = waffe or t.waffe
            e.treffer = t
        return e

    m = _TOD.search(zeile)
    if m:
        e.tod = m.group(1)
    return e
