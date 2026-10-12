# Plattformen und Paketierung

Stand der Prüfung: 12. Oktober 2026. Die Versionen sind in den Anforderungsdateien festgelegt. Eine Änderung der Abhängigkeiten benötigt einen erneuten Build und Funktionstest.

| Komponente | Gewählte Version | Geprüfte Hersteller-/PyPI-Metadaten |
| --- | --- | --- |
| Python | 3.12 | Gemeinsame unterstützte Python-Version aller verwendeten Pakete. |
| PySide6-Essentials | 6.12.0 | Python ≥3.10 und <3.16; macOS ≥14 als universal2; Windows x64 und ARM64. |
| OR-Tools | 9.15.6755 | Python ≥3.9; Python-3.12-Wheels für Windows x64, macOS Intel ≥10.15 und Apple Silicon ≥11. |
| PyInstaller | 6.22.3 | Python ≥3.8 und <3.16; native Bootloader für Windows und macOS Intel/Apple Silicon. |

Damit stehen für macOS Sequoia 15 sowohl Intel- als auch Apple-Silicon-Abhängigkeiten zur Verfügung. Für Windows wird ein x64-Paket vorgesehen. Die offizielle Qt-6.12-Plattformtabelle nennt Windows 10 ab Version 1809 sowie Windows 11 auf x86_64. Qt 6.12 ist laut dieser Tabelle die letzte Qt-Version mit Windows-10-Unterstützung. Windows auf ARM wird hier nicht als natives Ziel unterstützt, weil OR-Tools in dieser Version keinen Windows-ARM64-Wheel anbietet. Die Ausführung eines x64-Pakets unter Emulation wurde nicht geprüft.

Die Prüfung der angebotenen Artefakte und Herstellerquellen ersetzt keinen Starttest auf dem Betriebssystem. Windows 10/11 x64 und macOS Sequoia sind die vorgesehenen Ziele; die tatsächlich durchgeführten Tests und Größen stehen in der README. Die gerenderten Qt-/PyInstaller-/GitHub-Dokumentationsseiten antworteten in dieser Cloud-Umgebung mit HTTP 403. Deshalb wurden die offiziellen Dokumentationsquellen über `raw.githubusercontent.com` geprüft.

## Offizielle Quellen

Die folgenden PyPI-JSON-Antworten wurden mit aktivierter TLS-Prüfung abgerufen. Insbesondere die Python-Bedingungen und Dateinamen sind nachprüfbar:

- [PySide6-Essentials 6.12.0](https://pypi.org/pypi/PySide6-Essentials/6.12.0/json)
- [OR-Tools 9.15.6755](https://pypi.org/pypi/ortools/9.15.6755/json)
- [PyInstaller 6.22.3](https://pypi.org/pypi/pyinstaller/6.22.3/json)

Zusätzlich geprüft wurden diese offiziellen Dokumentationsquellen:

- [Qt-6.12-Plattformtabelle](https://raw.githubusercontent.com/qt/qtdoc/6.12/doc/src/platforms/supported-platforms.qdocinc): Windows-Mindestversion, macOS-Architekturen und Unterstützung ab der jeweiligen Mindestversion.
- [PyInstaller 6.22.3 README](https://raw.githubusercontent.com/pyinstaller/pyinstaller/v6.22.3/README.rst): Python 3.8–3.15 und native Erstellung statt Cross-Kompilierung.
- [GitHub-Runner-Images](https://raw.githubusercontent.com/actions/runner-images/main/README.md): `macos-15` auf ARM64 und `macos-15-intel` auf x64.

Weiterführende Herstellerdokumentation (gerenderte Seiten):

- [Unterstützte Qt-Plattformen](https://doc.qt.io/qt-6/supported-platforms.html)
- [PyInstaller-Dokumentation](https://pyinstaller.org/en/stable/)
- [GitHub-gehostete Runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

## Native Erstellung und Größe

PyInstaller verpackt die Anwendung einschließlich Python, Qt und OR-Tools. Auf Windows entsteht ein Ordner mit `Dienstplan.exe`, auf macOS ein `Dienstplan.app`-Paket. Es werden jeweils native Pakete auf dem jeweiligen Zielsystem erstellt. Ein Linux-Build ist kein Windows- oder macOS-Build. Intel und Apple Silicon erhalten getrennte macOS-Pakete, passend zum verwendeten Python/OR-Tools-Wheel.

Das Werkzeug verwendet `onedir` statt `onefile`: Das Programm muss nicht bei jedem Start in einen temporären Ordner entpackt werden. Qt Widgets benötigt nur PySide6-Essentials. WebEngine, QML, Multimedia und ungenutzte OR-Tools-Schnittstellen werden ausgeschlossen; die erforderlichen CP-SAT-, NumPy- und Pandas-Abhängigkeiten bleiben enthalten. Weitere Kürzungen müssen durch einen Test des gebauten Programms abgesichert werden.

Auf Linux werden über PyInstallers unterstütztes `--strip` unnötige Debugsymbole entfernt, sofern das native `strip`-Werkzeug verfügbar ist. `--no-strip` erhält sie für Diagnosebuilds. Windows und macOS verwenden diese Kürzung nicht. `build-report.json` dokumentiert mit `stripped`, ob sie tatsächlich angewendet wurde; die gemessenen Größen beziehen sich jeweils auf den erzeugten Build. Der Funktionstest des fertigen Pakets muss auch nach dieser Kürzung bestehen.

`python scripts/build.py` misst die tatsächliche unkomprimierte Paketgröße und speichert Betriebssystem, Architektur und Bytes in `dist/build-report.json`. Es erstellt außerdem ein ZIP für Windows oder ein TAR.GZ für macOS/Linux und misst dessen Downloadgröße getrennt. Der gesamte erzeugte Ordner beziehungsweise das `.app`-Paket muss weitergegeben werden. Das TAR.GZ erhält Unix-Ausführungsrechte und Symlinks; im GitHub-Workflow werden diese fertigen Archive hochgeladen statt einzelner `.app`-Dateien.

Die Workflow-Datei erstellt native Prüfartefakte für Windows x64 sowie macOS Sequoia auf Intel und Apple Silicon. Das Vorhandensein der Workflow-Datei bedeutet noch keinen ausgeführten oder bestandenen CI-Lauf. Die Pakete sind zunächst unsigniert. Für eine öffentliche Auslieferung können Authenticode unter Windows sowie Developer-ID-Signatur und Notarisierung unter macOS ergänzt werden; dafür werden eigene Zertifikate benötigt.
