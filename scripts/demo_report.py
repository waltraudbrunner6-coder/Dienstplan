"""Erstellt geprüfte bestätigte Monatsbeispiele und CSV-Berichte lokal."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dienstplan.csvio import export_fairness, export_hours, export_plan
from dienstplan.demo import demo_month
from dienstplan.hours import demand_minutes, fairness_rows, hour_rows
from dienstplan.planner import solve, validate_assignments
from dienstplan.storage import Store


def main():
    parser=argparse.ArgumentParser(description="Fiktive Dienstplan-Demonstration für Oktober bis Dezember 2026")
    parser.add_argument("--output",default="examples/generated")
    parser.add_argument("--seconds",type=float,default=20)
    args=parser.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    db=out/"demo.sqlite3"
    if db.exists():
        parser.error("Die Demo-Datenbank existiert bereits. Bitte einen neuen Ausgabeordner wählen.")
    store=Store(db)
    report=[]
    for month in (10,11,12):
        data=demo_month(2026,month)
        history=store.history(data.year,data.month)
        boundary=store.boundary(data.year,data.month)
        result=solve(data,history=history,boundary=boundary,time_limit=args.seconds)
        data.assignments=result.assignments
        errors=validate_assignments(data,data.assignments,boundary)
        if errors or result.status in ("invalid","unknown","cancelled"):
            raise RuntimeError(f"Demo fehlgeschlagen: {result.status} / {errors} / {result.messages}")
        store.save_month(data)
        if not result.open_slots:
            store.set_confirmed(2026,month,True)
        export_plan(out/f"{data.key}-dienstplan.csv",data)
        export_hours(out/f"{data.key}-stunden.csv",data)
        export_fairness(out/f"{data.key}-verteilung.csv",data,history)
        special=[r for r in fairness_rows(data,history=history) if r['type_id']=="sonder"]
        row=dict(monat=data.key,status=result.status,offene_plaetze=sum(result.open_slots.values()),
                 bedarf_stunden=demand_minutes(data)/60,planungsziele_stunden=sum(r.planning_minutes for r in hour_rows(data))/60,
                 optimalitaet_stufen=result.optimal_stages,sekunden=round(result.elapsed_seconds,3),
                 hinweise=result.messages,sonderverteilung=[{k:r[k] for k in ('name','count','expected_count','historical_count','historical_expected','cumulative_deviation')} for r in special])
        report.append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
    (out/"pruefbericht.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    store.close()


if __name__ == "__main__":
    main()
