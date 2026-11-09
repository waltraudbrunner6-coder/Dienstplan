# V2-Prüfbereich – technischer Stand

Die normale Anwendung arbeitet weiter mit ihren bisherigen Daten und Regeln.
Über **V2-Prüfbereich (Testprofile)** öffnet sich ein getrenntes Fenster innerhalb
derselben Anwendung. Dieser Bereich dient der fachlichen Prüfung. Er schaltet
keine produktive V2-Planung frei und öffnet die normale Benutzerdatenbank nicht.

1. Der Startdatensatz enthält zwölf fiktive Personen und vier WL-Testtermine.
   Das ist ausdrücklich kein vollständiger Betriebsmonat. „Neue Testdatei“ legt
   eine getrennte SQLite-Datei an; der anfängliche temporäre Stand ist flüchtig.
2. Namen, Wochenstunden und Minutenkonten bearbeiten und speichern. Für neue
   Konten gilt Wunschende 0. **Beschäftigung, Verträge und Rechte bearbeiten**
   ermöglicht mehrere datierte Fassungen. Alle Enddaten sind ausgeschlossen:
   Beschäftigung einschließlich 31.12. bedeutet Ende 01.01. Die Personen-ID bleibt
   stabil. Wochenstunden erteilen keine Berechtigungen oder Führerscheine.
3. Termine mit echten Katalogkürzeln ergänzen; VN/INT/N17/LB/FK brauchen feste IDs.
   FK braucht konkrete ISO-Zeitpunkte; mehrdeutige Herbstzeiten mit richtigem
   Offset angeben. W16 braucht einen Ersatzgrund. R erhält ohne geklärtes Profil
   keine Arbeitskandidaten. Die gesamten Kataloghäufigkeiten sind in diesem
   kleinen Prüfdatensatz nicht als Betriebsmonat freigegeben.
4. CSV-Format 2 aus den Fachregeln importieren. Ein fehlerhafter Stapel bleibt
   vollständig sichtbar/bearbeitbar. Änderungen in den Spalten vornehmen und
   den gesamten Stapel erneut prüfen. Erst die vollständige erfolgreiche Übernahme
   aktiviert Einträge. Die daneben angezeigten Wunschbudgets sind ausdrückliche
   Testeingaben. Bestehende bestätigte Vergangenheit bleibt unverändert.
5. **Testplan berechnen** startet die Optimierung im Hintergrund. **Abbrechen**
   erhält den besten gültigen Zwischenstand. Änderungen während des Laufs machen
   dessen Ergebnis veraltet. **Ergebnis übernehmen** übernimmt ausdrücklich den
   nachgeprüften Vorschlag. Offene Plätze und fehlende Grundlagen bleiben sichtbar.
6. In der Plantabelle eine Zeile wählen und Zuteilung/Pause ändern, entfernen
   oder einzeln fixieren. Jede Änderung wird unabhängig geprüft. Fixierungen gelten
   bei erneuter Suche weiter; „Alle manuellen Fixierungen lösen“ ist ausdrücklich.
   Eingabeänderungen können einen neuen Entwurf verlangen; gespeicherte Revisionen
   werden nicht überschrieben.
7. **Exportpaket** erstellt ein neues ZIP mit Dienstplan, Stunden, Verteilung,
   Wünschen, Zeitmengen, vollständigem Arbeitsstand und Prüfmanifest. Alle Tabellen
   tragen dieselbe Revisions-ID; Hashes belegen die zusammengehörigen Dateien.
   Bei Schreibfehlern wird kein halbes Paket veröffentlicht. Bestehende Ziele
   werden nicht überschrieben. Eurobeträge bleiben ohne Tarif ungeklärt.
8. **Testmonat bestätigen** friert nur synthetische Testfakten ein, nur bei gültiger
   Vollbesetzung. Wiederholen zählt nicht doppelt. Ein bestätigter Testmonat ist
   geschützt. Aufhebung/Ablösung ist noch nicht bedienbar. **Testmonat wählen**
   lädt einen vorhandenen Arbeitsstand oder erzeugt einen weiteren gekennzeichneten
   Testdatensatz mit bestätigter Historie und übernommenen Prognosesalden.

## Rechen- und Nachweisgrenzen

S0 und M0 sind explizite technische Profile. S0 summiert zeitgültige W/7-Anteile
über Beschäftigungstage und rundet einmal monatlich auf Minuten. M0 ordnet reale
Arbeitssegmente ihrem lokalen Kalendermonat zu. Urlaub verwendet ausschließlich
ausdrücklich anrechenbare Tage mit gültigem W/5. Ziel: `S+E−B−G`, Prognoseende:
`B+P+G−S`. Ein negatives Ziel erzeugt keine negative Arbeit. Es wird als Überdeckung
ausgewiesen. Arbeitszeit bleibt Planprognose, keine Ist-Zeiterfassung.

E0 ist eine ausgewählte Testhierarchie; Formeln und genaue Prüfstände stehen in
[V2_FORTSCHRITT.md](V2_FORTSCHRITT.md). Höhere beste Ziele bleiben fest. Ein späteres
Optimum unter unbewiesenem Präfix ist bedingt, kein Gesamtoptimum. Bei manuellen
Änderungen werden Solverbeweise verworfen. Zielrundung erfolgt mit Skala 1000;
die zuerst untersuchte Skala 100 war zu grob und wurde vor Auslieferung korrigiert.

Das Fenster bietet noch keine vollständige produktive Monatskonfiguration aller
Wochen-/Reserve-/Tarifprofile, keine Aufhebung bestätigter Teststände und keinen
vollständigen aktiven Abwesenheitseditor. Einzelne neue/zu korrigierende Einträge
können über denselben CSV-Stapel erfasst werden. Bekannte Randtage sind Teil des
gespeicherten Testprofils; fehlende Randdaten werden nicht als Freizeit angenommen.
Die offenen F01–F14 bleiben verbindlich sichtbar. Linux-Qt-Tests sind kein nativer
Windows-/macOS-Sequoia-Nachweis.

## Reproduzieren

```sh
python scripts/v2_benchmark.py --seconds 5 20 60 --output NEUER_BERICHT.json
python scripts/v2_multimonth_demo.py --output NEUER_DEMOORDNER --seconds 5
```

Die Mehrmonatsdemo umfasst November/Dezember 2026 und Jänner 2027. Sie prüft
Testbestätigung, Salden und eingefrorene Verteilung. Vollständige R-/Randwochen- und
Urlaubs-/Tarifintegration von X04 bleibt gesondert offen; vier Termine beweisen
keine betriebliche Monatsmachbarkeit. Die SQLite-Datei und ZIPs bleiben lokal.
