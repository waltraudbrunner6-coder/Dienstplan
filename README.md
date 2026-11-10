# Dienstplan

**Neu in 0.4.0:** XLSX-/CSV-Import für Termine, einzelne oder vollständige
Dienstzuteilungen sowie gemischte Wünsche/Urlaub; bearbeitbare Gesamtvorschau mit
zentraler Personen-ID-Zuordnung. Monatsübersicht mit Wochentagen, Excel-Tabellenexport
und automatische Pausenwahl bei manueller Zuteilung. BK/WL: zwei WL und ein BK pro
Woche, niemals am selben Startdatum; Wochen-/Randprofil einmal ausdrücklich wählen.
Die erste normale Berechnung fordert diese Auswahl an; Folgemonate übernehmen sie.
Details und offene Zuordnungen: [Tabellenimport und Excel-Export](docs/TABELLENIMPORT.md).
Unbekannte Kürzel oder widersprüchliche Altangaben werden nicht still umgedeutet.

Lokale, deutschsprachige Desktop-Anwendung für Monatsdienstpläne mit Python/Qt,
OR-Tools CP-SAT und SQLite. Planung und Speicherung funktionieren offline.
Ergebnisse sind Planprognosen, keine tatsächlich erfassten Arbeitszeiten.

**Anzeigekorrektur 0.3.1:** Berechnete Vorschläge erscheinen sofort im Reiter
**Dienstplan**, einschließlich zugeteilter Namen und zugehöriger Stundenübersichten.
Erst **Ergebnis übernehmen** speichert den Vorschlag; bestehende Pläne bleiben
bis dahin erhalten. Die Vorschau lässt sich verwerfen oder direkt exportieren.

## Start

Windows: den vollständigen Paketordner entpacken und `Dienstplan.exe` öffnen.
macOS: das enthaltene `Dienstplan.app` öffnen. Python und Terminal sind dafür
nicht erforderlich. Die Pakete sind derzeit unsigniert.

**Ab Version 0.3.0 startet ausschließlich die neue V2-Hauptoberfläche.** Es gibt
keine Startauswahl und keinen zusätzlichen Testbereich mehr. Version und
Buildkennung stehen im Fenster; der Commit steht auch im Archivnamen.
Die bisherigen Vier-Schichten-Pakete beziehungsweise Pakete mit Startauswahl
enthalten noch diesen früheren Programmstand.

## Bedienung

1. **Monat wählen.** Neue Monate enthalten automatisch die regulären KC10-,
   KC16- und W17-Termine; donnerstags stattdessen KCT10, KCT, TW und T.
   Der vollständige Standardkatalog mit **17 Dienstkürzeln / 19 Varianten**
   steht unter **Dienste und Planungsangaben**, einschließlich Zeiten, Besetzung
   und Auftreten. Die Reservefenster werden vom 24.12. bis 06.01. erzeugt.
2. Unter **Personen** Namen, Wochenstunden und Konten erfassen. Neue Dateien
   enthalten keine erfundenen Teammitglieder. **Person ergänzen** öffnet
   Beschäftigung, Vertragsversionen und die **ausgeschlossenen Dienste**.
   In der Auswahlliste bedeutet ein Häkchen „ausgeschlossen“; eine leere Liste
   schließt keinen Dienst aus. N17 benötigt zusätzlich bestätigten Führerschein.
3. **Monatstermine** prüfen und feste Sondertermine mit Datum und Personen
   ergänzen. Für WL/BK fehlt weiterhin das bestätigte Wochenprofil; für LB
   Referenzdatum und Personen. Diese Angaben werden sichtbar benannt und nicht
   erfunden. TS, VN, INT, N17 und FK brauchen die vorgesehenen konkreten Eingaben.
4. Urlaub und Wünsche manuell vormerken oder als **CSV-Format 2** importieren.
   Fehlerhafte Einträge bleiben gemeinsam bearbeitbar zur Korrektur vorgemerkt;
   es gibt keine teilweise Übernahme. Donnerstagswünsche bleiben unzulässig.
5. Das Rechenprofil ausdrücklich wählen, **Arbeitsstand speichern**, danach
   **Dienstplan erstellen**. Die Suche läuft im Hintergrund, ist zeitlich
   begrenzt und abbrechbar. **Ergebnis übernehmen** ersetzt den Entwurf erst
   nach der unabhängigen Prüfung. Offene Plätze bleiben als **OFFEN** sichtbar.
6. Zuteilungen im Dienstplan ändern, entfernen oder fixieren; Stundenprognose,
   Verteilung und Freiwünsche prüfen. **Exportpaket** enthält konsistente CSVs,
   den exakten Arbeitsstand und ein Prüfmanifest. Nur gültige vollbesetzte
   Rechenstände lassen sich unveränderlich bestätigen.

Dauern, Salden und Prognosen werden in **Stunden mit Dezimalkomma** angezeigt
und eingegeben: `7,5` entspricht siebeneinhalb Stunden. CSV-Zeitmengen stehen
in Stunden mit eindeutigen Spaltennamen. Intern bleiben ganze Minuten und exakte
Brüche erhalten; unverändertes Speichern gerundeter Anzeigen verliert keine
Minute. Neue V2-Konten haben Wunschende null; vorhandene Anfangssalden bleiben.

