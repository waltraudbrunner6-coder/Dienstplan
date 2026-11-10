# V2 – tatsächliche Paketprüfungen

Stand 10.11.2026. Technischer Prüfbereich, **keine produktive V2-Freigabe**.
Alle Angaben nennen den tatsächlich geprüften Commit. Keine Linux-Prüfung wird
als nativer Windows-/Mac-Nachweis ausgegeben.

## Aktueller Code und Zugangssperre

Code/Testkorrektur bis `fa61c12` ist auf `feat/v2-implementation` gepusht.
Der letzte lokale Gesamtlauf bestand mit **330 Tests in 94,71 s**.
Ein weiterer nativer Lauf dieses Commits wurde erfolgreich angestoßen. Sein
Ergebnis konnte anschließend nicht mehr abgefragt werden: GitHub-API meldet
`401 Bad credentials`, `gh auth status` kennzeichnet `GH_TOKEN` als ungültig,
Git kann keine Anmeldung abrufen. Eine frische Status-/Verbindungsprüfung hat
dies bestätigt. Keine Zugangsdaten wurden umgangen oder im Chat angefordert.

Deshalb bleibt der letzte native Intel-Nachweis nach der Testkorrektur ausdrücklich
**unbestätigt**. Nach erneuerter GitHub-Verbindung zuerst den letzten Lauf für
`fa61c12` lesen, nicht nochmals ungeprüft neu implementieren oder Tests lockern.
Bei Fehlern konkrete Annotationen prüfen und korrigieren; erst danach den
Abschlussbericht pushen. Der externe Blob-Logspeicher ist zusätzlich mit HTTP 403
gesperrt; die reguläre GitHub-API konnte zuvor Mess- und Fehlerannotationen liefern.

## Bereits vollständig beobachtete native Läufe

- [42724231255](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42724231255),
  Commit `b358351`: alle drei Zielarchitekturen grün, damaliger 325-Test-Stand,
  gebaute Programme mit Legacy- und V2-Selbsttest.
- [42725140124](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42725140124),
  Commit `6527faf`: alle drei Zielarchitekturen grün, erweiterter 329-Test-Stand
  einschließlich gemeinsamer Zwölfer-Teaminstanzen.
- [42726096163](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42726096163),
  Commit `527d639`: Windows und ARM64 grün; Intel scheiterte im Zwei-Sekunden-
  Wunschzähltest an einem leeren Ergebnisbericht. Die Korrektur `fa61c12` verwendet
  einen gültigen Startplan und 10 s und fordert zusätzlich einen bewiesenen
  CP-Zielwert. Die fachliche Zählerwartung wurde nicht abgeschwächt. Separat
  geprüfte Zeitlimit-/Abbruchregeln bleiben erhalten.

## Gemessene native Größen des belegten Stands b358351

Diese Werte gehören ausschließlich zu Run `42724231255`, nicht zum noch nicht
abschließend kontrollierten Nachfolgelauf. Rohdaten samt Artefaktlinks:
[native-gepruefter-zwischenstand.json](../examples/v2/native-gepruefter-zwischenstand.json).

| Plattform / tatsächliches System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB |
| --- | --- | ---: | ---: | ---: |
| Windows-Runner 10.0.26100 | AMD64 / x64 | 240.715.491 | 229,56 | 82,80 |
| macOS Sequoia 15.8.2 | ARM64 | 180.674.901 | 172,31 | 60,72 |
| macOS Sequoia 15.7.9 | Intel x86_64 | 187.185.847 | 178,51 | 67,18 |

Python der nativen Läufe: 3.12.10. Paketprüfung belegt Wien-DST, tzdata 2026.6 /
IANA 2026f, CP-SAT/Prüfer, SQLite-Workspace, konsistentes ZIP und sichtbare Qt-Widgets.
Legacy-Selbsttest: 12 Personen/186 Zuteilungen; V2-Test: 12 Personen/8 Zuteilungen
im ausdrücklich synthetischen Vier-Termine-Datensatz. Die Zahl acht bedeutet
keinen vollständig besetzten betrieblichen Monatskalender.

## Aktuelles Linux-Paket

Programmstand `527d639`, Linux x86_64/Python 3.12.14: tatsächlich **293.991.514 Bytes
/ 280,37 MiB**, TAR.GZ **114.285.491 Bytes / 108,99 MiB**. Beide Paketselbsttests
bestanden. V2 lief mit `PYTHONTZPATH=""`; gebündelte Datei Europe/Vienna und
deutsche Qt-Basistranslation sind im Paket vorhanden. Ausgabe im lokalen
ignorierten Verzeichnis `dist-v2/`; keine Binärdateien im Git.

## Bewusst offene Nachweise

Die nativen Builds sind unsigniert; keine Notarisierung behauptet. Qt wurde auf
den jeweiligen nativen Runnern automatisiert/offscreen gestartet. Eine vollständige
manuelle Bedienabnahme auf Endgeräten und eine OS-weite Netzabschaltung wurden
nicht durchgeführt. S0/M0/E0/Q0 und synthetische Bestätigungen sind keine KV-/BV-,
Abrechnungs- oder Produktfreigabe. Weitere Grenzen: [Abnahmestatus](V2_ABNAHMESTATUS.md).

Nach wiederhergestelltem Zugang lässt sich ein abgeschlossener Lauf reproduzierbar
auslesen, ohne den externen Logspeicher zu benötigen:

```sh
python scripts/v2_native_report.py --run RUN_ID --output NEUER_BERICHT.json
```
