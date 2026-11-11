"""Genehmigte Wunsch-Datumswahl darf niemals neue Dienstregeln ausschalten."""
from dataclasses import replace
from datetime import date
import pytest
from dienstplan.v2.catalog import event
from dienstplan.v2.entries import Entry
from dienstplan.v2.planning_validation import accepted_wish_warnings,blocking_issues
from dienstplan.v2.solver import solve_feasibility,verify,verify_for_planning
from dienstplan.v2.time import Interval
from dienstplan.v2.validation import Issue
from test_v2_solver import inputs
from test_v2_validation import person,pause


def granted():
    term=event('KC10',date(2026,11,10));block=term.assign('B')
    wish=Entry('thursday-A','A','freiwunschtag',Interval.local('2026-11-12T00:00','2026-11-13T00:00'),rule_override=True)
    return replace(inputs((term,),(block,)),absences=(wish,),manual_override=True,locked=(block,)),block


def test_raw_audit_stays_strict_but_approved_configuration_is_plannable():
    d,b=granted()
    raw,_=verify(d,(b,),active_events=d.events)
    planned,_=verify_for_planning(d,(b,),active_events=d.events)
    assert raw.issues and not planned.issues
    assert {i.rule for i in raw.issues}=={'overridden_rule'}
    result=solve_feasibility(d,time_limit=2,existing=(b,),existing_events=d.events)
    assert result.blocks==(b,) and not result.open_slots and result.status=='conditional'
    assert not result.global_optimal and result.proofs and all(p.conditional for p in result.proofs)
    assert any('Donnerstag' in text and 'Genehmigte' in text for text in result.unchecked)


def test_approval_requires_both_month_and_entry_flags_and_exact_issue():
    d,b=granted();raw,_=verify(d,(b,),active_events=d.events)
    assert accepted_wish_warnings(d,raw.issues)
    assert not accepted_wish_warnings(replace(d,manual_override=False),raw.issues)
    unrelated=Issue('overridden_rule','A','thursday-A','Ein Dienst über sechs Stunden benötigt eine Pause.')
    assert blocking_issues(d,(unrelated,))==(unrelated,)
    leave=Entry('thursday-A','A','urlaub',Interval.local('2026-11-12T00:00','2026-11-13T00:00'),rule_override=True)
    assert not accepted_wish_warnings(replace(d,absences=(leave,)),raw.issues)


def test_unapproved_wish_configuration_is_rejected_before_search():
    d,b=granted()
    result=solve_feasibility(replace(d,manual_override=False),time_limit=2)
    assert result.status=='invalid' and not result.blocks
    assert any(i.rule=='overridden_rule' and i.person_id=='A' and i.event_id=='thursday-A'
               and 'Donnerstag' in i.message for i in result.issues)
    assert not any('Genehmigte' in text for text in result.unchecked)


def test_mutually_invalid_fixed_rest_reports_specific_conflict_without_existing_plan():
    day=date(2026,11,9);late=event('KC16',day);early=event('KC10',date(2026,11,10))
    locks=(late.assign('A',(pause(day),)),early.assign('A'))
    d=replace(inputs((late,early),locks),locked=locks)
    result=solve_feasibility(d,time_limit=2)
    assert result.status=='infeasible'
    assert any(i.rule=='rest' and i.person_id=='A' and i.event_id==early.id and '45' in i.message for i in result.issues)
    assert not any('Manuelle Fixierung ist mit' in i.message for i in result.issues)


def test_real_eligibility_error_is_not_masked_by_approved_wish():
    d,b=granted()
    bad=replace(d.people[1],rights=())
    d=replace(d,people=(d.people[0],bad))
    result=solve_feasibility(d,time_limit=2)
    assert result.status=='infeasible'
    assert any(i.rule=='eligibility' and i.person_id=='B' and i.event_id==b.id for i in result.issues)
    assert not any(i.event_id=='thursday-A' for i in result.issues)


def test_new_assignment_cannot_break_hard_leave_even_when_wish_exception_exists():
    d,b=granted()
    leave=Entry('hard-B','B','urlaub',Interval.local('2026-11-10T00:00','2026-11-11T00:00'),frozenset({date(2026,11,10)}))
    # The only assignment would violate leave. It is not fixed and must stay open.
    d=replace(d,locked=(),absences=d.absences+(leave,))
    result=solve_feasibility(d,time_limit=2)
    assert not result.blocks and result.open_slots==((b.id,1),)
    assert result.status=='incomplete'
