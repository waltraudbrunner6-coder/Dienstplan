# Informationsprüfung und bereinigter Entscheidungsstand

Stand 11.11.2026. Geprüft wurden V2-Fachregeln, offene Fragen, Anwendung,
Urlaubs-/Stundenrechnung, Katalog, Import und letzte Nutzeraufträge. Für die
Prüfung wurde keine echte Benutzerdatenbank geöffnet oder verändert.

## Ursache der unverständlichen Urlaubsmeldung

Die Formel war nicht unbekannt: `accounting.leave_credits` berechnet bereits
**an diesem Tag gültige Wochenstunden ÷ 5**. Die alte Eingabe ließ aber Urlaub
mit leerer `credit_days`-Menge zu. `reporting.hours_rows` kennzeichnete die
Stundengutschrift dann als ungeklärt; `history.confirmation` verweigerte die
Bestätigung. Die Importvorschau zeigte dazu nur einen Hinweis. Die Oberfläche
verlangte technische ISO-/Datumslisten statt einer verständlichen Tagesauswahl.

Neu bestätigt sind zwei Urlaubstage Anspruch je Monat, Ansparen und ein
Anfangsbestand je Person. Dies sind drei getrennte Größen:

- Anspruch und vorhandener Bestand in Tagen;
- tatsächlich verwendete, ausdrücklich markierte Urlaubstage;
- Stundengutschrift W/5 je solchem Tag.

Ein ausdrücklich mit U markiertes Datum zählt auch am Wochenende/Feiertag.
Doppelte Einträge derselben Person am selben Datum zählen einmal. Zwei Tage
monatlicher Anspruch sind kein Verbrauchs-Hartlimit. Ein voller
Beschäftigungsmonat bringt zwei Tage; Teilmonate zählen exakt mit
`2 × Beschäftigungskalendertage / Kalendertage_des_Monats`. Die Bruchteile werden
ohne pauschale Tagesrundung angespart. Fehlende Anfangsbestände werden nicht geraten.

## Ergebnis der sieben aktuellen Rückfragen

Alle sieben Fragen und die drei anschließenden Restfragen wurden beantwortet.
Die thematisch zusammengefassten Antworten sind verbindlich; Umsetzungs- und
Teststatus werden unabhängig davon nachgeführt.

| Geprüfter Mangel | Bestätigte Regel / notwendige Korrektur | Betroffene Codebereiche |
| --- | --- | --- |
| Urlaub ohne Gutschrifttage blockierte Bestätigung; U wurde als ungeklärt behandelt | Jedes ausdrücklich markierte U-Datum zählt mit W/5, einschließlich Wochenende/Feiertag. Auswahl und errechnete Stunden sichtbar machen; vorhandene unvollständige Einträge verständlich korrigierbar. | `entries.py`, `leave.py`, `reporting.py`, `spreadsheets.py`, `plan_import.py`, `history.py` |
| Urlaubskonto fehlte | Zwei Tage Anspruch je Monat, angespart, mit persönlichem Anfangsbestand. Anspruch, Verbrauch und Stundengutschrift getrennt führen. Keine künstliche Zwei-Tage-Eingabegrenze. | `leave.py`, Konten-/Urlaubsoberfläche und Speicherung |
| R wurde aus normalen Kandidaten ausgeschlossen und Zuteilung verweigert | R zählt wie ein normaler Dienst: früh sechs Stunden, spät 7,5 bezahlte Stunden nach der normalen Pause. | `application.service_candidates`, `catalog.Event.assign`, Bedarf und Import |
| KC15 war im Katalog nicht definiert | Ersatz für beide Dienste KC10 und KC16, wenn sonst die Besetzung nicht gelingt: 15:00–00:00, eine Person, normale Pause; kein zusätzlicher paralleler Dienst. | `catalog.py`, Ersatz-/Solverlogik, Import, Bedarf |
| Gleichzeitige Pausen waren mangels Abdeckungsprofil möglich, aber nicht entschieden | Gleichzeitige Pausen sind ausdrücklich erlaubt. Keine zusätzliche Vertretungsplanung oder durchgängige Mindestzahl erfinden. | Pausen-/Abdeckungslogik und verständliche Hinweise |
| LB-Anker fehlte | Ab Donnerstag 03.12.2026 alle 14 Tage. Feste Personen weiterhin als normale Eingabe erfassen. | `catalog.month_calendar` und Kalenderoberfläche |
| Monatsquote freier Wochenenden blieb ohne Profil ungeprüft | Sonntag bestimmt den Monat des Wochenendes. Die schon entschiedene Zwei-Wochenenden-Regel damit aktiv anbinden. | `application.standard_month`, `calendar_rules.check_calendar` |
| Monatsbuchung wich vom gewünschten Startmonat ab | Neues Profil M1 bucht den ganzen bezahlten Dienst im Monat des lokalen Dienstbeginns. Tages-/Nacht-/Feiertagsmengen bleiben physisch segmentiert. Alte bestätigte M0-Daten unverändert lassen. | `reporting.py`, `objectives.py`, UI, Exporte, Bestätigungen |
| KC10 am Donnerstag 31.12.2026 war inhaltlich zweideutig | Gemeint ist der lange KCT10 bis 17:30. Im Import entsprechend nachvollziehbar zuordnen. | Katalog- und Importzuordnung |

