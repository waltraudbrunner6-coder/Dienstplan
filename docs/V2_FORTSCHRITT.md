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

## Offene Fachentscheidungen und Grenzen

F01–F14 aus `V2_OFFENE_FRAGEN.md` bleiben offen, außer den dort ausdrücklich bereits
erledigten Klärungen. Donnerstagswünsche bleiben zur Korrektur vorgemerkt, ohne
aktive/teilweise Importübernahme. Testprofile sind ausdrücklich keine betrieblichen
Freigaben. Pausenvertretung, vollständige Wunschhistorie, Migration, V2-Solver
und neue Oberfläche sind noch nicht implementiert. T-/TS-Erfüllung liegt als
reine Domainfunktion vor, noch nicht als vollständiges Optimierungsziel.

## Nächster zusammenhängender Schritt

B3: versionierte Profile, schreibgeschützter Legacy-Reader, transaktionale
Kopienmigration mit Abbruch-/Rollbacktests und persistente Korrekturvormerkung.
