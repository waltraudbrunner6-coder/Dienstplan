"""Anonymisierte Regression für bestätigte Donnerstagswünsche beim Import.

Diese kleinen Testprofile bilden die Fehlerklasse nach; sie enthalten keine
Zeilen oder Personenbezeichnungen aus hochgeladenen Dienstplänen.
"""
from datetime import date

from dienstplan.v2.application import service_candidates
from dienstplan.v2.calendar_rules import WeekendPolicy,dates,horizon
from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import Contract,Contracts,DateRange,Employment
from dienstplan.v2.entries import WishBudget
from dienstplan.v2.people import Eligibility,Person
from dienstplan.v2.plan_import import prepare_plan_import
from dienstplan.v2.solver import PlanningInput,solve_feasibility,verify


def synthetic_month(day_numbers,person_count=2):
    span=DateRange(date(2026,1,1),date(2028,1,1))
    people=tuple(Person(f'P{i:02d}',f'Fiktive Person {i}',Employment(f'P{i:02d}',span),
                        Contracts(f'P{i:02d}',(Contract(f'P{i:02d}',span,'25'),)),
                        (Eligibility.from_exclusions(span,driving_license=True),)) for i in range(1,person_count+1))
    terms=tuple(event('KC10',date(2026,12,n)) for n in day_numbers)
    known=frozenset((p.id,d) for p in people for d in dates(horizon(2026,12)))
    return PlanningInput(people,terms,service_candidates(terms,people),2026,12,known,
                         WeekendPolicy('sunday','Synthetisches Wochenend-Testprofil'),
                         'Synthetischer Dezember-Import, keine betrieblichen Personendaten')


def duty(number,pid='P01'):
    return dict(art='dienst',datum=f'2026-12-{number:02d}',dienst='KC10',person_id=pid,fixiert='ja')


def wish(number,pid):
    return dict(art='freiwunschtag',datum=f'2026-12-{number:02d}',person_id=pid)


def physical_issues(report):
    # Der unabhängige Prüfer darf eine genehmigte Konfigurationsabweichung
    # weiter melden. Beschäftigung, Rechte, tatsächliche Arbeit und Ruhe gelten.
    return tuple(i for i in report.issues if i.rule!='overridden_rule')


def test_accepted_thursday_wish_of_other_person_does_not_invalidate_valid_lock():
    data=synthetic_month((28,))
    rows=(duty(28),wish(24,'P02'))
    assert not prepare_plan_import(data,rows,budgets={('P02','2026-12'):WishBudget(1)}).ready
    proposal=prepare_plan_import(data,rows,budgets={('P02','2026-12'):WishBudget(1)},allow_rules=True)
    assert proposal.ready and len(proposal.inputs.locked)==1
    result=solve_feasibility(proposal.inputs,time_limit=3,existing=proposal.blocks,existing_events=proposal.events)
    assert result.status in {'feasible','conditional'},(result.status,result.issues)
    assert not result.open_slots and set(proposal.inputs.locked)<=set(result.blocks)
    core,calendar=verify(proposal.inputs,result.blocks,active_events=result.events)
    assert not physical_issues(core) and calendar.hard_ok
    assert any('Donnerstag' in message for message in result.unchecked)


def test_eight_valid_imported_locks_survive_twelve_accepted_configuration_wishes():
    data=synthetic_month((1,2,8,9,15,16,22,23),person_count=4)
    rows=tuple(duty(n,'P01' if i%2==0 else 'P02') for i,n in enumerate((1,2,8,9,15,16,22,23)))
    rows+=tuple(wish(day,f'P{i:02d}') for i in range(1,5) for day in (3,10,17))
    proposal=prepare_plan_import(data,rows,budgets={(p.id,'2026-12'):WishBudget(3) for p in data.people},allow_rules=True)
    assert proposal.ready,proposal.errors
    assert len(proposal.inputs.locked)==8 and len(proposal.inputs.absences)==12
    result=solve_feasibility(proposal.inputs,time_limit=5,existing=proposal.blocks,existing_events=proposal.events)
    assert result.status in {'feasible','conditional'},(result.status,result.issues)
    assert not result.open_slots and set(result.blocks)==set(proposal.blocks)
    core,calendar=verify(proposal.inputs,result.blocks,active_events=result.events)
    assert not physical_issues(core) and calendar.hard_ok
    assert result.unchecked


def test_accepted_wish_does_not_waive_actual_leave_conflicting_with_a_lock():
    data=synthetic_month((28,))
    rows=(duty(28),wish(24,'P02'),dict(art='urlaub',datum='2026-12-28',person_id='P01',gutschrifttage='2026-12-28'))
    proposal=prepare_plan_import(data,rows,budgets={('P02','2026-12'):WishBudget(1)},allow_rules=True)
    assert proposal.ready
    result=solve_feasibility(proposal.inputs,time_limit=3,existing=proposal.blocks,existing_events=proposal.events)
    assert result.status=='infeasible' and not result.blocks
    assert any(issue.rule=='leave' and issue.person_id=='P01' and 'Urlaub' in issue.message for issue in result.issues)
