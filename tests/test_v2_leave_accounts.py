"""Synthetische Konten: expliziter Start, keine Doppelzählung, eingefrorene Monate."""
from dataclasses import replace
from datetime import date
from fractions import Fraction
import json
import pytest

from dienstplan.v2.contracts import DateRange,Employment
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.entries import Entry
from dienstplan.v2.errors import DomainError
from dienstplan.v2.history import confirmation
from dienstplan.v2.leave_accounts import leave_account_settings,save_leave_account,leave_account_rows
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.serialization import plain,fingerprint
from dienstplan.v2.time import Interval


def leave(day,ident='u'):
    d=date.fromisoformat(day)
    from datetime import timedelta
    return Entry(ident,'A','urlaub',Interval.local(day+'T00:00',(d+timedelta(days=1)).isoformat()+'T00:00'),frozenset((d,)))


def save_month(store,month=11,entries=(),people=None):
    data,p,_=technical_demo(month=month)
    data=replace(data,absences=tuple(entries),people=people or data.people)
    store.save_workspace(data,p,expected_revision=store.input_revision)
    return data,p


def row(store,people,month=11,entries=None):
    return next(r for r in leave_account_rows(store,people,2026,month,current_entries=entries) if r.person_id=='A')


def freeze(store,data,profile):
    value=confirmation(data,(),data.events,accounts=profile.accounts,wish_policy=profile.wish_policy,fairness_policy=profile.fairness_policy,
                       holidays=frozenset(),history=profile.history,target_profile='S0',month_profile='M0',synthetic=True,allow_violations=True)
    value['leave_accounts']=plain(leave_account_rows(store,data.people,data.year,data.month,current_entries=data.absences))
    value['content_fingerprint']=fingerprint({k:v for k,v in value.items() if k!='content_fingerprint'})
    store.save_draft_revision('confirmed',value)
    with store.transaction():store.connection.execute('INSERT INTO v2_meta VALUES(?,?)',(f'confirmation:{data.year:04d}-{data.month:02d}','confirmed'))
    return value


def test_account_setting_roundtrip_exact_negative_opening_and_idempotence(tmp_path):
    path=tmp_path/'db'
    with V2Store(path,create=True) as s:
        save_leave_account(s,'A','2026-11','-1,25',expected_revision=0)
        revision=s.input_revision
        assert leave_account_settings(s)['A'].opening_days==Fraction(-5,4)
        save_leave_account(s,'A','2026-11',Fraction(-5,4),expected_revision=revision)
        assert s.input_revision==revision
        with pytest.raises(DomainError,match='geändert'):save_leave_account(s,'A','2026-11',0,expected_revision=0)
    with V2Store(path) as s:
        setting=leave_account_settings(s)['A']
        assert setting.start_month=='2026-11' and setting.opening_days==Fraction(-5,4)


