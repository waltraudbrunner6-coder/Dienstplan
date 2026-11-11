# V2 – Implementierungsstand und Wiederaufnahme

Aktueller Folgeauftrag: **0.5.0 – Urlaubskonten, verständliche Bedienung und geklärte Dienstregeln**. Der jüngste Prüf-/Lieferstand steht am Dateiende;
die folgenden älteren Etappenberichte bleiben als Verlauf erhalten.

## Aktueller Folgeauftrag: Excel-Import, Monatsansicht, Pausen und BK/WL (0.4.0)

Implementiert: lokale XLSX-/CSV-Bediengrenze mit openpyxl 3.1.5 und festgelegter
et_xmlfile-Abhängigkeit. Formate, Zuordnung und Grenzen: [TABELLENIMPORT.md](TABELLENIMPORT.md).
Termine ohne Person, Dienstzuteilungen mit Fixierung, Urlaub, Einzel- und
Wochenendwünsche können gemeinsam als vollständig geprüfter Stapel übernommen
werden. Korrekturen/ID-Zuordnungen bleiben in SQLite vorgemerkt. Aktiver Plan,
Abwesenheiten und Staging werden in einer Transaktion übernommen; Fehler rollen
alles zurück. Bestätigte Monate bleiben geschützt; keine echte Datenmigration.

Die bereitgestellten privaten Quelldateien wurden lokal ausgewertet, nicht ins
Repository übernommen. Vorbereitete XLSX-Dateien liegen ausschließlich außerhalb
des Repositories unter `/workspace/artifacts/dienstplan-import/`. November enthält
172 importierte Zeilen plus drei Einträge der ursprünglichen 01.12.-Spalte in einer
separaten Datei; zwei NH wurden wie erlaubt ignoriert. 13 Personenreferenzen werden
erhalten, weil außerhalb der zwölf Hauptzeilen in Zeile 17 noch ein W17 steht.
Dezember: 60 Zeilen, davon 48 gelbe Einzelwünsche, acht Dienstzuteilungen und vier
ungeklärte U-Einträge, ohne vorweggenommene Urlaubszuordnung. Grüne Markierungen werden ignoriert.
Keine Personenidentität zwischen Dateien aus identischen Zeilennummern geraten.

Offen und gezielt nachgefragt: Donnerstagswünsche (bisher verboten), globale
Randwochenabgrenzung, KC15-Zeiten, R-Zeitfenster/-Bewertung und U-Bedeutung sowie
KC10 am Donnerstag 31.12. (kurzer KC10 oder KCT10). Unklare Werte bleiben erhalten,
aber fehlerhafte Stapel werden nicht teilweise aktiv übernommen. Einige alte
Besetzungs-/Zeitangaben können außerdem den aktuellen harten Regeln widersprechen;
Einlesen ist keine Behauptung eines regelkonformen neuen Plans. IDs ergänzt die
Bedienperson. Diese offenen Inhalte wurden nicht als „fertig importiert“ ausgegeben.

Neue bestätigte Regel: ganzjährig zwei WL und ein BK pro Woche, keine BK/WL am
selben lokalen Startdatum. F07 damit für den neuen Pfad geklärt; die alte saisonale
Testfunktion bleibt nur als historisches Profil bestehen. Bei erster normaler
Berechnung wird das Wochenprofil ausdrücklich gewählt (gemeinsame ISO-Randwochen
oder ausdrücklich nur volle Monatswochen). Folgemonate übernehmen es. CP-SAT wählt
Termine und Personen gemeinsam, Fixierungen bleiben bestehen; gemeinsame Quoten
haben dieselbe ISO-ID, Nachbarmonate keine unabhängige zweite Wochenquote.
Gespeicherte gemeinsame Termine und vorhandene Zuteilungen werden übernommen;
widersprüchliche Änderungen werden abgelehnt. Kalenderzeiten im Nachbarmonat
werden weder verborgen noch als nachgewiesene Freizeit angenommen. Stundenrechnung
dedupliziert identische Zuteilungen in Randdaten und aktuellem Entwurf.

Anzeige: Datum/Wochentag/Beginn/Ende in der Detailliste, zusätzliche Monatsmatrix
mit festen Personenlabels beim Scrollen, Wochenenden und textlichen offenen
Plätzen. XLSX-Export wie die Person×Datum-Vorlage mit Drucklayout, Stunden und
offenen Plätzen sowie reimportierbaren Einzelzeilen. Bestehende Dateien werden
nicht überschrieben, Fehler veröffentlichen keine halbe Datei. Konkrete Pausen,
Fixierungsstatus und Budgetbesitz grenzüberschreitender Wochenendwünsche bleiben
im Reimport erhalten. Im manuellen Ablauf nur Personenauswahl; konkrete Pause
bevorzugt vor 22 Uhr des Starttags, sonst möglichst mittig, unter allen harten Regeln.

Prüfungen: Ausgang 368 Tests bestanden in 88,80 s. Zwischenstände 384 Tests in
109,18 s und 390 Tests in 96,35 s. Neue synthetische Regressionen für farbige Wünsche,
Formelsicherheit, IDs, Duplikate, atomare gemischte Importe/Rollback, Speicherung,
reale Solverfixierung, Wochenprofile/Randwochen, Stunden-Deduplizierung, Pausen,
Excel-Reimport, Monatsgrenzen und Exportfehler. Keine privaten Tabellen als Testfixture.
Paketprobe erweitert um Excel-Import/Export, automatische Pause und Wochenkonfiguration.
Keine offenen KV-/BV-/Reserve-/Gutschriftprofile hierdurch als entschieden ausgegeben.

Abschließender Gesamtlauf `.venv/bin/python scripts/run_tests.py`:
**393 bestanden in 100,87 s**, keine Fehler/Skips. Gezielte letzte Prüfungen
für neue Tabellen-, UI- und gekoppelte Regeln ebenfalls bestanden. `pip check`:
keine defekten Anforderungen. Neue Abhängigkeiten direkt und im Lock festgelegt:
openpyxl 3.1.5, et_xmlfile 2.0.0.

Letzter vollständiger Gesamtlauf: **394 bestanden in 101,84 s**. Danach drei
zusätzliche CSV-Formatfälle (BOM/Trennzeichen/Strukturfehler) mit dem gesamten
neuen Tabellenmodul geprüft: **24 bestanden in 16,76 s**. Die Erwartung des neu
angelegten Farbzellentests zu U wurde nach fachlicher Prüfung korrigiert:
U ist nicht bestätigt, deshalb `u_zuordnung_offen` statt angenommener Urlaub.
Die Originaleinträge bleiben erhalten und bis zur Entscheidung inaktiv. Keine
bestehende harte Schutzregel wurde für einen grünen Test abgeschwächt.
Neue native Paketprobe mit Excel-Roundtrip und echter Speicherübernahme im
Quellcode bestanden; die native Matrix prüft zusätzlich den gesamten aktuellen Stand.

Stand 974cc90 wurde gepusht und auf Windows x64/macOS Sequoia ARM64/Intel mit
Tests, Build und verschärfter Paketprobe erfolgreich geprüft (Run 42890069478).
Anschließend Randdatenabsicherung ergänzt: auch Nachbarpläne ohne neues
Wochenprofil liefern vorhandene Nacht-/BK-/WL-Dienste und bekannte Tage; alte
BK-/WL-Zuteilungen werden nicht durch eine neue unabhängige Randquote verdrängt.
Regression mit W17 am 30.11. bis 01.12. 01:00: KC10 am 01.12. um 10:15 wird
wegen tatsächlicher Ruhe von nur 9:15 abgelehnt. Früherer Nachbar benötigt dafür
kein bereits freigegebenes neues Wochenprofil. Finale Pakete müssen diesen
nachfolgenden geprüften Code ebenfalls enthalten.

Randdaten-Gesamtlauf: **398 bestanden in 109,18 s**. Danach zusätzlich den
normalen Erstfall einer manuellen Zuteilung geprüft: Wochenprofil wählen,
konkrete statt aller optionalen Datumsalternativen prüfen und speichern.
Relevante komplette Tabellen-/Qt-Regressionen: **41 bestanden in 24,54 s**.
Das schließt die neue normale Erstzuteilung ein; kein technischer Vier-Termine-
Datensatz als Ersatz dieses Ablaufs. Neue finale Pakete werden aus dem gesamten
nachfolgenden Code gebaut. Keine privaten Tabellen ins Repository aufgenommen.

Vor Berechnung werden jetzt eine vorläufige gültige 2-WL-/1-BK-Datumswahl
und entsprechend benötigte Plätze gezeigt, keine Summe aller Kandidatentage.
Die Eingabetabelle kennzeichnet weitere Termine ausdrücklich als Datumsoptionen;
für den Solver bleiben sie unverändert frei wählbar. Regression November 2026:
84 Datumsoptionen, aber nur 156 operative Plätze im gesamten Randwochenhorizont
(120 regulär + sechs ISO-Wochen mit je sechs Mitarbeiterplätzen).

Bedarf wird getrennt für den Planungshorizont und den tatsächlichen lokalen
Kalendermonat gezeigt. Offene Pausen über Monatsgrenzen ergeben eine Bandbreite,
konkrete Pausen und bekannte Randdienste exakte Minuten; keine Vier-Wochen- oder
Dienststart-Abrechnungsannahme. Ein W17 vom 30.11. 17:00 bis 01.12. 01:00 benötigt
für zwei Personen im Dezember 1–2 Stunden, mit konkreter Pause vor 22 Uhr genau
2 Stunden. Randdienste zählen nicht doppelt. Die Wochen-/R-/Abrechnungsprofile
bleiben davon unabhängig ausdrücklich dokumentiert.

Die zusätzlichen Bedarfs-/Datumsoptionsregressionen sind bestanden.
Abschließender vollständiger Lauf des jetzt eingefrorenen Codes:
**401 bestanden in 106,16 s**. Keine Fehler/Skips. Der vorangehende Randdatenstand
0c30111 ist bereits auf allen drei nativen Zielen vollständig erfolgreich
geprüft (Run 42892087768); die aktuelle zusätzliche Bedarfsanzeige wird vor
Verlinkung nochmals in den tatsächlich gebauten Paketen geprüft.

