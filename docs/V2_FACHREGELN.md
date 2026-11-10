# V2 – Fachregeln

**Folgeauftrag Tabellenimport (10.11.2026):** zwei WL und ein BK pro Woche
unabhängig von der Saison; BK/WL niemals am selben lokalen Startdatum. Die
Randwochenentscheidung bleibt ausdrücklich auszuwählen. Manuelle Zuteilungen
wählen ihre konkrete Pause automatisch vor 22 Uhr, sonst möglichst in der
Dienstmitte, jeweils unter allen harten Regeln. Donnerstagswünsche/KC15/R und
KC10 am Donnerstag werden aus unklaren Excel-Angaben nicht neu interpretiert.
Siehe [Tabellenimport](TABELLENIMPORT.md).

**Aktualisierung 10.11.2026:** Der ausdrückliche Folgeauftrag ersetzt ab Version 0.3.0 die alte Oberfläche durch die V2-Hauptanwendung. Es gibt keinen zusätzlichen Testbereich mehr. Dienstrechte werden als zeitgültige **Ausschlüsse** bedient; gespeicherte Rechte bleiben durch verlustfreie Komplementdarstellung erhalten. Zeitmengen erscheinen in Stunden, intern bleiben Minuten/Brüche. Neue Monate erhalten den Standardkatalog und die bestimmten Tagesmuster automatisch. Dieser Oberflächenauftrag entscheidet keine offenen Fach-/Tarifprofile und autorisiert keine Migration echter Altdateien. Historische Aussagen zum parallelen Altbetrieb weiter unten beschreiben den vorherigen Stand. Details: [Bedienung](V2_BEDIENUNG.md), [Fortschritt](V2_FORTSCHRITT.md).

Aktueller Implementierungs- und Prüfstand: [Fortschritt](V2_FORTSCHRITT.md),
[Zuordnung aller 125 Abnahmefälle](V2_ABNAHMESTATUS.md) und
[Bedienung des technischen Prüfbereichs](V2_BEDIENUNG.md). Die nachfolgende
Etappe-A-Spezifikation bleibt die fachliche Grundlage; Testprofile ersetzen sie nicht.

Stand 09.11.2026, Etappe A. **Soll-Spezifikation, keine implementierte V2-Funktion.**
Die Altversion bleibt nach [Spezifikation 0.2](SPEZIFIKATION.md) bedienbar.
Feste Anforderungen dieses Dokuments werden nicht erneut zur Entscheidung gestellt.
`Fxx` bezeichnet eine tatsächlich offene Entscheidung in
[V2_OFFENE_FRAGEN.md](V2_OFFENE_FRAGEN.md). Technische Festlegungen sind als solche
benannt; Testprofile ersetzen keine betriebliche/rechtliche Bestätigung.

## 1. Identitäten und Begriffe

Person, zeitgültiger Vertrag, Dienstvorlage, Veranstaltung, Besetzungsbedarf,
Dienstblock, Zuteilung, Arbeitsabschnitt, Pause und Gutschrift sind getrennte Objekte.
Ein Bedarf zählt besetzte Plätze mit **unterschiedlichen** berechtigten Personen.
Tätigkeits- und Teilnahmereferenzen erzeugen keine zusätzlichen Stunden.

Pro Person und lokalem **Dienststartdatum** höchstens ein Dienstblock.
VN und KC16 am selben Startdatum bleiben zwei verbotene Einsätze, selbst mit
ausreichendem Abstand. Ein vom Vortag hineinragender Dienst ist kein zweiter
Start am neuen Datum. Zwei Nachtdienste mit verschiedenen Startdaten sind bei
elf Stunden tatsächlicher Ruhe und sonst erfüllten Regeln möglich.
Nur ausdrücklich definierte zusammengesetzte Dienste sind ein gemeinsamer Block.
Eine echte Pause darin teilt ihn nicht in zwei Dienste. Es gibt keine allgemeine
Funktion, mit der beliebige Einsätze zu einem legalen Block zusammengeklebt werden.

## 2. Vollständiger Dienstkatalog

Alle Uhrzeiten sind **Europe/Vienna**; `+1` ist der folgende Kalendertag.
Arbeitswerte gelten ohne Zeitumstellung und, bei R, ausschließlich bei bestätigter
voller Arbeitsbewertung. Die Pause ist bereits in der Anwesenheit enthalten.

