"""Fachliche Regressionen: dieselben Grenzen in Solver und manueller Prüfung."""
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from fractions import Fraction
from threading import Event, Timer

from dienstplan.hours import demand_minutes, fairness_rows, hour_rows
from dienstplan.model import (
    Assignment, Blocker, Employee, HistoryEntry, MonthData, Rules,
    ShiftOccurrence, ShiftType, generate_shifts,
)
from dienstplan.planner import (
    coverage, paid_segments, preference_violations, solve, validate_assignments,
)


def month(people=4, hours="11.5", year=2026, number=2):
    return MonthData(year, number,
                     [Employee(f"p{i}", f"Person {i + 1}", Decimal(hours)) for i in range(people)],
                     [ShiftType("a", "Früh", time(6), time(7)),
                      ShiftType("b", "Spät", time(12), time(13)),
                      ShiftType("c", "Abend", time(18), time(19)),
                      ShiftType("d", "Besonderer Dienst", time(9), time(11), weekday=2)])


def full_day(person, day, priority=1, key="block"):
    start = datetime(2026, 2, day)
    return Blocker(key, person, start, start + timedelta(days=1), priority)


def occurrence(sid, start, end, paid=None):
    return ShiftOccurrence(sid, "a", "Randdienst", start, end,
                           paid if paid is not None else int((end - start).total_seconds() / 60), 2)


def test_default_two_distinct_staff_and_four_special_dates():
    data = month()
    result = solve(data, time_limit=5)
    assert result.status in {"optimal", "feasible"}
    assert result.open_slots == {}
    assert validate_assignments(data, result.assignments) == []
    counts = Counter(a.shift_id for a in result.assignments)
    assert set(counts.values()) == {2}
    assert len([s for s in generate_shifts(data) if s.special]) == 4
    assert demand_minutes(data) == 184 * 60


def test_staff_count_changes_demand_and_coverage():
    data = month()
    data.shift_types[0].staff_required = 3
    result = solve(data, time_limit=4)
    assert not result.open_slots
    assert demand_minutes(data) == (184 + 28) * 60
    assert all(sum(a.shift_id == s.id for a in result.assignments) == s.staff_required
               for s in generate_shifts(data))


def test_p1_never_sacrificed_for_p2_and_wish_counts_once():
    data = month(2, "23")
    data.blockers = [full_day("p0", 2, 1), full_day("p1", 2, 2)]
    result = solve(data, time_limit=4)
    assert result.status == "incomplete"
    assert sum(result.open_slots.values()) == 3
    assert not any(a.employee_id == "p0" and a.shift_id.startswith("2026-02-02/")
                   for a in result.assignments)
    assert len(result.violations) == 1  # Ein Tageswunsch, trotz drei zugeteilter Schichten.
    assert "Person 2" in result.violations[0]
    assert not validate_assignments(data, result.assignments)


def test_p2_avoided_if_full_coverage_still_possible():
    data = month(4)
    data.blockers = [full_day("p0", 2, 2)]
    result = solve(data, time_limit=4)
    assert not result.open_slots
    assert result.violations == []
    assert result.optimal_stages[:2] == [True, True]


def test_fixed_assignment_retained_and_flag_preserved():
    data = month()
    data.assignments = [Assignment("2026-02-01/a", "p0", True)]
    result = solve(data, time_limit=4)
    assert Assignment("2026-02-01/a", "p0", True) in result.assignments
    assert data.assignments == [Assignment("2026-02-01/a", "p0", True)]


def test_invalid_fixed_assignment_explained_without_violating_block():
    data = month()
    data.blockers = [full_day("p0", 1)]
    data.assignments = [Assignment("2026-02-01/a", "p0", True)]
    result = solve(data, time_limit=2)
    assert result.status == "invalid"
    assert result.assignments == []
    assert any("Priorität-1" in message for message in result.messages)


def test_manual_duplicate_unknown_and_capacity_rejected():
    data = month()
    chosen = [Assignment("2026-02-01/a", "p0"), Assignment("2026-02-01/a", "p0"),
              Assignment("2026-02-01/a", "p1"), Assignment("2026-02-01/a", "p2"),
              Assignment("unknown", "p1"), Assignment("2026-02-01/a", "unknown")]
    errors = validate_assignments(data, chosen)
    assert any("doppelt" in error for error in errors)
    assert any("überschreiten" in error for error in errors)
    assert sum("unbekannt" in error for error in errors) == 2


def test_equal_hours_balanced_each_type_and_special():
    data = month(4)
    result = solve(data, time_limit=6)
    rows = fairness_rows(data, result.assignments)
    assert all(row["count_deviation"] == 0 for row in rows)
    assert all(row.planned_minutes == row.planning_minutes for row in hour_rows(data, result.assignments))
    assert result.status == "optimal"


