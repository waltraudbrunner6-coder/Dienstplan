"""Korrektur vorhandener Urlaubstage erhält Plan und genaue W/5-Rechnung."""
from dataclasses import replace
import pytest
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.entries import Entry,preview
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.reporting import hours_rows
from dienstplan.v2.time import Interval
from dienstplan.v2.errors import DomainError


def staged(store,entry_id='old'):
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;A;fixed;urlaub;2026-11-06T00:00;2026-11-07T00:00;2026-11-06;Ausgewählter Urlaubstag\n'
    store.save_correction('repair',preview(text,month='2026-11'),replaces=entry_id)


def test_repair_credit_days_without_losing_assignments_then_confirm(tmp_path):
    inputs,profile,blocks=technical_demo()
    leave=Entry('old','A','urlaub',Interval.local('2026-11-06T00:00','2026-11-07T00:00'))
    inputs=replace(inputs,absences=(leave,),locked=blocks)
    path=tmp_path/'db'
    with V2Store(path,create=True) as store:
        store.save_workspace(inputs,profile,blocks,inputs.events,expected_revision=0)
        kwargs=dict(accounts=profile.accounts,wish_policy=profile.wish_policy,fairness_policy=profile.fairness_policy,target_profile='S0',month_profile='M0',synthetic=True)
        with pytest.raises(DomainError,match='A.*06.11.2026'):
            store.confirm('month',inputs,blocks,inputs.events,expected_revision=store.input_revision,allow_violations=True,**kwargs)
        staged(store)
        updated=store.apply_correction('repair',inputs,profile,budgets={},expected_revision=store.input_revision,blocks=blocks,events=inputs.events)
        assert store.load_workspace(2026,11)==(updated,profile,blocks,inputs.events)
        rows=hours_rows(updated.people,blocks,updated.absences,2026,11,accounts=profile.accounts,target_profile='S0',month_profile='M0')
        assert rows[0].credits_known and rows[0].credits==300  # 25 h / 5 = 5 h.
        confirmed=store.confirm('month',updated,blocks,inputs.events,expected_revision=store.input_revision,allow_violations=True,**kwargs)
        assert confirmed['hours'][0]['credits']==300
    with V2Store(path) as store:assert store.load_workspace(2026,11)[2]==blocks


def test_delete_absence_preserves_plan_and_failed_repair_rolls_back(tmp_path):
    inputs,profile,blocks=technical_demo()
    leave=Entry('old','A','urlaub',Interval.local('2026-11-06T00:00','2026-11-07T00:00'))
    inputs=replace(inputs,absences=(leave,))
    with V2Store(tmp_path/'db',create=True) as store:
        store.save_workspace(inputs,profile,blocks,inputs.events,expected_revision=0);staged(store)
        store.connection.execute("CREATE TRIGGER stop_repair BEFORE INSERT ON v2_revisions BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(Exception,match='test failure'):
            store.apply_correction('repair',inputs,profile,budgets={},expected_revision=store.input_revision,blocks=blocks,events=inputs.events)
        assert store.load_workspace(2026,11)==(inputs,profile,blocks,inputs.events)
        assert store.load_correction('repair',budgets={},month='2026-11',additional_existing=inputs.absences).ready
        store.connection.execute('DROP TRIGGER stop_repair')
        updated=store.delete_entry('old',inputs,profile,expected_revision=store.input_revision,blocks=blocks,events=inputs.events)
        assert store.load_workspace(2026,11)==(updated,profile,blocks,inputs.events)
        assert not updated.absences
