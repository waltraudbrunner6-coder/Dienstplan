# Dienstplan – die neue Hauptoberfläche

Ab Version 0.3.0 ersetzt V2 die frühere Oberfläche vollständig. Der vorherige
Testbereich und die Startauswahl entfallen. Die Anwendung verwendet eine
dauerhafte lokale V2-Datei; es wird kein flüchtiger Vier-Termine-Teststand mehr
beim normalen Start erzeugt. Der ausdrückliche Nutzerauftrag vom 10.11.2026
autorisiert diesen Oberflächenwechsel. Offene fachliche Profile werden dadurch
nicht entschieden.

## Monat und Standarddienste

**Monat wählen** lädt einen vorhandenen Monat oder legt einen neuen an.
Personen samt Vertragsversionen und Ausschlüssen werden im Folgemonat übernommen;
Anfangssalden kommen aus dem letzten bestätigten Vormonat, sonst bleiben die
bisherigen Anfangssalden erhalten. Das neue Wunschende ist null.
Gespeicherte andere Monate werden dabei nicht verändert.

Der Katalog unter **Dienste und Planungsangaben** ist sofort vorhanden:
T, KC10, KCT10, KC16, KCT, TS, W17, TW, W16, WL, BK, VN, LB, INT, N17, R, FK.
LB mit TS und die beiden R-Zeitfenster sind getrennte Varianten, insgesamt 19.
Dort stehen Uhrzeiten, Folgetag, Besetzung und Auftreten.

Im Monat sind die normalen Tagesmuster bereits eingetragen: außer Donnerstag
KC10 10:15–16:15 (1 Person), KC16 16:00–00:00 (1) und W17 17:00–01:00 (2).
Donnerstags KCT10 10:15–17:30 (1), KCT 14:30–00:00 (1), TW 14:30–00:00 (2)
und die Teamveranstaltung T 14:30–17:30. Für November 2026 sind dies
94 Termine, 120 operative Plätze und 876,00 Stunden Bedarf vor Sonderdiensten.
Reservefenster kommen täglich 24.12.–06.01. hinzu; ohne bestätigte Bewertung
werden sie nicht als volle Arbeitszeit angenommen oder automatisch besetzt.

Feste Sondertermine werden unter **Monatstermine** ergänzt. VN/INT/N17/LB/FK
brauchen feste Personenkennungen; FK zusätzlich konkrete ISO-Zeitpunkte.
W16 braucht einen dokumentierten Ersatzgrund. WL/BK sind im Katalog als
automatisch vorgesehen, erhalten aber vor Klärung von F06/F07 keine erfundene
Wochenquote oder still gewählte Wochentage. LB benötigt den gültigen
Donnerstagsanker und seine beiden Personen. Fehlende Angaben bleiben sichtbar.
Der Katalog allein bestätigt deshalb keine Monatsvollständigkeit.

## Personen und ausgeschlossene Dienste

Unter **Personen** Namen, Wochenstunden, Anfangs- und Wunschendsaldo bearbeiten.
**Arbeitsstand speichern** übernimmt Tabelleneingaben. Neue Dateien beginnen
mit einem leeren Team; fiktive Personen gibt es nur beim ausdrücklichen Demostart.

**Person ergänzen** fragt eine dauerhafte eindeutige Kennung ab.
**Person bearbeiten / Dienste ausschließen** enthält Beschäftigung,
zeitgültige Vertragsversionen und zeitgültige Dienstausschlüsse. Enddaten
sind derzeit als **ausgeschlossen** bezeichnet: Beschäftigung einschließlich
31.12. bedeutet Ende 01.01. Für Vertrags- und Ausschlussversionen ihre
Gültigkeitszeiträume vollständig erfassen.

**Ausgeschlossene Dienste auswählen** öffnet eine Liste mit Häkchen:
angehakt bedeutet ausgeschlossen; keine Häkchen bedeutet keine Ausschlüsse.
Die Liste lässt sich auch mit durch Leerzeichen getrennten Kürzeln bearbeiten.
Die bisherigen intern gespeicherten Berechtigungen werden durch das Komplement
verlustfrei dargestellt; bestehende Rechte werden beim Laden nicht erweitert.
N17 benötigt zusätzlich bestätigten Führerschein, unabhängig von Wochenstunden.
Die feste Personenbindung eines Sondertermins wird durch Ausschlüsse nicht
aufgehoben und kann bei Widersprüchen einen Eingabekonflikt erzeugen.

## Stunden

Konten und alle Arbeitszeitmengen erscheinen in Stunden mit zwei Dezimalstellen,
z. B. **7,50 h**, **-2,25 h**. Eingaben akzeptieren Dezimalkomma oder Punkt.
Wochenstunden bleiben exakt, auch mit mehr als zwei Nachkommastellen.
Intern wird weiterhin mit ganzen Minuten und exakten Bruchwerten gerechnet.
Geänderte Stundenwerte werden einmal kaufmännisch auf Minuten gerundet;
unverändert gespeicherte gerundete Anzeigen behalten die ursprünglichen Minuten.
Uhrzeiten bleiben Uhrzeiten, beispielsweise 10:15–16:15.

