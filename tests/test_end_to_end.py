"""Vollständige Offline-Kette mit echten Dateien und erneut geöffneter SQLite."""
import csv
import socket
from datetime import time

from dienstplan.csvio import export_fairness, export_hours, export_plan, preview_csv
from dienstplan.hours import demand_minutes, hour_rows
from dienstplan.model import Employee, MonthData, ShiftType
from dienstplan.planner import solve, validate_assignments
from dienstplan.storage import Store


def test_offline_import_plan_forecast_export_and_restart(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Die lokale Dienstplanung darf keine Netzwerkverbindung benötigen.")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    data=MonthData(2026,2,[Employee(str(i),f"Offline-Person {i}","12.5") for i in range(3)],
                   [ShiftType("a","Früh",time(6),time(7)),ShiftType("b","Spät",time(12),time(13)),
                    ShiftType("c","Abend",time(18),time(19)),ShiftType("d","Sonder",time(9),time(11),weekday=2)])
    source=tmp_path/"sperren.csv"
    source.write_text("datum,von,bis,prioritaet,kommentar\n2026-02-03,,,1,Ganztägig gesperrt\n",encoding="utf-8-sig")
    preview=preview_csv(source,"0")
    assert preview.valid
    data.blockers=preview.blockers
    result=solve(data,time_limit=4)
    assert result.status in {"optimal","feasible"}
    assert not result.open_slots and not validate_assignments(data,result.assignments)
    data.assignments=result.assignments
    assert sum(row.planned_minutes for row in hour_rows(data))==demand_minutes(data)
    db=tmp_path/"offline.sqlite3"
    with Store(db) as store:
        store.save_month(data)
        store.set_confirmed(2026,2,True)
    with Store(db) as store:
        loaded=store.load_month(2026,2)
        assert loaded.confirmed
        assert loaded.assignments==data.assignments
        assert loaded.blockers==data.blockers
        assert sum(h.special_count for h in store.history(2026,3))==8
        export_plan(tmp_path/"plan.csv",loaded)
        export_hours(tmp_path/"stunden.csv",loaded)
        export_fairness(tmp_path/"verteilung.csv",loaded,store.history(2026,2))
    with (tmp_path/"plan.csv").open(encoding="utf-8-sig",newline="") as stream:
        rows=list(csv.DictReader(stream,delimiter=";"))
    assert len(rows)==176  # 28 × 3 × 2 tägliche plus 4 × 2 besondere Plätze.
    assert all(row["Person"]!="OFFEN" for row in rows)
    assert not any(row["Person"]=="Offline-Person 0" and row["Datum"]=="2026-02-03" for row in rows)
