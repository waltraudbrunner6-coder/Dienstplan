# V2 – Konkreter Abnahmetestkatalog

Aktueller Implementierungs- und Prüfstand: [Fortschritt](V2_FORTSCHRITT.md),
[Zuordnung aller 125 Abnahmefälle](V2_ABNAHMESTATUS.md) und
[Bedienung der Desktop-Anwendung](V2_BEDIENUNG.md). Die nachfolgende
Etappe-A-Spezifikation gilt mit den datierten Nutzerergänzungen; alte Testprofile ersetzen diese Antworten nicht.

Stand 09.11.2026. **Geplante Abnahme für die Folgeimplementierung**, keine Behauptung,
diese Tests seien bereits implementiert oder bestanden. Die damals ausgeführten
158 Legacy-Tests sind als historischer Ausgangsbericht getrennt in [Bestandsaufnahme](V2_BESTANDSAUFNAHME.md) belegt.
Regeln: [Fachregeln](V2_FACHREGELN.md); offene Profile: [Fragen](V2_OFFENE_FRAGEN.md).

## Verbindliche Überlagerung: Nutzerantworten vom 11.11.2026 / Version 0.5.0

Die nachstehenden 125 IDs bleiben erhalten. Ihre nun aktualisierten Erwartungen
richten sich nach den ausdrücklich beantworteten Fachfragen; die unveränderten
Etappe-A-Beispiele sind kein Grund, die neuen Antworten wieder als offen zu behandeln.
Dies ist ein **Abnahmekatalog**, keine Erklärung, alle Fälle seien implementiert
oder bestanden. Ausgeführte Befehle, aktuelle Testzahlen und native Nachweise
stehen ausschließlich im [Fortschritt](V2_FORTSCHRITT.md).

- **Urlaub:** Jedes neu ausdrücklich als Urlaub markierte U-Datum zählt, auch am
  Wochenende oder Feiertag, genau einmal mit dem an diesem Tag gültigen W/5.
  Neue Urlaubszeiträume wählen die enthaltenen Kalendertage entsprechend sichtbar
  aus. Alte, bereits explizit gespeicherte Tages-Teilmengen bleiben unverändert
  lesbar: U01 und I01 sind bewusst **Legacy-/Kompatibilitätsfälle**, keine neue
  Aufforderung, Wochenenden bei Urlaub wegzulassen. U05 prüft die neue Eingabe.
- **Urlaubsanspruch:** Zwei Tage je vollem Beschäftigungsmonat werden angespart;
  Anfangsbestand und Kontostart werden ausdrücklich erfasst. Bei Teilmonaten gilt
  exakt `2 × beschäftigte Kalendertage / Kalendertage des Monats`, ohne vorzeitige
  Tagesrundung. Fehlende frühere Verbrauchsmonate bleiben als unbekannt gekennzeichnet.
  Negativer Urlaubsrest ist eine nachvollziehbare Prognose, kein neues Hartlimit.
- **Pausen:** Gleichzeitige Pausen sind ausdrücklich erlaubt. Strengere
  `CoverageRule`-Tests bleiben als technisch ausdrücklich gewählte Zusatzprofile
  sinnvoll, dürfen aber nicht als betrieblicher Standard ausgegeben werden.
- **Dienste:** R zählt wie normale Arbeit; KC15 ersetzt bei erforderlichem Ersatz
  gemeinsam KC10 und KC16 durch einen Dienst 15:00–00:00 mit einer Person und
  30 Minuten Pause. Reguläre vollständige Besetzung wird bevorzugt. LB beginnt
  am 03.12.2026, danach alle 14 Tage mit zwei ausdrücklich gewählten festen Personen.
  FK ist ein Einzeltermin ohne automatische Wiederholung. Für den 31.12. ist KCT10 bis 17:30 bestätigt. WL/BK bleiben ganzjährig 2/1 je Woche.
- **Kalender/Buchung:** Freie Wochenenden gehören zum Monat ihres Sonntags.
  Die enge Freitags-W17-Ausnahme gilt auch für Wochenend-Freiwünsche; ein sonst
  freies Samstag/Sonntag-Wochenende wird durch diesen W17 nicht als Wunschverletzung gezählt.
  M1 bucht die gesamte bezahlte Arbeit im Monat des Dienstbeginns; physische
  Tages-/Nacht-/Feiertagsmengen bleiben tatsächlich segmentiert. M0 bleibt für
  alte bestätigte Stände und bewusst benannte Vergleichstests unverändert erhalten.
- **Übersteuerung:** Eine Meldung „unzulässig“ bezeichnet die unabhängige Prüfung
  und den automatischen Solver. Sie verbietet nicht die bereits genehmigte
  manuelle/Import-Übernahme bzw. Monatsbestätigung nach ausdrücklicher Warnung.
  Technische Identitätsfehler und unveränderliche bestätigte Fakten bleiben geschützt.

## Gemeinsame Testkonvention

- Zwölf fiktive Personen A–L, standardmäßig 25 Wochenstunden, B=E=0, alle im
  gesamten Testzeitraum beschäftigt und für den jeweils geprüften Dienst berechtigt.
  Für N17 ist standardmäßig ein Führerschein vorhanden. Abweichungen werden pro
  Fall genannt; eine zusätzliche Person X bezeichnet das
  befristete Außendienstprofil. Kein Zugriff auf eine echte Benutzerdatenbank.
- Lokale Angaben Europe/Vienna, Sekunden null, Intervalle `[Start, Ende)`;
  `+1` ist der Folgetag. Bei Bedarf verbindlich bekannte leere Randtage als
  Testdaten liefern, nicht durch fehlende Datensätze ersetzen.
- November 2026: Donnerstag 05./12./19./26.; Fr/Sa/So 13./14./15.; unmittelbar
  vorherige Mo–Fr-Tage 09.–13.11. Ein Nicht-DST-Tag ist der Normalfall.
- Katalogtests prüfen Erzeugung/Bedarf; Regeltests prüfen die genannte Regel direkt.
  Ein Teilbeispiel mit nur zwei Zuteilungen behauptet keinen vollständig besetzten
  operativen Monatsplan. Integration prüft anschließend alle harten Regeln gemeinsam.
