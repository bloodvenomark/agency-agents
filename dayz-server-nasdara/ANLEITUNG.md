# GER Broken-LegZ PVP – angepasste Serverdateien (Nasdara)

## Hochladen

**Vorher:** Server stoppen und von jeder Originaldatei eine Sicherung herunterladen.

Im Nitrado-Dateibrowser unter `dayzps_missions/dayzOffline.nasdara/`:

| Datei aus dieser ZIP | Ziel auf dem Server |
|---|---|
| `db/types.xml` | `dayzOffline.nasdara/db/types.xml` |
| `db/events.xml` | `dayzOffline.nasdara/db/events.xml` |
| `db/globals.xml` | `dayzOffline.nasdara/db/globals.xml` |
| `env/zombie_territories.xml` | `dayzOffline.nasdara/env/zombie_territories.xml` |
| `cfgspawnabletypes.xml` | `dayzOffline.nasdara/cfgspawnabletypes.xml` |
| `cfggameplay.json` | `dayzOffline.nasdara/cfggameplay.json` |
| `cfgplayerspawnpoints.xml` | `dayzOffline.nasdara/cfgplayerspawnpoints.xml` |
| `custom/startgear.json` | `dayzOffline.nasdara/custom/startgear.json` (neu) |
| `custom/safezone.json` | `dayzOffline.nasdara/custom/safezone.json` (neu) |

Danach im Webinterface prüfen, dass **cfggameplay.json aktiviert** ist, und den Server starten.

**Neustart-Zeitplan:** alle 2 Stunden ab 00 Uhr (00, 02, 04, … 22 Uhr), im Nitrado-Webinterface
unter *Geplante Neustarts* einstellen. Die M4A1-Zeiten sind darauf abgestimmt.

## Was geändert wurde

### Loot (`db/types.xml`)
- **+50 %** für alle Items (gesamt 25.080 → 37.738). Einzelstücke (nominal 1, z. B. M4A1, FAL, AUG)
  bleiben einzeln, sonst gäbe es sie doppelt so oft.
- **Plattenträger (Weste, Holster, Taschen) und Nachtsicht (Brille, Kopfband)** spawnen jetzt
  allgemein in **Tier 3 (gelb)** in Militärgebieten und weiterhin in Tier 4.
- **M4A1 pro Restart-Zyklus (2 h): 1× in Gelb (Tier 3), 2× in Lila (Tier 4).**
  - Normale M4A1: genau 1 Stück, nur in gelben Militärgebieten.
  - Schwarze M4A1 (`M4A1_Black`): genau 2 Stück, nur an den Tier-4-Orten, gleiche Ausstattung.
  - Nach dem Looten kommt die nächste erst nach 2 Stunden. Ungelootet verschwindet sie nach
    2 Stunden und spawnt woanders neu.
- **Rest von Tier 4 bleibt Tier 4.** Etwa 10 % davon sind zusätzlich in Tier 3 möglich:
  AK-Schalldämpfer, CMAG-40er-Magazin, STANAG-60er-Magazin.
- **Grüne Gebiete (Tier 1):** Kein Tier-4-Item wurde dort freigegeben.
- **Loot-Respawn höchstens 15 Minuten:** 112 Items (vor allem Waffen und seltene Sachen) hatten
  30 Minuten bis 24 Stunden Wartezeit, jetzt 15 Minuten. Alle anderen respawnen wie bisher sofort
  bzw. schneller. Ausnahme: M4A1 (fest pro Restart, siehe oben).
- **Zustand des Loots nur „abgenutzt“ oder „beschädigt“** (`db/globals.xml`:
  LootDamageMin 0.3 / LootDamageMax 0.7). Kein makelloser, kein stark beschädigter und kein
  ruinierter Loot mehr.
  Auch Waffen und Optiken mit eigenen Zustandswerten (96 Einträge in `cfgspawnabletypes.xml`)
  sind angeglichen. Fahrzeuge sind davon ausgenommen.
- **Magazine** spawnen mit 10–90 % Füllung statt 5–50 %, also mal fast leer, mal fast voll.
- **Benzinkanister und Wasserflaschen** spawnen immer voll (auch in der Welt, nicht nur im Auto).

### Waffen (`cfgspawnabletypes.xml`)
- Alle 51 Magazin-Plätze an Waffen auf **50 %**: Waffen kommen mal mit, mal ohne Magazin.