Die 30-Minuten-Pause bei Diensten über sechs Stunden stand bereits fest. Die
neue Antwort zu gleichzeitigen Pausen schafft keine abweichende Pausenlänge und
keine Ausnahme von der enthaltenen Lage oder den geschützten Teamzeiten.

## Monatsbuchung und physische Zeitmengen getrennt halten

Die neue Regel ist M1: Ein Dienst am 30.11. von 17:00 bis 01:00 mit 30 Minuten
Pause zählt mit 7,5 Stunden zum Novemberkonto. Für Nacht-/Tages-/Feiertagsmengen
bleiben die tatsächlichen Kalenderabschnitte auf November und Dezember verteilt.

M0 bleibt zum Lesen alter Daten verfügbar und bedeutet weiterhin tatsächliche
Arbeitszeit im jeweiligen Kalendermonat. Unterstützte alte Profile werden nicht
stillschweigend umgedeutet. Neue offene Monatsstände und ausdrücklich übernommene
Entwürfe erhalten die neue Buchung nach der dafür vorgesehenen Anbindung;
bestätigte Geschichte wird nicht neu bewertet. In Berichten und Optimierung
muss dieselbe Profilwahl verwendet werden.

Relevante APIs sind `reporting.booked_work_minutes`, `hours_rows` und
`booked_required_work_range`. Letztere berücksichtigt R standardmäßig als normalen
Dienst. Die ältere physische `required_work_range` behält ihren bisherigen
R-Ausschluss als API-Standard; neue Aufrufer können `include_reserve=True`
explizit setzen. Diese Kompatibilitätsoption darf in der neuen normalen Anzeige
nicht zu einem fehlenden R-Bedarf führen.

## Anschließend ebenfalls geklärt

- Teilmonatsurlaub: exakt zwei Tage × Beschäftigungskalendertage ÷ Kalendertage
  des Monats. Keine neue Rundung auf ganze oder halbe Tage erfinden.
- FK: ausschließlich Einzeltermine, kein automatischer Wiederholungsrhythmus.
- Die enge Freitags-W17-Ausnahme gilt auch für Wochenend-Freiwünsche. Andere
  Arbeit am Samstag/Sonntag wird dadurch nicht ausgenommen. Neue offene
  Normalmonate verwenden diese Regel; bestätigte Wunschhistorie wird nicht
  nachträglich umgedeutet.

## Tatsächlich noch fehlende Angaben

- Wochenendquote und Einbeziehung nur teilweise beschäftigter Wochenenden bei
  Ein-/Austritten. Der Sonntag als Monatsbesitzer ist jetzt geklärt.
- Konkrete feste LB-Personen als normale Kalenderangabe.
- Relativer Optimierungsrang freiwilliger T-/TS-Teilnahme, falls sie mit Wünschen
  und Stundenbalance konkurriert. Der freiwillige Charakter ist entschieden.
- Zeitgültige Tarif-/BV-Daten, Einzelraten und Kumulation nur für betroffene
  Rechts-/Euroaussagen. Kein pauschaler Blocker für die normale Urlaubsroutine.

Diese Restfragen sollen im betroffenen Sonderfall konkret benannt werden. Sie
stellen die aktuell geklärten Urlaubs-, Dienst- und Buchungsregeln nicht erneut
zur Disposition. Details: `V2_OFFENE_FRAGEN.md`.

## Bereits beschlossene Regeln und Dokumentationsfehler

Nicht erneut abzufragen sind insbesondere: V2 als Standardanwendung, Monatssoll
W × Kalendertage ÷ 7, Urlaub W/5, zwei WL und ein BK ganzjährig, BK/WL nicht am
selben Startdatum, Vertragsstunden-Fairness, Schutz weniger Freiwünsche,
bestätigte Historie ohne Doppelzählung sowie übersteuerbare manuelle Änderungen,
Importe und Monatsbestätigungen. Ebenfalls entschieden sind die betrieblichen
Ruhe-/Arbeitstagsregeln, zwei freie Wochenenden, freiwilliges T/TS, Zeitzone Wien
und österreichischer nationaler Feiertagskalender.

Überholte Texte zu zusätzlicher Testoberfläche, zwingender Ablehnung jedes
Donnerstagswunsches oder Bestätigung nur vollbesetzter gültiger Pläne sind zu
bereinigen oder historisch zu kennzeichnen. Sie sind keine neuen Fachfragen.
Technische Namen wie S0/M0/M1/E0 gehören in zusätzliche Erläuterungen, nicht als
unverständliche Voraussetzung vor die normale Bedienung.

Dieser Informationsbericht erklärt keine Funktion allein aufgrund einer Antwort
für vollständig implementiert und nicht alle 125 V2-Abnahmefälle für bestanden.
Tatsächliche Änderungen, Regressionen und native Nachweise stehen jeweils in
`V2_FORTSCHRITT.md` und `V2_NATIVE_PRUEFUNG.md`.