- Pausen liegen in den ausdrücklich angegebenen zulässigen Fenstern; ohne weitere
  Angabe Testprofil mit frei wählbarer 30-Minuten-Pause innerhalb des Blocks und
  außerhalb verpflichtender Teamzeit. Gleichzeitige Pausen sind erlaubt; eine zusätzliche
  durchgehende Mindestabdeckung wird nur unter ausdrücklich ausgewähltem Zusatzprofil geprüft.
- Für bedingte Fälle wird das Profil explizit angegeben. Testprofil **S0**:
  Soll `Σ(W_d × 60/7)` über eingeschlossene Beschäftigungstage, pro Person/Monat
  einmal `ROUND_HALF_UP`; Gutschrift getrennt ebenso. Für Monatsschnitte gilt im
  Legacy-/Vergleichsprofil **M0** der tatsächliche lokale Arbeitsmonat. Der neue
  bestätigte Standard **M1** bucht dagegen den ganzen Dienst im Startmonat.
  S0 entspricht der bereits bestätigten Kalendertage-Sollregel; keine Tarifregel daraus ableiten.
- Einzelergebnis enthält Regel-ID/Person/Termin, konkrete Werte und verständliche
  Ursache. „Zulässig“ für eine Einzelregel ersetzt keinen Gesamtnachweis bei
  unbekannten Randdaten oder fehlendem Rechts-/Reserveprofil.

## D – Dienstkatalog und gemeinsame Teilnahme

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| D01 | KC10, KC16, W17 am Mi 11.11.2026; zusätzlich zulässiger KC15-Ersatzfall bei fehlender regulärer Besetzung | Regulär je ein Termin, Plätze 1/1/2, Arbeit 360/450/450 min je Person: 1710 min und 4 Plätze. Bei KC15-Ersatz entfallen KC10 und KC16 gemeinsam: KC15 15:00–00:00, eine Person, 510 bezahlte min; W17 bleibt unverändert. Dann 1410 min und 3 Plätze. Ersatz und geänderter Bedarf sind sichtbar; kein leerer Ersatz zum Verbergen offener Plätze. |
| D02 | Regulärer Do 12.11., keine TS/LB/R-Zusätze | KCT10=1 Platz/405 min, KCT=1/540, TW=2/je 540; keine zusätzlichen KC10/KC16/W17. Operativer Bedarf 2025 min, 4 Plätze. |
| D03 | D02: A KCT10, B KCT, C/D TW, E–L T; vollständige zulässige Pausen außerhalb T | Alle 12 erfüllen T genau einmal. Nur acht eigenständige T-Zuteilungen. Gesamte Arbeit 3465 min, enthaltene T-Zeit nicht nochmals addieren. |
| D04 | Do 12.11. als TS-Tag; A KCT10, B KCT, C/D TW, E–L TS | Eine TS-Veranstaltung statt T. A–D erfüllen T und sind vom zusätzlichen TS-Ziel ausgenommen. E–L erfüllen TS. Keine vier falschen T-Fehlmeldungen, keine zusätzlichen T-Blöcke. |
| D05 | Manuell vorgegebener LB am regulären Do 12.11. für E/F (Legacy-Einzelfunktionsfall, kein neuer Rhythmusanker) | Zwei Plätze, je 12:00–17:30, 330 min Arbeit, kein automatischer Pausenabzug; beide erfüllen T ohne zweite T-Zuteilung. Automatische Rhythmustermine beginnen erst 03.12.2026, siehe Q09. |
| D06 | Manuell vorgegebener LB E/F am TS-Do 12.11.; Pause 13:00–13:30 (Legacy-Einzelfunktionsfall) | Je ein Block 12:00–19:30, 450 min Anwesenheit, 420 Arbeit, genau eine Pause; volle TS und T enthalten, keine zusätzlichen T/TS-Stunden. Dieser technische Kombiblocktest setzt keinen November-Rhythmusanker. |
| D07 | BK bis Do 12.11. 04:00, T 14:30 für dieselbe Person angefragt | Kein unzulässiger zusätzlicher T-Block. 630 min Abstand erklären; BK-Ausnahme/zulässiges Auslassen zeigen, nicht „verbindliche Teamsitzung verletzt“. |
| D08 | Zwei verschiedene operative Aufgaben mit zufällig gleicher/überlappender Zeit, kein freigegebener gemeinsamer Block | Doppelzuteilung bleibt unzulässig; Intervallvereinigung darf den Konflikt nicht kaschieren. |
| D09 | TS-Tag, teilnahmeberechtigte Person ohne erfüllenden Block/Teilnahme; keine Ausnahme | Ein unerfülltes Person-Veranstaltungsziel, nicht zwei unabhängige Strafen für T und TS. Erfüllter Umfang 0. |
| D10 | Eigenständiges T plus KCT10 derselben Person am 12.11. manuell eingetragen | Als Doppel-/Ein-Block-Konflikt zurückweisen, nicht als 585 Arbeitsminuten buchen. Korrekte KCT10-Zuteilung allein 405 min. |
| D11 | VN am 11.11. und 18.11., jeweils Person G; INT am 10./24.11. für H/I, N17 am 20.11. für J | Je 1 Platz; VN je 120, INT/N17 je 450 min Arbeit; Termine und Personen bleiben fest, keine automatische Ersatzperson/-verschiebung. |
| D12 | FK einmalig am 21.11. für K, 09:00–16:00, Pause 12:00–12:30; bestätigter Einzeltermin | Ein fester Platz, 420 min Anwesenheit/390 Arbeit. Keine automatische monatliche oder jährliche Wiederholung/Kopie; F09 ist hierfür beantwortet. |

