# Aufgabe für Claude Code: Discord-Bot auf Nasdara umstellen

> Diese Datei als ersten Auftrag in eine neue Claude-Code-Sitzung geben
> (z. B. „Lies `dayz-discord-bot/AUFGABE_CLAUDE_CODE.md` und arbeite die Aufgabe ab“).

Antworte und schreibe immer auf Deutsch.

## Kontext

- Repository `bloodvenomark/agency-agents`, Branch `claude/compassionate-bell-q9h95s`.
  Dort entwickeln, committen und pushen. Keinen Pull Request ohne Rückfrage.
- `dayz-discord-bot/` ist ein Discord-Bot für den DayZ-PS5-Server **„GER Broken-LegZ PVP“** auf der
  Karte **Nasdara**. Die Mission heißt `dayzOffline.nasdara` und liegt im Nitrado-Ordner `dayzps_missions/`.
  - Technik: Python 3.13, discord.py 2.5.2, aiohttp, sqlite3 und die Nitrado-API.
  - Funktionen: Shop mit Lieferung (feste Orte oder „Mein Standort“), Killfeed mit Belohnung,
    Hitfeed, Kopfgeld (manuell und automatisch bei Killserien), Airdrops/Lootdrops,
    Safezone-Bann (30 Tage, nur Kills, Notwehr ausgenommen), Bauverbotszone (nur Trader- und
    Admin-Rolle) sowie Trader-Läden (Zutritt nur mit der passenden Rolle „Trader 1..6“).
  - Dateien: `bot.py`, `adm.py`, `db.py`, `nitrado.py`, `lootdrop.py`, `safezone.py`, `shop.json`,
    `orte.json`, `lootdrops.json`, `trader_laeden.json`, `.env.example`, `README.md`.
- `dayz-server-nasdara/` enthält die Serverkonfiguration. Die Werkzeuge liegen in
  `dayz-server-nasdara/werkzeuge/`:
  - `safezone_bau.py` erzeugt die Safezone, eine Moschee mit Mitte x 8699.5 / z 8263.6. Die Liste
    `MESSUNGEN` enthält die im Spiel gemessenen Bodenhöhen (ca. 272–286).
  - `teleporter_bau.py` erzeugt 86 Dixi-Teleporter von den Orten zur Safezone und 6 Rück-Teleporter
    in die großen Städte. Die Übersicht steht in `dayz-server-nasdara/TELEPORTER.md`.
- Koordinaten: x = Ost-West, z = Nord-Süd, Kartengröße 16384. Im ADM-Log stehen Positionen als
  `pos=<x, z, höhe>`.

## Aufgaben

1. **`orte.json` und `lootdrops.json` auf Nasdara umstellen.** Beide haben noch Chernarus-Koordinaten.
   - Lieferpunkt Safezone vor dem Haupttor: Hof-Mitte ca. x 8700 / z 8264. Die Höhe kommt aus den
     `MESSUNGEN` in `safezone_bau.py` (ca. 280).
   - Die 6 großen Städte aus `TELEPORTER.md` (Rückreise-Ziele) als Lieferorte.
   - Airdrop-Orte auf freien Flächen, mindestens 600 m von der Safezone entfernt, über die Karte
     verteilt. Die Höhen eher +2 m ansetzen, damit nichts im Boden steckt.
   - Safezone und Bauverbot in `.env.example` müssen dazu passen: x 8700 / z 8264, Radius 75 bzw. 150.
2. **Neuer Befehl `/teleporter`.**
   - Zeigt die Dixi-Teleporter (Nummer, Koordinaten, nächste Stadt bzw. Himmelsrichtung) als Embed,
     seitenweise oder gefiltert nach Stadt oder Richtung.
   - Die Daten kommen aus einer neuen `dayz-discord-bot/teleporter.json`. Diese schreibt
     `teleporter_bau.py` zusätzlich zu `TELEPORTER.md`. Danach `teleporter_bau.py` einmal ausführen.
   - `/admin-kanaele` bzw. `/admin-einrichten` legen den Kanal „🚽│teleporter“ an und pinnen dort
     die Liste an.
3. **Gegencheck mit dem Server-Setup.**
   - Restart alle 2 Stunden ab 00:00: Erkennung in `status_schleife`.
   - Missionspfad über `missionsordner_suchen()`.
   - Trader-Rollen „Trader 1..6“ aus `trader_laeden.json`.
   - Shop-Artikel in `shop.json` gegen `dayz-server-nasdara/db/types.xml` abgleichen. Unbekannte
     Klassen korrigieren oder melden.
4. **README.md** (Deutsch) um die neuen Punkte ergänzen.

## Fertig, wenn

- `python -m py_compile` auf allen Bot-Dateien ohne Fehler durchläuft.
- Ein kurzer synthetischer Test durchläuft:
  - ADM-Beispielzeilen mit `adm.parse_zeile` parsen
  - alle JSON-Dateien laden
  - die Abstände der Airdrop-Orte zur Safezone prüfen
- Alles ist committet und nach `claude/compassionate-bell-q9h95s` gepusht.
- Am Ende steht eine kurze deutsche Zusammenfassung mit den Punkten, die der Server-Betreiber
  selbst messen oder eintragen muss, z. B. echte Städtenamen und Höhen vor Ort.
