# Dienstplan – Bedienung ab 0.5.1

Die Anwendung plant und speichert vollständig lokal. V2 ist die normale
Hauptoberfläche, kein zusätzlicher Prüfbereich. Fiktive Personen erscheinen
nur bei einem ausdrücklich gestarteten Demo. Die tatsächliche Version und
Buildkennung stehen im Fenster; geprüfte Downloads in `V2_NATIVE_PRUEFUNG.md`.
Die 0.5.1-Korrektur ist erst mit dem dort ausgewiesenen nativen Paket auch für
die jeweilige Plattform belegt. Eine vorhandene Datenbank weiter öffnen;
wegen dieser Korrektur ist kein Neuimport erforderlich.

## 1. Monat und Personen

**Monat wählen** lädt einen vorhandenen Monat oder legt einen neuen an. Andere
gespeicherte Monate bleiben erhalten. Personen, Verträge und Ausschlüsse werden
übernommen; Stunden-Anfangssalden kommen aus dem letzten bestätigten Vormonat,
sonst bleiben vorhandene Anfangssalden erhalten. Neue Wunschendsalden sind null.

Unter **Personen** Namen, Wochenstunden und Stundensalden bearbeiten und mit
**Arbeitsstand speichern** übernehmen. **Person ergänzen** benötigt eine stabile
Kennung. **Person bearbeiten / Dienste ausschließen** verwendet Kalender für
Beschäftigung und Gültigkeitszeiträume sowie eine Ausschlussliste. Die angezeigten
letzten Tage sind einschließlich; technisch speichert die App das Ende am
folgenden lokalen Mitternachtspunkt. Bestehende exklusive Datengrenzen werden
nicht um einen Tag verschoben.

Ein Häkchen bedeutet „ausgeschlossen“, kein Häkchen „nicht ausgeschlossen“.
N17 benötigt zusätzlich bestätigten Führerschein. Wochenstunden allein erzeugen
keine Qualifikation oder besondere Dienstberechtigung. Vertragswechsel lassen
sich mit eigenen Gültigkeitszeiträumen erfassen.

## 2. Dienste und Monatstermine

Unter **Dienste und Einstellungen** sind der Katalog mit Zeiten, Folgetag,
Besetzung und Auftreten sowie die verständliche Stundenregel sichtbar. Vor einer
normalen Planung muss kein technischer Name wie S0/M1/E0 ausgewählt werden.

Regulär sind außer Donnerstag KC10 10:15–16:15 (eine Person), KC16 16:00–00:00
(eine) und W17 17:00–01:00 (zwei). Donnerstags stehen KCT10 bis 17:30, KCT und
TW ab 14:30 bis 00:00 sowie die Teamzeit T 14:30–17:30. TS ersetzt an den
gewählten Donnerstagen die Teamveranstaltung und läuft bis 19:30.

**Termin hinzufügen** öffnet Kalender, Dienst, Uhrzeiten und Namensauswahl.
Bei regulären Vorlagen werden die Zeiten erklärt; für FK können eigene Uhrzeiten
angegeben werden. Bei einem Ende am Folgetag das entsprechende Feld setzen.
Im Herbst benötigen doppelte Uhrzeiten eine ausdrückliche Variante. Eine nicht
existierende Frühlingszeit wird nicht still verschoben.

VN, INT, N17, LB und FK benötigen die vorgesehenen festen Personen. FK ist
ausschließlich ein einzeln erfasster Termin ohne automatische Wiederholung.
W16 benötigt einen dokumentierten Ersatzgrund. R zählt wie normale Arbeit: früh 10:15–16:15
sechs Stunden, spät 16:00–00:00 nach Pause 7,5 Stunden. Die Reservefenster werden
vom 24.12. bis einschließlich 06.01. zusätzlich erzeugt.

**LB-Termine ergänzen** fragt zwei Namen ab und ergänzt die fehlenden Termine
des geöffneten Monats. Der feste Rhythmus beginnt am Donnerstag, 03.12.2026,
und läuft alle 14 Tage über Monats-/Jahresgrenzen weiter. Schon vorhandene
LB-Paare werden dabei erhalten. An TS-Tagen läuft LB bis 19:30.

