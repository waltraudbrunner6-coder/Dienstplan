"""Rohhistorie und Rechenprofile ausschließlich mit fiktiven Personen/Dateien."""
from dataclasses import replace
from datetime import date
from fractions import Fraction
import json

import pytest

from dienstplan.v2.accounting import MonthAccount
from dienstplan.v2.allowances import allowances,austrian_holidays
from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import Contract,Contracts,DateRange
from dienstplan.v2.entries import Entry
from dienstplan.v2.errors import DomainError
from dienstplan.v2.history import historical_shares
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.profiles import Profile,Profiles
from dienstplan.v2.reporting import FairnessPolicy,hours_rows,quantity_rows,shares
from dienstplan.v2.solver import solve_feasibility
from dienstplan.v2.time import Interval
from dienstplan.v2.wishes import WishHistory,WishPolicy,relevant_wishes,wish_rows
from test_v2_solver import inputs
from test_v2_validation import person,pause

WISH=WishPolicy('W0 – synthetisch','2026-10',False,True,1)
FAIR=FairnessPolicy('F0 – synthetisch','contract')


def wish(pid,start,end,kind='freiwunschtag',owner=None):
    return Entry(pid+start,pid,kind,Interval.local(start,end),budget_month=owner)


def confirm(store,id,data,blocks,**kw):
    args=dict(accounts=tuple(MonthAccount(p.id,0) for p in data.people),wish_policy=WISH,fairness_policy=FAIR,
              target_profile='S0',month_profile='M0',expected_revision=store.input_revision,synthetic=True)
    args.update(kw)
    return store.confirm(id,data,blocks,data.events,**args)


def test_unique_relevant_wish_counts_once_across_two_shifts_and_duplicates():
    a=event('W17',date(2026,11,9));b=event('W17',date(2026,11,10))
    wanted=wish('A','2026-11-10T00:00','2026-11-11T00:00')
    irrelevant=wish('A','2026-11-16T00:00','2026-11-17T00:00')
    blocks=tuple(e.assign('A',(pause(e.attendance.start_day),)) for e in (a,b))
    rows=wish_rows((person(),),(wanted,replace(wanted,id='duplicate',comment='anders'),irrelevant),(a,b),blocks,policy=WISH)
    assert len(rows[0].relevant)==len(rows[0].violated)==len(rows[0].cumulative)==1
    assert rows[0].fulfilled_count==0
    assert relevant_wishes((irrelevant,),(a,b))==()


def test_explicit_weekend_wish_variants_do_not_change_protection_count():
    term=event('W17',date(2026,11,13));wanted=wish('A','2026-11-14T00:00','2026-11-16T00:00','wochenendwunsch','2026-11')
    block=term.assign('A',(pause(date(2026,11,13)),))
    strict=wish_rows((person(),),(wanted,),(term,),(block,),policy=WISH)[0]
    exception=wish_rows((person(),),(wanted,),(term,),(block,),policy=replace(WISH,weekend_friday_exception=True))[0]
    assert len(strict.violated)==1 and not exception.violated


def test_confirmation_idempotent_and_drafts_have_no_history(tmp_path):
    term=event('KC10',date(2026,11,10));wanted=wish('A','2026-11-10T00:00','2026-11-11T00:00')
    data=inputs((term,),(term.assign('A'),),absences=(wanted,))
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        for i in range(3):store.save_draft_revision('draft'+str(i),{'unconfirmed':True})
        assert not store.wish_history('2026-12',policy=WISH).violated
        saved=confirm(store,'nov',data,(term.assign('A'),));revision=store.input_revision
        assert saved==confirm(store,'nov',data,(term.assign('A'),)) and store.input_revision==revision
        history=store.wish_history('2026-12',policy=WISH)
        assert history.violated==frozenset({wanted.identity}) and history.confirmation_ids==('nov',)
        assert len(history.missing)==1 and '2026-10' in history.missing[0]
        # Aktueller Monat/Folgemonate sind keine historische Quelle.
        assert not store.wish_history('2026-11',policy=WISH).violated
        with pytest.raises(DomainError,match='bestätigt'):confirm(store,'other',data,(term.assign('A'),))
        with pytest.raises(DomainError,match='bestätigt'):confirm(store,'nov',replace(data,profile_label='Änderung'),(term.assign('A'),))


