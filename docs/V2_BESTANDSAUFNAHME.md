# V2 – Bestandsaufnahme, Etappe A

Aktueller Implementierungs- und Prüfstand: [Fortschritt](V2_FORTSCHRITT.md),
[Zuordnung aller 125 Abnahmefälle](V2_ABNAHMESTATUS.md) und
[Bedienung des technischen Prüfbereichs](V2_BEDIENUNG.md). Die nachfolgende
Etappe-A-Spezifikation bleibt die fachliche Grundlage; Testprofile ersetzen sie nicht.

Stand: 09.11.2026. Geprüfte Basis: `eae8ed882fb597c8f82fe92a6aeca247ffe9c0e1`,
identisch mit dem beim Audit abgefragten Remote-`main`. Arbeitsbranch:
`docs/v2-etappe-a`. Vor Arbeitsbeginn war der Arbeitsstand sauber.
Im Checkout und seinen übergeordneten Projektverzeichnissen wurde keine `AGENTS.md`
gefunden. Vorhandene Quellen und Tests bleiben unverändert. Dieser Auftrag liefert
die Spezifikation für **Produktversion 2**; die bestehende Produktversion **0.2.0**
und ihr **SQLite-Schema 2** sind davon zu unterscheiden.

## Gelesener Bestand und Entscheidung

| Bereich / Quelle | Tatsächlicher Befund | V2-Entscheidung |
| --- | --- | --- |
| [README](../README.md), [bisherige Spezifikation](SPEZIFIKATION.md) | Deutsche Offline-Anwendung, feste vier Schichten; keine Ist-Zeiterfassung | Offline/Desktop und Prognosekennzeichnung behalten; alte Spezifikation als Legacy dokumentieren |
| [model.py](../dienstplan/model.py): `Employee` | Eine Wochenstundenzahl und zwei Minutensalden, `E` ohne Eingabe gleich `B`; keine Beschäftigungs- oder Berechtigungszeiträume | Stabile Personen-IDs erhalten; Vertrags-/Beschäftigungshistorie, Berechtigungen und neuer Monatsstandard `E=0` ergänzen |
| `MonthData.validate`, `generate_shifts` | Erzwingen genau drei tägliche und eine wöchentliche Schicht; Ausnahmen nur tägliche Termin-IDs | Für V2 durch Katalog, Veranstaltung, Bedarf, Varianten und Quoten ersetzen; Legacy-Generator behalten |
| `ShiftType`, `ShiftOccurrence`, `Assignment` | Ein Start-/Endintervall, numerischer Pausenabzug, einfacher Zuteilungsbezug | Zusammengesetzte Blöcke mit echten Pausen und Arbeitsabschnitten neu modellieren |
| `Blocker`, `validate_blockers` | P1/P2, höchstens 24 h je Eintrag, maximal vier eindeutige P1 pro betroffenem Monat | Alte Sperren als Legacy-Sperren erhalten; Urlaub, Gutschrifttage und Freiwünsche getrennt modellieren |
| [planner.py](../dienstplan/planner.py): `validate_assignments`, `_add_rules` | Getrennte Ergebnisprüfung und CP-Bedingungen für Überlappung, optionale Ruhe-, Tages-/Wochen- und Arbeitstagsgrenzen; tatsächliche Anwesenheit über Mitternacht | Muster behalten, V2-Prüfer und V2-Constraint-Compiler getrennt neu erstellen; neue Wochenend-/Ein-Block-Regeln fehlen |
| `paid_segments`, `_attendance_days` | Anwesenheit inklusive Mitternachtsanteil; bezahltes Ende rechnerisch nach vorne gezogen, Pause damit am Schichtende | Anwesenheit, tatsächliche Arbeit, Pause und Gutschrift trennen; Abzugsalgorithmus nicht übernehmen |
| [hours.py](../dienstplan/hours.py) | `W × Monatstage / 7`, einmal kaufmännisch auf Minuten gerundet; `S+E−B`; negative Arbeitsziele werden abgelehnt | Dezimal-/Bruchrechnung behalten, zeitabhängiges Soll und Gutschriften hinzufügen; negatives Rohziel als Überdeckung erklären |
| [optimization.py](../dienstplan/optimization.py), `_ObjectiveBuilder` | Lexikografische Besetzung/P2-Gruppen/Belastung/Stundenmaximum; dann gemeinsame Quadratsumme mit Gewichten 10000/1/4/8 | Stufenmechanik, warmen Start und geprüfte Verbesserungen behalten; konkrete Gewichtung und pauschale Vertragsanteile ersetzen |
| [wishes.py](../dienstplan/wishes.py) | Stabile Zeitraumsschlüssel, einmalige Verletzung und historische Mengenvereinigung; bestätigter P2-Snapshot | Identitäts-/Bestätigungsmuster behalten; Wünsche über mehrere Tage und Korrekturstatus erweitern; alte Gruppenbevorzugung nicht automatisch als V2-Regel übernehmen |
| [storage.py](../dienstplan/storage.py) | SQLite `user_version=2`; `months(month_key,payload)` als JSON, globale `blockers`; WAL, FK-Option, Transaktionen; Schutz bestätigter Pläne | SQLite behalten; neuer, versionierter V2-Bereich plus Legacy-Leseadapter; keine Umdeutung alter Datensätze |
| `Store.history`, `wish_history`, `boundary` | Bestätigte frühere Sonderanteile/Wunschschlüssel; Randdaten aus allen gespeicherten anderen Monaten, auch Entwürfen; unbekannte Zukunft ist nicht modelliert | Bestätigte Historie mit damaligen Anteilen behalten; getrennte V2-Zeitmengenhistorie und explizite Randdatenabdeckung einführen |
| [csvio.py](../dienstplan/csvio.py) | UTF-8/BOM, Komma/Semikolon, Vorschau, Duplikate; Import speichert nicht selbst; atomarer Ersatz je Exportdatei | Parser-/Dateimuster wiederverwenden; V2-Typen, Bereiche und Korrekturvormerkung ergänzen; gesamtes Exportpaket versionieren |
| [ui.py](../dienstplan/ui.py) | Feste vier Tabellenzeilen und vier Teamfelder; Monatserstellung kopiert `E=B`; Auswahl jeder Person für jeden Dienst; `QThread`/Abbruch/Übernahmeabfrage und Sofortprüfung | Qt/Worker-/Übernahmemuster behalten; dynamische Fachformulare, Kalender und gefilterte Personenauswahl neu aufbauen |
| [Build](../scripts/build.py), [Workflow](../.github/workflows/build.yml) | PyInstaller onedir/windowed, Windows-OR-Tools-DLLs, getrennte native Matrix, voller Checkout, Tests, Paket-Selbsttest und Artefakte | Behalten; später IANA-Zeitzonendaten und V2-Demos/Prüfbericht mit paketieren |

