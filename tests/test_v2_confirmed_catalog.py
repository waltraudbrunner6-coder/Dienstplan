"""Nutzerantworten vom 11.11.2026, ausschließlich fiktive Personen."""
from datetime import date
import pytest
from openpyxl import Workbook
from dienstplan.v2.catalog import event,lb_dates,CalendarInput,month_calendar
from dienstplan.v2.application import demonstration_month,service_candidates
from dienstplan.v2.pauses import automatic_pause_choices
from dienstplan.v2.plan_import import prepare_plan_import
from dienstplan.v2.spreadsheets import read_import
from dienstplan.v2.time import Interval


def row(code,day='2026-12-28',pid='P01',**values):
    return dict(art='dienst',datum=day,dienst=code,person_id=pid,**values)


def test_reserve_is_normal_paid_work_and_gets_real_candidates():
    early=event('R_early',date(2026,12,28));late=event('R_late',date(2026,12,28))
    assert early.assign('P01').work_minutes==360
    assert automatic_pause_choices(late,'P02')[0].work_minutes==450
    data,_,_=demonstration_month(2026,12)
    choices=service_candidates((early,late),data.people)
    assert {b.code for b in choices}=={'R'}
    assert len({b.person_id for b in choices})==12
    assert not any('F02' in m for m in month_calendar(2026,12,CalendarInput()).missing)


def test_reserve_import_accepts_defined_window_and_infers_only_explicit_matching_times():
    data,_,_=demonstration_month(2026,12)
    proposal=prepare_plan_import(data,[row('R_early')])
    assert proposal.ready,proposal.errors
    assert proposal.blocks[0].work_minutes==360
    proposal=prepare_plan_import(data,[row('R',beginn='2026-12-28T16:00',ende='2026-12-29T00:00')])
    assert proposal.ready,proposal.errors
    assert proposal.blocks[0].work_minutes==450
    bad=prepare_plan_import(data,[row('R')])
    assert not bad.ready and any('Zeitfenster' in m for m in bad.errors)
    assert not any('Arbeitsbewertung' in m for m in bad.errors)


def test_lb_default_anchor_and_persistent_fortnightly_dates():
    assert lb_dates(2026,11)==()
    assert lb_dates(2026,12)==(date(2026,12,3),date(2026,12,17),date(2026,12,31))
    assert lb_dates(2027,1)==(date(2027,1,14),date(2027,1,28))
    settings=CalendarInput(lb_people=('P01','P02'))
    calendar=month_calendar(2026,12,settings)
    assert tuple(e.attendance.start_day for e in calendar.events if e.service.code=='LB')==lb_dates(2026,12)
    missing=month_calendar(2026,12,CalendarInput()).missing
    assert any('03.12.2026' in m and 'Personen' in m for m in missing)


def test_normal_month_uses_sunday_weekends_and_start_month_accounting():
    data,profile,_=demonstration_month()
    assert data.weekend_policy.owner=='sunday'
    assert profile.month_profile=='M1'
    assert profile.wish_policy.weekend_friday_exception


def test_fk_is_explicit_single_term_without_false_missing_recurrence_warning():
    calendar=month_calendar(2026,12,CalendarInput())
    assert not any('FK-Wiederhol' in m for m in calendar.missing)
    assert not any(e.service.code=='FK' for e in calendar.events)


def test_confirmed_friday_exception_only_protects_weekend_wish():
    from dienstplan.v2.entries import Entry
    from dienstplan.v2.wishes import violated
    _,profile,_=demonstration_month()
    weekend=Entry('weekend','P01','wochenendwunsch',Interval.local('2026-11-07T00:00','2026-11-09T00:00'),budget_month='2026-11')
    friday=automatic_pause_choices(event('W17',date(2026,11,6)),'P01')[0]
    assert not violated(weekend,(friday,),policy=profile.wish_policy)
    saturday=automatic_pause_choices(event('W17',date(2026,11,7)),'P01')[0]
    assert violated(weekend,(friday,saturday),policy=profile.wish_policy)
    day=Entry('day','P01','freiwunschtag',Interval.local('2026-11-07T00:00','2026-11-08T00:00'))
    assert violated(day,(friday,),policy=profile.wish_policy)


def test_kc15_template_paid_duration_and_explicit_import_replaces_both_regular_terms():
    term=event('KC15',date(2026,11,10))
    assert term.service.staff==1 and term.attendance.minutes==540
    assert automatic_pause_choices(term,'P01')[0].work_minutes==510
    data,_,_=demonstration_month()
    proposal=prepare_plan_import(data,[row('KC15',day='2026-11-10')])
    assert proposal.ready,proposal.errors
    codes={e.service.key for e in proposal.events if e.attendance.start_day==date(2026,11,10)}
    assert 'KC15' in codes and 'KC10' not in codes and 'KC16' not in codes
    conflicting=prepare_plan_import(data,[row('KC15',day='2026-11-10'),row('KC10',day='2026-11-10',pid='P02')])
    assert not conflicting.ready and any('gleichzeitig' in m for m in conflicting.errors)


def test_marked_u_dates_are_vacation_and_thursday_shortcut_is_corrected(tmp_path):
    book=Workbook();sheet=book.active;sheet['A1']=date(2026,12,27);sheet['B1']=date(2026,12,31)
    sheet['A4']='U';sheet['B4']='KC10';target=tmp_path/'wishes.xlsx';book.save(target)
    rows,_,_=read_import(target,source_kind='wishes')
    assert rows[0]['art']=='urlaub' and rows[0]['gutschrifttage']=='2026-12-27'
    assert rows[1]['dienst']=='KCT10'
    data,_,_=demonstration_month(2026,12)
    upgraded=prepare_plan_import(data,[dict(art='u_zuordnung_offen',datum='2026-12-27',person_id='P01',dienst='U')])
    assert upgraded.ready,upgraded.errors
    assert upgraded.inputs.absences[0].credit_days==frozenset({date(2026,12,27)})
    thursday=prepare_plan_import(data,[row('KC10',day='2026-12-31')])
    assert thursday.ready,thursday.errors
    assert thursday.blocks[0].attendance==event('KCT10',date(2026,12,31)).attendance
