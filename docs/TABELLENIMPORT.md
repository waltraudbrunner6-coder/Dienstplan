# Termine, Dienstpläne und Wünsche importieren – Version 0.4.0

**Termine / Dienstplan / Wünsche importieren** liest XLSX oder das unten beschriebene
CSV-Format. Bei ursprünglichen Person×Datum-Tabellen ausdrücklich Dienstplan oder
Wünsche auswählen. X bedeutet im alten Dienstplan „kein Dienst“; in einer
Wunschtabelle werden ausschließlich gelbe X als Freiwünsche interpretiert. Grüne
Markierungen werden ignoriert. Dienstkürzel ergeben fixierte Zuteilungen; NH wird
wie beauftragt ignoriert. U bleibt als u_zuordnung_offen erhalten, bis seine Bedeutung ausdrücklich bestätigt
ist. Bei bestätigtem Urlaub die Art auf urlaub setzen; Gutschrifttage separat angeben. Die Originaldatei wird niemals verändert.

## Zuordnung und Korrektur

Die vorbereiteten XLSX-Dateien enthalten **Personen**, **Import** und **Hinweise**.
Im Blatt Personen die tatsächliche stabile App-ID einmal pro Quellzeile eintragen.
Gleiche Zeilennummern in zwei Quelldateien werden nicht als bewiesene identische
Personen behandelt. Zuordnung ist auch in der App-Vorschau möglich. Die zentrale
Zuordnung hat Vorrang vor der person_id einer referenzierten Importzeile.

Die Tabelle bleibt bearbeitbar vorgemerkt. **Vorschau prüfen und vormerken** speichert
auch fehlerhafte Eingaben zur späteren Korrektur. **Vorgemerkten Tabellenimport
fortsetzen** öffnet sie nach Neustart wieder. Erst **Gesamten gültigen Import
übernehmen** aktiviert alle Inhalte gemeinsam. Es gibt keine Teilübernahme eines
fehlerhaften Stapels. Datenbankfehler rollen den gesamten Vorgang zurück.

Der bisherige Plan wird standardmäßig ergänzt. Die ausdrücklich auswählbare Option
**Vorhandenen unfixierten Entwurf … ersetzen** verwirft dessen unfixierte Zuteilungen;
Fixierungen bleiben erhalten. Bestätigte Monate werden nicht überschrieben.

Unbekannte IDs/Kürzel, widersprüchliche Zeiten, Besetzungsüberschreitungen, fehlende
Berechtigung/Führerschein, Urlaub, Ruhezeiten und weitere harte Regeln werden
angezeigt. Fehlertexte nennen Quellzelle beziehungsweise Termin/Person. Ein alter
Plan ist nicht automatisch ein gültiger neuer Plan. Keine erfundene KC15-Definition,
keine automatische KC10→KCT10-Verlängerung an Donnerstagen und keine angenommene
volle Arbeitsbewertung von R. R verlangt konkrete Variante und bestätigte Bewertung;
als reiner Termin ohne Zuteilung kann R_early/R_late erhalten bleiben.

Bisher unzulässige Donnerstagswünsche bleiben bis zur ausdrücklichen fachlichen
Änderung zur Korrektur vorgemerkt. Das angezeigte Wunschbudget vor Übernahme
gegebenenfalls ausdrücklich anpassen. Urlaub ohne Gutschrifttage bleibt verbindlich,
Stundenprognose/Stundenoptimierung bleiben für diesen Teil ungeklärt.

## Zeilenformat

Pflichtspalten (auch leere Werte benötigen eine Spalte):

```csv
quelle;person_ref;person_id;datum;art;dienst;fixiert;beginn;ende;gutschrifttage;kommentar
Beispiel!A4;Zeile 4;P01;2026-11-10;dienst;W17;ja;;;;Fiktives Beispiel
Beispiel!A5;;;2026-11-11;termin;BK;;;;;Nur der Termin, noch keine Person
Beispiel!B4;Zeile 4;P01;2026-11-11;freiwunschtag;;;;;;Übergehbarer Wunsch
```

- `art`: dienst, termin, freiwunschtag, wochenendwunsch, urlaub oder ignorieren.
- `dienst`: tatsächlicher Katalogschlüssel; für reine Termine bleibt Person leer.
  Sonderdienste mit vorgeschriebenen festen Personen als Dienstzeilen erfassen.
- `datum`: YYYY-MM-DD, lokales Startdatum. Diensttermine gehören zum geöffneten
  Monat; Abwesenheiten über Monatsgrenzen müssen den Monat tatsächlich berühren.
- `fixiert`: ja / nein. Importierte Dienste standardmäßig ja; beide Plätze werden
  durch zwei Zeilen mit unterschiedlichen IDs besetzt. Doppelte Zeilen zählen einmal.