## P – Personen, Verträge und Berechtigungen

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| P01 | A ohne Führerschein, N17 am 20.11. | A ist kein Kandidat; manuelle Fixierung wird vor Übernahme beanstandet. |
| P02 | Derselbe fehlende Führerschein, explizite Rechte für W17/WL/BK | Nicht allein wegen Führerschein ausschließen; keine erfundene Führerscheinregel außerhalb N17. |
| P03 | X vom 01.11.–31.12. beschäftigt, Außendienstprofil, Führerschein vorhanden | Nur W17/W16/BK/WL/N17/TW operativ sowie T/TS erlaubt; KC10/KCT10/KC16/KC15/KCT/LB/VN/INT/FK/R nicht aus dem Profil ableiten. |
| P04 | X am Do 12.11. ohne operativen Block, kein Urlaub, Ruhe erfüllt | X ist für T bzw. TS auf TS-Tag teilnahmeberechtigt und im weichen Ziel enthalten. |
| P05 | X Beschäftigung bis 31.12.; N17 31.12. 17:00–01.01. 01:00 | Unzulässig: Ende außerhalb Beschäftigung, obwohl Startdatum darin liegt. |
| P06 | Gleiches Ende; erlaubter Block endet exakt 01.01.2027 00:00 | Beschäftigungsgrenze eingehalten; Start außerhalb am 01.01. wäre unzulässig. |
| P07 | Vertrag A: 25 h bis 15.11., 30 h ab 16.11.; zwei überlappende Vertragsfassungen eingeben | Eindeutiger Wechsel erlaubt, Überlappung/Lücke im benötigten Vertragszeitraum erkennbar; kein zufälliger Auswahlgewinner. |
| P08 | A darf nur Innendienst, B nur Außendienst; Fairness des Außendienstpools | A bekommt keinen Außendienst-Sollanteil und wird nicht als unfair übergangen gezählt; B erhält keinen Innendienst-Sollanteil. |

## R – Ruhe, Startdatum, tatsächliche Tage und Wochenenden

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| R01 | A VN Di 10.11. 10:00–12:00 und KC16 desselben Startdatums 16:00–00:00 | Unzulässig nach Ein-Block-Regel, selbst bei nicht überlappenden Zeiten. |
| R02 | A W17 Mo 09.11. 17:00–Di 01:00 und Di 10.11. 17:00–Mi 01:00 | Startdaten verschieden, 960 min Ruhe; Ruhe/Startdatumsregel erfüllt. Arbeitstage Mo/Di/Mi, nicht nur zwei. |
| R03 | A KC16 Di 10.11. bis Mi 00:00, KC10 Mi 11.11. ab 10:15 | 615 statt 660 min Ruhe: unzulässig, es fehlen 45 min. |
| R04 | Voriger Block endet Mi 00:00; FK Mi ab 11:00 bzw. 10:59 | Exakt 660 min besteht; 659 min wird abgelehnt. |
| R05 | Fünf tägliche kurze Blöcke Mo 09.–Fr 13.11.; zusätzlich Sa 14.11. | Fünferfolge besteht; sechster Tag verletzt die Fünf-Tage-Regel. Einzelregel isoliert prüfen; weitere Wochenendkonflikte getrennt berichten. |
| R06 | Kurze Blöcke 28.12.2026–01.01.2027 sowie 02.01. | Fünf Tage über Jahres-/Monatsgrenze erlaubt, sechster nicht; kein Reset am 01.01. |
| R07 | Ein Block Fr 13.11. endet Sa exakt 00:00, Vergleich Ende Sa 00:01 | Im ersten Fall Samstag nicht berührt, im zweiten belegt. Pause/Gutschrift ändern diese Endgrenze nicht fiktiv. |
| R08 | FK Fr 18:00–Sa 00:30, Pause Sa 00:00–00:30 | Samstag hat 0 Arbeitsminuten, ist wegen Dienstanwesenheit/Randpause trotzdem nicht künstlich vollständig frei; keine W17-Ausnahme für FK. |
| R09 | Arbeit Sa 14.11.; Mo 09./Di 10.11. ausdrücklich vollständig frei | Vorwochenpaarregel erfüllt; Paar liegt im direkt davorliegenden Mo–Fr. |
| R10 | Arbeit Sa 14.11.; nur Mo und Mi davor frei, Di/Do/Fr belegt | Unzulässig: zwei einzelne freie Tage sind kein zusammenhängendes Paar. |
| R11 | So 08.11. W17 bis Mo 09.11. 01:00; Di 10.11. frei, übriges Mo–Fr belegt; Sa 14.11. Arbeit | Montag ist kein ganzer freier Tag, Mo/Di kein gültiges Freipaar. |
| R12 | Geplantes Do/Fr-Freipaar vor 14./15.11.; T am Do 12.11. oder Nachtdienst Do→Fr 01:00 | Paar ungültig: T belegt Donnerstag; im Vergleich belegt der Nachtdienst Freitag. |
| R13 | Urlaub Mo 09./Di 10.11., keine Dienste, je 5 h Gutschrift; Sa 14.11. Arbeit | Mo/Di bilden ein Freipaar; Gutschrift erzeugt keine Arbeits-/Anwesenheitstage. |
| R14 | Nur W17 Fr 13.11. 17:00–Sa 01:00, sonst Sa/So keine Arbeit; Mo/Di vorher frei | Wochenende darf für Schutzquote als frei zählen; Samstag bleibt tatsächlicher belegter Tag für Folgen/Ruhe/Vorwochenpaar. |
| R15 | R14 mit WL, BK oder N17 anstelle W17, alternativ zusätzlicher Sa-Dienst | Keine W17-Zählausnahme; Wochenende belegt. Nicht das gleiche Zeitmuster als Berechtigung verwenden. |
| R16 | Voller November 2026 mit bekannten Randtagen; genau zwei der fünf sonntagszugeordneten Wochenenden frei, Vergleich nur eines frei | Zwei erfüllen die Schutzquote, eines verletzt sie. 31.10./01.11. zählt wegen des Sonntags zum November. Unbekannte Randtage dürfen nicht als nachgewiesen frei gelten; Teilmonatsquote bleibt gesondert ungeklärt. |
| R17 | R14, aber in Mo–Fr vorher kein zusammenhängendes Freipaar; zusätzlich Randtag unbekannt | W17-Zählausnahme hebt die Vorwochen-Schutzregel nicht auf. Bei fehlenden nötigen Randdaten außerdem „Prüfung unvollständig“, kein Nachweis durch leere Zukunft. |

## Q – Quoten, Termine und Jahreswechsel

