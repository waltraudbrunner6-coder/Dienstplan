# Dienstplan 0.3.0 – native Pakete der neuen Hauptoberfläche

Stand 10.11.2026. **Neue Downloads mit ausschließlich der V2-Hauptanwendung.**
Der normale Start öffnet dauerhaft gespeicherte Monatsdaten, keine Startauswahl
und keinen zusätzlichen Vier-Termine-Testbereich.

## Aktuelle Downloads

[Run 42830290050](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050) des Programm-/Testcommits **4035132** ist vollständig
**erfolgreich**. Alle drei nativen Jobs führten Testsuite, Paketbuild und die neue
Paketprobe erfolgreich aus. Lokal sind **362 Tests bestanden**. Nachfolgende reine
Dokumentationscommits ändern diesen geprüften Programm-/Teststand nicht.

- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050/artifacts/13770774528)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050/artifacts/13770438683)
- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42830290050/artifacts/13770423434)

Alte App schließen, das aktuelle Archiv in einen neuen Ordner entpacken und die
enthaltene App/EXE öffnen. Im Fenster müssen **Dienstplan V2 · Version 0.3.0** und
**Build 4035132** stehen. Unter Windows den vollständigen Programmordner behalten;
macOS ARM64 ist für Apple Silicon, x64 für Intel. Python und Terminal sind nicht nötig.
Archive mit anderen Commitkennungen gehören zu früheren Programmständen.

Der vollständige Standardkatalog enthält 17 Kürzel/19 Varianten. Neue Monate
enthalten die bestimmten Tagesmuster automatisch: November 2026 hat ohne
Sonderdienste 94 Termine, 120 operative Plätze und 876,00 h Bedarf. Eine neue Datei
beginnt ohne erfundene Personen. Frühere `dienstplan.sqlite3`-Benutzerdaten bleiben
unverändert; bisherige V2-Dateien lassen sich über „Datei öffnen“ laden.

## Tatsächlich gemessene Größen

Rohdaten, Betriebssysteme, Commit, Paketproben und Artefaktlinks:
[native-pruefung.json](../examples/v2/native-pruefung.json).

| System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB | Paketprüfung |
| --- | --- | ---: | ---: | ---: | --- |
| macOS Sequoia 15.7.9 | x86_64 | 187.223.795 | 178.55 | 67.20 | bestanden |
| macOS Sequoia 15.8.2 | arm64 | 180.712.848 | 172.34 | 60.73 | bestanden |
| Windows 10.0.26100 | AMD64 | 240.752.674 | 229.60 | 82.83 | bestanden |

Die native Paketprobe verlangt sichtbare Hauptoberfläche, Standarddienste,
Ausschlussliste, Stundenanzeige und persistenten Neustart. Zusätzlich prüft sie
Wiener DST, paketiertes tzdata ohne System-Zeitzonenpfad, CP-SAT/Prüfer, SQLite und
konsistenten Export anhand einer isolierten synthetischen Zwölf-Personen-Fixture
mit acht Zuteilungen. Das ist ausdrücklich kein Vollmonats-/Rechtsnachweis.
Die echten Einstiegstests öffnen die Hauptoberfläche mit Qt-Ereignisloop und prüfen,
dass eine synthetische Altdatei unverändert bleibt. Ein Legacy-Paketbericht reicht
für den neuen Pakettest nicht mehr aus.

Linux x86_64/Python 3.12.14: zusätzlich tatsächlich gebaut und geprüft,
**294.024.047 Bytes / 280,40 MiB**, TAR.GZ **114.309.689 Bytes / 109,01 MiB**.
Buildkennung stimmt mit dem sauberen Commit überein; keine SQLite-Benutzerdatenbank
im Paket gefunden. Ignorierter Ausgabeordner `dist-v2/`, keine Binärdateien im Git.
Linux ist ein gesonderter Nachweis und ersetzt keine native Prüfung.

## Grenzen und frühere Pakete

Alle Pakete sind **unsigniert**, ohne Notarisierung. Automatisierte native
Offscreen-Prüfungen sind keine vollständige manuelle Endgeräteabnahme; OS-weite
Netzabschaltung wurde nicht geprüft. Der Oberflächenauftrag ersetzt keine offenen
Fachantworten: insbesondere keine Rechts-/KV-/BV-/Tarifprofile, Reservebewertung,
Pausenabdeckung oder WL/BK-Wochenregeln erfinden. Das technische Rechenprofil muss
vor der Planung ausdrücklich gewählt werden. Feste Sondertermine brauchen
weiterhin tatsächliche Datums-/Personenangaben.

Frühere Downloads mit Startauswahl sind als historische Belege unter
[historischer Paketstand 32e3732](V2_NATIVE_STARTAUSWAHL_HISTORISCH.md) und
[native-startauswahl.json](../examples/v2/native-startauswahl.json) erhalten.
Sie sind nicht die aktuellen Downloads.

[Bedienungsanleitung](V2_BEDIENUNG.md), [Fortschritt](V2_FORTSCHRITT.md),
[offene Fachentscheidungen](V2_OFFENE_FRAGEN.md), [Abnahmestatus](V2_ABNAHMESTATUS.md).
