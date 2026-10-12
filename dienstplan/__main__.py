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
    parser.add_argument("--self-test-report", type=Path, help="JSON-Bericht des Selbsttests speichern")
    parser.add_argument("--year", type=int, default=None, help="Jahr des Startmonats")
    parser.add_argument("--month", type=int, default=None, help="Startmonat (1–12)")
    args = parser.parse_args(argv)
    if args.self_test:
        from .smoke import run_smoke_test
        return run_smoke_test(args.self_test_report)
    from PySide6.QtCore import QLibraryInfo, QLocale, QStandardPaths, QTranslator
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .storage import Store
    from .ui import MainWindow
    app = QApplication.instance() or QApplication(sys.argv[:1])
    QLocale.setDefault(QLocale("de_DE"))
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_de", translations): app.installTranslator(translator)
    app._dienstplan_translator = translator
    app.setApplicationName("Dienstplan"); app.setOrganizationName("Dienstplan")
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
