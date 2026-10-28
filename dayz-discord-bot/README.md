# DayZ Discord-Bot (PlayStation / Nitrado)

Shop mit Lieferung an Orte, Killfeed mit Belohnung, Hitfeed, Kopfgeld-System mit
automatischem Kopfgeld und anpassbaren Airdrops. Funktioniert ohne Mods, also auch
auf PS4/PS5-Servern von Nitrado.

## Funktionen

| Befehl | Beschreibung |
|---|---|
| `/verknuepfen <gamertag>` | Discord mit PSN-Name verbinden (gibt Startguthaben) |
| `/konto` | Guthaben anzeigen |
| `/taeglich` | Täglicher Bonus (alle 20 Stunden) |
| `/shop [kategorie]` | Shop anzeigen |
| `/kaufen <artikel> <ort>` | Kaufen und liefern lassen, mit Auswahlliste für Artikel und Ort |
| `/bestellungen` | Eigene Bestellungen und deren Status |
| `/statistik [gamertag]` | Kills, Tode, K/D, Killserie, weitester Kill |
| `/bestenliste` | Top 10 nach Kills |
| `/kopfgeld setzen <gamertag> <betrag>` | Kopfgeld aus eigenem Guthaben aussetzen |
| `/kopfgeld liste` | Alle offenen Kopfgelder |
| `/admin-geld <spieler> <betrag>` | Geld geben oder abziehen (negativer Betrag) |
| `/admin-kopfgeld-entfernen <gamertag>` | Kopfgeld löschen |
| `/admin-lootdrop [paket] [ort] [sofort] [ankuendigen]` | Airdrop planen (Paket und Ort wählbar oder Zufall) |
| `/admin-neustart` | Server neu starten, damit alles sofort geliefert wird |
| `/admin-einrichten` | Trägt die Lieferdatei automatisch in `cfggameplay.json` ein |
| `/admin-kanaele` | Erstellt fehlende Bot-Kanäle und die Admin-Rolle neu |
| `/admin-basisschaden <basis_schaden> [container_schaden]` | Schaltet Schaden an Zäunen/Wachtürmen bzw. Zelten/Fässern direkt in `cfggameplay.json` ein oder aus |

Außerdem:
- **Lieferung an den eigenen Standort**: Die Position stammt aus dem Admin-Log
  (Spielerliste, etwa alle 5 Minuten).

### Killfeed mit Kill-Belohnung
Jeder Spieler-Kill erscheint im Killfeed-Kanal mit Täter, Opfer, Waffe, Distanz und
Killserie. Der Täter bekommt `KILL_BELOHNUNG`, optional plus `KILL_BONUS_PRO_100M`
für jede 100 m Distanz. Geld gibt es nur für verknüpfte Spieler.

### Hitfeed
Jeder Treffer von Spieler auf Spieler erscheint im Hitfeed-Kanal mit Körperteil,
Waffe, Distanz, Schaden und restlicher HP. Kopftreffer sind orange markiert.
Auf vollen Servern kann das viel werden, dann `HITFEED_AN=false` setzen.

### Kopfgeld-System
- **Manuell**: Spieler setzen mit `/kopfgeld setzen` Geld auf einen anderen Spieler aus.
  Mehrere Kopfgelder auf denselben Spieler werden addiert.
- **Automatisch**: Ab einer Killserie von `AUTO_KOPFGELD_AB_SERIE` Kills ohne Tod
  setzt der Server `AUTO_KOPFGELD_START` aus, danach `AUTO_KOPFGELD_PRO_KILL` pro
  weiterem Kill.
- Wer den Gesuchten tötet (und verknüpft ist), kassiert alles. Die Ankündigung zeigt
  den ungefähren letzten Standort (± 100 m), abschaltbar mit `KOPFGELD_STANDORT_ZEIGEN`.
- Stirbt der Gesuchte anders (Zombie, Hunger, Selbstmord, Täter nicht verknüpft),
  verfällt nur der automatische Anteil. Von Spielern gesetztes Kopfgeld bleibt stehen.

### Lootdrops / Airdrops
Alles wird in **`lootdrops.json`** eingestellt:
- **`pakete`**: beliebig viele Loot-Pakete (Beispiele: Militär, Medizin, Basisbau, Survival)
  - `immer`: Items, die garantiert dabei sind
  - `loot`: Pool, aus dem zufällig `anzahl_min` bis `anzahl_max` Items gezogen werden.
    Ein höheres `gewicht` bedeutet häufiger, `menge` gibt die Stückzahl pro Ziehung an.
  - `gewicht` des Pakets: wie oft es bei Zufallsauswahl gewählt wird
  - `radius`: wie weit die Items um den Abwurfpunkt verteilt werden
  - `markierung`: optionales Objekt in der Mitte (z. B. ein Wrack), vorher testen
- **`orte`**: vorinstallierte Abwurforte `[x, höhe, z]`. Ohne Angabe wird zufällig
  einer gewählt.
- **`automatisch`**: Nach jedem Neustart plant der Bot mit `chance_pro_neustart` %
  einen zufälligen Airdrop für den nächsten Neustart. Mit `ort_vorher_ankuendigen`
  wird der Ort schon vorher verraten, sonst erst bei der Landung.

