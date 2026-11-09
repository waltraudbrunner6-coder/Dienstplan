"""Synthetische Q0-/Pausenprofile, keine betrieblichen Rechtsnachweise."""
from dataclasses import replace
from datetime import date

import pytest

from dienstplan.v2.calendar_rules import WeekPolicy,WeekQuota,check_quotas
from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import DateRange
from dienstplan.v2.entries import Entry
from dienstplan.v2.errors import DomainError
from dienstplan.v2.pauses import CoverageRule,PausePolicy,check_coverage,pause_candidates
from dienstplan.v2.solver import solve_feasibility,verify
from dienstplan.v2.time import Interval
from dienstplan.v2.weekly import weekly_options
from test_v2_solver import inputs
from test_v2_validation import person,pause

Q0=WeekPolicy('week_start','both','Q0 – synthetisches Wochenprofil')


def weekly_data(first=date(2026,11,9),last=date(2026,11,16),wl=1,allowed=None):
    span=DateRange(first,last)
    quotas=tuple(WeekQuota(code,code,span,count,first.strftime('%Y-%m')) for code,count in (('WL',wl),('BK',1)))
    terms=weekly_options(quotas,allowed_dates=allowed).events
    candidates=[]
    for term in terms:
        for pid in 'ABCD':candidates.append(term.assign(pid,(pause(term.attendance.start_day),)))
    data=inputs(terms,candidates,people=tuple(person(p) for p in 'ABCD'),
                optional_ids=frozenset(e.id for e in terms),quotas=quotas,week_policy=Q0)
    return replace(data,year=first.year,month=first.month)


def test_coupled_november_dates_and_people_no_preselection():
    data=weekly_data();result=solve_feasibility(data,time_limit=3)
    assert result.status=='feasible' and not result.open_slots
    assert len(result.events)==2 and len(result.blocks)==4
    assert not check_quotas(data.quotas,result.events,policy=Q0)
    assert not verify(data,result.blocks,active_events=result.events)[0].issues
    assert result.events[0].attendance.start_day!=result.events[1].attendance.start_day


def test_two_wl_dates_in_december_and_fixed_date_does_not_fix_people():
    data=weekly_data(date(2026,12,7),date(2026,12,14),2,
                     allowed={'WL':{date(2026,12,7),date(2026,12,9)},'BK':{date(2026,12,11)}})
    result=solve_feasibility(data,time_limit=3)
    assert not result.open_slots and len(result.blocks)==6
    assert {e.attendance.start_day for e in result.events if e.service.code=='WL'}=={date(2026,12,7),date(2026,12,9)}
    assert not check_quotas(data.quotas,result.events,policy=Q0)


def test_date_filter_with_unavailable_ab_chooses_cd_without_moving_date():
    data=weekly_data(allowed={'WL':{date(2026,11,10)},'BK':{date(2026,11,12)}})
    leave=tuple(Entry('vac'+p,p,'urlaub',Interval.local('2026-11-10T00:00','2026-11-11T18:00')) for p in 'AB')
    data=replace(data,absences=leave)
    result=solve_feasibility(data,time_limit=3)
    assert not result.open_slots
    wl=[b for b in result.blocks if b.code=='WL']
    assert {b.person_id for b in wl}=={'C','D'} and all(b.attendance.start_day==date(2026,11,10) for b in wl)


def test_fixed_date_with_no_people_remains_open_not_silently_shifted():
    data=weekly_data(allowed={'WL':{date(2026,11,10)},'BK':{date(2026,11,12)}})
    leave=tuple(Entry('vac'+p,p,'urlaub',Interval.local('2026-11-10T00:00','2026-11-11T18:00')) for p in 'ABCD')
    result=solve_feasibility(replace(data,absences=leave),time_limit=3)
    assert result.status=='incomplete' and result.open_slots==(('2026-11-10/WL',2),)
    assert any(e.id=='2026-11-10/WL' for e in result.events)