Native Matrix des Programmstands 0e1735f: Windows und Apple Silicon erfolgreich.
Intel scheiterte in zwei unveränderten Versuchen an der bisherigen Legacy-Regression
`test_twelve_people_special_slots_distributed_without_repetition`: nach acht Sekunden
maximal drei statt eines besonderen Einsatzes pro Person. Der Plan war gültig und
vollbesetzt; die Fairnesssuche noch unvollständig. Derselbe Test ist kein Vertrag
über Fairness innerhalb von acht Sekunden auf jeder Hardware. Nur sein Suchbudget
wird auf 30 s erhöht; alle Assertions bleiben erhalten (acht Einsätze insgesamt,
maximal einer pro Person, tägliche Typen höchstens ein Einsatz Unterschied).
Die unmittelbar folgenden expliziten Timeout-/Startplanprüfungen bleiben unverändert.
Kein Solver-/Produktcode wird wegen dieser CI-Kalibrierung geändert und kein
8-Sekunden-Fairnessnachweis aus dem späteren Lauf behauptet. Beide Fehlversuche
sind in Run 42894838022 dokumentiert. Neue native Prüfung folgt mit dieser
präzise benannten Testkonfiguration. Lokal gezielte Fairness- und unveränderte
Timeout-/Startplanregression: **2 bestanden in 31,62 s**.

Kalibrierter vollständiger Lauf: **401 bestanden in 134,30 s**. Zusätzlich
native Excel-Zelltypen geprüft: Datum/Gutschrifttag bleiben reine Daten,
Beginn/Ende/Pause behalten ihre Uhrzeit statt auf Mitternacht gekürzt zu werden.
Regression: FK 15:00–23:00 mit Pause 19:00–19:30 bleibt 450 Arbeitsminuten,
Gutschrifttag als echte Excel-Datumszelle bleibt 10.11.2026.
Relevante gesamte Tabellen-/Qt-Prüfung: **44 bestanden in 29,49 s**.
Keine weitere fachliche Interpretation von R/U/KC15/Donnerstagswünschen.

Letzter vollständiger Lauf einschließlich nativer Excel-Zelltypen und
kalibriertem unverändertem Fairnessziel: **402 bestanden in 136,65 s**.
Die Intel-Matrix des vorangehenden Testkalibrierungsstands besteht nun ebenfalls
die Tests; Windows und Apple Silicon dort bereits vollständig erfolgreich.
Die abschließenden Programmdateien werden einschließlich Uhrzeit-Erhalt aus
echten Excel-Zellen erneut gebaut; danach folgen nur noch Prüfbericht/Links.

Programm-/Teststand **4e74b10** ist auf `feat/v2-implementation` gepusht.
Endgültige native Matrix [Run 42899281763](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42899281763) vollständig erfolgreich:
Windows x64 und macOS Sequoia ARM64/Intel einschließlich Tests, Build und neuer
Paketprobe. Aktuelle Paketlinks/Messwerte: [V2_NATIVE_PRUEFUNG.md](V2_NATIVE_PRUEFUNG.md).
Linux-Paket des identischen sauberen Standes ebenfalls gebaut/geprüft.

Unabhängige Implementierung und private Formatvorlagen sind geliefert. Die
vollständige aktive Übernahme aller privaten Excel-Zeilen bleibt von den oben
genannten konkreten Fachantworten und der Korrektur echter Regelkonflikte abhängig.
Keine unbestätigte Ausnahme erfunden. Nächster abhängiger Schritt: Antworten zu
Donnerstag-X, KC15, R/U und KC10 am 31.12. übernehmen, die betroffenen Vorlagen
anpassen und die konkrete Gesamtübernahme erneut prüfen. Die von Fachantworten abhängigen Importzeilen
bleiben bis zur Klärung vorgemerkt.


## Aktueller Fehlerbericht: berechneter Dienstplan bleibt unsichtbar (0.3.1)

Ursache reproduziert: `on_worker_completed()` legte das Ergebnis ausschließlich
in `pending` ab. Weder Plantabelle noch Stunden-/Verteilungs-/Wunschtabellen
wurden aktualisiert; erst der zusätzliche Übernahmeklick machte es sichtbar.
Der Ablauf war in den bisherigen Tests auf explizite Übernahme geprüft, aber
nicht auf die Sichtbarkeit vor dieser Übernahme.

Korrektur: Jeder gültige aktuelle Vorschlag wird unabhängig geprüft, sofort in
allen Ergebnistabellen angezeigt und der Dienstplan-Reiter automatisch geöffnet.
Vorschaukennzeichnung und Zuteilungs-/Offen-Zähler unterscheiden Vorschlag,
gespeicherten Plan und Ergebnis ohne Zuteilungen. Personen erscheinen mit Namen
und stabiler ID. Der bisherige Plan bleibt bis zur ausdrücklichen Übernahme in
Speicher und SQLite erhalten; Verwerfen stellt ihn sichtbar wieder her. Export
verwendet den sichtbaren Vorschlag. Manuelle Änderungen/Bestätigungen verlangen
zuerst Übernahme oder Verwerfen. Veraltete und ungültige Ergebnisse werden nicht
als Vorschau dargestellt; Eingabeänderungen entfernen die veraltete Vorschau.

Neue Regressionen: echter Qt-Worker mit unmittelbar sichtbaren Zuteilungen und
Stunden vor Übernahme, Tabwechsel, unveränderter vorheriger SQLite-Stand,
Verwerfen, Export des sichtbaren Ergebnisses, Übernahme/Neustart, Eingabeänderung,
Teil-/Nullbesetzung und Ablehnung eines regelwidrigen Resultats. Die native
Paketprobe verlangt jetzt zusätzlich `vorschau_anzeige=true` und prüft die echte
Qt-Anzeige vor dem Übernahmeklick. Kein Absenken fachlicher Regeln.

