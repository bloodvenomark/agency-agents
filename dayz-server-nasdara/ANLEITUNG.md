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
| `custom/startgear.json` | `dayzOffline.nasdara/custom/startgear.json` (neu) |

Danach im Webinterface prüfen, dass **cfggameplay.json aktiviert** ist, und den Server starten.

## Was geändert wurde

### Loot (`db/types.xml`)
- **+50 %** für alle Items (gesamt 25.080 → 37.738). Einzelstücke (nominal 1, z. B. M4A1, FAL, AUG)
  bleiben einzeln, sonst gäbe es sie doppelt so oft.
- **Plattenträger (Weste, Holster, Taschen) und Nachtsicht (Brille, Kopfband)** spawnen jetzt
  allgemein in **Tier 3 (gelb)** in Militärgebieten und weiterhin in Tier 4.
- **M4A1: ca. 1 pro Restart in Tier 3 (gelb).** Es liegt immer genau 1 M4A1 auf der Karte, meist in
  gelben Militärgebieten. Nach dem Looten kommt die nächste erst nach 4 Stunden. Liegt sie
  ungelootet 4 Stunden herum, verschwindet sie und spawnt woanders neu.
- **Rest von Tier 4 bleibt Tier 4.** Etwa 10 % davon sind zusätzlich in Tier 3 möglich:
  AK-Schalldämpfer, CMAG-40er-Magazin, STANAG-60er-Magazin.
- **Grüne Gebiete (Tier 1):** Kein Tier-4-Item wurde dort freigegeben.
- **Loot-Respawn höchstens 15 Minuten:** 112 Items (vor allem Waffen und seltene Sachen) hatten
  30 Minuten bis 24 Stunden Wartezeit, jetzt 15 Minuten. Alle anderen respawnen wie bisher sofort
  bzw. schneller. Ausnahme: M4A1 (1 pro Restart).
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
**Sandalen**. Dazu Umhängetasche, 2× Essen (Cracker, Salzstangen),
3× Trinken (Wasserflasche, 2 Dosen), Verband, **Schiene**, Knicklicht, Papierkarte,
1 zufälliges **Messer**, 1 zufällige Pistole **ohne Magazin** mit etwas Munition.
- Pistolen: Makarov, CZ75, Glock 19, P1, FNX45, Colt 1911, MKII. Kein Revolver.
- Messer: Küchenmesser, Steakmesser, Jagdmesser, Kampfmesser, Kukri, Fange-Messer, Dönermesser.

**Eigener Charakter:** Aussehen (Gesicht, Körper) bleibt erhalten, die Kleidung ist aber für alle
die kartentypische Startkleidung.

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
6. **Loot:** Nach 1–2 Stunden mal Militärgebiete in Gelb abgehen. Gibt es Plattenträger/Nachtsicht?

Wenn etwas fehlt oder der Server nicht startet: die Originaldatei zurückspielen und mir
den Fehler schicken.

Hinweis: Durch +50 % Loot braucht der Server nach dem Hochladen einige Neustarts, bis die Welt
richtig gefüllt ist.