Ankündigung und Landung (mit Koordinaten) erscheinen im Lootdrop-Kanal. Admins können
mit `/admin-lootdrop` jederzeit einen Drop planen, mit `sofort: True` startet der
Server direkt neu.

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
   wählen. Als Rechte brauchst du:
   `Manage Roles`, `Manage Channels`, `View Channels`, `Send Messages` und `Embed Links`.
   Mit dem Link den Bot auf deinen Discord einladen.
3. In Discord unter Einstellungen → Erweitert den **Entwicklermodus** einschalten,
   dann Rechtsklick auf deinen Server → **Server-ID kopieren** und als `GUILD_ID`
   in die `.env` eintragen.

**Kanäle und Rolle legt der Bot beim ersten Start selbst an:**

```
🧟 DayZ
├── 🛒│shop       Spieler nutzen hier die Befehle
├── 💀│killfeed   nur lesen
├── 🎯│hitfeed    nur lesen (abschaltbar mit HITFEED_AN=false)
├── 💰│kopfgeld   nur lesen
└── 🪂│airdrops   nur lesen
+ Rolle „DayZ Admin“
```

Vorhandene Kanäle mit gleichem Namen werden wiederverwendet, es entsteht also nichts
doppelt. Wer eigene, schon bestehende Kanäle nutzen will, trägt deren IDs in die
`.env` ein (`KILLFEED_KANAL` usw.). Mit `KANAELE_AUTOMATISCH=false` schaltest du die
automatische Erstellung ab. Gelöschte Kanäle stellt `/admin-kanaele` wieder her.
Kanäle und Rolle kannst du danach frei umbenennen. Die Rolle muss sich aber weiter
mit `ADMIN_ROLE` decken.

### 2. Nitrado vorbereiten
1. Einen Long-Life-Token erstellen: https://server.nitrado.net/deu/developer/tokens
   (Rechte: `service`).
2. Die **Service-ID** steht in der URL deines Servers im Webinterface.
3. In den Server-Einstellungen:
   - **cfggameplay.json aktivieren** (heißt je nach Oberfläche „enableCfgGameplayFile“)
   - **Admin-Log aktivieren, inklusive Spielerliste und Treffer (Hits)**. Sonst
     funktionieren „Mein Standort“, Hitfeed und Kopfgeld-Standort nicht.

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
Gib dir die neue Rolle **DayZ Admin**. Dann im Discord `/admin-einrichten` ausführen
und den DayZ-Server einmal neu starten.

## Anpassen

- **`shop.json`**: Kategorien, Artikel, Preise und Mengen. `klasse` ist der
  DayZ-Klassenname (wie in `types.xml`).
- **`orte.json`**: Lieferorte als `[x, höhe, z]`. Die x- und z-Werte kannst du z. B.
  von izurvive.com nehmen.
  **Die Höhe muss stimmen**, sonst schweben die Items oder stecken im Boden. Sicher
  bekommst du sie aus dem Admin-Log: Stell dich an den Ort und lies deine Position ab.
  Im Log steht sie als `pos=<x, z, höhe>`.
  Die Beispielorte sind nur grobe Werte und müssen vor dem Einsatz geprüft werden.
- **`lootdrops.json`**: Airdrop-Pakete, Loot, Wahrscheinlichkeiten und Orte (siehe oben).
- **`.env`**: Startgeld, Bonus, Kill-Belohnung, Kopfgeld-Regeln, Discord-Kanäle,
  Währungsname, Karte.

## Wichtig: Basisschaden und cfggameplay.json

Der Bot braucht eine aktivierte `cfggameplay.json`. Sobald sie aktiv ist, gelten deren
Werte unter `GeneralData` (`disableBaseDamage`, `disableContainerDamage`) und **nicht mehr**
die Schalter im Nitrado-Webinterface. Steht dort `false`, lässt sich der Zaunschaden
über Nitrado nicht abschalten. Lösung: `/admin-basisschaden basis_schaden:False`
ausführen (oder den Wert in der Datei per Hand auf `true` setzen) und den Server neu starten.

## Bekannte Grenzen

- Lieferungen und Airdrops kommen erst **nach einem Neustart** an. Anders geht es auf
  Konsole nicht.
- Killfeed und Hitfeed hängen ca. 1 Minute hinterher, weil das Admin-Log jede Minute
  abgeholt wird.
- Die Log-Formate (Kills, Treffer) sind nach dem bekannten DayZ-ADM-Format gebaut.
  Weicht dein Log ab, schick mir ein paar Zeilen daraus, dann passe ich den Parser an.
- Die Beispiel-Orte in `lootdrops.json` sind grobe Werte für Chernarus. Prüfe sie vorher.
- Items, die über den Object Spawner erscheinen, sollten aufhebbar sein. Teste das
  mit einem günstigen Item, bevor du den Shop freigibst.
- Die Pfade werden automatisch über die Nitrado-API ermittelt. Falls das nicht
  klappt, trage `MISSION_DIR` und `ADM_LOG_DIR` in der `.env` ein (Pfade findest du
  im Nitrado-Dateibrowser).
- Ein Gamertag kann nur mit einem Discord-Konto verknüpft werden. Wer jedoch einen
  fremden Gamertag zuerst einträgt, kassiert dessen Kill-Belohnungen. Für öffentliche
  Server sollte ein Admin die Verknüpfungen prüfen.
