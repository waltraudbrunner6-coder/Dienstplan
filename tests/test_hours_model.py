from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

from dienstplan.hours import demand_minutes, hour_rows, monthly_target, planning_target
from dienstplan.model import (Assignment, Blocker, Employee, MonthData, ShiftType, ValidationError,
                             default_shifts, generate_shifts, overlaps, to_minutes, validate_blockers)


@pytest.mark.parametrize("year,month,days", [(2026,2,28),(2028,2,29),(2026,4,30),(2026,1,31)])
def test_actual_month_length(year, month, days):
    e = Employee("a", "Anna", "40")
    expected = int((Decimal(40)*days*60/7).quantize(Decimal(1), rounding="ROUND_HALF_UP"))
    assert monthly_target(e, year, month) == expected
    d = MonthData(year, month, [e], default_shifts())
    assert sum(not s.special for s in generate_shifts(d)) == days*3


def test_round_once_after_conversion_and_comma():
    assert monthly_target(Employee("a", "Anna", "0,00625"),2026,2) == 2
    assert monthly_target(Employee("a", "Anna", "0.101"),2026,1) == 27
    assert to_minutes("1,25") == 75
    assert to_minutes("-0,025") == -2


def test_balance_reduction_and_forecast():
    a=Employee("a", "Anna", "40", 600,0)
    b=Employee("b", "Ben", "40",-480,0)
    assert monthly_target(a,2026,2) == 9600
    assert planning_target(a,2026,2) == 9000
    assert planning_target(b,2026,2) == 10080
    assert planning_target(Employee("c","Clara","40",600),2026,2) == 9600
    d=MonthData(2026,2,[a,b],default_shifts())
    shift=generate_shifts(d)[0]
    rows=hour_rows(d,[Assignment(shift.id,a.id)])
    assert rows[0].planned_minutes == 480
    assert rows[0].new_balance_minutes == 480-9600
    assert rows[0].projected_balance_minutes == 600+480-9600
    assert rows[0].deviation_minutes == 480-9000


@pytest.mark.parametrize("value", ["NaN","Infinity","-Infinity","Text"])
def test_invalid_numbers(value):
    with pytest.raises(ValidationError): Employee("a","Anna",value)


def test_negative_goal_rejected():
    with pytest.raises(ValidationError, match="negativ"):
        planning_target(Employee("a","Anna","5",6000,0),2026,2)


def test_required_employee_hours_and_staffing():
    d=MonthData(2026,2,[Employee("a","Anna","40")],default_shifts())
    assert demand_minutes(d) == (28*3*8*2 + 4*12*2)*60
    d.shift_types[0].staff_required=3
    assert demand_minutes(d) == (28*3*8*2 + 4*12*2 + 28*8)*60


@pytest.mark.parametrize("year,month,count",[(2026,2,4),(2026,7,5),(2026,11,4)])
def test_weekly_occurrences(year,month,count):
    d=MonthData(year,month,[],default_shifts())
    assert sum(s.special for s in generate_shifts(d)) == count


def test_overnight_pause_and_start_month():
    d=MonthData(2026,11,[],default_shifts())
    d.shift_types[2].pause_minutes=30
    s=next(s for s in generate_shifts(d) if s.type_id=="nacht" and s.start.day==30)
    assert s.end == datetime(2026,12,1,6)
    assert s.paid_minutes == 450
    assert not overlaps(s.start,s.end,s.end,s.end+timedelta(hours=1))
    assert overlaps(s.start,s.end,datetime(2026,12,1,2),datetime(2026,12,1,3))
    assert ShiftType("a","24 Stunden",time(8),time(8)).duration_minutes == 1440


def test_blocker_limit_cross_month_and_duplicates():
    blocks=[Blocker(str(i),"a",datetime(2026,12,i),datetime(2026,12,i+1),1) for i in (2,4,6,8)]
    assert len(validate_blockers(blocks+blocks)) == 4
    cross=Blocker("cross","a",datetime(2026,11,30,22),datetime(2026,12,1,2),1)
    with pytest.raises(ValidationError,match="vier"):
        validate_blockers(blocks+[cross])
    at_boundary=Blocker("end","a",datetime(2026,11,30),datetime(2026,12,1),1)
    assert len(validate_blockers(blocks+[at_boundary])) == 5


def test_special_duration_is_independent_of_daily_shifts():
    d=MonthData(2026,11,[Employee("a","Anna","40")],default_shifts())
    d.validate()
    d.shift_types[3].pause_minutes=241
    d.validate()


def test_minute_precision_and_unplausible_values_rejected():
    with pytest.raises(ValidationError,match="ganze Minuten"):
        Employee("a","Anna","40",0.5,0).validate()
    with pytest.raises(ValidationError,match="ganzen Minuten"):
        ShiftType("a","Früh",time(8,0,1),time(12)).validate()
    with pytest.raises(ValidationError,match="10.000"):
        to_minutes("1e10000")
