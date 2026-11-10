# V2 – Offene Entscheidungen und begrenzte Auswirkungen

**Folgeauftrag 10.11.2026:** F07 ist hinsichtlich der betrieblichen Ausschlussregel
geklärt: BK und WL niemals am selben lokalen Startdatum. WL-Anzahl jetzt zwei
pro Woche in jedem Monat, BK einmal. Die Randwochenabgrenzung aus F06 bleibt als
explizite Auswahl gespeichert; bisher kein globaler Standard bestätigt. Für die
übergebenen Tabellen wurden Donnerstag-X, KC15/R/U und KC10 am Donnerstag gezielt
nachgefragt; bis zur Antwort bleiben deren abhängige Angaben Korrekturfälle.
Die früheren Fragen unten dokumentieren den bisherigen Entscheidungsstand.

Aktueller Implementierungs- und Prüfstand: [Fortschritt](V2_FORTSCHRITT.md),
[Zuordnung aller 125 Abnahmefälle](V2_ABNAHMESTATUS.md) und
[Bedienung des technischen Prüfbereichs](V2_BEDIENUNG.md). Die nachfolgende
Etappe-A-Spezifikation bleibt die fachliche Grundlage; Testprofile ersetzen sie nicht.

Stand 09.11.2026. Die bestätigten Regeln stehen in
[V2_FACHREGELN.md](V2_FACHREGELN.md). Eine offene Profilentscheidung blockiert nur
die hier genannten Teile. Kalender, Personen-/Vertragsmodell, echte Arbeits-/
Pausenintervalle, Legacy-Lesesicherung und isolierte Abnahmetests können weitergehen.
Eine fehlende Entscheidung ist keine Erlaubnis, einen stillen Produktstandard
einzuführen. Testvarianten werden ausdrücklich als Testprofile gekennzeichnet.

## P0 – Vor einer vollständigen produktiven Planung nötig

| ID | Präzise Entscheidung | Varianten und Folgen | Abhängiger Teil / unabhängige Arbeit |
| --- | --- | --- | --- |
| F01 | Welche konkrete zeitgültige Caritas-/VkA-Dienstform und welche Betriebsvereinbarungen gelten für Kältetelefon Wien und die betroffenen Personen? Welche zusätzlichen Tages-/Wochen-/Durchrechnungs-/Pausengrenzen folgen daraus? | Belegte Zuordnung anhand Originalfassung und BV; unterschiedliche Dienstformen können andere Bemessungsgrundlagen/Kombinationen verlangen. „Außendienst“ allein genügt nicht. Auch Zeitumstellungsgutschriften benötigen Beleg. | Rechtlicher Gesamtnachweis und Eurobewertung; betriebliche 11-h-/5-Tage-/Wochenendregeln und Zeitmengen unabhängig modellieren |
| F02 | Ist R je Zeitfenster volle Arbeit, eine konkret definierte Bereitschaft oder eine Kombination mit tatsächlich abgerufener Arbeit? Wie sind Geld, Gutschrift, Ruhe-/Arbeitstagswirkung und Bemessungsgrundlagen geregelt? | Volle Arbeit: Normalfall 360/450 Arbeitsminuten; reine Bereitschaft: eigenes bestätigtes Profil, keine automatische volle Arbeit oder automatische Freizeit; Mischform: zusätzliche Einsatzabschnitte ohne Doppelzählung. Keine Ist-Abrufe erfinden. | Reservebewertung und betroffene Schutz-/Saldenprüfung; feste zwei R-Zeitfenster/Tag und je eine Person sind bereits modellierbar |
| F03 | Muss eine Mindestbesetzung während Pausen/Teamteilnahme durchgehend tatsächlich arbeiten? Wer darf real vertreten, an welchem Ort und mit welchen Einschränkungen? | Starttermin-Besetzung ohne ununterbrochene Arbeitsabdeckung oder zeitlich lückenlose Mindestabdeckung mit bestätigten Vertretungsrollen. Bei Letzterem reicht keine nominelle Zweierbesetzung mit gleichzeitigen Pausen. Vertretung darf keine verbotenen zusätzlichen Blöcke erzeugen. | Pausenkandidaten und Abdeckungsconstraints; echte Pausenobjekte und Zeitrechnung unabhängig fertigstellen |
| F04 | Welches Soll-/Durchrechnungsprofil gilt bei Vertragswechsel, Teilmonat und Feiertag; welchem Abrechnungsmonat werden über Mitternacht/Monatsgrenzen laufende Arbeit und Ausgleichsgutschriften zugerechnet? | Technische Tagesanteilsregel `Σ W_d/7` versus belegter Dienst-/Sollkalender; tatsächlicher Arbeitsmonat versus ausdrückliche Dienststart-Zuordnung. Physische Kalender-/Nacht-/Feiertagsmengen bleiben in allen Varianten tatsächlich segmentiert. | Exaktes `S`, monatliches `P/G`, Salden; Verträge, Rohmengen und Beispielrechnungen mit benanntem Testprofil unabhängig |
| F05 | Welche Datumsmenge innerhalb eines mehrtägigen Urlaubs ist als anrechenbare Urlaubstage zu erfassen? | Explizit ausgewählte Tage oder nachvollziehbar vorgeschlagene Tage aus einem bestätigten individuellen Arbeits-/Urlaubskalender. Nicht ungeprüft alle Kalendertage und nicht ungefragt Montag–Freitag annehmen. Feiertagsbehandlung aus F04/F01. | Tagesmenge der Gutschrift; die Formel **gültiges W/5**, harte Abwesenheit, Urlaub als frei und Deduplizierung sind entschieden |
| F06 | Welche Bezugswoche und Randwochenabgrenzung gilt global? | Zwei WL und ein BK ganzjährig sind jetzt bestätigt. Die App bietet explizit gemeinsame ISO-Mo–So-Randwochen oder nur volle Monatswochen; kein stiller globaler Standard. | Gemeinsame Quoten/Reservierungen sind implementiert; die betriebliche Profilwahl bleibt ausdrücklich. |
| F07 – geklärt 10.11.2026 | BK und WL dürfen niemals dasselbe lokale Startdatum haben. | Neue ausdrückliche Nutzervorgabe; als harte Regel unabhängig vom Wochenprofil geprüft. | Keine offene Variantenwahl mehr; F06 zur Randwochenabgrenzung bleibt gesondert. |
| F10 | Welcher Monat zählt ein Samstag/Sonntag-Wochenende über der Monatsgrenze? Wie werden Eintritt/Austritt mitten im Monat und nur teilweise aktive Wochenenden gezählt? | Samstag- oder Sonntagbesitzer beziehungsweise ein bestätigtes anderes, eindeutiges Verfahren; Teilmonat unveränderte zwei Wochenenden oder explizite anteilige/anders geregelte Quote. Niemals dasselbe Wochenende zweimal als Ressource verplanen. | Monatsquote; tatsächliche Tagesbelegung, W17-Zählausnahme und Vorwochen-Freipaare unabhängig prüfen |
| F14 | Ab welchem Planmonat/Datum wird V2 für neue Planstände wirksam? | Expliziter Stichtag, frühere bestätigte Monate bleiben Legacy; Übergangsmonate gegebenenfalls nur mit ausdrücklich versioniertem Profil. Kein automatischer Stichtag aus dem Programmdownload. | Profilwahl/Übernahme; additive Migration und Legacy-Archiv unabhängig |