Prüfungen: `.venv/bin/python -m pytest tests/test_v2_ui.py -q` zunächst
12 bestanden (vor zusätzlichem Invalid-Ergebnis-Test). Abschließend
`.venv/bin/python scripts/run_tests.py`: **368 bestanden in 84,15 s**.
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m dienstplan --self-test
--self-test-report /tmp/preview-smoke.json`: bestanden, einschließlich echter
Vorschauanzeige und Übernahme in SQLite.

Programm-/Teststand **bbb6909** ist auf `feat/v2-implementation` gepusht.
Eigenständig startbares Linux-Paket gebaut und mit `check_v2_package` bei leerem
System-Zeitzonenpfad geprüft: **bestanden**, `vorschau_anzeige=true`, Version
0.3.1, saubere Buildkennung bbb6909. Gemessen 294.033.766 Bytes / 280,41 MiB,
Archiv 114.297.571 Bytes / 109,00 MiB. Zusätzliche visuelle Qt-Probe: acht sichtbare
Zuteilungen vor Übernahme, null gespeicherte Zuteilungen im ursprünglichen leeren
Entwurf; keine echte Benutzerdatenbank verwendet.

Native Matrix: [Run 42870257885](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885).
Native Prüfung vollständig erfolgreich: [Run 42870257885](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885).
Windows x64 und macOS Sequoia ARM64/Intel haben Tests, Build und die verschärfte
Paketprobe mit `vorschau_anzeige=true` bestanden. Aktuelle Paketlinks und tatsächliche
Messwerte: [V2_NATIVE_PRUEFUNG.md](V2_NATIVE_PRUEFUNG.md).
Der Anzeigefehler ist damit behoben und auf allen drei Zielarchitekturen automatisiert
geprüft; keine zusätzlichen Fachprofile oder echte Datenmigration freigegeben. Keine Änderung echter Benutzerdaten.
Die folgenden Abschnitte sind der bisherige Verlauf.


## Aktueller Folgeauftrag: eine Hauptoberfläche, Ausschlüsse und Stunden

Der ausdrückliche Auftrag vom 10.11.2026 ersetzt die bisherige Startauswahl
und parallele Testoberfläche. Version **0.3.0** startet ausschließlich die
V2-Monatsanwendung mit dauerhafter `dienstplan-v2.sqlite3`.
Die vorherige `dienstplan.sqlite3` bleibt bytegleich unberührt; alte V2-Dateien
mit Schema 3 bleiben ladbar. Kein Merge nach main und keine echte Datenmigration.
Die nachfolgenden älteren Verlaufsabschnitte bleiben historische Belege.

Implementiert:

- Einziger Startweg, sichtbar benannte Version/Buildkennung, echter Neustart mit
  gespeicherten Monatsdaten. Kein temporärer Vier-Termine-Stand beim normalen Start.
- Vollständiger Standardkatalog mit 17 Kürzeln/19 Varianten. Neue Monate erzeugen
  die bestimmten Tagesmuster und saisonalen R-Fenster automatisch. November 2026:
  94 Termine, 120 operative Plätze, 876,00 Stunden ohne Sonderdienste/Reserve.
  Keine erfundenen WL/BK-Quoten, LB-Anker, festen Personen oder Sonderdaten.
- Personenmaske mit zeitgültigen ausgeschlossenen Diensten und anklickbarer
  Ausschlussliste. Leer heißt keine Ausschlüsse; Führerscheinprüfung bleibt extra.
  Bestehende gespeicherte Rechte werden über das Komplement verlustfrei abgebildet.
- Alle Dauern/Konten/Verteilungsmengen in Oberfläche und CSV in Stunden;
  Uhrzeiten bleiben Uhrzeiten. CSV-Formatversion 2 benennt Stundenfelder,
  Arbeitsstand-JSON bleibt exakt in Minuten. Unverändertes Speichern erhält auch
  einzelne Minuten und exakte Vertragswerte. Neue Konten behalten E=0.
- Monatswechsel übernimmt Personen, Verträge und Ausschlüsse, erhält Anfangssalden
  beziehungsweise verwendet bestätigte Vormonatsprognosen; E wird für neue Monate null.
- TS/T und W16/W17 ersetzen beim Ergänzen das vorhandene Standardgegenstück;
  TS verlängert vorhandenes LB. Keine doppelten Veranstaltungen/operativen Bedarfe.
- Modellaufbau für vollständige Monate: Zuordnungsvariablen teilen Anwesenheits-
  und Ruhekonflikte über Pausenvarianten. Die bestätigte Vorwochen-Freipaarregel
  wird mit derselben Randdaten-Unbekanntbehandlung wie im unabhängigen Prüfer
  kompiliert. Rein dominante Pausenlagen mit identischen Monats-/Gesamtarbeitsmengen
  werden nur im Suchmodell reduziert; vorhandene/fixierte Pausen und sämtliche
  Arbeitsabdeckungs-/Vertretungsrollen bleiben erhalten. Eingabekandidaten bleiben
  vollständig für manuelle Änderungen verfügbar. Keine Schutzregel entfernt.

Offene F01–F14 werden nicht durch den UI-Wechsel beantwortet. S0/M0/E0 wird vor
neuer Berechnung ausdrücklich ausgewählt; ein bestätigter Rechenstand ist keine
KV-/BV-/Rechtsfreigabe. F06/F07 blockieren weiter verbindliche WL/BK-Wochenquoten,
F08 LB ohne Referenzdatum, F02 Reserve-Arbeitsbewertung. Alle 125 Abnahmefälle
behalten ihren tatsächlichen Status; der Oberflächenwechsel besteht sie nicht
pauschal. F1 ist verbessert, bleibt bei vollständiger Profilkonfiguration und
Aufhebung bestätigter Stände teilweise offen. Der produktive Abrechnungsstichtag
F14 wird aus dem Download nicht abgeleitet.

Tatsächliche Prüfungen dieses Folgeauftrags:

- Ausgangskontrolle `.venv/bin/python scripts/run_tests.py`: **339 bestanden,
  76,51 s**.
- Zwischenstand nach UI-/Stunden-/Ausschlussänderung: **360 bestanden, 84,85 s**.
- Erforderliche Anpassungen alter Tests: Startauswahl-/Legacy-Start-Erwartungen
  sind durch den ausdrücklichen Auftrag überholt; sie prüfen jetzt den einzigen
  V2-Einstieg und den unveränderten Altdatei-Hash. Zeitspalten ändern ausschließlich
  ihre Einheit/Namen; insbesondere unbekannte Gutschriften/Feiertage bleiben `null`.
  Der alte Paketbericht mit 186 Vier-Schichten-Zuteilungen gilt nicht mehr als
  Nachweis der neuen App. Die Paketprobe verlangt jetzt sichtbare Hauptoberfläche,
  Standarddienste, Ausschlussliste, Stundenanzeige und persistenten Neustart;
  Solver/DST/SQLite/Export werden zusätzlich mit isolierter synthetischer Fixture geprüft.
- Visuelle Qt-Offscreen-Probe der tatsächlichen Hauptoberfläche; kleine Mindestgröße
  800 × 458, normale Fenstergröße 1360 × 900. Kein nativer Nachweis daraus abgeleitet.

- Abschließender Gesamtlauf `.venv/bin/python scripts/run_tests.py`: **362 bestanden,
  110,81 s**, keine Fehler/Skips. Paketquellprobe `QT_QPA_PLATFORM=offscreen
  .venv/bin/python -m dienstplan --self-test --self-test-report /tmp/dienstplan-ui-smoke.json`:
  bestanden, einschließlich echter Hauptoberfläche, 19 Varianten/94 Novemberterminen,
  Ausschlüssen/Stunden und persistentem Neustart.
- Vollständiger synthetischer November mit zwölf Personen à 25 h und allen bestimmten
  Tagesmustern: bei 45 s Suchlimit **0 offene operative Plätze**, 146 Dienstblöcke
  einschließlich freiwilliger T-Teilnahmen; Gesamtdauer einschließlich Nachprüfung
  46,05 s. Bedingt gültig wegen ausdrücklich offener Profile/Randdaten; kein
  vollständiger Optimalitäts- oder Rechtsnachweis behauptet. Bei 20 s blieben in
  einem Lauf 2 Plätze offen (gültiger unvollständiger Entwurf). Standardzeit der
  Hauptoberfläche daher 60 s, weiterhin änderbar/abbrechbar.

Programm-/Teststand **4035132** ist auf `feat/v2-implementation` gepusht.
Linux-Paket tatsächlich gebaut und mit deaktiviertem System-Zeitzonenpfad geprüft:
294.024.047 Bytes / 280,40 MiB, Archiv 114.309.689 Bytes / 109,01 MiB.
Paketprobe vollständig bestanden; Buildkennung stimmt mit dem sauberen Commit
überein. Im Paket keine SQLite-Benutzerdatenbanken gefunden. Die native Matrix
läuft unter [Run 42830290050](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050).

Native Prüfung abgeschlossen: [Run 42830290050](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050)
ist vollständig erfolgreich. Windows x64 sowie macOS Sequoia ARM64/Intel haben
Tests, Build und die neue Paketprobe bestanden. Aktuelle Downloads/Messwerte:
[V2_NATIVE_PRUEFUNG.md](V2_NATIVE_PRUEFUNG.md). Der neue Pakettest bestätigt die
Hauptoberfläche mit Standarddiensten, Ausschlüssen, Stunden und Neustart sowie
die zusätzliche synthetische Rechenkette. Kein bloßer Legacy-Selbsttest.

Der begrenzte Oberflächenfolgeauftrag ist umgesetzt und geprüft. Das Gesamtprojekt
bleibt bei den dokumentierten offenen Fachprofilen, vollständiger Monatskonfiguration,
bestätigter Übernahme/Abrechnung und manueller Endgeräte-/Signierprüfung offen.
Nächster fachlicher Schritt: nur die von F01–F14 abhängigen Funktionen nach den
jeweiligen tatsächlichen Entscheidungen freigeben; keine neuen Betriebsprofile
oder Datenübernahmen aus dem UI-Wechsel ableiten.

## Folgeauftrag: Artefakte wirken wie die alte Version

Die Rückmeldung wurde am 10.11.2026 nachvollzogen: Auch das neue Paket startete
in `MainWindow` der bisherigen Vier-Schichten-App und öffnete deren lokale
Benutzerdatenbank. Das war wegen der ausdrücklich nicht beauftragten produktiven
V2-Umschaltung so angelegt; der alleinige Menüeinstieg in den V2-Prüfbereich war
jedoch zu wenig sichtbar. Die Paketversion 0.2.0 allein unterschied die neuen
Entwicklungsstände ebenfalls nicht. Alte Benutzerdaten waren nicht im Build
gebündelt und wurden nicht nach V2 migriert.

Korrektur: explizite Startauswahl vor jedem Datenbankzugriff beim normalen Start,
sichtbare V2-Schaltfläche und reguläres Bereiche-Menü in der bisherigen App,
eindeutiger Fenstertitel für den Vier-Schichten-Bereich und Offline-Paketkennung
mit Commit in beiden Fenstern. V2-Auswahl öffnet keine Legacy-Datenbank. Direkte
Entwickleraufrufe `--v2`/`--legacy`; bisherige explizite Datenbank-/Demoaufrufe
bleiben kompatibel. Archivnamen enthalten künftig die Build-Commitkennung.
Keine produktive Aktivierung und keine Änderung/Löschung echter Benutzerdaten.

Regression: normale Startauswahl und `--v2` mit echtem Qt-Ereignisloop,
unveränderter synthetischer Altdatei und verbotenem Legacy-Store-Zugriff;
Abbruch legt keine Datei an. Paketprobe verlangt nun Startauswahl, eingebettete
Commitkennung und Übereinstimmung mit dem Buildbericht. Gesamtlauf:
**339 bestanden in 96,90 s**; gezielte Start-/Einstieg-/Paketprüfungen danach
**13 bestanden in 0,73 s**. Der aktualisierte Startdialog wurde offscreen visuell
geprüft. Neue native Pakete werden vor Verlinkung tatsächlich gebaut/geprüft;
vorherige native Belege bleiben getrennt in `native-vor-startauswahl.json` erhalten.

Basis: Etappe A `0a0bc48`, Arbeitsbranch `feat/v2-implementation`.
Aktueller geprüfter Programm-/Teststand: `32e3732`, **339 lokale Tests grün**,
alle drei nativen Zielarchitekturen einschließlich Paket-/V2-Selbsttests grün in
Run `42821811250`. Zwischenzeitlicher Anmeldeausfall ist behoben; Push/API wieder
funktionsfähig. Größen/Artefaktlinks: [V2_NATIVE_PRUEFUNG.md](V2_NATIVE_PRUEFUNG.md).
Die produktive Altanwendung bleibt unverändert; keine V2-Umschaltung, kein Merge
nach main und keine Migration einer echten Benutzerdatenbank.

## B1 – Zeit-, Arbeits- und Vertragsgrundlage

Implementiert: unveränderliche UTC-Intervalle, explizite Wien-Auflösung mit
Rückkonvertierung, Existenz-/Mehrdeutigkeitsprüfung, Offset/fold, Schnitt/Differenz,
reale Ruhe, Tages-/Monatsschnitte, konkrete Pausen mit Normalregel und geschützten
Fenstern, getrennte Anwesenheitsbelegung und physische Nacht-/Sonntags-/Feiertagsmengen.
Beschäftigung (Datum ende-exklusiv, inklusive Eingabehilfe), datierte exakte
Vertragswerte, Überlappungs-/Lückenprüfung, explizite Urlaubstage mit monatlich
einmaliger Rundung, nur ausdrücklich gewähltes technisches S0 und reine Kontowerte.
M0-/Euro-/Reserve-/Tarifbewertung wird nicht automatisch gewählt.

`tzdata==2026.6` in direkten und gesperrten Abhängigkeiten. Wien wird aus diesem
Paket geladen; IANA-/Paketversion sind zugänglich. Der isolierte Prozess mit
`PYTHONTZPATH=""` belegt Offlinebetrieb ohne Systemtzdb und ohne Qt/SQLite/OR-Tools-
Import der B1-Module. Native Pakete/Starts sind noch nicht neu geprüft.

### Tatsächliche Prüfungen

- Ausgang: `QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/dienstplan-v2-qt-cache .venv/bin/python scripts/run_tests.py`:
  **158 bestanden, 61,25 s**.
- ` .venv/bin/python -m pytest -q tests/test_v2_foundation.py`: neue fokussierte Fälle.
- ` .venv/bin/python -m pip check`: keine widersprüchlichen Abhängigkeiten.
- Gesamtlauf nach B1: **200 bestanden, 66,49 s**, keine Fehler oder Skips.

### Abnahmezuordnung B1

Vollständig als reine Fach-/Rechenfunktion: Z01, Z08, Z09, Z11, K01, K03, K04,
K06, K07, K08. Teilweise: P05/P06 (Beschäftigung ohne Rechteprüfung), P07
(Verträge), R04/R07/R08 (Zeit-/Tageswerte ohne vollständigen Regelprüfer),
Z02–Z06/Z10 (Mengen/Fenster ohne Katalog/Optimierer), K02/K05/K09 (Kontowerte,
keine Anwendungskonten/Fairness), L03/L04 (übergebene Feiertagsmenge, keine Tarife).
Alle anderen der 125 Fälle sind zunächst späteren Etappen zugeordnet, keine
aufgeschobenen Tests als bestanden gezählt.

## B2 – Katalog, Rechte und Korrekturverfahren

Umgesetzt: alle 17 Kürzel mit getrennten R-Fenstern/LB-Varianten, feste Personen,
Donnerstagsersatz, LB-Rhythmus mit explizitem Anker, Reserveperiode, W16 als
derselbe Außendienstbedarf mit Grund. Kalender nennt fehlende WL/BK-/FK-/Reserve-
Profile und fehlende INT/N17-Daten, statt Termine/Personen zu erfinden.
Zeitgültige Rechte und N17-Führerschein, Außendienstprofil inklusive T/TS,
explizite Team-Erfüllung und geschützte Fenster. Keine Teilnahme aus zufälliger
Überlappung. Konkrete B1-Pausen bleiben Pflichtinput, kein Pausenoptimierer.

CSV-Format 2 mit typisierten Einträgen, vollständigen Korrekturstapeln,
gemeinsamer Budgetprüfung, Identitäts-/Gutschrift-Deduplizierung und Bearbeitung.
Fehlerhafte Stapel können nie aktive Teilmengen liefern. Strukturfehler bleiben
auch nach Bearbeiten einer vorherigen gültigen Zeile erhalten. Speicherung der
Vormerkung folgt in B3; die Legacy-UI bleibt unverändert.

Prüfung: `tests/test_v2_catalog_entries.py tests/test_v2_foundation.py`:
**73 bestanden**. Gesamtlauf: **231 bestanden in 71,78 s**.
Zusätzlich abgedeckt als Domain-/Kalenderfunktion: D01–D06, D08, D10–D12,
P01–P04/P08, Q09/Q10, W02/W04–W07, I01–I05; teilweise D07/D09,
Q05–Q07/Q11, W01/W03/W08–W10 und Z02/Z05/Z06. Speicher-/Solver-/UI-Anteile
dieser Fälle bleiben offen und sind keine Ende-zu-Ende-Abnahme.

## B3 – Profile und Kopienspeicher

Versionierte Profile mit Gültigkeit/Anwendung, exakten JSON-Parametern,
Quellenbelegen, expliziter Bestätigung und abgetrennten synthetischen Profilen.
Schreibgeschützter Legacy-Reader, SQLite-Backup einschließlich committed WAL,
additive Schema-3-Kopie, bytegleiche alte Monats-Payloads/Sperren, Integritäts-
und FK-Prüfung, kein Überschreiben des Originals oder fremder Zieldateien.
Fehlerinjektionen nach Backup/DDL/vor Commit einschließlich KeyboardInterrupt,
Idempotenz und Wiederöffnung geprüft. Keine Personen-/Urlaubs-/BK-/WL-Zuordnung
aus fehlenden Altdaten erfunden.

Persistente Korrekturstapel mit erneuter gemeinsamer Prüfung innerhalb der
Übernahmetransaktion, Revisionsprüfung und vollständigem Rollback. Unveränderliche
Profile und Entwurfsrevisionen; noch keine produktive Bestätigungs-/Historien-API.
Das Schema enthält nur die tatsächlich benötigten Speicherbereiche; weitere
Repositories/Migrationen werden mit ihren jeweiligen Funktionen ergänzt.

`tests/test_v2_persistence.py`: **11 bestanden** (nur synthetische Datenbanken).
Gesamtlauf: **242 bestanden in 91,76 s**. M01–M07 und I06 sind als isolierte
Speicher-/Migrationsfälle abgedeckt, M08 teilweise (noch keine Anwendungskonten).
W08 ist nun als Speicher-/Neustartverfahren abgedeckt, noch nicht über die UI.

## C1 – Unabhängige Kernprüfung

Direkt aus Ergebnisblöcken geprüft: Referenzen/Duplikate/Kapazität, feste Personen,
Katalogzeiten, Rechte/Führerschein/Beschäftigung, benötigte Vertragsversionen,
Urlaub, geschützte Teamzeit und LB-Verlängerung, ein Block je Startdatum,
reale 660-Minuten-Ruhe und höchstens fünf belegte Arbeitstage inklusive Randpause
und alter Randdienste. Alte Konflikte ohne Bezug zu neuer Zuteilung werden nicht
nachträglich umgeschrieben. Enthaltene Teilnahme wird separat erklärt.
Der Bericht kennzeichnet seinen Kernumfang ausdrücklich als keinen vollständigen
V2-/Rechtsnachweis. Keine Solverflags werden als Regelbeleg übernommen.

`tests/test_v2_validation.py`: 10 gezielte Fälle einschließlich exakter 660/659-
Grenze, Jahresrand und manipulierter Pause in Teamzeit. Gesamtlauf: **252 Tests bestanden**, Details im aktuellen JUnit-Bericht.
R01–R08, U07, P01–P07 und O09 sind damit auf Kernprüferebene abgedeckt;
Wochenenden/Quoten, komplette UI und produktive Profile bleiben separat.

## C2 – Wochenenden, Randdaten und Quoten

Vollständiger technischer Horizont mit Vor-/Nachlauf, explizit bekannte Tage,
unbekannte Zukunft statt angenommener Freizeit, zusammenhängendes Mo–Fr-Freipaar
vor beobachteter Wochenendarbeit und enge W17-Zählausnahme. Die Ausnahme ändert
keine Arbeitstags-/Vorwochenbelegung. Historische Konflikte ohne Beteiligung neuer
Zuteilungen werden nicht rückwirkend beanstandet.

Monats-Wochenendquote mit ausdrücklich benanntem Testprofil; Besitzer/Teilmonats-
quote/Zuordnung nicht automatisch gewählt. Gemeinsame stabile Wochenquoten-IDs,
parametrisierter Saisonanker, eindeutige WL-Tage und WL/BK-Ausschluss. Fehlende
Profile/Randdaten ergeben „nicht vollständig geprüft“, keinen Gesamtnachweis.

`tests/test_v2_calendar_rules.py`: 8 Fälle; zusammen mit C1 18 bestanden.
Gesamtlauf: **260 Tests bestanden**. R09–R17 und Q01–Q04/Q07 sind als Prüfer-/Quotenfunktionen
abgedeckt, nicht als bereits fertige automatische Terminwahl. D2 bleibt getrennt.

## D1 – Kleine echte Machbarkeitsmodelle

CP-SAT wählt aus konkreten gültigen Personen-/Pausenkandidaten, erhält feste
Personen und lässt unbesetzbare Plätze offen. Startdatum, Ruhe und Fünferfolgen
sind modelliert; unabhängige Kern-/Kalenderprüfung verwirft ungültige Ergebnisse
mit exakten Ausschlussschnitten. Das ist für kleine Modelle vorgesehen, noch
kein skalierter Monatscompiler. Fehlende Randdaten/Produktprofile bleiben sichtbar.
Gültiger Altentwurf als Startpunkt, Abbruch/Zeitlimit, unveränderlicher
Eingabefingerprint einschließlich tzdata und abschließende Ergebnisprüfung.
„Besetzung optimal“ belegt nur diese Stufe, keine globale Fairness-/Rechtsoptimalität.

`tests/test_v2_solver.py`: 9 bestanden. Gesamtlauf mit konkretisierten
Fixierungsdiagnosen: **269 bestanden in 69,28 s**.
O01/O02/O05/O09 sind auf kleiner Solver-/Prüferebene abgedeckt; O06 teilweise
(Besetzungsbeweis, noch keine mehrstufige Optimierung). Noch keine produktive
V2-App-Anbindung, keine Pausenvertretung oder automatische Wochen-Terminauswahl.

## D2 – Gekoppelte Termin-/Personen-/Pausenwahl

Optionale WL/BK-Daten sind echte CP-SAT-Terminvariablen mit gemeinsamen stabilen
Wochenquoten und getrennten Datums-/Personenvorgaben. Verschiedene WL-Tage,
WL/BK-Ausschluss, Randwochenprofile und konkrete Pausenvarianten werden zusammen
gelöst. Nicht existierende lokale WL-Endzeiten werden mit Ursache als unzulässige
Option gemeldet, nicht verschoben. Gewählte Termine bleiben auch ohne Personal
als offene Bedarfe erhalten; der Ergebnisprüfer prüft dieselbe Terminauswahl.

Explizite Abdeckungs-Testprofile prüfen tatsächliche Arbeit je UTC-Teilsegment,
einschließlich dedizierter realer Vertretungstermine. Keine doppelte Person/
gleichzeitige Vertretungsrolle, keine neuen Halbblöcke. Bei offenen Plätzen ist
die fehlende Abdeckung ausdrücklich offen; erst Vollbesetzung belegt das ganze
Abdeckungsprofil. Ohne F03 gibt es keinen produktiven Abdeckungsnachweis.

`tests/test_v2_coupled.py tests/test_v2_solver.py`: **19 bestanden**.
Gesamtlauf einschließlich DST-Kandidatendiagnose: **279 bestanden in 100,33 s**.
Q01/Q02/Q05/Q06/Q07 und Z07 sind als kleine integrierte Testprofilfälle abgedeckt;
Q03/Q04 bleiben gemeinsame Quoten-/Randfunktionen, Q08 folgt als weiches Ziel.
Keine betriebliche Freigabe der offenen F03/F06/F07, keine vollständige Monatsabnahme.

## E1 – Rohhistorie, Wünsche und getrennte Rechenmengen

Implementiert: relevante eindeutige Wunschmengen, zwei explizite Varianten für
die Freitags-W17-Wunschbehandlung, getrennte aktuelle/historische/kumulierte
Belastung und sichtbare Historienlücken. Bestätigungsfakten enthalten damalige
Eingaben/Verträge, Wunschschlüssel, Roh-/Rundungswerte, Konten, berechtigte
Sollanteile und physische Mengen. Kein Entwurf erhöht die Historie; gleiche
Testbestätigung ist idempotent, spätere Blocker-/Vertragsänderungen schreiben
die Vergangenheit nicht um. Monatsübergreifende Wunschschlüssel werden kumuliert
vereinigt. Gemeinsame Randwochenbindungen werden transaktional erhalten.

Bestätigungen bleiben derzeit **ausschließlich synthetische Testbestätigungen**.
Produktive Bestätigung und stilles Ersetzen bestätigter Monate sind gesperrt.
Revision, unabhängige Regeln, Vollbesetzung und Datenfingerprints werden geprüft;
Speicherfehler rollen Revision und Bestätigungszeiger vollständig zurück.
Eine Aufhebungs-/Ablösungsbedienung ist noch nicht implementiert.

Exakte S0-/M0-Prognosen mit expliziten Konten und deduplizierten Urlaubstagen,
getrennte Nacht-/Sonntags-/Feiertagsmengen, berechtigte Vertrags-/Absolutanteile
und eingefrorene historische Sollanteile. Bei ausschließlich Nullstunden erzeugt
das Vertragsprofil keine erfundenen Anteile; ein absoluter Vergleich ist separat
wählbar. Nationale AT-Daten nur als technischer Testkalender. Zeitgültige
synthetische Einzelraten sind berechenbar; fehlende KV-/BV-Basis ergibt Euro
„ungeklärt“, keine Nullbewertung oder automatische Kumulationsregel.

`tests/test_v2_history_reporting.py tests/test_v2_persistence.py`: **23 bestanden
in 1,98 s**, einschließlich eingefrorener historischer Sollanteile.
Gesamtlauf: **291 bestanden in 63,80 s**, keine Fehler oder Skips.
H01–H03, W03/W10 und U03/U04/K05/K09 sind als Domain-/Testbestätigungsfunktionen
abgedeckt; L01/L02/L05/L06 nur mit ausdrücklich synthetischen Kalender-/Tarifdaten.
H04–H06 sind noch keine optimierte Fairnessabnahme. E2 und UI-Anbindung fehlen.

## E2 – Stufen, bessere Entwürfe und Nachbarschaften

Am 10.11.2026 wiederaufgenommen; Ausgang erneut **291 Tests bestanden in 65,05 s**.
Benannte explizite Testzielprofile; Besetzung immer zuerst, danach konfigurierbare
Teilnahme/Wünsche/Gruppen/Belastung/Stunden/Schichten/Termin-/Pausenpräferenz.
Höhere beste Werte werden festgehalten. Direkte Bewertung wird mit jedem CP-Ziel
verglichen. Getrennte Präfix-/Stufenbeweise, bedingte spätere Optima und abschließende
Neubewertung. Kein globaler Optimalitätsanspruch aus Besetzungsnull/Teilbeweisen.
Gültiger Altentwurf, Einzel-Fixierungen und konkrete Pausen bleiben erhalten.
Geprüfte Transfers, Zweiertausche und Dreierzyklen akzeptieren nur lexikografisch
bessere zulässige Ergebnisse; dadurch veraltete Beweise werden entfernt.

Technisches E0: Skala 1000, Stundenfehler ceil(1000×|P−Ziel|/max(S,60)); erst
Maximum, danach Quadratsumme. Schichtziel: Quadrate von Anzahlfehler×1000 und
auf Stunden umgerechneten Minutenfehlern, WL/BK vierfach. Sollanteile je Termin
aus berechtigtem Pool, danach einmal auf Skaleneinheiten gerundet; eingefrorene
Historie wird addiert. Offene Plätze verkleinern die Sollanteile nicht. Nullsoll
hat ausdrücklich Mindestnenner 60, keine Division durch null. Diese Reihenfolge
ist Testprofil, keine Entscheidung von F12/F13. Randbelegung bleibt echte Anwesenheit.

`tests/test_v2_objectives.py`: **14 bestanden**, einschließlich A=2/B=6 Wünsche,
historischer Belastung, Mehrfachtreffer, Stundenmangel, Tausch/Dreierzyklus,
Einzelfixierung, Nullsoll, bedingtem Nachweis und acht Einsätzen für zwölf Personen.
Gesamtprüfung: **305 bestanden in 67,60 s**. O04–O07/H04–H06 sowie Q08/Z04 sind
damit als kleine Testprofilfälle (keine Produkt-/Monatsabnahme) geprüft.
`scripts/v2_benchmark.py` vergleicht 5/20/60 s mit identischem gültigem Startplan,
Snapshot/Profil/Seed/Worker; tatsächliche Läufe in `examples/v2/benchmark-e2.json`.
Es sind ausdrücklich nur vier WL-Testtermine, kein rekonstruierter Betriebsmonat.

## F1 – Angebundener technischer Prüfbereich und Exporte

V2-Prüfbereich als explizites Fenster innerhalb der vorhandenen Qt-Anwendung,
getrennte temporäre/neue Schema-3-Testdatei. Name/Vertrag/Konten, datierte
Beschäftigung/Vertrags-/Berechtigungsversionen, feste Sondertermine und konkrete
Pausen, CSV-Korrekturvorschau, atomare Übernahme einschließlich aktualisierter
Eingaben und verworfenem Altentwurf, Hintergrundsuche/Abbruch, Versionskonflikt,
ausdrückliche Ergebnisübernahme, manuelle Zuteilungen/Einzelfixierungen und
unabhängige Nachprüfung sind angeschlossen. Normale App/Benutzerdatenbank bleiben
auf dem Legacy-Pfad. Keine produktive V2-Umschaltung.

Vollständiger exakter Workspace-Codec mit tzdata-/Katalogversion und Fingerprint,
unveränderlichen SQLite-Revisionen, geschützten Bestätigungen und Neustartprüfung.
Atomare neue ZIP-Exportpakete mit gemeinsamer Revision, CSVs/Arbeitsstand/Prüfmanifest
und Dateihashes; Schreibfehler veröffentlichen nichts, fremde Ziele bleiben erhalten.
Anleitung `V2_BEDIENUNG.md`; der kleine Mehrmonatslauf mit 2 s pro Monat ist in
`examples/v2/mehrmonats-zusammenfassung.json` dokumentiert. SQLite/ZIPs nur temporär,
keine Benutzerdaten oder Datenbank im Git. Wiederholte Bestätigung zählt nicht doppelt.

Fokussiert: Qt/Workspace/Export/Persistenz **23 Tests bestanden in 5,09 s**.
Gesamtlauf: **317 bestanden in 72,89 s**. X01–X03 sind für den ausdrücklich kleinen
Testbereich abgedeckt, kein fertiger produktiver Konfigurationsablauf. X04 teilweise:
Monatswechsel/Prognosesalden/Historie geprüft, noch keine vollständige
R-/Randwochen-/Urlaubsintegration oder betriebliche Vollmonatsmachbarkeit.
Bestätigungsaufhebung und die produktive Profilführung bleiben offen.
Der aktive Abwesenheitseditor wurde im nachfolgenden Änderungssatz ergänzt.

## F2 – Paketierter Selbsttest und native Prüfabläufe

PyInstaller bündelt tzdata ausdrücklich. Neuer Paketaufruf `--self-test-v2`
prüft Wien-DST, echte Optimierung/Prüfer, SQLite-Workspace, Export und sichtbares
Qt-Fenster in temporären Testdateien. Der native Paketprüfer führt jetzt sowohl
Legacy- als auch V2-Selbsttest aus; V2 mit leerem System-Zeitzonenpfad.
Vorhandene Windows-/macOS-Matrix verwendet diesen Prüfer, ohne Produktumschaltung.

Lokal: **320 Tests bestanden in 69,88 s**, zusätzliche fokussierte Qt/Paketprüfung
nach visueller Textbereinigung **16 bestanden in 3,47 s**. Linux x86_64-Paket
tatsächlich gebaut: **293.954.856 Bytes / 280,34 MiB**, TAR.GZ **108,97 MiB**.
Legacy-Paketselbsttest mit 186 Zuteilungen und V2-Test mit zwölf Personen/acht
Zuteilungen erfolgreich, einschließlich gebündeltem tzdata 2026.6 / IANA 2026f.
Keine Windows-/macOS-Abnahme aus diesen Linux-Ergebnissen abgeleitet.
Native Actions-Läufe werden nach dem Push gestartet und anschließend separat
mit tatsächlichem Commit/Architektur/Ergebnis dokumentiert. X05 bleibt bis zu
diesen Prüfungen und manueller Offline-/Signierungsabnahme teilweise offen.

## Nachprüfung: aktive Einträge und Windows-Export

Manuelle Erfassung/Bearbeitung/Löschung von Urlaub und Wünschen ist jetzt im
Prüfbereich angeschlossen. Ungültige Bearbeitung erhält den alten aktiven Eintrag
und die editierbare Vormerkung. Ersetzung prüft das Budget ohne Doppelverbrauch
und aktualisiert Eintrag/Workspace/Vormerkung atomar. Bestätigte Snapshots bleiben
geschützt. Beschäftigung und Vertragsgrundlage expliziter Gutschriften werden
auch bei reinen Eingaben vor Aktivierung geprüft; Fehlimport rollt vollständig zurück.

Native Erstprüfung von `4a04315`, Run `42722171266`: beide macOS-Sequoia-Builds
bestanden einschließlich Paket-/V2-Selbsttest; Windows scheiterte in zwei
ZIP-Exporttests. Der Flush verwendet jetzt ausdrücklich einen schreibbar geöffneten
Handle, wie Windows fsync/_commit verlangt. Regression erzwingt diese Voraussetzung
auch auf Linux. Fehlerursache steht künftig vor dem langen Traceback in der
CI-Annotation. Native Größen/V2-Nachweise werden als API-lesbare Notices ausgegeben,
weil der externe Blob-Logspeicher hier mit HTTP 403 gesperrt ist; GitHub-API-Checks
und Annotationen sind regulär erreichbar.

Abschluss vor erneutem nativen Lauf: **323 Tests bestanden in 70,62 s**;
fokussierter Editor/Workspace/Persistenzlauf vorher **26 bestanden in 4,95 s**.
Keine Anforderungen oder Tests gelockert. Nächster nativer Lauf prüft genau den
folgenden gepushten Commit, Ergebnisse werden anschließend ergänzt.

## Abnahmeprüfung und letzter Schutzsatz

Run `42723146880` auf `1d25a47` ist auf Windows x64 sowie macOS Sequoia ARM64/Intel
vollständig grün, jeweils inklusive gebautem Programm und Legacy-/V2-Selbsttest.
Der Windows-Exportfehler ist damit nativ nachgeprüft behoben.

Zusätzliche Abnahmegegenprobe U05: Urlaub ohne ausgewählte Gutschrifttage ist
verbindliche Abwesenheit mit **ungeklärter** Gutschrift, keine bestätigte Null.
Anzeige/CSV kennzeichnen unbekannte Werte; Stundenoptimierung und Bestätigung
werden zurückgestellt. Pläne/physische Mengen bleiben exportierbar. Dies
entscheidet weder die anrechenbaren Tage F05 noch die Feiertagsregel F04.
Die Alt-App lehnt Schema 3 jetzt vor der Journalumschaltung ab; eine synthetische
V2-Datei bleibt dabei bytegleich, ohne neu erzeugtes WAL. Keine echte Datei geändert.

**325 Tests bestanden in 73,36 s**; gezielte abschließende Qt-/Workspace-Prüfung
**17 bestanden in 3,71 s**. [V2_ABNAHMESTATUS.md](V2_ABNAHMESTATUS.md) ordnet alle
125 Fälle einzeln zu und präzisiert frühere gruppierte Etappenaussagen. Vollständige
Fachfunktion/Testprofil, Teilprüfung und noch fehlende Produktintegration sind
getrennt. Insbesondere ist X04 kein bereits bestandener vollständiger Betriebsmonat.
Ein abschließender nativer Lauf des folgenden Schutzsatzes wird separat belegt.

## Gemeinsame Team-Integration und aktueller Gesamtstand

`tests/test_v2_team_integration.py`: **4 bestanden in 8,48 s**. Echte gemeinsame
CP-SAT-Instanz mit zwölf Personen: D03 genau vier operative Plätze plus acht T,
3465 Minuten; D04 acht TS und vier enthaltene T-Ausnahmen ohne doppelte Teilnahme;
D07/O03 lässt BK-Personen bei nur 630 Minuten Ruhe ausgenommen; U04 berechnet
vorgegebene Urlaubstage über W=37/30 exakt mit 1968 Minuten. Kein bloßes UI-Beispiel.
Die Zuordnung D03/D04/U04 wurde entsprechend auf vollständige Fach-/Testprofilprüfung
angehoben. Das ersetzt weiterhin keinen vollständigen Betriebsmonat.

Letzter gesamter lokaler Lauf: **329 bestanden in 84,68 s**. Der Programmcode
`b358351` hat Run `42724231255` auf allen drei nativen Zielarchitekturen einschließlich
der 325 damaligen Tests und beider Paket-Selbsttests bestanden. Die vier zusätzlich
geprüften Teamfälle ändern keinen Programmcode; der anschließende native Lauf
führt auch diesen erweiterten Teststand aus und wird im nativen Bericht belegt.

## Offene Fachentscheidungen und Grenzen

Nachtrag zur Exportgrundlage: Nicht übergebene Feiertagsdaten sind im CSV `null`
und im Manifest ungeklärt; eine ausdrücklich leere Datumsmenge ist separat
erkennbar und verändert die Export-Revisions-ID. Keine behauptete Nullmenge aus
fehlenden Eingaben. Letzter lokaler Gesamtlauf hierzu: **330 bestanden in 79,56 s**.
Run `42725140124` hat den vorherigen erweiterten 329-Test-Stand auf allen drei
Zielarchitekturen bestanden. Das neue read-only Berichtsskript
`scripts/v2_native_report.py` wurde gegen einen abgeschlossenen echten Run geprüft;
es sammelt Messwerte, OS-/Architekturstände, Paketprüfungen und Artefaktlinks über
die erlaubte GitHub-API, ohne den gesperrten Blob-Logzugriff zu umgehen.

F01–F14 aus `V2_OFFENE_FRAGEN.md` bleiben offen, außer den dort ausdrücklich bereits
erledigten Klärungen. Donnerstagswünsche bleiben zur Korrektur vorgemerkt, ohne
aktive/teilweise Importübernahme. Testprofile sind ausdrücklich keine betrieblichen
Freigaben. Produktive Wunschhistorie und vollständige produktive Oberfläche sind
noch nicht freigegeben. Testprofiloptimierung ersetzt keine betriebliche Rechts-/Tarifprüfung.
Monatsskalierung des Kalenders mit Ausschlussschnitten ist weiterhin begrenzt.

## Verlauf der letzten nativen Nachprüfung (abgeschlossen)

Nativer Lauf `42726096163` von `527d639`: Windows und ARM64 bestanden, Intel
meldete im Wunschzähltest einen leeren Ergebnisbericht (`KeyError: wishes`).
Der identische Solverfall war in den vorherigen nativen Läufen grün; eine
garantierte Lösung innerhalb des dortigen Zwei-Sekunden-Limits ist keine
Fachanforderung und widerspricht der erlaubten Zeitlimit-Klassifikation.
Der fachliche Zähltest verwendet jetzt einen gültigen unveränderlichen Startplan
und 10 s; zusätzlich muss ein **bewiesener CP-Wunschzielwert** vorliegen. So kann
er nicht allein durch die direkte Nachbewertung des Startplans bestehen. Alle
bisherigen Kardinalitäts-/Zählassertionen bleiben erhalten; separate kontrollierte
Abbruch-/Zeitlimitfälle bleiben unverändert. Gezielte Ziel-/Teamprüfung hierzu:
**18 bestanden in 13,70 s**. Nächster nativer Lauf führt diese Präzisierung aus.
Gesamtlauf nach dieser Präzisierung: **330 bestanden in 94,71 s**.

Nutzer hat am 10.11.2026 selbstständige Fortsetzung bestätigt.
Zwischenzeitlich war die GitHub-Anmeldung ungültig. Der Bericht wurde lokal
gesichert und nach Wiederherstellung erfolgreich gepusht; der letzte Lauf wurde
anschließend vollständig kontrolliert. Keine produktive Umschaltung oder echte
Datenmigration ohne gesonderten Auftrag.

## Abschluss dieses technischen Änderungssatzes und Wiederaufnahme

Run `42727609885`, Commit `fa61c12`: Windows x64, macOS Sequoia ARM64 und Intel
vollständig erfolgreich einschließlich der 330-Test-Suite, Builds und beider
Paketselbsttests. Tatsächliche Paketgrößen und Downloadlinks sind in
`V2_NATIVE_PRUEFUNG.md` und `examples/v2/native-pruefung.json` belegt. Die zuvor
ungültige GitHub-Anmeldung war vorübergehend und blockiert nicht mehr.
Alle Programmänderungen sind auf `feat/v2-implementation` committed/gepusht;
kein Merge nach main, keine produktive Umschaltung, keine echte Datenbankmigration.

Der technische Zwischenstand ist keine vollständige Produktabnahme der 125 Fälle.
Offene F01–F14 begrenzen weiterhin die produktive Profilführung, R-/Tarif-/
Sollbewertung, Wochen-/Teilmonatszuordnung und vollständige betriebliche
Mehrmonatsabnahme. Insbesondere werden gesetzliche Werte nicht aus Testprofilen
übernommen. Die Frage nach F02/R-Bewertung wurde gezielt gestellt; ohne Antwort
keine volle Arbeit oder Freizeit unterstellen. Normale monatliche Eingaben sind
von diesen Fachentscheidungen getrennt zu erfassen.

Bei Fortsetzung zuerst Git-Stand, diese Datei, native Prüfnachweise und
`V2_ABNAHMESTATUS.md` lesen. Erledigte Etappen nicht neu beginnen. Nach geklärten
Profilen die jeweils abhängige produktive Integration und vollständige X04-/
Endgeräteabnahme ergänzen. Produktive Umschaltung benötigt weiterhin gesonderten
Auftrag. Dies ist ausdrücklich noch kein fertiges Gesamtprojekt.

## Folgeauftrag abgeschlossen: sichtbarer Einstieg und eindeutige Artefakte

Geprüfter Programm-/Testcommit `32e3732`, nativer Run `42821811250`: **Windows x64,
macOS Sequoia Intel und ARM64 vollständig grün**, jeweils 339 Tests, Paketbuild
und beide Paketselbsttests. Im Paket werden Startauswahl und eingebetteter Commit
zusätzlich geprüft und mit dem Buildbericht verglichen. Archive haben den Commit
im Namen; die alte 0.2.0-Basisnummer allein wird nicht mehr als Paketkennung benutzt.
Aktuelle Downloadlinks/Größen stehen in `V2_NATIVE_PRUEFUNG.md`, Rohdaten in
`examples/v2/native-pruefung.json`. Vorheriger Stand separat erhalten.

Lokaler Linux-Neubau und beide Selbsttests ebenfalls erfolgreich. Keine
SQLite-Benutzerdatenbank im Paket; echte bisherige Daten wurden nicht geöffnet,
gelöscht oder migriert. Die bisherige App bleibt über eine ausdrückliche Wahl
verfügbar. V2 startet getrennt mit fiktiven Testdaten. Dies ist eine Bedienkorrektur,
keine Freigabe einer fertigen produktiven V2-Anwendung.

## Folgeauftrag 10.11.2026: Regeln manuell und beim Import übergehen (0.4.1)

Implementiert: ausdrückliche, standardmäßig abgelehnte Warnbestätigung; alle
vorhandenen Personen manuell auswählbar; fachliche Objektregeln (Donnerstag,
Diensttag/-variante, Pausenfenster) bei bestätigter Ausnahme übergehbar;
CSV-/Excel-/manuelle Abwesenheitsübernahme einschließlich Wunschbudget.
Speicher und Reader erhalten Ausnahme-Kennzeichnung und bestätigte Meldungen;
Prüfer bleibt unverändert streng, Excel-/ZIP-Exporte weisen Verstöße aus.
Keine Aufweichung automatischer Solverregeln oder Erfindung unbekannter Zeiten.

Regressionen: neue synthetische Ausnahme-, Abbruch-, Speicher-/Neustart- und
Exporttests. Zwei bisherige Qt-Test-Erwartungen von Exception auf Ablehnen der
Warnung mit unverändertem Plan umgestellt: fachliche Grundlage ist der neue
Nutzerauftrag; die Schutzprüfung für nicht bestätigte Änderungen bleibt erhalten.
Gezielte Prüfung: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
 tests/test_v2_overrides.py tests/test_v2_ui.py --maxfail=2`: 26 bestanden.
