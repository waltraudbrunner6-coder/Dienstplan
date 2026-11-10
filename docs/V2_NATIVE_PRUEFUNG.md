# V2 – tatsächliche native Paketprüfung

Stand 10.11.2026. **Technischer Prüfbereich, keine produktive V2-Freigabe.**

## Geprüfter Stand und Pakete

[Run 42727609885](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42727609885) des Commits `fa61c12` ist vollständig
**erfolgreich**. Alle drei nativen Jobs führten die vollständige damalige
330-Test-Suite, den Paketbuild sowie den Legacy- und V2-Paketselbsttest erfolgreich
aus. Nachfolgende Dokumentationscommits ändern diesen Programm-/Testcode nicht.

Download der tatsächlich erzeugten Prüfartefakte:

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42727609885/artifacts/13723920072)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42727609885/artifacts/13723796238)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42727609885/artifacts/13722788520)

Die Archive enthalten eigenständig startbare Programme; Python/Terminal werden
für die Nutzung nicht benötigt. Vollständigen Paketordner beziehungsweise das
macOS-App-Bundle behalten. Native Rohdaten einschließlich OS/Architektur,
Bytegrößen und Selbsttestergebnissen: [native-pruefung.json](../examples/v2/native-pruefung.json).

| Tatsächliches System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB | Paketprüfung |
| --- | --- | ---: | ---: | ---: | --- |
| macOS Sequoia 15.8.2 | arm64 | 180.680.151 | 172,31 | 60,72 | bestanden |
| macOS Sequoia 15.7.9 | x86_64 | 187.191.097 | 178,52 | 67,18 | bestanden |
| Windows-Runner 10.0.26100 | AMD64 | 240.720.802 | 229,57 | 82,81 | bestanden |

Python der nativen Läufe: 3.12.10. Die Paketprüfung belegt Wien-DST, gebündeltes
tzdata 2026.6 / IANA 2026f, CP-SAT/Prüfer, SQLite-Workspace, konsistentes ZIP und
sichtbare Qt-Widgets. Legacy-Selbsttest: zwölf Personen/186 Zuteilungen; V2-Test:
zwölf Personen/acht Zuteilungen im ausdrücklich synthetischen Vier-Termine-
Datensatz. Acht Zuteilungen bedeuten keinen vollständig besetzten Betriebsmonat.

## Zusätzlich gebautes Linux-Paket

Programmstand `527d639`, Linux x86_64/Python 3.12.14: tatsächlich **293.991.514 Bytes
/ 280,37 MiB**, TAR.GZ **114.285.491 Bytes / 108,99 MiB**. Beide Paketselbsttests
bestanden. V2 lief mit `PYTHONTZPATH=""`; gebündelte Datei Europe/Vienna und deutsche
Qt-Basistranslation sind vorhanden. Lokale Ausgabe: ignoriertes `dist-v2/`, keine
Binärdateien im Git. Linux ersetzt keinen der oben tatsächlich ausgeführten nativen
Windows-/Mac-Nachweise.

## Reparaturen und Grenzen

Der erste Windows-Lauf scheiterte am Exportflush: der Handle wird jetzt schreibbar
geöffnet, wie Windows fsync/_commit es benötigt. Eine plattformübergreifende
Regression erzwingt das. Der später einmal auf Intel gescheiterte Wunschzähltest
unterstellte einen Fund innerhalb von zwei Sekunden. Er verwendet nun einen gültigen
Startplan/10 s und verlangt zusätzlich einen bewiesenen CP-Zielwert. Die fachliche
Zählerwartung und kontrollierte Abbruch-/Zeitlimittests wurden nicht abgeschwächt.
Der oben verlinkte letzte Lauf prüft beide Korrekturen auf allen drei Architekturen.
Frühere Messdaten bleiben separat in
[native-gepruefter-zwischenstand.json](../examples/v2/native-gepruefter-zwischenstand.json) erhalten.

Die Builds sind **unsigniert**, keine Notarisierung behauptet. Qt wurde auf den
jeweiligen nativen Runnern automatisiert/offscreen gestartet. Vollständige manuelle
Bedienabnahme auf Endgeräten und OS-weite Netzabschaltung wurden nicht durchgeführt.
S0/M0/E0/Q0 und synthetische Bestätigungen sind keine KV-/BV-, Abrechnungs- oder
Produktfreigabe. Weitere Grenzen: [Abnahmestatus](V2_ABNAHMESTATUS.md).

Der zwischenzeitliche GitHub-Anmeldeausfall (`401 Bad credentials`) war vorübergehend;
frische Verbindungen erlaubten danach wieder Push und Prüfung. Der externe Blob-
Logspeicher blieb mit HTTP 403 gesperrt. Mess- und Fehlerannotationen wurden regulär
über die erlaubte GitHub-API gelesen, ohne die Netzbeschränkung zu umgehen.

Ein abgeschlossener Lauf lässt sich ohne externen Logdownload reproduzierbar erfassen:

```sh
python scripts/v2_native_report.py --run RUN_ID --output NEUER_BERICHT.json
```
