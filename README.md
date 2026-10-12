# Dienstplan

Lokale Desktop-Anwendung für die monatliche Dienstplanung eines Teams. Oberfläche und Meldungen sind deutsch. Die Planung verwendet OR-Tools CP-SAT, die Oberfläche Qt Widgets und die Speicherung SQLite. Im Betrieb werden keine Netzwerkverbindung und keine externen Konten benötigt. Ergebnisse sind **Prognosen aus dem Dienstplan**; tatsächlich geleistete Arbeitszeit wird nicht erfasst.

## Start und Bedienung

Im fertigen Windows-Paket `Dienstplan.exe` öffnen; auf macOS `Dienstplan.app` öffnen. Den vollständigen Paketordner behalten. Eine Python-Installation oder ein Terminal ist für diese Pakete nicht nötig. Die ersten Prüfbuilds sind unsigniert; vor einer breiten Auslieferung stehen native Prüfung und Signierung aus.

1. Monat und Jahr wählen. Die Monatslänge wird automatisch berücksichtigt.
2. Team mit Namen, Wochenstunden, Anfangssaldo und gewünschtem Endsaldo erfassen. Wochenstunden dürfen Nachkommastellen haben.
3. Drei tägliche Schichten und die wöchentliche besondere Schicht mit Wochentag konfigurieren. Standardbesetzung: zwei verschiedene Personen je Termin. Start, Ende, Pause und Besetzung gelten für den gewählten Monat.
4. Unter **Ausnahmetage** tägliche Dienste an einzelnen Tagen entfallen lassen; die besondere Schicht bleibt aktiv.
5. Sperren je Person manuell eintragen oder über eine CSV-Vorschau importieren.
6. Regeln und Rechenzeit wählen und **Dienstplan erstellen** anklicken. Die Berechnung läuft im Hintergrund und ist abbrechbar.
7. Offene Plätze, übergangene Wünsche, Stunden und Verteilung prüfen. Zuteilungen können geändert und für die nächste Berechnung fixiert werden.
8. Monat speichern; erst bei endgültiger Prüfung für die Historie bestätigen. Tabellen können als CSV exportiert werden.

Ein bereits vorhandener Plan wird vor einer neuen Berechnung nicht unbemerkt ersetzt. Die Schichten lassen sich in einen Folgemonat kopieren; bereits gespeicherte Monate behalten ihre eigenen Einstellungen. Die Datenbank liegt standardmäßig im lokalen Anwendungsdatenordner des Betriebssystems. Über `--database DATEI` lässt sich für Entwicklung und Sicherung ein anderer Speicherort wählen. Für eine Sicherung die Anwendung schließen und die SQLite-Datei kopieren. Ein Verlust dieser Datei bedeutet den Verlust der lokalen Daten.

## Entwicklung und Demonstration