Die **Stundenprognose** enthält Soll, Anfangssaldo, Wunschende, Urlaubsgutschrift,
Arbeitsziel, geplante Arbeit, Prognose-Endsaldo und Abweichung. Die
**Schichtverteilung** zeigt Anzahl, Stunden und faire Anteile. **Freiwünsche**
zeigt relevante, erfüllte, übergangene, historische und kumulierte Wünsche.

## Urlaub, Wünsche und Planung

Manuelle Einträge und CSV-Format 2 verwenden denselben Korrekturstapel:

```csv
format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar
2;P01;urlaub-1;urlaub;2026-11-09T00:00;2026-11-11T00:00;2026-11-09|2026-11-10;Zwei ausdrücklich anrechenbare Tage
2;P01;wunsch-1;freiwunschtag;2026-11-11T00:00;2026-11-12T00:00;;Freiwunsch
```

Ende ist ausgeschlossen; Nachtintervalle benötigen das tatsächliche Enddatum.
Donnerstagsanteile sind bei Wünschen unzulässig. Fehlerhafte Stapel bleiben
vollständig bearbeitbar vorgemerkt; keine teilweise aktive Übernahme.
Beim Bearbeiten eines aktiven Eintrags bleibt sein alter Stand bis zur
vollständig geprüften atomaren Ersetzung aktiv. Wunschbudgets ausdrücklich
prüfen; vorhandene Anzeigewerte sind keine betriebliche Profilbestätigung.

Vor **Dienstplan erstellen** unter **Dienste und Planungsangaben** das technische
Rechenprofil S0/M0/E0 ausdrücklich wählen. Dies entscheidet keine offenen
Rechts-/Abrechnungsfragen. S0 summiert gültige Wochenstunden / 7 je
Beschäftigungstag und rundet einmal monatlich; M0 ordnet physische Arbeit dem
Kalendermonat zu. Urlaub berücksichtigt nur ausdrücklich anrechenbare Tage
mit gültigem W/5. Ziel `S+E−B−G`, Prognoseende `B+P+G−S`.
Fehlende Urlaubsgutschrifttage bleiben ungeklärt, keine angenommene Nullgutschrift.

Die Berechnung läuft im Hintergrund und ist abbrechbar. Nach der Berechnung öffnet sich automatisch **Dienstplan** mit dem unabhängig
geprüften Vorschlag. Die Tabelle zeigt zugeteilte Namen und offene Plätze sofort;
Stunden, Schichtverteilung und Wünsche beziehen sich ebenfalls auf diese Vorschau.
**VORSCHLAG – noch nicht gespeichert** kennzeichnet den Zustand.
**Ergebnis übernehmen** speichert ihn dauerhaft. **Vorschlag verwerfen und bisherigen
Plan anzeigen** stellt die bisherige Anzeige wieder her. Bis zur Übernahme bleibt
der gespeicherte Plan unverändert. Ein Export enthält den gerade sichtbaren
Vorschlag; manuelle Änderungen und Monatsbestätigung verlangen zuerst seine Übernahme. Geänderte Eingaben machen ein
laufendes Ergebnis veraltet. Offene Plätze sind mit **OFFEN** bezeichnet;
fehlende Randdaten gelten nicht als Freizeit. Manuelle Zuteilungen und Fixierungen
werden mit denselben Regeln geprüft. Änderungen verwerfen bestehende
Optimalitätsnachweise; ein Zeitlimit ist kein Beweis der Unlösbarkeit.

**Monat bestätigen** friert ausschließlich einen gültigen vollbesetzten
Rechenstand mit seinen ausgewählten Annahmen ein, keine KV-/BV- oder
Tariffreigabe. Bestätigte Stände sind geschützt; Aufhebung/Ablösung ist noch
nicht bedienbar. Wiederholen erzeugt keine doppelte Historie.

## Datei und Export

Die Standarddatei heißt **dienstplan-v2.sqlite3** im lokalen Anwendungsdatenordner.
Beim nächsten Start wird der zuletzt vorhandene Monatsarbeitsstand geladen.
**Datei öffnen** unterstützt bisherige V2-Dateien mit Schema 3.
**Neue Datei** speichert eine separate Kopie des Arbeitsstands.
Die frühere `dienstplan.sqlite3` wird nicht automatisch geöffnet oder verändert.
Sie wird nicht ungeprüft als Urlaub/BK/WL umgedeutet.

**Exportpaket** erzeugt ein neues ZIP mit Dienstplan, Stunden, Verteilung,
Wünschen, Zeitmengen, exaktem Arbeitsstand und Prüfmanifest. CSV-Zeitspalten sind
in Stunden mit Dezimalkomma und benannter Einheit; das Arbeitsstand-JSON behält
exakte Minuten für verlustfreies Laden. Alle Dateien tragen dieselbe
Revisions-ID und sind per Hash zusammengehörig. Feiertagsmengen ohne übergebenen
Kalender und unbekannte Urlaubsgutschriften sind `null`, nicht fälschlich null
Stunden. Bestehende Exportdateien werden nicht überschrieben.

Offene Produktprofile und tatsächliche Prüfstände:
[offene Fragen](V2_OFFENE_FRAGEN.md), [Fortschritt](V2_FORTSCHRITT.md),
[native Downloads](V2_NATIVE_PRUEFUNG.md), [Abnahmestatus](V2_ABNAHMESTATUS.md).
