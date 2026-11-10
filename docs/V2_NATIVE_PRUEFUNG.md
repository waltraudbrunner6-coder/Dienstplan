> Folgeversion 0.4.1 ergänzt ausdrückliche Regelübersteuerung. Die folgenden
> Downloadlinks dokumentieren noch 0.4.0; native Nachweise für 0.4.1 werden nach
> erfolgreichem Build ergänzt.

# Dienstplan 0.4.0 – Tabellenimport und Monatsübersicht

Stand 10.11.2026. Aktuelle Pakete des geprüften Programm-/Testcommits **4e74b10**.
Der komplette lokale Gesamtlauf bestand **402 Tests in 136,65 s**. Alle drei
nativen Ziele führten Testsuite, Build und verschärfte Paketprobe erfolgreich aus:
[Run 42899281763](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42899281763). Nachfolgende reine Dokumentationscommits ändern
diesen geprüften Programm-/Testcode nicht.

## Aktuelle Downloads

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42899281763/artifacts/13802381766)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42899281763/artifacts/13801848228)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42899281763/artifacts/13801478552)

Alte App schließen, GitHub-Download und darin enthaltenes ZIP/TAR.GZ vollständig
entpacken. Windows: den vollständigen Dienstplan-Ordner behalten und darin die EXE
öffnen. Mac ARM64 ist für Apple Silicon, x64 für Intel; das gesamte App-Bundle
behalten. Im Fenster müssen **Version 0.4.0 · Build 4e74b10** stehen. Python und
Terminal werden nicht benötigt. Bestehende V2-Dateien sind weiterhin lesbar;
Originale und frühere Altdatenbanken werden nicht automatisch verändert.

## Neue Funktionen und Auswahlgrenzen

- XLSX-/CSV-Import von Terminen, einzelnen/vollständigen Zuteilungen und gemischten
  Wünschen/Urlaub mit zentraler ID-Zuordnung und bearbeitbarer Gesamtvorschau.
- Atomare Übernahme, Duplikaterkennung, Rollback bei Fehlern, keine fehlerhafte
  Teilaktivierung. Formeln werden nicht ausgeführt; alte Datumsköpfe nur aus
  gespeicherten Cachewerten gelesen, ohne externe Verknüpfungen zu öffnen.
- Datum/Wochentag/Beginn/Ende sowie Monatsmatrix mit festen Personenlabels;
  XLSX-Tabellenexport mit Stunden, offenen Plätzen und reimportierbaren Zeilen.
- Manuell nur Person wählen: Pause möglichst vor 22 Uhr, sonst mittig unter
  allen harten Regeln. Konkrete Pausen/Fixierungen bleiben im Reimport erhalten.
- Zwei WL und ein BK je Woche, nie am selben lokalen Startdatum. Das Wochenprofil
  wird vor der ersten normalen Berechnung/manuellen Zuteilung ausdrücklich
  gewählt, Folgemonate übernehmen es. Termine und Personen optimiert der Solver
  gemeinsam. Die globale Randwochenentscheidung wird nicht still geraten.
- Bekannte Nachbarpläne liefern Dienste/Ruhezeiten auch ohne neues Wochenprofil.
  Keine zweite unabhängige gemeinsame Randquote, keine Doppelzählung von Stunden.
- Vorläufige Datumswahl zeigt echte benötigte Plätze statt aller Kandidatentage;
  Horizont- und Kalendermonatsbedarf werden getrennt ausgewiesen. Noch freie
  Pausen an Monatsgrenzen ergeben eine Bandbreite statt falscher Genauigkeit.

Die privaten Originaltabellen und vorbereiteten persönlichen Importdateien sind
**nicht im Repository oder in diesen Programmpaketen enthalten**. Sie werden im
Chat separat bereitgestellt. Ungeklärte KC15-/R-/U-Angaben, Donnerstagswünsche und
KC10 am Donnerstag bleiben bis zur ausdrücklichen Klärung Korrekturfälle.
Einlesen ist kein Nachweis, dass ein alter Plan den aktuellen Regeln entspricht.
Der Import prüft auch Rechte, Besetzung, Ruhe, Urlaub und vorhandene Fixierungen.

## Tatsächlich gemessene Paketgrößen

Rohdaten, Betriebssysteme und Paketnachweise:
[native-pruefung.json](../examples/v2/native-pruefung.json).

| System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB | Paketprobe |
| --- | --- | ---: | ---: | ---: | --- |
| Windows 10.0.26100 | AMD64 | 241317035 | 230.14 | 83.35 | bestanden |
| macOS Sequoia 15.8.2 | arm64 | 181281151 | 172.88 | 61.26 | bestanden |
| macOS Sequoia 15.7.9 | x86_64 | 187792098 | 179.09 | 67.73 | bestanden |

Linux x86_64 zusätzlich gebaut und geprüft: **294587932 Bytes / 280.94 MiB**,
Archiv **114839087 Bytes / 109.52 MiB**.
Die Paketprobe bei leerem System-Zeitzonenpfad ist erfolgreich; Buildkennung
stimmt mit dem sauberen Programmstand überein. Dies ersetzt keinen nativen Nachweis.

Die neue Paketprobe verlangt zusätzlich Excel-Export→Import→SQLite-Roundtrip,
automatische Pausen und Wochenkonfiguration, außerdem weiterhin sichtbare
Vorschau, Standardkatalog, Stunden, Neustart, Wiener DST und CP-SAT/Prüfer.
Sie verwendet ausschließlich synthetische Daten, keine hochgeladenen Dienstpläne.
Der unveränderte Legacy-Fairnessfall läuft nun ausdrücklich mit 30 s statt 8 s Suchbudget, nachdem Intel zweimal noch unbalancierte gültige Zwischenstände lieferte; alle Assertions und separate Kurzzeit-/Timeoutprüfungen bleiben erhalten. Dies ist kein Nachweis derselben Fairness innerhalb von acht Sekunden. Details im Fortschritt. Native Tests sind automatisierte Offscreen-Prüfungen. Vollständige manuelle
Endgeräteabnahme, Signierung und Notarisierung bleiben offen; Pakete unsigniert.
Keine KV-/BV-, Reserve-, Gehalts- oder Abrechnungsfreigabe aus diesen Tests ableiten.

Frühere Belege: [0.3.1](../examples/v2/native-0-3-1.json),
[0.3.0](../examples/v2/native-0-3-0.json),
[Startauswahl](../examples/v2/native-startauswahl.json).
[Tabellenimport](TABELLENIMPORT.md), [Fortschritt](V2_FORTSCHRITT.md),
[offene Entscheidungen](V2_OFFENE_FRAGEN.md).
