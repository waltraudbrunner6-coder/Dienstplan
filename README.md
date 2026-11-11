# Dienstplan

Lokale, deutschsprachige Desktop-Anwendung für Monatsdienstpläne mit Python/Qt,
OR-Tools CP-SAT und SQLite. Planung und Speicherung funktionieren offline.
Die Stunden sind Prognosen aus dem Dienstplan, keine erfassten Ist-Arbeitszeiten.

**Änderungen für 0.5.0:** Urlaub mit Kalender, verständlicher Tages-/Stundenübersicht
und angespartem Urlaubskonto; Termine mit Datum, Uhrzeit und Namensauswahl;
Reserve als normale Arbeit; KC15 als echte Ersatzwahl; Nachtdienste vollständig
im Startmonat. Die bestätigten Antworten stehen in den
[Fachregeln](docs/V2_FACHREGELN.md). Tatsächlich geprüfte Versionen, Builds und
Downloads sind im [nativen Prüfbericht](docs/V2_NATIVE_PRUEFUNG.md) ausgewiesen.
Eine Beschreibung neuer Funktionen ist kein Nachweis eines abgeschlossenen Builds.

## Start

Windows: Paket vollständig entpacken und `Dienstplan.exe` öffnen.
macOS: das vollständige `Dienstplan.app` für Apple Silicon oder Intel öffnen.
Python und Terminal sind dafür nicht erforderlich. Version und Buildkennung
stehen im Fenster. V2 ist die normale Hauptanwendung; eine Startauswahl oder
zusätzliche Testoberfläche gibt es nicht.

## Einfacher Ablauf

1. **Monat wählen.** Vorhandene Monate werden geladen; neue Monate enthalten die
   regulären Tages- und Donnerstagsdienste sowie die vorgesehenen Reservefenster.
2. **Personen** erfassen: Namen, Wochenstunden, Anfangssaldo und gewünschter
   Endsaldo. Im Personeneditor Beschäftigung, Verträge und ausgeschlossene Dienste
   prüfen. Ein Häkchen bedeutet „ausgeschlossen“; N17 braucht bestätigten Führerschein.
3. **Monatstermine** prüfen. **Termin hinzufügen** verwendet Kalender, Uhrzeiten
   und Namen statt technischer Personenlisten. **LB-Termine ergänzen** fragt die
   beiden Personen und ergänzt die fehlenden Termine der Monatsserie ab 03.12.2026
   im 14-Tage-Rhythmus. Bereits erfasste LB-Paare bleiben erhalten.
4. Unter **Urlaub und Wünsche** Einträge hinzufügen oder eine Tabelle importieren.
   Im Urlaubskalender zählen alle angezeigten ausgewählten Daten, auch Wochenenden
   und Feiertage. Pro Tag wird die gültige Wochenarbeitszeit ÷ 5 gutgeschrieben.
5. In der **Urlaubsübersicht** einmal den Kontenstart und Anfangsbestand je Person
   eintragen. Zwei Tage Anspruch je vollem Beschäftigungsmonat werden angespart;
   Teilmonate zählen anteilig nach Beschäftigungskalendertagen.
   Anspruch in Tagen und Stundengutschrift sind unterschiedliche Größen.
6. **Dienstplan erstellen**, Vorschlag prüfen und **Ergebnis übernehmen**.
   Erst die Übernahme ersetzt den gespeicherten Entwurf. Die Suche läuft im
   Hintergrund, hat ein Zeitlimit und kann abgebrochen werden.
7. Manuell zuordnen, fixieren, exportieren oder den **Monat bestätigen**.
   Regelverstöße werden angezeigt und sind bei manuellen Änderungen, Import und
   Monatsbestätigung nach ausdrücklicher Warnung übersteuerbar. Offene Plätze
   bleiben sichtbar; bestätigte Abweichungen werden nicht als regelkonform bezeichnet.

BK/WL: ganzjährig zwei WL und ein BK je Woche, nie am selben Startdatum.
Die Wochen-/Randregel wird über **BK/WL automatisch: 2 WL + 1 BK** bzw. vor der
entsprechenden automatischen Planung eingerichtet. Manuelles Zuordnen öffnet
direkt die Personenauswahl und verändert diese Termine nicht nebenbei.

KC15 15:00–00:00 mit einer Person kann KC10 und KC16 gemeinsam ersetzen, wenn
sonst Besetzung fehlt. Der Solver bevorzugt bei gleicher Besetzbarkeit die
reguläre Variante. Bei Zeitlimit ist die Notwendigkeit eines Ersatzes nicht
automatisch bewiesen. Gleichzeitige Pausen sind erlaubt; die normale enthaltene
30-Minuten-Pause bei mehr als sechs Stunden bleibt bestehen.

## Stunden und Urlaub

Anzeigen und Eingaben verwenden Stunden mit Dezimalkomma: `7,5` ist siebeneinhalb
Stunden. Intern bleiben ganze Minuten und exakte Brüche erhalten.

```text
Monatssoll S = Wochenstunden × Kalendertage ÷ 7
Urlaubsgutschrift G = Summe der gültigen Wochenstunden ÷ 5 je Urlaubstag
Arbeitsziel = S + gewünschter Endsaldo E − Anfangssaldo B − G
Prognose-Endsaldo = B + geplante Stunden P + G − S
```

