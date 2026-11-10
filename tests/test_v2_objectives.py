"""E2 mit synthetischen, ausdrücklich gewählten Zielhierarchien."""
from dataclasses import replace
from datetime import date
from fractions import Fraction
from time import monotonic

import pytest

from dienstplan.v2.accounting import MonthAccount
from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import Contract,Contracts
from dienstplan.v2.entries import Entry
from dienstplan.v2.improvement import improve
from dienstplan.v2.objectives import ObjectiveProfile,evaluate
from dienstplan.v2.reporting import FairnessPolicy,ShareRow
from dienstplan.v2.solver import solve_feasibility
from dienstplan.v2.time import Interval
from dienstplan.v2.wishes import WishHistory,WishPolicy
from test_v2_solver import inputs
from test_v2_validation import person,pause


def profile(data,order,**kw):
    return ObjectiveProfile('E0 – synthetische Optimierung',tuple(order),tuple(MonthAccount(p.id,0) for p in data.people),
                            WishPolicy('W0 – synthetisch','2026-01',False,True,1),FairnessPolicy('F0 – synthetisch','contract'),**kw)


def wish(pid,day):
    return Entry(pid+str(day),pid,'freiwunschtag',Interval.local(f'2026-11-{day:02d}T00:00',f'2026-11-{day+1:02d}T00:00'))


def test_cp_stages_protect_two_wishes_before_six_and_preserve_higher_values():
    terms=tuple(event('KC10',date(2026,11,d)) for d in (1,2,3,4,6,10))
    candidates=tuple(e.assign(chr(67+i)) for i,e in enumerate(terms[:-1]))+(terms[-1].assign('A'),terms[-1].assign('B'))
    wishes=tuple(wish('A',d) for d in (2,10))+tuple(wish('B',d) for d in (1,2,3,4,6,10))
    data=inputs(terms,candidates,people=tuple(person(p) for p in 'ABCDEFGH'),absences=wishes)
    p=profile(data,('wishes','groups','burden','hours_max','shifts'))
    result=solve_feasibility(data,time_limit=4,objective_profile=p)
    assert not result.open_slots and next(b.person_id for b in result.blocks if b.id==terms[-1].id)=='B'
    values=dict(result.objectives)
    assert values['wishes']==1 and values['groups/2']==0 and values['groups/6']==1
    assert result.objectives==evaluate(data,result.blocks,result.events,p)
    assert result.proofs[0].proven


def test_equal_group_protects_person_with_higher_frozen_burden():
    term=event('KC10',date(2026,11,10));wishes=(wish('A',10),wish('B',10))
    data=inputs((term,),tuple(term.assign(p) for p in 'AB'),absences=wishes)
    history=WishHistory(frozenset((('A','old','one','end'),('A','old','two','end'))),('old-confirmation',))
    p=profile(data,('wishes','burden'),history=history)
    result=solve_feasibility(data,time_limit=2,objective_profile=p)
    assert [b.person_id for b in result.blocks]==['B']
    assert dict(result.objectives)['burden/1/max']==2 and dict(result.objectives)['burden/1/squares']==5
    assert result.global_optimal


def test_same_wish_hit_by_two_duties_is_once_in_cp_and_direct_report():
    terms=tuple(event('W17',date(2026,11,d)) for d in (9,10))
    candidates=tuple(e.assign(p,(pause(e.attendance.start_day),)) for e in terms for p in 'AB')
    data=inputs(terms,candidates,absences=(wish('A',10),));p=profile(data,('wishes',))
    # Dieser Fall prüft eindeutige Wunschzählung, keine garantierte Wallclock-
    # Leistung. Langsame native Runner dürfen den gültigen Startplan erhalten.
    # Der CP-Nachweis bleibt zusätzlich Pflicht: kein Pass nur aus Nachbewertung.
    result=solve_feasibility(data,time_limit=10,existing=candidates,objective_profile=p)
    assert len(result.blocks)==4 and not result.open_slots and dict(result.objectives)['wishes']==1
    assert any(proof.name=='wishes' and proof.proven for proof in result.proofs)