KC15 ist ein Ersatz für das gemeinsame Tagespaar KC10 und KC16: eine Person
15:00–00:00, darin eine halbe Stunde Pause. Er kommt nicht zusätzlich zu beiden
regulären Diensten hinzu. Die automatische Planung bevorzugt bei gleicher
Besetzbarkeit weniger Ersatztermine, bevor sie Wünsche und Stundenfairness
optimiert. Bei Zeitlimit beweist ein gefundener Ersatzplan noch nicht, dass das
reguläre Paar unmöglich wäre; der tatsächliche Nachweisstatus bleibt maßgeblich.

**Termin entfernen** betrifft nur diesen Termin mit seinen Zuteilungen und
Fixierungen. Die anderen Dienste bleiben erhalten. Gleiches gilt beim Ergänzen.
Nach Prüfung wird die Änderung vor der neuen Anzeige gespeichert; Abbruch oder
Schreibfehler lassen den bisherigen Stand unverändert.

## 3. BK und WL

Ganzjährig sind zwei WL- und ein BK-Termin je Woche vorgesehen. BK und WL dürfen
nicht dasselbe lokale Startdatum haben. Über **BK/WL automatisch: 2 WL + 1 BK**
die Wochen-/Randregel wählen; die entsprechende automatische Planung fordert sie
bei Bedarf an. Zur Wahl stehen gemeinsame ISO-Randwochen oder nur volle
Montag–Sonntag-Wochen im Monat. Folgemonate übernehmen die gewählte Einstellung.

Das Einrichten erhält bestehende Zuteilungen; zusätzliche benötigte Termine
werden offen angezeigt. Der Solver verbindet Datum und Personenwahl. Bereits
optionale Daten bleiben innerhalb der gewählten Quoten für spätere Optimierungen
frei. Manuelles Zuordnen öffnet dieses Einstellungsfenster nicht.

## 4. Urlaub und Wünsche ohne technische Datumslisten

Unter **Urlaub und Wünsche** auf **Urlaub oder Freiwunsch hinzufügen** klicken:

1. Person und Art wählen: Urlaub, einzelner Freiwunsch oder Wochenendwunsch.
2. Bei ganztägigen Einträgen ersten und letzten Tag im Kalender wählen. Der
   letzte angezeigte Tag zählt mit. Bei Uhrzeiten werden Beginn und tatsächliches
   Enddatum benötigt; die Endzeit selbst gehört nicht mehr zum Intervall.
3. Bei Urlaub die angezeigten Tage und Stunden prüfen. Jeder Tag des ausdrücklich
   gewählten Urlaubszeitraums zählt, auch Samstag, Sonntag und Feiertag. Sollten
   nur einzelne getrennte Daten Urlaub sein, diese als getrennte Einträge erfassen.
4. **Eintrag speichern** wählen und eventuelle Konflikte prüfen.

Pro Urlaubstag gilt der dann gültige Wochenvertrag ÷ 5: 25 Wochenstunden ergeben
fünf Stunden je Tag. Vertragswechsel werden an den betreffenden Tagen berücksichtigt.
Doppelte oder überlappende Einträge schreiben denselben Personen-/Kalendertag
nur einmal gut. Abwesenheit und Stundengutschrift sind keine zusätzlich geleistete
Arbeit und belegen keine freien Tage als Arbeitstage.

Alte Meldung „Urlaubsgutschrifttage ungeklärt“: Für den gespeicherten Urlaub
fehlte die Tagesmenge, nicht die Formel. Unter **Urlaubsübersicht** →
**Fehlende Urlaubstage auswählen** den Eintrag öffnen, seinen Zeitraum und die
angezeigten Tage prüfen und übernehmen. Eine fehlende Tagesauswahl wird nicht
als null Gutschrift ausgegeben. Bei der Monatsbestätigung kann die App direkt
zu dieser Korrektur führen.

