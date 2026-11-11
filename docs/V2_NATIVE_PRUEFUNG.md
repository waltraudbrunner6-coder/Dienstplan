# Dienstplan 0.4.4 – Monatsbestätigung trotz Abweichungen

Stand 11.11.2026. Programm-/Testcommit **90a67d6**. Windows x64, macOS Sequoia ARM64 und Intel: Testsuite, Paketbuild und Prüfung des gebauten Programms erfolgreich.

[Prüflauf 42931888956](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42931888956). Rohdaten: `examples/v2/native-pruefung.json`; voriger 0.4.3-Nachweis: `examples/v2/native-0-4-3.json`. Nachfolgende reine Nachweiscommits ändern den geprüften Programm-/Testcode nicht.

## Downloads

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42931888956/artifacts/13817191611)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42931888956/artifacts/13817142253)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42931888956/artifacts/13816423194)

Alte App schließen und neue Archive vollständig entpacken. Windows: vollständigen Dienstplan-Ordner behalten und darin die EXE öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges App-Bundle behalten. Im Fenster muss **Version 0.4.4 · Build 90a67d6** stehen. Python und Terminal sind nicht erforderlich. Bestehende Monatsdatei weiterverwenden.

## Bedienung und Nachweise

- „Monat bestätigen“ zeigt Regelverstöße, offene Plätze, Stundenabweichungen und ungeprüfte Regeln. Mit „Ja“ wird dieser Stand trotz der Hinweise unveränderlich bestätigt; „Nein“ lässt den Monat unverändert.
- Bestätigungs-Snapshots speichern ausdrückliche Übersteuerung, Regelmeldungen, offene Plätze und weitere Hinweise. Die Oberfläche zeigt „MONAT BESTÄTIGT MIT ABWEICHUNGEN“ auch nach Neustart.
- Widersprüchliche bestätigte Randwochen dürfen nach ausdrücklicher Zustimmung eingefroren werden; die älteren Bestätigungen bleiben unverändert.
- Wiederholtes Bestätigen zählt Historie nicht doppelt. Revisionsschutz, Fingerprints, Unveränderlichkeit und Transaktionen bleiben erhalten. Technisch widersprüchliche Kennungen oder undefinierte Rechenwerte werden nicht erfunden.
- Lokaler Gesamtlauf: **441 bestanden in 284,52 s**. Zusätzlicher Bestätigungsnachlauf einschließlich Qt-Neustart: **4 bestanden in 1,24 s**. Native Jobs führten dieselbe Testsuite, Build und Programm-Selbsttests erfolgreich aus. Keine Testanforderung abgeschwächt.

## Tatsächlich gemessene Paketgrößen

| Plattform | Native Archivgröße | Entpacktes Programm |
| --- | ---: | ---: |
| Darwin arm64 | 64,248,462 Bytes / 61.27 MiB | 181,316,178 Bytes / 172.92 MiB |
| Windows AMD64 | 87,415,840 Bytes / 83.37 MiB | 241,352,032 Bytes / 230.17 MiB |
| Darwin x86_64 | 71,031,964 Bytes / 67.74 MiB | 187,827,125 Bytes / 179.13 MiB |

Die GitHub-Artifact-Hülle kann durch zusätzliche Kompression eine andere Downloadgröße haben. Plattform-/Pythonversionen und Bytewerte sind im Rohbericht gespeichert.

Automatisierte native Qt-Prüfung, keine vollständige manuelle Bedienabnahme jeder Eingabekombination. Pakete sind nicht signiert/notarisiert. Die Bestätigung eines abweichenden Plans erklärt ihn nicht für regelkonform; offene betriebliche Rechts-/Tarifprofile bleiben offen. Keine echte Benutzerdatenbank geöffnet oder verändert; bestehende Bestätigungsdaten bleiben lesbar.
