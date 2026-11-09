from datetime import date
import csv
import io

import pytest

from dienstplan.v2.catalog import CATALOG, CalendarInput, FixedTerm, event, month_calendar, participation
from dienstplan.v2.contracts import Contract, Contracts, DateRange, Employment
from dienstplan.v2.entries import HEADER, WishBudget, correct, preview
from dienstplan.v2.errors import DomainError
from dienstplan.v2.people import Eligibility, OUTSIDE_CODES, Person
from dienstplan.v2.time import Interval
from dienstplan.v2.work import WorkBlock


def pause(day,clock='21:00',end='21:30'):
    return Interval.local(f'{day}T{clock}',f'{day}T{end}')


@pytest.mark.parametrize('key,day,staff,paid,clock',[
    ('T',12,None,180,None),('KC10',11,1,360,None),('KCT10',12,1,405,'13'),
    ('KC16',11,1,450,'21'),('KCT',12,1,540,'21'),('TS',12,None,300,None),
    ('W17',11,2,450,'21'),('TW',12,2,540,'21'),('W16',11,2,450,'21'),
    ('WL',11,2,450,'21'),('BK',11,2,450,'21'),('VN',11,1,120,None),
    ('LB',12,2,330,None),('LB_TS',12,2,420,'13'),('INT',11,1,450,'21'),
    ('N17',11,1,450,'21'),('R_early',24,1,360,None),('R_late',24,1,450,'21'),
])
def test_catalog_staff_duration_and_participation_protection(key,day,staff,paid,clock):
    d=date(2026,12 if key.startswith('R_') else 11,day)
    people=('A','B') if key.startswith('LB') else ('A',) if key in {'VN','INT','N17'} else ()
    term=event(key,d,people=people,reason='Abstand zum Folgedienst' if key=='W16' else '')
    breaks=(pause(d,clock+':00',clock+':30'),) if clock else ()
    duty=term.assign('A',breaks,reserve_profile='full_work_test' if key.startswith('R_') else None)
    assert (term.service.staff,duty.work_minutes)==(staff,paid)


def test_complete_catalog_contains_all_seventeen_codes():
    assert {t.code for t in CATALOG}==set('T KC10 KCT10 KC16 KCT TS W17 TW W16 WL BK VN LB INT N17 R FK'.split())


def test_thursday_generation_lb_rhythm_and_missing_parameters():
    settings=CalendarInput(frozenset({date(2026,11,12)}),date(2026,11,12),('E','F'))
    result=month_calendar(2026,11,settings)
    thursday=[e for e in result.events if e.attendance.start_day==date(2026,11,12)]
    assert {e.service.key for e in thursday}=={'KCT10','KCT','TW','TS','LB_TS'}
    assert [e.attendance.start_day for e in result.events if e.service.code=='LB']==[date(2026,11,12),date(2026,11,26)]
    december=month_calendar(2026,12,settings)
    assert [e.attendance.start_day for e in december.events if e.service.code=='LB']==[date(2026,12,10),date(2026,12,24)]
    assert any('F06' in error for error in result.missing)
    assert not any(e.service.code in {'WL','BK'} for e in result.events)


def test_reserve_cross_year_two_windows_requires_explicit_assessment():
    terms=[]
    for year,month in ((2026,12),(2027,1)):
        result=month_calendar(year,month,CalendarInput())
        terms.extend(e for e in result.events if e.service.code=='R')
        assert any('F02' in s for s in result.missing)
    assert len(terms)==28
    with pytest.raises(DomainError,match='Reserve'):terms[0].assign('A')
    total=0
    for term in terms:
        breaks=(pause(term.attendance.start_day),) if term.service.key=='R_late' else ()
        total+=term.assign('A',breaks,reserve_profile='full_work_test').work_minutes
    assert total==11340


def test_w16_replacement_preserves_coverage_and_no_parallel_w17():
    d=date(2026,11,10)
    result=month_calendar(2026,11,CalendarInput(w16_reasons=((d,'11 Stunden Ruhe zum Folgedienst'),)))
    outside=[e for e in result.events if e.attendance.start_day==d and e.service.code in {'W16','W17'}]
    assert len(outside)==1 and outside[0].service.code=='W16'
    assert outside[0].coverage_id==event('W17',d).coverage_id
    with pytest.raises(DomainError):event('W16',d)
    with pytest.raises(DomainError):event('W17',date(2026,11,12))


def test_team_coverage_exactly_once_no_incidental_overlap():
    d=date(2026,11,12);occasion=event('TS',d)
    early=event('KCT10',d).assign('A',(pause(d,'13:00','13:30'),))
    assert participation(early,occasion)=='T erfüllt; TS-Ausnahme'
    lb=event('LB_TS',d,people=('E','F')).assign('E',(pause(d,'13:00','13:30'),))
    assert participation(lb,occasion)=='vollständig' and lb.work_minutes==420
    with pytest.raises(DomainError):event('LB_TS',d,people=('E','F')).assign('E',(pause(d,'17:00','17:30'),))
    incidental=WorkBlock('other','G','FK',occasion.attendance)
    assert participation(incidental,occasion)=='fehlt'


