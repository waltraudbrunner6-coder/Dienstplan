"""Synthetische KC15-Gegenbeispiele; keine Personen-/Datums-Sonderbehandlung."""
from dataclasses import replace
from datetime import date
from threading import Event
import pytest
from dienstplan.v2.catalog import event
from dienstplan.v2.entries import Entry
from dienstplan.v2.fallback import with_kc15_fallbacks,default_fallback_events,dissolve_fallback_groups
from dienstplan.v2.solver import solve_feasibility,verify
from dienstplan.v2.time import Interval
from dienstplan.v2.application import service_candidates
from test_v2_solver import inputs
from test_v2_validation import person


def data(people=2):
    terms=tuple(event(code,date(2026,11,10)) for code in ('KC10','KC16'))
    persons=tuple(person(chr(65+i),codes={'KC10','KC16','KC15'}) for i in range(people))
    return with_kc15_fallbacks(inputs(terms,service_candidates(terms,persons),people=persons))


def test_complete_regular_pair_is_preferred_to_fully_assignable_replacement():
    d=data(2);result=solve_feasibility(d,time_limit=3)
    assert not result.open_slots
    assert {e.service.code for e in result.events}=={'KC10','KC16'}
    assert dict(result.objectives)['kc15_replacements']==0
    assert verify(d,result.blocks,active_events=result.events)[0].hard_ok


def test_one_person_can_cover_replacement_but_not_two_regular_blocks():
    d=data(1);result=solve_feasibility(d,time_limit=3)
    assert not result.open_slots and len(result.blocks)==1
    assert result.blocks[0].code=='KC15' and result.blocks[0].work_minutes==510
    assert {e.service.code for e in result.events}=={'KC15'}
    assert dict(result.objectives)['kc15_replacements']==1
    assert any('statt KC10 und KC16' in message for message in result.unchecked)
    assert verify(d,result.blocks,active_events=result.events)[0].hard_ok


def test_empty_replacement_cannot_hide_two_open_regular_places():
    d=data(1)
    blocked=Entry('vac','A','urlaub',Interval.local('2026-11-10T00:00','2026-11-11T00:00'),frozenset({date(2026,11,10)}))
    d=replace(d,absences=(blocked,))
    result=solve_feasibility(d,time_limit=3)
    assert not result.blocks and sum(n for _,n in result.open_slots)==2
    assert {e.service.code for e in result.events}=={'KC10','KC16'}


def test_valid_regular_fixation_prevents_replacement():
    d=data(1);fixed=next(c for c in d.candidates if c.code=='KC10')
    d=replace(d,locked=(fixed,))
    result=solve_feasibility(d,time_limit=3)
    assert fixed in result.blocks and len(result.open_slots)==1
    assert all(e.service.code!='KC15' for e in result.events)


def test_independent_checker_rejects_mixed_or_empty_choice():
    d=data(1);group=d.fallbacks[0];terms={e.id:e for e in d.events}
    core,_=verify(d,(),active_events=d.events)
    assert 'kc15_choice' in {i.rule for i in core.issues}
    core,_=verify(d,(),active_events=(terms[group.replacement_id],))
    assert 'kc15_empty' in {i.rule for i in core.issues}
    assert {e.service.code for e in default_fallback_events(d)}=={'KC10','KC16'}


def test_removing_one_regular_term_does_not_generate_fallback():
    d=data(1);changed=dissolve_fallback_groups(d,{d.fallbacks[0].regular_ids[0]})
    changed=replace(changed,events=tuple(e for e in changed.events if e.service.code!='KC10'),candidates=tuple(c for c in changed.candidates if c.code!='KC10'))
    assert not with_kc15_fallbacks(changed).fallbacks
    assert {e.service.code for e in changed.events}=={'KC16'}


def test_cancel_and_empty_deadline_do_not_claim_infeasibility():
    d=data();stop=Event();stop.set()
    assert solve_feasibility(d,cancel=stop).status=='cancelled'
    assert solve_feasibility(d,time_limit=1e-12).status=='unknown'


def test_lexicographic_replacement_count_precedes_hours_and_direct_score_matches():
    from dienstplan.v2.demo import technical_demo
    from dienstplan.v2.accounting import MonthAccount
    from dienstplan.v2.objectives import evaluate
    d=data(2);_,profile,_=technical_demo()
    profile=replace(profile,accounts=tuple(MonthAccount(p.id,0) for p in d.people),month_profile='M1')
    result=solve_feasibility(d,time_limit=3,objective_profile=profile)
    assert not result.open_slots and {e.service.code for e in result.events}=={'KC10','KC16'}
    assert result.objectives==evaluate(d,result.blocks,result.events,profile)
    assert result.objectives[:2]==(('coverage',0),('kc15_replacements',0))


def test_fixed_people_in_regular_event_are_not_silently_made_optional():
    terms=(event('KC10',date(2026,11,10),people=('A',)),event('KC16',date(2026,11,10)))
    persons=(person('A',codes={'KC10','KC16','KC15'}),)
    d=with_kc15_fallbacks(inputs(terms,service_candidates(terms,persons),people=persons))
    assert not d.fallbacks
    result=solve_feasibility(d,time_limit=2)
    assert not any(e.service.code=='KC15' for e in result.events)
    assert any(b.code=='KC10' and b.person_id=='A' for b in result.blocks)
