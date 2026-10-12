# Dienstplan – Spezifikation – Version 0.2

Eine vollständig lokale Desktop-Anwendung für zunächst zwölf Personen. Python 3.12,
Qt Widgets aus PySide6-Essentials, OR-Tools CP-SAT und SQLite. Keine Cloud, Anmeldung
oder Internetverbindung im Betrieb. Deutsche Oberfläche, Meldungen und Anleitung.
Zielplattformen: Windows 10/11 x64 und macOS Sequoia 15 auf Intel/Apple Silicon.
Native Pakete werden mit PyInstaller auf der jeweiligen Zielplattform erstellt.

## Daten und Regeln

- Ein Monatsdatensatz enthält einen unveränderlich speicherbaren Stand von Team,
  Wochenstunden, Salden, vier Schichttypen, Regeloptionen, Ausnahmetage und Zuteilungen.
- Drei tägliche Schichten, eine wöchentliche besondere Schicht beliebiger Dauer. Besetzung standardmäßig
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

## Ausnahmetage

Monatsbezogene Ausnahmen sind eindeutige Termin-IDs `YYYY-MM-DD/Schichtkennung`.
Nur tägliche Schichten des gewählten Monats dürfen entfallen; Wochen-Sonderdienste
bleiben bestehen. Startdatum entscheidet auch bei Nachtschichten. Die zentrale
Schichterzeugung filtert Ausnahmen vor Bedarf, Konflikt-/Wunschprüfung, Stunden,
Fairness und Optimierung. Inaktive Termine sind im Export ausdrücklich ENTFÄLLT
und verursachen keine Plätze/Stunden. Entfernen einer Ausnahme erzeugt den Termin
wieder. Vor Entfernung zugeteilter Dienste nennt die UI alle betroffenen Einsätze
und Fixierungen und verlangt die Übernahme. Neue Monate übernehmen Vorlagen ohne
Datums-Ausnahmen. Bestätigte Monate sind weiterhin schreibgeschützt.

## Optimierung und Historie

Alle verbindlichen Bedingungen bleiben hart. Streng lexikografisch folgen:

1. Anzahl offener Plätze.
2. Gesamtzahl verletzter eindeutiger relevanter P2-Wünsche.
3. Verletzungszahlen für Gruppen nach Wunschanzahl aufsteigend (1, 2, …).
4. Pro Gruppe gleiche Anzahl: größte kumulierte Belastung, dann Quadratsumme.
5. Größte normierte absolute Abweichung zum persönlichen Planungsziel.
6. Gewichtete normierte Stundenquadrate und Schicht-/Sonderhistorienquadrate.

Ein relevanter Wunsch ist ein eindeutiger P2-Zeitraum mit Überschneidung einer
aktiven Monats-Schicht. P1, identische Duplikate und inaktive Zeiträume erhöhen
die Wunschanzahl nicht. Derselbe Wunsch zählt trotz mehrerer Dienste einmal.
Wunschbelastung ist die Vereinigung historisch und aktuell verletzter Schlüssel;
monatsübergreifende Wünsche werden kumuliert einmal gezählt. Gruppenschutz gilt
vor Stunden-/Schichtzielen. Bewiesene oder beste gefundene Werte einer höheren
Stufe können durch beliebig viele niedrigere Verbesserungen nicht verschlechtert
werden. Bei fehlenden Nachweisen werden nachgeordnete Stufen unter diesem
gefundenen Präfix optimiert, ohne ein globales Optimum zu behaupten.

Normierung: `r = ceil(1000 × |P − Ziel| / max(Monatssoll, 60 Minuten))`. Der
Mindestnenner 60 verhindert Division durch null und übermäßige Skalierung bei
sehr kleinen Verträgen. Zuerst minimieren wir max(r), dann in der gemeinsamen
letzten Stufe 10000 × Summe(r²). Die Schichtterme verwenden Vertragsanteile in
Tausendsteln (größte Reste, Summe 1000) und bewerten Quadrate der Anzahlbilanz
sowie der auf Stundenäquivalente skalierten Minutenbilanz. Faktor tägliche Dienste
1, besondere Dienste 4, zusätzliche kumulierte Sonderhistorie 8. Exakte Formel
steht in README und optimization.py; CP-Modell und Nachbewertung verwenden
identische ganzzahlige Maße. Bei null Wochenstunden aller Personen gelten gleiche
Anteile. Bei unvollständiger Besetzung beziehen sich faire Sollanteile auf die
tatsächlich besetzten aktiven Schichten.

Ein vorhandener gültiger Plan bleibt Startpunkt und Rückfall. CP-SAT nutzt feste
Seeds und einen Worker. Rechenzeit wird für letzte Stufen und eine allgemeine
Nachsuche reserviert. Einzelübertragungen und Zweiertausche müssen dieselbe harte
Regelprüfung bestehen, Fixierungen erhalten und die lexikografische Bewertung
verbessern. Der beste gefundene Plan wird zurückgegeben und nachbewertet;
betroffene Optimalitätsnachweise werden bei nachträglicher Änderung zurückgenommen.
Abbruch und Zeitlimit bedeuten keinen Beweis der Unlösbarkeit. Auch numerische
Grenzen einer späteren Stufe verwerfen keinen bereits gültigen Entwurf.

SQLite-Schema 2 ergänzt Ausnahmen und einen bestätigten Wunsch-Snapshot. Alte
JSON-Stände ohne Felder laden mit leeren Ausnahmen und fehlendem Wunsch-Snapshot;
bei der Migration werden weder alte Nutzdaten noch Wochenstunden umgeschrieben.
Wunschinformationen werden erst bei einer ausdrücklichen neuen Bestätigung
festgehalten. Wiederbestätigung desselben bestätigten Standes verändert sie nicht.
Nur bestätigte Vormonate zählen zur Historie. Fehlende alte Wunschstatistik wird
in UI/Export gemeldet und nicht rückwirkend geraten. Spätere globale Blockeränderungen
ändern eingefrorene Statistik und Markierungen nicht. Historische Sonderanteile
verwenden unverändert die damaligen Wochenstunden.

## Bedienung und Sicherheit der Daten

Monat wählen → Team erfassen → Schichten/Ausnahmetage konfigurieren → Sperren importieren/
bearbeiten → planen → prüfen/manuell ändern/fixieren → speichern/bestätigen/exportieren.
Ein Hintergrundthread führt den Solver mit Zeitlimit und Abbruch aus. Ein bestehender
Plan wird erst nach ausdrücklicher Übernahme des neuen Entwurfs ersetzt. Manuelle
Änderungen werden durch dieselbe zentrale Regelprüfung validiert. Bestätigte Monate
sind gegen unbeabsichtigte Änderungen geschützt; zum Bearbeiten Bestätigung aufheben.
SQLite liegt im persönlichen Anwendungsdatenverzeichnis. CSV-Exporte sind UTF-8
mit BOM und Semikolon. Kein automatischer Versand oder Telemetrie.

## Prüfung der Änderung

1. Regressionsprüfung Wunschreihenfolge, historische Schlüssel und Gruppenquadrate.
2. Stunden-/Typbewertung, Null-Sollstunden, allgemeine Transfers und Zweiertausche.
3. Ausnahmen, kurze/gleiche/lange Sonderdienste, schonende Datenmigration und Qt-Kette.
4. Novemberfixture und alter/neuer Solver mit gleichem Input und 30 Sekunden;
   Vorher-/Nachher-Bericht, aktualisiertes natives Linux-Paket samt Selbsttest.
   Windows/macOS-CI vorbereitet; native Durchführung nur mit tatsächlichem Beleg.