def test_fixed_terms_persons_and_fk_span_are_explicit():
    d=date(2026,11,11)
    with pytest.raises(DomainError):event('VN',d)
    with pytest.raises(DomainError):event('FK',d,people=('A',))
    fk=event('FK',d,people=('A',),attendance=Interval.local('2026-11-11T09:00','2026-11-11T16:00'))
    assert fk.assign('A',(pause(d,'12:00','12:30'),)).work_minutes==390
    result=month_calendar(2026,11,CalendarInput(fixed=(FixedTerm('INT',d,('A',)),)))
    assert any('INT' in s for s in result.missing) and any('N17' in s for s in result.missing)


def person(codes=OUTSIDE_CODES,license=False):
    dates=DateRange(date(2026,11,1),date(2027,1,1))
    return Person('X','Außendienst',Employment('X',dates),Contracts('X',(Contract('X',dates,'25'),)),
                  (Eligibility(dates,codes,license),))


def test_outside_person_team_license_and_full_employment():
    p=person()
    for code in ('T','TS','TW','W17','WL','BK'):
        d=date(2026,11,12) if code in {'T','TS','TW'} else date(2026,11,11)
        assert not p.eligibility_errors(code,event(code,d).attendance)
    for code in ('KC10','KC16','KCT10','KCT','LB','VN','INT','FK','R'):
        assert p.eligibility_errors(code,Interval.local('2026-11-11T10:00','2026-11-11T11:00'))
    assert any('Führerschein' in s for s in p.eligibility_errors('N17',Interval.local('2026-11-11T17:00','2026-11-12T01:00')))
    assert not person(license=True).eligibility_errors('N17',Interval.local('2026-11-11T17:00','2026-11-12T01:00'))
    assert any('Beschäftigung' in s for s in person(license=True).eligibility_errors('N17',Interval.local('2026-12-31T17:00','2027-01-01T01:00')))


def csv_text(rows,delimiter=';'):
    s=io.StringIO();w=csv.writer(s,delimiter=delimiter);w.writerow(HEADER)
    for row in rows:w.writerow(['2','A',row[0],row[1],row[2],row[3],row[4] if len(row)>4 else '',row[5] if len(row)>5 else ''])
    return s.getvalue()


BUDGET={('A','2026-11'):WishBudget(2)}


def test_correction_batch_retains_thursday_and_never_promotes_partial_rows():
    original=csv_text([('mon','freiwunschtag','2026-11-09T00:00','2026-11-10T00:00'),
                       ('wed','freiwunschtag','2026-11-11T22:00','2026-11-12T01:00')])
    batch=preview(original,budgets=BUDGET,month='2026-11')
    assert not batch.ready and 'Donnerstag' in batch.rows[1].errors[0]
    assert batch.original_text==original and len(batch.rows)==2
    with pytest.raises(DomainError,match='Teilübernahme'):batch.promote()
    fixed=correct(batch,3,{'bis':'2026-11-12T00:00'},budgets=BUDGET,month='2026-11')
    assert fixed.ready and len(fixed.promote())==2 and fixed.original_text==original


@pytest.mark.parametrize('delimiter,bom',[(';',True),(',',False)])
def test_vacation_beyond_four_days_and_duplicates(delimiter,bom):
    days='|'.join(f'2026-11-{d:02d}' for d in range(9,14))
    row=('vac','urlaub','2026-11-09T00:00','2026-11-16T00:00',days)
    batch=preview(('\ufeff' if bom else '')+csv_text([row,row],delimiter),month='2026-11')
    assert batch.ready and len(batch.promote())==1
    assert len(batch.promote()[0].credit_days)==5


def test_joint_budget_dedupe_and_id_collision():
    first=preview(csv_text([('a','freiwunschtag','2026-11-02T00:00','2026-11-03T00:00')]),budgets=BUDGET,month='2026-11').promote()
    duplicate=preview(csv_text([('another','freiwunschtag','2026-11-02T00:00','2026-11-03T00:00')]),existing=first,budgets=BUDGET,month='2026-11')
    assert duplicate.promote()[0].id=='a'
    batch=preview(csv_text([('b','freiwunschtag','2026-11-03T00:00','2026-11-04T00:00'),('c','freiwunschtag','2026-11-04T00:00','2026-11-05T00:00')]),existing=first,budgets=BUDGET,month='2026-11')
    assert not batch.ready and 'Wunschbudget' in batch.errors[0]
    collision=preview(csv_text([('a','freiwunschtag','2026-11-03T00:00','2026-11-04T00:00')]),existing=first,budgets=BUDGET,month='2026-11')
    assert not collision.ready and 'Kennung' in collision.rows[0].errors[0]


def test_weekend_is_one_entry_and_budget_uses_explicit_owner():
    batch=preview(csv_text([('we','wochenendwunsch','2026-11-14T00:00','2026-11-16T00:00')]),budgets=BUDGET,month='2026-11')
    assert batch.ready and len(batch.promote())==1 and batch.promote()[0].budget_month=='2026-11'


def test_legacy_and_malformed_csv_never_activate_valid_prefix_after_edit():
    legacy=preview('datum;von;bis;prioritaet;kommentar\n2026-11-09;;;1;Alt\n',month='2026-11')
    assert not legacy.ready and 'Altformat' in legacy.errors[0]
    text=csv_text([('a','freiwunschtag','2026-11-02T00:00','2026-11-03T00:00')])+'2;A;bad\n'
    malformed=preview(text,budgets=BUDGET,month='2026-11')
    edited=correct(malformed,2,{'kommentar':'Korrektur'},budgets=BUDGET,month='2026-11')
    assert not edited.ready and edited.parse_errors
