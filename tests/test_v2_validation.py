from dataclasses import replace
from datetime import date
import pytest

from dienstplan.v2.catalog import event
from dienstplan.v2.contracts import Contract,Contracts,DateRange,Employment
from dienstplan.v2.entries import Entry
from dienstplan.v2.people import Eligibility,Person
from dienstplan.v2.time import Interval
from dienstplan.v2.validation import check_core
from dienstplan.v2.work import WorkBlock

def person(id='A',codes=None,license=True):
    dates=DateRange(date(2026,1,1),date(2027,2,1))
    return Person(id,id,Employment(id,dates),Contracts(id,(Contract(id,dates,'25'),)),
                  (Eligibility(dates,frozenset(codes or 'T TS KC10 KCT10 KC16 KCT W17 W16 WL BK VN LB INT N17 R FK TW'.split()),license),))

def pause(day,clock='21:00',end='21:30'):
    return Interval.local(f'{day}T{clock}',f'{day}T{end}')

def rules(report):return {i.rule for i in report.issues}


def test_startdate_and_true_rest_are_independent_checks():
    d=date(2026,11,10)
    vn=event('VN',d,people=('A',));late=event('KC16',d)
    blocks=(vn.assign('A'),late.assign('A',(pause(d),)))
    assert {'one_block','rest'}<=rules(check_core((person(),),(vn,late),blocks))
    # Ein voller Abstand genügt nicht, um zwei Starts am selben Datum zu erlauben.
    a=event('VN',d,people=('A',))
    b=event('FK',d,people=('A',),attendance=Interval.local('2026-11-10T23:00','2026-11-10T23:59'))
    report=check_core((person(),),(a,b),(a.assign('A'),b.assign('A')))
    assert rules(report)=={'one_block'}


@pytest.mark.parametrize('clock,allowed',[('11:00',True),('10:59',False)])
def test_core_exact_eleven_hour_boundary(clock,allowed):
    a=event('KC16',date(2026,11,10))
    b=event('FK',date(2026,11,11),people=('A',),attendance=Interval.local('2026-11-11T'+clock,'2026-11-11T12:00'))
    report=check_core((person(),),(a,b),(a.assign('A',(pause(date(2026,11,10)),)),b.assign('A')))
    assert ('rest' not in rules(report)) is allowed


def test_kc16_to_kc10_missing_45_minutes():
    a=event('KC16',date(2026,11,10));b=event('KC10',date(2026,11,11))
    report=check_core((person(),),(a,b),(a.assign('A',(pause(date(2026,11,10)),)),b.assign('A')))
    assert any(i.rule=='rest' and '45' in i.message for i in report.issues)


def test_exact_rest_and_consecutive_overnights_allowed_core():
    a=event('W17',date(2026,11,9));b=event('W17',date(2026,11,10))
    report=check_core((person(),),(a,b),(a.assign('A',(pause(date(2026,11,9)),)),b.assign('A',(pause(date(2026,11,10)),))))
    assert report.hard_ok and sum(n for _,n in report.open_slots)==2


def test_six_days_across_year_boundary_with_fixed_past():
    before=[]
    for d in (28,29,30,31):
        before.append(WorkBlock(str(d),'A','FK',Interval.local(f'2026-12-{d}T10:00',f'2026-12-{d}T11:00')))
    before.append(WorkBlock('jan1','A','FK',Interval.local('2027-01-01T10:00','2027-01-01T11:00')))
    term=event('FK',date(2027,1,2),people=('A',),attendance=Interval.local('2027-01-02T10:00','2027-01-02T11:00'))
    assert 'consecutive' in rules(check_core((person(),),(term,),(term.assign('A'),),boundary=before))
    # Alte Konflikte ohne Bezug zu einer aktuellen Zuteilung nicht neu beurteilen.
    assert check_core((person(),),(),(),boundary=before).hard_ok


def test_qualifications_vacation_and_fixed_presence_are_hard():
    term=event('N17',date(2026,11,11),people=('A',))
    block=term.assign('A',(pause(date(2026,11,11)),))
    vacation=Entry('vac','A','urlaub',Interval.local('2026-11-09T00:00','2026-11-16T00:00'))
    report=check_core((person(license=False),),(term,),(block,),absences=(vacation,))
    assert {'eligibility','leave','fixed'}<=rules(report)
    assert report.open_slots==((term.id,1),)
    assert 'fixed' in rules(check_core((person(),),(term,),()))


def test_independent_checker_reconstructs_protected_team_window():
    d=date(2026,11,12);term=event('KCT10',d);team=event('TS',d)
    legitimate=term.assign('A',(pause(d,'13:00','13:30'),))
    forged=replace(legitimate,breaks=(pause(d,'15:00','15:30'),),protected=())
    report=check_core((person(),),(term,team),(forged,))
    assert 'team_window' in rules(report)
    valid=check_core((person(),),(term,team),(legitimate,))
    assert valid.hard_ok and valid.participation==((team.id,'A','T erfüllt; TS-Ausnahme'),)


def test_bk_excuses_soft_team_and_vacation_creates_no_work():
    d=date(2026,11,11);bk=event('BK',d);team=event('T',date(2026,11,12))
    block=bk.assign('A',(pause(d),))
    report=check_core((person(),),(bk,team),(block,))
    assert report.hard_ok and report.participation[-1][-1]=='ausgenommen'
    vacation=Entry('vac','A','urlaub',Interval.local('2026-11-12T00:00','2026-11-13T00:00'))
    assert check_core((person(),),(team,),(),absences=(vacation,)).participation[-1][-1]=='Urlaub'


def test_duplicate_unknown_and_parallel_replacement_are_not_silently_valid():
    d=date(2026,11,11);a=event('W17',d);b=event('W16',d,reason='Ruhe')
    block=a.assign('A',(pause(d),))
    report=check_core((person(),),(a,b),(block,block,replace(block,person_id='unknown')))
    assert {'coverage','duplicate','reference'}<=rules(report)