## Besonders wichtige Grenzen

- Die alte Schichtprüfung erlaubt mehrere getrennte, nicht überlappende Dienste
  desselben Startdatums, wenn andere aktivierte Regeln sie zulassen. Eine kleine
  Auditprobe mit 10:00–12:00 und 16:00–00:00 sowie ausgeschalteter Ruhezeit bestätigt
  dies. Das ist nach den alten Regeln zulässig, nach V2 unzulässig.
- Alle Personen sind im bisherigen CP-Modell für alle Schichttypen Kandidaten.
  Arbeitsverhältnisse, Führerschein und operative Berechtigungen existieren nicht.
- Eine weitere Probe bestätigt: P2 am Donnerstag wird derzeit angenommen;
  der fünfte ganztägige P1-Eintrag wird abgelehnt. Für V2-Urlaub wäre das falsch.
- Es existieren weder Urlaubsentgelt/Gutschrifttage noch Feiertags-/Nacht-/Reserve-
  profile, echte Pausenpositionen, freie Wochenendquoten oder Veranstaltungsanteile.
- `datetime` ist absichtlich zeitzonenlos. `ShiftType.validate`/`Blocker.validate`
  weisen Zeitzonen sogar zurück. Nur `tzinfo` nachzurüsten würde die alten
  Differenz-/Tagesrechnungen deshalb nicht zuverlässig korrigieren.
- Es gibt eine einzige aggregierte Sonderdiensthistorie. Die damaligen Wochenstunden
  bleiben im Monat erhalten; daraus werden historische Sollanteile ermittelt.
  Daraus darf weder BK-/WL- noch Zulagenhistorie abgeleitet werden.
- Globale Sperren sind **kein vollständiger historischer Eingabesnapshot**.
  Bestätigte P2-Statistiken sind eingefroren, Kommentare und allgemeine Sperrstände
  aber nicht sämtlich historisiert. Migration muss den am Stichtag verfügbaren
  Sperrstand sichern und fehlende frühere Information ausdrücklich kennzeichnen.
- Einzeln atomare CSV-Exporte sind noch kein gemeinsam atomarer Export eines
  unveränderlichen Planstands. Ebenso ersetzt der vorhandene Bestätigungsschutz
  noch keine vollständige, unveränderliche Revision mit Regel-/Quellenprofilen.

## Aktuell ausgeführte Prüfungen