## Speicherung und bestehende Daten

Die neue Hauptanwendung speichert dauerhaft in `dienstplan-v2.sqlite3` im
lokalen Anwendungsdatenordner. Beim nächsten Start wird der zuletzt vorhandene
Monatsarbeitsstand geladen. Über **Datei öffnen** sind bisherige V2-Dateien
mit Schema 3 weiter nutzbar. **Datei kopieren** legt eine getrennte Datei an.
Für Sicherungen die Anwendung schließen und die SQLite-Datei kopieren.

Die frühere `dienstplan.sqlite3` wird weder geöffnet noch verändert, gelöscht
oder automatisch umgedeutet. Eine V1-Datei wird beim Öffnen verständlich
abgewiesen; Migration und Übernahme bedürfen weiterhin einer ausdrücklich
geprüften Zuordnung. Bestätigte historische Daten bleiben geschützt.

## Rechenannahmen und noch offene Grundlagen

Der Oberflächenwechsel ersetzt keine fachlich fehlende Profilbestätigung.
Vor einer Berechnung ist das vorhandene technische Profil **S0/M0/E0**
ausdrücklich auszuwählen. S0 summiert die je Tag gültigen Wochenstunden / 7
und rundet einmal am Monatsende auf Minuten; M0 ordnet tatsächliche
Arbeitssegmente ihrem Kalendermonat zu. Urlaubsgutschrift: gültige Wochenstunden
/ 5 je ausdrücklich anrechenbarem Urlaubstag.

`Arbeitsziel = S + E − B − G`; `Prognose-Endsaldo = B + P + G − S`.
Ein negatives Ziel erzeugt keine negative Arbeitszuteilung. E0 ist die benannte
technische Zielreihenfolge; Profile und nicht bewiesene Ziele werden mitexportiert.
Fehlende Randdaten gelten nicht als nachgewiesene Freizeit.

Ungeklärte Rechts-/Tarifprofile, Reservebewertung, durchgängige Pausenabdeckung,
WL/BK-Wochenregeln und weitere Entscheidungen bleiben sichtbar offen. Ein
bestätigter Rechenstand ist keine Rechts-, KV-/BV- oder Abrechnungsfreigabe.
Ein vollständiger Standardkatalog bedeutet nicht, dass alle Sondertermine und
Betriebsprofile eines Monats bereits konfiguriert sind.

Details: [Bedienungsanleitung](docs/V2_BEDIENUNG.md),
[Fachregeln](docs/V2_FACHREGELN.md), [offene Entscheidungen](docs/V2_OFFENE_FRAGEN.md),
[Architektur/Migration](docs/V2_ARCHITEKTUR_UND_MIGRATION.md),
[Fortschritt und aktuelle Tests](docs/V2_FORTSCHRITT.md),
[125 Abnahmefälle und tatsächlicher Status](docs/V2_ABNAHMESTATUS.md),
[native Pakete und Messwerte](docs/V2_NATIVE_PRUEFUNG.md).

## Entwicklung und Builds

Python 3.12 und die festgelegten Abhängigkeiten verwenden:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m dienstplan
python -m dienstplan --demo --database NEUE_DEMODATEI.sqlite3
python scripts/run_tests.py
python scripts/build.py
python scripts/check_package.py
```

`--demo` ist eine ausdrückliche Option mit zwölf fiktiven Personen und dem
Standardmonat November 2026. Ein vorhandener Monatsstand wird dabei bewahrt.
`--database` bezeichnet jetzt eine V2-Datei; `--v2` ist ein kompatibler Alias.
`--legacy` startet keine alte Oberfläche mehr und wird abgewiesen.

PyInstaller erstellt eine selbstständig startbare Ordneranwendung.
Windows-Pakete auf Windows bauen, macOS-Sequoia-Pakete auf macOS 15 jeweils
für ARM64/Intel. Die [GitHub-Actions-Matrix](.github/workflows/build.yml)
führt Tests, Build und Paketprobe auf allen drei Zielen aus. Die Paketprobe
verlangt die tatsächliche Hauptoberfläche mit Standarddiensten, Ausschlussliste,
Stundenanzeige und persistentem Neustart sowie Solver, SQLite und Wiener DST.
Sie verwendet ausschließlich temporäre synthetische Daten. Linux-Tests ersetzen
keinen nativen Windows-/macOS-Nachweis. Aktuelle Downloadlinks sind im nativen
Prüfbericht ausdrücklich einem Commit zugeordnet.

Ab Version 0.4.1 können manuelle Änderungen und Importe nach ausdrücklicher Warnung
auch trotz Regelverstößen übernommen werden. Der Plan und Exporte kennzeichnen
diese Abweichungen dauerhaft. Siehe [Regelübersteuerung](docs/TABELLENIMPORT.md).

Ab 0.4.3 öffnet die manuelle Zuordnung direkt die Personenauswahl, auch nach einem
Import ohne BK/WL-Wochenprofil. Fixierungen werden bei einem bestätigten Wechsel
korrekt auf die neue Person übertragen. Umfang der erneuten Funktionsprüfung:
[Bedienprüfung 0.4.3](docs/V2_BEDIENPRUEFUNG_0_4_3.md).