## P1 – Vor den jeweiligen Katalog-/Optimierungsschritten nötig

| ID | Entscheidung | Varianten / Folgen | Unabhängig möglich |
| --- | --- | --- | --- |
| F08 | Konkretes eingeschlossenes Donnerstags-Referenzdatum für LB? | Alle 14 Kalendertage ab diesem Anker; Referenzmonat allein ist nicht eindeutig. Das 14-Tage-Verfahren selbst steht fest. | Rhythmusfunktion und Tests mit künstlichem Anker |
| F09 | In welchem Zeitraum wiederholt sich FK? | Monatlich, jährlich oder einmaliges Ereignis; jeweils ein konkret festgelegter Tag/Person/Zeitspanne pro bestätigter Periode. | Allgemeine feste Ereignisse und einmalige Testtermine |
| F11 | Gilt die enge Freitags-W17-Ausnahme auch für den **Wochenendwunsch**? | Gleiche Ausnahme: solcher Wunsch kann trotz Samstag-Nachtminute erfüllt sein; strikte tatsächliche Freiheit: Wunsch einmal verletzt, obwohl das Wochenende für die Schutzquote frei zählt. | Eigene Wunschidentität und verschiedene Klassifikationen |
| F12 | Welcher Fairnessmaßstab und Historienzeitraum gilt je Zielklasse? Soll die alte Bevorzugung von Personen mit weniger Wünschen weitergelten? | Gleiche absolute Anteile oder Anteile nach zeitgültigen Wochenstunden, Beschäftigung und Berechtigung; rollierender Zeitraum oder kumulativ ab Stichtag; unterschiedliche Pools je Dienst-/Zulagenklasse. Anzahl-/Zeitmengen- oder erst bei belegtem Tarif Euroausgleich. „Wenige Wünsche bevorzugen“ separat Ja/Nein. | Unveränderliche bestätigte Rohhistorie, berechtigte Pools und mehrere Auswertungen |
| F13 | Welche Reihenfolge haben die noch offenen weichen Ziele, und wie stark wiegt ein Wochenendwunsch gegenüber einem Einzeltag? Welche Toleranz verbindet Stunden- und Zulagenfairness? | Arbeitsvorschlag aus Fachregeln, alternativ Wünsche vor Teilnahme bzw. andere ausdrücklich bestätigte Stufen. Wochenendwunsch eigenes Gewicht `w_WE`, nicht automatisch 2. Stunden vor Zulagen oder bestätigte Stunden-Toleranz, innerhalb derer Zulagen ausgeglichen werden. | Stufen-Engine mit benannten Zielkomponenten, separate Maße und reproduzierbare Vergleiche |

