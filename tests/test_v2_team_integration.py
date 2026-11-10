"""Gemeinsame Zwölfer-Teaminstanz, kein vollständiger Betriebsmonat."""
from datetime import date
from dataclasses import replace

import pytest

from dienstplan.v2.accounting import leave_credits
from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import Contract,Contracts,DateRange,Employment
from dienstplan.v2.solver import solve_feasibility,verify
from test_v2_solver import inputs
from test_v2_validation import person,pause
from test_v2_objectives import profile


@pytest.mark.parametrize('occasion,total',[('T',3465),('TS',4425)])
def test_d03_d04_full_twelve_person_team_is_counted_once(occasion,total):
    day=date(2026,11,12)
    terms=tuple(event(key,day) for key in ('KCT10','KCT','TW',occasion))
    people=tuple(person(chr(65+i)) for i in range(12));candidates=[]
    for e in terms:
        breaks=() if e.service.code in {'T','TS'} else (pause(day,'13:00','13:30'),) if e.service.code=='KCT10' else (pause(day),)
        candidates.extend(e.assign(p.id,breaks) for p in people)
    data=inputs(terms,candidates,people=people)
    result=solve_feasibility(data,time_limit=3,objective_profile=profile(data,('participation',)))
    assert not result.open_slots and len(result.blocks)==12
    assert sum(b.work_minutes for b in result.blocks)==total
    assert sum(b.code==occasion for b in result.blocks)==8
    core,calendar=verify(data,result.blocks,active_events=result.events)
    assert core.hard_ok and calendar.hard_ok and len(core.participation)==12
    assert dict(result.objectives)['participation']==0
    assert sum(state=='T erfüllt; TS-Ausnahme' for _,_,state in core.participation)==(4 if occasion=='TS' else 0)


def test_d07_o03_bk_exception_does_not_force_team_after_only_630_minutes_rest():
    team=event('T',date(2026,11,12));bk=event('BK',date(2026,11,11))
    boundary=tuple(bk.assign(pid,(pause(date(2026,11,11)),)) for pid in 'AB')
    people=tuple(person(chr(65+i)) for i in range(12))
    data=inputs((team,),tuple(team.assign(p.id) for p in people),people=people,boundary=boundary)
    result=solve_feasibility(data,time_limit=3,objective_profile=profile(data,('participation',)))
    assert len(result.blocks)==10 and not {b.person_id for b in result.blocks}&{'A','B'}
    core,_=verify(data,result.blocks,active_events=result.events)
    assert core.hard_ok and sum(state=='ausgenommen' for _,_,state in core.participation)==2
    assert dict(result.objectives)['participation']==0


def test_u04_daily_contract_versions_give_exact_1968_credit_minutes():
    contracts=Contracts('A',(Contract('A',DateRange(date(2026,11,1),date(2026,11,11)),'37'),
                             Contract('A',DateRange(date(2026,11,11),date(2026,12,1)),'30')))
    employment=Employment('A',DateRange(date(2026,11,1),date(2026,12,1)))
    credit=leave_credits(contracts,employment,[date(2026,11,d) for d in range(9,14)])[0]
    assert credit.raw_minutes==credit.minutes==1968
