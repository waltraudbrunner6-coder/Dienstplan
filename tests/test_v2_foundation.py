"""B1: echte Intervalle, konkrete Pausen und exakte Vertragsrechnungen."""
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dienstplan.v2.accounting import MonthAccount, leave_credits, round_minutes, s0_target
from dienstplan.v2.contracts import Contract, Contracts, DateRange, Employment
from dienstplan.v2.errors import DomainError
from dienstplan.v2.time import Interval, day_segments, local_instant, rest_minutes, vienna
from dienstplan.v2.work import WorkBlock, physical_months, quantities


def span(a, b):
    return Interval.local(a, b)


def block(start="2026-11-11T17:00", end="2026-11-12T01:00", pause=("2026-11-11T21:00", "2026-11-11T21:30"), **kw):
    return WorkBlock("b", "A", "W17", span(start, end), (span(*pause),) if pause else (), **kw)


def schedule(hours="25", first=date(2026, 1, 1), end=date(2027, 1, 1)):
    employment = Employment("A", DateRange(first, end))
    return Contracts("A", (Contract("A", employment.dates, hours),)), employment


def test_intervals_are_utc_immutable_positive_and_half_open():
    a = span("2026-11-11T10:00", "2026-11-11T12:00")
    b = span("2026-11-11T12:00", "2026-11-11T13:00")
    assert a.minutes == 120 and a.start.isoformat().endswith("+00:00")
    assert not a.overlaps(b) and a.intersection(b) is None
    with pytest.raises(FrozenInstanceError): a.end = b.end
    for start, end in ((a.start, a.start), (a.end, a.start)):
        with pytest.raises(DomainError): Interval(start, end)
    with pytest.raises(DomainError): Interval(datetime(2026, 1, 1), a.end)
    with pytest.raises(DomainError): Interval(a.start.replace(second=1), a.end)


def test_difference_clips_cuts_without_duplicate_or_lost_minutes():
    whole = span("2026-11-11T10:00", "2026-11-11T12:00")
    cut = span("2026-11-11T10:30", "2026-11-11T11:00")
    assert [i.minutes for i in whole.difference((cut, cut))] == [30, 60]
    assert whole.intersection(cut) == cut
    assert whole.difference((span("2026-11-10T00:00", "2026-11-12T00:00"),)) == ()
    assert whole.difference((span("2026-11-11T12:00", "2026-11-11T13:00"),)) == (whole,)


def test_local_gap_fold_offset_and_roundtrip():
    with pytest.raises(DomainError, match="existiert"):
        local_instant(datetime(2026, 3, 29, 2))
    naive = datetime(2026, 10, 25, 2, 30)
    with pytest.raises(DomainError, match="mehrdeutig"): local_instant(naive)
    a, b = local_instant(naive, fold=0), local_instant(naive, fold=1)
    assert b - a == timedelta(hours=1)
    assert local_instant(naive, offset=timedelta(hours=2)) == a
    assert local_instant(naive, offset=timedelta(hours=1)) == b
    assert (a.astimezone(vienna()).fold, b.astimezone(vienna()).fold) == (0, 1)
    with pytest.raises(DomainError): local_instant(naive, fold=0, offset=timedelta(hours=1))
    with pytest.raises(DomainError): span("2026-10-25T02:30+03:00", "2026-10-25T05:00+01:00")
    assert span("2026-10-25T02:30+02:00", "2026-10-25T02:30+01:00").minutes == 60


@pytest.mark.parametrize("start,end,minutes", [
    ("2026-03-28T20:00", "2026-03-29T08:00", 660),
    ("2026-03-28T20:00", "2026-03-29T07:59", 659),
    ("2026-11-10T00:00", "2026-11-10T11:00", 660),
    ("2026-11-10T00:00", "2026-11-10T10:59", 659),
])
def test_real_rest_including_spring_transition(start, end, minutes):
    end_of_first = local_instant(datetime.fromisoformat(start))
    begin_second = local_instant(datetime.fromisoformat(end))
    assert rest_minutes(Interval(end_of_first-timedelta(hours=1), end_of_first),
                        Interval(begin_second, begin_second+timedelta(hours=1))) == minutes


@pytest.mark.parametrize("end,days", [("2027-01-01T00:00", [date(2026,12,31)]),
                                    ("2027-01-01T00:01", [date(2026,12,31),date(2027,1,1)])])