| Kürzel | Anwesenheit | Auftreten / Bedarf | Pause / bezahlte Arbeit im Normalfall |
| --- | --- | --- | --- |
| T | 14:30–17:30 | Jeder Donnerstag; weiches Teilnahmeziel für jede aktive, nicht ausgenommene Person; keine zusätzliche pauschale Zweierbesetzung | 0 / 180 min |
| KC10 | 10:15–16:15 | Täglich außer Donnerstag, Innendienst früh, 1 Person | 0 / 360 min |
| KCT10 | 10:15–17:30 | Jeden Donnerstag, Innendienst früh mit vollständigem T, 1 Person; anstelle KC10 | 30 / 405 min |
| KC16 | 16:00–00:00 +1 | Täglich außer Donnerstag, Innendienst spät, 1 Person | 30 / 450 min |
| KCT | 14:30–00:00 +1 | Jeden Donnerstag, Innendienst spät mit vollständigem T, 1 Person; anstelle KC16 | 30 / 540 min |
| TS | 14:30–19:30 | Ausgewählte Donnerstage, ersetzt die T-Veranstaltung; weiches Teilnahmeziel | 0 / 300 min |
| W17 | 17:00–01:00 +1 | Täglich außer Donnerstag, Außendienst, 2 verschiedene Personen | 30 / 450 min je Person |
| TW | 14:30–00:00 +1 | Jeden Donnerstag, Außendienst mit vollständigem T, 2 verschiedene Personen; anstelle W17 | 30 / 540 min je Person |
| W16 | 16:00–00:00 +1 | Dokumentierte Ausnahmealternative zu W17; derselbe Außendienstbedarf, 2 verschiedene Personen | 30 / 450 min je Person |
| WL | 18:00–02:00 +1 | Zusatz-Außendienst; **Neue Vorgabe 10.11.2026: 2 verschiedene Termine je Bezugswoche in jedem Monat**; je 2 Personen | 30 / 450 min je Person |
| BK | 20:00–04:00 +1 | Zusatz-Außendienst; 1 Termin je Bezugswoche, 2 Personen | 30 / 450 min je Person |
| VN | 10:00–12:00 | Festgelegte Tage, jeweils festgelegte Person, 1 Platz | 0 / 120 min |
| LB | 12:00–17:30; an TS-Tagen bis 19:30 | Jeder zweite Donnerstag ab Referenzdatum, 2 festgelegte Personen; enthält T bzw. gesamte TS-Veranstaltung | regulär 0 / 330 min; TS-Tag 30 / 420 min |
| INT | 16:00–00:00 +1 | Zwei festzulegende Tage pro Monat, jeweils festgelegte Person, 1 Platz | 30 / 450 min |
| N17 | 17:00–01:00 +1 | Ein festzulegender Tag pro Monat, festgelegte Person, 1 Platz | 30 / 450 min |
| R | früh 10:15–16:15; spät 16:00–00:00 +1 | Zusätzlich täglich 24.12.–06.01. einschließlich, je Zeitfenster 1 Person; zwei separate Bedarfe, niemals dieselbe Person in beiden | bei voller Arbeit: früh 0 / 360 min; spät 30 / 450 min; Bewertung noch F02 |
| FK | individuell | Ein festzulegender Tag, festgelegte Person, Wiederholungszeitraum F09 | aus dem konkreten Zeitraum; über 6 h genau 30 min aus dieser Vorgabe |

Die feste operative Donnerstagsgrundbesetzung ist damit KCT10=1, KCT=1, TW=2.
Keine zusätzlichen KC10/KC16/W17-Termine an diesem Donnerstag erzeugen.
R, WL/BK und feste Sondertermine sind zusätzliche Bedarfe nach ihren Regeln.
W16 und W17 sind Alternativen **eines** Bedarfs, keine zwei parallelen Bedarfe.
Für INT sind zwei konkrete Termine zu erfassen; keine unbekannten Daten ergänzen.

WL/BK stehen standardmäßig auf **Automatisch**. Der Solver wählt Termine und
Personen gemeinsam; bei 2 WL sind zwei verschiedene Startdaten nötig. Ein
Wochentags-/Datumsfilter schränkt Kandidaten ein; ein festgelegter Termin wird
nicht verschoben. Eine Datumsfixierung fixiert keine Person. Personenfixierungen
sind eigenständige Vorgaben. Unvereinbare fixe Daten werden gemeldet, nicht
stillschweigend umgeplant. Sonntag/Feiertag möglichst vermeiden, nicht verbieten.
WL/BK-Ausschluss ist verbindlich; seine Abgrenzung ist F07. Wochenbesitz,
Randquoten und November/Dezember-/Jänner/Februar-Übergänge sind F06.
LB verwendet einen echten Zweiwochenrhythmus über Monats-/Jahresgrenzen (F08),
keinen Neustart am ersten Donnerstag jedes Monats.