Die folgenden Standardbeispiele benutzen die ausdrücklich gewählte ISO-Woche
Mo–So mit gemeinsamer Wochen-ID über Monatspläne und ganzjährig zwei WL plus
einem BK. Ob gemeinsame Randwochen oder nur volle Monatswochen geplant werden,
bleibt die konkrete gespeicherte Profilwahl. Frühere saisonale Q0-Beispiele bleiben
als benannte parametrische Legacy-Regressionen erhalten, sind aber kein neuer Standard.

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| Q01 | Vollständige Woche 09.–15.11., WL/BK automatisch, alle nötigen Personen verfügbar | Genau zwei WL an unterschiedlichen Daten und ein BK mit jeweils zwei unterschiedlichen Personen; Solver wählt Daten und Personal gekoppelt, ohne vorgegebene Person. |
| Q02 | Vollständige ISO-Woche 07.–13.12.2026, ausreichend zulässige Daten | Zwei WL an zwei verschiedenen Startdaten und ein BK, jeweils zwei Personen; nicht vier WL-Personenplätze an einem einzigen Termin bündeln. |
| Q03 | Gemeinsame ISO-Randwoche 30.11.–06.12.2026 aus November und Dezember nacheinander geöffnet | Genau eine gemeinsame Quote von zwei WL und einem BK; keine zweite Monatsquote und kein Saisonwechsel innerhalb der Woche. Profilwahl und tatsächlich übernommene Randtermine sichtbar halten. |
| Q04 | Woche 25.–31.01.2027 und Woche 01.–07.02.2027 | In beiden Wochen zwei WL und ein BK; ganzjährig dieselbe Anzahl, kein saisonaler Wechsel zum Februar. Kein Quoten-Reset mitten in derselben Woche. |
| Q05 | WL auf 10.11. fixiert, Personal nicht fixiert; A/B dort nicht verfügbar, C/D geeignet | WL bleibt am 10.11.; C/D dürfen gewählt werden. Nicht das Datum verschieben und nicht A/B aus der Datumsfixierung ableiten. |
| Q06 | WL nur auf 10.11. zugelassen; zusätzliche bestätigte Fixierungen schließen dort alle Plätze aus | Termin bleibt fest und bekommt offene Plätze bzw. konkreten Vorgabenkonflikt; keine stille Verschiebung. Harte Personenkonflikte nicht zugunsten Besetzung verletzen. |
| Q07 | WL und BK beide gleicher Starttag 13.11., normale Zeiten | Verbindlicher Ausschluss im Standardprofil verletzt, unabhängig von zufällig getrennten Zeitintervallen. Automatischer Solver wählt keinen solchen Plan; ausdrückliche manuelle Übersteuerung bleibt als Abweichung sichtbar. |
| Q08 | Zwei gleichwertig besetzbare WL-Tage: Di 17.11. und So 22.11.; gleiche höheren Ziele | Dienstag bevorzugen. Wenn nur Sonntag regelgültig möglich ist, Sonntag zulassen und Präferenzabweichung erklären. |
| Q09 | Bestätigter LB-Anker 03.12.2026; Kalender November/Dezember 2026/Jänner 2027, zwei feste Personen | November ohne automatische LB-Termine; Dezember 03./17./31., Jänner 14./28. Ein TS-Termin verlängert nur seinen LB, kein Rhythmusreset. Fehlende Termine gemeinsam ergänzen, bestehende LB-Termine/Personen/Zuteilungen unverändert lassen; ohne gewählte Personen nichts erfinden. |
| Q10 | Reserveperiode 24.12.2026–06.01.2027; R als bestätigte normale Arbeit | 14 Startdaten × zwei Zeitfenster = 28 Einpersonentermine; 31.12./01.01. eingeschlossen, 23.12./07.01. nicht. Früh 360, spät nach 30-min-Pause 450 Arbeitsminuten; insgesamt 11340 min/189 h. Dieselbe Person darf automatisch nicht beide Fenster eines Tages übernehmen. M1 bucht je Dienst vollständig im Startmonat. |
| Q11 | INT-Daten nur einer statt zwei oder N17-Datum/Person fehlt | Konkrete fehlende Monatseingabe nennen; keinen zweiten Termin/keine Person erfinden. Fester VN/FK-Konflikt wird ebenso ausgewiesen. |

## U – Urlaub und anrechenbare Tage

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| U01 | Legacy-Urlaub 09.–15.11. mit bereits explizit gespeicherten Gutschrifttagen 09.–13.11., W=25 | Kompatibilität: ganzer gespeicherter Abwesenheitszeitraum bleibt erhalten, bestehende fünf explizite Gutschrifttage bleiben 1500 min und werden nicht rückwirkend auf sieben/2100 min umgeschrieben. Neue U-Eingaben richten sich nach U05. Mehr als vier Urlaubstage bleiben zulässig. |
| U02 | Urlaub Do 12.11., Gutschrifttag ausdrücklich erfasst | Urlaub erlaubt, keine T-/TS-Zuteilung; Urlaub wird nicht wegen Donnerstagsverbot für Wünsche verworfen. |
| U03 | Derselbe Urlaub zweimal mit anderen Kommentaren, dazu überlappender Urlaubsdatensatz | Person/Datum nur einmal gutschreiben. Abwesenheitsvereinigung nachvollziehbar, keine doppelte Gutschrift/kein doppelter Bedarf. |
| U04 | Fünf Urlaubstage, zwei mit W=37 und drei nach Wechsel mit W=30 | G = 2×444 + 3×360 = 1968 min. Nicht den neuesten Vertrag rückwirkend für alle Tage anwenden. |
| U05 | Neue ausdrücklich als U/Urlaub markierte Kalendertage 24.–27.12.2026 einschließlich Feiertagen/Wochenende; W=25 | Jedes der vier markierten Daten zählt einmal: vier Urlaubstage und 4×300=1200 Gutschriftminuten. Neue Datumseingabe/Import übernimmt die sichtbaren U-Tage; kein ungeklärter Feiertags-/Wochenendfilter und keine Nullgutschrift. Alte Datensätze ohne Tagesmenge werden verständlich vervollständigt, bestehende explizite Teilmengen aus U01 nicht umgedeutet. |
| U06 | Urlaubsgutschrift auf Datum außerhalb der Beschäftigung oder außerhalb des Urlaubs | Als ungültigen Gutschriftbezug melden, keine Stunden erzeugen. Vertrags-/Beschäftigungsbeginn nicht zur Füllung des Saldos verschieben. |
| U07 | Urlaub und manuell fixierter operativer Dienst mit echter Überschneidung | Konflikt klar benennen; automatische Planung respektiert die Sperre. Manuelle Änderung/Import und Monatsbestätigung dürfen nach ausdrücklicher Warnung übersteuert werden; Konflikt und unveränderlicher Bestätigungsstand bleiben dokumentiert. |

