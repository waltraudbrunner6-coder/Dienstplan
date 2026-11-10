# Dienstplan 0.4.2 – Terminänderungen ohne Planverlust

Stand 10.11.2026. Programm-/Testcommit **304f3e1**. Alle drei nativen Ziele haben Testsuite, Paketbuild und die Prüfung des gebauten Programms erfolgreich abgeschlossen.

[Prüflauf 42917710392](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42917710392). Rohdaten: `examples/v2/native-pruefung.json`. Der vorige 0.4.1-Nachweis bleibt unter `examples/v2/native-0-4-1.json` erhalten. Nachfolgende reine Dokumentationscommits ändern diesen Programm-/Testcode nicht.

## Downloads

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42917710392/artifacts/13810187585)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42917710392/artifacts/13810034153)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42917710392/artifacts/13809214082)

Archive vollständig entpacken. Windows: vollständigen Dienstplan-Ordner behalten und darin die EXE öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges App-Bundle behalten. Im Fenster muss **Version 0.4.2 · Build 304f3e1** stehen. Python und Terminal werden nicht benötigt.

## Fehlerkorrektur und Wiederaufnahme

- Termin entfernen: nur diesen Termin, seine Zuteilungen und Fixierungen entfernen; alle übrigen Dienste erhalten. Die Änderung wird vor der Anzeige atomar gespeichert.
- Termin ergänzen: ebenfalls kein Verwerfen des restlichen Plans. Bestehende Regelprüfung und ausdrückliche Übersteuerung bleiben erhalten.
- Reimport: Fixierungen eindeutig nach Termin und Person zuordnen. Originalpausen wiederverwenden; keine Doppelanlage durch abweichende Pausen-/Override-Objekte.
- Nach dem alten Löschfehler: vorhandene Monatsdatei öffnen. Falls der Plan noch leer ist, ursprünglichen Novemberplan erneut importieren. Erhaltene Fixierungen werden in der Vorschau ausdrücklich als wiederhergestellt ausgewiesen. Regelverletzungen wie zuvor bestätigen; keine neue Datenbank erforderlich.
- „Datei kopieren“ heißt eindeutig, was vorher „Neue Datei“ bedeutete: bestehender Arbeitsstand mit Fixierungen in einer separaten Datei, kein leeres Zurücksetzen.

## Prüfungen und gemessene Größen

Lokal abschließend **418 Tests bestanden in 152,68 s**. Neue synthetische Regressionen decken den früher geleerten Zustand, Reimport, Dateikopie, Terminergänzung/-entfernung, Erhalt der übrigen Dienste, Abbruch und Schreibfehler sowie Speicherung/Neustart ab. Domain-Duplikatschutz und Solverregeln bleiben unverändert streng.

| Plattform | Native Archivgröße | Entpacktes Programm |
| --- | ---: | ---: |
| Darwin x86_64 | 71,018,197 Bytes / 67.73 MiB | 187,807,718 Bytes / 179.11 MiB |
| Darwin arm64 | 64,243,794 Bytes / 61.27 MiB | 181,296,771 Bytes / 172.90 MiB |
| Windows AMD64 | 87,404,516 Bytes / 83.36 MiB | 241,332,732 Bytes / 230.15 MiB |

Die GitHub-Artifact-Hülle kann durch zusätzliche Kompression eine andere Downloadgröße haben. Alle Builds: Python 3.12.10; Windows 10.0.26100, macOS Sequoia 15.8.2 (ARM64) und 15.7.9 (Intel).

Automatisierte native Qt-Prüfung, keine vollständige manuelle Bedienabnahme. Pakete sind nicht signiert/notarisiert. Keine Rechts-/Tariffreigabe durch synthetische Tests. Keine echte Benutzerdatenbank geöffnet oder migriert. Bestehende Monatsdateien bleiben lesbar.

Die Regelübersteuerung aus 0.4.1 sowie Tabellenimport und Exporte bleiben enthalten; unbekannte IDs, undefinierte Dienstzeiten und beschädigte Daten sind weiterhin zu korrigieren. Bedienung: `V2_BEDIENUNG.md` und `TABELLENIMPORT.md`.