## 3. Personen und Beschäftigung

- Name/ID, Beschäftigungsbeginn/-ende, zeitgültige Wochenstunden, Anfangssaldo,
  individuell änderbarer gewünschter Endsaldo, Führerschein und explizite
  Dienstberechtigungen. Keine Namen als technische Identitäten.
- Für neue V2-Monate gilt standardmäßig `E=0`; `B` bleibt erhalten. Bestehende
  gespeicherte Endsaldoziele und bestätigte Altpläne werden nicht geändert.
- Beschäftigungsende wird in der UI als letzter eingeschlossener Kalendertag
  erfasst; technisch gilt ein exklusives Ende am folgenden lokalen Mitternachtspunkt.
  Der gesamte Block muss im Beschäftigungsintervall liegen, nicht nur sein Start.
- N17 erfordert Führerschein. Keine zusätzliche Führerscheinpflicht für andere
  Dienste ableiten. Sonstige ausdrücklich erfasste Berechtigungen bleiben nötig.
- Die auf zwei Monate befristete Außendienstperson ist operativ ausschließlich
  für W17, W16, BK, WL, N17 und TW berechtigt. Zusätzlich darf und soll sie T/TS
  besuchen; daraus folgen keine Rechte für Innendienst, Lager, VN, INT, FK oder R.
- Berechtigung, Vertrag und Beschäftigung werden zeitgültig geprüft. Bei fehlender
  Berechtigung entsteht kein Fairness-Sollanteil für diese Dienstklasse.
- Konkrete Beschäftigungsdaten, Wochenstunden, TS-/VN-/INT-/N17-/FK-Termine und
  feste Personen sind Monatseingaben, keine erneut zu klärenden Fachregeln.

## 4. Gemeinsame Teamzeit

Je Donnerstag genau eine Teamveranstaltung: T oder an ausgewählten Tagen TS.
Erfüllende Blöcke werden ausdrücklich zugeordnet; reine Intervallüberlappung
genügt nicht als Nachweis einer Teilnahme oder einer zweiten operativen Tätigkeit.

| Zugewiesener Block | Normaler Donnerstag | TS-Donnerstag |
| --- | --- | --- |
| KCT10, KCT, TW | ganzes T erfüllt, kein separater T-Dienst | ganzes T erfüllt; vom zusätzlichen TS-Teilnahmeziel ausgenommen |
| LB | ganzes T erfüllt, ein Block | verlängert 12:00–19:30; ganzes TS einschließlich T erfüllt, ein Block, eine Pause |
| BK-Ausnahme | Teilnahmeziel ausgenommen | T-/TS-Ziele ausgenommen |
| T bzw. TS allein | T als eigener Block | TS als eigener Block; kein zusätzlicher T-Block |
| Andere berechtigte aktive Person | T-Teilnahme wichtiges weiches Ziel | volle TS-Teilnahme wichtiges weiches Ziel |
| Urlaub / nicht beschäftigt | keine Zuteilung | keine Zuteilung |

Die TS-Ausnahmen sind **KCT10, KCT, BK, TW**. Die frühere Schreibweise KC10 ist
ersetzt. Eine TS-Ausnahme bei erfülltem T ist kein versäumtes T. Die befristete
Außendienstperson ist ausdrücklich im Teilnahmeziel enthalten.

T/TS sind **keine harte Pflicht**. Urlaub, Beschäftigung, Berechtigungen,
Ein-Block-Regel, Ruhe, Arbeitstagsfolgen und Wochenendregeln haben Vorrang.
Beispiel: BK-Ende 04:00 bis Teamstart 14:30 sind nur 10:30 h; keine illegale
Teilnahme erzwingen. Im Ergebnis erlaubte BK-Ausnahme bzw. Ruhezeitursache nennen.
Kein verspätetes Eintreffen, früheres Verlassen oder zusätzlicher T-Block erfinden.
BK-Ausnahmen beziehen sich auf den konkreten betroffenen Teamtag, nicht auf
sämtliche Donnerstage eines Monats, in dem jemand einmal BK übernimmt.

Eine Teilnahme wird pro Person/Veranstaltung höchstens einmal bewertet. An TS-Tagen
nicht gleichzeitig „T fehlt“ und „TS fehlt“ als zwei unabhängige Versäumnisse zählen.
Ausgabe unterscheidet vollständig erfüllt, enthaltenes T/TS erfüllt, bestätigte
Ausnahme, Urlaub/inaktiv und nicht erfüllt mit Ursache/erfülltem Teilumfang.
Ein vorgeschlagenes Zielmaß ist die Zahl unbefriedigter berechtigter
Person-Veranstaltungsziele; seine Stellung in der Zielhierarchie ist F13.

