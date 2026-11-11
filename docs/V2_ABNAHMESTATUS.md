# V2 – Zuordnung aller 125 Abnahmefälle

Folgeauftrag 0.4.0: Tabellenimport/-export, Monatsmatrix, automatische manuelle
Pausen und ausdrücklich konfigurierte 2-WL-/1-BK-Wochen ergänzt. Neue separate
Regressionen stehen im Fortschritt; die 125 Fälle werden dadurch nicht pauschal
als bestanden eingestuft. Ungeklärte Excel-Kürzel, Donnerstagsausnahmen und
Randwochenstandard sowie offene Produktprofile bleiben ausdrücklich offen.

Aktualisierung 10.11.2026: Die V2-Hauptoberfläche ersetzt auf ausdrücklichen Auftrag die alte UI (Version 0.3.0). Ausschlussauswahl, Stundenanzeige, dauerhafte Arbeitsstände und automatisch erzeugte Standard-Tagesmuster sind ergänzt. Dies stuft keine offenen Profil-, Team-/Vertretungs-, Migrations- oder Abrechnungsfälle pauschal auf „bestanden“ hoch; die 125 Einzelfallzuordnungen bleiben bestehen. Aktuelle zusätzliche Regressionen und Grenzen: [Fortschritt](V2_FORTSCHRITT.md).

Stand 10.11.2026. Die folgenden Angaben präzisieren die Etappenübersicht. Ein grüner
pytest-Lauf bedeutet **nicht**, dass alle 125 Produktfälle bestanden sind.
„Vollständig als Fachfunktion“ bezieht sich ausschließlich auf die angegebene reine
Regel/Rechnung beziehungsweise das explizite Testprofil, nicht auf Produkt-/KV-Freigabe.
„Teilweise“ nennt vorhandene Teilprüfungen und die noch fehlende Integration/Freigabe.
Die verlinkten Dateien enthalten die relevanten Tests; Prüfungszahlen und tatsächlich
ausgeführte Plattformläufe stehen in [V2_FORTSCHRITT.md](V2_FORTSCHRITT.md).