def test_two_days_monthly_accrual_and_used_days_deduplicated_across_month_copies(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        nov,p=save_month(s,entries=(leave('2026-11-03'),))
        dec,_=save_month(s,12,entries=(leave('2026-11-03'),leave('2026-12-01','dec')))
        save_leave_account(s,'A','2026-11',4)
        first=row(s,nov.people,entries=nov.absences)
        assert (first.earned_days,first.used_days,first.projected_days)==(2,1,5)
        second=row(s,dec.people,12,dec.absences)
        assert (second.earned_days,second.used_days,second.projected_days)==(4,2,6)
        assert second.monthly_earned_days==2 and second.monthly_used_days==1
        assert row(s,dec.people,12,dec.absences)==second


def test_missing_setting_and_unknown_initial_balance_are_never_zero_guesses(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,_=save_month(s)
        report=row(s,data.people,entries=())
        assert report.projected_days is None and report.opening_days is None and report.diagnostics
        with pytest.raises(DomainError):save_leave_account(s,'A','2026-11',None)


def test_partial_employment_month_uses_confirmed_calendar_day_rule(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p,_=technical_demo();person=replace(data.people[0],employment=Employment('A',DateRange(date(2026,11,15),date(2028,1,1))))
        data=replace(data,people=(person,)+data.people[1:])
        s.save_workspace(data,p,expected_revision=0)
        save_leave_account(s,'A','2026-11',0)
        report=row(s,data.people,entries=())
        # Neue Nutzerregel: 15.–30.11. = 16 beschäftigte von 30 Kalendertagen.
        assert report.earned_days == Fraction(16,15) and report.projected_days == Fraction(16,15)
        assert not any('noch festlegen' in message for message in report.diagnostics)


def test_missing_old_usage_month_keeps_balance_unknown(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,_=save_month(s,12)
        save_leave_account(s,'A','2026-11',0)
        report=row(s,data.people,12,())
        assert report.earned_days==4 and report.used_days is None and report.projected_days is None
        assert report.known_earned_days==4 and any('2026-11' in message for message in report.diagnostics)


def test_negative_rest_is_forecast_not_rejection(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        entries=tuple(leave(day,day) for day in ('2026-11-03','2026-11-04','2026-11-05'))
        data,_=save_month(s,entries=entries)
        save_leave_account(s,'A','2026-11',0)
        report=row(s,data.people,entries=entries)
        assert report.projected_days==-1 and report.used_days==3 and report.diagnostics


def test_current_explicit_empty_draft_does_not_resurrect_old_leave(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,_=save_month(s,entries=(leave('2026-11-03'),))
        save_leave_account(s,'A','2026-11',0)
        assert row(s,data.people,entries=()).used_days==0
        assert row(s,data.people,entries=()).projected_days==2


def test_confirmation_freezes_account_and_usage_against_later_settings(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p=save_month(s,entries=(leave('2026-11-03'),))
        save_leave_account(s,'A','2026-11',5)
        saved=freeze(s,data,p)
        save_leave_account(s,'A','2026-11',99)
        report=row(s,data.people,entries=())
        assert report.confirmed and report.opening_days==5 and report.projected_days==6 and report.used_days==1
        assert s.confirmed_month(2026,11)==saved


def test_old_confirmation_without_new_stats_is_transparently_reconstructed(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p=save_month(s,entries=(leave('2026-11-03'),))
        save_leave_account(s,'A','2026-11',0)
        # Real confirmation facts, deliberately without the new optional statistic.
        value=confirmation(data,(),data.events,accounts=p.accounts,wish_policy=p.wish_policy,fairness_policy=p.fairness_policy,
                           holidays=frozenset(),history=p.history,target_profile='S0',month_profile='M0',synthetic=True,allow_violations=True)
        value.pop('leave_accounts',None)
        value['content_fingerprint']=fingerprint({k:v for k,v in value.items() if k!='content_fingerprint'})
        s.save_draft_revision('old-confirmed',value)
        with s.transaction():s.connection.execute('INSERT INTO v2_meta VALUES(?,?)',('confirmation:2026-11','old-confirmed'))
        report=row(s,data.people,entries=())
        assert report.confirmed and report.reconstructed and report.used_days==1
        assert any('rekonstruiert' in message for message in report.diagnostics)


def test_earlier_than_account_start_is_not_a_fake_known_rest(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,_=save_month(s)
        save_leave_account(s,'A','2026-12',3)
        report=row(s,data.people,entries=())
        assert report.projected_days is None and any('2026-12' in message for message in report.diagnostics)


def test_settings_transaction_rolls_back_on_write_error(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        s.connection.execute("CREATE TRIGGER stop_leave BEFORE INSERT ON v2_meta WHEN NEW.key='leave-accounts' BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END")
        with pytest.raises(Exception,match='write failure'):save_leave_account(s,'A','2026-11',3)
        assert leave_account_settings(s)=={} and s.input_revision==0


def test_months_before_employment_do_not_invent_accrual_or_unknown_consumption(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p,_=technical_demo();employee=replace(data.people[0],employment=Employment('A',DateRange(date(2026,11,1),date(2028,1,1))))
        data=replace(data,people=(employee,)+data.people[1:]);s.save_workspace(data,p,expected_revision=0)
        save_leave_account(s,'A','2026-01',0)
        report=row(s,data.people,entries=())
        assert report.earned_days==2 and report.used_days==0 and report.projected_days==2


def test_confirmed_previous_month_and_copied_global_leave_count_once(tmp_path):
    from dienstplan.v2.persistence import encoded,entry_payload
    with V2Store(tmp_path/'db',create=True) as s:
        old=leave('2026-11-03');nov,p=save_month(s,entries=(old,))
        save_leave_account(s,'A','2026-11',0);freeze(s,nov,p)
        dec,_=save_month(s,12,entries=(old,leave('2026-12-01','dec')))
        with s.transaction():s.connection.execute('INSERT INTO v2_entries VALUES(?,?,?)',(old.id,encoded(old.identity),encoded(entry_payload(old))))
        report=row(s,dec.people,12,dec.absences)
        assert report.earned_days==4 and report.used_days==2 and report.projected_days==2


def test_fractional_year_boundary_entitlement_confirmation_roundtrip(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        employment=Employment('A',DateRange(date(2026,12,31),date(2027,1,2)))
        data,p,_=technical_demo(year=2026,month=12)
        data=replace(data,people=(replace(data.people[0],employment=employment),)+data.people[1:])
        s.save_workspace(data,p,expected_revision=0)
        save_leave_account(s,'A','2026-12','1/3')
        jan,profile,_=technical_demo(year=2027,month=1)
        jan=replace(jan,people=(replace(jan.people[0],employment=employment),)+jan.people[1:])
        s.save_workspace(jan,profile,expected_revision=s.input_revision)
        report=next(r for r in leave_account_rows(s,jan.people,2027,1,current_entries=()) if r.person_id=='A')
        assert report.earned_days==Fraction(4,31) and report.monthly_earned_days==Fraction(2,31)
        assert report.projected_days==Fraction(1,3)+Fraction(4,31)
        freeze(s,jan,profile)
        before=s.connection.execute("SELECT payload FROM v2_revisions WHERE id='confirmed'").fetchone()[0]
        save_leave_account(s,'A','2027-01',99)
        frozen=next(r for r in leave_account_rows(s,jan.people,2027,1,current_entries=()) if r.person_id=='A')
        assert frozen.confirmed and frozen.earned_days==Fraction(4,31)
        assert frozen.projected_days==Fraction(1,3)+Fraction(4,31)
        assert s.connection.execute("SELECT payload FROM v2_revisions WHERE id='confirmed'").fetchone()[0]==before


def test_old_integer_frozen_stats_are_read_without_rewriting_bytes(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p=save_month(s);save_leave_account(s,'A','2026-11',0)
        saved=freeze(s,data,p)
        # Synthetische historische Darstellungsform vor Fraction-Tagesansprüchen.
        for raw in saved['leave_accounts']:
            for key in ('earned_days','monthly_earned_days','known_earned_days'):
                if isinstance(raw.get(key),dict):
                    assert raw[key]['denominator']==1
                    raw[key]=raw[key]['numerator']
        saved['content_fingerprint']=fingerprint({k:v for k,v in saved.items() if k!='content_fingerprint'})
        payload=json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        s.connection.execute("UPDATE v2_revisions SET payload=? WHERE id='confirmed'",(payload,))
        report=row(s,data.people,entries=())
        assert report.earned_days==Fraction(2) and report.confirmed
        assert s.connection.execute("SELECT payload FROM v2_revisions WHERE id='confirmed'").fetchone()[0]==payload


def test_old_unknown_partial_stats_stay_frozen_but_new_projection_is_transparent(tmp_path):
    with V2Store(tmp_path/'db',create=True) as s:
        data,p,_=technical_demo()
        data=replace(data,people=(replace(data.people[0],employment=Employment('A',DateRange(date(2026,11,15),date(2028,1,1)))),)+data.people[1:])
        s.save_workspace(data,p,expected_revision=0);save_leave_account(s,'A','2026-11',0)
        saved=freeze(s,data,p)
        for raw in saved['leave_accounts']:
            if raw['person_id']=='A':
                raw['earned_days']=None;raw['monthly_earned_days']=None;raw['projected_days']=None;raw['known_earned_days']=0
                raw['diagnostics']=['Historische Teilmonatsregel ungeklärt.']
        saved['content_fingerprint']=fingerprint({k:v for k,v in saved.items() if k!='content_fingerprint'})
        payload=json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        s.connection.execute("UPDATE v2_revisions SET payload=? WHERE id='confirmed'",(payload,))
        frozen=row(s,data.people,entries=())
        assert frozen.earned_days is None and frozen.projected_days is None
        dec,_=save_month(s,12)
        reconstructed=row(s,dec.people,12,())
        assert reconstructed.earned_days==Fraction(16,15)+2
        assert reconstructed.reconstructed and any('Teilmonatsregel rekonstruiert' in m for m in reconstructed.diagnostics)
        assert s.connection.execute("SELECT payload FROM v2_revisions WHERE id='confirmed'").fetchone()[0]==payload