Die kombinierten Katalogblöcke erzeugen jeweils nur ihren ausgeschriebenen
operativen Bedarf und die ausdrückliche Teilnahmezuordnung. Sie decken nicht
automatisch weitere, gleichzeitig gesondert verlangte Tätigkeiten ab. Ergibt
ein bestätigtes Profil einen unabhängigen durchgängigen Besetzungsbedarf,
muss auch dessen reale Erfüllbarkeit während Teamzeit/Pausen geprüft werden.

## 5. Zeit und Pausen

Technische Konvention: halboffene Intervalle `[Start, Ende)`, lokale Dienststartdaten,
UTC-Zeitpunkte für Dauer/Ruhe/Überlappung. Nicht erst lokale Zeiten voneinander
abziehen: DST kann den Abstand um eine Stunde ändern. Lokale Zeit, UTC-Offset,
gewähltes `fold` bei einer doppelt vorkommenden Uhrzeit und verwendete
IANA-Zeitzonenfassung werden nachvollziehbar gespeichert.

Nicht existierende Ortszeiten werden nicht automatisch verschoben; doppelte Zeiten
benötigen eine eindeutige Auswahl. Beispiel: WL-Ende 29.03.2026 02:00 existiert
in Wien nicht. Eine abweichende Variante darf nur ausdrücklich bestätigt werden;
die automatische Terminwahl kann diesen Kandidaten vermeiden.

Anwesenheit, tatsächliche Arbeit, Pausen, Arbeitszeitgutschrift und Zulagenmengen
sind getrennte Summen. Ohne besondere Gutschriftregel ist die physische Arbeit
die UTC-Dauer der Arbeitsabschnitte. Etwaige Zeitumstellungs-/Bereitschaftsgutschriften
brauchen ein bestätigtes Profil, keine fiktiven zusätzlichen Arbeitsminuten (F01/F02/F04).

Aus dieser betrieblichen Vorgabe gilt: jeder Block mit tatsächlicher Anwesenheit
über 6 h enthält genau **eine 30-Minuten-Pause**, bei genau 6 h oder weniger keine
automatische Pause. Weitergehende zwingende Schutzvorgaben werden zusätzlich
im Rechtsprofil geprüft. Die Pause liegt vollständig innerhalb des Blocks,
verlängert ihn nicht und wird nur einmal abgezogen. Arbeitsabschnitte sind die
Anwesenheit abzüglich der echten Pause, keine auf ein früheres Ende verkürzte Schicht.

Pausen möglichst vollständig vor 22:00, aber nur nach allen höheren Zielen.
Eine Pause darf weder vollständige erforderliche T-/TS-Teilnahme noch bestätigte
Besetzungs-/Schutzregeln verletzen. Pausenfreiheit und nötige reale Vertretung
werden nach F03 ausdrücklich modelliert. Unbekannte kontinuierliche Besetzung
darf nicht als eingehalten ausgewiesen werden.

W17 17:00–01:00 mit Pause 21:00–21:30: 450 Arbeitsminuten, davon 180 Nachtminuten.
Mit Pause 22:00–22:30: ebenfalls 450, davon 150 Nachtminuten. Kein Nachtbonus für Pause.
BK in der Frühjahrs-Umstellungsnacht 28./29.03.2026: 420 reale Anwesenheitsminuten,
bei 30 min Pause 390 Arbeitsminuten; im Herbst 24./25.10.2026 entsprechend 540/510.
Ob zusätzliche Zeitgutschriften anfallen, wird getrennt durch das Profil bestimmt.

## 6. Verbindliche Schutz-/Kalenderregeln

1. Mindestens **660 tatsächliche Minuten** ununterbrochene Ruhe zwischen Blöcken.
   Eine Pause im Block ist kein vorgezogener Beginn dieser täglichen Ruhe.
2. Maximal **fünf tatsächliche Arbeitstage** hintereinander. Jeder durch Arbeit
   berührte lokale Kalendertag zählt. Für normale Arbeitsblöcke umfasst die
   Tagesbelegung auch eine im Block liegende unbezahlte Randpause; ein berührter
   Tag wird nicht durch deren Lage künstlich frei. Ende exakt 00:00 belegt den
   neuen Tag nicht; Dienstanwesenheit bis 00:01 schon. Belegte Tage und bezahlte
   Arbeitsminuten sind deshalb getrennte Auswertungen.