Vollständige Prüfung und native Paketstände werden nach Abschluss ergänzt.

Aktueller Gesamtlauf: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
--disable-warnings --maxfail=1`: **411 bestanden in 146,61 s**. Abschließende
Qt-/Ausnahmeregression mit dem Status für noch ungeplante Monate: **26 bestanden
in 17,48 s**. Vorheriger Lauf meldete 409 bestanden/2 fehlgeschlagen (angepasster
Buttontext und Tuple/List-Rundlauf des neuen Manifestfelds); beides korrigiert,
keine fachlichen Erwartungen abgeschwächt. `git diff --check` fehlerfrei.
Version 0.4.1. Native Prüfungen werden im Buildlauf nach diesem Commit ausgeführt;
bisherige 0.4.0-Pakete enthalten die neue Ausnahmefunktion noch nicht.

Native Lieferung 0.4.1: Run **42912433306**, Programm-/Testcommit **72b168a**:
Windows x64, macOS Sequoia ARM64 und Intel vollständig erfolgreich. Testsuite,
Build und beide gebauten Programmproben je Ziel grün. Rohdaten unter
`examples/v2/native-pruefung.json`; 0.4.0 unter `native-0-4-0.json` archiviert.
Aktuelle Downloads und gemessene Größen: `V2_NATIVE_PRUEFUNG.md`. Nachfolgende
reine Nachweis-/Dokumentationscommits ändern diesen Programm-/Testcode nicht.
Keine Datenbankmigration; keine Zusammenführung nach main.

## Fehlerkorrektur: Termin löschen leert Plan / doppelte Fixierung (0.4.2)

Reproduziert mit synthetischen Daten: beide neuen Regressionen scheiterten vor
der Korrektur (leerer Plan nach `remove_term`, `Doppelte manuelle Fixierung`
beim Import mit erhaltenen Fixierungen und anderer konkreter Pause/Overrideflag).
Ursache: globales `clear_plan()` bei einzelnen Terminänderungen; Reimport verglich
Fixierungen als vollständige Objekte statt nach Termin-/Personenkennung.

Korrektur: Terminergänzung/-entfernung erhält alle unbetroffenen Zuteilungen und
Fixierungen; transaktionales Speichern vor UI-Änderung; gleiche Regelprüfung und
explizite Übersteuerung wie zuvor. Löschbestätigung nennt betroffene Einsätze.
Import verwendet eine eindeutige Fixierungszuordnung; bei früher geleertem
Entwurf werden verbliebene Fixierungen einschließlich konkreter Pausen in der
Vorschau wiederhergestellt. Kein Herabsetzen der strengen Domain-Duplikatprüfung.
Die Kopierfunktion heißt nun eindeutig „Datei kopieren“ (keine neue leere DB).

Neue Regressionen: Löschung plus erneuter Import, Speicher-/Neustartstand,
Abbruch und künstlicher Schreibfehler ohne Mutation, Terminergänzung ohne
Planverlust, Wiederherstellung aus kopierter alter Leerfassung, strenge Ablehnung
widersprüchlicher Fixierungen, Strukturprüfung ohne aktiven Plan. Nur synthetische
Dateien getestet; keine Benutzerdatenbank geöffnet oder migriert.
Testergebnisse und native Pakete werden nach Abschluss ergänzt.

Prüfungen: beide Fehler vor Änderung reproduziert (2 fehlgeschlagene neue Tests).
Gezielte Zwischenläufe: 47 bzw. 50 Tests erfolgreich. Gesamtlauf vor der letzten
Strukturregression: 417 bestanden in 191,21 s. Abschließender serieller Gesamtlauf
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q --disable-warnings
--maxfail=1`: **418 bestanden in 152,68 s**. Ein parallel zum ersten Gesamtlauf
gestarteter Qt-Lauf erreichte im bestehenden 1-Sekunden-Solvertest keine volle
Besetzung; unveränderte Erwartung im seriellen Gesamtlauf erfolgreich. Keine
Testanforderung oder Solverregel abgeschwächt. `git diff --check` fehlerfrei.
Native Pakete werden nach diesem geprüften Programm-/Testcommit erzeugt.