## W – Wünsche und die bestätigte Korrekturvormerkung

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| W01 | Monatsbudget 2 Einzeltage + 1 Wochenendwunsch; 02./03.11. plus Wochenende 14./15.11.; zusätzlich 04.11. | Erste drei Wünsche passen ins Budget; 04.11. als dritter eindeutiger Einzeltag überschreitet es. Keine alte Vier-P1-Grenze verwenden. |
| W02 | Derselbe gültige Einzeltagswunsch in UI und CSV, Kommentar verschieden | Eine aktive Wunschidentität, Budgetverbrauch 1, keine zweite Historienbelastung. |
| W03 | Wochenendwunsch 14./15.11.; zwei verletzende Dienste für dieselbe Person | Genau ein übergangener Wochenendwunsch; Gewicht nach F13, nicht automatisch zwei Tage/Übergehungen. |
| W04 | Neuer ganztägiger Do-Wunsch 12.11. in UI | Zur Korrektur vormerken, Originaldatum/Fehler sichtbar, nicht still verwerfen. Kein aktiver Wunsch, kein Budgetverbrauch, keine Zuteilungssperre oder Historienwirkung. |
| W05 | CSV mit gültigem Mo-Wunsch und Mi 11.11. 22:00–Do 12.11. 01:00 | Ganzer Stapel zur Korrektur; Donnerstagsanteil/Zeilennummer nennen. Keine teilweise aktive Übernahme des Mo-Eintrags. Bestehende Daten unverändert. |
| W06 | Vergleich Mi 11.11. 22:00–Do 12.11. 00:00 | Kein echter Donnerstagsanteil, insofern gültig; sonstige Budget-/Duplikat-/Beschäftigungsregeln weiterhin prüfen. |
| W07 | W05: Problemzeile auf gültigen Mittwoch-Zeitraum korrigieren, dann gesamte Vorschau übernehmen | Gesamten Stapel gegen vorhandene UI-/CSV-Daten erneut prüfen und atomar aktivieren; Korrekturvormerkung erledigt, keine Teilimporte zurücklassen. |
| W08 | Offene Vormerkung speichern, Anwendung schließen/öffnen, dann verwerfen | Original/Zeilenfehler wiederherstellbar, aktive Planung unverändert; Verwerfen entfernt nur die Vormerkung. Bestätigte Vergangenheit bleibt unberührt. |
| W09 | Bestätigter Legacy-Donnerstagswunsch; neuer V2-Importregelstand | Historischer Snapshot/Übergehungen unverändert; nicht nachträglich herausfiltern oder umtypisieren. Neue Einträge folgen Korrekturverfahren. |
| W10 | Wochenendwunsch 14./15.11., nur Freitags-W17 bis Sa 01:00, sonst Samstag/Sonntag ohne Dienst | Im neuen bestätigten Standard ist der Wochenendwunsch erfüllt: die enge Freitags-W17-Ausnahme gilt auch für diesen Wunsch. Eine andere Dienstart oder zusätzlicher Samstag-/Sonntagdienst erfüllt die Ausnahme nicht. Alte ausdrücklich strengere Wunschprofile bleiben als Legacy-Vergleich lesbar, werden aber nicht als neuer Standard eingesetzt. |

## I – Importtypen und Atomarität

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| I01 | Legacy-Zeile mit ausdrücklich gespeicherter Teilmenge im CSV-Format 2; W=25; UTF-8/BOM, Semikolon oder dieselben Felder komma-getrennt | Kompatibilität: normalisierte Abwesenheit 09.–15.11. und die fünf expliziten Gutschrifttage bleiben 1500 min. Kein 24-h-/Vier-P1-Limit. Davon getrennt zählt jeder neu importierte markierte U-Tag gemäß U05, auch Wochenende/Feiertag. |
| I02 | Typ unbekannt, ungültiges Datum, nur eine Uhrzeit, widersprüchlicher Zeitraum in verschiedenen Zeilen | Alle lesbaren Fehler mit Zeilennummern, vollständige Korrekturvormerkung, aktive Daten unverändert. |
| I03 | Altes `datum;von;bis;prioritaet;kommentar`, P1 an fünf verschiedenen Tagen | Als Altformat erkennen; bestehende Legacy-Validierung erklären. P1 keinesfalls automatisch zu Urlaub machen, um die alte Grenze zu umgehen. Explizite V2-Typzuordnung/Korrektur nötig. |
| I04 | Gleicher mehrtägiger V2-Wochenendwunsch erneut importiert, anderer Kommentar | Stabile Importidentität wiederverwenden, keine doppelte Budget-/Historienwirkung. |
| I05 | Gesamter korrigierter Import kollidiert mit vorhandenem Wunschbudget oder Urlaubs-Gutschriftduplikat | Gemeinsame Prüfung vor aktiver Übernahme; entweder gültig dedupliziert vollständig speichern oder Stapel zur Korrektur lassen, nichts teilweise übernehmen. |
| I06 | Datenbankfehler während aktiver Stapelübernahme | Transaktion rollt alle aktiven Änderungen zurück; Korrekturstapel und verständliche Ursache bleiben zur Bearbeitung verfügbar. |