Python 3.12 verwenden. Die folgenden Befehle sind für Entwickler*innen; Nutzer*innen erhalten ein fertiges Paket. `requirements-lock.txt` hält die in Linux geprüften direkten und transitiven Versionen fest; die nativen Builds installieren die direkt festgelegten Versionen aus `requirements-dev.txt` mit passenden Plattformabhängigkeiten.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m dienstplan
python -m dienstplan --demo --database examples/demo.sqlite3
python -m dienstplan --self-test
python scripts/demo_report.py
python -m pytest -q
```

Die Demonstration umfasst zwölf fiktive Personen mit unterschiedlichen Wochenstunden und CSV-Sperren unter `examples/`. Die geprüften CSV-Pläne für Oktober bis Dezember 2026 und der [Prüfbericht](examples/generated/pruefbericht.json) liegen unter `examples/generated/`. Alle Plätze sind besetzt; die jeweils 20-sekündige Suche beweist die optimalen Ziele für Besetzung und Wünsche, aber nicht das Optimum der dritten Stufe. Die Demo-Datenbank lässt sich mit `python -m dienstplan --database examples/generated/demo.sqlite3 --year 2026 --month 11` öffnen. Sie ist eine lokal erzeugte Datei; aus einem frischen Checkout erzeugt `python scripts/demo_report.py` sie erneut. Für einen erneuten Bericht einen neuen Ordner über `--output` wählen. Auf Linux ohne Display können UI-Tests mit `QT_QPA_PLATFORM=offscreen python -m pytest -q` ausgeführt werden. Ein solcher Test ersetzt die manuelle Prüfung auf Windows/macOS nicht.

| Personen (Wochenstunden) | Oktober Sonderdienste | November | Dezember | Summe |
| --- | --- | --- | --- | --- |
| Anna / Ben (je 40), Clara / David (je 36) | je 1 | je 1 | je 1 | je 3 |
| Eva / Felix (je 32), Greta / Hannes (je 30) | je 1 | je 0 | je 1 | je 2 |
| Ida / Jonas (je 28) | je 0 | je 1 | je 1 | je 2 |
| Klara / Leon (je 24) | je 0 | je 1 | je 0 | je 1 |

Im zweiten Monat bekommen damit alle vier zuvor nicht berücksichtigten Personen einen besonderen Dienst. Die verbleibenden Abweichungen vom vertraglichen Sollanteil stehen im Verteilungsexport; ein Zeitlimit garantiert keine perfekte Verteilung.

## Stunden und Salden

Berechnet wird in ganzen Minuten. Das Monatssoll wird **einmal nach der gesamten Umrechnung** kaufmännisch auf Minuten gerundet:

`Monatssoll S = Wochenstunden W × Kalendertage des Monats ÷ 7`

| Größe | Berechnung |
| --- | --- |
| Individuelles Planungsziel | `S + E − B` |
| Neue Plus-/Minusstunden im Monat | `P − S` |
| Voraussichtlicher Endsaldo | `B + P − S` |
| Abweichung vom Planungsziel | `P − (S + E − B)` |

`B` bezeichnet den Anfangssaldo, `E` den gewünschten Endsaldo und `P` die eingeplanten bezahlten Stunden. Standardmäßig ist `E = B`; bestehende Salden werden dann nicht gezielt abgebaut. Für vollständigen Abbau `E = 0` wählen. Bei 28 Tagen und 40 Wochenstunden sind `S = 160 h`; mit `B = +10 h` und `E = 0` ist das Ziel `150 h`, mit `B = −8 h` das Ziel `168 h`. Negative Planungsziele werden abgelehnt.

Eine achtstündige Schicht für zwei Personen benötigt 16 Mitarbeiterstunden. Vor der Planung wird der Gesamtbedarf mit den summierten individuellen Zielen verglichen. Ein rechnerischer Unterschied lässt sich auch durch eine gute Verteilung nicht auflösen.

## CSV-Sperren

Für jede Person getrennt importieren; die Zuordnung wird in der Oberfläche gewählt. UTF-8 mit oder ohne BOM, Semikolon oder Komma als Trennzeichen:

```csv
datum;von;bis;prioritaet;kommentar
2026-11-03;;;1;Ganztägig nicht verfügbar
2026-11-10;08:00;12:00;2;Privater Termin
2026-11-30;22:00;06:00;1;Bis zum nächsten Morgen
```

Datum: exakt `YYYY-MM-DD`; Zeit: `HH:MM`. Beide Zeiten leer bedeutet den ganzen Kalendertag. Nur eine leere Zeit ist ungültig. Ein Ende vor oder gleich dem Beginn bedeutet das Ende am **Folgetag**; gleiche Zeiten ergeben 24 Stunden. Ein Blocker dauert höchstens 24 Stunden. Angrenzende Intervalle kollidieren nicht; jede echte Überschneidung mit einer Schicht zählt.

Priorität **1** ist verbindlich, Priorität **2** ein übergehbarer Wunsch. Pro Person und betroffenem Kalendermonat sind insgesamt höchstens vier eindeutige Priorität-1-Blocker erlaubt, gemeinsam für Import und manuelle Eingabe. Ein Intervall über eine Monatsgrenze zählt in beiden Monaten. Gleiche Person, Startzeit, Endzeit und Priorität bilden ein Duplikat; ein anderer Kommentar legt keinen zusätzlichen Blocker an. Fehler werden vor dem Speichern mit Zeilennummer angezeigt. Ein fehlerhafter Import oder eine Überschreitung der Grenze verändert bestehende Sperren nicht. Kommentare sind optional.

## Planung, Fairness und Annahmen

Alle Personen können alle vier Schichttypen übernehmen. Überlappungen, Priorität-1-Sperren und gültige Fixierungen sind verbindlich. Mindestabstand, Tages-/Wochenstunden und aufeinanderfolgende Arbeitstage sind einzeln aktivierbar. Nicht konfigurierte Regeln werden als **nicht geprüft** ausgewiesen; die Anwendung setzt keine gesetzlichen Grenzwerte voraus.

Schichten mit Endzeit vor oder gleich der Startzeit enden am Folgetag. Unbezahlte Pausen vermindern die bezahlte Dauer. Die gesamte Schicht zählt für Monatssoll und Historie zum Monat ihres Startdatums. Sperren, Überschneidungen und Ruhezeiten berücksichtigen den tatsächlichen vollständigen Zeitraum, auch über die Monatsgrenze. Gespeicherte Zuteilungen anderer Monate werden als Randbedingungen berücksichtigt; unbekannte Schichten außerhalb der gespeicherten Daten können nicht geprüft werden. Für Tages- und ISO-Kalenderwochengrenzen werden bezahlte Minuten über Mitternacht aufgeteilt; die Pause wird rechnerisch am Schichtende abgezogen. Zeiten werden als lokale Kalenderzeiten ohne Zeitzonen-/Sommerzeitkorrektur behandelt. Daher entsteht in dieser Version bei einer Zeitumstellung keine zusätzliche oder kürzere bezahlte Stunde.

Die besondere Schicht wird durch ihren wöchentlichen Termin bestimmt. Sie darf kürzer, gleich lang oder länger als die täglichen Dienste sein; ihre tatsächliche bezahlte Dauer zählt für Stunden und Verteilung.

### Ausnahmetage

In der Monatsansicht **Ausnahmetage** bedeutet ein Haken **entfällt**. Jede der drei täglichen Schichten ist je Datum unabhängig deaktivierbar. Mehrere Zeilen auswählen, um alle täglichen Dienste dieser Tage abzuschalten; einzelne Haken oder „Ausnahmen aufheben“ aktivieren sie wieder. Die wöchentliche besondere Schicht ist davon unberührt. Es zählt das Startdatum: eine Nacht vom 15. in den 16. bleibt bestehen, wenn die Nacht des 16. entfällt.

Entfallene Termine zählen weder zu Bedarf, offenen Plätzen noch Planung/Fairness und Wunschrelevanz. CSV-Dienstplanexporte führen sie als **ENTFÄLLT** ohne Besetzungsplatz oder Mitarbeiterstunden. Bei vorhandenen Zuteilungen zeigt die Anwendung vor der Übernahme die entfallenden Personen und Fixierungen; nach Zustimmung werden genau diese Einsätze aus dem aktuellen Entwurf entfernt. Bestätigte Monate bleiben geschützt. Ausnahmen gehören nur zum jeweiligen Monat und werden beim Übernehmen einer Vorlage in einen neuen Monat nicht mitkopiert.

### Freiwünsche und Nachweisstatus

Alle verbindlichen Regeln bleiben hart. Danach minimiert CP-SAT streng in dieser Reihenfolge:

1. Offene Besetzungsplätze.
2. Gesamtzahl übergangener eindeutiger relevanter Priorität-2-Wünsche.
3. Übergehungen je Gruppe: zuerst Personen mit einem relevanten Wunsch, dann mit zwei usw.
4. Innerhalb jeder Gruppe gleicher Wunschanzahl: zuerst die größte kumulierte persönliche Belastung, anschließend die Summe der Belastungsquadrate.
5. Größte relative persönliche Stundenabweichung.
6. Gemeinsame quadratische Stunden- und Schichtfairness (Gewichte unten).

Relevant ist ein eindeutiger P2-Eintrag, der mindestens einen **aktiven** Schichttermin überschneidet. Mehrere verletzende Dienste zählen denselben Wunsch einmal. Duplikate, P1-Sperren und Wünsche ohne aktive Überschneidung erhöhen diese Wunschanzahl nicht. Bei gleicher minimaler Gesamtzahl werden so wenige Wünsche stärker geschützt; innerhalb gleicher Anzahl trifft es möglichst nicht immer dieselben Personen. Stunden- oder Schichtverbesserungen können keine höhere Stufe verschlechtern.

Die Übersicht **Freiwünsche** zeigt pro Person relevante, erfüllte und übergangene Wünsche, historische Übergehungen sowie kumulierte Belastung und fehlende Althistorie; sie hat einen eigenen CSV-Export. „Erfüllt“ bedeutet im aktuellen Plan nicht verletzt, auch bei offenen Plätzen; es ist keine Erfassung tatsächlich geleisteter Zeit.

Nur bestätigte **Vormonate** zählen zur Wunschhistorie. Beim Bestätigen werden die damaligen relevanten und verletzten Wunschschlüssel eingefroren. Spätere globale Sperrenänderungen verändern bestätigte Statistiken und Konfliktmarkierungen nicht. Die kumulierte Belastung ist die Vereinigung historischer und aktueller verletzter Schlüssel: ein über Monatsgrenzen laufender Wunsch wird einmal gezählt. Erneute Planung/Speicherung desselben Monats erhöht die Historie nicht. Alte bestätigte Daten ohne Wunsch-Snapshot sind weiter ladbar, werden aber als **damals nicht erfasst** gekennzeichnet und nicht nachträglich anhand veränderlicher Blocker geschätzt. Aufheben und erneutes Bestätigen ist eine ausdrückliche neue Bestätigung des bearbeiteten Standes.

Jede nachgeordnete Solverstufe hält die besten gefundenen Werte der höheren Stufen fest. Bei fehlendem Beweis darf die Suche weiter verbessern, aber das Gesamtergebnis bleibt **ohne vollständigen Optimalitätsnachweis**. Die Oberfläche nennt die nachgewiesenen Stufen. Ein vorhandener gültiger Plan ist Startpunkt und Rückfall. Geprüfte Einzelneuzuweisungen und Zweiertausche verbessern nur ein lexikografisch besseres gültiges Ergebnis und bewahren Fixierungen. Der endgültige Plan wird erneut geprüft/bewertet; Änderungen entwerten betroffene Nachweise. Bei Zeitlimit oder Abbruch bleibt der beste gefundene gültige Entwurf verfügbar; „noch kein Ergebnis“ beweist keine Unlösbarkeit.

### Stunden- und Schichtfairness

Für Person i ist der normierte Fehler `rᵢ = ceil(1000 × |Pᵢ − Planungszielᵢ| / max(Monatssollᵢ, 60 Minuten))`. Der Nenner bleibt das vertragliche Monatssoll, nicht das durch Salden veränderte Ziel; null und sehr kleine Sollwerte erhalten ausdrücklich einen Mindestnenner von einer Stunde. Zuerst wird `max(rᵢ)` minimiert. Dadurch unterscheiden sich ein gleichmäßig verteilter Stundenmangel und eine starke Belastung einzelner Personen, auch wenn ihre Summe absoluter Abweichungen gleich ist.

Die letzte Stufe minimiert `10000 × Σrᵢ² + Schichtterme + historische Sonderdienstterme`. Faire Schichtanteile richten sich nach Wochenstunden und tatsächlich besetzten aktiven Diensten. Pro Typ/Person gilt `c = 1000 × Einsätze − Anteil × insgesamt besetzte Einsätze`, `h = ceil(|1000 × Minuten − Anteil × insgesamt besetzte Minuten| / 60)`. Bewertet wird `c² + h²`, mit Faktor **1** für tägliche und **4** für besondere Schichten. Hinzu kommen kumulierte besondere Anzahl-/Stundenquadrate mit Faktor **8**, unter Einbeziehung bestätigter früherer Monate und ihrer damaligen Wochenstunden. Ohne Sonderhistorie gilt der aktuelle Monat. Bei ausschließlich null Wochenstunden sind die Anteile gleich. Solveranteile werden durch größte Reste auf Tausendstel verteilt; die gespeicherten historischen Sollanteile bleiben exakte Brüche.

Diese Ziele bevorzugen breitere Sonderdienstverteilung und weniger Stundenstreuung. Harte Grenzen, Verfügbarkeit, höhere Wunschziele und das Zeitlimit können Ungleichverteilungen erforderlich machen. Ein Worker, stabiler Seed und stabile Kennungen bestimmen die Suche; der Suchstand bei einem Zeitlimit und Änderungen der Solverversion können das Ergebnis verändern.

## Reproduzierbarer Novembervergleich

`python scripts/compare_planners.py --seconds 30 --output examples/comparison` berechnet den originalen Solver aus Commit `e7e0fc5` und die neue Version **seriell mit identischen Eingaben, Regeln und Zeitlimits**. Die fachliche Novemberfixture liegt in `dienstplan/fixtures.py`: zwölf Personen, je 25 Wochenstunden, Anfangs-/Wunschsaldo null, die vorgegebenen Schichten und Blockertage. Ohne Ausnahmen: **188 Plätze, 1.238 Mitarbeiterstunden Bedarf, 1.285,80 Stunden Ziele**. Frühdienst 16.11. ausgeschaltet: **186 Plätze, 1.226 Stunden**.

Der Vergleich benötigt den Baseline-Commit und seine Originaldateien in der lokalen Git-Historie. Der native Workflow lädt deshalb mit `fetch-depth: 0` die vollständige Historie. Vor dem Vergleich werden Commit und Dateien geprüft; fehlende Historie wird mit der tatsächlichen Git-Fehlermeldung erklärt. Der Test lädt nichts aus dem Netzwerk nach und ändert den Checkout nicht.

Die ausdrücklich gewählten Testgrenzen sind **11 Stunden Ruhezeit, 12 Tagesstunden, 40 Stunden je ISO-Woche, sechs tatsächliche Arbeitstage in Folge**. Frühere externe Testgrenzen sind unbekannt; der Vergleich beansprucht keinen identischen damaligen Testaufbau. [Vorher-/Nachher-Bericht](docs/VORHER_NACHHER.md) und `examples/comparison/` enthalten Kennzahlen, Einzelstunden, Wunschübergehungen, Schichtverteilungen und tatsächliche Nachweise. Die ältere Oktober–Dezember-Demo oben dokumentiert Version 0.1; aktuelle Ergebnisse bitte neu erzeugen.

## Pakete erstellen und Prüfstand

Auf dem jeweiligen Zielbetriebssystem mit Python 3.12 und den Entwicklungsabhängigkeiten:

```sh
python scripts/build.py
```

Windows: `dist/Dienstplan/Dienstplan.exe`; macOS: `dist/Dienstplan.app`. Das Buildskript erzeugt zusätzlich ein ZIP für Windows beziehungsweise ein TAR.GZ für macOS/Linux. Das TAR.GZ erhält die für `.app` nötigen Dateirechte und Symlinks. PyInstaller erzeugt eigenständig startbare Pakete einschließlich Python. Es findet keine plattformübergreifende Kompilierung statt. Intel- und Apple-Silicon-macOS-Pakete werden getrennt gebaut. Der native GitHub-Workflow liegt unter `.github/workflows/build.yml`.

Die **tatsächliche unkomprimierte Größe** wird nach jedem Build ausgegeben und in `dist/build-report.json` gespeichert. Windows- und macOS-Größen sind erst nach deren nativen Builds bekannt. Die aktuelle Cloud-Umgebung ist Linux; native Windows-/macOS-Starttests sind darin nicht möglich. Details der geprüften Versionen, Quellen und Plattformgrenzen: [Kompatibilität](docs/KOMPATIBILITAET.md). Technische Spezifikation und Etappen: [Spezifikation](docs/SPEZIFIKATION.md).

Prüfstand nach der CI-Reparatur: **158 Tests bestanden**, einschließlich kontrollierter Zeitlimitfälle, eines fairen Startplans ohne zusätzlichen Solverfund, schneller Tausche unter Wunsch-/Historienregeln und Paketprüfungen ohne Windows-Konsole. Der Selbsttest des fertigen Linux-Pakets besteht mit zwölf Personen und **186 besetzten Plätzen**, Ausnahmetagen, kurzem besonderem Dienst und bestätigter Freiwunschhistorie. Der frühere Novembervergleich steht im [Vorher-/Nachher-Bericht](docs/VORHER_NACHHER.md); Ursachen und aktuelle Prüfungen stehen unter [CI-Reparatur](docs/CI_REPARATUR.md). Native Windows-/macOS-Ergebnisse werden erst nach Abschluss des jeweiligen Actions-Laufs ausgewiesen.