def test_hours_normalization_distinguishes_all_below_target_and_local_transfer():
    terms=tuple(event('W17',date(2026,11,d)) for d in (2,4,9,11))
    candidates=tuple(e.assign(p,(pause(e.attendance.start_day),)) for e in terms for p in 'ABC')
    old=tuple(e.assign('A' if i<3 else 'B',(pause(e.attendance.start_day),)) for i,e in enumerate(terms))+tuple(e.assign('C',(pause(e.attendance.start_day),)) for e in terms)
    data=inputs(terms,candidates,people=tuple(person(p) for p in 'ABC'))
    p=profile(data,('hours_max','hours_spread'))
    improved=improve(data,old,terms,p,deadline=monotonic()+2)
    assert dict(evaluate(data,improved,terms,p))['hours_spread']<dict(evaluate(data,old,terms,p))['hours_spread']
    assert len(improved)==len(old)
    result=solve_feasibility(data,time_limit=3,existing=old,objective_profile=p)
    assert tuple(v for _,v in result.objectives)<=tuple(v for _,v in evaluate(data,improved,terms,p))


def test_shift_swap_improves_distribution_with_unchanged_hours_and_hard_rules():
    days=(date(2026,11,9),date(2026,11,11))
    terms=tuple(event(code,d) for d in days for code in ('KC10','KC16'))
    candidates=tuple(e.assign(p,() if e.service.code=='KC10' else (pause(e.attendance.start_day),)) for e in terms for p in 'AB')
    old=tuple(c for c in candidates if (c.code=='KC10' and c.person_id=='A') or (c.code=='KC16' and c.person_id=='B'))
    data=inputs(terms,candidates);p=profile(data,('shifts',))
    changed=improve(data,old,terms,p,deadline=monotonic()+2)
    assert dict(evaluate(data,changed,terms,p))['shifts']<dict(evaluate(data,old,terms,p))['shifts']
    assert all(sum(b.person_id==pid and b.code==code for b in changed)==1 for pid in 'AB' for code in ('KC10','KC16'))


def test_historical_special_shares_prefer_previously_underrepresented_people():
    term=event('WL',date(2026,11,10));candidates=tuple(term.assign(p,(pause(date(2026,11,10)),)) for p in 'ABC')
    data=inputs((term,),candidates,people=tuple(person(p) for p in 'ABC'))
    old=tuple(ShareRow(p,'WL',2 if p=='A' else 0,900 if p=='A' else 0,Fraction(2,3),Fraction(300)) for p in 'ABC')
    p=profile(data,('shifts',),historical_shares=old)
    result=solve_feasibility(data,time_limit=3,objective_profile=p)
    assert {b.person_id for b in result.blocks}=={'B','C'} and not result.open_slots


def test_zero_contracts_and_pre_cancel_keep_valid_incumbent_without_global_claim():
    term=event('KC10',date(2026,11,10));a=person()
    a=replace(a,contracts=Contracts('A',(Contract('A',a.employment.dates,'0'),)))
    data=inputs((term,),(term.assign('A'),),people=(a,));p=profile(data,('hours_max','hours_spread','shifts'))
    from threading import Event
    cancel=Event();cancel.set()
    result=solve_feasibility(data,time_limit=2,existing=(term.assign('A'),),cancel=cancel,objective_profile=p)
    assert result.blocks==(term.assign('A'),) and result.coverage_optimal and not result.global_optimal
    assert dict(result.objectives)['hours_max']==6000


def test_late_pause_preference_cannot_override_coverage_or_protected_team():
    term=event('W17',date(2026,11,10));day=term.attendance.start_day
    candidates=tuple(term.assign(p,(pause(day,clock,end),)) for p in 'AB' for clock,end in (('21:00','21:30'),('22:00','22:30')))
    data=inputs((term,),candidates);p=profile(data,('late_break',))
    result=solve_feasibility(data,time_limit=2,objective_profile=p)
    assert not result.open_slots and dict(result.objectives)['late_break']==0


def test_conditional_proofs_and_restricted_integer_domains_are_explicit():
    from dienstplan.v2.solver import StageProof
    first=StageProof('coverage',1,False,(),False)
    second=StageProof('shifts',0,True,(('coverage',1),),True)
    assert not first.proven and second.conditional
    term=event('KC10',date(2026,11,10));data=inputs((term,),(term.assign('A'),))
    with pytest.raises(ValueError,match='Skalierung'):profile(data,('hours_max',),scale=0)
    with pytest.raises(ValueError,match='Testprofil'):replace(profile(data,()),synthetic=False)