Native Lieferung 0.4.2: **Run 42917710392**, Programm-/Testcommit **304f3e1**.
Windows x64, macOS Sequoia ARM64 und Intel: alle Tests, Paketbuilds und
Programm-Selbsttests erfolgreich. Der langsamere Intel-Testlauf endete ebenfalls
erfolgreich, ohne geänderte Anforderungen oder Wiederholung. Aktuelle Links und
Größen: `V2_NATIVE_PRUEFUNG.md`; Rohdaten `examples/v2/native-pruefung.json`.
0.4.1-Nachweis unter `native-0-4-1.json` archiviert. Keine Benutzerdatenbank
verändert, keine Migration, kein Merge nach main. Reine nachfolgende Nachweis-
commits ändern den geprüften Programm-/Testcode nicht.

## Bedienkorrektur 0.4.3: manuelle Zuordnung und erneute Funktionsprüfung

Ursache reproduziert: manuelle Handler riefen bei normalem importierten Monat
ohne Wochenprofil das BK/WL-Fenster auf. Zwei neue Regressionen scheiterten vor
der Korrektur. Implizite Konfiguration aus manuellen Änderungen entfernt;
vorhandene konkrete Termine bleiben bei manueller Bearbeitung unverändert.
Fixierte Zuteilungen übertragen nach Bestätigung ihre Fixierung auf die neue
Person; Entfernen beseitigt auch die zugehörige Fixierung. Keine doppelte Belegung
einer Person innerhalb desselben Termins. Unpassende Berechtigungen und andere
fachliche Regeln bleiben nach ausdrücklicher Warnung übersteuerbar.

