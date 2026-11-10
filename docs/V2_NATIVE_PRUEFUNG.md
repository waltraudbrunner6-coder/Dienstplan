# Dienstplan 0.3.0 – native Pakete der neuen Hauptoberfläche

Der neue Programmeinstieg ersetzt die frühere Startauswahl vollständig. Er öffnet
sofort die dauerhafte V2-Monatsanwendung mit Standarddiensten, Dienstausschlüssen
und Stundenanzeige. Frühere Downloads gehören zu einem anderen Programmstand:
[historische Pakete mit Startauswahl](V2_NATIVE_STARTAUSWAHL_HISTORISCH.md).

Die aktualisierte native Windows-/macOS-Matrix wird nach den **362 bestandenen
lokalen Tests** neu ausgeführt. Neue Downloadlinks und gemessene Paketgrößen
werden erst nach tatsächlich erfolgreichen Builds und Paketproben eingetragen.
Die bisherigen Artefaktlinks sind kein Nachweis dieser Oberfläche.

Die neue Paketprobe verlangt die sichtbare Hauptoberfläche mit 19 Standardvarianten,
94 Novemberterminen, Ausschlussliste, Stundenanzeige und persistentem Neustart.
Die Rechenkette prüft zusätzlich Wiener DST, Offline-tzdata, CP-SAT/Prüfer, SQLite
und konsistentes Exportpaket anhand temporärer synthetischer Daten. Sie startet
keine zweite Benutzeroberfläche und akzeptiert keinen Legacy-Selbsttestbericht.

Alle Pakete bleiben unsigniert. Automatisierte native Offscreen-Prüfungen sind
keine vollständige manuelle Abnahme; ein Linux-Build beweist keinen Windows-/
macOS-Start. Offene Rechts-, KV-/BV-, Reserve- und Abrechnungsprofile bleiben
separat offen. [Bedienung](V2_BEDIENUNG.md), [Fortschritt](V2_FORTSCHRITT.md).