## D

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_validation.py](../tests/test_v2_validation.py), [test_v2_team_integration.py](../tests/test_v2_team_integration.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| D01 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D02 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D03 | Vollständig als Fachfunktion/Testprofil | Gemeinsame CP-SAT-Zwölferinstanz: vier operative Plätze plus acht T-Blöcke, genau 3465 Arbeitsminuten, zwölf einmalige Erfüllungen. |
| D04 | Vollständig als Fachfunktion/Testprofil | Gemeinsame CP-SAT-Zwölferinstanz: vier operative T-/TS-Ausnahmen plus acht TS-Blöcke; keine doppelte Zeit/Teilnahme. |
| D05 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D06 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D07 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D08 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D09 | Teilweise | Fehlende Teilnahme als einzelnes Ziel vorhanden; konkrete TS-Gesamtinstanz noch separat zu prüfen. |
| D10 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D11 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |
| D12 | Teilweise | Katalog-/Teilnahmefunktion und Kernprüfung vorhanden; keine vollständige betriebliche Monatsinstanz abgenommen. |

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
| R16 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| R17 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |

## Q

Prüfbelege: [test_v2_calendar_rules.py](../tests/test_v2_calendar_rules.py), [test_v2_coupled.py](../tests/test_v2_coupled.py), [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| Q01 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q02 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q03 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q04 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q05 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q06 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q07 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q08 | Teilweise | Dienstag-vor-Sonntag-Test vorhanden; ausschließlich zulässiger Sonntag und erklärter Präferenzgrund noch kein eigener Integrationstest. |
| Q09 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q10 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |
| Q11 | Teilweise | Parametrisierte Quoten/Kandidaten und kleine Modelle; F02/F06/F07/F08/F09 nicht produktiv entschieden. |

## U

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_validation.py](../tests/test_v2_validation.py), [test_v2_workspace_export.py](../tests/test_v2_workspace_export.py), [test_v2_team_integration.py](../tests/test_v2_team_integration.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| U01 | Teilweise | Abwesenheit/Gutschrift-/Korrekturteil geprüft; anrechenbare betriebliche Tagesmenge F05 separat. |
| U02 | Teilweise | Abwesenheit/Gutschrift-/Korrekturteil geprüft; anrechenbare betriebliche Tagesmenge F05 separat. |
| U03 | Teilweise | Abwesenheit/Gutschrift-/Korrekturteil geprüft; anrechenbare betriebliche Tagesmenge F05 separat. |
| U04 | Vollständig als Fachfunktion/Testprofil | Exakte vorgegebene Tagesmenge: zweimal 37/5 plus dreimal 30/5 Stunden = 1968 Minuten, zeitgültige Vertragsversionen. |
| U05 | Teilweise | Fehlende Gutschrifttage ausdrücklich ungeklärt, Bestätigung/Stundenoptimierung blockiert; keine Nullgutschrift angenommen. Betrieblicher Tagesvorschlag F05 offen. |
| U06 | Teilweise | Abwesenheit/Gutschrift-/Korrekturteil geprüft; anrechenbare betriebliche Tagesmenge F05 separat. |
| U07 | Teilweise | Abwesenheit/Gutschrift-/Korrekturteil geprüft; anrechenbare betriebliche Tagesmenge F05 separat. |

## W

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_persistence.py](../tests/test_v2_persistence.py), [test_v2_ui.py](../tests/test_v2_ui.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| W01 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W02 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W03 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W04 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W05 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W06 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W07 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W08 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W09 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |
| W10 | Teilweise | Domain, Korrektur, Statistik und Testprofile geprüft; F11/F12/F13 bleiben offen. |

## I

Prüfbelege: [test_v2_catalog_entries.py](../tests/test_v2_catalog_entries.py), [test_v2_persistence.py](../tests/test_v2_persistence.py), [test_v2_ui.py](../tests/test_v2_ui.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| I01 | Teilweise | Format-2-Import und atomare Aktivierung geprüft; produktive Freigabe nicht abgeleitet. |
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
| Z02 | Teilweise | Konkrete Arbeits-/Pausenmengen geprüft; produktives Abdeckungsprofil F03 fehlt. |
| Z03 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z04 | Teilweise | Konkrete Arbeits-/Pausenmengen geprüft; produktives Abdeckungsprofil F03 fehlt. |
| Z05 | Teilweise | Konkrete Arbeits-/Pausenmengen geprüft; produktives Abdeckungsprofil F03 fehlt. |
| Z06 | Teilweise | Konkrete Arbeits-/Pausenmengen geprüft; produktives Abdeckungsprofil F03 fehlt. |
| Z07 | Teilweise | Konkrete Arbeits-/Pausenmengen geprüft; produktives Abdeckungsprofil F03 fehlt. |
| Z08 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z09 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z10 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| Z11 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |

## K

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py), [test_v2_objectives.py](../tests/test_v2_objectives.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| K01 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K02 | Teilweise | Exakte Rechenfunktionen mit ausdrücklich S0/M0; produktives Soll-/Buchungsprofil F04 fehlt. |
| K03 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K04 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K05 | Teilweise | Exakte Rechenfunktionen mit ausdrücklich S0/M0; produktives Soll-/Buchungsprofil F04 fehlt. |
| K06 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K07 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K08 | Vollständig als Fachfunktion/Testprofil | Genaue Einzelregel/Rechnung geprüft; betrieblicher Gesamtplan wird damit nicht freigegeben. |
| K09 | Teilweise | Exakte Rechenfunktionen mit ausdrücklich S0/M0; produktives Soll-/Buchungsprofil F04 fehlt. |

## L

Prüfbelege: [test_v2_foundation.py](../tests/test_v2_foundation.py), [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| L01 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L02 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L03 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L04 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L05 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |
| L06 | Teilweise | Technische Kalender-/Mengen-/synthetische Einzelratenprüfung; Primärquellen/KV/BV nicht verifiziert. |

## H

Prüfbelege: [test_v2_history_reporting.py](../tests/test_v2_history_reporting.py), [test_v2_objectives.py](../tests/test_v2_objectives.py).

| ID | Abdeckung | Grenze / nächster Nachweis |
| --- | --- | --- |
| H01 | Teilweise | Unveränderliche Testhistorie und Optimierungsprofile geprüft; produktiver F12-Zeitraum/Maßstab offen. |
| H02 | Teilweise | Unveränderliche Testhistorie und Optimierungsprofile geprüft; produktiver F12-Zeitraum/Maßstab offen. |
| H03 | Teilweise | Unveränderliche Testhistorie und Optimierungsprofile geprüft; produktiver F12-Zeitraum/Maßstab offen. |
| H04 | Teilweise | Unveränderliche Testhistorie und Optimierungsprofile geprüft; produktiver F12-Zeitraum/Maßstab offen. |
| H05 | Teilweise | Berechtigte 1:2-Sollanteile geprüft; genaue Drei-Einsätze-Optimierung und alle Teilbeschäftigungsvarianten noch kein vollständiger eigener Fall. |
| H06 | Teilweise | Unveränderliche Testhistorie und Optimierungsprofile geprüft; produktiver F12-Zeitraum/Maßstab offen. |

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
| X01 | Teilweise | Technischer Qt-Prüfbereich/Export vorhanden; vollständige Produktabnahme offen. |
| X02 | Teilweise | Technischer Qt-Prüfbereich/Export vorhanden; vollständige Produktabnahme offen. |
| X03 | Teilweise | Technischer Qt-Prüfbereich/Export vorhanden; vollständige Produktabnahme offen. |
| X04 | Teilweise | Drei Testmonate/Bestätigungen/Salden/Historie vorhanden; zusammenhängende R-/Randwochen-/Urlaubs-/Vertragswechsel-Gesamtinstanz noch offen. |
| X05 | Teilweise | Native automatisierte Starts/Qt/SQLite/Solver/tzdata werden je Commit im Fortschritt belegt; echte OS-Netzabschaltung, manuelle Bedienung, Signierung/Notarisierung offen. |

## Keine vorgetäuschte Fertigstellung

Offene Abnahmeanteile bleiben offen; es wurden keine Tests entfernt, übersprungen
oder Erwartungen auf Grund eines schlechteren Ergebnisses abgeschwächt.
Die technische Zielskalierung wurde anhand eines reproduzierten Gegenbeispiels
von 100 auf 1000 verfeinert. Fehlende Gutschrifttage sind keine bestätigte Null.
Vor Produktbetrieb sind F01–F14 einschließlich Stichtag/Anwendbarkeit zu klären; eine
konkrete Zuordnung kann nicht aus Dienstkürzeln oder einem erfolgreichen Test folgen.

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
