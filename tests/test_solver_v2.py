"""Freiwunschprioritäten durch echte CP-SAT-Läufe, nicht nur Bewertungsformeln."""
from dataclasses import replace
from datetime import datetime, time, timedelta

from dienstplan.model import (Assignment, Blocker, Employee, MonthData, ShiftType,
                             WishHistoryEntry, default_shifts)
from dienstplan.optimization import evaluate_plan
from dienstplan.planner import solve, validate_assignments
from dienstplan.wishes import wish_rows


def competing_wishes(a_count=2, two_shifts=False):
    data=MonthData(2026,11,[Employee(p,p,"25") for p in ("A","B","C")],
                   [ShiftType("a","Früh",time(10),time(16),staff_required=1),
                    ShiftType("b","Spät",time(16),time(22),staff_required=1),
                    ShiftType("c","Nacht",time(22),time(6),staff_required=1),
                    ShiftType("d","Sonder",time(19),time(20),staff_required=1,weekday=2)])
    data.exceptions={f"2026-11-{day:02d}/{type_id}" for day in range(1,31) for type_id in ("a","b","c")
                     if not (type_id=="a" and day<=6) and not (two_shifts and day==1 and type_id=="b")}
    def add(person,day,priority):
        start=datetime(2026,11,day)
        data.blockers.append(Blocker(f"{person}-{day}-{priority}",person,start,start+timedelta(days=1),priority))
    for person,count in (("A",a_count),("B",6)):
        for day in range(1,count+1): add(person,day,2)
        for day in (4,11,18,25): add(person,day,1)
    add("C",1,1)  # Am 1. muss genau einer von A/B seinen Wunsch übergehen.
    return data


def test_solver_protects_two_wishes_ahead_of_six():
    data=competing_wishes()
    result=solve(data,time_limit=4)
    assert not result.open_slots and not validate_assignments(data,result.assignments)
    rows={r["employee_id"]:r for r in wish_rows(data,result.assignments)}
    assert (rows["A"]["relevant"],rows["B"]["relevant"])==(2,6)
    assert (rows["A"]["violated"],rows["B"]["violated"])==(0,1)
    assert result.optimal_stages[:4]==[True]*4


def test_solver_protects_historically_burdened_person_in_same_group():
    data=competing_wishes(6)
    history=[WishHistoryEntry("A",{"frueher-1","frueher-2"})]
    result=solve(data,time_limit=4,wish_history=history)
    rows={r["employee_id"]:r for r in wish_rows(data,result.assignments,history)}
    assert rows["A"]["violated"]==0 and rows["B"]["violated"]==1
    assert rows["A"]["cumulative"]==2 and rows["B"]["cumulative"]==1
    assert not validate_assignments(data,result.assignments)


def test_solver_protects_person_with_two_other_current_violations():
    data=competing_wishes(6)
    data.assignments=[Assignment("2026-11-02/a","A",True),Assignment("2026-11-03/a","A",True)]
    result=solve(data,time_limit=4)
    rows={r["employee_id"]:r for r in wish_rows(data,result.assignments)}
    assert rows["A"]["violated"]==2 and rows["B"]["violated"]==1
    assert Assignment("2026-11-01/a","B") in result.assignments
    assert not validate_assignments(data,result.assignments)


def test_solver_counts_same_wish_once_for_two_adjacent_shifts():
    data=competing_wishes(two_shifts=True)
    result=solve(data,time_limit=4)
    assert Assignment("2026-11-01/a","B") in result.assignments
    assert Assignment("2026-11-01/b","B") in result.assignments
    assert len(result.violations)==1
    assert result.objective_values==list(evaluate_plan(data,result.assignments))


def test_numeric_solver_limit_keeps_known_valid_plan():
    data=MonthData(2026,11,[Employee(p,p,0,-600000,600000) for p in ("A","B")],default_shifts())
    for shift in data.shift_types: shift.staff_required=1
    data.assignments=[Assignment("2026-11-01/frueh","A",True)]
    result=solve(data,time_limit=2)
    assert result.status in {"feasible","incomplete"}
    assert data.assignments[0] in result.assignments
    assert not validate_assignments(data,result.assignments)
    assert result.objective_values==list(evaluate_plan(data,result.assignments))
    assert any("numerischer Grenzen" in message for message in result.messages)
    assert not all(result.optimal_stages)


def test_tiny_limit_keeps_existing_valid_plan_and_input_unchanged():
    data=competing_wishes()
    first=solve(data,time_limit=2)
    data.assignments=list(first.assignments)
    before=list(data.assignments)
    again=solve(data,time_limit=0.0001)
    assert again.status=="feasible"
    assert again.assignments==before and data.assignments==before
    assert again.objective_values==list(evaluate_plan(data,before))
    assert not any(again.optimal_stages)
