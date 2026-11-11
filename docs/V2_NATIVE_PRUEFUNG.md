# Dienstplan 0.5.0 – Urlaubskonten, Kalenderbedienung und geklärte Dienstregeln

Stand 11.11.2026. Programm-/Teststand **1361571**. Windows x64, macOS Sequoia
Apple Silicon und Intel: vollständige Testsuite, Paketbau und Prüfung der
gebauten Anwendung erfolgreich.

[Prüflauf 43054833208](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43054833208). Rohdaten:
`examples/v2/native-pruefung.json`; der unveränderte 0.4.4-Nachweis ist unter
`examples/v2/native-0-4-4.json` archiviert. Nachfolgende reine Nachweiscommits
ändern den geprüften Programm-/Testcode nicht.

## Downloads

- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43054833208/artifacts/13872581097)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43054833208/artifacts/13870669310)
- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/43054833208/artifacts/13870389354)

Alte App schließen und neue Archive vollständig entpacken. Der GitHub-Download
enthält das eigentliche ZIP/TAR.GZ und `build-report.json`; auch dieses innere
Archiv entpacken. Windows: den vollständigen Dienstplan-Ordner behalten und die
EXE darin öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges
App-Bundle behalten. Im Fenster muss **Version 0.5.0 · Build 1361571** stehen.
Python und Terminal sind nicht erforderlich. Bestehende Monatsdatei weiterverwenden.

## Änderungen und geprüfte Bedienung

- Urlaubskalender mit erstem und letztem eingeschlossenen Tag; jedes markierte
  U-Datum zählt mit den dann gültigen Wochenstunden ÷ 5, auch am Wochenende/Feiertag.
  Zwei U-Tage bei 25 Wochenstunden ergeben 10 Stunden Gutschrift.
- Urlaubskonto mit persönlichem Anfangsbestand und Startmonat. Zwei Tage je
  Beschäftigungsmonat werden angespart; Teilmonate exakt mit
  `2 × Beschäftigungskalendertage / Monatskalendertage`. Keine Vorabrundung der
  Bruchteile; Tagesbestände in der Oberfläche auf zwei Nachkommastellen angezeigt.
- Fehlende alte Urlaubstage sind über „Urlaubsübersicht → Fehlende Urlaubstage
  auswählen“ korrigierbar. Speichern, Bearbeiten und Löschen erhält den übrigen
  Dienstplan. Bestätigte Vergangenheit bleibt unverändert.
- Personen und Vertragsversionen mit Kalenderfeldern und inklusiven letzten Tagen;
  Termine mit Kalender, Uhrzeiten und Namensauswahl; vollständige Hinweise separat
  lesbar. Abgelehnte Änderungen verändern keine Daten oder Zuteilungen.
- R zählt normale Arbeitszeit; KC15 ist eine echte besetzte Ersatzwahl statt
  KC10 und KC16. „LB-Termine ergänzen“ fragt zwei Personen und ergänzt nur die
  fehlende Serie ab 03.12.2026 im 14-Tage-Rhythmus. FK wird einzeln erfasst.
- Neue/offene normale Monate buchen die volle Schicht im Startmonat (M1), ordnen
  Wochenenden dem Sonntagsmonat zu und berücksichtigen Freitags-W17 beim
  Wochenendwunsch als Ausnahme. Alte bestätigte M0-Stände bleiben unverändert.
- Manuelle Änderungen, Import und Monatsbestätigung dürfen nach Warnung fachliche
  Regeln übergehen. Technisch ungültige Daten bleiben Fehler; automatische Planung
  hält die verbindlichen Regeln weiter ein.

Lokale Gesamtkontrolle: **549 Tests bestanden in 334,61 s**. Alle drei nativen
Jobs führten die vollständige Testsuite, Build und Programm-Selbsttest erfolgreich
aus. Der Paketnachweis verlangt insbesondere `leave_calendar=true` und
`manual_assignment=true`. Offline-Zeitzonenfallback wird mit leerem
`PYTHONTZPATH` geprüft. Rechenkette mit synthetischer Fixture, tatsächliche
Qt-Hauptoberfläche mit Standardmonat; keine Benutzerdatenbank verändert.

Der erste Lauf 43053041304 wird nicht als erfolgreicher Nachweis verwendet:
Ein älterer Test erwartete zwingende Ablehnung statt der ausdrücklich gewünschten
Terminausnahme nach Warnung. Der korrigierte Test prüft Warnung und unveränderte
Daten bei Ablehnung; technisch ungültige Daten bleiben gesperrt. Die erneute
vollständige Matrix auf 1361571 ist erfolgreich.

## Tatsächlich gemessene Paketgrößen

| Plattform | Natives Archiv | Entpacktes Programm |
| --- | ---: | ---: |
| macOS Sequoia / Apple Silicon | 64.339.067 Bytes / 61,36 MiB | 181.426.152 Bytes / 173,02 MiB |
| macOS Sequoia / Intel | 71.115.607 Bytes / 67,82 MiB | 187.937.099 Bytes / 179,23 MiB |
| Windows x64 | 87.506.542 Bytes / 83,45 MiB | 241.461.564 Bytes / 230,28 MiB |

Die GitHub-Artifact-Hülle kann wegen zusätzlicher Kompression eine andere
Downloadgröße haben. Plattform-/Pythonversionen, Bytewerte und Selbsttestdetails
stehen im Rohbericht. Die Pakete sind nicht signiert/notarisiert. Automatisierte
native Qt-Prüfung, keine vollständige manuelle Abnahme jeder Eingabekombination.

Offene betroffene Fachdetails bleiben in [Informationsprüfung](V2_INFO_AUDIT.md)
und [offenen Fragen](V2_OFFENE_FRAGEN.md) benannt, insbesondere Teilmonatsquoten
freier Wochenenden und der relative Rang freiwilliger T-/TS-Teilnahme. Eine
Bestätigung erklärt einen abweichenden Plan nicht für regelkonform. Dies ist kein
pauschaler Nachweis aller 125 Produktabnahmen oder betrieblicher Rechts-/Tarifprofile.