Vertragswechsel werden tagweise berücksichtigt; Soll und Urlaubsgutschrift
werden jeweils erst am Monatsende einmal auf Minuten gerundet. Neue Konten
haben Wunschendsaldo null. Ein negatives Arbeitsziel erzeugt keine negative Arbeit.

Die neue Monatsbuchung **M1** rechnet die gesamte bezahlte Dienstzeit zum Monat
des lokalen Dienstbeginns. Ein Nachtdienst am 30.11. bis 01.12. zählt deshalb
vollständig zum Novemberkonto. Physische Nacht-/Sonn-/Feiertagsmengen bleiben
nach tatsächlichen Kalendertagen getrennt. Alte bestätigte M0-Monatsstände werden
unverändert gelesen und nicht nachträglich umgerechnet. Eine technische
Profilauswahl ist für die normale Bedienung nicht erforderlich.

Urlaub: Jeder ausdrücklich markierte U-Tag zählt, auch am Wochenende/Feiertag;
25 Wochenstunden ergeben fünf Stunden Gutschrift je Tag. Doppelte Einträge
zählen denselben Personen-/Kalendertag einmal. Zwei monatliche Anspruchstage
sind keine Grenze für die Zahl gebuchter Tage. Fehlende Anfangsbestände oder
nicht belegte historische Verbräuche werden als unbekannt gezeigt.
Für Ein-/Austritt gilt exakt: zwei Tage × Beschäftigungskalendertage ÷
Kalendertage des Monats. Diese Bruchteile werden ohne pauschale Tagesrundung
angespart.

## Import, Dateien und Exporte

XLSX/CSV unterstützt Dienstpläne, einzelne fixierte Dienste, Termine und
Urlaub/Freiwünsche mit Personen-ID-Zuordnung und bearbeitbarer Vorschau.
Ein fehlerhafter Import wird nicht teilweise übernommen. Wiederholte Importe
legen identische Fixierungen nicht doppelt an. Details und CSV-Beispiele:
[Tabellenimport](docs/TABELLENIMPORT.md), [Bedienung](docs/V2_BEDIENUNG.md).

Die App speichert lokal in `dienstplan-v2.sqlite3` im Anwendungsdatenordner.
**Datei öffnen** lädt eine vorhandene V2-Datei. **Datei kopieren** legt den
Arbeitsstand separat ab; sie setzt ihn nicht zurück. Für eine vollständige
Sicherung die App schließen und die SQLite-Datei kopieren.
Die alte V1-Datei wird nicht automatisch verändert oder umgedeutet.

**Monatstabelle als Excel exportieren** liefert die übersichtliche Personen-
und Tagesmatrix. **Exportpaket** enthält zusammengehörige CSVs, exakte
Monatsdaten und Prüfmanifest. Alle Daten beziehen sich auf denselben sichtbaren
Stand. Bestehende Exportdateien werden nicht überschrieben.

## Noch benötigte Angaben und Nachweise

Feste Personen und konkrete Sondertermine bleiben normale Eingaben. FK wird
ausschließlich als Einzeltermin erfasst. Die enge Freitags-W17-Ausnahme gilt
auch für Wochenend-Freiwünsche; sonstige Wochenendarbeit bleibt zu berücksichtigen.
Wirklich offene Sonderfälle sind noch Teilmonats-Wochenendquoten, die relative
Priorität freiwilliger Teamteilnahme und gegebenenfalls Euro-/Tarifdaten.
Sie blockieren nicht pauschal Urlaub und lokale Dienstplanung.
Eine Bestätigung ist kein Rechts-/Tarifnachweis.

- [Bedienungsanleitung](docs/V2_BEDIENUNG.md)
- [Fachregeln](docs/V2_FACHREGELN.md) und [verbleibende Fragen](docs/V2_OFFENE_FRAGEN.md)
- [Informationsprüfung](docs/V2_INFO_AUDIT.md) und [Fortschritt](docs/V2_FORTSCHRITT.md)
- [Abnahmestatus](docs/V2_ABNAHMESTATUS.md) und [native Downloads/Messwerte](docs/V2_NATIVE_PRUEFUNG.md)

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

`--demo` erzeugt ausdrücklich zwölf fiktive Personen. Normale neue Dateien
enthalten kein erfundenes Team. Ein bestehender Monatsstand wird nicht durch
einen Demostart ersetzt. `--database` bezeichnet eine V2-Datei; `--v2` bleibt
kompatibel, `--legacy` startet keine alte Oberfläche.

PyInstaller baut eine selbstständig startbare Ordneranwendung. Windows auf
Windows bauen, macOS Sequoia jeweils nativ für ARM64 und Intel. Die
[GitHub-Actions-Matrix](.github/workflows/build.yml) führt Tests, Build und die
Prüfung des gebauten Programms aus. Linux-Tests ersetzen keinen nativen
Plattformnachweis. Nur der aktuelle Prüfbericht belegt tatsächlich erstellte
Pakete; die Pakete sind ohne gesonderten Nachweis nicht signiert/notarisiert.