def test_reopen_and_changed_contract_or_wishes_cannot_rewrite_old_facts(tmp_path):
    file=tmp_path/'test.sqlite3';term=event('KC10',date(2026,11,10))
    wanted=wish('A','2026-11-10T00:00','2026-11-11T00:00');data=inputs((term,),(term.assign('A'),),absences=(wanted,))
    with V2Store(file,create=True) as store:saved=confirm(store,'nov',data,(term.assign('A'),))
    with V2Store(file) as store:
        old=store.confirmations()[0][1]
        changed=replace(data,absences=(),people=(replace(person(),contracts=Contracts('A',(Contract('A',person().employment.dates,'30'),))),person('B')))
        assert changed.people[0].contracts.at(date(2026,12,1)).weekly_hours==30
        assert old==saved and old['hours'][0]['target']==6429
        assert old['inputs']['people'][0]['contracts']['versions'][0]['weekly_hours']=={'numerator':25,'denominator':1}
        assert store.wish_history('2026-12',policy=WISH).violated==frozenset({wanted.identity})
        past=historical_shares(store.confirmations(),start='2026-10',month='2026-12')
        assert past[0].expected_count==Fraction(1,2) and past[0].count==1
        assert historical_shares(store.confirmations(),start='2026-12',month='2027-01')==()
        old['hours'][0]['target']=0
        assert store.confirmations()[0][1]['hours'][0]['target']==6429


def test_same_cross_month_wish_is_one_cumulative_historical_identity(tmp_path):
    wanted=wish('A','2026-10-31T00:00','2026-11-02T00:00','wochenendwunsch','2026-10')
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        for month,day in ((10,31),(11,1)):
            term=event('W17',date(2026,month,day))
            blocks=tuple(term.assign(p,(pause(date(2026,month,day)),)) for p in 'AB')
            data=replace(inputs((term,),blocks,absences=(wanted,)),month=month)
            confirm(store,f'month{month}',data,blocks)
        history=store.wish_history('2026-12',policy=WISH)
        assert len(history.confirmation_ids)==2 and history.violated==frozenset({wanted.identity})
        rows=wish_rows((person(),),(wanted,),(term,),blocks,policy=WISH,history=history)
        assert len(rows[0].historical)==len(rows[0].cumulative)==1