def test_conflicting_fixed_date_filters_are_really_infeasible():
    data=weekly_data(allowed={'WL':{date(2026,11,10)},'BK':{date(2026,11,10)}})
    assert solve_feasibility(data,time_limit=2).status=='infeasible'


def test_pause_windows_protect_team_and_preserve_real_night_quantities():
    term=event('KCT10',date(2026,11,12))
    policy=PausePolicy('Synthetisches Fenster',
                       (Interval.local('2026-11-12T14:00','2026-11-12T16:00'),),30)
    choices=pause_candidates(term,'A',policy=policy)
    assert len(choices)==1 and choices[0].breaks[0].start==pause(date(2026,11,12),'14:00','14:30').start
    assert choices[0].work_minutes==405 and choices[0].attendance==term.attendance


def coverage_data(relief):
    day=date(2026,11,11);term=event('W17',day)
    helper=event('FK',day,people=('C',),attendance=term.attendance)
    policy=PausePolicy('Testfenster 20–21:30',
                       (Interval.local('2026-11-11T20:00','2026-11-11T21:30'),),30)
    terms=(term,helper) if relief else (term,)
    candidates=tuple(b for pid in 'AB' for b in pause_candidates(term,pid,policy=policy))
    if relief:candidates+=pause_candidates(helper,'C',policy=policy)
    rule=CoverageRule(term.id,2,'Synthetische durchgehende Besetzung', (helper.id,) if relief else ())
    return inputs(terms,candidates,people=tuple(person(p) for p in 'ABC'),coverage=(rule,))


def test_simultaneous_breaks_fail_independent_coverage_even_with_nominal_two():
    data=coverage_data(False);term=data.events[0]
    blocks=tuple(term.assign(p,(pause(date(2026,11,11),'20:00','20:30'),)) for p in 'AB')
    issues=check_coverage(data.events,blocks,data.coverage)
    assert len(issues)==1 and '0 tatsächlich arbeitend' in issues[0].message
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='incomplete' and result.open_slots==((term.id,2),) and not result.blocks


def test_real_relief_and_joint_pause_choice_make_full_coverage_possible():
    data=coverage_data(True);result=solve_feasibility(data,time_limit=2)
    assert result.status=='feasible' and len(result.blocks)==3 and not result.open_slots
    assert len({b.breaks[0] for b in result.blocks})==3
    assert not check_coverage(result.events,result.blocks,data.coverage)
    assert all(len([b for b in result.blocks if b.person_id==pid])==1 for pid in 'ABC')
    # Nachträgliche Manipulation wird direkt am Ergebnis bemerkt.
    changed=tuple(replace(b,breaks=(result.blocks[0].breaks[0],)) for b in result.blocks)
    assert not verify(data,changed,active_events=result.events)[0].hard_ok


def test_optional_inputs_require_explicit_quota_and_selected_event_snapshot():
    data=weekly_data()
    with pytest.raises(DomainError,match='gewählten Termine'):verify(data,())
    with pytest.raises(DomainError,match='Wochenprofil'):replace(data,week_policy=None)
    with pytest.raises(DomainError,match='genau einer'):replace(data,quotas=())
    with pytest.raises(DomainError,match='Datumsfilter'):weekly_options(data.quotas,allowed_dates={})
    # Vorhandene reine Offenplanung bleibt auch ohne Personenzuteilung ein Startpunkt.
    chosen=(next(e for e in data.events if e.id=='2026-11-09/WL'),next(e for e in data.events if e.id=='2026-11-11/BK'))
    result=solve_feasibility(data,time_limit=1e-12,existing_events=chosen)
    assert result.status=='incomplete' and result.events==chosen and sum(n for _,n in result.open_slots)==4


def test_nonexistent_spring_wl_end_is_excluded_with_visible_cause():
    quota=WeekQuota('spring/WL','WL',DateRange(date(2026,3,23),date(2026,3,30)),1,'2026-03')
    options=weekly_options((quota,))
    assert len(options.events)==6
    assert len(options.rejected)==1 and options.rejected[0].event_id=='2026-03-28/WL'
    assert 'existiert' in options.rejected[0].message