Zusätzliche Befunde: Wochenkonfiguration verwarf den Plan; sie erhält jetzt die
Zuteilungen und lässt bereits optionale Daten für spätere Optimierung frei.
Dateikopie schützt vor Kopieren des falschen Standes hinter einer Vorschau und
zeigt keine Korrekturvormerkung aus der alten Datei weiter an. Ursprünglicher
Korrekturstapel bleibt gespeichert. Keine Änderung bestätigter Historie.

Prüfumfang: `V2_BEDIENPRUEFUNG_0_4_3.md`. Neue durchgehende Qt-Prüfungen mit
normalem Monat, synthetischem Import, manueller Änderung, Speicherung, Exporten,
Dateikopie/Öffnen und Monatsnavigation. Bestehende 418 Tests als Ausgangskontrolle
in 146,86 s bestanden. Gezielte neue/Qt-/Paketprüfungen: 52 bestanden in 62,80 s;
zusätzliche Regression für erneute Wochenkonfiguration: bestanden in 11,28 s.
Quell-Selbsttest `QT_QPA_PLATFORM=offscreen .venv/bin/python -m dienstplan
--self-test-v2 --self-test-report /tmp/dienstplan-0.4.3-smoke.json` erfolgreich,
einschließlich tatsächlicher manueller Qt-Bedienung ohne Wochenprofil. Dieser
Nachweis `manual_assignment` ist jetzt für native Pakete verpflichtend.

