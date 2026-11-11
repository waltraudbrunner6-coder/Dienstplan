# V2 – Geklärte Regeln und verbleibende Angaben

Stand 11.11.2026. Alle sieben Rückfragen der ersten Fragerunde und die drei
anschließenden Restfragen zu Teilmonatsurlaub, FK und Wochenendwunsch wurden
beantwortet. Die folgenden Antworten ersetzen überholte offene Punkte aus
Etappe A; sie sind nicht erneut abzufragen.

Prüfbericht: [Informationsprüfung](V2_INFO_AUDIT.md). Tatsächlicher Umsetzungs- und
Teststand: [Fortschritt](V2_FORTSCHRITT.md). Verbindliche Regeln:
[Fachregeln](V2_FACHREGELN.md). Bedienung: [Anleitung](V2_BEDIENUNG.md).

## Am 11.11.2026 ausdrücklich bestätigt

| Thema | Bestätigte Antwort | Auswirkung |
| --- | --- | --- |
| Urlaubstage / F05 | Jedes ausdrücklich mit U markierte Datum zählt als ein Urlaubstag, auch am Wochenende oder Feiertag. | Gutschrift pro markiertem Datum mit den an diesem Tag gültigen Wochenstunden ÷ 5; gleiche Person/Datum nicht doppelt zählen. Bei einem längeren Zeitraum bleibt sichtbar, welche Daten ausdrücklich ausgewählt wurden. |
| Anspruch und Übertrag | Zwei Urlaubstage Anspruch pro Monat werden angespart; pro Person kann ein Anfangsbestand eingegeben werden. Teilmonatsanspruch exakt `2 × Beschäftigungskalendertage / Kalendertage_des_Monats`. | Anspruch, Verbrauch, Stundengutschrift und Resttage getrennt anzeigen. Bruchteile ohne pauschale Tagesrundung fortführen. Zwei Tage Anspruch sind keine Begrenzung auf höchstens zwei gebuchte Tage. Keine erfundenen fehlenden Anfangsbestände. |
| Pausenabdeckung / F03 | Gleichzeitige Pausen sind erlaubt. | Keine zusätzliche durchgängige Mindestbesetzung oder Vertretungsplanung aus fehlenden Angaben ableiten. Die bestehende enthaltene 30-Minuten-Pause bei mehr als sechs Stunden bleibt bestehen. |
| Reserve / F02 | R zählt wie ein normaler Dienst. | Früh 10:15–16:15: sechs bezahlte Stunden; spät 16:00–00:00: acht Stunden Anwesenheit abzüglich 30 Minuten Pause, also 7,5 Stunden. Keine gesonderte Bereitschaftsbewertung erforderlich. |
| KC15 | Wenn sonst nicht alle Schichten besetzbar sind, darf statt beider Dienste KC10 und KC16 ein gemeinsamer Ersatzdienst 15:00–00:00 mit einer Person verwendet werden. | Kein zusätzlicher Dienst neben KC10/KC16. Bestehende Pausenregel ergibt 8,5 bezahlte Stunden. Originalvarianten und Ersatz bleiben nachvollziehbar. |
| LB / F08 | Erster Termin Donnerstag, 03.12.2026, danach alle 14 Tage. | Kalenderanker steht fest; die festen Personen sind normale Monatseingaben. |
| Wochenend-Monatszuordnung / F10 | Der Sonntag bestimmt den Monat. | Das Wochenende 31.10./01.11. zählt zum November; ein Wochenende zählt nicht doppelt als Monatsressource. |
| Stundenbuchung / F04 | Der ganze bezahlte Nachtdienst zählt zum Monat seines Startdatums. | Neues explizites Profil M1. Tatsächliche Tages-/Nacht-/Sonn-/Feiertagsmengen bleiben kalendarisch segmentiert. Alte bestätigte Monatsstände werden nicht neu bewertet. |
| KC10 am Donnerstag, 31.12.2026 | Gemeint ist KCT10 bis 17:30. | Im betreffenden Import den langen Teamdienst verwenden; keine ungeklärte Kurz-/Langvariante mehr. |
| FK / F09 – geklärt | FK ausschließlich als einzelnen Termin erfassen. | Kein automatischer Wiederholungsrhythmus zu konfigurieren. |
| Wochenendwunsch / F11 – geklärt | Die enge Freitags-W17-Ausnahme gilt auch für den Wochenend-Freiwunsch. | Ein Freitag–Samstag-W17 allein verletzt den Sa/So-Wunsch nicht; weitere Wochenendarbeit weiterhin prüfen. |

Die Regeln stehen fest. Ob eine Funktion bereits vollständig integriert und
geprüft ist, wird gesondert in `V2_FORTSCHRITT.md` dokumentiert; eine Antwort allein
ist kein bestandener Implementierungs- oder Plattformtest.