def test_confirmation_revalidates_and_transaction_failure_rolls_back(tmp_path):
    term=event('KC10',date(2026,11,10));block=term.assign('A');data=inputs((term,),(block,))
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        with pytest.raises(DomainError,match='freigegeben'):confirm(store,'nov',data,(block,),synthetic=False)
        with pytest.raises(DomainError,match='Offene Plätze'):confirm(store,'nov',data,())
        with pytest.raises(DomainError,match='Eingaben/Historie'):confirm(store,'nov',data,(block,),expected_revision=999)
        store.connection.execute("CREATE TRIGGER stop_confirmation BEFORE INSERT ON v2_meta WHEN NEW.key LIKE 'confirmation:%' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(Exception,match='test failure'):confirm(store,'nov',data,(block,))
        assert not store.confirmations() and store.input_revision==0
        assert not store.connection.execute("SELECT id FROM v2_revisions WHERE id='nov'").fetchall()


def test_confirmation_corruption_is_detected_without_reconstructing_live_entries(tmp_path):
    term=event('KC10',date(2026,11,10));data=inputs((term,),(term.assign('A'),))
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        saved=confirm(store,'nov',data,(term.assign('A'),));saved['hours'][0]['target']=0
        store.connection.execute('UPDATE v2_revisions SET payload=? WHERE id=?',(json.dumps(saved),'nov'))
        with pytest.raises(DomainError,match='Fingerprint'):store.confirmations()


def test_shared_week_reservations_are_atomic_and_cannot_be_changed_in_next_month(tmp_path):
    from dienstplan.v2.calendar_rules import WeekPolicy,WeekQuota
    quotas=tuple(WeekQuota(code,code,DateRange(date(2026,11,30),date(2026,12,7)),1,'2026-11') for code in ('WL','BK'))
    policy=WeekPolicy('week_start','both','Q0 synthetisch')
    def data(month,days):
        terms=tuple(event(code,day) for code,day in zip(('WL','BK'),days))
        blocks=tuple(e.assign(p,(pause(e.attendance.start_day),)) for e in terms for p in 'AB')
        return replace(inputs(terms,blocks,quotas=quotas,week_policy=policy),month=month),blocks
    november,blocks=data(11,(date(2026,11,30),date(2026,12,2)))
    december,new_blocks=data(12,(date(2026,12,1),date(2026,12,3)))
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        saved=confirm(store,'nov',november,blocks);revision=store.input_revision
        assert len(saved['events'])==1 and saved['events'][0]['service']['code']=='WL'
        assert saved['quota_reservations']=={'WL':['2026-11-30/WL'],'BK':['2026-12-02/BK']}
        with pytest.raises(DomainError,match='Randwochenbindung'):confirm(store,'dec',december,new_blocks)
        assert len(store.confirmations())==1 and store.input_revision==revision
        overridden=confirm(store,'dec',december,new_blocks,allow_violations=True)
        assert overridden['confirmation_override'] and any('Randwochenbindung' in m for m in overridden['warnings'])
        assert len(store.confirmations())==2


def test_exact_leave_credit_union_and_negative_work_goal_without_negative_assignment():
    p=replace(person(),contracts=Contracts('A',(Contract('A',person().employment.dates,'25.04'),)))
    vacation=Entry('v','A','urlaub',Interval.local('2026-11-09T00:00','2026-11-14T00:00'),frozenset(date(2026,11,d) for d in range(9,14)))
    rows=hours_rows((p,),(),(vacation,replace(vacation,id='duplicate')),2026,11,
                    accounts=(MonthAccount('A',10000),),target_profile='S0',month_profile='M0')
    row=rows[0]
    assert row.raw_credits==Fraction(7512,5) and row.credits==1502
    assert row.goal<0 and row.work==0 and row.projected>0 and row.deviation==-row.goal
    with pytest.raises(DomainError,match='ausdrücklich'):hours_rows((p,),(),(),2026,11,accounts=(MonthAccount('A',0),),target_profile=None,month_profile='M0')


def test_rights_and_time_valid_contracts_define_explicit_fair_pools():
    a=person('A',codes=('KC10',));b=person('B',codes=('W17',));outside=event('W17',date(2026,11,10))
    result=shares((a,b),(outside,),(),policy=FAIR)
    assert result[0].expected_count==0 and result[1].expected_count==2
    a=person();b=replace(person('B'),contracts=Contracts('B',(Contract('B',person('B').employment.dates,'50'),)))
    result=shares((a,b),(outside,),(),policy=FAIR)
    assert result[0].expected_count==Fraction(2,3) and result[1].expected_count==Fraction(4,3)
    zero=replace(a,contracts=Contracts('A',(Contract('A',a.employment.dates,'0'),)))
    assert shares((zero,),(outside,),(),policy=FAIR)[0].expected_count==0
    assert shares((zero,),(outside,),(),policy=replace(FAIR,mode='absolute'))[0].expected_count==2


def test_national_test_calendar_and_overlapping_allowance_quantities():
    holidays=austrian_holidays(2026,profile='AT_TEST')
    assert len(holidays)==13 and {date(2026,4,6),date(2026,5,14),date(2026,5,25),date(2026,6,4)}<=holidays
    assert date(2026,12,24) not in holidays and date(2026,12,31) not in holidays
    assert {date(2026,12,25),date(2026,12,26)}<=holidays
    term=event('N17',date(2026,10,31),people=('A',));block=term.assign('A',(pause(date(2026,10,31)),))
    rows=quantity_rows((block,),holidays);nov=next(q for q in rows if q.day==date(2026,11,1))
    assert nov.work_minutes==nov.night_minutes==nov.sunday_minutes==nov.holiday_minutes==60
    result=allowances((nov,),profiles=Profiles(()),scope='test')
    assert len(result)==3 and all(r.euros is None and 'ungeklärt' in r.explanation for r in result)


def test_synthetic_time_valid_tariff_uses_exact_rates_without_legal_claim():
    from dienstplan.v2.reporting import QuantityRow
    rows=(QuantityRow('A',date(2026,12,31),60,60,0,0),QuantityRow('A',date(2027,1,1),60,60,0,0))
    profiles=Profiles(tuple(Profile(str(year),'night_rate','test',DateRange(date(year,1,1),date(year+1,1,1)),
                                   json.dumps({'euros_per_hour':str(rate)}),synthetic=True) for year,rate in ((2026,2),(2027,3))))
    assert all(r.euros is None for r in allowances(rows,profiles=profiles,scope='test'))
    result=allowances(rows,profiles=profiles,scope='test',allow_synthetic=True)
    assert sum(r.euros for r in result)==5 and all('keine KV' in r.explanation for r in result)
