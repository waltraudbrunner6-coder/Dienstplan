# Bedienprüfung und Korrekturen 0.4.3

Stand 11.11.2026. Die Prüfung verwendet synthetische Personen und normale
Monatsdaten einschließlich Import und gespeicherter SQLite-Datei. Keine echte
Benutzerdatenbank wurde geöffnet oder verändert.

## Behobene Ursachen

Die bisherige manuelle Bearbeitung rief bei fehlendem Wochenprofil
`configure_weekly()` auf. Der Dialog änderte damit den gesamten Monatskontext,
obwohl nur eine Person zugeordnet werden sollte. Manuelle Änderungen benötigen
jetzt kein Wochenprofil; die vorhandenen konkreten Termine bleiben erhalten.
Ein Wochenprofil wird über die eigene BK/WL-Schaltfläche oder vor der ersten
automatischen Planung ausgewählt.

Bei fixierten Importzuteilungen wird nach ausdrücklicher Bestätigung die alte
Fixierung auf die neue Person übertragen bzw. gemeinsam mit der Zuteilung
entfernt. Zurückbleibende alte Fixierungen werden nicht neu erzeugt. Die Auswahl
derselben Person ist eine unveränderte Rückkehr; konkrete Pausen bleiben erhalten.
Eine bereits für denselben Termin ausgewählte Person belegt keinen zweiten Platz.
Andere Personen bleiben einschließlich nicht passender Berechtigungen auswählbar;
fachliche Konflikte benötigen wie bisher die ausdrückliche Regelübersteuerung.

Die explizite Wochenkonfiguration erhält bestehende Zuteilungen. Zusätzliche
benötigte BK/WL-Termine bleiben offen. Bereits vorhandene Datumsoptionen bleiben
innerhalb der gewählten Quoten für spätere Optimierungen frei. Eine Dateikopie
übernimmt keine offene Vorschau oder Korrekturvormerkung aus der Quelldatei als
scheinbar aktive Bearbeitung; deren gespeicherter Korrekturstapel bleibt dort
bestehen.

## Geprüfte Bedienwege

| Bereich | Nachweis |
| --- | --- |
| Importierter Monat ohne Wochenprofil → Person ändern | `test_v2_workflows.py`: echte Schaltfläche, nur Personenauswahl, übriger Plan unverändert |
| Fixierte Person ändern/entfernen, Fixieren und Lösen | Eindeutige neue Fixierung, unabhängiger Prüfer, SQLite-Rundlauf |
| Abbruch/gleiche Person | Daten, Pause und Eingaberevision unverändert |
| Zwei Besetzungsplätze | Bereits für denselben Termin zugeteilte Person kein zweites Mal auswählbar |
| Bereits gewählte BK/WL-Daten | Beim manuellen Bearbeiten unverändert, Datumsoptionen nicht still fixiert |
| BK/WL ausdrücklich konfigurieren | Zuteilungen erhalten, Quoten geprüft, spätere Datumsoptimierung möglich |
| Speichern, Kopieren, Datei öffnen, Monat wechseln/zurück | Zusammenhängender Ablauf mit demselben importierten Plan |
| Excel und technisches Exportpaket | Derselbe sichtbare Stand, JSON-Rundlauf und Monatsmatrix |
| Korrekturvormerkung bei Dateikopie | Kein alter In-Memory-Stapel in der neuen Datei; Quelle unverändert |
| Berechnung, Zeitlimit, Abbruch und Ergebnisvorschau | Bestehende Solver-/Qt-Regressionen; keine stille Übernahme |
| Termine ergänzen/entfernen, Reimport | Bestehende 0.4.2-Regressionen einschließlich Schreibfehler/Neustart |
| Personen, Wochenstunden, Vertragsversionen und Ausschlüsse | Bestehende Personen-, Stunden- und Qt-Regressionen |
| CSV/XLSX-Fehler, Duplikate und Wunschbearbeitung | Bestehende Import-, Speicher- und Korrekturstapelprüfungen |
| Bestätigte Monate und Historie | Bestehende Tests für Unveränderlichkeit, Rundlauf und Doppelzählung |

Der Paket-Selbsttest bedient zusätzlich die echte normale Monatsoberfläche:
zuordnen → fixieren → Person ändern → entfernen, ohne ein BK/WL-Fenster zu öffnen.
`manual_assignment=true` ist jetzt ein verpflichtender Paketnachweis.

Dies ist eine automatisierte Prüfung der dokumentierten Bedienwege, keine
vollständige manuelle Prüfung jeder Eingabekombination und keine betriebliche
Rechts-/Tariffreigabe. Ergebnisse und native Downloads stehen in
`V2_FORTSCHRITT.md` und `V2_NATIVE_PRUEFUNG.md`. Fachlich noch ungeklärte Profile
bleiben offen; Schutzprüfungen und Tests wurden nicht abgeschwächt.