def test_actual_later_proof_is_conditional_if_higher_stage_was_unproven(monkeypatch):
    from dienstplan.v2 import solver
    original=solver.cp_model.CpSolver.solve;calls=[]
    def search(self,*args,**kwargs):
        status=original(self,*args,**kwargs);calls.append(status)
        return solver.cp_model.FEASIBLE if len(calls)==2 and status==solver.cp_model.OPTIMAL else status
    monkeypatch.setattr(solver.cp_model.CpSolver,'solve',search)
    term=event('KC10',date(2026,11,10));data=inputs((term,),tuple(term.assign(p) for p in 'AB'))
    result=solve_feasibility(data,time_limit=2,objective_profile=profile(data,('hours_max','shifts')))
    assert len(result.proofs)==3 and result.proofs[0].proven
    assert not result.proofs[1].proven and result.proofs[2].conditional and not result.global_optimal


def test_three_cycle_is_found_when_no_valid_transfer_or_pair_swap_exists():
    terms=tuple(event(code,date(2026,11,10)) for code in ('KC10','KC16','W17'))
    permitted={'KC10':'AC','KC16':'AB','W17':'BCD'}
    candidates=tuple(e.assign(pid,() if e.service.code=='KC10' else (pause(e.attendance.start_day),)) for e in terms for pid in permitted[e.service.code])
    old=tuple(c for c in candidates if (c.code,c.person_id) in {('KC10','A'),('KC16','B'),('W17','C'),('W17','D')})
    data=inputs(terms,candidates,people=tuple(person(pid) for pid in 'ABCD'))
    history=tuple(ShareRow(pid,code,10,4500,Fraction(0),Fraction(0)) for pid,code in (('A','KC10'),('B','KC16'),('C','W17')))
    p=profile(data,('shifts',),historical_shares=history)
    result=improve(data,old,terms,p,deadline=monotonic()+2)
    assert {(b.code,b.person_id) for b in result}=={('KC10','C'),('KC16','A'),('W17','B'),('W17','D')}


def test_manual_individual_fixations_survive_search_and_local_changes():
    term=event('WL',date(2026,11,10));candidates=tuple(term.assign(pid,(pause(date(2026,11,10)),)) for pid in 'ABC')
    fixed=candidates[0];data=replace(inputs((term,),candidates,people=tuple(person(pid) for pid in 'ABC')),locked=(fixed,))
    history=tuple(ShareRow(pid,'WL',10 if pid=='A' else 0,4500 if pid=='A' else 0,Fraction(0),Fraction(0)) for pid in 'ABC')
    p=profile(data,('shifts',),historical_shares=history)
    result=solve_feasibility(data,time_limit=2,objective_profile=p)
    assert fixed in result.blocks and not result.open_slots


def test_broad_special_distribution_and_wl_tuesday_preference():
    from dienstplan.v2.calendar_rules import WeekPolicy,WeekQuota
    from dienstplan.v2.contracts import DateRange
    terms=tuple(event('WL',date(2026,11,d)) for d in (10,15))
    candidates=tuple(e.assign(pid,(pause(e.attendance.start_day),)) for e in terms for pid in 'ABCD')
    data=inputs(terms,candidates,people=tuple(person(pid) for pid in 'ABCD'),optional_ids=frozenset(e.id for e in terms),
                quotas=(WeekQuota('week','WL',DateRange(date(2026,11,9),date(2026,11,16)),1,'2026-11'),),
                week_policy=WeekPolicy('week_start','both','Q0'))
    result=solve_feasibility(data,time_limit=2,objective_profile=profile(data,('weekday','shifts')))
    assert result.events==(terms[0],) and not result.open_slots


def test_eight_special_slots_spread_across_eight_of_twelve_comparable_people():
    from dienstplan.v2.demo import technical_demo
    data,p,old=technical_demo()
    result=improve(data,old,data.events,p,deadline=monotonic()+10)
    assert len(result)==8 and len({b.person_id for b in result})==8
