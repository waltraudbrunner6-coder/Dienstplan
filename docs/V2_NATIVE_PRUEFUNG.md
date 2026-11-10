# Dienstplan 0.3.1 – Pakete mit sofort sichtbarer Dienstplanvorschau

Stand 10.11.2026. Die Anzeigekorrektur ist in den folgenden Paketen enthalten.
Berechnete Vorschläge öffnen jetzt sofort den Reiter **Dienstplan** mit Namen,
Zuteilungen und offenen Plätzen. Stunden, Verteilung und Wünsche zeigen denselben
Vorschlag. **Ergebnis übernehmen** speichert ihn dauerhaft; bis dahin bleibt der
vorherige Plan erhalten. Verwerfen stellt dessen Anzeige wieder her. Exportiert
wird der gerade sichtbare Vorschlag.

## Aktuelle Downloads

[Run 42870257885](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885) des Programm-/Testcommits **bbb6909** ist vollständig
**erfolgreich**. Alle drei nativen Jobs führten Testsuite, Paketbuild und
Paketprobe erfolgreich aus. Lokal: **368 bestandene Tests**. Nachfolgende reine
Dokumentationscommits ändern diesen geprüften Programm-/Teststand nicht.

- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885/artifacts/13790395890)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885/artifacts/13789896584)
- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42870257885/artifacts/13789292461)

Alte App schließen und neues Paket in einen eigenen Ordner entpacken. Im Fenster
müssen **Version 0.3.1 · Build bbb6909** stehen. Unter Windows den vollständigen
Ordner behalten; Mac ARM64 ist für Apple Silicon, x64 für Intel. Python und
Terminal sind nicht nötig. Bestehende V2-Dateien bleiben direkt ladbar, die
bisherige Altdatei wird nicht verändert. Einen zuvor nicht übernommenen Vorschlag
nach dem Neustart erneut berechnen und anschließend ausdrücklich übernehmen.

In Version 0.3.0 war der Vorschlag erst nach **Ergebnis übernehmen** sichtbar.
Die Korrektur ändert Anzeige und Vorschauablauf, keine fachlichen Planungsregeln.
Standardkatalog, automatische Tagesmuster und weiterhin offene Sonderangaben
bleiben bestehen.

## Gemessene Paketgrößen und Nachweis

Rohdaten: [native-pruefung.json](../examples/v2/native-pruefung.json).

| System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB | Paketprobe |
| --- | --- | ---: | ---: | ---: | --- |
| macOS Sequoia 15.8.2 | arm64 | 180722575 | 172.35 | 60.74 | bestanden |
| Windows 10.0.26100 | AMD64 | 240762514 | 229.61 | 82.84 | bestanden |
| macOS Sequoia 15.7.9 | x86_64 | 187233522 | 178.56 | 67.21 | bestanden |

Die native Paketprobe verlangt zusätzlich **vorschau_anzeige=true**: echte
Qt-Hauptoberfläche, Tabwechsel und sichtbare zugeteilte Personen vor dem
Übernahmeklick, danach Speichern in SQLite. Sie prüft außerdem Standarddienste,
Ausschlüsse, Stundenanzeige, persistenten Neustart, Wiener DST mit paketiertem
tzdata bei leerem System-Zeitzonenpfad, CP-SAT/Prüfer und Export. Rechenkette und
Vorschau werden mit einer isolierten synthetischen Zwölf-Personen-Fixture mit
acht Zuteilungen geprüft; dies ist kein betrieblicher Vollmonats-/Rechtsnachweis.
Die Regressionen prüfen auch den unveränderten vorherigen Plan, verworfene,
veraltete, ungültige, unvollständige und leere Ergebnisse und den Vorschau-Export.

Linux x86_64 zusätzlich gebaut und geprüft: **294.033.766 Bytes / 280,41 MiB**,
Archiv **114.297.571 Bytes / 109,00 MiB**. Saubere Buildkennung bbb6909, neue
Paketprobe vollständig bestanden. Linux ersetzt keinen nativen Nachweis.

## Grenzen und frühere Belege

Pakete sind unsigniert und nicht notarisiert. Native automatisierte
Offscreen-Prüfungen sind keine vollständige manuelle Endgeräteabnahme. OS-weite
Netzabschaltung wurde nicht geprüft. Offene KV-/BV-/Rechts-, Reserve-, Pausen- und
Abrechnungsprofile werden durch die Anzeigekorrektur nicht entschieden.

Die früheren erfolgreichen Pakete 0.3.0 sind als historischer Nachweis in
[native-0-3-0.json](../examples/v2/native-0-3-0.json) erhalten; Pakete mit alter
Startauswahl in [native-startauswahl.json](../examples/v2/native-startauswahl.json).
Aktuelle Downloads stehen ausschließlich oben.

[Bedienungsanleitung](V2_BEDIENUNG.md), [Fortschritt](V2_FORTSCHRITT.md),
[offene Entscheidungen](V2_OFFENE_FRAGEN.md), [Abnahmestatus](V2_ABNAHMESTATUS.md).
