# Dienstplan 0.4.1 – ausdrückliche Regelübersteuerung

Stand 10.11.2026. Programm-/Testcommit **72b168a**. Alle drei nativen Ziele haben Testsuite, Paketbuild und Paket-Selbsttests erfolgreich abgeschlossen.

[Prüflauf 42912433306](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42912433306). Rohdaten: `examples/v2/native-pruefung.json`; vorheriger 0.4.0-Nachweis: `examples/v2/native-0-4-0.json`.

## Downloads

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42912433306/artifacts/13808880595)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42912433306/artifacts/13808362177)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42912433306/artifacts/13807473117)

Alle Archive vollständig entpacken. Windows: vollständigen Dienstplan-Ordner behalten und darin die EXE öffnen. macOS: ARM64 für Apple Silicon, x64 für Intel; vollständiges App-Bundle behalten. Im Fenster muss **Version 0.4.1 · Build 72b168a** stehen. Python und Terminal werden nicht benötigt.

## Tatsächlich gemessene Paketgrößen

| Plattform | Native Archivgröße | Entpacktes Programm |
| --- | ---: | ---: |
| Windows AMD64 | 87,404,107 Bytes / 83.36 MiB | 241,328,800 Bytes / 230.15 MiB |
| Darwin arm64 | 64,243,921 Bytes / 61.27 MiB | 181,292,829 Bytes / 172.89 MiB |
| Darwin x86_64 | 71,018,750 Bytes / 67.73 MiB | 187,803,776 Bytes / 179.10 MiB |

Die GitHub-Artifact-Hülle kann durch zusätzliche Kompression eine andere Downloadgröße haben. Alle Builds: Python 3.12.10; Windows 10.0.26100, macOS Sequoia 15.8.2 (ARM64) und 15.7.9 (Intel).

## Bedienung und Prüfungen

- Manuelle Zuteilung: alle vorhandenen Personen auswählbar; bei Regelverstößen ausdrückliche Warnung mit Ja/Nein. Nein verändert den bisherigen Plan nicht.
- XLSX-/CSV-Tabellenimport: Checkbox „Regeln für diesen Import übergehen“, anschließend Warnung bestätigen. CSV-Format-2-Wünsche und manuell vorgemerkte Abwesenheiten unterstützen ebenfalls eine ausdrückliche Übernahme.
- Regelmeldungen bleiben im gespeicherten Monatsstand sowie in Excel- und technischen Exporten erhalten. Unbekannte IDs, nicht definierte Zeiten/Kürzel und beschädigte Daten bleiben technisch zu korrigieren.
- Der unabhängige Prüfer bleibt streng; übersteuerte Pläne erhalten keinen Konformitäts- oder Optimalitätsnachweis. Automatische Solverregeln werden nicht gelockert.
- Lokal: vollständige Testsuite **411 bestanden in 146,61 s**; abschließende Qt-/Ausnahmeregression **26 bestanden in 17,48 s**. Native Jobs führen dieselbe Testsuite sowie echte Builds und gebaute Programm-Selbsttests aus.

Automatisierte native Qt-Prüfung, keine vollständige manuelle Bedienabnahme. Pakete sind nicht signiert/notarisiert. Keine Rechts-/Tariffreigabe durch synthetische Tests. Keine echte Benutzerdatenbank geöffnet oder migriert. Frühere Monatsdateien ohne Ausnahmefelder bleiben lesbar.

Die vorbereiteten Importdateien liegen auf ausdrücklichen Nutzerwunsch unter `examples/importvorlagen-2026/` im Repository. Hochgeladene Originaldateien wurden nicht übernommen. Fachlich noch undefinierte KC15-/R-/U-Angaben werden durch die Ausnahmefunktion nicht erfunden. Donnerstagswünsche und abweichende bekannte Dienstvarianten können nun ausdrücklich übernommen werden.
