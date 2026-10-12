"""Reproduzierbare Monatsdaten und allgemeine lokale Verbesserungsfälle."""
from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest

from dienstplan.fixtures import (
    NOVEMBER_BLOCKERS, daily_swap_case, night_transfer_case, november_2026,
)
from dienstplan.hours import demand_minutes, fairness_rows, hour_rows, monthly_target
from dienstplan.model import Blocker, PlanResult, generate_shifts, validate_blockers
from dienstplan.planner import coverage, validate_assignments
from dienstplan.wishes import relevant_wishes, wish_rows


def test_exact_november_contracts_demand_and_blocker_table():
    data = november_2026()
    data.validate()
    assert len(data.employees) == 12
    assert all(e.weekly_hours == 25 and e.opening_minutes == e.desired_minutes == 0
               for e in data.employees)
    assert all(monthly_target(e, 2026, 11) == 6429 for e in data.employees)
    assert sum(r.planning_minutes for r in hour_rows(data)) == 77148
    shifts = generate_shifts(data)
    assert demand_minutes(data) == 1238 * 60
    assert sum(s.staff_required for s in shifts) == 188
    assert [s.start.day for s in shifts if s.special] == [4, 11, 18, 25]
    assert len(validate_blockers(data.blockers)) == 74
    for number, priorities in NOVEMBER_BLOCKERS.items():
        for priority, days in priorities.items():
            actual = tuple(b.start.day for b in data.blockers
                           if b.employee_id == f"person-{number:02d}" and b.priority == priority)
            assert actual == days
    assert not any(b.employee_id in {f"person-{n:02d}" for n in range(9, 13)} for b in data.blockers)
    assert data.rules.rest_minutes == 660
    assert data.rules.max_day_minutes == 720
    assert data.rules.max_week_minutes == 2400
    assert data.rules.max_consecutive_days == 6


def test_one_early_exception_exact_demand_and_slots():
    data = november_2026()
    data.exceptions.add("2026-11-16/frueh")
    data.validate()
    shifts = generate_shifts(data)
    assert demand_minutes(data) == 1226 * 60
    assert sum(s.staff_required for s in shifts) == 186
    assert {s.type_id for s in shifts if s.start.day == 16} == {"spaet", "nacht"}
    assert sum(coverage(data).values()) == 186
    data.exceptions.clear()
    assert demand_minutes(data) == 1238 * 60
    assert sum(coverage(data).values()) == 188


def test_three_daily_exceptions_leave_weekly_shift_and_previous_night():
    data = november_2026()
    data.exceptions.update(f"2026-11-18/{kind}" for kind in ("frueh", "spaet", "nacht"))
    shifts = {s.id: s for s in generate_shifts(data)}
    assert set(s.type_id for s in shifts.values() if s.start.day == 18) == {"sonder"}
    assert shifts["2026-11-17/nacht"].end == datetime(2026, 11, 18, 1)
    assert demand_minutes(data) == (1238 - 39) * 60
    assert sum(s.staff_required for s in shifts.values()) == 182


def test_month_boundary_exception_removes_only_start_date_and_wish_relevance():
    data = november_2026()
    data.blockers.append(Blocker("cross-boundary", "person-09", datetime(2026, 12, 1),
                                datetime(2026, 12, 1, 1), 2))
    assert any(b.id == "cross-boundary" for b in relevant_wishes(data))
    data.exceptions.add("2026-11-30/nacht")
    data.validate()
    shifts = {s.id: s for s in generate_shifts(data)}
    assert "2026-11-29/nacht" in shifts and "2026-11-30/nacht" not in shifts
    assert not any(b.id == "cross-boundary" for b in relevant_wishes(data))
    assert demand_minutes(data) == 1223 * 60
    assert next(r for r in wish_rows(data) if r["employee_id"] == "person-09")["relevant"] == 0


def test_fairness_soll_uses_only_active_assigned_occurrences():
    from dienstplan.model import Assignment

    data = november_2026()
    # Vollständig besetzter rechnerischer Verteilungssnapshot, ohne Anspruch
    # auf einen regelgültigen Gesamtplan: hier wird nur der Sollanteil geprüft.
    data.assignments = [Assignment(s.id, e.id) for s in generate_shifts(data)
                        for e in data.employees[:s.staff_required]]
    before = next(r for r in fairness_rows(data)
                  if r["employee_id"] == "person-01" and r["type_id"] == "frueh")
    data.exceptions.add("2026-11-16/frueh")
    data.assignments = [a for a in data.assignments if a.shift_id != "2026-11-16/frueh"]
    after = next(r for r in fairness_rows(data)
                 if r["employee_id"] == "person-01" and r["type_id"] == "frueh")
    assert before["expected_count"] == 5
    assert after["expected_count"] == pytest.approx(58 / 12)
    assert after["expected_minutes"] == pytest.approx(58 * 360 / 12)


def test_night_transfer_counterexample_has_all_active_limits_and_exact_hours():
    data = night_transfer_case()
    data.validate()
    assert validate_assignments(data) == []
    assert coverage(data) == {}
    assert len(data.assignments) == 188
    by_person = {r.employee_id: r for r in hour_rows(data)}
    assert by_person["person-10"].deviation_minutes == 446
    assert by_person["person-06"].deviation_minutes == -609
    transferred = [replace(a, employee_id="person-06")
                   if (a.shift_id, a.employee_id) == ("2026-11-10/nacht", "person-10")
                   else a for a in data.assignments]
    assert validate_assignments(data, transferred) == []
    after = {r.employee_id: r for r in hour_rows(data, transferred)}
    assert after["person-10"].deviation_minutes == -4
    assert after["person-06"].deviation_minutes == -159
    assert sum(a.shift_id.endswith("/nacht") and a.employee_id == "person-10" for a in transferred) == 8
    assert sum(a.shift_id.endswith("/nacht") and a.employee_id == "person-06" for a in transferred) == 4
    shifts = {s.id: s for s in generate_shifts(data)}
    target = shifts["2026-11-10/nacht"]
    assert (target.start - shifts["2026-11-09/nacht"].end).total_seconds() / 3600 == 16
    assert (shifts["2026-11-11/nacht"].start - target.end).total_seconds() / 3600 == 16


