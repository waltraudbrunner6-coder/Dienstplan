"""M1-Monatsbuchung bleibt getrennt von M0 und physischen Kalendermengen."""
from dataclasses import replace
from datetime import date
import csv
import io
import json
import zipfile

import pytest
from dienstplan.v2.accounting import MonthAccount,s0_target
from dienstplan.v2.catalog import event
from dienstplan.v2.codec import workspace,restore_workspace
from dienstplan.v2.exporting import export_package
from dienstplan.v2.objectives import evaluate
from dienstplan.v2.reporting import booked_work_minutes,booked_required_work_range,required_work_range,hours_rows,quantity_rows
from dienstplan.v2.serialization import fingerprint
from dienstplan.v2.solver import solve_feasibility
from dienstplan.v2.time import Interval
from dienstplan.v2.work import WorkBlock
from test_v2_objectives import profile
from test_v2_solver import inputs
from test_v2_validation import person,pause


def overnight(day='2026-11-30',end='2026-12-01'):
    term=event('FK',date.fromisoformat(day),people=('A',),attendance=Interval.local(day+'T17:00',end+'T01:00'))
    return term,term.assign('A',(pause(date.fromisoformat(day)),))


def test_m1_books_full_night_in_start_month_while_m0_remains_unchanged():
    _,block=overnight()
    assert block.work_minutes==450
    assert booked_work_minutes(block,2026,11,month_profile='M1')==450
    assert booked_work_minutes(block,2026,12,month_profile='M1')==0
    assert booked_work_minutes(block,2026,11,month_profile='M0')==390
    assert booked_work_minutes(block,2026,12,month_profile='M0')==60
    physical=quantity_rows((block,),frozenset({date(2026,12,1)}))
    assert [(q.day,q.work_minutes,q.night_minutes,q.holiday_minutes) for q in physical]==[
        (date(2026,11,30),390,120,0),(date(2026,12,1),60,60,60)]


def test_year_boundary_and_pause_after_midnight_keep_actual_work():
    block=WorkBlock('year','A','FK',Interval.local('2026-12-31T20:00','2027-01-01T04:00'),
                    (Interval.local('2027-01-01T00:00','2027-01-01T00:30'),))
    assert booked_work_minutes(block,2026,12,month_profile='M1')==450
    assert booked_work_minutes(block,2027,1,month_profile='M1')==0
    assert booked_work_minutes(block,2026,12,month_profile='M0')==240
    assert booked_work_minutes(block,2027,1,month_profile='M0')==210
    rows=quantity_rows((block,),frozenset({date(2027,1,1)}))
    assert sum(q.work_minutes for q in rows)==450
    assert rows[-1].holiday_minutes==210


def test_m1_uses_real_dst_duration_and_exact_unpaid_pause():
    block=WorkBlock('dst','A','BK',Interval.local('2026-10-24T20:00','2026-10-25T04:00'),
                    (Interval.local('2026-10-24T21:00','2026-10-24T21:30'),))
    assert block.attendance.minutes==540
    assert booked_work_minutes(block,2026,10,month_profile='M1')==510
    assert sum(q.work_minutes for q in quantity_rows((block,)))==510
    with pytest.raises(ValueError):booked_work_minutes(block,2026,10,month_profile='unknown')


@pytest.mark.parametrize('booking,expected_work',[('M0',630),('M1',450)])
def test_cp_and_direct_hours_use_same_month_booking_with_boundary(booking,expected_work):
    term,block=overnight();p=person('A')
    past=event('BK',date(2026,10,31)).assign('A',(pause(date(2026,10,31)),))
    data=inputs((term,),(block,),people=(p,),boundary=(past,))
    target=s0_target(p.contracts,p.employment,2026,11,profile='S0').minutes
    objective=replace(profile(data,('hours_max','hours_spread')),month_profile=booking,
                      accounts=(MonthAccount('A',target-450),))
    result=solve_feasibility(data,time_limit=4,objective_profile=objective,existing=(block,),existing_events=(term,))
    assert not result.open_slots
    assert result.objectives==evaluate(data,result.blocks,result.events,objective)
    rows=hours_rows(data.people,(past,block),(),2026,11,accounts=objective.accounts,target_profile='S0',month_profile=booking)
    assert rows[0].work==expected_work and rows[0].deviation==expected_work-450
    assert (dict(result.objectives)['hours_max']==0)==(booking=='M1')
    assert result.proofs and all(p.proven for p in result.proofs)