## Z – Pausen, Nacht und Zeitumstellung

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| Z01 | KC10/R früh genau 6 h; FK 6:01 h | Erste beiden ohne automatischen Abzug; FK enthält 30 min Pause, 331 min Arbeit. Keine 6-h-Pause allein aus Gewohnheit. |
| Z02 | KCT10 7:15 h, KC16/W17/W16/WL/BK/INT/N17/R spät je 8 h, KCT/TW 9:30 h; KC15 9 h | Je eine 30-min-Pause, Arbeit 405/450/540 min wie Katalog; KC15 510 min. Pause verlängert keinen Block. R ist bestätigte normale Arbeit und benötigt kein ungeklärtes Reserve-Bewertungsprofil mehr. |
| Z03 | W17 17:00–01:00, Pause 21:00–21:30 | 480 Anwesenheit, 450 Arbeit, 180 Nachtminuten; kein Pausenabzug von 22:00–01:00. |
| Z04 | W17 gleiche Zeiten, Pause 22:00–22:30 | 450 Arbeit, 150 Nachtminuten. Bei sonst exakt gleicher höherer Qualität Z03 bevorzugen. |
| Z05 | KCT10/TW/KCT mit Pause 15:00–15:30; Vergleich zulässige Pause außerhalb T | Erster Kandidat erfüllt nicht die volle erforderliche T-Teilnahme und ist kein zulässiger erfüllender Kombiblock; nicht fiktiv voll anrechnen. Zweiter korrekt. |
| Z06 | LB an TS-Tag, Pause 17:00–17:30 | Verletzt vollständige TS-Erfüllung; keine volle TS markieren. Zulässige 13:00–13:30 ergibt dagegen 420 min Arbeit und volle Teilnahme. |
| Z07 | Zwei Personen eines normalen Dienstes nehmen gleichzeitig ihre enthaltene 30-min-Pause; Vergleich ausdrücklich zusätzlich aktiviertes CoverageRule-Profil | Im bestätigten Standard sind gleichzeitige Pausen erlaubt und verlangen keine Vertretung. Enthaltene/korrekte Pausen und geschützte Teamfenster bleiben zu prüfen. Ein ausdrücklich separat konfiguriertes strengeres Abdeckungsprofil darf den Vergleichsfall technisch ablehnen; sein Test ist kein Nachweis eines betrieblichen Vertretungszwangs. |
| Z08 | BK 28.03.2026 20:00–29.03.04:00, Pause 21:00–21:30 | 420 reale Anwesenheitsminuten, 390 Arbeit, 300 reale Nachtminuten. Geld/zusätzliche Gutschrift separat nach Profil. |
| Z09 | BK 24.10.2026 20:00–25.10.04:00, Pause 21:00–21:30 | 540 Anwesenheit, 510 Arbeit, 420 Nachtminuten; doppelte Herbststunde physisch berücksichtigen. |
| Z10 | Ende 28.03.2026 20:00 CET; nächster Start 29.03.08:00 CEST; Vergleich 07:59 | Tatsächlich 660 min Ruhe, Vergleich 659; lokale Anzeige von 12 h ist kein korrekter Dauernachweis. |
| Z11 | Lokales WL-Ende 29.03.2026 02:00; manueller Zeitpunkt 25.10.02:30 ohne `fold` | Erstes nicht existent: keine stille Verschiebung. Zweites mehrdeutig: expliziten Offset/fold verlangen; zwei Varianten unterscheiden sich in UTC um 60 min. |

## K – Stunden, Verträge und Rundung

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| K01 | S0, W=25, volle Monate Februar 2026/2028, April/November 2026, Jänner 2026 | Monatssoll 6000 / 6214 / 6429 / 6643 min für 28/29/30/31 Tage; keine pauschalen vier Wochen. |
| K02 | S0 November, W=25, B=+600, neues V2-Konto | E standardmäßig 0, B bleibt 600; ohne G Arbeitsziel 5829 min. Bei gewünschtem E=600 ist Ziel 6429, nicht B gelöscht. |
| K03 | S0 November, W=25, B=−480, E=0, G=0 | Arbeitsziel 6909 min; Vorzeichen richtig, keine Erhöhung des Minussaldos durch falsche Formel. |
| K04 | Ein expliziter Urlaubstag bei W=25/30/37 | G=300/360/444 min. 7,4 h sind 444 min, keine Rundung auf 7 oder 8 h. |
| K05 | S0 November W=25, fünf erfasste Urlaubstage, B=600, E=0 | G=1500; Ziel `6429−600−1500=4329` min. Rein rechnerisch P=4329 ergibt Ende 0; keine zusätzliche Sollminderung. Kein Anspruch, eine echte Schichtkombination könne dieses Ziel exakt erreichen. |
| K06 | Fünf Gutschrifttage bei W=25,04 | Roh-G = 5×300,48 = 1502,4 min, nach einmaliger Monatsrundung 1502; nicht fünfmal runden und 1500 buchen. |
| K07 | S0 November, W=25 an 01.–15., W=30 an 16.–30.; Urlaub 02. und 16. | S roh 49500/7 min → 7071; G=300+360=660 min. Tagesgültigen Vertrag verwenden. |
| K08 | S0, Eintritt 16.11., W=25, außerhalb Beschäftigung keine Tage | S roh 22500/7 → 3214 min für 15 Beschäftigungstage, nicht ganzer Monat. Urlaubserwerb separat exakt 2×15/30 = 1 Tag; Sollstunden- und Urlaubskonto nicht vermischen. Bei 16 Beschäftigungstagen in einem 31-Tage-Monat Erwerb exakt 32/31 Tage, nicht vorzeitig auf ganze Tage runden. |
| K09 | S=600, B=300, E=0, G=600; Vergleich W=0 | Roh-Arbeitsziel −300, keine negative Zuteilung. Bei P=0 Ende +300 und Abweichung +300 erklären. Bei Nullsoll keine Division durch null in Fairness; Nullfall ausdrücklich anzeigen. |

