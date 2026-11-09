# V2 – Implementierungsstand und Wiederaufnahme

Basis: Etappe A `0a0bc48`, Arbeitsbranch `feat/v2-implementation`.
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
Ein vollständiger aktiver Abwesenheitseditor, Bestätigungsaufhebung und die
produktive Profilführung bleiben offen; CSV-Korrektur ist funktional angebunden.

## Offene Fachentscheidungen und Grenzen

F01–F14 aus `V2_OFFENE_FRAGEN.md` bleiben offen, außer den dort ausdrücklich bereits
erledigten Klärungen. Donnerstagswünsche bleiben zur Korrektur vorgemerkt, ohne
aktive/teilweise Importübernahme. Testprofile sind ausdrücklich keine betrieblichen
Freigaben. Produktive Wunschhistorie und vollständige produktive Oberfläche sind
noch nicht freigegeben. Testprofiloptimierung ersetzt keine betriebliche Rechts-/Tarifprüfung.
Monatsskalierung des Kalenders mit Ausschlussschnitten ist weiterhin begrenzt.

## Nächster zusammenhängender Schritt

Nutzer hat am 10.11.2026 selbstständige Fortsetzung bestätigt.
Nächster Schritt F2: paketierter V2-Selbsttest mit gebündeltem tzdata und echte
native Plattformprüfungen über den vorhandenen Workflow;
keine produktive Umschaltung oder echte Datenmigration ohne gesonderten Auftrag.
