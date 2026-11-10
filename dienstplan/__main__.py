"""Eintrittspunkt für Quellcode und das eigenständig startbare Paket."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

def main(argv=None):
    parser = argparse.ArgumentParser(description="Lokale deutsche Monatsdienstplanung")
    parser.add_argument("--database", type=Path, help="Abweichende lokale SQLite-Datei")
    parser.add_argument("--demo", action="store_true", help="Zwölf-Personen-Demonstrationsmonat öffnen")
    parser.add_argument("--self-test", action="store_true", help="Lokalen Funktionstest ohne Benutzereingaben ausführen")
    parser.add_argument("--self-test-v2", action="store_true", help="Paketierten V2-Prüfbereich mit Testprofilen prüfen")
    parser.add_argument("--self-test-report", type=Path, help="JSON-Bericht des Selbsttests speichern")
    parser.add_argument("--year", type=int, default=None, help="Jahr des Startmonats")
    parser.add_argument("--month", type=int, default=None, help="Startmonat (1–12)")
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--v2',action='store_true',help='Getrennten V2-Prüfbereich direkt öffnen')
    mode.add_argument('--legacy',action='store_true',help='Bisherige Anwendung direkt öffnen')
    args = parser.parse_args(argv)
    if args.v2 and (args.database or args.demo or args.year is not None or args.month is not None):
        parser.error('--v2 verwendet getrennte Testdateien; Datei und Monat im V2-Prüfbereich wählen.')
    if args.self_test_v2:
        from .v2.smoke import run
        return run(args.self_test_report)
    if args.self_test:
        from .smoke import run_smoke_test
        return run_smoke_test(args.self_test_report)
    from PySide6.QtCore import QLibraryInfo, QLocale, QStandardPaths, QTranslator
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication(sys.argv[:1])
    QLocale.setDefault(QLocale("de_DE"))
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_de", translations): app.installTranslator(translator)
    app._dienstplan_translator = translator
    app.setApplicationName("Dienstplan"); app.setOrganizationName("Dienstplan")
    # Zuerst wählen; insbesondere vor dem Öffnen/Anlegen einer Legacy-Datei.
    legacy_options=args.legacy or args.database or args.demo or args.year is not None or args.month is not None
    if args.v2:selection='v2'
    elif legacy_options:selection='legacy'
    else:
        from .startup import choose_start_mode
        selection=choose_start_mode()
    if selection is None:return 0
    if selection=='v2':
        try:
            from .v2.ui import Workbench
            window=Workbench();window.show()
            return app.exec()
        except Exception as exc:
            QMessageBox.critical(None,'V2-Prüfbereich konnte nicht gestartet werden',f'Bitte Installation und temporären Speicherort prüfen.\n{exc}')
            return 1
    from .storage import Store
    from .ui import MainWindow
    if args.database:
        database = args.database
    else:
        base = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        database = base / "dienstplan.sqlite3"
    store = None
    try:
        database.parent.mkdir(parents=True, exist_ok=True)
        store = Store(database)
        data = None
        if args.demo:
            from .demo import demo_month
            year, month = args.year or 2026, args.month or 11
            data = store.load_month(year, month) or demo_month(year, month)
        window = MainWindow(store, args.year, args.month, data=data)
        window.show()
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None, "Dienstplan konnte nicht gestartet werden", f"Bitte den Speicherort und die Installation prüfen.\n{exc}")
        return 1
    finally:
        if store is not None:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