- `beginn`/`ende`: vollständige ISO-Zeitpunkte mit Datum, bei mehrdeutiger Ortszeit
  ausdrücklicher Offset. Für Katalogdienste gelten deren Zeiten; FK benötigt beide.
- `gutschrifttage`: ausdrücklich anrechenbare Urlaubstage, mit `|` getrennt.
- Optional: `pause_von`, `pause_bis` als konkrete ISO-Zeitpunkte. Leer bedeutet
  automatische Pause. Der Excel-Export erhält konkrete Pausen für den Reimport.
- Optional: `budgetmonat` als YYYY-MM für grenzüberschreitende Wochenendwünsche.
  Export/Reimport erhält den gewählten Monat ohne Doppelzählung.

UTF-8/BOM und Semikolon oder Komma als Trennzeichen werden unterstützt. XLSX-Formeln
in Importdaten werden nicht ausgeführt und zurückgewiesen. Die ursprünglichen
Datumsköpfe dürfen gespeicherte Formel-Cachewerte liefern; externe Verknüpfungen
werden nicht geöffnet oder neu berechnet. Grenzen: 16 MiB Datei, 64 MiB entpackt,
20.000 Zeilen und 64 Spalten bei Excel.

## Automatische BK-/WL-Termine

Die neue konkrete Vorgabe lautet **zwei WL und ein BK je Woche**, unabhängig vom
Monat. BK und WL dürfen niemals am selben lokalen Startdatum stattfinden; dies
wird auch ohne Wochenkonfiguration als harte Regel geprüft.

**BK/WL automatisch: 2 WL + 1 BK** konfiguriert die Woche ausdrücklich. Im normalen
Monatsablauf wird diese Auswahl vor der ersten Berechnung angefordert. Angeboten:

- Montag–Sonntag mit gemeinsam geplanten Randwochen: die komplette ISO-Woche,
  gegebenenfalls mit Terminen im Nachbarmonat. Keine unabhängige doppelte Quote.
- Nur volle Montag–Sonntag-Wochen im Monat: ausdrücklich abweichendes Profil;
  ausgeschlossene Randwochen werden als ungeprüft ausgewiesen.

Die globale betriebliche Randwochenentscheidung wird nicht stillschweigend geraten.
Die gewählte Einstellung wird gespeichert und in neue Folgemonate übernommen.
Der Solver wählt Termine und Personen gemeinsam, keine vorab festgezurrten Tage.
Offene Personenplätze bleiben erlaubt; verbindliche Termine, Zuteilungen und Regeln
bleiben erhalten. Die Eingabetabelle enthält Datumsoptionen, der fertige Plan nur
die tatsächlich gewählten Termine.

Bei bereits gespeicherten Nachbarmonaten werden gemeinsame Termine und vorhandene
Zuteilungen übernommen. Widersprüchliche nachträgliche Änderungen werden abgelehnt;
keine stille Änderung eines bestätigten oder gespeicherten Nachbarmonats.
„BK/WL automatisch“ übernimmt die gemeinsamen Vorgaben erneut. Randdaten werden
nicht als erfundene Freizeit betrachtet. Historie entsteht weiterhin erst durch
ausdrückliche Bestätigung; eine Reservierung erhöht sie nicht.

## Anzeige, Pausen und Export

**Dienstplan** zeigt Datum, Wochentag, Beginn/Ende, Person, Stunden, Pause und
Fixierung. **Monatsübersicht** ordnet Personen als Zeilen und Datum/Wochentag als
Spalten an. Namen bleiben beim horizontalen Scrollen sichtbar; Wochenenden sind
hervorgehoben. Offene Plätze tragen weiterhin den Text OFFEN.

Beim manuellen Eintragen wird nur die Person gewählt. Die App sucht eine
regelkonforme konkrete Pause: zuerst vollständig vor 22:00 des Starttags und
möglichst nahe der Dienstmitte, sonst möglichst in der Dienstmitte. Geschützte
Teamzeit und bekannte Abdeckungsregeln bleiben verbindlich. Bis sechs Stunden
wird aus der Normalregel keine Pause abgezogen. Fixierungen zuerst ausdrücklich
lösen; eine Pause beseitigt keinen Urlaubs-/Ruhe-/Doppelbelegungskonflikt.

**Monatstabelle als Excel exportieren** exportiert den sichtbaren Plan oder
Vorschlag als Person×Datum-Tabelle ähnlich der Vorlage: Wochentage, Wochenenden,
Kürzel, Urlaub und Wünsche, fixierte Namensspalten, Querformat-Druckeinstellungen.
Eigene Blätter enthalten offene Plätze, Stunden und reimportierbare Einzelzeilen.
Eine Vorschau ist noch keine Monatsbestätigung. Exportdateien werden atomar
veröffentlicht, vorhandene Dateien nicht überschrieben. Vollständige technische
Sicherung einschließlich Profile/Prüfmanifest weiterhin über **Exportpaket**.
