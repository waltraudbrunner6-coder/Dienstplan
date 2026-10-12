"""Funktionaler Selbsttest, auch aus dem eigenständigen Paket ausführbar."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def run_smoke_test() -> int:
    try:
        from .csvio import export_fairness, export_hours, export_plan, preview_csv
        from .demo import demo_month
        from .hours import hour_rows
        from .planner import solve, validate_assignments
        from .storage import Store
        from PySide6.QtWidgets import QApplication
        from .ui import MainWindow

        with tempfile.TemporaryDirectory(prefix="dienstplan-selbsttest-") as tmp:
            root=Path(tmp)
            os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
            os.environ.setdefault("XDG_CACHE_HOME",str(root/"cache"))
            data=demo_month()
            csv_path=root/"import.csv"
            csv_path.write_text("datum;von;bis;prioritaet;kommentar\n2026-11-20;22:00;06:00;1;Test über Mitternacht\n",encoding="utf-8-sig")
            preview=preview_csv(csv_path,data.employees[3].id)
            assert preview.valid and len(preview.blockers)==1, "CSV-Import funktioniert nicht."
            data.blockers.extend(preview.blockers)
            store=Store(root/"test.sqlite3")
            result=solve(data,time_limit=8)
            assert result.assignments, f"Kein Plan gefunden: {result.status} / {result.messages}"
            assert not result.open_slots, "Selbsttest: Demo ist nicht vollständig besetzt."
            assert not validate_assignments(data,result.assignments), "Ungültige Zuteilungen im Selbsttest."
            data.assignments=result.assignments
            assert sum(r.planned_minutes for r in hour_rows(data))>0
            store.save_month(data)
            loaded=store.load_month(data.year,data.month)
            assert loaded is not None and loaded.assignments==data.assignments
            assert len(loaded.blockers)==len(data.blockers), "Sperren wurden nicht gespeichert."
            store.set_confirmed(data.year,data.month,True)
            history=store.history(2026,12)
            assert sum(h.special_count for h in history)==8, "Bestätigte Sonderhistorie stimmt nicht."
            export_plan(root/"plan.csv",loaded)
            export_hours(root/"stunden.csv",loaded)
            export_fairness(root/"verteilung.csv",loaded)
            assert all((root/f).stat().st_size>100 for f in ("plan.csv","stunden.csv","verteilung.csv"))
            app=QApplication.instance() or QApplication([])
            window=MainWindow(store,year=data.year,month=data.month)
            window.show(); app.processEvents()
            assert window.isVisible(), "Desktop-Fenster wurde nicht angezeigt."
            window.close(); app.processEvents()
            store.close()
            print(json.dumps({"selbsttest":"bestanden","personen":12,"zuteilungen":len(result.assignments),
                              "status":result.status,"csv_sqlite_solver_qt":True},ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"selbsttest":"fehlgeschlagen","fehler":str(exc)},ensure_ascii=False))
        return 1