def test_m0_snapshot_is_not_revalued_when_m1_is_supported_and_export_is_explicit(tmp_path):
    term,block=overnight();data=inputs((term,),(block,),people=(person('A'),))
    old=profile(data,('hours_max',));saved=workspace(data,old,(block,),(term,));before=json.dumps(saved,sort_keys=True)
    restored=restore_workspace(json.loads(before))
    assert restored[1].month_profile=='M0' and json.dumps(saved,sort_keys=True)==before
    assert hours_rows(data.people,(block,),(),2026,11,accounts=old.accounts,target_profile='S0',month_profile='M0')[0].work==390
    new=replace(old,month_profile='M1')
    report=export_package(tmp_path/'plan.zip',data,new,(block,),(term,),holidays=frozenset({date(2026,12,1)}))
    assert report['month_booking_profile']=='M1' and 'Dienstbeginn' in report['month_booking_rule']
    with zipfile.ZipFile(tmp_path/'plan.zip') as archive:
        rows=list(csv.DictReader(io.StringIO(archive.read('stunden.csv').decode('utf-8-sig')),delimiter=';'))
        assert rows[0]['work_hours']=='7,50'
        physical=list(csv.DictReader(io.StringIO(archive.read('zeitmengen.csv').decode('utf-8-sig')),delimiter=';'))
        assert [r['work_hours'] for r in physical]==['6,50','1,00']
        assert restore_workspace(json.loads(archive.read('arbeitsstand.json')))[1].month_profile=='M1'


def test_start_month_demand_counts_both_positions_and_does_not_double_boundary():
    term=event('BK',date(2026,11,30));one=term.assign('A',(pause(date(2026,11,30)),))
    # 2 × 7.5 Stunden; physische Buchung lässt 4 Stunden je Person im Dezember.
    assert booked_required_work_range((term,),(one,),2026,11,month_profile='M1',boundary=(one,))==(900,900)
    assert booked_required_work_range((term,),(one,),2026,12,month_profile='M1',boundary=(one,))==(0,0)
    assert booked_required_work_range((),(),2026,11,month_profile='M1',boundary=(one,one))==(450,450)
    assert booked_required_work_range((term,),(one,),2026,12,month_profile='M0')[0]>0


def test_confirmed_full_reserve_duration_is_included_by_explicit_booking_api():
    terms=(event('R_early',date(2026,12,31)),event('R_late',date(2026,12,31)))
    assert booked_required_work_range(terms,(),2026,12,month_profile='M1')==(810,810)
    assert booked_required_work_range(terms,(),2027,1,month_profile='M1')==(0,0)
    assert booked_required_work_range(terms,(),2026,12,month_profile='M1',include_reserve=False)==(0,0)
    # Alte Aufrufer können ihre vor Bestätigung bestehende R-Ausnahme behalten.
    assert required_work_range(terms,(),2026,12)==(0,0)
    assert required_work_range(terms,(),2026,12,include_reserve=True)==(810,810)


def test_export_retains_calendar_quantities_of_previous_month_boundary_without_rebooking(tmp_path):
    past=event('BK',date(2026,10,31)).assign('A',(pause(date(2026,10,31)),))
    data=inputs((),(),people=(person('A'),),boundary=(past,))
    objective=replace(profile(data,()),month_profile='M1')
    export_package(tmp_path/'boundary.zip',data,objective,(),(),holidays=frozenset({date(2026,11,1)}))
    with zipfile.ZipFile(tmp_path/'boundary.zip') as archive:
        hours=list(csv.DictReader(io.StringIO(archive.read('stunden.csv').decode('utf-8-sig')),delimiter=';'))
        quantities=list(csv.DictReader(io.StringIO(archive.read('zeitmengen.csv').decode('utf-8-sig')),delimiter=';'))
        assert hours[0]['work_hours']=='0,00'
        november=next(q for q in quantities if q['day']=='"2026-11-01"')
        assert november['work_hours']==november['night_hours']==november['holiday_hours']=='4,00'


def test_confirmed_m0_hours_and_fingerprint_remain_frozen_after_m1_calculation(tmp_path):
    from dienstplan.v2.persistence import V2Store
    term,block=overnight();data=inputs((term,),(block,),people=(person('A'),))
    old=profile(data,('hours_max',))
    path=tmp_path/'confirmed.sqlite3'
    with V2Store(path,create=True) as store:
        store.save_workspace(data,old,(block,),(term,),expected_revision=0)
        saved=store.confirm('nov-m0',data,(block,),(term,),accounts=old.accounts,wish_policy=old.wish_policy,
            fairness_policy=old.fairness_policy,target_profile='S0',month_profile='M0',
            expected_revision=store.input_revision,synthetic=True)
        before=json.dumps(saved,sort_keys=True)
        assert saved['hours'][0]['work']==390
        new=replace(old,month_profile='M1')
        assert hours_rows(data.people,(block,),(),2026,11,accounts=new.accounts,target_profile='S0',month_profile='M1')[0].work==450
    with V2Store(path) as store:
        assert json.dumps(store.confirmed_month(2026,11),sort_keys=True)==before
        loaded=store.load_workspace(2026,11)
        assert loaded[1].month_profile=='M0'