3. Mindestens **zwei freie Wochenenden** pro Monat, regulär Samstag/Sonntag.
   Monatszuordnung und Teilmonate sind F10; die Zahl zwei ist bestätigt.
4. Vor einem belegten Samstag/Sonntag liegen **zwei vollständig freie,
   aufeinanderfolgende Kalendertage** innerhalb des unmittelbar davorliegenden
   Montag–Freitag. Ein Sonntag bis Montag 01:00 verhindert einen freien Montag,
   ein Donnerstag bis Freitag 01:00 einen freien Freitag. Donnerstag-Teamzeit ist Arbeit.
5. Urlaub ohne Dienst gilt für Freizeit-/Wochenendprüfung als frei. Gutschriften
   sind keine Arbeit und erzeugen keine Anwesenheits-/Arbeitstagsmarkierung.
6. Nur ein **W17 mit Start Freitag und Ende Samstag**, ohne sonstige Arbeit am
   Samstag/Sonntag, darf für die Wochenendzählung als freies Wochenende gelten.
   Diese enge Ausnahme ändert weder Arbeit noch Ruhe noch die Fünf-Tage-Folge.
   Kein Übertrag auf WL, BK, N17 oder nur ähnlich lange Dienste. Der Einfluss auf
   Wochenendwünsche ist F11. Tatsächliche Wochenendbelegung bleibt für das
   vorgeschriebene Vorwochen-Freipaar maßgeblich: die eng begrenzte Zählausnahme
   wird nicht zu einer zusätzlichen Befreiung von dieser Schutzregel erweitert.
7. Urlaub, Beschäftigungsgrenzen, Dienstberechtigungen, ein Block je Startdatum,
   echte Überschneidungsfreiheit und bestätigte feste Vorgaben bleiben verbindlich.
   Feste illegale Zuteilungen werden nicht unter Berufung auf ihre Fixierung erlaubt.
8. W16 braucht eine dokumentierte Begründung, erhält den Außendienstbedarf und
   ist eine Ausnahmealternative. WL/BK-Ausschluss und Wochenquoten gelten nach
   den ausdrücklich festgelegten Randparametern F06/F07.

Tages-/Wochenhöchstzeiten und zusätzliche Schutz-/Durchrechnungsregeln nicht aus
alten Beispielen erben. Anwendbare Rechts-/Betriebsprofile sind F01/F04. Aus den
betrieblichen Regeln allein folgt kein Nachweis vollständiger Rechtskonformität.

Der Planungshorizont umfasst ganze betroffene Wochen und Wochenenden sowie genug
Randtage für Arbeitsfolgen und Ruhe. Bestätigte Vormonate sind feste Tatsachen;
verfügbare Folgemonatsdienste werden einbezogen, Entwürfe als solche ausgewiesen.
Fehlende Randdaten sind **unbekannt**, nicht automatisch frei. Ergänzende Randplanung
wird getrennt gezeigt; nur der gewählte Monat wird übernommen. Quoten-/Randbindung
ausgewählter Dienste muss dabei transaktional mitgeführt werden.

## 7. Urlaub, Freiwünsche und Korrekturvormerkung

Urlaub ist verbindliche Abwesenheit auch für T/TS und auch donnerstags. Er darf
länger als 24 h sein und mehr als vier Tage umfassen. Keine alte P1-Grenze auf
Urlaub übertragen. Ein Abwesenheitsintervall und seine **expliziten anrechenbaren
Gutschrifttage** sind getrennt; Auswahl dieser Tage ist F05. Pro Person/Datum
höchstens eine Urlaubsgutschrift, auch bei Duplikaten/Überlappungen.

Freiwünsche sind weiche Ziele mit einstellbarer Zahl einzelner Tage plus einem
gewünschten freien Wochenende je Person/Monat. Ein Wochenendwunsch ist ein
eigenständiger mehrtägiger Wunsch, bei Verletzung einmal gezählt; kein automatisches
Gewicht zwei. Für Budgetzählung/Verletzung zählen eindeutige Wunschidentitäten,
UI und CSV gemeinsam. Reimport und Monatsgrenzen dürfen Identitäten nicht vervielfachen.
Die genaue Gewichtung und frühere Bevorzugung kleiner Wunschzahlen sind F12/F13.

**Am Donnerstag sind aktive Freiwünsche unzulässig**, auch ein Mittwoch-
Nachtwunsch mit echtem Donnerstagsanteil. Ende Donnerstag exakt 00:00 enthält
keinen Donnerstagsanteil. Urlaub ist davon nicht betroffen.

