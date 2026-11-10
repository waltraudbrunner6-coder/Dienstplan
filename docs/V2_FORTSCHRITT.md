# V2 – Implementierungsstand und Wiederaufnahme

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
