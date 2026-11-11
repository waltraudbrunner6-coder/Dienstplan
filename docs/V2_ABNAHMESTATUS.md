# V2 – Zuordnung aller 125 Abnahmefälle

## Verbindliche Regelüberlagerung 11.11.2026 – Nutzerantworten für 0.5.0

Die Nutzerantworten konkretisieren die betroffenen Eingaben/Erwartungen im
[Abnahmekatalog](V2_ABNAHMETESTS.md). **Sie sind kein Testresultat.** Die 125 IDs
bleiben vollständig zugeordnet. Aktuelle Befehle, Resultate und tatsächlich
gebaute native Pakete werden ausschließlich im [Fortschritt](V2_FORTSCHRITT.md)
und im [nativen Prüfbericht](V2_NATIVE_PRUEFUNG.md) nachgewiesen.

- U01/I01 bleiben Legacy-Kompatibilitätsfälle mit unveränderten bereits expliziten
  Teilmengen. U05 prüft neue U-Eingaben: jeder markierte Kalendertag, auch
  Wochenende/Feiertag, zählt einmal mit gültigem W/5. Fehlende alte Tagesmengen
  erhalten eine konkrete Korrekturhilfe statt einer angenommenen Nullgutschrift.
- Das Urlaubskonto sammelt zwei Tage je vollem Beschäftigungsmonat mit explizitem
  Anfangsbestand und Kontostart. Teilmonate erwerben exakt `2 × Beschäftigungstage /
  Kalendertage des Monats`; fehlende historische Verbrauchsmonate bleiben als
  unbekannt gekennzeichnet. Kein erfundener Übertrag oder vorzeitiges Abrunden.
- Z07 verlangt im Standard keine Pausenvertretung: gleichzeitige Pausen sind
  erlaubt. Strengere explizite CoverageRule-Tests sind zusätzliche technische
  Profile und keine betriebliche Standardanforderung.
- R zählt als normale Arbeit. KC15 ist der sichtbare Ein-Personen-Ersatz für das
  Paar KC10/KC16, 15:00–00:00 mit 30-min-Pause; vollständige reguläre Besetzung
  wird bevorzugt. LB-Rhythmus ab 03.12.2026 und KCT10 bis 17:30 am 31.12. sind geklärt.
- FK ist ein Einzeltermin ohne automatische Wiederholung. Die enge Freitags-W17-
  Ausnahme gilt jetzt auch für Wochenend-Freiwünsche, siehe W10.
- Freie Wochenenden gehören zum Sonntagsmonat. S0 ist die bestätigte
  Kalendertage-Sollrechnung, M1 die bestätigte Startmonatsbuchung. Alte bestätigte
  M0-Werte und physische Kalender-/Nacht-/Feiertagssegmente werden nicht umgeschrieben.
- Manuelle/Import-Übersteuerung und Bestätigung trotz dokumentierter Abweichungen
  gelten weiter. Eine solche Bestätigung macht keinen Regeltest nachträglich grün.

Zugehörige neue/erweiterte Testdateien: `test_v2_leave.py`,
`test_v2_leave_accounts.py`, `test_v2_leave_repair.py`, `test_v2_absence_ui.py`,
`test_v2_term_dialog.py`, `test_v2_catalog_entries.py`, `test_v2_fallback.py` und
`test_v2_month_booking.py`. Die Nennung belegt den Prüfumfang, **nicht** die
ungeprüfte Aussage, dass jeder dort vorgesehene Integrations-/Produktfall bestanden sei.

Folgeauftrag 0.4.0: Tabellenimport/-export, Monatsmatrix, automatische manuelle
Pausen und ausdrücklich konfigurierte 2-WL-/1-BK-Wochen ergänzt. Neue separate
Regressionen stehen im Fortschritt; die 125 Fälle werden dadurch nicht pauschal
als bestanden eingestuft. Die folgenden älteren Etappenberichte bleiben als Verlauf erhalten; die aktuelle
Regelüberlagerung oben ersetzt ihre inzwischen beantworteten Fachfragen.

Aktualisierung 10.11.2026: Die V2-Hauptoberfläche ersetzt auf ausdrücklichen Auftrag die alte UI (Version 0.3.0). Ausschlussauswahl, Stundenanzeige, dauerhafte Arbeitsstände und automatisch erzeugte Standard-Tagesmuster sind ergänzt. Dies stuft keine offenen Profil-, Team-/Vertretungs-, Migrations- oder Abrechnungsfälle pauschal auf „bestanden“ hoch; die 125 Einzelfallzuordnungen bleiben bestehen. Aktuelle zusätzliche Regressionen und Grenzen: [Fortschritt](V2_FORTSCHRITT.md).

