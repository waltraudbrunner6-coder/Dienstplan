"""Einziger Programmeinstieg: die dauerhaft gespeicherte Monatsoberfläche."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description='Lokale deutsche Monatsdienstplanung')
    parser.add_argument('--database',type=Path,help='Abweichende lokale Dienstplandatei (V2-Format)')
    parser.add_argument('--demo',action='store_true',help='Standardmonat mit zwölf ausdrücklich fiktiven Personen anlegen')
    parser.add_argument('--self-test',action='store_true',help='Paketfunktionstest ohne Benutzerdaten ausführen')
    parser.add_argument('--self-test-v2',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--self-test-report',type=Path,help='JSON-Bericht des Selbsttests speichern')
    parser.add_argument('--year',type=int,help='Jahr des Startmonats')
    parser.add_argument('--month',type=int,help='Startmonat (1–12)')
    parser.add_argument('--v2',action='store_true',help=argparse.SUPPRESS)  # kompatibler Alias, keine zweite Oberfläche
    args=parser.parse_args(argv)
    if args.month is not None and not 1<=args.month<=12:parser.error('Monat muss zwischen 1 und 12 liegen.')
    if args.self_test or args.self_test_v2:
        from .v2.smoke import run
        return run(args.self_test_report)
    from PySide6.QtCore import QLibraryInfo,QLocale,QStandardPaths,QTranslator
    from PySide6.QtWidgets import QApplication,QMessageBox
    app=QApplication.instance() or QApplication(sys.argv[:1])
    QLocale.setDefault(QLocale('de_DE'))
    translator=QTranslator(app)
    translations=QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load('qtbase_de',translations):app.installTranslator(translator)
    app._dienstplan_translator=translator
    app.setApplicationName('Dienstplan');app.setOrganizationName('Dienstplan')
    window=None
    try:
        from .v2.ui import Workbench
        initial=None
        if args.demo:
            from .v2.application import demonstration_month
            initial=demonstration_month(args.year or 2026,args.month or 11)
        database=args.database
        if args.demo and database is None:
            base=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
            database=base/'dienstplan-v2-demo.sqlite3'
        window=Workbench(database=database,initial=initial,year=args.year or (2026 if args.demo else None),month=args.month or (11 if args.demo else None))
        window.show()
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None,'Dienstplan konnte nicht gestartet werden',
            'Bitte Speicherort und Dateiformat prüfen. Alte Datenbanken werden nicht automatisch verändert oder übernommen.\n'+str(exc))
        return 1
    finally:
        if window is not None:window.store.close()


if __name__=='__main__':
    raise SystemExit(main())
