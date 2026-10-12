# Dienstplan – Spezifikation der ersten Version

Eine vollständig lokale Desktop-Anwendung für zunächst zwölf Personen. Python 3.12,
Qt Widgets aus PySide6-Essentials, OR-Tools CP-SAT und SQLite. Keine Cloud, Anmeldung
oder Internetverbindung im Betrieb. Deutsche Oberfläche, Meldungen und Anleitung.
Zielplattformen: Windows 10/11 x64 und macOS Sequoia 15 auf Intel/Apple Silicon.
Native Pakete werden mit PyInstaller auf der jeweiligen Zielplattform erstellt.

## Daten und Regeln

- Ein Monatsdatensatz enthält einen unveränderlich speicherbaren Stand von Team,
  Wochenstunden, Salden, vier Schichttypen, Regeloptionen und Zuteilungen.
- Drei tägliche Schichten, eine längere wöchentliche Schicht. Besetzung standardmäßig
  zwei unterschiedliche Personen. Gleiche Start-/Endzeit bedeutet 24 Stunden;
  Ende vor Start liegt am Folgetag. Unbezahlte Pause reduziert die Stunden.
- Monatssoll = Wochenstunden × Kalendertage / 7, einmal kaufmännisch auf Minuten
  gerundet. Ziel = Soll + gewünschter Endsaldo − Anfangssaldo. Negative Ziele sind
  ungültig. Stunden werden ausschließlich als Planprognose dargestellt.
- Eine Schicht zählt vollständig zum Startmonat. Konflikte verwenden tatsächliche
  halboffene Zeitintervalle [Start, Ende); angrenzende Intervalle überlappen nicht.
- Priorität 1 ist verbindlich, höchstens vier eindeutige Einträge pro Person und
  betroffenem Monat. Priorität 2 darf mit sichtbarem Hinweis übergangen werden.
- CSV-Vorschau prüft alle Zeilen vor einer atomaren Speicherung. UTF-8/BOM,
  Semikolon/Komma, datum/von/bis/prioritaet/kommentar. Identische Zeiträume mit
  gleicher Person und Priorität zählen einmal; Kommentare sind Zusatzinformation.
- Optionale Ruhezeit, Tages-/Wochenstunden und aufeinanderfolgende Arbeitstage.
  Keine stillschweigenden gesetzlichen Werte. Tages-/Wochenstunden teilen bezahlte
  Minuten an Mitternacht auf; die Pause wird für diese Prüfung am Schichtende
  abgezogen. Wochen sind ISO-Kalenderwochen (Montag bis Sonntag). Arbeitstage sind
  alle Kalendertage mit tatsächlicher Schichtanwesenheit.
- Monatsübergreifende Randbedingungen berücksichtigen gespeicherte Zuteilungen
  benachbarter Monate. Ein Monat wird jeweils für sich optimiert.

## Optimierung und Historie

Strenge lexikografische Ziele: (1) offene Plätze minimieren, (2) verletzte
Priorität-2-Einträge minimieren, (3) Stundenabweichung und gewichtete Fairness.
Nach jeder Stufe wird ihr gefundenes Ziel festgehalten, bevor die nächste startet.
Ohne Optimalitätsnachweis einer höheren Stufe wird das Gesamtergebnis niemals als
nachweislich optimal bezeichnet. Ein Zeitlimit liefert ggf. einen gültigen Entwurf,
keine Behauptung der Unlösbarkeit.

Fairer Anteil proportional zu vertraglichen Wochenstunden. Die dritte Stufe
bewertet absolute Minutenabweichung zum individuellen Ziel und Abweichungen von
Anzahl und Stunden je Schichttyp. Die besondere Schicht erhält zusätzlich höheres
Gewicht und eine Bilanz aus ausdrücklich bestätigten früheren Monaten. Historische
Sollanteile verwenden die damaligen Wochenstunden; ein Monat zählt nur einmal.
Ein fester Solver-Seed und ein Worker machen Gleichstände reproduzierbar bei
gleicher Version und identischem Datenstand; Namen sind kein Bevorzugungskriterium.
Die exakten Gewichte stehen in der README und im Planungsmodul.

## Bedienung und Sicherheit der Daten

Monat wählen → Team erfassen → Schichten konfigurieren → Sperren importieren/
bearbeiten → planen → prüfen/manuell ändern/fixieren → speichern/bestätigen/exportieren.
Ein Hintergrundthread führt den Solver mit Zeitlimit und Abbruch aus. Ein bestehender
Plan wird erst nach ausdrücklicher Übernahme des neuen Entwurfs ersetzt. Manuelle
Änderungen werden durch dieselbe zentrale Regelprüfung validiert. Bestätigte Monate
sind gegen unbeabsichtigte Änderungen geschützt; zum Bearbeiten Bestätigung aufheben.
SQLite liegt im persönlichen Anwendungsdatenverzeichnis. CSV-Exporte sind UTF-8
mit BOM und Semikolon. Kein automatischer Versand oder Telemetrie.

## Überprüfbare Etappen

1. Rechenmodell, SQLite und CSV: Rundung, Grenzfälle, atomare Speicherung testen.
2. CP-SAT: Besetzung, Sperren, Fairness, Historie, Regeln und Fixierungen testen.
3. Vollständige Qt-Oberfläche: Eingabe bis Neustart, Importvorschau und Export prüfen.
4. Zwölf-Personen-Demo und Mehrmonatsbeispiel ausführen; native Linux-Paketierung
   messen. Windows/macOS-Anleitungen und CI vorbereiten, ungetestete Builds benennen.
