from dataclasses import replace
from datetime import date
from threading import Event

import pytest

from dienstplan.v2.catalog import event
from dienstplan.v2.calendar_rules import WeekendPolicy,dates,horizon
from dienstplan.v2.entries import Entry
from dienstplan.v2.solver import PlanningInput,solve_feasibility,verify
from dienstplan.v2.time import Interval
from test_v2_validation import person,pause


def inputs(events,candidates,people=None,**kw):
    people=tuple(people or (person('A'),person('B')))
    known=frozenset((p.id,d) for p in people for d in dates(horizon(2026,11)))
    return PlanningInput(people,tuple(events),tuple(candidates),2026,11,known,
                         WeekendPolicy('saturday','Synthetisches Testprofil'),'Synthetisches Machbarkeitsprofil – keine Betriebsfreigabe',**kw)


def test_real_cp_sat_fills_two_distinct_positions_and_revalidates():
    d=date(2026,11,11);term=event('W17',d)
    data=inputs((term,),[term.assign(p,(pause(d),)) for p in ('A','B')])
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='feasible' and not result.open_slots
    assert {b.person_id for b in result.blocks}=={'A','B'} and result.coverage_optimal
    core,calendar=verify(data,result.blocks)
    assert core.hard_ok and calendar.hard_ok and calendar.fully_checked
    assert result.input_fingerprint==data.fingerprint


def test_unstaffable_position_stays_open_instead_of_violating_leave():
    d=date(2026,11,11);term=event('W17',d)
    vacation=Entry('vac','B','urlaub',Interval.local('2026-11-09T00:00','2026-11-16T00:00'))
    data=inputs((term,),[term.assign(p,(pause(d),)) for p in ('A','B')],absences=(vacation,))
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='incomplete' and result.open_slots==((term.id,1),)
    assert [b.person_id for b in result.blocks]==['A']


def test_fixed_invalid_person_is_not_reassigned_to_someone_else():
    d=date(2026,11,11);term=event('N17',d,people=('A',))
    data=inputs((term,),[term.assign('A',(pause(d),))],people=(person('A',license=False),person('B')))
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='infeasible' and not result.blocks
    assert any(i.rule=='eligibility' and 'Führerschein' in i.message for i in result.issues)


def test_same_startdate_and_rest_are_enforced_in_model():
    d=date(2026,11,10);a=event('VN',d,people=('A',));b=event('KC16',d)
    data=inputs((a,b),(a.assign('A'),b.assign('A',(pause(d),))),people=(person(),))
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='incomplete' and result.blocks==(a.assign('A'),)


def test_unknown_calendar_is_not_a_complete_validity_claim():
    term=event('KC10',date(2026,11,11));data=inputs((term,),(term.assign('A'),))
    data=replace(data,known_days=frozenset())
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='conditional' and not result.open_slots and result.unchecked


def test_controlled_deadline_keeps_existing_plan_and_no_false_global_optimum(monkeypatch):
    from dienstplan.v2 import solver
    term=event('KC10',date(2026,11,11));data=inputs((term,),(term.assign('A'),))
    old=(term.assign('A'),);ticks=iter((0.,1.))
    monkeypatch.setattr(solver,'monotonic',lambda:next(ticks,1.))
    monkeypatch.setattr(solver.cp_model.CpSolver,'solve',lambda *a:pytest.fail('Abgelaufenes Budget darf Solver nicht starten'))
    result=solve_feasibility(data,time_limit=.0001,existing=old)
    assert result.blocks==old and result.status=='feasible'
    # Nur Besetzungsnull analytisch bewiesen, keine anderen Optimierungsstufen behauptet.
    assert result.coverage_optimal and data.candidates==old


def test_cancel_before_search_and_timeout_without_solution_are_distinguished():
    stop=Event();stop.set();term=event('KC10',date(2026,11,11));data=inputs((term,),(term.assign('A'),))
    assert solve_feasibility(data,cancel=stop).status=='cancelled'
    assert solve_feasibility(data,time_limit=1e-12).status=='unknown'


def test_fingerprint_is_independent_of_input_order_and_changes_with_rules():
    a=event('KC10',date(2026,11,10));b=event('KC10',date(2026,11,11))
    one=inputs((a,b),(a.assign('A'),b.assign('B')))
    two=replace(one,people=tuple(reversed(one.people)),events=(b,a),candidates=tuple(reversed(one.candidates)))
    assert one.fingerprint==two.fingerprint
    assert one.fingerprint!=replace(one,profile_label='Anderes Testprofil').fingerprint


def test_independent_calendar_cuts_reject_bad_weekend_but_return_valid_open_draft():
    fixed=[event('FK',date(2026,11,d),people=('A',),attendance=Interval.local(f'2026-11-{d:02d}T10:00',f'2026-11-{d:02d}T11:00')) for d in (9,10,12,13)]
    sunday=event('W17',date(2026,11,15))
    candidates=[e.assign('A') for e in fixed]+[sunday.assign('A',(pause(date(2026,11,15)),))]
    data=inputs(tuple(fixed)+(sunday,),candidates,people=(person(),))
    result=solve_feasibility(data,time_limit=2)
    assert result.status=='incomplete' and result.open_slots==((sunday.id,2),)
    assert {b.id for b in result.blocks}=={e.id for e in fixed}
    core,calendar=verify(data,result.blocks)
    assert core.hard_ok and calendar.hard_ok
