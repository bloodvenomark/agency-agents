"""SQLite-Datenbank: Konten, Gamertag-Verknüpfung, Positionen, Bestellungen."""

import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS konten (
    discord_id  INTEGER PRIMARY KEY,
    gamertag    TEXT UNIQUE COLLATE NOCASE,
    geld        INTEGER NOT NULL DEFAULT 0,
    letzter_bonus INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS positionen (
    gamertag TEXT PRIMARY KEY COLLATE NOCASE,
    x REAL, y REAL, z REAL,
    zeit INTEGER
);
CREATE TABLE IF NOT EXISTS bestellungen (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    artikel    TEXT NOT NULL,
    klasse     TEXT NOT NULL,
    menge      INTEGER NOT NULL,
    preis      INTEGER NOT NULL,
    ort        TEXT NOT NULL,
    x REAL, y REAL, z REAL,
    status     TEXT NOT NULL DEFAULT 'wartend',   -- wartend | geliefert | erstattet
    erstellt   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS zustand (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT
);
"""


class DB:
    def __init__(self, path: str):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.con.commit()

    # --- Konten -----------------------------------------------------------
    def konto(self, discord_id: int) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM konten WHERE discord_id = ?", (discord_id,)
        ).fetchone()

    def konto_per_gamertag(self, gamertag: str) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM konten WHERE gamertag = ?", (gamertag,)
        ).fetchone()

    def verknuepfen(self, discord_id: int, gamertag: str, startgeld: int):
        if self.konto(discord_id):
            self.con.execute(
                "UPDATE konten SET gamertag = ? WHERE discord_id = ?", (gamertag, discord_id)
            )
        else:
            self.con.execute(
                "INSERT INTO konten (discord_id, gamertag, geld) VALUES (?, ?, ?)",
                (discord_id, gamertag, startgeld),
            )
        self.con.commit()

    def geld_aendern(self, discord_id: int, betrag: int):
        self.con.execute(
            "UPDATE konten SET geld = geld + ? WHERE discord_id = ?", (betrag, discord_id)
        )
        self.con.commit()

    def bonus_setzen(self, discord_id: int):
        self.con.execute(
            "UPDATE konten SET letzter_bonus = ? WHERE discord_id = ?",
            (int(time.time()), discord_id),
        )
        self.con.commit()

    # --- Positionen -------------------------------------------------------
    def position_setzen(self, gamertag: str, x: float, y: float, z: float):
        self.con.execute(
            "INSERT INTO positionen (gamertag, x, y, z, zeit) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(gamertag) DO UPDATE SET x=excluded.x, y=excluded.y, "
            "z=excluded.z, zeit=excluded.zeit",
            (gamertag, x, y, z, int(time.time())),
        )
        self.con.commit()

    def position(self, gamertag: str) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM positionen WHERE gamertag = ?", (gamertag,)
        ).fetchone()

    # --- Bestellungen -----------------------------------------------------
    def kaufen(self, discord_id: int, artikel: str, klasse: str, menge: int,
               preis: int, ort: str, x: float, y: float, z: float) -> int:
        """Bucht Geld ab und legt die Bestellung an (in einer Transaktion)."""
        with self.con:
            cur = self.con.execute(
                "UPDATE konten SET geld = geld - ? WHERE discord_id = ? AND geld >= ?",
                (preis, discord_id, preis),
            )
            if cur.rowcount == 0:
                raise ValueError("nicht genug Geld")
            cur = self.con.execute(
                "INSERT INTO bestellungen (discord_id, artikel, klasse, menge, preis, "
                "ort, x, y, z, erstellt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (discord_id, artikel, klasse, menge, preis, ort, x, y, z, int(time.time())),
            )
            return cur.lastrowid

    def wartende(self) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM bestellungen WHERE status = 'wartend' ORDER BY id"
        ).fetchall()

    def bestellungen_von(self, discord_id: int, limit: int = 10) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM bestellungen WHERE discord_id = ? ORDER BY id DESC LIMIT ?",
            (discord_id, limit),
        ).fetchall()

    def als_geliefert(self, bis_id: int) -> list[sqlite3.Row]:
        rows = self.con.execute(
            "SELECT * FROM bestellungen WHERE status = 'wartend' AND id <= ?", (bis_id,)
        ).fetchall()
        self.con.execute(
            "UPDATE bestellungen SET status = 'geliefert' WHERE status = 'wartend' AND id <= ?",
            (bis_id,),
        )
        self.con.commit()
        return rows

    def letzte_bestell_id(self) -> int:
        row = self.con.execute("SELECT MAX(id) FROM bestellungen").fetchone()
        return row[0] or 0

    # --- Zustand (z. B. Log-Fortschritt) ---------------------------------
    def get(self, schluessel: str, default: str | None = None) -> str | None:
        row = self.con.execute(
            "SELECT wert FROM zustand WHERE schluessel = ?", (schluessel,)
        ).fetchone()
        return row[0] if row else default

    def set(self, schluessel: str, wert: str):
        self.con.execute(
            "INSERT INTO zustand (schluessel, wert) VALUES (?, ?) "
            "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert",
            (schluessel, wert),
        )
        self.con.commit()
