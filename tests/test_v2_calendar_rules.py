from datetime import date
from dataclasses import replace

from dienstplan.v2.catalog import event
from dienstplan.v2.calendar_rules import (WeekendPolicy,WeekPolicy,check_calendar,check_quotas,dates,
    horizon,merge_quotas,week_quotas,weekend_free)
from dienstplan.v2.contracts import Employment,DateRange
from dienstplan.v2.entries import Entry
from dienstplan.v2.time import Interval
from dienstplan.v2.work import WorkBlock
from test_v2_validation import person,pause

WEEKENDS=WeekendPolicy('saturday','Synthetisches Testprofil, keine Betriebsfreigabe')
WEEKS=WeekPolicy('week_start','both','Q0 – synthetisches Testprofil')

def known(p='A'):
    return frozenset((p,d) for d in dates(horizon(2026,11)))

def short(day,start='10:00',end='11:00'):
    return WorkBlock(str(day),'A','FK',Interval.local(f'{day}T{start}',f'{day}T{end}'))

def test_preceding_free_pair_is_adjacent_and_in_immediate_week():
    weekend=short(date(2026,11,14))
    good=check_calendar((person(),),(weekend,),2026,11,known_days=known(),policy=WEEKENDS)
    assert good.hard_ok and good.fully_checked
    # Mo/Mi frei, Di/Do/Fr belegt: zwei einzelne freie Tage reichen nicht.
    blocks=(weekend,short(date(2026,11,10)),short(date(2026,11,12)),short(date(2026,11,13)))
    report=check_calendar((person(),),blocks,2026,11,known_days=known(),policy=WEEKENDS)
    assert any(i.rule=='preceding_free_pair' for i in report.issues)

def test_incoming_sunday_night_and_thursday_team_remove_free_days():
    sunday=event('W17',date(2026,11,8)).assign('A',(pause(date(2026,11,8)),))
    blocks=(sunday,short(date(2026,11,11)),short(date(2026,11,12)),short(date(2026,11,13)),short(date(2026,11,14)))
    report=check_calendar((person(),),blocks,2026,11,known_days=known(),policy=WEEKENDS)
    assert any(i.rule=='preceding_free_pair' and '2026-11-14' in i.message for i in report.issues)
    assert date(2026,11,9) in sunday.occupied_days

def test_w17_exception_is_only_weekend_counting_not_free_pair_or_actual_days():
    day=date(2026,11,13);night=event('W17',day).assign('A',(pause(day),))
    assert weekend_free((night,),'A',date(2026,11,14),known()) is True
    assert date(2026,11,14) in night.occupied_days
    for code in ('WL','BK'):
        other=event(code,day).assign('A',(pause(day),))
        assert weekend_free((other,),'A',date(2026,11,14),known()) is False
    blocked=tuple(short(date(2026,11,d)) for d in (9,10,11,12))+(night,)
    assert any(i.rule=='preceding_free_pair' for i in check_calendar((person(),),blocked,2026,11,known_days=known(),policy=WEEKENDS).issues)

def test_unknown_future_is_not_free_and_unknown_pair_is_not_a_failure_proof():
    empty=frozenset()
    assert weekend_free((),'A',date(2026,11,14),empty) is None
    report=check_calendar((person(),),(short(date(2026,11,14)),),2026,11,known_days=empty,policy=WEEKENDS)
    assert not report.fully_checked and any('Randdaten' in s for s in report.unchecked)
    assert not any(i.rule=='preceding_free_pair' for i in report.issues)

def test_two_free_weekends_required_with_explicit_owner_and_partial_profile():
    blocks=tuple(short(date(2026,11,d)) for d in (7,14))
    report=check_calendar((person(),),blocks,2026,11,known_days=known(),policy=WEEKENDS)
    assert report.free_weekends==( ('A',2), )
    blocks+= (short(date(2026,11,21)),)
    assert any(i.rule=='free_weekends' for i in check_calendar((person(),),blocks,2026,11,known_days=known(),policy=WEEKENDS).issues)
    assert any('F10' in s for s in check_calendar((person(),),(),2026,11,known_days=known(),policy=None).unchecked)
    partial=replace(person(),employment=Employment('A',DateRange(date(2026,11,16),date(2027,1,1))))
    assert any('Teilmonatsquote' in s for s in check_calendar((partial,),(),2026,11,known_days=known(),policy=WEEKENDS).unchecked)

def test_vacation_credit_does_not_occupy_a_day():
    # Nur wirkliche Dienstblöcke gehen in Kalenderbelegung ein, keine Gutschrift.
    vacation=Entry('vac','A','urlaub',Interval.local('2026-11-09T00:00','2026-11-11T00:00'),frozenset({date(2026,11,9),date(2026,11,10)}))
    assert vacation.credit_days
    report=check_calendar((person(),),(short(date(2026,11,14)),),2026,11,known_days=known(),policy=WEEKENDS)
    assert report.hard_ok

def test_shared_week_ids_and_season_anchor_across_month_year():
    nov=week_quotas(2026,11,policy=WEEKS);dec=week_quotas(2026,12,policy=WEEKS)
    boundary=[q for q in merge_quotas(nov,dec) if q.id=='2026-W49/WL']
    assert len(boundary)==1 and boundary[0].required==1 and boundary[0].owner_month=='2026-11'
    alternative=WeekPolicy('week_end','both','Anderes synthetisches Testprofil')
    assert next(q for q in week_quotas(2026,12,policy=alternative) if q.id=='2026-W49/WL').required==2
    assert next(q for q in week_quotas(2027,1,policy=WEEKS) if q.dates.start==date(2027,1,25) and q.code=='WL').required==2
    assert next(q for q in week_quotas(2027,2,policy=WEEKS) if q.dates.start==date(2027,2,1) and q.code=='WL').required==1

def test_exact_quotas_different_dates_and_exclusion():
    quotas=tuple(q for q in week_quotas(2026,12,policy=WEEKS) if q.dates.start==date(2026,12,7))
    events=(event('WL',date(2026,12,7)),event('WL',date(2026,12,9)),event('BK',date(2026,12,11)))
    assert check_quotas(quotas,events,policy=WEEKS)==()
    assert any(i.rule=='weekly_quota' for i in check_quotas(quotas,(events[0],events[0],events[2]),policy=WEEKS))
    assert any(i.rule=='wl_bk_exclusion' for i in check_quotas(quotas,events+(event('BK',date(2026,12,9)),),policy=WEEKS))