def test_general_local_search_finds_night_transfer_and_preserves_fixed():
    from dienstplan.planner import evaluate_plan, improve_plan

    data = night_transfer_case()
    before = list(data.assignments)
    improved = improve_plan(data, before, time_limit=2)
    assert validate_assignments(data, improved) == []
    assert len(improved) == len(before)
    assert all(a in improved for a in before if a.fixed)
    assert next(a for a in improved if not a.fixed).employee_id == "person-06"
    assert next(a for a in improved if not a.fixed).shift_id == "2026-11-10/nacht"
    assert evaluate_plan(data, improved) < evaluate_plan(data, before)
    assert data.assignments == before


def test_daily_swap_counterexample_preserves_hours_and_all_active_limits():
    data = daily_swap_case()
    data.validate()
    assert validate_assignments(data) == []
    assert coverage(data) == {}
    assert len(data.assignments) == 188
    rows = {r.employee_id: r for r in hour_rows(data)}
    assert rows["person-02"].planning_minutes == rows["person-04"].planning_minutes == 5040
    assert rows["person-02"].deviation_minutes == rows["person-04"].deviation_minutes == 0
    counts = Counter((a.employee_id, a.shift_id.split("/")[1]) for a in data.assignments)
    assert (counts["person-02", "frueh"], counts["person-02", "spaet"]) == (12, 2)
    assert (counts["person-04", "frueh"], counts["person-04", "spaet"]) == (3, 7)
    swapped = [replace(a, employee_id="person-04")
               if (a.shift_id, a.employee_id) == ("2026-11-16/frueh", "person-02")
               else replace(a, employee_id="person-02")
               if (a.shift_id, a.employee_id) == ("2026-11-16/spaet", "person-04")
               else a for a in data.assignments]
    assert validate_assignments(data, swapped) == []
    assert [r.planned_minutes for r in hour_rows(data, swapped)] == [r.planned_minutes for r in hour_rows(data)]


def test_general_local_search_finds_daily_swap_without_changing_hours():
    from dienstplan.planner import evaluate_plan, improve_plan

    data = daily_swap_case()
    before = list(data.assignments)
    improved = improve_plan(data, before, time_limit=2)
    assert validate_assignments(data, improved) == []
    assert len(improved) == len(before)
    assert all(a in improved for a in before if a.fixed)
    assert next(a for a in improved if a.shift_id == "2026-11-16/frueh" and not a.fixed).employee_id == "person-04"
    assert next(a for a in improved if a.shift_id == "2026-11-16/spaet" and not a.fixed).employee_id == "person-02"
    assert [r.planned_minutes for r in hour_rows(data, improved)] == [r.planned_minutes for r in hour_rows(data)]
    assert evaluate_plan(data, improved) < evaluate_plan(data, before)
    assert data.assignments == before


def test_comparison_payload_preserves_contracts_and_metrics_validate_complete_plan():
    """Vergleichsbericht erhält Dezimalverträge und bewertet echte Zuteilungen."""
    from scripts.compare_planners import fixture_payload, metrics

    data = night_transfer_case()
    payload = fixture_payload(data)
    assert payload["employees"][9]["weekly_hours"] == "24.9833333333"
    assert payload["rules"] == {
        "rest_minutes": 660, "max_day_minutes": 720,
        "max_week_minutes": 2400, "max_consecutive_days": 6,
    }
    result = PlanResult("feasible", list(data.assignments),
                        stage_names=["Besetzung"], optimal_stages=[True])
    measured = metrics(data, result)
    assert measured["required_slots"] == measured["assigned_slots"] == 188
    assert measured["open_slots"] == measured["wishes_violated"] == 0
    assert measured["required_hours"] == 1238
    assert measured["optimal_stages"] == [True]
    assert measured["hours"][9]["deviation_minutes"] == 446
    invalid = replace(result, assignments=result.assignments + [result.assignments[0]])
    with pytest.raises(RuntimeError, match="Ungültiger Vergleichsplan"):
        metrics(data, invalid)


def test_comparison_against_original_commit_reads_identical_fixture_without_checkout_changes():
    """Kurzer Integrationslauf des Originalsolvers im isolierten temporären Paket."""
    from scripts.compare_planners import BASELINE_COMMIT, fixture_payload, metrics, run_baseline

    data = november_2026()
    original_payload = fixture_payload(data)
    result = run_baseline(original_payload, BASELINE_COMMIT, seconds=0.1)
    assert fixture_payload(data) == original_payload
    assert validate_assignments(data, result.assignments) == []
    measured = metrics(data, result)
    assert measured["required_slots"] == 188
    assert measured["required_hours"] == 1238
    assert measured["planning_target_hours"] == 1285.8
    # Ein sehr kurzes Zeitlimit beweist weder Unbesetzbarkeit noch Optimalität.
    assert measured["assigned_slots"] + measured["open_slots"] == 188
