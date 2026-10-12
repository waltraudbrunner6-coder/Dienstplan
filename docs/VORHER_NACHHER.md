# Vorher-/Nachher-Prüfbericht – Version 0.2

Vergleich vom 12. Oktober 2026 unter Linux x64, Python 3.12.14, OR-Tools 9.15.6755.
Originalsolver aus Commit `e7e0fc5e319cc636ca95f0685b0728e5d535e1f8` und neue Optimierung wurden seriell mit identischen Eingaben und jeweils **30 Sekunden** Gesamtzeitlimit ausgeführt. Beide verwenden einen Suchworker und Seed 202611. Es wurde kein Checkout zurückgesetzt.

## Vergleichseingaben

November 2026: zwölf Personen mit je 25 Wochenstunden, Anfangs-/Wunschsaldo null; Schichten, Besetzung und Blockertage entsprechen dem Änderungsauftrag. Keine Ausnahmen und keine bestätigten Vormonate in beiden Läufen. Das Monatssoll wird je Person einmal auf 6.429 Minuten gerundet: insgesamt 1.285,80 Stunden.
Ausdrücklich gewählte Testgrenzen: **11 Stunden Ruhezeit, 12 Stunden pro Tag, 40 Stunden je ISO-Kalenderwoche, sechs tatsächliche Arbeitstage in Folge**. Die unbekannten Grenzwerte früherer externer Läufe werden damit nicht nachgebildet. Der vollständige Input und sein SHA-256 stehen in [vergleich.json](../examples/comparison/vergleich.json) und [eingabe.json](../examples/comparison/eingabe.json).

## Gemessene Ergebnisse

| Kennzahl | Vorher | Nachher |
| --- | ---: | ---: |
| Besetzte / benötigte Plätze | 188 / 188 | 188 / 188 |
| Offene Plätze | 0 | 0 |
| Bedarf | 1.238 h | 1.238 h |
| Übergangene eindeutige P2-Wünsche | 2 | 2 |
| Größte absolute Zielabweichung / Monatssoll | 38,40 % | 9,01 % |
| Summe quadratischer relativer Stundenabweichungen | 0.679905 | 0.028139 |
| Summe absoluter Zielabweichungen | 275,30 h | 47,80 h |
| Personen mit besonderem Dienst | 6 | 8 |
| Höchste persönliche Sonderdienstanzahl | 2 | 1 |

Beide Pläne wurden erneut mit sämtlichen aktivierten Grenzen validiert. Im neuen Plan bleiben die Personen mit fünf relevanten Wünschen ohne Verletzung; die zwei notwendigen Übergehungen verteilen sich auf zwei Personen mit sechs Wünschen. Die acht besonderen Plätze besetzen acht unterschiedliche Personen.

## Einzelwerte

Stunden sind Abweichungen vom individuellen Planungsziel. Schichtzahlen stehen in der Reihenfolge **Früh / Spät / Nacht / Sonder**. Historische Wunschübergehungen sind in diesem Vergleich für alle null.

| Person | Relevante P2 | Übergehungen vorher → nachher | Stunden vorher → nachher | Schichten vorher → nachher |
| --- | ---: | ---: | ---: | --- |
| Person 1 | 6 | 0 → 1 | -27,65 → -1,15 | 7/5/1/0 → 5/5/5/1 |
| Person 2 | 5 | 1 → 0 | -4,15 → -9,65 | 9/3/3/1 → 5/5/5/0 |
| Person 3 | 6 | 1 → 0 | -23,15 → -7,15 | 3/6/4/0 → 5/4/5/1 |
| Person 4 | 5 | 0 → 0 | -11,15 → -1,15 | 7/4/4/0 → 5/5/5/1 |
| Person 5 | 6 | 0 → 0 | -27,65 → -3,65 | 4/3/5/0 → 6/5/5/0 |
| Person 6 | 5 | 0 → 0 | -41,15 → -1,15 | 1/5/4/0 → 5/5/5/1 |
| Person 7 | 6 | 0 → 1 | -26,65 → -7,15 | 3/4/4/1 → 4/5/5/1 |
| Person 8 | 5 | 0 → 0 | 4,35 → -1,15 | 6/6/3/2 → 5/5/5/1 |
| Person 9 | 0 | 0 → 0 | 18,85 → -9,65 | 4/7/8/0 → 5/5/5/0 |
| Person 10 | 0 | 0 → 0 | 26,85 → -1,15 | 5/7/6/2 → 5/5/5/1 |
| Person 11 | 0 | 0 → 0 | 25,85 → -3,65 | 9/8/3/1 → 5/6/5/0 |
| Person 12 | 0 | 0 → 0 | 37,85 → -1,15 | 2/2/15/1 → 5/5/5/1 |