Ausführung ausschließlich unter Linux x86_64, Python 3.12.14, Qt/PySide6-Essentials
6.12.0, OR-Tools 9.15.6755, pytest 9.1.1. Installation aus den vorhandenen
`requirements-lock.txt` und `requirements-dev.txt` in einer lokalen `.venv`;
keine Abhängigkeitsdatei geändert.

```sh
QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/dienstplan-v2-qt-cache \
  .venv/bin/python scripts/run_tests.py
QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/dienstplan-v2-qt-cache \
  .venv/bin/python -m dienstplan --self-test \
  --self-test-report /tmp/dienstplan-v2-bestand-selbsttest.json
```

Ergebnis: **158 bestanden in 63,11 Sekunden**, keine übersprungenen oder als
erwartet fehlschlagend markierten Fälle. JUnit: `build/test-results.xml`.
Selbsttest ebenfalls bestanden: zwölf Personen, 186 Zuteilungen, Status `feasible`,
CSV/SQLite/Solver/Qt, Ausnahmetage, kurzer Sonderdienst und Wunschhistorie.
`feasible` bedeutet ausdrücklich keinen vollständigen Optimalitätsnachweis.

Relevante bestehende Regressionen: `test_hours_model.py`, `test_planner.py`,
`test_optimization.py`, `test_cp_objectives.py`, `test_storage_csv.py`,
`test_wish_history.py`, `test_fixtures_v2.py`, `test_ui.py`, `test_ui_v2.py`,
`test_end_to_end.py`, `test_entry.py` und `test_package_check.py`.
Die Dateien mit `_v2` im Namen betreffen frühere Erweiterungen der Version 0.2,
**nicht** die hier spezifizierte Produktversion 2.

`test_end_to_end.py` unterbindet Netzwerkverbindungen während der lokalen Kette.
`test_version_one_migration_preserves_payload_and_decimal_hours` erzeugt eine
eigene Testdatenbank mit Schema 1, prüft Schema 2 und unveränderten JSON-Payload,
Kennungen und Dezimalstunden. Dies belegt nicht bereits die zukünftige V2-Migration.
Alle aktuellen Speicher-/Migrationsprüfungen benutzen Testdatenbanken bzw.
temporäre Dateien; eine echte Benutzerdatenbank wurde nicht geöffnet.

Die native Matrix ist gelesen; in diesem Auftrag wurden **keine neuen Windows-
oder macOS-Builds ausgeführt**. Der historisch erfolgreiche
[Lauf für die Auditbasis](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/38283999558)
ist aus dem bisherigen Projektverlauf bekannt, kein neuer Plattformnachweis.

## Referenzdaten und Recherchegrenzen

Vorhanden sind fiktive Oktober–Dezember-2026-Exporte und der alte Novembervergleich
unter `examples/`. Ein vollständiger anonymisierter Jännerfall mit 1294 Bedarfs-
und 1548 Zielstunden ist nicht vorhanden. Die im Auftrag genannten 27,58 → 26,08 h
werden deshalb nicht rekonstruiert oder als Optimum ausgegeben. Seine alten
Grenzen (15 h Ruhe, 7,5 Tagesstunden, 30 Wochenstunden, drei Arbeitstage) gelten
keinesfalls als V2-Standard.

Die vorgegebenen Primärquellen wurden am 09.11.2026 tatsächlich angefragt:
VkA-Downloadseite und PDF, Caritas-Betriebsrat und USP. Alle vier Aufrufe scheiterten
am Netzwerkproxy mit `Tunnel connection failed: 403 Forbidden`. Die Domains sind
zur Freigabe vorgeschlagen; die Quelleninhalte wurden **nicht gelesen**. Daher
werden weder Tarifwerte noch Anwendbarkeit noch Paragrapheninhalte als recherchiert
behauptet. Die Fundstellen, Freigaben und Nacharbeiten stehen in
[Fachregeln](V2_FACHREGELN.md) und [offenen Fragen](V2_OFFENE_FRAGEN.md).

## Ergebnis und nächster Schritt

Python, PySide6/Qt Widgets, SQLite und CP-SAT bleiben geeignet. Die konkrete Hürde
liegt in der bisherigen Fachstruktur, nicht im Technologie-Stack. Vorhandene
Zeit-/CSV-/Worker-/Optimierungsmuster sind nützlich; vier Schichtsonderfälle
weiter auszubauen wäre nicht tragfähig. Nächster kleiner Schritt ist B1 aus
[Architektur und Migration](V2_ARCHITEKTUR_UND_MIGRATION.md): isolierte V2-Wertobjekte,
Europe/Vienna-Zeitintervalle und Arbeits-/Pausensegmente mit kleinen Tests,
zunächst ohne produktiven Solver- oder Datenbankwechsel.