## L – Kalender, Zeitmengen und Tarife

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| L01 | Nationaler AT-Testkalender 2026 | Ostermontag 06.04., Himmelfahrt 14.05., Pfingstmontag 25.05., Fronleichnam 04.06. sowie neun feste Feiertage aus Fachregeln. Osterdatum selbst ist nicht zusätzlich als Werktagsfeiertag einzusetzen. Primärquellenfreigabe bleibt vor Produktabnahme nötig. |
| L02 | 24.12., 31.12., 25.12., 26.12.2026 | Erste beiden keine nationalen gesetzlichen Feiertage, letzte beiden ja; zusätzliches KV-Profil darf erste beiden separat markieren. R-Periode verändert den nationalen Kalender nicht. |
| L03 | N17 30.04.2026 17:00–01.05.01:00, Pause 21:00–21:30 | 450 Arbeits-, 180 Nacht-, 60 gesetzliche Feiertagsminuten. Physische Segmente: April 390 Arbeit/120 Nacht, Mai 60/60. M1 bucht dagegen alle 450 Arbeitsminuten auf April und null auf Mai. Alte M0-Buchung bleibt als Legacy-Vergleich unverändert; Mengen werden nicht doppelt gezählt. |
| L04 | N17 31.10.17:00–01.11.2026 01:00, Pause vor 22:00 | 01.11. ist Sonntag und Feiertag: je 60 Minuten in beiden Kategorien, aber nur 60 physische Arbeitsminuten dort. Keine automatische doppelte Eurovergütung. |
| L05 | Zeitmengen vorhanden, KV-/BV-Zuordnung oder personenbezogene Bemessungsbasis fehlt | Exakte Mengen, Euro „ungeklärt“, nicht 0 und nicht erfundener Tarif. Nachweisstatus nennt fehlende Grundlage. |
| L06 | Zwei ausdrücklich bestätigte **synthetische** Testtarife: 2 EUR/Nachtstunde bis 31.12.2026, 3 EUR ab 01.01.2027; je 60 Nachtminuten beiderseits | 2+3=5 EUR nach Zeitgültigkeit; keine Aussage über echte KV-Beträge. Vor Wirksamkeitsbeginn/neben Anwendungsbereich kein passender Tarif statt stiller Übernahme KV 2026. |

## H – Historie und Fairness

Die Fälle prüfen die bestätigte Freitags-W17-Ausnahme, vertragliche Fairness,
Gruppenschutz und eingefrorene Historie. Abweichende alte Profile bleiben explizite
Legacy-Vergleiche; andere bloß synthetische Zielgewichte entscheiden keine neue Betriebsregel.

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| H01 | Derselbe Entwurf dreimal planen/speichern, dann dieselbe Revision zweimal bestätigen | Vor Bestätigung keine neuen historischen Fakten; danach genau eine aktive Bestätigung/Faktenmenge, keine Doppelzählung. |
| H02 | Bestätigter November mit alten W=25; Dezember Vertrag auf W=30 und globale Wünsche geändert | Alte Sollanteile, Wunschschlüssel und Mengen bleiben unverändert; nur neue Revision benutzt neue Daten. |
| H03 | Ein Wunsch über Monatsgrenze, durch zwei Dienste in zwei bestätigten Monaten verletzt | In kumulierter Historie einmal dieselbe Wunschidentität; monatliche Einzelberichte dürfen denselben Bezug zeigen, ohne kumuliert zwei zu behaupten. |
| H04 | A/B gleiche relevanten Rechte/Verträge/Wunschanzahl, historisch A zwei Übergehungen und B null; genau eine weitere unvermeidlich | Unter gewähltem historisch ausgleichendem Testziel eher B belasten; nicht bloß feste Belastungssumme minimieren. Höhere Besetzung/harte Regeln unverändert. |
| H05 | Nach Wochenstunden gewichtetes Testprofil, A=25/B=50, gleiche Verfügbarkeit und Rechte; drei gleiche Nacht-Einsätze | Sollanteile 1:2, entsprechende Verteilung bevorzugen. Bei fehlender Berechtigung oder Teilbeschäftigung Pool/Gewichte korrekt begrenzen; bei absolutem Profil andere explizite Sollanteile. |
| H06 | Legacy-Sonderhistorie ohne belegte V2-Zulagenhistorie; zusätzlich A mit zwei und B mit sechs relevanten Wünschen | Fehlende Zulagenhistorie kennzeichnen und keine BK/WL-Zuordnung erfinden. Der bereits bestätigte Schutz kleiner Wunschgruppen gilt weiter: bei gleicher höherer Qualität A stärker schützen; keine erneute offene Grundsatzfrage daraus machen. |

## M – Speicherung, Kopienmigration und Legacy

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| M01 | Synthetische Schema-1-/Schema-2-Dateien, bestätigte Monate, feste Personen-IDs, unterschiedliche Dezimalwochenstunden/Salden | Migration auf Kopie nach Schema 3: Legacy-Payloads bytegleich, IDs/Bestätigungen/Salden unverändert; neue Tabellen additiv. Originalhash identisch vor/nach Prüfung. |
| M02 | Testdatei mit committed WAL-Inhalten, Sicherung über SQLite-Backup-API | Vollständige konsistente Zieldatei inklusive WAL-Daten; bloße Kopie der Hauptdatei gilt nicht als hinreichender Nachweis. |
| M03 | Prozess-/SQL-Fehler an mehreren Migrationsstellen vor Commit | Zieltransaktion vollständig zurückgerollt, keine halbe Version/teilweise Historie; Original und Sicherung unverändert. |
| M04 | Migration zweimal, Ziel schließen/neu öffnen, `foreign_key_check`/`integrity_check` | Keine doppelten Personen/Fakten/Quoten; Checks bestehen; unbekannte neuere Schemafassung verständlich ablehnen. |
| M05 | Alter P1-Blocker sowie alter einzelner Sonderdienst | `legacy_hard_block` ohne Urlaubsgutschrift; Sonderdienst bleibt Legacy, nicht BK oder WL. Fehlende Qualifikations-/Beschäftigungsdaten nicht als unbegrenzt beschäftigt erfinden. |
| M06 | Legacy-Monat ohne `wish_snapshot`, mit geänderten aktuellen globalen Sperren | Fehlende damalige Historie kennzeichnen; beim Lesen keine rückwirkenden historischen Zahlen erzeugen. Am Migrationsstichtag verfügbare Sperren nur als solchen Snapshot bezeichnen. |
| M07 | Bestätigten Legacy-Monat anzeigen/exportieren, neue V2-Regeln unvereinbar | Lesbar/exportierbar nach Legacy-Profil, kein Umschreiben/Neuoptimieren und keine falsche V2-Konformitätsmarkierung. |
| M08 | Neues V2-Monatskonto und späteres ausdrücklich bestätigtes Stichtagsprofil | Anfangssaldo übernehmen, E neu 0; vorhandene gespeicherte Alt-E nicht ändern. Alte App schreibt weiterhin nur ihre ursprüngliche Datendatei, keine Schema-3-Datei. |