### Fahrzeuge
- **+50 %** (`db/events.xml`), z. B. Sedan 8 → 12, Motorräder 30 → 45, LKW 6 → 9.
- **Voll ausgestattet:** alle Räder, Türen, Batterie, Kühler, Zündkerze und Lichter bei 26 Fahrzeugtypen.
- **Ladung:** Autos und LKW (16 Typen) haben **1 vollen Benzinkanister + 5 volle Wasserflaschen**
  im Kofferraum. Damit können Spieler Tank und Kühler selbst füllen. Motorräder haben keinen Stauraum.

### Zombies (+30 %)
- `env/zombie_territories.xml`: Zombies pro Zone +30 %.
- `db/events.xml`: Infected-Events +30 %, `db/globals.xml`: Obergrenze 1000 → 1300.

### Startausrüstung (`custom/startgear.json`)
**Kartentypische Kleidung** in zufälligen Farben: **Turban**, Kameez-Hemd, Shalwar-Hose und
**Sandalen**. Dazu Umhängetasche, 2× Essen (Dosenspeck),
3× Trinken (Wasserflasche, 2 Dosen), Verband, **Schiene**, Knicklicht, Papierkarte,
1 zufälliges **Messer**, 1 zufällige Pistole **ohne Magazin** mit etwas Munition.
- Pistolen: Makarov, CZ75, Glock 19, P1, FNX45, Colt 1911, MKII. Kein Revolver.
- Messer: Küchenmesser, Steakmesser, Jagdmesser, Kampfmesser, Kukri, Fange-Messer, Dönermesser.

**Eigener Charakter:** Aussehen (Gesicht, Körper) bleibt erhalten, die Kleidung ist aber für alle
die kartentypische Startkleidung.

### Spieler-Spawns (`cfgplayerspawnpoints.xml`)
- **50 Spawnpunkte** für neue Charaktere statt 20, verteilt über die ganze Karte (Nord bis Süd).
- **+1 Spawnpunkt in der Safezone-Moschee** (x 8725 / z 8265), also insgesamt 51.
- **Nicht in Ortschaften:** jeder Punkt 400–900 m von der nächsten Ortschaft entfernt,
  mindestens 700 m von Militär und 500 m von den Giftgas-Tunneln.
- Das Spiel sucht rund um jeden Punkt (200 × 200 m) eine trockene, nicht zu steile Stelle.
- Übersicht: `spawns_vorschau.png` (grüne Sterne = neu, blaue Kreuze = bisher).
- Spawns für Server-Wechsler (`hop`) sind unverändert.

### Safezone: Moschee südlich von Bam-e Sabz (`custom/safezone.json`)
- **Kopie der großen Nasdara-Moschee** (28 Teile, ca. 100 × 100 m) bei **x 8725 / z 8265**,
  ca. 55 m südöstlich deiner Markierung, auf einer freien, baumlosen Fläche. Jedes Teil steht
  auf seiner eigenen geschätzten Bodenhöhe (Gelände fällt nach Osten um ca. 6 % ab). Die Original-Moschee in Nasdara bleibt stehen.
- **Eingerichteter Innenhof** (Grundriss: `safezone_grundriss.png`), nach jedem Restart neu:
  - **Grillplatz (Südosten):** Feuerstelle + Grillrost. Daneben 2 Holzkisten mit 6× Feuerholz und
    4× Streichhölzern sowie 2 Kisten mit Essen **obendrauf**: 3 Dosenspeck, 2 Bohnen, 2 Pfirsiche
    (linke Kiste) und 3 Ziegen- und 3 Hühnerfleisch (rechte Kiste).
  - **Wasser (Südwesten):** Wasser-Tankwagen als Wasserquelle + 10 Wasserflaschen zum Befüllen.
    Keine sonstigen Getränke.
  - **Sanitätszelt (Nordwesten):** großes Sanitätszelt mit 2 Tischen, darauf 5 Verbände,
    2 Desinfektionsspray, 1 Erste-Hilfe-Kasten.
  - Die Items liegen neben den Kisten (in Kisten hineinlegen kann der Object Spawner nicht).
  - Eine Couch gibt es in den Nasdara-Dateien nicht.
