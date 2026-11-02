# GER Broken-LegZ PVP – angepasste Serverdateien (Nasdara)

## Hochladen

**Vorher:** Server stoppen und von jeder Originaldatei eine Sicherung herunterladen.

Im Nitrado-Dateibrowser unter `dayzps_missions/dayzOffline.nasdara/`:

| Datei aus dieser ZIP | Ziel auf dem Server |
|---|---|
| `db/types.xml` | `dayzOffline.nasdara/db/types.xml` |
| `db/events.xml` | `dayzOffline.nasdara/db/events.xml` |
| `db/globals.xml` | `dayzOffline.nasdara/db/globals.xml` |
| `cfgspawnabletypes.xml` | `dayzOffline.nasdara/cfgspawnabletypes.xml` |
| `cfggameplay.json` | `dayzOffline.nasdara/cfggameplay.json` |
| `custom/startgear.json` | `dayzOffline.nasdara/custom/startgear.json` (neu) |

Danach im Webinterface prüfen, dass **cfggameplay.json aktiviert** ist, und den Server starten.

## Was geändert wurde

| Wunsch | Änderung |
|---|---|
| Loot +10 % | `types.xml`: nominal/min aller Items × 1,1 (gesamt 25.080 → 27.672 Items, +10,3 %). Sehr seltene Items mit 1–4 Stück bleiben gleich, damit z. B. NVGs nicht doppelt so oft spawnen. |
| Fahrzeuge +50 % | `events.xml`: alle aktiven Fahrzeug-Events × 1,5 (z. B. Sedan 8 → 12, Motorräder 30 → 45, LKW 6 → 9). Spawnpunkte reichen überall. |
| Fahrzeuge voll ausgestattet | `cfgspawnabletypes.xml`: alle Anbauteile (Räder, Türen, Batterie, Kühler, Zündkerze, Licht) bei 26 Fahrzeugtypen auf 100 %. |
| Mehr Zombies | `events.xml`: Infected-Events +30 %, `globals.xml`: ZombieMaxCount 1000 → 1300. |
| Startausrüstung | `custom/startgear.json`: Kleidung, Umhängetasche, 2× Essen (Cracker, Salzstangen), 3× Trinken (Wasserflasche, 2 Dosen), Verband, Knicklicht, Papierkarte, 1 zufällige Pistole ohne Magazin + etwas Munition. Pistolen: Makarov, CZ75, Glock 19, P1, FNX45, Colt 1911, MKII. |
| Karte zeigt Position | `cfggameplay.json`: `displayPlayerPosition` = true (nur mit Karte im Inventar). |
| Einstürzende Bauten | `cfggameplay.json`: `disableItemFalling` = true. Bitte testen, siehe unten. |

## Bitte nach dem ersten Start testen

1. **Startausrüstung:** Neuen Charakter spawnen. Ist alles da? Wie viel Munition?
2. **Karte:** Papierkarte öffnen. Zeigt sie Nasdara und deine Position?
3. **Fahrzeuge:** Ein paar Fahrzeuge anschauen. Sind alle Teile dran?
4. **Wachturm:** Einen Testturm bauen und das unterste Stockwerk abbauen. Bleiben Nachbarbauten stehen?

Wenn etwas fehlt oder der Server nicht startet: die Originaldatei zurückspielen und mir
den Fehler schicken.
