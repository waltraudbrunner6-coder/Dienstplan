"""Gleiches Zielfunktionsmaß für CP-SAT und allgemeine Nachverbesserung."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from fractions import Fraction
from threading import Event
from time import monotonic

from dienstplan.model import (Assignment, Blocker, Employee, HistoryEntry, MonthData,
                             Rules, ShiftType, WishHistoryEntry)
from dienstplan.optimization import (HOURS_WEIGHT, ObjectiveContext, ceil_div,
                                     evaluate_plan, history_totals, improve_plan,
                                     round_fraction, shares, stage_names)
from dienstplan.planner import validate_assignments
from dienstplan.wishes import wish_key


def month(hours="4.2", people=2):
    return MonthData(2026, 11,
                     [Employee(f"p{i}", f"Person {i + 1}", Decimal(hours)) for i in range(people)],
                     [ShiftType("a", "Früh", time(10), time(16)),
                      ShiftType("b", "Spät", time(16), time(22)),
                      ShiftType("c", "Nacht", time(17), time(1), 30),
                      ShiftType("d", "Besonderer Dienst", time(19), time(4), 30, weekday=2)])


def assignment(day, shift, person, fixed=False):
    return Assignment(f"2026-11-{day:02d}/{shift}", person, fixed)


def wish(person, day, key=None, priority=2):
    start = datetime(2026, 11, day)
    return Blocker(key or f"{person}-{day}", person, start, start + timedelta(days=1), priority)


def test_exact_integer_rounding_shares_and_zero_hours():
    data = month("0", 3)
    assert shares(data) == {"p0": 334, "p1": 333, "p2": 333}
    assert round_fraction(Fraction(1, 2)) == 1
    assert round_fraction(Fraction(-1, 2)) == -1
    assert ceil_div(1001, 1000) == 2
    result = evaluate_plan(data, [assignment(1, "a", "p0")])
    assert result[-2] == 6000  # 360 Minuten / Mindestnenner 60, in Promille.
    assert result[-1] >= HOURS_WEIGHT * 6000 ** 2
    assert len(stage_names(data)) == len(result)


def test_hours_normalized_by_monthly_target_not_balance_adjusted_goal():
    data = month("4.2")  # 18 Monatssollstunden.
    data.employees[0].opening_minutes = 720
    data.employees[0].desired_minutes = 0  # Planungsziel 6 h; Nenner weiterhin 18 h.
    score = evaluate_plan(data, [assignment(1, "a", "p0"), assignment(2, "a", "p1")])
    assert score[-2] == 667  # Person 2: 12 / 18 Stunden Abweichung, aufgerundet.


def test_relevant_wishes_count_once_and_smaller_group_has_priority():
    data = month()
    data.blockers = [wish("p0", 1), wish("p0", 2)] + [wish("p1", d) for d in range(1, 7)]
    duplicate = wish("p0", 1, "duplicate")
    data.blockers.extend([duplicate, wish("p0", 1, "hard", 1)])
    data.blockers.append(Blocker("irrelevant", "p0", datetime(2026, 12, 8),
                                datetime(2026, 12, 9), 2))
    context = ObjectiveContext(data)
    assert list(context.wish_groups) == [2, 6]
    # Ein Tageswunsch überschneidet zwei zugeteilte Schichten, zählt einmal.
    twice = context.evaluate([assignment(1, "a", "p0"), assignment(1, "b", "p0")])
    assert twice[1] == 1
    assert context.evaluate([assignment(1, "a", "p1")]) < context.evaluate([assignment(1, "a", "p0")])


def test_equal_wish_group_protects_already_burdened_person():
    data = month()
    data.blockers = [wish(p, d) for p in ("p0", "p1") for d in range(1, 7)]
    history = [WishHistoryEntry("p0", {"previous-one", "previous-two"})]
    protected = evaluate_plan(data, [assignment(1, "a", "p1")], wish_history=history)
    burdened = evaluate_plan(data, [assignment(1, "a", "p0")], wish_history=history)
    assert protected[:3] == burdened[:3]
    assert protected[3:5] == (2, 5)
    assert burdened[3:5] == (3, 9)
    assert protected < burdened


def test_same_cross_month_wish_is_not_counted_again_in_cumulative_burden():
    data = month()
    blocker = Blocker("cross", "p0", datetime(2026, 10, 31, 20), datetime(2026, 11, 1, 20), 2)
    data.blockers = [blocker]
    history = [WishHistoryEntry("p0", {wish_key(blocker)}),
               WishHistoryEntry("p0", {wish_key(blocker)})]
    score = evaluate_plan(data, [assignment(1, "a", "p0")], wish_history=history)
    assert score[1:5] == (1, 1, 1, 1)


def test_historical_special_counts_and_actual_minutes_affect_score():
    data = month("4.2")
    history = [HistoryEntry("p0", 2, 600, Fraction(1), Fraction(300)),
               HistoryEntry("p1", 0, 0, Fraction(1), Fraction(300))]
    assert evaluate_plan(data, [assignment(4, "d", "p1")], history) < evaluate_plan(
        data, [assignment(4, "d", "p0")], history)
    totals = history_totals([history[0], history[0]])
    assert totals["p0"].special_count == 4
    assert history[0].special_count == 2  # Kein Schreiben in historische Eingaben.


def test_general_transfer_improves_hours_and_night_counts_with_all_limits_enabled():
    data = month()
    data.rules = Rules(rest_minutes=960, max_day_minutes=480,
                       max_week_minutes=1440, max_consecutive_days=3)
    for shift in data.shift_types:
        shift.staff_required = 1
    data.exceptions = {f"2026-11-{d:02d}/{s}" for d in range(1, 31) for s in ("a", "b", "c")
                       if not (d in (1, 4, 10, 14) and s == "c")}
    data.shift_types[3].start, data.shift_types[3].end = time(8), time(9)
    data.shift_types[3].pause_minutes = 0
    data.blockers = [Blocker(f"{p}-{d}", p, datetime(2026, 11, d, 8),
                            datetime(2026, 11, d, 9), 1)
                     for p in ("p0", "p1") for d in (4, 11, 18, 25)]
    before = [assignment(1, "c", "p0", True), assignment(4, "c", "p0", True),
              assignment(10, "c", "p0"), assignment(14, "c", "p1", True)]
    assert not validate_assignments(data, before)
    after = improve_plan(data, before, time_limit=1)
    assert assignment(10, "c", "p1") in after
    assert not validate_assignments(data, after)
    assert evaluate_plan(data, after) < evaluate_plan(data, before)
    assert assignment(10, "c", "p0") in before


def test_general_two_shift_swap_improves_counts_without_changing_hours():
    data = month()
    data.rules = Rules(rest_minutes=960, max_day_minutes=360,
                       max_week_minutes=720, max_consecutive_days=2)
    before = [assignment(d, "a", "p0", d != 16) for d in (1, 5, 16)]
    before += [assignment(d, "b", "p1", d != 16) for d in (1, 5, 16)]
    # Offene Plätze dürfen hier nicht die absichtlich isolierte Tauschsituation
    # verändern: alle 12 Einsätze sind durch Sperren/Höherprioritäten eingeschränkt.
    # Test der echten allgemeinen Verbesserung mit fixierter Gesamtbesetzung:
    for shift in data.shift_types:
        shift.staff_required = 1
    data.exceptions = {f"2026-11-{d:02d}/{s}" for d in range(1, 31) for s in ("a", "b", "c")
                       if not (d in (1, 5, 16) and s in ("a", "b"))}
    # Besondere Dienste durch verbindliche Sperren für beide Personen unbesetzbar.
    data.blockers = [wish(p, d, priority=1) for p in ("p0", "p1") for d in (4, 11, 18, 25)]
    assert not validate_assignments(data, before)
    after = improve_plan(data, before, time_limit=1)
    assert assignment(16, "a", "p1") in after
    assert assignment(16, "b", "p0") in after
    assert evaluate_plan(data, after)[:-1] == evaluate_plan(data, before)[:-1]
    assert evaluate_plan(data, after)[-1] < evaluate_plan(data, before)[-1]
    assert not validate_assignments(data, after)


def test_local_search_hard_rules_and_both_sources_of_fixing_preserved():
    data = month()
    data.rules = Rules(rest_minutes=960)
    data.blockers = [wish("p1", 10, priority=1)]
    before = [assignment(1, "c", "p0", True), assignment(4, "c", "p0"),
              assignment(10, "c", "p0"), assignment(14, "c", "p1", True)]
    data.assignments = [assignment(4, "c", "p0", True)]
    after = improve_plan(data, before, time_limit=.2)
    for a in [before[0], before[-1], data.assignments[0]]:
        assert a in after
    assert not validate_assignments(data, after)
    assert not any(a.shift_id == "2026-11-10/c" and a.employee_id == "p1" for a in after)


def test_invalid_initial_plan_cancel_and_zero_budget_return_input():
    data = month()
    before = [assignment(1, "a", "p0"), assignment(1, "a", "p0")]
    assert improve_plan(data, before) == before
    cancelled = Event()
    cancelled.set()
    assert improve_plan(data, before, cancel=cancelled) == before
    assert improve_plan(data, before, time_limit=0) == before
    assert improve_plan(data, before, time_limit=float("inf")) == before


def test_search_never_worsens_higher_wish_objective_and_respects_budget():
    data = month()
    data.blockers = [wish("p1", d) for d in (1, 4, 10)]
    before = [assignment(d, "c", "p0") for d in (1, 4, 10)]
    started = monotonic()
    after = improve_plan(data, before, time_limit=.05)
    assert monotonic() - started < .3
    assert evaluate_plan(data, after) <= evaluate_plan(data, before)
    assert not validate_assignments(data, after)