def test_different_contract_hours_receive_proportional_types():
    data = month(3)
    data.employees[0].weekly_hours = Decimal("23")
    result = solve(data, time_limit=6)
    # Verhältnis 2:1:1, 56 regelmäßige Einsätze und 8 besondere je Typ.
    by_type = {st.id: Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/" + st.id))
               for st in data.shift_types}
    for st in data.shift_types:
        target = {"p0": 4, "p1": 2, "p2": 2} if st.special else {"p0": 28, "p1": 14, "p2": 14}
        assert dict(by_type[st.id]) == target


def test_twelve_people_special_slots_distributed_without_repetition():
    data = month(12, "4")
    result = solve(data, time_limit=8)
    special = Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/d"))
    assert not result.open_slots
    assert not validate_assignments(data, result.assignments)
    assert sum(special.values()) == 8
    assert max(special[e.id] for e in data.employees) == 1
    for st in data.shift_types[:3]:
        counts = Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/" + st.id))
        all_counts = [counts[e.id] for e in data.employees]
        assert max(all_counts) - min(all_counts) <= 1


def test_balanced_start_survives_solver_timeout_without_global_proof(monkeypatch):
    """Auch ohne CP-SAT-Fund bleibt der faire gültige Startplan verfügbar."""
    from dienstplan import planner
    from dienstplan.optimization import evaluate_plan
    data = month(12, "4")
    # Keine Hardware-Zeitmessung: Startheuristik vollständig ausführen, dann
    # alle echten Solverläufe gezielt ohne Ergebnis enden lassen.
    monkeypatch.setattr(planner, "monotonic", lambda: 0.0)
    monkeypatch.setattr(planner.cp_model.CpSolver, "solve", lambda *args: planner.cp_model.UNKNOWN)
    monkeypatch.setattr(planner, "improve_plan", lambda data, assignments, *args, **kwargs: list(assignments))
    result = planner.solve(data, time_limit=8)
    assert not result.open_slots
    assert not validate_assignments(data, result.assignments)
    assert data.assignments == []
    special = Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/d"))
    assert sum(special.values()) == 8
    assert max(special[e.id] for e in data.employees) == 1
    for st in data.shift_types[:3]:
        counts = Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/" + st.id))
        assert max(counts[e.id] for e in data.employees) - min(counts[e.id] for e in data.employees) <= 1
    assert result.objective_values == list(evaluate_plan(data, result.assignments))
    # Null offene Plätze/Null Wünsche sind analytisch bewiesen. Der
    # Optimierungsnachweis für Stunden/Fairness fehlt weiterhin.
    assert result.optimal_stages == [True, True, False, False]
    assert result.status == "feasible"


def test_start_timeout_retains_valid_partial_progress(monkeypatch):
    from dienstplan import planner
    data = month(12, "4")
    ticks = iter([0.0] * 4)
    monkeypatch.setattr(planner, "monotonic", lambda: next(ticks, 1.0))
    result = planner._balanced_hint(data, generate_shifts(data), None, None, [], 0.5, None)
    assert 0 < len(result) < sum(s.staff_required for s in generate_shifts(data))
    assert not validate_assignments(data, result)
    assert data.assignments == []


def test_history_prefers_people_below_their_previous_share():
    data = month(4)
    history = [HistoryEntry("p0", 4, 480, Fraction(2), Fraction(240)),
               HistoryEntry("p1", 4, 480, Fraction(2), Fraction(240)),
               HistoryEntry("p2", 0, 0, Fraction(2), Fraction(240)),
               HistoryEntry("p3", 0, 0, Fraction(2), Fraction(240))]
    result = solve(data, history, time_limit=6)
    counts = Counter(a.employee_id for a in result.assignments if a.shift_id.endswith("/d"))
    assert counts["p2"] + counts["p3"] > counts["p0"] + counts["p1"]
    # solve darf gespeicherte historische Sollanteile weder ändern noch mehrfach erhöhen.
    assert history[0].special_count == 4 and history[0].expected_count == Fraction(2)


def test_missing_people_returns_valid_partial_plan():
    data = month(1, "46")
    result = solve(data, time_limit=3)
    assert result.status == "incomplete"
    assert sum(result.open_slots.values()) == 88
    assert not validate_assignments(data, result.assignments)
    assert any("Unvollständiger Entwurf" in message for message in result.messages)