**Aktiven Eintrag bearbeiten** übernimmt den neuen Stand erst nach gemeinsamer
Prüfung; bestätigte Geschichte wird nicht umgeschrieben. Freiwünsche sind weiche
Ziele. Beim Wochenendwunsch zählt ein am Freitag begonnener, nur in den Samstag
hineinragender W17 allein nicht als Verletzung. Sonstige Arbeit am Samstag oder
Sonntag verhindert diese Ausnahme. Ein Donnerstagseintrag erzeugt einen
Regelhinweis und kann wie andere fachliche Abweichungen ausdrücklich übergangen
werden. Es gibt keine stille
Kürzung oder Umwandlung in Urlaub.

## 5. Urlaubskonto und Resttage

In **Urlaubsübersicht** → **Urlaubskonto bearbeiten** pro Person den Kontenstart
und Anfangsbestand in Urlaubstagen eingeben. Der Anfangsbestand gilt vor der
Gutschrift des Startmonats. Wenn sicher kein Rest vorhanden ist, ausdrücklich
`0` eintragen; ein leerer Wert wird nicht geraten.

Ab Kontenstart kommen je vollem Beschäftigungsmonat zwei Anspruchstage dazu.
Bei Teilmonaten gilt exakt: zwei Tage × Beschäftigungskalendertage ÷
Kalendertage des Monats. Anspruchsbruchteile werden ohne pauschale Tagesrundung
weitergeführt. Verwendete Urlaubstage werden einmal abgezogen; der Rest wird
angespart. Zwei Tage pro Monat sind kein Verbot, in einem Monat mehr als zwei Urlaubstage zu
verwenden. Ein negativer prognostizierter Rest wird als Hinweis ausgewiesen.

Die Übersicht trennt Anfang, erworbenen Anspruch, Verbrauch, Resttage und
Stundengutschrift des Monats. Gespeicherte Bestätigungen haben Vorrang vor späteren
Entwurfsänderungen. Fehlende historische Monate werden nicht als sicher ohne
Urlaub behandelt. Ein unbekannter Bestand wird als ungeklärt gezeigt, nicht null.
Beispiel: 15 Beschäftigungstage in einem Monat mit 30 Tagen ergeben einen
Anspruchstag. Eine gerundete Anzeige ändert den exakten Bestand nicht.

## 6. Stunden und Monatsbuchung

Stunden erscheinen mit Dezimalkomma, zum Beispiel **7,50 h**. Dezimalkomma und
Punkt werden bei der Eingabe akzeptiert. Intern bleiben ganze Minuten und exakte
Brüche erhalten; unveränderte gerundete Anzeigen verlieren beim Speichern keine
Minute.

```text
Monatssoll S = Summe der gültigen Wochenstunden ÷ 7 je Beschäftigungstag
Arbeitsziel = S + gewünschter Endsaldo E − Anfangssaldo B − Urlaubsgutschrift G
Prognose-Endsaldo = B + geplante Arbeitsstunden P + G − S
```

Bei konstanten Wochenstunden ergibt das W × Kalendertage ÷ 7, keine pauschalen
vier Wochen. Soll und Urlaub werden je Person/Monat exakt summiert und erst am
Ende einmal auf Minuten gerundet. Ein negatives Ziel erzeugt keine negative Arbeit.

Neue offene Monate verwenden die bestätigte Startmonatsbuchung M1: Ein Dienst
am 30.11. von 17:00 bis 01:00 mit 30 Minuten Pause zählt mit 7,5 Stunden vollständig
zum Novemberkonto. Physische Tages-/Nacht-/Sonn-/Feiertagsminuten bleiben nach
wirklichen Kalendertagen getrennt. Deshalb kann eine Kalender-Zeitmengenübersicht
von der Buchungsmenge des Stundenkontos abweichen, ohne Minuten zu verlieren.

Alte bestätigte Monatsstände mit M0 bleiben unverändert. Die Anzeige benennt dort
die historische Zuordnung nach tatsächlichen Kalendertagen. Offene reguläre
Monatsstände werden beim Laden auf die neue Regel umgestellt; bestätigte Historie
wird dabei nicht neu bewertet.