**Klärung durch die Bedienperson am 09.11.2026:** Solche UI-/CSV-Einträge werden
**zur Korrektur vorgemerkt**. Der ursprüngliche widersprüchliche Ablehnungs-Test
wird entsprechend präzisiert:

- Originalinhalt und betroffene Daten/Zeilen sichtbar erhalten, Status
  „Zur Korrektur vorgemerkt – noch nicht in Planung übernommen“.
- Keine stille Kürzung, Löschung oder Umwandlung in Urlaub; keine automatische
  Donnerstag-Ausnahme. Die Vormerkung ist kein aktiver Freiwunsch.
- Ein eigener, lokal wiederherstellbarer Korrekturentwurf darf gespeichert werden;
  aktive Sperren, Wünsche und bestätigte Monatsstände bleiben unverändert.
- Ein fehlerhafter Import bleibt als kompletter Stapel vorgemerkt; keine teilweise
  Übernahme seiner gültigen Zeilen. Erst nach Korrektur und vollständiger gemeinsamer
  Prüfung erfolgt die atomare Übernahme. Verwerfen entfernt nur die Vormerkung.
- Korrekturdatensätze zählen weder zu Wunschbudget noch Solver, Übergehungsstatistik
  oder bestätigter Historie. Die bestätigten historischen Wünsche werden nicht
  rückwirkend nach dem neuen Donnerstagsverbot verändert.

Alte P1 sind allgemeine verbindliche Sperren ohne belegte Urlaubstage. Sie bleiben
Legacy-Sperren, ohne Urlaubslabel oder Gutschrift. Alt-CSV wird ausdrücklich als
Altformat gelesen; eine Übernahme nach V2 braucht eine nachvollziehbare Typzuordnung.

Technischer Entwurf für das getrennte **CSV-Format 2**, umzusetzen in B2:

```csv
format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar
2;A;urlaub-a-1;urlaub;2026-11-09T00:00+01:00;2026-11-16T00:00+01:00;2026-11-09|2026-11-10|2026-11-11|2026-11-12|2026-11-13;Eine Woche abwesend
2;A;wunsch-a-1;freiwunschtag;2026-11-11T22:00+01:00;2026-11-12T01:00+01:00;;Zur Korrektur vormerken
```

`bis` ist exklusiv; Gutschrifttage sind eine eigene Datumsmenge, nur bei Urlaub.
Typen: `urlaub`, `freiwunschtag`, `wochenendwunsch`; Legacy-Sperren haben einen
gesonderten, ausdrücklich gekennzeichneten Übernahmeweg. UTF-8/BOM und Komma/
Semikolon bleiben unterstützt. Exportierte Personenkennungen müssen zur gewählten
Person/Zuordnung passen. Offsetangaben müssen zu Europe/Vienna passen; bei fehlendem
Offset wird lokale Existenz/Eindeutigkeit geprüft, nicht geraten. Gleiche normalisierte
Person/Typ/Zeiträume werden beim Reimport trotz anderer Kommentare dedupliziert.
Eine vorhandene `entry_id` mit anderem Inhalt ist eine explizit zu prüfende Änderung,
kein stilles Überschreiben; bestätigte Historienbezüge bleiben unverändert.

## 8. Stunden und Salden

Für Monatssoll `S`, Anfang `B`, gewünschtes Ende `E`, bezahlte geplante Arbeit `P`
und zusätzliche anrechenbare Gutschriften `G`:

```text
Arbeitsziel roh = S + E − B − G
Voraussichtlicher Endsaldo = B + P + G − S
Neue Monatsdifferenz einschließlich Gutschriften = P + G − S
Abweichung vom gewünschten Ende = B + P + G − S − E
```

Urlaubstag: am jeweiligen Tag gültiges `W/5` Stunden. 25/30/37 Wochenstunden
ergeben 300/360/444 Minuten. Fünf Tage bei 25 h ergeben 1500 min Gutschrift.
Nicht zugleich `S` vermindern und dieselben Urlaubstage nochmals zu `G` addieren.
Zeitabhängige Verträge und Beschäftigungstage gehen in Soll und Gutschrift ein.

Technische Minutenkonvention: Eingabe-Decimals verlustfrei als Dezimaltext/
rationale Zahlen; physische Zeitpunkte minutengenau; Rohsummen für `S` und `G`
je Person/Monat getrennt exakt aufsummieren und jeweils **einmal** kaufmännisch
auf Minuten runden. Keine einzelne Tagesgutschrift vor der Summierung runden.
Abweichende zwingende Profilrundung ist versioniert auszuweisen.