Der bisherige Test erwartete bei der ersten manuellen Zuordnung das automatische
Öffnen der Wochenkonfiguration. Gemäß aktuellem Nutzerauftrag korrigiert:
Personenauswahl ohne Nebenfenster, sowohl ohne als auch mit explizitem Profil;
Termine, Optionen und strenge Ergebnisprüfung weiterhin geprüft. Kein Abschwächen
von Solverregeln. Alle Datenbanken ausschließlich synthetisch.

Zusätzlich wird die Fixierungsidentität in der Oberfläche nach Termin-/Personen-ID
ermittelt: ein abweichendes Override-Metadatum erzeugt beim Ändern/Entfernen oder
Umschalten keine zweite Fixierung. Drei weitere Regressionen dafür bestanden.
Zwischenlauf: 433 bestanden, 1 fehlgeschlagen in 217,69 s; die alte positive
Paketbericht-Testvorlage enthielt den neu verpflichtenden `manual_assignment`-
Nachweis noch nicht. Vorlage ergänzt, strenge Prüfung unverändert. Gezielter
Nachlauf Paketbericht/Metadaten: 9 bestanden in 12,72 s. Abschließender Gesamtlauf
mit allen Ergänzungen läuft anschließend; Ergebnisse werden ergänzt.

Abschließende Gesamtprüfung: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m
pytest -q --disable-warnings --maxfail=1`: **437 bestanden in 257,35 s**.
`git diff --check` fehlerfrei. Version 0.4.3. Native Windows-/macOS-Builds werden
mit diesem geprüften Programm-/Teststand und verschärfter Paketprobe erzeugt.

Native Lieferung 0.4.3: **Run 42924260302**, Programm-/Testcommit **1ef36fe**.
Windows x64, macOS Sequoia ARM64 und Intel vollständig erfolgreich. Je Plattform
Testsuite, Build und Selbsttest des gebauten Programms; ausdrücklich neu geprüft:
`manual_assignment=true` (Zuordnen/Fixieren/Ändern/Entfernen ohne Wochenprofil).
Der längere Intel-Testlauf endete erfolgreich ohne geänderte Anforderungen oder
Wiederholung. Rohdaten: `examples/v2/native-pruefung.json`; 0.4.2 unter
`native-0-4-2.json` archiviert. Aktuelle Links und Paketgrößen:
`V2_NATIVE_PRUEFUNG.md`. Keine Datenmigration, kein Merge nach main. Reine spätere
Nachweiscommits ändern diesen geprüften Programm-/Teststand nicht.

## Bestätigung mit Abweichungen 0.4.4

Neue Nutzerregel: Monatsbestätigung darf trotz Verfehlungen nach ausdrücklicher
Warnung erfolgen. UI prüft Regeln, offene Plätze, Stundenabweichungen und
ungeprüfte Regeln; Zustimmung separat von der bisherigen manuellen
Regelübersteuerung, standardmäßig Nein. Speicher prüft unabhängig erneut;
`allow_violations=True` ist erforderlich für harte Konflikte/offene Plätze und
abweichende bestätigte Randwochen. Bestätigungs-Snapshot friert Hinweise,
Regelmeldungen, offene Plätze und ausdrückliche Übersteuerung ein. Sichtbarer
Status nach Neustart. Bestehende Hashes/Reader bleiben kompatibel; unveränderliche
Historie, Revisionsprüfung, Transaktionen und Idempotenz bleiben erhalten.
Technisch widersprüchliche Kennungen und ungeklärte Rechengrundlagen bleiben
Fehler, keine erfundenen Werte. Keine echte Benutzerdatenbank verändert.

Gezielte Prüfung: neue Bestätigungs-, bestehende Historien- und Qt-Tests:
40 bestanden in 12,71 s. Zusätzliche Randwochen-Override-Regression ergänzt.
Gesamtprüfung und native Nachweise folgen nach Abschluss.

Abschließender Gesamtlauf `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest
-q --disable-warnings --maxfail=1`: **441 bestanden in 284,52 s**. Erweiterter
gezielter Bestätigungsnachlauf einschließlich tatsächlichem Schließen und
Wiederöffnen der Qt-Anwendung: **4 bestanden in 1,24 s**. `git diff --check`
fehlerfrei. Native Pakete werden nach diesem geprüften Programm-/Testcommit
gebaut; bisherige 0.4.3-Pakete enthalten die neue Bestätigung noch nicht.

Native Lieferung 0.4.4: **Run 42931888956**, Programm-/Testcommit **90a67d6**.
Windows x64, macOS Sequoia ARM64 und Intel vollständig erfolgreich: Testsuite,
Paketbuild und Programm-Selbsttests. Rohdaten: `examples/v2/native-pruefung.json`;
0.4.3 unter `native-0-4-3.json` archiviert. Aktuelle Links und Paketgrößen in
`V2_NATIVE_PRUEFUNG.md`. Keine echte Datenbank verändert, kein Merge nach main.
Nachfolgende reine Nachweiscommits ändern den geprüften Programm-/Testcode nicht.

## Laufender Folgeauftrag 0.5.0 – Urlaub und verständliche Bedienung (noch nicht freigegeben)

Arbeitsstand nach Unterbrechung: uncommittete Implementierung auf
`feat/v2-implementation`; letzte veröffentlichte stabile Pakete bleiben 0.4.4.
Keine neue Test-/Buildfreigabe behaupten. `git status` und gezielte aktuelle Tests
vor weiteren Schritten prüfen. Neue Module Urlaub, Urlaubskonten, Kalenderdialog,
Termindialog, M1-Stundenbuchung und KC15-Alternativen werden integriert.

Verbindliche Nutzerantworten: Jedes ausdrücklich markierte U-Datum zählt,
auch Wochenende/Feiertag; W/5 je Tag. Zwei Urlaubstage Monatsanspruch ansparen,
Anfangsbestand je Person erfassbar. Gleichzeitige Pausen erlaubt. R zählt volle
Normalarbeitszeit. KC15 ersetzt bei fehlender regulärer Besetzung KC10 UND KC16:
15–00 Uhr, eine Person, normale 30-Minuten-Pause. LB ab 03.12.2026 alle14Tage,
feste Personen nicht erfinden. Freies Wochenende gehört zum Sonntagsmonat.
Gesamte bezahlte Schicht im Startmonat buchen (M1); bestätigte alte M0-Monate
unverändert lassen. KC10 am Donnerstag31.12. ist KCT10 bis17:30.

Noch echte Restfragen: Teilmonatsansprüche/aktive Teilwochenenden, FK-Wiederholung,
R-Fenster bei bloßem Tabellenkürzel R, konkrete feste LB-Personen als normale Eingabe,
gewünschte Eurotarife und besondere W17-Wochenendwunsch-Ausnahme. Bereits bestätigte
Grundregeln nicht erneut abfragen. Hauptaufgabe jetzt Integration, Regressionen,
Dokumentationsbereinigung und erst dann Commit/Push/neue native Pakete.

### Integration und weitere Nutzerantworten

Die vorstehende Liste ist inzwischen weiter präzisiert: Urlaub bei Ein-/Austritt
im Monat wird **anteilig nach beschäftigten Kalendertagen** erworben, FK wird
**nur einzeln erfasst**, Freitags-W17 ist **vom Wochenend-Freiwunsch ausgenommen**.
Teilmonatsurlaub wird exakt als `2 × Beschäftigungstage / Monatskalendertage`
summiert; keine monatliche Abrundung des Tagesbestands. Die W17-Ausnahme betrifft
nicht einen normalen Einzel-Freiwunsch und nicht zusätzliche Samstagsdienste.
Offene normale Altentwürfe übernehmen diese bestätigten Regeln im Speicher;
bestätigte historische Stände und ihre Profile bleiben unverändert.

Erledigte Änderungssätze: Urlaubskalender und U-Import mit sichtbarer W/5-Gutschrift;
Korrektur alter fehlender Tagesmengen; angesparte Urlaubskonten mit explizitem
Start/Anfangsbestand und eingefrorener Bestätigungsstatistik; Kalender-/Namensdialoge
für Termine; LB-Monatsserie nach Auswahl zweier Namen; Personeneditor mit inklusiven
letzten Kalendertagen und korrekter exklusiver Domain-Grenze; kurze Statusübersicht
mit vollständigem Hinweisfenster; Planerhalt bei Urlaub, Namen, Stunden und
Personendetails; R als Normalarbeit; echte KC15-Alternativen im Solver/Import;
M1-Kontobuchung in Bewertung, Berichten und Exporten. Keine echte Benutzerdatenbank
verändert, keine produktive Tarif-/Rechtszuordnung abgeleitet.

Zwischenprüfung: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
--disable-warnings --maxfail=5`: **524 bestanden, 2 fehlgeschlagen in 301,69 s**.
Die beiden Fehler betrafen alte Duplikat-Urlaubsfixtures ohne Gutschrifttage;
neuer U-Import wählt nach Nutzerantwort alle markierten Tage. Duplikatfixtures
verwenden nun explizit vollständig erfassten Urlaub. Ein zusätzlicher Test schützt
den alten ungeklärten Datensatz gegen stille Änderung. Prüfung/Schutz unverändert.
Gezielter Nachlauf: 69 bestanden, 1 neue Fixture ungültig (Wochenendwunsch ohne
erforderlichen Budgetmonat); Fixture korrigiert, keine Regel abgeschwächt.
Vier neue Personendialog-Prüfungen bestanden in 1,51 s. Abschließende Nachläufe
einschließlich der zusätzlichen Nutzerantworten stehen noch aus.