## 7. Planen, prüfen und manuell ändern

**Dienstplan erstellen** berechnet im Hintergrund mit Zeitlimit und Abbruch.
Ein vorhandener gültiger Plan dient als Startpunkt. Fehlende Randdaten sind
unbekannt und kein Beleg für Freizeit. Ein Zeitlimit ist kein Beweis der Unlösbarkeit.

Ab 0.5.1 blockiert eine bereits genehmigte Freiwunsch-Ausnahme, etwa ein Wunsch
mit Donnerstagsanteil, nicht mehr alle Dienstkandidaten. Zuvor konnte deshalb die
Meldung **Die fixierten Vorgaben lassen sich so nicht gemeinsam planen** erscheinen,
obwohl die Fixierungen selbst gültig waren. Genehmigte Wünsche bleiben aktiv und
als Ausnahme sichtbar; ihre Zustimmung bleibt beim Speichern und bei ansonsten
gültigen manuellen Änderungen erhalten. Das Ergebnis gilt unter diesen
genehmigten Wunschvorgaben, ohne dadurch einen Optimalitätsnachweis zu erhalten.

Tatsächliche Fixierungskonflikte verschwinden dadurch nicht. Eine Fehlermeldung
nennt die betroffene Person, Datum und Dienst; bei Ruhekonflikten auch vorhandene
und fehlende Stunden. Beispielsweise sind zwei
gleichzeitige fixierte Dienste oder ein fixierter Dienst mit zu kurzer Ruhezeit
weiterhin kein automatisch gültiger Plan. Betroffene Zuteilung im Dienstplan
prüfen, ändern oder ihre Fixierung ausdrücklich lösen; die App löst sie nicht
ungefragt. Urlaub, Beschäftigung, Berechtigungen und Ruhe bleiben für die
automatische Planung verbindlich.

Der Vorschlag erscheint sofort im **Dienstplan**. **Monatsübersicht** zeigt die
Personen-/Tagesmatrix; **Stundenprognose**, **Schichtverteilung** und **Freiwünsche**
beziehen sich auf denselben sichtbaren Stand. **OFFEN** markiert fehlende Plätze.
**Ergebnis übernehmen** speichert den Vorschlag; erst damit ersetzt er den bisherigen
Entwurf. **Vorschlag verwerfen und bisherigen Plan anzeigen** stellt die vorherige
Anzeige wieder her. Ein Export kann auch den sichtbaren Vorschlag enthalten;
manuelle Änderung und Monatsbestätigung verlangen vorher seine Übernahme.

**Zuteilung ändern** öffnet direkt die Namensauswahl. Die Pause wird automatisch
möglichst vor 22:00 gesetzt, sonst mittig; sie liegt innerhalb des Blocks und
verändert dessen Beginn/Ende nicht. Bei mehr als sechs Stunden bleibt es eine
30-Minuten-Pause. Gleichzeitige Pausen verschiedener Personen sind erlaubt.

Bei einem fixierten Dienst wird ein bestätigter Personenwechsel mit neuer
Fixierung gespeichert; beim Entfernen verschwindet auch die zugehörige Fixierung.
Gleicher Name oder Abbruch lässt den Dienst samt Pause unverändert. Andere Termine
und Zuteilungen werden nicht nebenbei neu verteilt.

Fachliche Regelverletzungen werden weiterhin geprüft. Bei manueller Änderung,
Import und Monatsbestätigung darf die Bedienperson nach ausdrücklicher Warnung
trotzdem übernehmen. Die Abweichung bleibt sichtbar. Ungültige IDs, widersprüchliche
Zeitangaben oder fehlende technische Definitionen werden dadurch nicht erfunden.
Die automatische Planung erhält keine allgemeine Erlaubnis, Schutzregeln zu verletzen.

## 8. Import und Export

