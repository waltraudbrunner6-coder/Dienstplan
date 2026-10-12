from dataclasses import replace
from datetime import datetime, time, timedelta

from dienstplan.model import Assignment, Blocker, Employee, MonthData, ShiftType, WishHistoryEntry
from dienstplan.wishes import display_wishes, relevant_wishes, violated_wish_keys, wish_key, wish_rows, wish_snapshot


def data():
    return MonthData(2026,11,[Employee("a","Anna","25"),Employee("b","Ben","25")],
                     [ShiftType("frueh","Früh",time(10),time(16)),
                      ShiftType("spaet","Spät",time(16),time(22)),
                      ShiftType("nacht","Nacht",time(17),time(1),30),
                      ShiftType("sonder","Sonder",time(19),time(4),30,weekday=2)])


def blocker(person="a", day=16, priority=2, start_hour=0, end_hour=0):
    start=datetime(2026,11,day,start_hour)
    end=datetime(2026,11,day,end_hour)
    if end<=start: end+=timedelta(days=1)
    return Blocker(f"{person}-{day}-{priority}",person,start,end,priority)


def test_only_unique_p2_with_active_overlap_counts():
    d=data()
    b=blocker(start_hour=10,end_hour=16)
    d.blockers=[b,replace(b,id="duplicate",comment="Anderer Kommentar"),blocker(priority=1)]
    assert len(relevant_wishes(d))==1
    d.exceptions.add("2026-11-16/frueh")
    assert relevant_wishes(d)==[]
    assert wish_rows(d)[0]["relevant"]==0


def test_one_wish_over_two_shifts_counts_once():
    d=data(); d.blockers=[blocker()]
    d.assignments=[Assignment("2026-11-16/frueh","a"),Assignment("2026-11-16/spaet","a")]
    assert len(violated_wish_keys(d))==1
    row=wish_rows(d)[0]
    assert (row["relevant"],row["fulfilled"],row["violated"])==(1,0,1)


def test_historical_key_union_avoids_month_boundary_double_count():
    d=data()
    b=Blocker("cross","a",datetime(2026,10,31,22),datetime(2026,11,1,12),2)
    d.blockers=[b]
    d.assignments=[Assignment("2026-11-01/frueh","a")]
    history=[WishHistoryEntry("a",{wish_key(b)})]
    row=wish_rows(d,wish_history=history)[0]
    assert (row["historical"],row["violated"],row["cumulative"])==(1,1,1)
    assert history[0].violated_keys=={wish_key(b)}


def test_confirmed_snapshot_does_not_follow_later_blocker_changes():
    d=data(); d.blockers=[blocker()]
    d.assignments=[Assignment("2026-11-16/frueh","a")]
    d.wish_snapshot=wish_snapshot(d); d.confirmed=True
    before=wish_rows(d)
    displayed=display_wishes(d)
    d.blockers=[]
    assert wish_rows(d)==before
    assert wish_rows(d,d.assignments)==before
    assert display_wishes(d)==displayed


def test_missing_legacy_history_is_per_person_and_transparent():
    d=data(); d.confirmed=True
    rows=wish_rows(d,wish_history=[WishHistoryEntry("a",missing_months=["2026-10"])])
    assert rows[0]["missing_months"]==["2026-10"]
    assert rows[1]["missing_months"]==[]
    assert all(r["snapshot_missing"] for r in rows)