def test_midnight_end_is_exclusive(end, days):
    parts = day_segments(span("2026-12-31T23:00", end))
    assert [d for d,_ in parts] == days
    assert sum(i.minutes for _,i in parts) == (60 if len(days)==1 else 61)


@pytest.mark.parametrize("pause,night", [(("2026-11-11T21:00","2026-11-11T21:30"),180),
                                       (("2026-11-11T22:00","2026-11-11T22:30"),150)])
def test_work_and_night_use_real_pause(pause, night):
    duty = block(pause=pause)
    assert duty.work_minutes == 450
    assert sum(r.night_minutes for r in quantities(duty)) == night
    assert duty.work_minutes + sum(p.minutes for p in duty.breaks) == duty.attendance.minutes
    assert duty.attendance == span("2026-11-11T17:00","2026-11-12T01:00")


@pytest.mark.parametrize("start,end,pause,attendance,work,night", [
    ("2026-03-28T20:00","2026-03-29T04:00",("2026-03-28T21:00","2026-03-28T21:30"),420,390,300),
    ("2026-10-24T20:00","2026-10-25T04:00",("2026-10-24T21:00","2026-10-24T21:30"),540,510,420),
])
def test_bk_dst_z08_z09(start,end,pause,attendance,work,night):
    duty=block(start,end,pause)
    assert (duty.attendance.minutes,duty.work_minutes)==(attendance,work)
    assert sum(r.night_minutes for r in quantities(duty))==night
    assert sum(r.work_minutes for r in quantities(duty))==work


def test_month_year_holiday_and_sunday_are_separate_physical_quantities():
    duty=block("2026-04-30T17:00","2026-05-01T01:00",("2026-04-30T21:00","2026-04-30T21:30"))
    assert physical_months(duty)==(("2026-04",390),("2026-05",60))
    assert sum(r.holiday_minutes for r in quantities(duty,frozenset({date(2026,5,1)})))==60
    duty=block("2026-10-31T17:00","2026-11-01T01:00",("2026-10-31T21:00","2026-10-31T21:30"))
    row=quantities(duty,frozenset({date(2026,11,1)}))[-1]
    assert (row.work_minutes,row.sunday_minutes,row.holiday_minutes)==(60,60,60)


def test_edge_break_does_not_make_occupied_day_free():
    duty=block("2026-11-13T18:00","2026-11-14T00:30",("2026-11-14T00:00","2026-11-14T00:30"))
    assert duty.work_minutes==360
    assert date(2026,11,14) in duty.occupied_days
    assert [r.day for r in quantities(duty)]==[date(2026,11,13)]


@pytest.mark.parametrize("pauses", [(),
    (("2026-11-11T21:00","2026-11-11T21:29"),),
    (("2026-11-11T16:50","2026-11-11T17:20"),),
    (("2026-11-11T21:00","2026-11-11T21:30"),)*2,
    (("2026-11-11T21:00","2026-11-11T21:30"),("2026-11-11T21:15","2026-11-11T21:45")),
])
def test_invalid_missing_or_duplicate_breaks(pauses):
    with pytest.raises(DomainError):
        WorkBlock("b","A","W17",span("2026-11-11T17:00","2026-11-12T01:00"),tuple(span(*p) for p in pauses))


def test_six_hour_threshold_and_protected_windows():
    assert block("2026-11-11T10:00","2026-11-11T16:00",None).work_minutes==360
    with pytest.raises(DomainError): block("2026-11-11T10:00","2026-11-11T16:01",None)
    assert block("2026-11-11T10:00","2026-11-11T16:01",("2026-11-11T13:00","2026-11-11T13:30")).work_minutes==331
    protected=span("2026-11-12T14:30","2026-11-12T17:30")
    with pytest.raises(DomainError):
        block("2026-11-12T10:15","2026-11-12T17:30",("2026-11-12T15:00","2026-11-12T15:30"),protected=(protected,))


def test_employment_inclusive_end_and_full_block():
    e=Employment.inclusive("A",date(2026,11,1),date(2026,12,31))
    assert e.contains(span("2026-12-31T16:00","2027-01-01T00:00"))
    assert not e.contains(span("2026-12-31T17:00","2027-01-01T01:00"))
    assert not e.contains(span("2026-10-31T23:59","2026-11-01T01:00"))


@pytest.mark.parametrize("hours", ["-1","NaN","Infinity","-Infinity",float('nan'),25.1])
def test_invalid_contract_hours(hours):
    with pytest.raises(DomainError): schedule(hours)