**Termine / Dienstplan / Wünsche importieren** liest XLSX oder CSV. Die Vorschau
ordnet Personen-IDs zu und lässt Korrekturen zu. Gelbes X in einer Wunschtabelle
ist Freiwunsch, Grün wird wie beauftragt ignoriert, Kürzel sind vorgegebene Dienste.
U bedeutet nun Urlaub; jedes ausdrücklich markierte Datum zählt. KC10 am Donnerstag
wird als bestätigter KCT10 bis 17:30 kenntlich zugeordnet. R braucht die konkrete
frühe oder späte Variante; gleiche Zeiten und Kürzel dürfen nicht geraten werden.

KC15 und KC10/KC16 desselben Tages sind keine gemeinsam importierbare Doppelbesetzung.
Fehlerhafte Importe bleiben als ganzer Stapel vorgemerkt; keine teilweise Übernahme.
Mit **Regeln für diesen Import übergehen** und zusätzlicher Bestätigung sind
fachliche Abweichungen erlaubt. Technische Fehler bleiben zu korrigieren.
Identische Dienste/Fixierungen werden nicht doppelt angelegt. Bestehende konkrete
Pausen werden beim Reimport wiederverwendet.

CSV-Format 2 bleibt für Abwesenheiten lesbar:

```csv
format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar
2;P01;urlaub-1;urlaub;2026-11-09T00:00;2026-11-11T00:00;2026-11-09|2026-11-10;Zwei Urlaubstage
2;P01;wunsch-1;freiwunschtag;2026-11-11T00:00;2026-11-12T00:00;;Freiwunsch
```

`bis` ist im Dateiformat weiterhin ausgeschlossen; das Kalenderformular zeigt bei
Ganztägigkeit den letzten enthaltenen Tag. UTF-8/BOM und Komma/Semikolon werden
unterstützt. Details: `TABELLENIMPORT.md`.

**Monatstabelle als Excel exportieren** liefert eine vergleichbare Personen-/Tages-
Matrix mit Datum und Wochentag sowie Einzelzeilen zum Reimport.
**Exportpaket** enthält CSVs, exakte Monatsdaten und Prüfmanifest mit gemeinsamer
Revisions-ID und Hashes. Stundenkonto und physische Zeitmengen sind ausdrücklich
getrennt. Bestehende Exportdateien werden nicht überschrieben.
Das Prüfmanifest nennt genehmigte Freiwunsch-Ausnahmen gesondert und kennzeichnet
die Bewertung als unter diesen Vorgaben erfolgt. Die strengen Prüfhinweise
bleiben enthalten.

## 9. Monat bestätigen und Dateien sichern

**Monat bestätigen** zeigt Regelmeldungen, offene Plätze, Stundenabweichungen und
ungeprüfte Regeln. Mit **Ja** wird der vorhandene Stand trotzdem unveränderlich
bestätigt; **Nein** lässt ihn unverändert bearbeitbar. Gespeicherte Hinweise bleiben
auch nach Neustart sichtbar. Wiederholen erzeugt keine zusätzliche Historie.
Eine Bestätigung erklärt den Plan nicht für regelkonform oder tariflich abgerechnet.
Bereits bestätigte Monate bleiben geschützt; Aufhebung/Ablösung ist nicht bedienbar.

Die Standarddatei liegt als `dienstplan-v2.sqlite3` im lokalen Anwendungsdatenordner.
**Datei öffnen** lädt bisherige V2-Dateien. **Datei kopieren** speichert den aktuellen
Arbeitsstand mit seinen Urlaubskonteneinstellungen separat; sie setzt die Daten
nicht zurück und ist keine vollständige Archivkopie aller anderen Monate.
Für eine vollständige Sicherung die App schließen und die SQLite-Datei kopieren.
Die frühere V1-Datei `dienstplan.sqlite3` wird nicht automatisch verändert oder
ungeprüft als Urlaub/BK/WL umgedeutet.

Die Anwendung bleibt offline nutzbar. Verbleibende Sonderfragen und tatsächliche
Prüfstände: `V2_OFFENE_FRAGEN.md`, `V2_FORTSCHRITT.md`, `V2_NATIVE_PRUEFUNG.md` und
`V2_ABNAHMESTATUS.md`. Eine Beschreibung der Bedienung ersetzt keinen Buildnachweis.
