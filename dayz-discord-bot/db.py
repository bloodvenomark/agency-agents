"""SQLite-Datenbank: Konten, Gamertag-Verknüpfung, Positionen, Bestellungen."""

import json
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
CREATE TABLE IF NOT EXISTS statistik (
    gamertag    TEXT PRIMARY KEY COLLATE NOCASE,
    kills       INTEGER NOT NULL DEFAULT 0,
    tode        INTEGER NOT NULL DEFAULT 0,
    serie       INTEGER NOT NULL DEFAULT 0,
    beste_serie INTEGER NOT NULL DEFAULT 0,
    weitester   REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kopfgelder (
    gamertag    TEXT PRIMARY KEY COLLATE NOCASE,
    betrag      INTEGER NOT NULL DEFAULT 0,   -- von Spielern gesetzt
    auto_betrag INTEGER NOT NULL DEFAULT 0    -- automatisch (Killserie)
);
CREATE TABLE IF NOT EXISTS lootdrops (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    paket    TEXT NOT NULL,
    ort      TEXT NOT NULL,
    x REAL, y REAL, z REAL,
    objekte  TEXT NOT NULL,                   -- JSON: [[klasse, x, y, z], ...]
    status   TEXT NOT NULL DEFAULT 'wartend', -- wartend | gelandet
    erstellt INTEGER NOT NULL
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

    # --- Statistik --------------------------------------------------------
    def stat_kill(self, gamertag: str, distanz: float | None) -> int:
        """Zählt einen Kill und gibt die neue Killserie zurück."""
        self.con.execute(
            "INSERT INTO statistik (gamertag, kills, serie, beste_serie, weitester) "
            "VALUES (?, 1, 1, 1, ?) ON CONFLICT(gamertag) DO UPDATE SET "
            "kills = kills + 1, serie = serie + 1, "
            "beste_serie = MAX(beste_serie, serie + 1), "
            "weitester = MAX(weitester, excluded.weitester)",
            (gamertag, distanz or 0),
        )
        self.con.commit()
        return self.statistik(gamertag)["serie"]

    def stat_tod(self, gamertag: str, durch_spieler: bool):
        self.con.execute(
            "INSERT INTO statistik (gamertag, tode) VALUES (?, ?) "
            "ON CONFLICT(gamertag) DO UPDATE SET tode = tode + excluded.tode, serie = 0",
            (gamertag, 1 if durch_spieler else 0),
        )
        self.con.commit()

    def statistik(self, gamertag: str) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM statistik WHERE gamertag = ?", (gamertag,)
        ).fetchone()

    def bestenliste(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM statistik WHERE kills > 0 "
            "ORDER BY kills DESC, tode ASC LIMIT ?", (limit,)
        ).fetchall()

    def bekannte_spieler(self, suche: str, limit: int = 25) -> list[str]:
        rows = self.con.execute(
            "SELECT gamertag FROM positionen WHERE gamertag LIKE ? "
            "ORDER BY zeit DESC LIMIT ?", (f"%{suche}%", limit),
        ).fetchall()
        return [r[0] for r in rows]

    # --- Kopfgelder -------------------------------------------------------
    def kopfgeld(self, gamertag: str) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT * FROM kopfgelder WHERE gamertag = ?", (gamertag,)
        ).fetchone()

    def kopfgelder(self) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT *, betrag + auto_betrag AS gesamt FROM kopfgelder "
            "ORDER BY gesamt DESC"
        ).fetchall()

    def kopfgeld_setzen(self, discord_id: int, gamertag: str, betrag: int):
        """Spieler setzt Kopfgeld aus eigenem Guthaben."""
        with self.con:
            cur = self.con.execute(
                "UPDATE konten SET geld = geld - ? WHERE discord_id = ? AND geld >= ?",
                (betrag, discord_id, betrag),
            )
            if cur.rowcount == 0:
                raise ValueError("nicht genug Geld")
            self.con.execute(
                "INSERT INTO kopfgelder (gamertag, betrag) VALUES (?, ?) "
                "ON CONFLICT(gamertag) DO UPDATE SET betrag = betrag + excluded.betrag",
                (gamertag, betrag),
            )

    def kopfgeld_auto(self, gamertag: str, betrag: int):
        self.con.execute(
            "INSERT INTO kopfgelder (gamertag, auto_betrag) VALUES (?, ?) "
            "ON CONFLICT(gamertag) DO UPDATE SET auto_betrag = auto_betrag + excluded.auto_betrag",
            (gamertag, betrag),
        )
        self.con.commit()

    def kopfgeld_entfernen(self, gamertag: str):
        self.con.execute("DELETE FROM kopfgelder WHERE gamertag = ?", (gamertag,))
        self.con.commit()

    def kopfgeld_auto_zuruecksetzen(self, gamertag: str):
        """Killserie beendet: automatischer Anteil verfällt, gesetztes Kopfgeld bleibt."""
        self.con.execute(
            "UPDATE kopfgelder SET auto_betrag = 0 WHERE gamertag = ?", (gamertag,)
        )
        self.con.execute("DELETE FROM kopfgelder WHERE betrag = 0 AND auto_betrag = 0")
        self.con.commit()

    # --- Lootdrops --------------------------------------------------------
    def lootdrop_anlegen(self, paket: str, ort: str, x: float, y: float, z: float,
                         objekte: list) -> int:
        cur = self.con.execute(
            "INSERT INTO lootdrops (paket, ort, x, y, z, objekte, erstellt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (paket, ort, x, y, z, json.dumps(objekte), int(time.time())),
        )
        self.con.commit()
        return cur.lastrowid

    def lootdrops_wartend(self) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM lootdrops WHERE status = 'wartend' ORDER BY id"
        ).fetchall()

    def lootdrops_gelandet(self, bis_id: int) -> list[sqlite3.Row]:
        rows = self.con.execute(
            "SELECT * FROM lootdrops WHERE status = 'wartend' AND id <= ?", (bis_id,)
        ).fetchall()
        self.con.execute(
            "UPDATE lootdrops SET status = 'gelandet' WHERE status = 'wartend' AND id <= ?",
            (bis_id,),
        )
        self.con.commit()
        return rows

    def letzte_lootdrop_id(self) -> int:
        row = self.con.execute("SELECT MAX(id) FROM lootdrops").fetchone()
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