- **Traderbereich:** 6 Ladengeschäfte (`Land_Store_Street1`) im Innenhof, Fenster zur Hofmitte:
  Trader 1 + 2 an der Westmauer, Trader 3 + 4 vor dem Hauptgebäude, Trader 5 + 6 an der Ostmauer.
  - **Markierung über dem Fenster** mit festen Objekten (nicht aufhebbar), ca. 3 m hoch an der Front:
    1 roter Eimer, 2 grüne Trage, 3 orange Leitkegel, 4 rot-weißes Stoppschild, 5 Pfeilschild,
    6 Plastikeimer. Keine Fässer mehr, die man wegnehmen könnte.
  - Seemannskisten stellen die Trader selbst auf (bleiben so mit Inhalt erhalten).
  - **Eingang:** Der Trader baut selbst ein Tor mit Zahlenschloss (Trader-Rollen dürfen in der Bauverbotszone bauen).
  - **Zutritt:** Nur die Discord-Rolle des Ladens (Trader 1 … 6) und Admins. Der Bot meldet Fremde.
  - Zeigt ein Schaufenster zur Mauer statt zur Hofmitte: in `werkzeuge/safezone_bau.py`
    `LADEN_FRONT_KORREKTUR = 180` setzen bzw. mir Bescheid geben.
  - Ein Gitter vor dem Fenster gibt es in den Nasdara-Dateien nicht.
  - Liegengebliebenes verschwindet beim Restart, es häuft sich also nichts an.
- **Keine Zombies:** Zombie-Zonen im Umkreis von 300 m entfernt (`env/zombie_territories.xml`).
- **Bot-Strafe:** Wer in der Safezone jemanden **tötet**, wird **30 Tage gebannt** (Notwehr ausgenommen).
  Im Bot: `/admin-safezone 8725 8265 75`.
- Eingetragen in `cfggameplay.json` unter `objectSpawnersArr`.
- **Bauverbot (Bot):** Im Umkreis von 150 m dürfen nur Spieler mit der Discord-Rolle **Trader**
  oder **Admin** bauen. Andere werden gemeldet und verwarnt. Im Bot: `/admin-bauverbot 8725 8265 150`.

### Sonstiges (`cfggameplay.json`)
- **Papierkarte zeigt einen Punkt an der eigenen Position** (`displayPlayerPosition` + `ignoreNavItemsOwnership`, Karte muss im Inventar sein, Kompass/GPS nicht nötig).
- **Ausdauer nur beim Springen/Klettern:** Sprinten, Schwimmen, Leitern, Nahkampf, Luftanhalten und
  Gewicht kosten keine Ausdauer mehr (`StaminaData`).
- `disableItemFalling` = true gegen einstürzende Bauten.
- Basisschaden unverändert (kommt später).

## Bitte nach dem ersten Start testen

1. **Startausrüstung:** Ist alles da (Turban, Messer, Pistole)? Wie viel Munition?
   Tragen alle Kameez, Shalwar und Sandalen? Bleibt beim eigenen Charakter das Gesicht?
2. **Karte:** Zeigt die Papierkarte Nasdara und einen Punkt an deiner Position?
3. **Ausdauer:** Lange sprinten, sinkt die Ausdauer? Nur beim Springen/Klettern sollte sie sinken.
4. **Fahrzeuge:** Sind alle Teile dran? Liegen Kanister und Wasserflaschen im Kofferraum, und sind sie voll?
5. **Wachturm:** Testturm bauen, unterstes Stockwerk abbauen. Bleiben Nachbarbauten stehen?
6. **Spawns:** Ein paar Mal neu spawnen. Landet man immer im Gelände außerhalb von Orten?
   Liegt ein Spawn ungünstig (Berg, Wasser), Nummer aus `spawns_vorschau.png` melden.
7. **Safezone:** Zur Moschee laufen (x 8725 / z 8265). Steht sie sauber auf dem Boden, oder schwebt
   bzw. versinkt sie? Liegen Essen, Wasser und Erste Hilfe im Hof und lassen sich aufheben?
   Höhe falsch → Höhe von `/admin-position` (in der Hofmitte stehend) an mich schicken.
8. **Loot:** Nach 1–2 Stunden mal Militärgebiete in Gelb abgehen. Gibt es Plattenträger/Nachtsicht?

Wenn etwas fehlt oder der Server nicht startet: die Originaldatei zurückspielen und mir
den Fehler schicken.

Hinweis: Durch +50 % Loot braucht der Server nach dem Hochladen einige Neustarts, bis die Welt
richtig gefüllt ist.

## Werkzeuge

Im Ordner `werkzeuge/` liegen die Scripte, mit denen diese Dateien aus den Nitrado-Originalen
erzeugt wurden (`anpassen.py`, `startgear.py`, `spawns.py`, `safezone_bau.py`, `grundriss.py`). Sie werden auf dem Server nicht gebraucht.