def test_contract_change_gaps_overlap_and_references():
    a=Contract("A",DateRange(date(2026,11,1),date(2026,11,16)),"25")
    b=Contract("A",DateRange(date(2026,11,16),date(2026,12,1)),"30")
    c=Contracts("A",(b,a))
    e=Employment("A",DateRange(date(2026,11,1),date(2026,12,1)))
    assert c.at(date(2026,11,15)).weekly_hours==25 and c.at(date(2026,11,16)).weekly_hours==30
    assert s0_target(c,e,2026,11,profile="S0").minutes==7071
    assert leave_credits(c,e,[date(2026,11,2),date(2026,11,16)])[0].minutes==660
    with pytest.raises(DomainError,match="überlappen"): Contracts("A",(a,a))
    with pytest.raises(DomainError): Contracts("B",(a,))
    with pytest.raises(DomainError,match="Vertragslücke"):
        s0_target(Contracts("A",(a,)),e,2026,11,profile="S0")


@pytest.mark.parametrize("year,month,expected",[(2026,2,6000),(2028,2,6214),(2026,4,6429),(2026,11,6429),(2026,1,6643)])
def test_s0_is_explicit_and_month_length_correct(year,month,expected):
    c,e=schedule(first=date(year,1,1),end=date(year+1,1,1))
    assert s0_target(c,e,year,month,profile="S0").minutes==expected
    with pytest.raises(DomainError): s0_target(c,e,year,month,profile="produktiv")
    with pytest.raises(TypeError): s0_target(c,e,year,month)


def test_leave_rounds_once_deduplicates_and_does_not_invent_days():
    c,e=schedule("25.04")
    days=[date(2026,11,n) for n in range(9,14)]
    amounts=leave_credits(c,e,days+days)
    assert (amounts[0].raw_minutes,amounts[0].minutes)==(Fraction('1502.4'),1502)
    assert leave_credits(c,e,[])==()
    with pytest.raises(DomainError): leave_credits(c,e,[date(2027,1,1)])
    assert round_minutes(Fraction(-3,2))==-2
    c,e=schedule("25",first=date(2026,11,16))
    assert s0_target(c,e,2026,11,profile="S0").minutes==3214


def test_accounts_keep_opening_balance_and_negative_raw_target():
    account=MonthAccount("A",600)
    assert account.desired_minutes==0 and account.opening_minutes==600
    assert account.goal(6429,1500).raw_minutes==4329
    assert account.projected(6429,4329,1500)==0
    goal=MonthAccount("A",300).goal(600,600)
    assert (goal.raw_minutes,goal.minimum_nonnegative,goal.overcoverage_minutes)==(-300,0,300)
    assert MonthAccount("A",300).projected(600,0,600)==300
    assert MonthAccount("A",-480).goal(6429,0).raw_minutes==6909
    with pytest.raises(DomainError): account.projected(10,-1,0)


@pytest.mark.parametrize("hours,minutes",[("25",300),("30",360),("37",444),("0",0)])
def test_explicit_credit_day_value(hours,minutes):
    c,e=schedule(hours)
    assert leave_credits(c,e,[date(2026,11,9)])[0].minutes==minutes


def test_leave_month_boundary_separate_rounding_and_needed_contract_gap():
    c,e=schedule("25.04")
    values=leave_credits(c,e,[date(2026,11,30),date(2026,12,1)])
    assert [(v.month,v.raw_minutes,v.minutes) for v in values]==[
        ("2026-11",Fraction('300.48'),300),("2026-12",Fraction('300.48'),300)]
    gap=Contracts("A",())
    with pytest.raises(DomainError,match="Vertragslücke"): leave_credits(gap,e,[date(2026,11,9)])


def test_offline_package_tzdb_without_system_path_or_infrastructure_imports():
    code='''
import sys, socket
class Reject:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'PySide6','sqlite3','ortools'}:
            raise AssertionError('Verbotene Infrastruktur: '+fullname)
sys.meta_path.insert(0,Reject())
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Netzwerk'))
from dienstplan.v2 import accounting, contracts, time, work
from datetime import datetime
from zoneinfo import TZPATH
assert TZPATH==()
a=time.local_instant(datetime(2026,10,25,2,30),fold=0)
b=time.local_instant(datetime(2026,10,25,2,30),fold=1)
assert (b-a).total_seconds()==3600
print('Paket-tzdb offline, Infrastruktur unabhängig')
'''
    result=subprocess.run([sys.executable,"-c",code],env=dict(os.environ,PYTHONTZPATH=""),capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'offline' in result.stdout
