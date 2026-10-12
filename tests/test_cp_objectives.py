"""CP-Gleichungen und unabhängige Nachbewertung müssen denselben Plan bewerten."""
from datetime import datetime, time
from decimal import Decimal
from fractions import Fraction
from random import Random

import pytest
from ortools.sat.python import cp_model

from dienstplan.model import (Assignment, Blocker, Employee, HistoryEntry, MonthData,
                             ShiftType, WishHistoryEntry, generate_shifts)
from dienstplan.optimization import evaluate_plan
from dienstplan.planner import _ObjectiveBuilder, _hint_values
from dienstplan.wishes import wish_key


@pytest.mark.parametrize("seed",[0,3,8])
def test_cp_components_equal_post_evaluation_with_decimal_zero_and_history(seed):
    data=MonthData(2026,11,[Employee("A","A",Decimal(0 if seed%3==0 else 25)),
                           Employee("B","B",Decimal("17.125")),Employee("C","C",Decimal("33.334"))],
                    [ShiftType("a","Früh",time(10),time(16),staff_required=1),
                     ShiftType("b","Spät",time(16),time(22)),
                     ShiftType("c","Nacht",time(17),time(1),30),
                     ShiftType("d","Sonder",time(19),time(4),30,weekday=2)])
    data.exceptions={f"2026-11-{day:02d}/{typ}" for day in range(2,31) for typ in ("a","b","c")}
    cross=Blocker("cross","A",datetime(2026,10,31,20),datetime(2026,11,1,20),2)
    data.blockers=[cross]+[Blocker(str(day),"B",datetime(2026,11,day),datetime(2026,11,day+1),2) for day in (1,4,11)]
    history=[HistoryEntry("A",3,720,Fraction(2,3),Fraction(1000,3)),
             HistoryEntry("B",0,0,Fraction(4,3),Fraction(2000,3))]
    wish_history=[WishHistoryEntry("A",{wish_key(cross)})]
    rng=Random(seed)
    shifts=generate_shifts(data)
    assignments=[Assignment(s.id,e.id) for s in shifts
                 for e in rng.sample(data.employees,rng.randrange(s.staff_required+1))]
    model=cp_model.CpModel()
    variables={(s.id,e.id):model.new_bool_var(s.id+e.id) for s in shifts for e in data.employees}
    builder=_ObjectiveBuilder(model,data,shifts,variables,history,wish_history)
    builder.seed(assignments,[])
    objectives=[builder.objective(i) for i in range(len(builder.stages))]
    chosen={(a.shift_id,a.employee_id) for a in assignments}
    for key,var in variables.items(): model.add(var==int(key in chosen))
    solver=cp_model.CpSolver()
    assert solver.solve(model)==cp_model.OPTIMAL
    expected=evaluate_plan(data,assignments,history,wish_history)
    assert tuple(int(solver.value(o)) for o in objectives)==expected
    hints=_hint_values(model,builder,assignments,[])
    for objective,score in zip(objectives,expected):
        builder.hints=hints
        assert builder.expression_value(objective)==score
