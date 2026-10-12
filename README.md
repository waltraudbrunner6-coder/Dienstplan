# Dienstplan

Lokale Desktop-Anwendung für die monatliche Dienstplanung eines Teams. Oberfläche und Meldungen sind deutsch. Die Planung verwendet OR-Tools CP-SAT, die Oberfläche Qt Widgets und die Speicherung SQLite. Im Betrieb werden keine Netzwerkverbindung und keine externen Konten benötigt. Ergebnisse sind **Prognosen aus dem Dienstplan**; tatsächlich geleistete Arbeitszeit wird nicht erfasst.

## Start und Bedienung

Im fertigen Windows-Paket `Dienstplan.exe` öffnen; auf macOS `Dienstplan.app` öffnen. Den vollständigen Paketordner behalten. Eine Python-Installation oder ein Terminal ist für diese Pakete nicht nötig. Die ersten Prüfbuilds sind unsigniert; vor einer breiten Auslieferung stehen native Prüfung und Signierung aus.

1. Monat und Jahr wählen. Die Monatslänge wird automatisch berücksichtigt.
2. Team mit Namen, Wochenstunden, Anfangssaldo und gewünschtem Endsaldo erfassen. Wochenstunden dürfen Nachkommastellen haben.
3. Drei tägliche Schichten und die längere wöchentliche Schicht mit Wochentag konfigurieren. Standardbesetzung: zwei verschiedene Personen je Termin. Start, Ende, Pause und Besetzung gelten für den gewählten Monat.
4. Sperren je Person manuell eintragen oder über eine CSV-Vorschau importieren.
5. Regeln und Rechenzeit wählen und **Dienstplan erstellen** anklicken. Die Berechnung läuft im Hintergrund und ist abbrechbar.
6. Offene Plätze, übergangene Wünsche, Stunden und Verteilung prüfen. Zuteilungen können geändert und für die nächste Berechnung fixiert werden.
7. Monat speichern; erst bei endgültiger Prüfung für die Historie bestätigen. Tabellen können als CSV exportiert werden.

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

Die Optimierung erfolgt in drei Stufen:

1. Möglichst viele Besetzungsplätze füllen.
2. Bei nachgewiesen optimaler Besetzung möglichst wenige verschiedene Priorität-2-Einträge übergehen.
3. Bei nachgewiesenen höheren Zielen Stundenabweichungen und faire Schichtverteilung gemeinsam verbessern.

Eine niedrigere Stufe darf ein nachweislich optimales höheres Ziel nicht verschlechtern. Ein ausgewogener, durch dieselben Regeln geprüfter Startvorschlag beschleunigt die dritte Suche, sofern er die bereits bewiesene Besetzung und Wunschanzahl genau beibehält. Anschließend optimiert CP-SAT die vollständige Zielfunktion. Bei einem Zeitlimit wird ein gültiges vorhandenes Ergebnis mit seinem tatsächlichen Nachweisstatus zurückgegeben. Offene Plätze bleiben sichtbar; verbindliche Regeln werden nicht dafür verletzt. „Kein Ergebnis innerhalb des Zeitlimits“ bedeutet keinen Beweis der Unlösbarkeit.

Faire Sollanteile richten sich nach den vertraglichen Wochenstunden. Die dritte Stufe minimiert diese Summe absoluter Abweichungen:

`10 × Zielabweichungen in Minuten + je Schichttyp Faktor × (60 × Anzahlabweichungen + Minutenabweichungen) + 8 × (60 × kumulierte besondere Anzahlabweichungen + kumulierte besondere Minutenabweichungen)`

Der Faktor pro Schichttyp ist 1 für tägliche und 4 für besondere Schichten. Damit zählen Anzahl und Stunden; die lange Schicht und ihr historischer Ausgleich erhalten mehr Gewicht. Die Sollanteile werden für den Solver auf Tausendstel aufgeteilt, wobei ihre Summe exakt eins bleibt; historische Sollanteile bleiben in der Speicherung ungerundete Brüche. Stundenabweichungen und Fairness werden innerhalb dieser Stufe gemeinsam gewichtet, ohne eine genaue Stundenübereinstimmung zu erzwingen. Verfügbarkeit und harte Regeln können eine Gleichverteilung verhindern.

Nur ausdrücklich bestätigte, vollständig geprüfte Monatspläne vor dem aktuellen Monat zählen zur Historie. Wochenstunden und faire Sollanteile werden mit dem jeweiligen bestätigten Monat gespeichert; spätere Vertragsänderungen verändern sie nicht. Neue Berechnungen und wiederholtes Speichern zählen keine Einsätze doppelt. Ohne Historie gilt die Verteilung des aktuellen Monats. Gleichwertige Lösungen werden mit festem Solver-Seed und einem Suchworker reproduzierbar gesucht; Änderungen an Solver-Version oder Rechenzeit können ein anderes gleichwertiges Ergebnis ergeben. Verbleibende Abweichungen werden in der Verteilungsübersicht angezeigt.

## Pakete erstellen und Prüfstand

Auf dem jeweiligen Zielbetriebssystem mit Python 3.12 und den Entwicklungsabhängigkeiten:

```sh
python scripts/build.py
```

Windows: `dist/Dienstplan/Dienstplan.exe`; macOS: `dist/Dienstplan.app`. Das Buildskript erzeugt zusätzlich ein ZIP für Windows beziehungsweise ein TAR.GZ für macOS/Linux. Das TAR.GZ erhält die für `.app` nötigen Dateirechte und Symlinks. PyInstaller erzeugt eigenständig startbare Pakete einschließlich Python. Es findet keine plattformübergreifende Kompilierung statt. Intel- und Apple-Silicon-macOS-Pakete werden getrennt gebaut. Der native GitHub-Workflow liegt unter `.github/workflows/build.yml`.

Die **tatsächliche unkomprimierte Größe** wird nach jedem Build ausgegeben und in `dist/build-report.json` gespeichert. Windows- und macOS-Größen sind erst nach deren nativen Builds bekannt. Die aktuelle Cloud-Umgebung ist Linux; native Windows-/macOS-Starttests sind darin nicht möglich. Details der geprüften Versionen, Quellen und Plattformgrenzen: [Kompatibilität](docs/KOMPATIBILITAET.md). Technische Spezifikation und Etappen: [Spezifikation](docs/SPEZIFIKATION.md).

Prüfstand dieser ersten Version: **77 automatisierte Tests bestanden** (einschließlich Qt-Integration und einer vollständigen Offline-Kette mit gesperrten Python-Netzwerkverbindungen). Der eigenständig startbare Linux-x64-Build wurde funktional mit `--self-test` geprüft: CSV-Import, zwölf Personen, 188 besetzte Plätze, Stundenrechnung, SQLite-Neustart und Qt-Fenster. Gemessene Paketgröße: rund **279,5 MiB entpackt**, **108,5 MiB als TAR.GZ**; die exakten Bytewerte des jeweiligen letzten Builds stehen im Buildbericht. Die Linux-Oberfläche wurde ohne Bildschirm mit Qt offscreen geprüft. **Windows- und macOS-Pakete wurden noch nicht gebaut oder ausgeführt**; der native CI-Ablauf ist vorbereitet, aber nicht gestartet.