## Tatsächlicher Nachweisstatus

Original: Besetzung und Gesamtzahl der Wunschübergehungen nachweislich optimal; alte gewichtete Stunden-/Schichtsumme nicht bewiesen.
Neu: Besetzung, Wunschgesamtzahl, beide Wunschgruppen und deren größte/quadratische Belastung sind nachweislich optimal. Für größte normierte Stundenabweichung und abschließende quadratische Fairness besteht **kein Optimalitätsnachweis**. Ergebnisstatus: gültig ohne vollständigen Optimalitätsnachweis. Die vollständigen Stufennamen, Werte und Nachweise stehen im JSON; es wird kein globales Optimum behauptet.
Die Kennzahlen beschreiben diesen konkreten Zeitlimitlauf. Andere Suchstände können andere gültige Pläne liefern. Der Stundenbedarf liegt 47,80 Stunden unter den Zielen, sodass vollständige individuelle Zielerreichung unmöglich ist. Sperren, höhere Wunschziele und Arbeitszeitgrenzen bleiben verbindlich.

## Konkrete Gegenbeispiele als Regressionen

**A – Nachttransfer am 10.11.:** Vollständig besetzte Fixture mit allen vier aktivierten Grenzen. Allgemeine Einzelübertragung von Person 10 auf Person 6 findet den 7,5-Stunden-Dienst. Person 10: 9 → 8 Nächte, +7,43 → −0,07 h; Person 6: 3 → 4 Nächte, −10,15 → −2,65 h. Die Abstände von Person 6 vor/nach dem Dienst sind jeweils 16 Stunden. Die früheren Verträge waren unbekannt: explizit rekonstruierte 24,9833333333 Wochenstunden bei Person 10 ergeben 6.424 Sollminuten, Person 6 hat 25 Wochenstunden und 6.429 Minuten. Andere feste Einsätze und Verträge isolieren den Transfer; keine Sonderbehandlung im Planer.
**B – Früh-/Spättausch am 16.11.:** Person 2: 12 Früh / 2 Spät → 11 / 3; Person 4: 3 Früh / 7 Spät → 4 / 6. Beide Dienste dauern sechs Stunden, persönliche Stunden und Salden bleiben gleich. Beide Personen haben in dieser separaten Fixture 19,6 Wochenstunden und genau 84 Monatsstunden; weitere feste Dienste machen die Fixture vollständig. Allgemeine Zweiertausche finden die Verbesserung und erhalten alle Grenzen.
**Ausnahme:** Frühdienst 16.11. in der Novemberfixture deaktiviert: 186 statt 188 Plätze und 1.226 statt 1.238 Mitarbeiterstunden. Spät, Nacht und die wöchentliche besondere Schicht bleiben aktiv. Wiederaktivierung, Mitternachtsgrenzen, Speicherung, Altdaten und Wunschrelevanz sind automatisiert geprüft.

## Prüfstand und Pakete

Automatisierte Prüfungen umfassen echte CP-SAT-Freiwunschfälle, CP-/Nachbewertungs-Kongruenz, bestätigte Historie ohne Doppelzählung, Migration und Qt-Eingabe–Import–Planung–Speicherung–Neustart. Der aktualisierte Selbsttest prüft einen kürzeren Sonderdienst, Ausnahmetage und bestätigte Freiwunschhistorie mit zwölf Personen und 186 besetzten Plätzen.
Der native Linux-Build wird mit PyInstaller erzeugt und aus seinem entpackten Archiv ohne die Entwicklungsvenv funktional geprüft. Windows x64 und macOS Sequoia Intel/Apple Silicon sind als native CI-Builds vorbereitet; in dieser Linux-Umgebung wurden sie nicht gebaut oder ausgeführt. **146 automatisierte Tests bestanden** in 57,95 Sekunden. Die tatsächlichen Bytegrößen des aktualisierten Pakets werden im Buildbericht `dist/build-report.json` protokolliert.

Abschließender Build **0.2.0**: Linux x64, **279,54 MiB** entpackt (293.120.738 Bytes), **108,58 MiB** TAR.GZ (113.851.365 Bytes). Das entpackte Archiv bestand den Selbsttest mit 186 Plätzen, Ausnahmen, kürzerem Sonderdienst und bestätigter Wunschhistorie in einer minimalen Prozessumgebung ohne Entwicklungsvenv. Exakte Metadaten und SHA-256: [BUILD_PRUEFUNG.json](BUILD_PRUEFUNG.json). Die Qt-Prüfung erfolgte offscreen.
