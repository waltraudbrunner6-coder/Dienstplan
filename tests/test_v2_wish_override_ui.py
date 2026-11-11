"""Genehmigte Wunschkonfiguration sperrt keine physisch gültige Planung.

Alle Personen/Daten sind synthetisch. Die Acht-Dienste-Fassung ist ein gültiger
Startpunkt; der Worker darf bei zwei Sekunden ohne Optimalitätsbeweis liefern.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox

from dienstplan.v2.catalog import event
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.entries import Entry
from dienstplan.v2.solver import verify,verify_for_planning
from dienstplan.v2.time import Interval
from dienstplan.v2.ui import Workbench


@pytest.fixture
def approved_month(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    data,profile,old=technical_demo()
    wanted=Entry('accepted-thursday','C','freiwunschtag',Interval.local('2026-11-12T00:00','2026-11-13T00:00'),rule_override=True)
    data=replace(data,absences=(wanted,),manual_override=True,override_notes=('Donnerstagswunsch ausdrücklich genehmigt.',),locked=(old[0],))
    w=Workbench(database=tmp_path/'approved.sqlite3',initial=(data,profile,old),year=2026,month=11)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:pytest.fail('Unerwarteter Fehlerdialog: '+str(a)))
    monkeypatch.setattr(w,'configure_weekly',lambda:pytest.fail('Technischer Bestandsplan benötigt keine neue Wochenkonfiguration.'))
    monkeypatch.setattr(w,'confirm_override',lambda messages,**kw:pytest.fail('Genehmigter Wunsch darf keine neue Warnbestätigung verlangen: '+str(messages)))
    yield w,wanted,old
    if w.worker and w.worker.isRunning():w.worker.cancel.set();w.worker.wait(5000)
    w.close();app.processEvents()


def assert_permission_and_lock(w,wanted,lock):
    assert w.inputs.manual_override
    assert next(e for e in w.inputs.absences if e.id==wanted.id).rule_override
    assert lock in w.inputs.locked and lock in w.blocks


def wait_worker(w):
    clock=QElapsedTimer();clock.start()
    while w.worker.isRunning() and clock.elapsed()<15000:
        QApplication.processEvents();QTest.qWait(10)
    if w.worker.isRunning():
        w.worker.cancel.set();w.worker.wait(5000)
        pytest.fail('Worker überschreitet bei 2 Sekunden Suchbudget die Testfrist.')
    QApplication.processEvents()


def test_real_worker_shows_and_accepts_plan_with_approved_thursday_wish_and_reopens(approved_month):
    w,wanted,old=approved_month;old_events=w.events;path=Path(w.location.text());lock=w.inputs.locked[0]
    strict,_=verify(w.inputs,w.blocks,active_events=w.events)
    assert any(i.rule=='overridden_rule' for i in strict.issues)
    checked,calendar=verify_for_planning(w.inputs,w.blocks,active_events=w.events)
    assert checked.hard_ok and calendar.hard_ok
    w.seconds.setValue(2);w.start();wait_worker(w)
    assert w.pending is not None,w.status_text
    result,_=w.pending
    assert len(result.blocks)==8 and not result.open_slots and lock in result.blocks
    assert w.tabs.currentWidget() is w.plan.parentWidget()
    assert w.blocks==old  # Vorschau ersetzt den gespeicherten Stand erst nach Übernahme.
    w.apply_result()
    assert len(w.blocks)==8 and w.events==old_events
    assert_permission_and_lock(w,wanted,lock)
    persisted=w.store.load_workspace(2026,11)
    assert persisted==(w.inputs,w.profile,w.blocks,w.events)
    w.close()
    reopened=Workbench(database=path,year=2026,month=11)
    try:
        assert_permission_and_lock(reopened,wanted,lock)
        assert len(reopened.blocks)==8 and reopened.events==old_events
    finally:reopened.close()


def test_valid_manual_change_and_save_retain_approval_without_repeat_prompt(approved_month):
    w,wanted,old=approved_month;lock=w.inputs.locked[0]
    previous=next(b for b in old if b.person_id=='B' and b.id==lock.id)
    term=next(e for e in w.events if e.id==previous.id)
    replacement=term.assign('D',previous.breaks)
    changed=tuple(replacement if b==previous else b for b in old)
    w.manual(changed)
    assert w.blocks==changed
    assert_permission_and_lock(w,wanted,lock)
    w.team.item(0,1).setText('Geänderter Anzeigename')
    assert w.save()
    assert_permission_and_lock(w,wanted,lock)
    assert w.store.load_workspace(2026,11)==(w.inputs,w.profile,w.blocks,w.events)


@pytest.mark.parametrize('conflict',['urlaub','ruhe'])
def test_true_new_conflicts_still_require_consent_and_rejection_keeps_old_plan(approved_month,monkeypatch,conflict):
    w,wanted,old=approved_month;lock=w.inputs.locked[0]
    if conflict=='urlaub':
        leave=Entry('real-vacation','C','urlaub',Interval.local('2026-11-02T00:00','2026-11-03T00:00'),frozenset((date(2026,11,2),)))
        w.inputs=replace(w.inputs,absences=w.inputs.absences+(leave,))
        previous=next(b for b in old if b.id==lock.id and b.person_id=='B')
        term=next(e for e in w.events if e.id==previous.id)
        replacement=term.assign('C',previous.breaks)
        invalid=tuple(replacement if b==previous else b for b in old)
        expected='leave'
    else:
        term=event('KC10',date(2026,11,3));replacement=term.assign('A')
        people=tuple(replace(p,rights=tuple(replace(r,codes=r.codes|{'KC10'}) for r in p.rights)) if p.id=='A' else p for p in w.inputs.people)
        w.inputs=replace(w.inputs,people=people,events=w.inputs.events+(term,),candidates=w.inputs.candidates+(replacement,))
        w.events=w.events+(term,)
        invalid=w.blocks+(replacement,);expected='rest'
    w.store.save_workspace(w.inputs,w.profile,w.blocks,w.events,expected_revision=w.store.input_revision);w.fill()
    before=(w.inputs,w.blocks,w.events,w.store.input_revision)
    checked,calendar=verify_for_planning(w.inputs,invalid,active_events=w.events)
    assert expected in {i.rule for i in checked.issues+calendar.issues}
    messages=[]
    monkeypatch.setattr(w,'confirm_override',lambda found,**kw:messages.extend(found) or False)
    w.manual(invalid)
    assert messages and not any('Donnerstag' in message for message in messages)
    assert (w.inputs,w.blocks,w.events,w.store.input_revision)==before
    assert_permission_and_lock(w,wanted,lock)
    assert w.store.load_workspace(2026,11)==(w.inputs,w.profile,w.blocks,w.events)


def test_export_keeps_strict_audit_and_evaluates_only_under_approved_wish_conditions(approved_month,tmp_path):
    from dienstplan.v2.exporting import export_package
    w,_,_=approved_month
    manifest=export_package(tmp_path/'with-conditions.zip',w.inputs,w.profile,w.blocks,w.events)
    assert manifest['accepted_wish_exceptions'] and manifest['objectives']
    assert all(i['rule']=='overridden_rule' for i in manifest['issues'])
    assert manifest['objective_status']=='bewertet unter genehmigten Freiwunschvorgaben'
    assert any('Genehmigte' in note for note in manifest['unchecked'])


def test_real_fixed_rest_failure_shows_person_date_service_and_hours_without_losing_plan(approved_month):
    from dienstplan.v2.application import service_candidates
    from dienstplan.v2.serialization import fingerprint
    from dienstplan.v2.solver import solve_feasibility
    w,_,old=approved_month
    late=event('KC16',date(2026,11,24));early=event('KC10',date(2026,11,25))
    from dienstplan.v2.pauses import automatic_pause_choices
    locks=(automatic_pause_choices(late,'A')[0],early.assign('A'))
    people=tuple(replace(p,rights=tuple(replace(r,codes=r.codes|{'KC10','KC16'}) for r in p.rights)) if p.id=='A' else p for p in w.inputs.people)
    w.inputs=replace(w.inputs,people=people,events=w.inputs.events+(late,early),locked=locks,
                     candidates=w.inputs.candidates+service_candidates((late,early),people))
    w.store.save_workspace(w.inputs,w.profile,old,w.events,expected_revision=w.store.input_revision)
    before=w.store.input_revision
    result=solve_feasibility(w.inputs,time_limit=2)
    assert result.status=='infeasible'
    token=(w.generation,before,w.inputs.fingerprint,fingerprint(w.profile))
    w.on_worker_completed(result,token)
    assert w.pending is None and w.blocks==old and w.store.input_revision==before
    assert '(A)' in w.status_text and '25.11.2026' in w.status_text and 'KC10' in w.status_text
    assert '10,25 h' in w.status_text and '11,00 h' in w.status_text and '0,75 h' in w.status_text
    assert 'bisherige Dienstplan bleibt erhalten' in w.status_text


def test_timeout_is_not_reported_as_infeasible_and_preserves_previous_plan(approved_month):
    from dienstplan.v2.serialization import fingerprint
    from dienstplan.v2.solver import solve_feasibility
    w,_,old=approved_month
    result=solve_feasibility(w.inputs,time_limit=1e-12)
    assert result.status=='unknown'
    token=(w.generation,w.store.input_revision,w.inputs.fingerprint,fingerprint(w.profile))
    w.on_worker_completed(result,token)
    assert w.blocks==old and w.pending is None
    assert 'Zeitlimit' in w.status_text and 'Vorgabenkonflikt' not in w.status_text and 'infeasible' not in w.status_text