## O – Optimierung, Diagnose und Nachweise

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| O01 | Operativer Platz, alle berechtigten Personen im Urlaub bzw. nicht beschäftigt | Diagnostischer Teilplan mit offenem Platz und konkreten Ursachen; keine illegale Zuteilung für Vollbesetzung. |
| O02 | Zwei unvereinbare harte Personen-/Datumsfixierungen, keine zugelassene Alternative | Konkreter Fixierungskonflikt bzw. wirklich bewiesene Unlösbarkeit; Fixierungen nicht verschieben/löschen. Nicht jeden leeren Zeitlimitlauf als unlösbar darstellen. |
| O03 | Urlaub, 10:30 h Ruhe oder sechster Tag würde volle T/TS-Teilnahme ermöglichen | Schutzregeln bleiben unverletzt; weiches Teilnahmeziel auslassen und Ursache/zulässige Ausnahme anzeigen. |
| O04 | Eine Verbesserung der niedrigeren Fairnessstufe würde einen zusätzlichen höher priorisierten Wunsch verletzen | Unter bestätigter Hierarchie ablehnen; viele kleine Fairnessverbesserungen können höhere Stufe nicht überstimmen. |
| O05 | Gleicher Snapshot mit gültigem vorhandenen Plan, sofortiger Abbruch bzw. kontrolliertes Zeitlimit vor Suche | Vorhandenen Plan erhalten, Eingaben unverändert, Zielwerte zum zurückgegebenen Plan passend; keine falsche globale Optimalität. |
| O06 | Höhere Stufe unbewiesen, spätere Stufe optimal unter festem Präfix; außerdem analytisch null offene Plätze | Einzelbeweise korrekt ausweisen; späteres bedingtes Optimum und Nullziel ergeben zusammen nicht automatisch global `optimal`. |
| O07 | Einzeldienstübertragung, Zweiertausch, größere Umverteilung oder Pausenverschiebung | Nur unter sämtlichen harten Regeln und nicht schlechteren höheren Zielen akzeptieren; endgültig neu bewerten, betroffene Beweise zurücknehmen. |
| O08 | Selber Snapshot/Versionen/Hardware/Seed/Worker, Läufe 5/20/60 s; Start jeweils gleicher gültiger Incumbent | Abdeckung, Teilnahme, Wünsche je Person, maximale/gestreute Salden, Nacht-/Feiertagsmengen, Laufzeit und Beweise protokollieren. Keine garantierte optimale Verbesserung aus längerer Zeit behaupten; bester bekannter Plan bleibt Vergleichsmaßstab. |
| O09 | Ergebnisliste nach Solver manipulieren: Pause in T legen, unberechtigte Person einsetzen, Randtagdienst ergänzen | Unabhängiger Prüfer erkennt Fehler direkt am Ergebnis, selbst wenn Solverstatus/gespeicherte Hilfsflags „optimal/gültig“ sagen. |

## X – Bedienung, Export und Plattformabnahme

| ID | Eingabe | Erwartetes Ergebnis |
| --- | --- | --- |
| X01 | Monat erfassen → Korrekturstapel bearbeiten → planen → manuell ändern/fixieren → prüfen → bestätigen/exportieren | Deutsche Meldungen, Kalender-/Namensauswahl, sichtbare offene Plätze/W16-Gründe/KC15-Ausnahmen und vollständige zugängliche Hinweise. Ungültige Fixierung wird erkannt; ausdrückliche Übernahme/Bestätigung trotz Abweichung ist möglich. Kein falscher Regelkonformitätsnachweis. |
| X02 | Eingabedaten während Hintergrundrechnung geändert; alten Solverstand übernehmen | Revisionskonflikt erkennen; keine unbemerkte Übernahme auf geänderte Regeln. Abbruch bleibt bedienbar, UI blockiert nicht. |
| X03 | Dienstplan-, Stunden-, Wunsch-, Zulagen-/Fairness-CSV und Prüfmanifest erzeugen; Fehler mitten im Schreiben injizieren | Alle tragen dieselbe Revisions-ID/Profil-/Historienbasis. Vollständiges Paket atomar veröffentlichen oder gar nicht; keine gemischten Planversionen. |
| X04 | Mehrmonatsdemo über Dezember/Jänner mit Rand-WL/BK, R, Urlaub, Vertragswechsel, Bestätigung und erneuter Planung | Quoten/Gutschriften/Wunschidentitäten nicht doppeln, nur bestätigte frühere Monate historisieren, Randplanung sichtbar und vom übernommenen Monat getrennt. |
| X05 | Native Windows x64 sowie macOS Sequoia ARM64/Intel, paketierte tzdata, Netz abgeschaltet | Programm ohne Python/Terminal startet, UI/CSV/SQLite/Prüfer/Solver und Wien-DST-Fälle funktionieren; Paketgrößen/Architektur/Signing-/Prüfstatus tatsächlich erfassen. Erst nach Ausführung als bestanden melden. |

## Abnahmegrenzen und spätere Automatisierung

Die Fälle werden schrittweise zu kleinen pytest-Datensätzen, Ergebnisprüfer-
Gegenproben und Qt-Integrationstests. Offene Profilvarianten werden parametrisiert,
nicht durch `skip` als scheinbar erledigte Produktabnahme geführt. Unit- und
Integrationsabnahme getrennt berichten; keine Oberflächenattrappe als Solvernachweis.

Für echte Mehrmonats-Benchmarks vollständige anonymisierte Eingaben samt damals
gültigen Regeln, Randständen und Versionen verlangen. Der alte Jännervergleich
1294/1548 h und 27,58 → 26,08 h bleibt ohne seine fehlenden Daten **nicht reproduziert**.
Seine 15-h-/7,5-h-/30-h-/Drei-Tage-Grenzen sind ausdrücklich kein V2-Rechtsprofil.
Die neuen Tests sollen diese Zahlen weder als Benchmarkeingabe erfinden noch
26,08 h als bewiesenes Optimum darstellen.
