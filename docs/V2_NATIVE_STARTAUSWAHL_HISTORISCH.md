# Historischer Paketstand 32e3732 – Startauswahl

Stand 10.11.2026. **Aktualisierte Pakete mit Startauswahl und Buildkennung.**
V2 bleibt ein technischer Prüfbereich, keine produktive V2-Freigabe.

## Historische Downloads (vor der einzigen V2-Hauptoberfläche)

[Run 42821811250](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42821811250) des Commits `32e3732` ist vollständig
**erfolgreich**. Alle drei nativen Jobs führten die 339-Test-Suite, den Paketbuild
sowie Legacy- und V2-Paketselbsttest erfolgreich aus. Der Pakettest verlangt jetzt
auch die Startauswahl und eine eingebettete Buildkennung, die zum Buildbericht
passt. Nachfolgende Dokumentationscommits ändern diesen Programm-/Testcode nicht.

- [Dienstplan-macOS-Sequoia-arm64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42821811250/artifacts/13767622250)
- [Dienstplan-Windows-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42821811250/artifacts/13766927836)
- [Dienstplan-macOS-Sequoia-x64](https://github.com/waltraudbrunner6-coder/Dienstplan/actions/runs/42821811250/artifacts/13766618743)

Die inneren Archive tragen `32e3732` im Dateinamen. Bisherige Anwendung vollständig
beenden, das neue Paket in einen eigenen Ordner entpacken und die darin enthaltene
App/EXE öffnen. Beim normalen Start erscheint **Dienstplan – Startauswahl**.
Für die neuen Funktionen **V2-Prüfbereich öffnen** wählen. In beiden Bereichen
muss **Build 32e3732** sichtbar sein. Unter Windows den vollständigen Programmordner,
auf dem Mac das gesamte App-Bundle behalten; Python/Terminal sind nicht erforderlich.

## Warum die bisherigen Pakete wie die alte Version aussahen

Die bisherigen Pakete enthielten den neuen V2-Code, starteten aber direkt in der
bisherigen Vier-Schichten-Oberfläche. V2 war nur über einen Menüeintrag erreichbar.
Das war für Nutzer*innen zu wenig erkennbar. Eine automatische produktive
Umschaltung und echte Datenmigration waren ausdrücklich nicht beauftragt.

Der neue Startdialog trennt beide Bereiche sichtbar. Die bisherige App hat
zusätzlich eine V2-Schaltfläche, ein reguläres Bereiche-Menü und einen eindeutigen
Fenstertitel. Die gespeicherten bisherigen Daten liegen im lokalen Benutzerkonto
außerhalb des Programmpakets; ein Paketwechsel löscht sie nicht. V2 öffnet diese
Datei nicht automatisch. Alte Daten wurden nicht als neue Beispieldaten gebündelt
oder ungefragt nach V2 übernommen. Der V2-Startdatensatz enthält zwölf fiktive
Personen und vier WL-Testtermine; der Dienstkatalog umfasst 17 Kürzel. Das ist
weiterhin kein fertig konfigurierter betrieblicher Monatsplan.

## Gemessene native Paketgrößen

Rohdaten mit OS/Architektur, Commit, Bytegrößen, Start-/Selbsttestergebnissen und
Artefaktlinks: [native-pruefung.json](../examples/v2/native-pruefung.json).
Vorherige Pakete ohne Startauswahl bleiben als historische Belege in
[native-vor-startauswahl.json](../examples/v2/native-vor-startauswahl.json) erhalten.

| Tatsächliches System | Architektur | Unkomprimiert Bytes | MiB | Archiv MiB | Paketprüfung |
| --- | --- | ---: | ---: | ---: | --- |
| Windows-Runner 10.0.26100 | AMD64 | 240.737.771 | 229,59 | 82,82 | bestanden |
| macOS Sequoia 15.7.9 | x86_64 | 187.208.588 | 178,54 | 67,19 | bestanden |
| macOS Sequoia 15.8.2 | arm64 | 180.697.641 | 172,33 | 60,72 | bestanden |

Python der nativen Läufe: 3.12.10. Paketprüfung: Startauswahl, Buildkennung,
Wien-DST, tzdata 2026.6 / IANA 2026f, CP-SAT/Prüfer, SQLite-Workspace, konsistentes
ZIP und sichtbare Qt-Widgets. Legacy-Test: zwölf Personen/186 Zuteilungen;
V2-Test: zwölf Personen/acht Zuteilungen im synthetischen Vier-Termine-Datensatz.
Die Startregression verwendet einen echten Qt-Ereignisloop und belegt, dass die
Auswahl von V2 die synthetische bisherige Datenbank weder öffnet noch verändert.

## Zusätzlich gebautes Linux-Paket

Gleicher Programmstand `32e3732`, Linux x86_64/Python 3.12.14: tatsächlich
**294.009.248 Bytes / 280.39 MiB**, TAR.GZ
**114.292.159 Bytes / 109.00 MiB**.
Beide Paketselbsttests bestanden; die Buildkennung stimmt mit dem Buildbericht
überein. Im Paket wurde keine SQLite-Benutzerdatenbank gefunden. Ausgabe im
ignorierten `dist-v2/`; keine Binärdateien im Git. Linux ersetzt keinen nativen
Windows-/Mac-Nachweis.

## Grenzen

Alle Pakete sind **unsigniert**, keine Notarisierung behauptet. Qt wurde auf den
nativen Runnern automatisiert/offscreen gestartet. Vollständige manuelle Bedienabnahme
auf Endgeräten und OS-weite Netzabschaltung wurden nicht durchgeführt. S0/M0/E0/Q0
und synthetische Bestätigungen sind keine KV-/BV-, Abrechnungs- oder Produktfreigabe.
Weitere Grenzen: [Abnahmestatus](V2_ABNAHMESTATUS.md).

Der frühere Windows-Exportflush und der einmal auf Intel gescheiterte Zwei-Sekunden-
Wunschzähltest sind in [V2_FORTSCHRITT.md](V2_FORTSCHRITT.md) samt Korrektur belegt.
Der aktuelle Lauf prüft diese unveränderten Fachbedingungen ebenfalls erfolgreich.
Mess- und Fehlerannotationen wurden über die reguläre erlaubte GitHub-API gelesen.

```sh
python scripts/v2_native_report.py --run RUN_ID --output NEUER_BERICHT.json
```
