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

## Offene Fachentscheidungen und Grenzen

F01–F14 aus `V2_OFFENE_FRAGEN.md` bleiben offen, außer den dort ausdrücklich bereits
erledigten Klärungen. Donnerstagswünsche bleiben zur Korrektur vorgemerkt, ohne
aktive/teilweise Importübernahme. Testprofile sind ausdrücklich keine betrieblichen
Freigaben. Pausenvertretung, T-/TS-Erfüllung, Wünsche/Historienspeicher, Migration,
V2-Solver und neue Oberfläche sind nach B1 noch nicht implementiert.

## Nächster zusammenhängender Schritt

B2: Katalog/Veranstaltungen/Bedarfe, zeitgültige Rechte und T-/TS-Erfüllungsbezüge;
danach echte CSV-Korrekturstapel. Fehlende Quoten-/Reserve-/LB-/FK-Profile werden
als fehlend ausgewiesen, nicht durch versteckte Produktstandards ersetzt.