Die Tabellen fragen weder nach dem freiwilligen Charakter von T/TS noch danach,
ob betriebliche Schutzregeln verletzt werden dürfen: **beides ist entschieden**.
F13 betrifft nur relative Ränge innerhalb zulässiger weicher Ziele. Eurobeträge
werden ohne F01/F02 und personenbezogene Bemessungsgrundlagen nicht geraten.

## Monatlich benötigte Eingaben statt neuer Fachfragen

Beschäftigungsdaten und Verträge, N17-Führerscheinstatus, individuelle Rechte,
TS-/VN-/INT-/N17-/FK-Daten und feste Personen, LB-Personen, Urlaubszeiträume samt
anrechenbaren Tagen, Wunschbudgets, gewünschte Wochenenden und optionale WL/BK-
Datumsfilter sind normale Eingaben. Leere Pflichtangaben werden im konkreten
Monat benannt; sie verhindern keinen Entwurf des Datenmodells.

## Erledigte Klärungen

- T/TS werden von den ausdrücklich festgelegten Blöcken ersetzt; kein doppelter
  Zeit- oder Teilnahmeeintrag. KCT10 statt des früheren Tippfehlers KC10.
- LB an TS-Tagen 12:00–19:30, gesamte TS-Teilnahme, genau eine Pause.
- Befristete Außendienstperson darf T/TS und hat dafür dasselbe weiche Teilnahmeziel.
- Ein Startdatum erlaubt einen Block, keine getrennten Tageseinsätze.
- Wien-Zeitzone, Nachtzeit 22:00–06:00 und österreichischer nationaler Feiertagskalender.
- Elf Stunden Ruhe, fünf tatsächliche Arbeitstage, zwei freie Wochenenden und
  zwei **zusammenhängende** freie Tage im unmittelbar davorliegenden Mo–Fr.
- Urlaub zählt ohne Dienst als frei; Tagesgutschrift gültiges W/5, keine Vier-Tage-Grenze.
- R hat zwei getrennte Zeitfenster täglich in der bestätigten Periode, je eine Person.
- WL/BK-Termin- und Personenwahl standardmäßig gemeinsam automatisch, Fixierungen getrennt.
- Neue V2-Monate standardmäßig gewünschter Endsaldo null, Anfangssaldo erhalten.
- Donnerstag-Freiwünsche bleiben unzulässig. Die Bedienperson hat am 09.11.2026
  die **Korrekturvormerkung** bestätigt: sichtbar und bearbeitbar erhalten, aber
  bis zur vollständigen Korrektur keine aktive Übernahme und keine Teilübernahme
  eines fehlerhaften Imports. Die ursprünglichen widersprüchlichen Formulierungen
  aus Abschnitt 6/11 sind damit bereinigt; keine offene Entscheidungsfrage mehr.

## Technischer Quellenblocker, keine erfundene KV-Auslegung

Die vier in den Fachregeln aufgeführten Primärquellen sind aus dieser Umgebung
mit `CONNECT 403` gesperrt. Der gespeicherte Freigabeentwurf erhält die bestehende
API-Freigabe und ergänzt `vka.or.at`, `www.betriebsrat-caritas-wien.at`,
`www.usp.gv.at`. Speichern des Entwurfs ist kein belegter Zugriff und keine
Veröffentlichung. Nach Übernahme der Änderung in den Umgebungseinstellungen
und Veröffentlichung werden frische Abrufe benötigt; eventuelle tatsächlich
auftretende Redirect-Domains sind dann gezielt nachzutragen.

Nach Freigabe sind Originalfassungen zu sichern, Hash/Datum/Fundstelle zu erfassen,
E.4 sowie C.8/E.6 tatsächlich zu lesen, die Anwendbarkeit/BV für Kältetelefon zu
belegen und die Profilversionen mit Gültigkeitsdaten zu versehen. Die benannten
Paragraphen sind **Prüfaufträge**, keine hier bereits verifizierten Rechtsaussagen.
Quellenzugang allein beantwortet außerdem nicht die konkrete betriebliche Zuordnung.

Für Etappe B1 wird keine dieser Antworten vorgetäuscht: reine Zeit-/Segment- und
Vertragswertobjekte sowie Migrationstests mit synthetischen Daten sind unabhängig.
Produktive vollständige V2-Planung bleibt von den betroffenen P0-Entscheidungen abhängig.