Quell-Selbsttest `QT_QPA_PLATFORM=offscreen .venv/bin/python -m dienstplan
--self-test-v2 --self-test-report /tmp/dienstplan-0.5.0-smoke.json` bestanden,
einschließlich tatsächlichem Urlaubs-Korrekturdialog, Planerhalt, SQLite-Neustart,
Solver und Export. `leave_calendar=true` ist jetzt auch für native Pakete
verpflichtend; native 0.5.0-Nachweise folgen erst nach finaler Regression.

Abschließender Gesamtlauf mit den zusätzlichen Nutzerantworten:
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q --disable-warnings
--maxfail=3`: **545 bestanden in 300,76 s**. Danach minimaler Löschcallback-Fix
im neuen Personeneditor: automatisch geführte Datumszellen werden beim Entfernen
von Versionen korrekt verschoben; ein vorher fehlschlagender Regressionstest
schützt manuell datierte Folgezeilen. Personendialog-Nachlauf: **5 bestanden
in 1,78 s**. Zusätzliche Prüfung manueller Terminausnahmen: Kalenderregel darf
nach Warnung übergangen werden, Ablehnung lässt Daten/Plan/Revision unverändert.
Gemeinsamer abschließender Nachlauf `tests/test_v2_term_dialog.py
tests/test_v2_person_dialog.py tests/test_v2_overrides.py
tests/test_v2_application.py`: **50 bestanden in 14,75 s**. Keine Abschwächung
der automatischen Solverregeln. Quell-Selbsttest erneut erfolgreich als
`/tmp/dienstplan-0.5.0-final-smoke.json`; synthetische Qt-Sichtproben von Haupt-,
Urlaubs- und Personenansicht erstellt und geprüft. `git diff --check` fehlerfrei.

Nächster Schritt: diesen geprüften Programm-/Teststand committen und auf
`feat/v2-implementation` pushen, native Windows-/macOS-Matrix ausführen und erst
nach Erfolg die aktuellen Paketlinks und tatsächlich gemessenen Größen eintragen.
Kein Merge nach main, keine echte Datenbank oder produktive Tarifzuordnung geändert.

Erster nativer Lauf **43053041304** auf **330b762**: Windows meldete einen
veralteten UI-Test, der für einen Donnerstagsdienst zwingend einen Fehler statt
der inzwischen gewünschten Warnung mit Übersteuerung erwartete. Die neue
Terminausnahme war im letzten gezielten Nachlauf geprüft; dieser ältere UI-Test
war darin nicht enthalten. Erwartung nach bestätigter Nutzerregel korrigiert:
Warnung muss „Teamvariante“ enthalten; Ablehnung lässt Eingaben, Plan, gewählte
Termine und Revisionsnummer unverändert. Zusätzlich bleibt eine technisch
ungültige Datumseingabe ein Fehler ohne Planverlust. Keine Änderung am
Programmcode oder an automatischen Schutzregeln für diese Testkorrektur.
Restliche Jobs dieses überholten Laufs abgebrochen; keine Pakete daraus freigegeben.
Erneuter gemeinsamer UI-Nachlauf und neue native Gesamtmatrix folgen.

Gemeinsamer Nachlauf `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
tests/test_v2_ui.py tests/test_v2_term_dialog.py tests/test_v2_person_dialog.py
--disable-warnings --maxfail=2`: **46 bestanden in 15,84 s**. Die vollständige
native Matrix wird mit der geprüften Testkorrektur erneut gestartet.
