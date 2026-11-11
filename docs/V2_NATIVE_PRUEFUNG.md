# Dienstplan 0.5.1 – Weiterplanung mit genehmigten Freiwünschen

Programm-/Teststand **bed7df9**. Windows x64, macOS Sequoia Apple Silicon und
Intel: vollständige Testsuite, Paketbau und Prüfung der gebauten Anwendung erfolgreich.

[Prüflauf 43111660919](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43111660919). Rohdaten:
`examples/v2/native-pruefung.json`; 0.5.0 ist unverändert unter
`examples/v2/native-0-5-0.json` archiviert. Nachfolgende reine Nachweiscommits
ändern den geprüften Programm-/Testcode nicht.

## Downloads und Start

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43111660919/artifacts/13897441039)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43111660919/artifacts/13896988801)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43111660919/artifacts/13896513344)

Alte App schließen und neue Archive vollständig entpacken. Der GitHub-Download
enthält das eigentliche ZIP/TAR.GZ und `build-report.json`; auch das innere Archiv
entpacken. Windows: vollständigen Dienstplan-Ordner behalten und darin die EXE
öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges App-Bundle
behalten. Im Fenster muss **Version 0.5.1 · Build bed7df9** stehen.

Bestehende Dienstplandatei öffnen und erneut „Dienstplan erstellen“ wählen.
Ein Neuimport oder eine neue Datenbank ist für diese Korrektur nicht erforderlich.
Keine Schemaänderung, keine Migration; gespeicherte Genehmigungen und gültige
Fixierungen werden weiterverwendet. Python und Terminal sind nicht erforderlich.

## Behobener Dezemberfehler

Die vorbereitete Dezemberdatei enthält acht fixierte Dienste und zwölf
Donnerstags-Freiwünsche, deren Abweichung ausdrücklich zugelassen wurde. Die
strenge Kandidatenprüfung behandelte diese Wunschhinweise fälschlich als harte
Konflikte für alle Personen und Daten. Dadurch fehlten gültige Kandidaten;
anschließend erschien die pauschale Fehlermeldung zur manuellen Fixierung.

- Genau zugeordnete genehmigte Wunsch-Konfigurationshinweise verhindern keine
  automatische Weiterplanung mehr. Beide gespeicherten Zustimmungsflags sind nötig.
  Die Wünsche bleiben aktive weiche Optimierungsziele.
- Der unabhängige strenge Prüfer, Stunden-/Wunschstatistik und bestätigte Historie
  bleiben erhalten. Urlaub, Beschäftigung, Berechtigungen, Ruhe, Pausen und alle
  anderen Dienstregeln werden nicht pauschal aufgehoben.
- Vorschau, Bewertung, Verbesserung und Übernahme verwenden dieselbe enge
  Planungssicht. Gültiges manuelles Bearbeiten/Speichern bewahrt die Genehmigung
  ohne erneute Bestätigung. Ein Vorschlag ersetzt den alten Plan erst nach Übernahme.
- Tatsächliche Fixierungskonflikte nennen Person, Datum, Dienst und Ursache;
  Ruheabstände erscheinen in Stunden. Zeitlimit oder Abbruch werden nicht als
  nachgewiesene Unmöglichkeit ausgegeben. Ein erfolgloser Vorschlag löscht keinen Plan.
- Exporte enthalten strenge Prüfmeldungen sowie `accepted_wish_exceptions` und
  kennzeichnen die Bewertung unter genehmigten Freiwunschvorgaben. Kein
  uneingeschränkter Optimalitätsnachweis bei solchen Ausnahmen.

## Tatsächliche Prüfungen

Lokale vollständige Regression: **566 Tests bestanden in 289,47 s** mit
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q --disable-warnings --maxfail=3`.
Alle drei nativen Jobs führten die vollständige Testsuite, Paketbau und den
Selbsttest der tatsächlich gebauten Anwendung erfolgreich aus.

Neu verpflichtend ist **`approved_wish_planning=true`**: CP-SAT-Berechnung mit
vorhandener gültiger Fixierung und genehmigtem Donnerstagwunsch, tatsächliche
Qt-Vorschau/Übernahme, SQLite und Export mit nachvollziehbarem Ausnahmehinweis.
Die übrigen Paketnachweise einschließlich `leave_calendar`, `manual_assignment`,
Offline-Zeitzonenfallback, Solver und Exporte sind ebenfalls bestanden.

Zusätzliche Regressionen prüfen acht gültige Locks und zwölf genehmigte Wünsche,
fehlende Zustimmung, echte Urlaubs-/Berechtigungs-/Ruhekonflikte, konkreten
Fixierungshinweis, echten Hintergrund-Worker, Speichern/Wiederöffnen und Zeitlimit
mit unverändertem bisherigen Plan. Ausschließlich synthetische Prüfdaten; keine
privaten Originalzeilen in Tests und keine echte Benutzerdatenbank verändert.

## Tatsächlich gemessene Paketgrößen

| Plattform | Natives Archiv | Entpacktes Programm |
| --- | ---: | ---: |
| macOS Sequoia / Apple Silicon | 64.357.593 Bytes / 61,38 MiB | 181.445.785 Bytes / 173,04 MiB |
| macOS Sequoia / Intel | 71.136.390 Bytes / 67,84 MiB | 187.956.732 Bytes / 179,25 MiB |
| Windows x64 | 87.516.917 Bytes / 83,46 MiB | 241.481.315 Bytes / 230,29 MiB |

Die GitHub-Artifact-Hülle kann wegen zusätzlicher Kompression eine andere Größe
haben. Plattform-/Pythonversionen, Bytewerte und Selbsttestdetails stehen im
Rohbericht. Pakete sind nicht signiert/notarisiert. Automatisierte native
Qt-Prüfung, keine vollständige manuelle Abnahme jeder Eingabekombination.

Bestehende offene Fachfragen sind weiterhin in [Informationsprüfung](V2_INFO_AUDIT.md)
und [offenen Fragen](V2_OFFENE_FRAGEN.md) begrenzt benannt. Diese Fehlerkorrektur ist
kein pauschaler Nachweis aller 125 Produktabnahmen oder betrieblicher Rechts-/Tarifprofile.