## Noch bedingt zu klären

Diese Punkte sind nicht durch die aktuelle Fragerunde entschieden und blockieren
nur die jeweils betroffenen Sonderfälle:

| Thema | Noch benötigte Angabe | Begrenzte Abhängigkeit |
| --- | --- | --- |
| Teilmonats-Wochenenden / Rest von F10 | Volle oder andere Quote; zählt volle Beschäftigung am Wochenende oder schon zeitliche Überschneidung? | Nur Wochenendquoten bei betroffenen Ein-/Austritten. Sonntag als Monatsbesitzer ist bereits entschieden. |
| LB-Personen | Welche beiden Personen übernehmen den konkreten LB-Termin bzw. die gewünschte feste Reihe? | Normale Kalender-/Personeneingabe; keine neue Frage zum 14-Tage-Rhythmus oder Ankerdatum. |
| Teilnahme-Ziel / Rest von F13 | Welchen relativen Optimierungsrang hat freiwillige T-/TS-Teilnahme gegenüber Wünschen und Stunden? | Nur konkurrierende weiche Ziele. Der freiwillige Charakter ist entschieden. |
| Geldbewertung / F01 | Welche konkrete zeitgültige Tarif-/BV-Zuordnung, Einzelraten und Kumulation gelten? | Nur die betroffenen Rechts-/Tarifnachweise und Eurobeträge. Kein allgemeiner Blocker für Urlaub oder lokale Planung. R zählt für die Arbeitszeit bereits normal. |

## Weitere bereits bestätigte Regeln

- V2 ist die Standardanwendung und kein zusätzlicher Prüfbereich.
- Monatssoll nach Wochenstunden × Kalendertagen ÷ 7, ohne Vier-Wochen-Pauschale.
  Zeitgültige Vertragswerte werden tagweise exakt berücksichtigt und einmal am
  Monatsende auf Minuten gerundet. Diese Formel nicht erneut zur Wahl stellen.
- Ganzjährig zwei WL und ein BK pro Woche; niemals BK und WL am selben Startdatum.
  Die vorhandene ISO-Wochenauswahl ist eine bedienbare Einstellung und keine neue
  Pflichtfrage vor jeder manuellen Zuordnung.
- Vertragsstundenbezogene faire Anteile, Schutz von Personen mit weniger
  Freiwünschen und Ausgleich bereits übergangener Wünsche anhand bestätigter
  Historie ohne Doppelzählung.
- Manuelle Änderungen und Importe dürfen fachliche Regeln nach Warnung übergehen,
  auch Donnerstagswünsche. Technisch ungültige Angaben werden dadurch nicht
  teilweise aktiv übernommen oder zu definierten Daten.
- Monatsbestätigung trotz Regelverletzungen und offener Plätze nach Warnung;
  Abweichungen unveränderlich dokumentieren, bestehende Historie nicht umschreiben.
- Elf Stunden Ruhe, maximal fünf tatsächliche Arbeitstage, zwei freie Wochenenden
  und vorherige zusammenhängende freie Tage bleiben festgelegt. Offene Randdaten
  sind von diesen Regeln getrennt zu kennzeichnen.
- T/TS freiwillig; festgelegte Ersatzblöcke und LB-TS-Verlängerung bleiben erhalten.
- Europe/Vienna, Nachtfenster 22:00–06:00 und österreichischer nationaler
  Feiertagskalender sind entschieden. Nicht erneut nach Land oder Zeitzone fragen.

Beschäftigung, Vertragsversionen, Ausschlüsse, Führerscheinstatus und konkrete
TS-/VN-/INT-/N17-/FK-Termine samt Personen sind normale Eingaben. Sie sollen direkt
in verständlichen Formularen erfassbar sein. S0/M0/M1/E0 sind technische
Profilbezeichnungen, keine Voraussetzung dafür, die Bedienoberfläche zu verstehen.

## Quellen und rechtliche Einordnung

Frühere Abrufe der KV-/BV-Primärquellen waren mit CONNECT 403 gesperrt. Ein
vorbereiteter Netzwerkentwurf ist kein Nachweis eines gelesenen Dokuments.
Originalfassungen, Wirksamkeit, Fundstellen und konkrete Anwendbarkeit müssen vor
entsprechenden Rechts-/Euroaussagen belegt werden. Diese fehlenden Belege verhindern
nicht die Umsetzung der ausdrücklich bestätigten Urlaubs- und Planungsregeln.

Offene Entscheidung, noch fehlende Eingabe und noch nicht vollständig
implementierte Funktion sind verschiedene Dinge. Maßgeblich für tatsächliche
Testergebnisse und native Pakete bleiben die aktuellen Prüfberichte.
