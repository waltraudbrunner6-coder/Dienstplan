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

Der [erste reparierte Lauf für debd60a](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/38280109872)
bestand auf beiden Mac-Architekturen sämtliche Schritte einschließlich Paket-Selbsttest
und Upload. Auf Windows bestanden Tests und PyInstaller; der gebaute Selbsttest endete
nach einer Sekunde mit Exitcode 1, der Upload wurde daraufhin richtigerweise ausgelassen.
Die öffentliche Schrittübersicht belegt diesen Zustand; das genaue alte Fehlerprotokoll
war ohne freigegebene GitHub-API nicht abrufbar.

Dabei wurde eine konkrete Windows-Verpackungslücke festgestellt: OR-Tools 9.15
lädt seine DLLs aus einem dynamisch gebildeten Pfad `ortools/.libs`. Das geprüfte
Windows-Wheel enthält dort neun DLLs. Für Windows verwendet der Build nun
`--collect-binaries ortools`, das die Paketverzeichnisstruktur erhält.
Zusätzlich schreibt `--self-test --self-test-report DATEI` einen JSON-Nachweis
auch ohne Standardausgabe. Qt-Importe des Eintrittspunkts erfolgen erst nach
der Argumentauswertung; Importfehler des Selbsttests können so erfasst werden.
`scripts/check_package.py` verlangt sowohl Exitcode null als auch den vollständigen
Funktionsnachweis. Fehler werden mit Traceback als GitHub-Annotation veröffentlicht.
Ein fehlender Bericht oder eine nur teilweise Prüfung führt nicht zu einem grünen Job.

Die sechs ergänzten Regressionfälle prüfen Importfehler ohne Standardausgabe sowie
Erfolg, fehlerhaften Exitcode, fehlenden/fehlgeschlagenen/unvollständigen Nachweis.
Der bestehende Demo-Neustarttest verwendet weiterhin die echte Speicherung und
prüft unverändert den Erhalt von Name und fixierter Zuteilung. Nach dieser Ergänzung
bestanden **156 Tests** in **61,35 Sekunden** unter Linux.
Der neu gebaute Linux-Stand besteht auch die neue JSON-Paketprüfung in minimaler
Prozessumgebung: **293.129.999 Bytes / 279,55 MiB** unkomprimiert,
**113.847.440 Bytes / 108,57 MiB** TAR.GZ. Die native Jobübersicht enthält
den jeweils gemessenen Größenbericht und den bestandenen Funktionsnachweis.

Der Workflow baut Windows x64, macOS Sequoia ARM64 und macOS Sequoia Intel getrennt.
Jeder Job führt die vollständigen Tests, PyInstaller, den Selbsttest des gebauten
Programms und den Upload des Archivs samt Größenbericht aus. Ein CI-Tag `v*` oder
`workflow_dispatch` startet diese Kette. Ein Tag für die CI-Prüfung veröffentlicht
keinen GitHub-Release.

Die lokalen Ergebnisse beweisen keine nativen Windows-/macOS-Builds. Der neue
Actions-Lauf und seine tatsächlich abgeschlossenen Job-/Artefaktzustände sind
gesondert zu prüfen; es gibt kein `continue-on-error`.

## Weitere Absicherung der begrenzten Suchzeit

Der [Diagnoselauf für 001620a](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/38282851586)
bestand auf **allen drei** Zielplattformen Tests, Build, Programm-Selbsttest und
Upload. Damit ist auch die Windows-DLL-Ergänzung nativ geprüft. Ein vorheriger
Intel-Lauf hatte einen Testfehler ohne abrufbare Einzeldiagnose; die vollständige
JUnit-Fehlermeldung wird deshalb künftig unter Beibehaltung des pytest-Exitcodes
als öffentliche Actions-Annotation ausgegeben. Die Diagnosefunktion wurde lokal
mit einem echten, absichtlich fehlschlagenden temporären pytest-Fall geprüft.

Unabhängig davon ließ sich die verbleibende Zeitabhängigkeit der täglichen
Typverteilung lokal reproduzieren: bei kontrolliert dreifach beschleunigter
Ablaufuhr und entsprechend verkürzten Solverbudgets enthielt eine tägliche
Schichtgruppe vier bis sechs Einsätze statt vier bis fünf. Das reale ursprüngliche
Intel-Fehlerprotokoll war nicht verfügbar; dieser Versuch beansprucht keine
identische Runnergeschwindigkeit oder identischen damaligen Suchstand.

Die Tauschbewertung wird daher weiter beschleunigt. Bei gleicher bezahlter Dauer
erhält ein Tausch persönliche Stunden, Besetzung und Typsummen. Ohne berührte
Wünsche verändern sich nur vier personenbezogene Typterme. Deren exakte marginale
Kosten werden je Suchrunde vorbereitet, einschließlich bestätigter Sonderhistorie.
Bei berührten Wünschen bleibt die vollständige lexikografische Prüfung erforderlich;
vor Übernahme gilt immer dieselbe harte Regelprüfung einschließlich Fixierungen
und Randmonaten. Die Zielfunktion, Prioritäten und das Acht-Sekunden-Limit ändern
sich nicht. Die Initialisierung benötigte im lokalen Vergleich rund **0,20 Sekunden**;
mit dreifacher Ablaufuhr gelang anschließend die geforderte Verteilung.

Zwei neue Tests prüfen die allgemeine tägliche Tauschverbesserung mit unveränderten
Fixierungen, die Ablehnung bei zusätzlicher Wunschverletzung und den Ausgleich
bestätigter Historie bei gleich langen besonderen/täglichen Diensten. CP-Modell
und Nachbewertung bleiben kongruent. Der gesamte aktuelle Stand besteht
**158 Tests in 59,86 Sekunden** unter Linux; sein nativer Workflow muss für
diesen abschließenden Stand erneut vollständig geprüft werden.
Auch das abschließende Linux-Paket besteht `scripts/check_package.py` ohne
Entwicklungsvenv: **293.133.947 Bytes / 279,55 MiB** unkomprimiert und
**113.851.127 Bytes / 108,58 MiB** TAR.GZ, mit zwölf Personen und 186 Plätzen.