Historische Einordnung 10.11.2026, mit der datierten Überlagerung oben. Die folgenden Angaben präzisieren die Etappenübersicht. Ein grüner
pytest-Lauf bedeutet **nicht**, dass alle 125 Produktfälle bestanden sind.
„Vollständig als Fachfunktion“ bezieht sich ausschließlich auf die angegebene reine
Regel/Rechnung beziehungsweise das explizite Testprofil, nicht auf Produkt-/KV-Freigabe.
„Teilweise“ nennt vorhandene Teilprüfungen und die noch fehlende Integration/Freigabe.
Die verlinkten Dateien enthalten die relevanten Tests; Prüfungszahlen und tatsächlich
ausgeführte Plattformläufe stehen in [V2_FORTSCHRITT.md](V2_FORTSCHRITT.md).

**Aktuelle Zuordnungszählung:** 125 eindeutige Fall-IDs; 95 als „Teilweise“, 30 als „Vollständig als Fachfunktion/Testprofil“. Diese Kategorien sind keine Anzahl bestandener aktueller pytest- oder Produktabnahmen. R16 ist wegen des geänderten Sonntags-Monatsfalls bewusst nicht mehr aus dem alten Vier-Paare-Test als vollständig abgeleitet.

## D

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_validation.py](../tests/test_v2_validation.py), [test_v2_team_integration.py](../tests/test_v2_team_integration.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| D01 | Teilweise | Reguläre Katalogprüfung vorhanden; neuer KC15-Ersatz mit geändertem Bedarf wird gesondert in test_v2_fallback.py geprüft. Kein zusätzlicher D13-Fall und keine pauschale Monatsfreigabe. |
| D02 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D03 | Vollständig als Fachfunktion/Testprofil | Gemeinsame CP-SAT-Zwölferinstanz: vier operative Plätze plus acht T-Blöcke, genau 3465 Arbeitsminuten, zwölf einmalige Erfüllungen. |
| D04 | Vollständig als Fachfunktion/Testprofil | Gemeinsame CP-SAT-Zwölferinstanz: vier operative T-/TS-Ausnahmen plus acht TS-Blöcke; keine doppelte Zeit/Teilnahme. |
| D05 | Teilweise | Manuell vorgegebener November-LB bleibt technischer Legacy-Einzelfall; neuer automatischer Rhythmus beginnt 03.12.2026, siehe Q09. |
| D06 | Teilweise | LB-/TS-Kombiblock wird als technische Funktion geprüft; Novemberbeispiel entscheidet keinen neuen Rhythmusanker. |
| D07 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D08 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D09 | Teilweise | Fehlende Teilnahme als einzelnes Ziel vorhanden; konkrete TS-Gesamtinstanz noch separat zu prüfen. |
| D10 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D11 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D12 | Teilweise | FK ist ausdrücklich ein Einzeltermin. Konkrete Zeiten/Person und Stunden bleiben zu prüfen; keine ungeklärte Wiederholungsfrage oder automatische Monatskopie mehr. |

## P

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| P01 | Teilweise | Domain/Rechte/Sollanteile geprüft; produktive Profilzuordnung nicht freigegeben. |
| P02 | Teilweise | Domain/Rechte/Sollanteile geprüft; produktive Profilzuordnung nicht freigegeben. |
| P03 | Teilweise | Domain/Rechte/Sollanteile geprüft; produktive Profilzuordnung nicht freigegeben. |
| P04 | Teilweise | Domain/Rechte/Sollanteile geprüft; produktive Profilzuordnung nicht freigegeben. |
| P05 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| P06 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| P07 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| P08 | Teilweise | Domain/Rechte/Sollanteile geprüft; produktive Profilzuordnung nicht freigegeben. |

## R

Prüfbelege: [test_v2_validation.py](../tests/test_v2_validation.py), [test_v2_calendar_rules.py](../tests/test_v2_calendar_rules.py), [test_v2_foundation.py](../tests/test_v2_foundation.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| R01 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R02 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R03 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R04 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R05 | Teilweise | Einzelregeln mit Rand-/Testprofilen geprüft; kein vollständiger Rechtsnachweis. |
| R06 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R07 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R08 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R09 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R10 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R11 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R12 | Teilweise | Einzelregeln mit Rand-/Testprofilen geprüft; kein vollständiger Rechtsnachweis. |
| R13 | Teilweise | Einzelregeln mit Rand-/Testprofilen geprüft; kein vollständiger Rechtsnachweis. |
| R14 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R15 | Teilweise | Einzelregeln mit Rand-/Testprofilen geprüft; kein vollständiger Rechtsnachweis. |
| R16 | Teilweise | Neue Sonntagszuordnung ist geklärt: November hat fünf zugeordnete Paare inklusive 31.10./01.11. Neuer Monats-/Randnachweis darf nicht aus dem alten Vier-Paare-Beispiel behauptet werden. |
| R17 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |

## Q

Prüfbelege: [test_v2_calendar_rules.py](../tests/test_v2_calendar_rules.py), [test_v2_coupled.py](../tests/test_v2_coupled.py), [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| Q01 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q02 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q03 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q04 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q05 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q06 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q07 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |
| Q08 | Teilweise | Dienstag-vor-Sonntag-Test vorhanden; ausschließlich zulässiger Sonntag und erklärter Präferenzgrund noch kein eigener Integrationstest. |
| Q09 | Teilweise | LB-Anker 03.12.2026 geklärt; Dezember 03./17./31. und Jänner 14./28.; zwei feste Personen als Eingabe. Alte andere Anker bleiben benannte technische Tests, keine neue Vorgabe. |
| Q10 | Teilweise | R ist bestätigte normale Arbeit (früh 360/spät 450 Minuten); Perioden-/Startmonats-/Fixierungsintegration bleibt gesondert nachzuweisen, keine fehlende F02-Bewertung mehr erfinden. |
| Q11 | Teilweise | Ganzjährig 2 WL/1 BK und BK/WL-Starttagsausschluss geklärt; konkrete Wochenprofil-/Fixierungs-/Randinstanz anhand aktueller Tests prüfen, keine pauschale Monatsfreigabe. |

## U

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_validation.py](../tests/test_v2_validation.py), [test_v2_workspace_export.py](../tests/test_v2_workspace_export.py), [test_v2_team_integration.py](../tests/test_v2_team_integration.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| U01 | Teilweise | Legacy-Kompatibilität: vorhandene explizite Fünf-Tage-Teilmenge erhalten; keine rückwirkende Gutschrift von sieben Tagen. Neue U-Eingabe unter U05. |
| U02 | Teilweise | Donnerstagsurlaub ist zulässig; Tagesgutschrift gültiges W/5 geklärt. Eigenständige Integration bleibt anhand aktueller Tests nachzuweisen. |
| U03 | Teilweise | Person-/Datum-Deduplizierung und Vereinigung bleiben erforderlich; neues Anspruchskonto darf Verbrauch und gespeicherte Monatskopien nicht doppeln. |
| U04 | Vollständig als Fachfunktion/Testprofil | Exakte vorgegebene Tagesmenge: zweimal 37/5 plus dreimal 30/5 Stunden = 1968 Minuten, zeitgültige Vertragsversionen. |
| U05 | Teilweise | Neue Regel geklärt: jeder markierte U-Tag wird einschließlich Wochenende/Feiertag angerechnet. Alte fehlende Tagesmengen korrigierbar; neue Oberfläche/Import und Speicherung gesondert prüfen. |
| U06 | Teilweise | Gutschrifttag muss weiter in Beschäftigung und Urlaub liegen; die neue U-Regel erzeugt keine fiktiven Vertrags- oder Beschäftigungstage. |
| U07 | Teilweise | Urlaubskonflikt wird unabhängig erkannt; automatische Planung bleibt streng, ausdrückliche manuelle/Import-/Bestätigungsübersteuerung erlaubt und dokumentiert. |

## W

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_persistence.py](../tests/test_v2_persistence.py), [test_v2_ui.py](../tests/test_v2_ui.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| W01 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W02 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W03 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W04 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W05 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W06 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W07 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W08 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W09 | Teilweise | Wunschidentität, Budget, atomare Korrektur und eingefrorene Statistik bleiben zu prüfen. Schutz kleiner Wunschgruppen und ausdrückliche Übersteuerung sind bereits entschieden; keine erneute pauschale F11/F12/F13-Sperre. |
| W10 | Teilweise | Freitags-W17-Ausnahme für Wochenend-Freiwünsche jetzt ausdrücklich bestätigt; neue Standardbewertung und alte explizit strengere Profile getrennt prüfen, keine rückwirkende Historienänderung. |

## I

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_persistence.py](../tests/test_v2_persistence.py), [test_v2_ui.py](../tests/test_v2_ui.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| I01 | Teilweise | Legacy-Format-2-Zeile mit expliziter Teilmenge erhalten; neue U-Zeilen erhalten gemäß U05 ihre markierten Daten, keine pauschale Umdeutung alter Fakten. |
| I02 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |
| I03 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |
| I04 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |
| I05 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |
| I06 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |

## Z

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_coupled.py](../tests/test_v2_coupled.py), [test_v2_objectives.py](../tests/test_v2_objectives.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| Z01 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z02 | Teilweise | Arbeits-/Pausenmengen bleiben zu prüfen; R ist normale Arbeit, KC15 hat 510 Arbeitsminuten. Fehlendes betriebliches Abdeckungsprofil ist hierfür kein pauschaler Blocker mehr. |
| Z03 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z04 | Teilweise | Frühe Pause bleibt weiches Ziel bei ansonsten gleicher höherer Qualität; gleichzeitige Pausen sind nicht pauschal verboten. |
| Z05 | Teilweise | Geschützte T-Zeit und tatsächliche Arbeitssegmente weiterhin prüfen; erlaubte gleichzeitige Pausen heben die konkrete Team-Erfüllung nicht auf. |
| Z06 | Teilweise | LB-/TS-Arbeitssegmente und geschützte Teilnahme weiterhin prüfen; kein zusätzlicher allgemeiner Vertretungszwang. |
| Z07 | Teilweise | Standardregel geändert: gleichzeitige Pausen erlaubt. Strenge CoverageRule-Regressionen bleiben ausdrücklich separate technische Profiltests, keine behauptete Betriebsvorgabe. |
| Z08 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z09 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z10 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z11 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |

## K

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py), [test_v2_objectives.py](../tests/test_v2_objectives.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| K01 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K02 | Teilweise | S0-Kalendertage-Soll und M1-Startmonatsbuchung fachlich geklärt; alte M0-Stände bleiben unverändert. Aktueller kombinierter Konto-/Buchungsnachweis erforderlich. |
| K03 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K04 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K05 | Teilweise | Gültiges W/5 plus S0 ist geklärt; Urlaubskonto/Anfangsbestand und M1-Zeitbuchung als integrierten aktuellen Stand prüfen, keine doppelte Sollminderung. |
| K06 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K07 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K08 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K09 | Teilweise | Negative rechnerische Arbeitsziele und Nullstunden bleiben ausdrücklich zu behandeln; kein erfundenes negatives Arbeitspensum oder Division durch null. |

## L

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| L01 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L02 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L03 | Teilweise | Physische April-/Mai-Segmente unverändert; M1 bucht alle 450 Arbeitsminuten im April, M0 bleibt Legacy-Vergleich. Tarif-/Eurofreigabe folgt daraus nicht. |
| L04 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L05 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L06 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |

## H

Prüfbelege: [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py), [test_v2_objectives.py](../tests/test_v2_objectives.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| H01 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |
| H02 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |
| H03 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |
| H04 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |
| H05 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |
| H06 | Teilweise | Bestätigte Rohhistorie, unveränderte damalige Anteile und Doppelzählungsschutz bleiben aktuell nachzuweisen. Vertragliche Fairness und Schutz kleiner Wunschgruppen sind entschieden; bloße Testprofile ersetzen keinen kombinierten Monatsnachweis. |

## M

Prüfbelege: [test_v2_persistence.py](../tests/test_v2_persistence.py), [test_v2_workspace_export.py](../tests/test_v2_workspace_export.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| M01 | Teilweise | Synthetische Kopien/Originalschutz geprüft; keine echte Migration oder Stichtagsübernahme. |
| M02 | Teilweise | Synthetische Kopien/Originalschutz geprüft; keine echte Migration oder Stichtagsübernahme. |
| M03 | Teilweise | Synthetische Kopien/Originalschutz geprüft; keine echte Migration oder Stichtagsübernahme. |
| M04 | Teilweise | Synthetische Kopien/Originalschutz geprüft; keine echte Migration oder Stichtagsübernahme. |
| M05 | Teilweise | Rohdaten bytegleich erhalten, keine Umdeutung; typisierte neue Legacy-Hard-Block-Ansicht noch nicht vollständig. |
| M06 | Teilweise | Synthetische Kopien/Originalschutz geprüft; keine echte Migration oder Stichtagsübernahme. |
| M07 | Teilweise | Legacy-Leser/Alt-App erhalten; neues integriertes V2-Archiv mit Legacy-Export noch nicht vollständig. |
| M08 | Teilweise | Kontowerte/Schema-3-Schreibschutz geprüft; produktiver Stichtag F14 und echte Übernahme ausdrücklich nicht beauftragt. |

## O

Prüfbelege: [test_v2_solver.py](../tests/test_v2_solver.py), [test_v2_objectives.py](../tests/test_v2_objectives.py), [test_v2_validation.py](../tests/test_v2_validation.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| O01 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O02 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O03 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O04 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O05 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O06 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O07 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |
| O08 | Teilweise | Reproduzierbare 5/20/60-s-Läufe mit gleichem Incumbent vorhanden, aber nur vier WL-Testtermine; kein Betriebsbenchmark. |
| O09 | Teilweise | Kleine Modelle, direkte Prüfung und benannte Testziele; kein großer produktiver Monatsbenchmark. |

## X

Prüfbelege: [test_v2_ui.py](../tests/test_v2_ui.py), [test_v2_workspace_export.py](../tests/test_v2_workspace_export.py), [test_v2_package_check.py](../tests/test_v2_package_check.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| X01 | Teilweise | Reguläre Desktop-Oberfläche, Kalender-/Namensauswahl und zugängliche Hinweise vorhanden; übersteuerbare Abweichungen sind keine bestandene Konformitätsabnahme. |
| X02 | Teilweise | Deutsche Hauptoberfläche und Exporte werden erweitert geprüft; keine zusätzliche Testoberfläche als Ersatz der eigentlichen Anwendung. |
| X03 | Teilweise | Arbeitsstände/Korrekturen und bestätigte Historie bleiben zu prüfen; neue Urlaubs-/Terminauswahl ist gesonderte UI-Regression, keine pauschale Produktfreigabe. |
| X04 | Teilweise | Drei Testmonate/Bestätigungen/Salden/Historie vorhanden; zusammenhängende R-/Randwochen-/Urlaubs-/Vertragswechsel-Gesamtinstanz noch offen. |
| X05 | Teilweise | Native automatisierte Starts/Qt/SQLite/Solver/tzdata werden je Commit im Fortschritt belegt; echte OS-Netzabschaltung, manuelle Bedienung, Signierung/Notarisierung offen. |

## Keine vorgetäuschte Fertigstellung

Offene Abnahmeanteile bleiben offen; es wurden keine Tests entfernt, übersprungen
oder Erwartungen auf Grund eines schlechteren Ergebnisses abgeschwächt.
Die technische Zielskalierung wurde anhand eines reproduzierten Gegenbeispiels
von 100 auf 1000 verfeinert. Fehlende Gutschrifttage sind keine bestätigte Null.
Bereits beantwortete Fragen sind nicht erneut als Blocker zu behandeln. Offen bleiben
unter anderem eine gesonderte Teilmonatsquote für freie Wochenenden, gegebenenfalls
fehlende Althistorie und konkrete Rechts-/Tarifzuordnung für entsprechende Nachweise; normale Urlaubserfassung
und Dienstplanung werden dadurch nicht pauschal blockiert. Eine Rechts-/Tarifzuordnung
kann nicht aus Dienstkürzeln oder einem erfolgreichen Test folgen.

### Nutzerergänzung 10.11.2026 – ausdrückliche Regelübersteuerung

Für manuelle Änderungen und CSV-/Excel-Importe ist die bisher zwingende Ablehnung
fachlicher Regelverletzungen durch eine ausdrückliche, standardmäßig verneinte
Warnbestätigung ersetzt. Unabhängige Prüfung, Status nach Neustart und Exporte
weisen die Abweichungen weiter aus. Kein bestandener Konformitätsnachweis für
einen solchen Entwurf. Technisch ungültige Eingaben bleiben atomar gesperrt.
Synthetische Regressionen: `test_v2_overrides.py` und `test_v2_ui.py`.
Dies erklärt die neue Erwartung bei den bisherigen Ablehnungsprüfungen; die
Regeln des automatischen Solvers und unveränderliche Historie bleiben erhalten.

### Nutzerergänzung 11.11.2026 – Bestätigung mit Abweichungen

Ab 0.4.4 können Regelverletzungen und offene Plätze ausdrücklich bestätigt werden.
Die unabhängige Prüfung bleibt streng; die Bestätigung friert die gemeldeten
Abweichungen ein und stellt keinen bestandenen Konformitätstest dar. Neue
Regressionen prüfen Ablehnen/Zustimmen, Speicher-Rundlauf und Qt-Neustart,
Unveränderlichkeit, Idempotenz, Transaktionsfehler und bestätigte Randwochen.
Gesamtlauf: 441 Tests bestanden. Dies erklärt die neue Ausnahme zu früheren
Ablehnungsfällen und erklärt nicht den vollständigen V2-Abnahmekatalog für bestanden.