Die bisherige Regel `W × Kalendertage / 7` ist ein **Legacy-/Testprofil**, nicht
bereits die bestätigte V2-Sollregel. Eine technisch mögliche zeitabhängige
Fortschreibung ist `Σ (W_des_Tages / 7)` über Beschäftigungstage. Ihre rechtliche
Zulässigkeit, Feiertagseffekte, Durchrechnung und Monatszuordnung von Arbeit/
Gutschrift bleiben F04. Physische Arbeits-/Zulagenmengen werden unabhängig davon
stets an lokalen Kalender-/Monats-/Jahresgrenzen segmentiert.

Bei negativem rohem Arbeitsziel keine negativen Dienste erzeugen: null Arbeit
als untere Grenze, rechnerische Überdeckung und unvermeidliche Zielabweichung
anzeigen. Der Rohwert darf nicht durch unbemerktes Ändern von `B`, `E`, `S`, `G`
oder Erfinden von Arbeit verschwinden. Ein erforderlicher operativer Dienst kann
auch bei negativem Rohziel nur innerhalb aller harten Regeln zugeteilt werden.

Vorab belastbare Grenzen statt einer scheinexakten Bedarfssumme: fester operativer
Bedarf, minimale/maximale Zusatz-/Teilnahme-/Reserveanteile und zulässige Kapazität
gesondert. Nachher tatsächliche Summen des gewählten Plans zeigen. T/TS-Zahl,
WL/BK-Tage, Varianten und Reservebewertung können den Bedarf beeinflussen.
Keine unbestellten Dienste oder zusätzlichen T-Einträge zum Füllen der Stunden.

## 9. Kalender, Nacht und Zulagen

Bestätigt sind Europe/Vienna, Nachtfenster **22:00–06:00**, bundesweite gesetzliche
Feiertage Österreichs einschließlich beweglicher Feiertage und ein zeitlich gültiges
Caritas-/VkA-Profil für Kältetelefon Wien mit belegten Betriebsvereinbarungen.

Kalender-Sollkatalog: 01.01., 06.01., Ostermontag, 01.05., Christi Himmelfahrt,
Pfingstmontag, Fronleichnam, 15.08., 26.10., 01.11., 08.12., 25.12., 26.12.
24.12./31.12. sind nicht allein wegen R gesetzliche Feiertage. Landes-/KV-/Betriebs-
Sondertage erhalten eigene Kategorien statt den nationalen Kalender zu verfälschen.
Die externe Primärquellenprüfung dieses Kalenders steht wegen des Zugriffsblocks aus.

Nur tatsächliche Arbeit trägt Nacht-/Sonntags-/Feiertagsminuten; Pause trägt null.
Kategorien dürfen sich bei derselben Arbeitsminute überschneiden und werden getrennt
ausgegeben, ohne physische Arbeitszeit doppelt zu zählen. Ob Eurozuschläge kumulieren,
einander ersetzen oder eine besondere Basis haben, bestimmt das belegte Profil.
Reservekomponenten bleiben separat; keine Geldbewertung allein aus dem Kürzel R.

