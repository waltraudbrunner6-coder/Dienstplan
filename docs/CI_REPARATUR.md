# Reparatur des nativen Build-Workflows

Ausgangslauf: [Desktop-Pakete, Commit 630e545](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/38275869064).

## Ursachen und Änderungen

- **Baseline-Historie:** Der flache CI-Checkout enthielt den Originalcommit
  `e7e0fc5e319cc636ca95f0685b0728e5d535e1f8` nicht. `actions/checkout` lädt nun
  die vollständige Historie (`fetch-depth: 0`). Der Vergleich prüft den Commit
  und alle vier benötigten Dateien, bevor er den echten Originalsolver in einem
  temporären Paket ausführt. Fehler nennen den Git-Exitcode und dessen Meldung.
  Tests benötigen kein Netzwerk und ändern den Checkout nicht.
- **Fairness bei zwölf Personen:** Der Startplan brauchte auf Linux rund
  0,51 Sekunden, sein Budget bei acht Sekunden Gesamtlimit betrug nur
  0,48 Sekunden. Bei Ablauf ging der gesamte Fortschritt verloren. Langsamere
  Runner erhielten daher keinen brauchbaren Startpunkt für spätere Stufen.
  Vorbereitete Schichtdaten und personenspezifische Prüfungen beschleunigen den
  Aufbau; gültige Teilergebnisse bleiben bei Ablauf erhalten. Kandidaten werden
  anhand der vollständigen lexikografischen Zielfunktion gewählt, einschließlich
  Wunschgruppen und bestätigter Wunschhistorie. Allgemeine, regelgeprüfte Tausche
  gleich langer Dienste glätten den Startplan. Fixierungen und Randmonatsregeln
  bleiben verbindlich. Das Gesamtlimit bleibt acht Sekunden; die Initialisierung
  erhält höchstens 0,8 Sekunden beziehungsweise 12 % des Gesamtlimits.
- **Windows-Zeitlimit:** Ein reales Limit von 0,0001 Sekunden garantiert keinen
  bestimmten Kontrollfluss auf jeder Plattform. Null offene Plätze oder null
  Wunschverletzungen sind zudem ohne Suchlauf analytisch optimal. Eine kontrollierte
  Uhr prüft nun den Ablauf vor der ersten Stufe. Ein separater Test erzwingt
  Solverstatus UNKNOWN: der vollständige faire Startplan bleibt gültig, die beiden
  Nullziele sind bewiesen, Stunden-/Fairnessziele und globale Optimalität nicht.

Die Acht-Sekunden-Fairnessprüfung bleibt bestehen und schließt Personen mit null
Einsätzen ein. Ein zusätzlicher deterministischer Test prüft acht besondere
Einsätze bei acht verschiedenen Personen und tägliche Typanzahlen mit höchstens
einem Einsatz Unterschied, auch ohne CP-SAT-Fund. Ein gezielter Startzeitablauf
prüft den Erhalt des gültigen Teilplans. Keine Tests werden übersprungen oder
pauschal als erwartete Fehler behandelt.

## Lokale Nachweise

Linux x64, Python 3.12.14, OR-Tools 9.15.6755:

- Betroffene Tests bestanden; anschließend **150 Tests bestanden** in 59,55 Sekunden.
- Neues PyInstaller-Paket: **293.123.660 Bytes / 279,54 MiB** unkomprimiert;
  TAR.GZ **113.846.417 Bytes / 108,57 MiB**.
- Gebautes Programm mit `--self-test` in minimaler Prozessumgebung ohne
  Entwicklungsvenv erfolgreich: zwölf Personen, 186 besetzte Plätze,
  CSV/SQLite/Solver/Qt, Ausnahmen, kurzer Sonderdienst und Wunschhistorie.
- Die bestehenden fachlichen Regressionen für Freiwünsche, Speicherung,
  Ausnahmetage und kürzere besondere Schichten bleiben aktiv und bestanden.

## Native Prüfung

Der Workflow baut Windows x64, macOS Sequoia ARM64 und macOS Sequoia Intel getrennt.
Jeder Job führt die vollständigen Tests, PyInstaller, den Selbsttest des gebauten
Programms und den Upload des Archivs samt Größenbericht aus. Ein CI-Tag `v*` oder
`workflow_dispatch` startet diese Kette. Ein Tag für die CI-Prüfung veröffentlicht
keinen GitHub-Release.

Die lokalen Ergebnisse beweisen keine nativen Windows-/macOS-Builds. Der neue
Actions-Lauf und seine tatsächlich abgeschlossenen Job-/Artefaktzustände sind
gesondert zu prüfen; es gibt kein `continue-on-error`.
