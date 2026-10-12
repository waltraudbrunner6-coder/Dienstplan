"""Alte/neue Optimierung seriell mit identischer Novemberfixture vergleichen.

Der alte Solver wird aus dem angegebenen Git-Commit in ein temporäres Paket
gelesen und im selben Python/OR-Tools ausgeführt. Checkout und Arbeitsdateien
werden dabei nicht geändert. Fremde frühere Testgrenzen werden nicht behauptet.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ortools

from dienstplan.csvio import export_fairness, export_hours, export_plan, export_wishes
from dienstplan.fixtures import november_2026
from dienstplan.hours import demand_minutes, fairness_rows, hour_rows
from dienstplan.model import Assignment, generate_shifts
from dienstplan.planner import coverage, solve, validate_assignments
from dienstplan.wishes import wish_rows

BASELINE_COMMIT = "e7e0fc5e319cc636ca95f0685b0728e5d535e1f8"
BASELINE_FILES = ("__init__.py", "model.py", "hours.py", "planner.py")


def baseline_sources(commit: str) -> dict[str, bytes]:
    """Benötigte lokale Historie vor jedem Vergleich prüfen, ohne Netzwerk."""
    commands = [("Commit", ["git", "cat-file", "-e", f"{commit}^{{commit}}"])]
    commands.extend((f"dienstplan/{name}", ["git", "show", f"{commit}:dienstplan/{name}"])
                    for name in BASELINE_FILES)
    sources = {}
    for label, command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        if result.returncode:
            details = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Originalsolver nicht verfügbar: {label} fehlt im lokalen Git-Stand "
                               f"für Baseline {commit}. Bitte die Historie vor dem Vergleich bereitstellen "
                               "(im CI actions/checkout mit fetch-depth: 0). "
                               f"Git-Fehler (Exitcode {result.returncode}): {details}")
        if label != "Commit":
            sources[label.removeprefix("dienstplan/")] = result.stdout
    return sources


def fixture_payload(data) -> dict:
    """Versionneutraler Eingabesnapshot einschließlich exakter Dezimalwerte."""
    return dict(year=data.year, month=data.month,
                employees=[dict(id=e.id, name=e.name, weekly_hours=str(e.weekly_hours),
                                opening_minutes=e.opening_minutes, desired_minutes=e.desired_minutes)
                           for e in data.employees],
                shift_types=[dict(id=s.id, name=s.name, start=s.start.isoformat(), end=s.end.isoformat(),
                                  pause_minutes=s.pause_minutes, staff_required=s.staff_required,
                                  weekday=s.weekday) for s in data.shift_types],
                blockers=[dict(id=b.id, employee_id=b.employee_id, start=b.start.isoformat(),
                               end=b.end.isoformat(), priority=b.priority, comment=b.comment)
                          for b in data.blockers],
                rules=asdict(data.rules), assignments=[asdict(a) for a in data.assignments],
                exceptions=sorted(data.exceptions), confirmed=data.confirmed)


BASELINE_RUNNER = '''from dataclasses import asdict
from datetime import datetime, time
import json
from pathlib import Path
import sys
import ortools
from dienstplan.model import Employee, ShiftType, Blocker, Rules, MonthData, Assignment
from dienstplan.planner import solve, validate_assignments

p=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if p.get("exceptions"):
    raise RuntimeError("Der alte Solver unterstützt keine datumsbezogenen Ausnahmen.")
employees=[Employee(**row) for row in p["employees"]]
shifts=[ShiftType(**dict(row, start=time.fromisoformat(row["start"]), end=time.fromisoformat(row["end"]))) for row in p["shift_types"]]
blockers=[Blocker(**dict(row, start=datetime.fromisoformat(row["start"]), end=datetime.fromisoformat(row["end"]))) for row in p["blockers"]]
data=MonthData(p["year"], p["month"], employees, shifts, blockers, Rules(**p["rules"]), [Assignment(**row) for row in p["assignments"]], p["confirmed"])
data.validate()
result=solve(data, time_limit=float(sys.argv[2]))
errors=validate_assignments(data,result.assignments)
if errors:
    raise RuntimeError("Alter Solver erzeugte ungültigen Plan: " + "; ".join(errors))
row=asdict(result)
row["ortools_version"]=ortools.__version__
row["stage_names"]=["Besetzung", "Wünsche insgesamt", "Alte gewichtete Stunden-/Schichtsumme"][:len(result.optimal_stages)]
row["objective_values"]=[]
Path(sys.argv[3]).write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
'''


def run_baseline(payload: dict, commit: str, seconds: float):
    sources = baseline_sources(commit)
    with tempfile.TemporaryDirectory(prefix="dienstplan-vergleich-") as directory:
        temporary = Path(directory)
        package = temporary / "dienstplan"
        package.mkdir()
        for name, content in sources.items():
            (package / name).write_bytes(content)
        input_file = temporary / "input.json"
        input_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        runner = temporary / "baseline.py"
        runner.write_text(BASELINE_RUNNER, encoding="utf-8")
        result_file = temporary / "result.json"
        environment = dict(os.environ, PYTHONPATH=str(temporary))
        completed = subprocess.run([sys.executable, str(runner), str(input_file), str(seconds), str(result_file)],
                                   cwd=temporary, env=environment, capture_output=True, text=True,
                                   timeout=max(120, seconds * 3))
        if completed.returncode:
            raise RuntimeError(f"Baseline fehlgeschlagen: {completed.stderr.strip()}")
        raw = json.loads(result_file.read_text(encoding="utf-8"))
        if raw.pop("ortools_version") != ortools.__version__:
            raise RuntimeError("Der Vergleich verwendete unterschiedliche OR-Tools-Versionen.")
        raw["assignments"] = [Assignment(**row) for row in raw["assignments"]]
        return SimpleNamespace(**raw)


def metrics(data, result) -> dict:
    assignments = result.assignments
    errors = validate_assignments(data, assignments)
    if errors:
        raise RuntimeError("Ungültiger Vergleichsplan: " + "; ".join(errors))
    hours = hour_rows(data, assignments)
    normalized = [abs(row.deviation_minutes) / max(60, row.target_minutes) for row in hours]
    hour_export = []
    for row in hours:
        values = asdict(row)
        values["weekly_hours"] = str(values["weekly_hours"])
        values["deviation_hours"] = row.deviation_minutes / 60
        values["absolute_relative_deviation"] = abs(row.deviation_minutes) / max(60, row.target_minutes)
        hour_export.append(values)
    wishes = wish_rows(data, assignments)
    fairness = fairness_rows(data, assignments)
    special = [row for row in fairness if next(s for s in data.shift_types if s.id == row["type_id"]).special]
    return dict(status=result.status, assigned_slots=len(assignments),
                required_slots=sum(s.staff_required for s in generate_shifts(data)),
                open_slots=sum(coverage(data, assignments).values()),
                required_hours=demand_minutes(data) / 60,
                planning_target_hours=sum(row.planning_minutes for row in hours) / 60,
                wishes_violated=sum(row["violated"] for row in wishes),
                total_absolute_deviation_minutes=sum(abs(row.deviation_minutes) for row in hours),
                max_absolute_relative_deviation=max(normalized, default=0),
                squared_relative_deviations=sum(value * value for value in normalized),
                special_distinct_people=sum(row["count"] > 0 for row in special),
                special_max_count=max((row["count"] for row in special), default=0),
                elapsed_seconds=result.elapsed_seconds, stage_names=result.stage_names,
                optimal_stages=result.optimal_stages,
                objective_values=getattr(result, "objective_values", []),
                local_improvements=getattr(result, "improvements", 0),
                messages=result.messages, hours=hour_export, wishes=wishes,
                distribution=fairness,
                assignments=[asdict(a) for a in assignments])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="examples/comparison")
    parser.add_argument("--seconds", type=float, default=30,
                        help="Identisches Gesamtzeitlimit je Solver in Sekunden (Standard: 30)")
    parser.add_argument("--baseline-commit", default=BASELINE_COMMIT)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("Das Zeitlimit muss endlich und größer als null sein.")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    data = november_2026()
    data.validate()
    payload = fixture_payload(data)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    (out / "eingabe.json").write_text(serialized, encoding="utf-8")
    print("Alter Solver: identische Novemberfixture wird seriell berechnet.", flush=True)
    baseline = run_baseline(payload, args.baseline_commit, args.seconds)
    print("Neuer Solver: gleicher Input, gleiche Regeln und Rechenzeit.", flush=True)
    current = solve(data, time_limit=args.seconds)
    report = dict(
        month=data.key, baseline_commit=args.baseline_commit, ortools_version=ortools.__version__,
        python_version=sys.version.split()[0], seconds_per_solver=args.seconds,
        input_sha256=sha256(serialized.encode("utf-8")).hexdigest(),
        rules=payload["rules"], history="Keine bestätigten Vormonate in beiden Läufen.",
        execution="Serielle Läufe mit jeweils einem CP-SAT-Suchworker und Solver-Seed 202611.",
        normalized_hours="Absolute Zielabweichung / max(Monatssoll, 60 Minuten); Quadrate summiert.",
        limitation="Frühere externe Testgrenzen sind unbekannt; dies ist eine neue, dokumentierte Vergleichsfixture. Laufzeitgrenzen können zu verschiedenen Suchständen führen.",
        before=metrics(data, baseline), after=metrics(data, current))
    for label, result in (("vorher", baseline), ("nachher", current)):
        data.assignments = result.assignments
        export_plan(out / f"{label}-dienstplan.csv", data)
        export_hours(out / f"{label}-stunden.csv", data)
        export_fairness(out / f"{label}-verteilung.csv", data)
        export_wishes(out / f"{label}-freiwuensche.csv", data)
    (out / "vergleich.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for label, result in (("vorher", report["before"]), ("nachher", report["after"])):
        concise = {key: result[key] for key in (
            "status", "assigned_slots", "open_slots", "wishes_violated",
            "max_absolute_relative_deviation", "squared_relative_deviations",
            "special_distinct_people", "special_max_count", "elapsed_seconds", "optimal_stages")}
        print(label + ": " + json.dumps(concise, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