| Primärquelle / Fundstelle | Verwendungszweck | Tatsächlicher Prüfstand am 09.11.2026 |
| --- | --- | --- |
| [VkA-Downloads](https://vka.or.at/download/) | Gültige Fassungen und Wirksamkeitsdaten ermitteln | Proxy `CONNECT 403`; Inhalt nicht gelesen |
| [VkA KV 2026](https://vka.or.at/fileadmin/storage/global/vka-wien/VkA_KV_2026.pdf) | Insbesondere vom Auftrag benannte E.4 und C.8/E.6, Dienstform/Reserve und nötige BV prüfen | Nicht geladen; keine Aussage zu deren konkretem Wortlaut oder Beträgen |
| [Betriebsrat Caritas Wien](https://www.betriebsrat-caritas-wien.at/kollektivvertraege/) | Zuordnung und weitere Fassungen/BV abgleichen | Proxy `CONNECT 403`; nicht verifiziert |
| [USP – Ruhezeiten](https://www.usp.gv.at/themen/mitarbeiter-und-gesundheit/urlaub-und-arbeitszeit/ruhezeiten.html) | Österreichischen Feiertags-/Ruhekalender anhand Primärquelle belegen | Proxy `CONNECT 403`; nicht verifiziert |

Jede später bestätigte Profilversion braucht Quelle, Fundstelle/Seite/Absatz,
Dokumenthash, Abruf-/Prüfdatum, Wirksamkeitsintervall und konkrete betriebliche/
personenbezogene Anwendbarkeit. „Außendienst“ belegt keinen KV-Tatbestand.
KV 2026 ist ohne neue Prüfung kein bestätigter Tarif für 2027 oder jeden anderen Monat.
Fehlt Zuordnung/Fassung/Bemessungsgrundlage/Kumulationsregel, Zeitmengen zeigen und
Euro als **ungeklärt** ausweisen, nicht als 0 oder als verbindliche Prognose.
Stunden-/Ruhe-/Reserveprüfungen mit fehlendem Pflichtprofil bleiben ebenfalls offen.

## 10. Optimierung, Nachweis und Ausgabe

Harte Regeln stehen stets außerhalb einer handelbaren Zielfunktion. Innerhalb
gültiger Ergebnisse ist folgender **Arbeitsvorschlag, noch F13**, vorgesehen:

1. Offene verbindliche operative Plätze minimieren.
2. Unerfüllte T-/TS-Teilnahmeziele minimieren, bestätigte Ausnahmen berücksichtigen.
3. Wunschübergehungen minimieren, dann historisch ausgleichen (F11/F12).
4. Vermeidbare WL/BK-Sonn-/Feiertagstermine und nötige W16-Ausnahmen reduzieren.
5. Größte verbleibende Stundenabweichung, dann Saldenstreuung minimieren.
6. Historische Nacht-/Feiertags-/Reservegerechtigkeit und weitere Dienstverteilung.
7. Änderungen gegenüber geprüftem Entwurf reduzieren.
8. Sonst gleichwertige Pausen vollständig vor 22:00 bevorzugen.

Die bisherige gewichtete gemeinsame Stunden-/Schichtquadratsumme nicht unverändert
auf die neuen Ziele oder Eurobeträge ausdehnen. Stunden- und Zulagenfairness brauchen getrennte, verständliche Maße,
Berechtigungs-/Beschäftigungsbezug, Zeitraum und ggf. bestätigte Toleranzen (F12/F13).
Unbesetzte Stellen dürfen Fairnessnenner nicht künstlich verbessern.
V2-Gruppenbevorzugung bei wenigen Wünschen ist noch unentschieden.

Vorhandener gültiger Plan bleibt unter **derselben** Eingabe-/Regel-/Profilversion
Startpunkt und Rückfall; nur bessere bzw. erlaubte gleichwertige Ergebnisse
übernehmen. Wählbares Zeitlimit, Hintergrundrechnung, Abbruch und beste gültige
Zwischenstände erhalten. Einzelwechsel, Tausche und größere Umverteilungen werden
einschließlich Pausen und Randdaten vollständig nachbewertet und unabhängig geprüft.

Ergebnis unterscheidet gültig/optimal, gültig ohne vollständigen Nachweis,
unvollständigen diagnostischen Teilplan, Zeitlimit ohne Fund und bewiesene Unlösbarkeit.
Ein Teilplan verletzt keine Schutzregel, hat aber ausdrücklich offene operative Plätze.
Fehlende Rand-/Rechtsprofile ergeben zusätzlich „Prüfung unvollständig“, keinen
gültigen Gesamtnachweis. Nachweise je Stufe nennen Voraussetzungen; später bedingte
Optima bei unbewiesenen früheren Zielen sind kein globales Optimum.

Ein Prüfbericht hält Eingaberevision, Katalog-/Profilversionen, Pausen, Quoten,
Ausnahmen, Randdatenabdeckung, bestätigte Historie, Soll-/Gutschriftrechnungen,
Zielwerte, Abbruchgrund und Nachweise zusammen mit derselben Planversion fest.
Alle CSVs/Tabellen müssen genau zu dieser Version passen. Manuelle Fixierungen
durchlaufen dieselbe unabhängige Ergebnisprüfung wie automatische Zuteilungen.

## Ergänzung Nutzerauftrag 10.11.2026: ausdrückliche Ausnahmen

Der Nutzer darf fachliche Planungsregeln bei manuellen Änderungen und Importen
nach sichtbarer Warnung ausdrücklich übergehen (einschließlich Donnerstag,
Berechtigung, Urlaub, Fixierungen, Ruhe, Wochenquoten und BK/WL-Ausschluss).
Das ersetzt für diese beiden Übernahmewege die bisher zwingende Ablehnung.
Prüfer und automatische Planung behalten ihre Regeln; Abweichungen bleiben
Abweichungen. Keine Freigabe einer Rechts-/Tarifkonformität. Technisch undefinierte
Daten können weiter nicht aktiv übernommen werden. Bedienung und Abgrenzung:
`TABELLENIMPORT.md`, Abschnitt „Ausdrückliche Regelübersteuerung“.
