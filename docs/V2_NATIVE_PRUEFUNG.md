> Folgeversion 0.4.4 ergänzt die Monatsbestätigung trotz Abweichungen.
> Die folgenden Downloads dokumentieren noch 0.4.3; neue Nachweise folgen
> nach erfolgreichem nativem Prüflauf.

# Dienstplan 0.4.3 – direkte manuelle Zuordnung und Bedienprüfung

Stand 11.11.2026. Geprüfter Programm-/Testcommit **1ef36fe**. Windows x64, macOS Sequoia ARM64 und Intel: Testsuite, Paketbuild und die Prüfung des gebauten Programms erfolgreich.

[Prüflauf 42924260302](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42924260302). Rohdaten: `examples/v2/native-pruefung.json`; vorheriger 0.4.2-Nachweis: `examples/v2/native-0-4-2.json`. Nachfolgende reine Nachweiscommits ändern den geprüften Programm-/Testcode nicht.

## Aktuelle Downloads

- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42924260302/artifacts/13813586611)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42924260302/artifacts/13813493122)
- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42924260302/artifacts/13812938898)

Alte App schließen, neue Archive vollständig entpacken. Windows: vollständigen Dienstplan-Ordner behalten und darin die EXE öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges App-Bundle behalten. Im Fenster muss **Version 0.4.3 · Build 1ef36fe** stehen. Python und Terminal sind nicht erforderlich. Bestehende Monatsdatei weiterverwenden; keine Migration oder erneuter Import erforderlich.

## Korrekturen und Prüfumfang

- „Zuteilung ändern“ öffnet direkt die Personenauswahl. Manuelle Änderungen, Entfernen und Fixieren benötigen kein BK/WL-Wochenprofil; vorhandene Termine bleiben unverändert.
- Fixierungen werden bei einem bestätigten Personenwechsel übertragen bzw. beim Entfernen mit entfernt. Termin-/Personen-ID bestimmt ihre Identität, abweichende Metadaten erzeugen keine Doppelanlage. Gleiche Person oder Abbruch erhält Pause und bisherigen Stand.
- Explizite Wochenkonfiguration erhält vorhandene Zuteilungen. Optionale Datumswahl bleibt innerhalb der gewählten Quoten für die spätere automatische Planung frei.
- Dateikopie schützt vor Übernahme des falschen Standes hinter einer Vorschau und übernimmt keinen fremden Korrekturstapel als aktive Bearbeitung. Ursprünglicher Stapel bleibt in seiner Datenbank.
- Erneute Funktionsprüfung: normale Monatsoberfläche mit synthetischem Import, manuelle Änderungen, Speicherung, beide Exporte, Kopie/Öffnen, Monatsnavigation sowie bestehende Termin-, Import-, Vertrags-, Historien- und Solverprüfungen. Einzelheiten: `V2_BEDIENPRUEFUNG_0_4_3.md`.
- Lokal abschließender Gesamtlauf: **437 bestanden in 257,35 s**. Der verschärfte native Paket-Selbsttest führt im gebauten Programm zuordnen → fixieren → Person ändern → entfernen ohne Wochenprofil aus. `manual_assignment=true` ist auf allen drei Plattformen nachgewiesen.

## Tatsächlich gemessene Paketgrößen

| Plattform | Native Archivgröße | Entpacktes Programm |
| --- | ---: | ---: |
| Darwin x86_64 | 71,024,978 Bytes / 67.73 MiB | 187,820,588 Bytes / 179.12 MiB |
| Darwin arm64 | 64,246,490 Bytes / 61.27 MiB | 181,309,641 Bytes / 172.91 MiB |
| Windows AMD64 | 87,412,044 Bytes / 83.36 MiB | 241,345,464 Bytes / 230.16 MiB |

Die GitHub-Artifact-Hülle kann durch zusätzliche Kompression eine andere Downloadgröße haben. Plattform-/Pythonversionen und Bytewerte stehen im Rohbericht.

Automatisierte native Qt-Prüfung, keine vollständige manuelle Bedienabnahme jeder Eingabekombination. Pakete sind nicht signiert/notarisiert. Keine betriebliche Rechts-/Tariffreigabe durch synthetische Tests; offene Profile bleiben offen. Keine echte Benutzerdatenbank geöffnet oder migriert. Keine Lockerung der Solverregeln.