def test_overnight_paid_minutes_and_adjacent_intervals():
    shift = occurrence("night", datetime(2026, 1, 31, 22), datetime(2026, 2, 1, 6), 420)
    assert paid_segments(shift) == {date(2026, 1, 31): 120, date(2026, 2, 1): 300}
    data = month()
    boundary = [(Assignment("night", "p0"), shift)]
    current = [Assignment("2026-02-01/a", "p0")]
    assert not validate_assignments(data, current, boundary)  # 06:00 direkt angrenzend.
    data.rules.rest_minutes = 60
    assert any("Ruhezeit" in error for error in validate_assignments(data, current, boundary))


def test_cross_month_boundary_blocked_by_solver_and_manual_rules():
    data = month()
    shift = occurrence("night", datetime(2026, 1, 31, 23), datetime(2026, 2, 1, 8))
    boundary = [(Assignment("night", "p0"), shift)]
    assert any("Überschneidung" in error for error in validate_assignments(
        data, [Assignment("2026-02-01/a", "p0")], boundary))
    result = solve(data, boundary=boundary, time_limit=4)
    assert not any(a.shift_id == "2026-02-01/a" and a.employee_id == "p0" for a in result.assignments)
    assert not validate_assignments(data, result.assignments, boundary)


def test_existing_current_month_is_filtered_from_boundary():
    data = month()
    first = generate_shifts(data)[0]
    assignment = Assignment(first.id, "p0", True)
    data.assignments = [assignment]
    boundary = [(assignment, first)]
    assert not validate_assignments(data, data.assignments, boundary)
    result = solve(data, boundary=boundary, time_limit=4)
    assert assignment in result.assignments


def test_day_week_and_consecutive_limits_include_boundary():
    data = month()
    old = occurrence("last", datetime(2026, 1, 31, 22), datetime(2026, 2, 1, 6))
    boundary = [(Assignment(old.id, "p0"), old)]
    current = [Assignment("2026-02-01/a", "p0")]
    data.rules = Rules(max_day_minutes=360, max_week_minutes=480, max_consecutive_days=1)
    errors = validate_assignments(data, current, boundary)
    assert any("Tagesstunden" in error for error in errors)
    assert any("Wochenstunden" in error for error in errors)
    assert any("Arbeitstage" in error for error in errors)
    result = solve(data, boundary=boundary, time_limit=4)
    assert not validate_assignments(data, result.assignments, boundary)
    assert current[0] not in result.assignments


def test_overnight_attendance_counts_even_unpaid_end_of_shift():
    data = month()
    data.shift_types[0].start, data.shift_types[0].end = time(23), time(1)
    data.shift_types[0].pause_minutes = 60
    data.rules.max_consecutive_days = 1
    chosen = [Assignment("2026-02-01/a", "p0")]
    assert any("2 Tage" in error for error in validate_assignments(data, chosen))
    result = solve(data, time_limit=3)
    assert not any(a.shift_id.endswith("/a") for a in result.assignments)


def test_p2_boundary_contact_is_not_overlap_and_duplicate_is_one():
    data = month()
    start = datetime(2026, 2, 1, 7)
    b = Blocker("b", "p0", start, start + timedelta(hours=1), 2)
    data.blockers = [b, Blocker("duplicate", "p0", b.start, b.end, 2)]
    assert preference_violations(data, [Assignment("2026-02-01/a", "p0")]) == []
    data.blockers[0].start = datetime(2026, 2, 1, 6)
    data.blockers[1].start = data.blockers[0].start
    assert len(preference_violations(data, [Assignment("2026-02-01/a", "p0")])) == 1


def test_cancel_before_start_and_tiny_limit_are_not_infeasible_claims():
    event = Event()
    event.set()
    result = solve(month(), cancel=event)
    assert result.status == "cancelled"
    result = solve(month(12), time_limit=0.000001)
    assert result.status == "unknown"
    assert any("beweist keine Unlösbarkeit" in message for message in result.messages)


def test_running_solver_is_cancelled_without_waiting_for_time_limit():
    event = Event()
    timer = Timer(0.15, event.set)
    timer.start()
    try:
        result = solve(month(12, "4"), cancel=event, time_limit=30)
    finally:
        timer.cancel()
    assert event.is_set()
    assert result.elapsed_seconds < 3
    assert any("abgebrochen" in message for message in result.messages)
    assert not validate_assignments(month(12, "4"), result.assignments)


def test_recalculation_keeps_input_and_reports_hours_mismatch():
    data = month(4, "40")
    result = solve(data, time_limit=3)
    assert data.assignments == []
    assert any("Rechnerischer Stundenvergleich" in message for message in result.messages)
    assert any("Nicht geprüft" in message for message in result.messages)

