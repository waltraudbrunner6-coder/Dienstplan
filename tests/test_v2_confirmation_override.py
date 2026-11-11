"""Explizite Bestätigung mit unveränderten, eingefrorenen Abweichungen."""
from dataclasses import replace
import pytest
from test_v2_ui import workbench
from test_v2_history_reporting import confirm
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.errors import DomainError


def test_open_slots_require_explicit_override_and_snapshot_is_idempotent(tmp_path):
    data,_,old=technical_demo()
    with V2Store(tmp_path/'db',create=True) as store:
        with pytest.raises(DomainError):confirm(store,'nov',data,())
        assert not store.confirmations()
        saved=confirm(store,'nov',data,(),allow_violations=True)
        assert saved['confirmation_override'] and saved['open_slots'] and saved['warnings']
        rev=store.input_revision
        assert confirm(store,'nov',data,(),allow_violations=True)==saved and store.input_revision==rev
        with pytest.raises(DomainError):confirm(store,'nov',data,())
        with pytest.raises(DomainError):confirm(store,'other',data,old,allow_violations=True)
    with V2Store(tmp_path/'db') as store:
        assert store.confirmed_month(2026,11)==saved
        assert len(store.confirmations())==1


def test_rule_violation_can_be_confirmed_without_relabeling_as_valid(tmp_path):
    data,_,old=technical_demo()
    data=replace(data,people=(replace(data.people[0],rights=()),)+data.people[1:])
    with V2Store(tmp_path/'db',create=True) as store:
        with pytest.raises(DomainError):confirm(store,'nov',data,old)
        saved=confirm(store,'nov',data,old,allow_violations=True)
        assert saved['issues'] and saved['confirmation_override']
        assert any(i['rule']=='eligibility' for i in saved['issues'])


def test_ui_decline_keeps_month_editable_accept_is_visible_after_restart(workbench,monkeypatch):
    w=workbench;w.blocks=w.blocks[:1];w.inputs=replace(w.inputs,manual_override=True)
    w.store.save_workspace(w.inputs,w.profile,w.blocks,w.events,expected_revision=w.store.input_revision)
    before=w.store.input_revision;seen=[]
    def decline(messages,**kw):
        assert kw['confirmation'];seen.extend(messages);return False
    monkeypatch.setattr(w,'confirm_override',decline);w.confirm()
    assert seen and w.store.input_revision==before and not w.store.confirmations()
    monkeypatch.setattr(w,'confirm_override',lambda messages,**kw:True);w.confirm()
    assert 'BESTÄTIGT MIT ABWEICHUNGEN' in w.status.text()
    saved=w.store.confirmed_month(2026,11)
    assert saved['open_slots'] and saved['warnings']
    revision=w.store.input_revision;w.confirm();assert w.store.input_revision==revision
    w.refresh_results();assert 'BESTÄTIGT MIT ABWEICHUNGEN' in w.status.text()
    with pytest.raises(DomainError,match='Bestätigter'):w.save()
    from dienstplan.v2.ui import Workbench
    path=w.location.text();w.close()
    reopened=Workbench(database=path,year=2026,month=11)
    try:assert 'BESTÄTIGT MIT ABWEICHUNGEN' in reopened.status.text()
    finally:reopened.close()


def test_confirmation_override_rolls_back_on_sql_failure(tmp_path):
    data,_,_=technical_demo()
    with V2Store(tmp_path/'db',create=True) as store:
        store.connection.execute("CREATE TRIGGER stop BEFORE INSERT ON v2_meta WHEN NEW.key LIKE 'confirmation:%' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with pytest.raises(Exception,match='test failure'):confirm(store,'nov',data,(),allow_violations=True)
        assert not store.confirmations() and store.input_revision==0
        assert not store.connection.execute("SELECT id FROM v2_revisions WHERE id='nov'").fetchall()
