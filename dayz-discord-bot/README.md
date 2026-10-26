# DayZ Discord-Bot mit Shop & Lieferung an Orte (PlayStation / Nitrado)

Spieler kaufen im Discord Items mit Spielgeld. Der Bot lässt die Items in DayZ an
einem festen Ort oder direkt am eigenen Standort spawnen. Funktioniert ohne Mods,
also auch auf PS4/PS5-Servern von Nitrado.

## Funktionen

| Befehl | Beschreibung |
|---|---|
| `/verknuepfen <gamertag>` | Discord mit PSN-Name verbinden (gibt Startguthaben) |
| `/konto` | Guthaben anzeigen |
| `/taeglich` | Täglicher Bonus (alle 20 Stunden) |
| `/shop [kategorie]` | Shop anzeigen |
| `/kaufen <artikel> <ort>` | Kaufen und liefern lassen, mit Auswahlliste für Artikel und Ort |
| `/bestellungen` | Eigene Bestellungen und deren Status |
| `/admin-geld <spieler> <betrag>` | Geld geben oder abziehen (negativer Betrag) |
| `/admin-neustart` | Server neu starten, damit alles sofort geliefert wird |
| `/admin-einrichten` | Trägt die Lieferdatei automatisch in `cfggameplay.json` ein |

Außerdem:
- **Kill-Belohnung**: Für jeden Spieler-Kill gibt es Geld (aus dem Admin-Log).
- **Lieferung an den eigenen Standort**: Die Position stammt aus dem Admin-Log
  (Spielerliste, etwa alle 5 Minuten).

## So funktioniert die Lieferung

Auf Konsole gibt es keine Mods und keine RCON-Befehle. Der Bot nutzt deshalb den
offiziellen **Object Spawner** von DayZ:

1. Nach dem Kauf schreibt der Bot das Item mit Koordinaten in
   `mpmissions/<karte>/custom/shop_lieferungen.json`.
2. Beim **nächsten Server-Neustart** spawnt DayZ die Items dort.
3. Der Bot erkennt den Neustart, schickt dem Käufer eine DM („Lieferung bereit“)
   und leert die Datei, damit nichts doppelt spawnt.

Mit `NEUSTART_NACH_KAUF=true` startet der Server nach jedem Kauf neu, die Lieferung
kommt dann sofort. Das ist für volle Server meist störend. Empfehlung: `false` lassen
und die geplanten Nitrado-Neustarts nutzen (z. B. alle 3 Stunden).

## Einrichtung

### 1. Discord-Bot anlegen
1. Auf https://discord.com/developers/applications eine **New Application** anlegen,
   dann unter **Bot** den Token kopieren.
2. Unter **OAuth2 → URL Generator** die Scopes `bot` und `applications.commands`
   wählen, als Rechte `Send Messages` und `Embed Links`. Mit dem Link den Bot auf
   deinen Discord einladen.

### 2. Nitrado vorbereiten
1. Einen Long-Life-Token erstellen: https://server.nitrado.net/deu/developer/tokens
   (Rechte: `service`).
2. Die **Service-ID** steht in der URL deines Servers im Webinterface.
3. In den Server-Einstellungen:
   - **cfggameplay.json aktivieren** (heißt je nach Oberfläche „enableCfgGameplayFile“)
   - **Admin-Log / Spielerliste aktivieren**, sonst funktioniert „Mein Standort“ nicht

### 3. Bot installieren
Benötigt wird Python 3.10 oder neuer, auf einem Rechner oder Raspberry Pi, der
dauerhaft läuft.

```bash
cd dayz-discord-bot
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # danach .env ausfüllen
python bot.py
```

### 4. Einmalig einrichten
Im Discord `/admin-einrichten` ausführen und danach den Server einmal neu starten.

## Anpassen

- **`shop.json`**: Kategorien, Artikel, Preise und Mengen. `klasse` ist der
  DayZ-Klassenname (wie in `types.xml`).
- **`orte.json`**: Lieferorte als `[x, höhe, z]`. Die x- und z-Werte kannst du z. B.
  von izurvive.com nehmen.
  **Die Höhe muss stimmen**, sonst schweben die Items oder stecken im Boden. Sicher
  bekommst du sie aus dem Admin-Log: Stell dich an den Ort und lies deine Position ab.
  Im Log steht sie als `pos=<x, z, höhe>`.
  Die Beispielorte sind nur grobe Werte und müssen vor dem Einsatz geprüft werden.
- **`.env`**: Startgeld, Bonus, Kill-Belohnung, Währungsname, Karte.

## Bekannte Grenzen

- Lieferungen kommen erst **nach einem Neustart** an. Anders geht es auf Konsole nicht.
- Items, die über den Object Spawner erscheinen, sollten aufhebbar sein. Teste das
  mit einem günstigen Item, bevor du den Shop freigibst.
- Die Pfade werden automatisch über die Nitrado-API ermittelt. Falls das nicht
  klappt, trage `MISSION_DIR` und `ADM_LOG_DIR` in der `.env` ein (Pfade findest du
  im Nitrado-Dateibrowser).
- Ein Gamertag kann nur mit einem Discord-Konto verknüpft werden. Wer jedoch einen
  fremden Gamertag zuerst einträgt, kassiert dessen Kill-Belohnungen. Für öffentliche
  Server sollte ein Admin die Verknüpfungen prüfen.
