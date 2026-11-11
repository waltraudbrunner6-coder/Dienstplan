"""Echte Qt-Terminmaske mit synthetischem Team und expliziten Wiener Zeiten."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

from dienstplan.v2.catalog import CATALOG
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.errors import DomainError
from dienstplan.v2.term_ui import TermDialog


@pytest.fixture
def form():
    app = QApplication.instance() or QApplication([])
    inputs, _, _ = technical_demo()
    window = QDialog()
    window.inputs = inputs
    window.day = QLineEdit('2026-11-10')
    dialog = TermDialog(window)
    yield dialog
    dialog.close();window.close();app.processEvents()


def select(dialog, key):
    dialog.service.setCurrentIndex(dialog.service.findData(key))


@pytest.mark.parametrize('approve',[False,True])
def test_manual_calendar_rule_needs_override_and_preserves_existing_plan(tmp_path,monkeypatch,approve):
    from dienstplan.v2.ui import Workbench
    app=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'rules.sqlite3',initial=technical_demo(),year=2026,month=11)
    before=(w.inputs,w.blocks,w.events,w.store.input_revision);warnings=[]
    monkeypatch.setattr(w,'confirm_override',lambda messages:warnings.extend(messages) or approve)
    try:
        w.code.setCurrentText('R_early');w.day.setText('2026-11-10')
        w.add_term()
        assert any('24.12.' in m for m in warnings)
        assert w.blocks==before[1]
        if approve:
            added=next(e for e in w.inputs.events if e.id=='2026-11-10/R_early')
            assert added.rule_override and w.inputs.manual_override
            saved=w.store.load_workspace(2026,11)
            assert next(e for e in saved[0].events if e.id==added.id).rule_override
            assert saved[2]==before[1] and added in saved[3]
        else:
            assert (w.inputs,w.blocks,w.events,w.store.input_revision)==before
    finally:w.close();app.processEvents()


def check_person(dialog, index=0):
    dialog.people.item(index).setCheckState(Qt.CheckState.Checked)


def test_catalog_labels_and_regular_service_need_no_guessed_person(form):
    assert form.service.count() == len(CATALOG)
    assert form.day.date().toPython() == date(2026, 11, 10)
    select(form, 'KC10')
    values = form.values()
    assert values == dict(key='KC10', day=date(2026, 11, 10), people=(), reason='', attendance=None)
    assert form.save.isEnabled()
    assert '10:15–16:15' in form.service.currentText() and '6,00 h' in form.summary.text()
    select(form, 'KC15')
    assert 'KC10 und KC16' in form.explanation.text() and '8,50 h' in form.summary.text()
    select(form, 'R_late')
    assert 'Reserve zählt wie normale Arbeit' in form.explanation.text()
    assert '7,50 h' in form.summary.text()


def test_lb_requires_exactly_two_named_people(form):
    select(form, 'LB')
    assert not form.save.isEnabled()
    assert form.people.item(0).text().startswith('Testperson 1')
    check_person(form)
    with pytest.raises(DomainError, match='genau 2'):form.values()
    check_person(form, 1)
    assert form.values()['people'] == ('A', 'B') and form.save.isEnabled()
    check_person(form, 2)
    assert not form.save.isEnabled()


def test_fk_over_midnight_has_explicit_following_day_and_paid_duration(form):
    select(form, 'FK');check_person(form)
    form.start_time.setTime(QTime(18, 0));form.end_time.setTime(QTime(2, 0))
    assert not form.save.isEnabled()
    with pytest.raises(DomainError, match='Ende'):form.values()
    form.next_day.setChecked(True)
    span = form.values()['attendance']
    assert span.minutes == 480 and '7,50 h' in form.summary.text()
    assert '11.11.2026 02:00' in form.summary.text()


def test_w16_requires_reason_and_adapter_avoids_second_reason_dialog(form):
    select(form, 'W16')
    with pytest.raises(DomainError, match='Ersatzgrund'):form.values()
    form.reason.setText('W17 kann erst ab 16 Uhr beginnen')
    assert form.values()['reason'] == 'W17 kann erst ab 16 Uhr beginnen'
    target = SimpleNamespace(code=Mock(), day=Mock(), fixed=Mock(), fk_start=Mock(), fk_end=Mock(), add_term=Mock())
    form.apply_to(target)
    target.add_term.assert_called_once_with(reason='W17 kann erst ab 16 Uhr beginnen')
    target.fixed.setText.assert_called_once_with('')


def test_unknown_service_is_not_silently_replaced(form):
    form.service.addItem('Unbekannt', 'missing')
    form.service.setCurrentIndex(form.service.count()-1)
    with pytest.raises(DomainError, match='Unbekannte Dienstvorlage'):form.values()
    assert not form.save.isEnabled()


def test_fk_ambiguous_autumn_time_requires_explicit_fold():
    app = QApplication.instance() or QApplication([])
    inputs, _, _ = technical_demo(2026, 10)
    window = QDialog();window.inputs = inputs;window.day = QLineEdit('2026-10-25')
    d = TermDialog(window)
    try:
        select(d, 'FK');check_person(d)
        d.start_time.setTime(QTime(2, 30));d.end_time.setTime(QTime(5, 0))
        with pytest.raises(DomainError, match='mehrdeutig'):d.values()
        d.start_fold.setCurrentIndex(d.start_fold.findData(0))
        first = d.values()['attendance']
        d.start_fold.setCurrentIndex(d.start_fold.findData(1))
        second = d.values()['attendance']
        assert first.minutes-second.minutes == 60
    finally:d.close();window.close();app.processEvents()


def test_fk_nonexistent_spring_time_is_rejected_even_with_fold():
    app = QApplication.instance() or QApplication([])
    inputs, _, _ = technical_demo(2026, 3)
    window = QDialog();window.inputs = inputs;window.day = QLineEdit('2026-03-29')
    d = TermDialog(window)
    try:
        select(d, 'FK');check_person(d)
        d.start_time.setTime(QTime(2, 30));d.end_time.setTime(QTime(5, 0))
        with pytest.raises(DomainError, match='existiert'):d.values()
        assert not d.save.isEnabled()
    finally:d.close();window.close();app.processEvents()


@pytest.fixture
def lb_window():
    app = QApplication.instance() or QApplication([])
    inputs, _, blocks = technical_demo(2026, 12)
    w = QDialog();w.inputs=inputs;w.events=inputs.events;w.blocks=blocks
    w.change_terms=Mock(return_value=True)
    yield w
    w.close();app.processEvents()


def test_missing_lb_adds_december_three_dates_and_named_people_with_ts_variant(lb_window,monkeypatch):
    from dataclasses import replace
    from PySide6.QtWidgets import QInputDialog
    from dienstplan.v2.catalog import event
    from dienstplan.v2.term_ui import add_missing_lb
    w=lb_window;ts=event('TS',date(2026,12,17));w.inputs=replace(w.inputs,events=w.inputs.events+(ts,));w.events=w.inputs.events
    before=(w.inputs,w.blocks,w.events);calls=[]
    def choose(parent,title,label,items,current,editable):
        calls.append((label,tuple(items)))
        wanted='A' if len(calls)==1 else 'B'
        assert all('Testperson' in item for item in items)
        return next(item for item in items if '('+wanted+')' in item),True
    monkeypatch.setattr(QInputDialog,'getItem',choose)
    assert add_missing_lb(w) is True
    removed,added=w.change_terms.call_args.args
    assert removed==set() and tuple(e.attendance.start_day for e in added)==(date(2026,12,3),date(2026,12,17),date(2026,12,31))
    assert tuple(e.service.key for e in added)==('LB','LB_TS','LB')
    assert all(e.fixed_people==('A','B') for e in added)
    assert not any('(A)' in item for item in calls[1][1])
    assert (w.inputs,w.blocks,w.events)==before


def test_missing_lb_preserves_existing_pair_and_only_adds_missing_dates(lb_window,monkeypatch):
    from dataclasses import replace
    from PySide6.QtWidgets import QInputDialog
    from dienstplan.v2.catalog import event
    from dienstplan.v2.term_ui import add_missing_lb
    w=lb_window;prior=event('LB',date(2026,12,3),people=('A','B'))
    w.inputs=replace(w.inputs,events=w.inputs.events+(prior,));w.events=w.inputs.events
    count=[0];prompts=[]
    def choose(parent,title,label,items,current,editable):
        prompts.append(label);count[0]+=1
        return next(item for item in items if ('(C)' if count[0]==1 else '(D)') in item),True
    monkeypatch.setattr(QInputDialog,'getItem',choose)
    add_missing_lb(w)
    _,added=w.change_terms.call_args.args
    assert tuple(e.attendance.start_day for e in added)==(date(2026,12,17),date(2026,12,31))
    assert all(e.fixed_people==('C','D') for e in added)
    assert prior in w.inputs.events and prior.fixed_people==('A','B')
    assert all('Bereits vorhandene LB-Termine' in text for text in prompts)


@pytest.mark.parametrize('cancel_at',[1,2])
def test_cancel_missing_lb_does_not_change_plan(lb_window,monkeypatch,cancel_at):
    from PySide6.QtWidgets import QInputDialog
    from dienstplan.v2.term_ui import add_missing_lb
    w=lb_window;before=(w.inputs,w.blocks,w.events);calls=[0]
    def choose(parent,title,label,items,current,editable):
        calls[0]+=1
        return items[0],calls[0]!=cancel_at
    monkeypatch.setattr(QInputDialog,'getItem',choose)
    assert add_missing_lb(w) is None
    assert (w.inputs,w.blocks,w.events)==before and not w.change_terms.called


@pytest.mark.parametrize('before_anchor',[True,False])
def test_no_lb_work_shows_information_without_person_dialog(lb_window,monkeypatch,before_anchor):
    from dataclasses import replace
    from PySide6.QtWidgets import QInputDialog,QMessageBox
    from dienstplan.v2.catalog import event,lb_dates
    from dienstplan.v2.term_ui import add_missing_lb
    w=lb_window
    if before_anchor:
        data,_,_=technical_demo(2026,11);w.inputs=data;w.events=data.events
    else:
        existing=tuple(event('LB',day,people=('A','B')) for day in lb_dates(2026,12))
        w.inputs=replace(w.inputs,events=w.inputs.events+existing);w.events=w.inputs.events
    messages=[]
    monkeypatch.setattr(QMessageBox,'information',lambda *args:messages.append(args[2]))
    monkeypatch.setattr(QInputDialog,'getItem',lambda *args:pytest.fail('Kein leerer Personen-Dialog'))
    add_missing_lb(w)
    assert messages and not w.change_terms.called


def test_missing_lb_needs_two_real_people(lb_window,monkeypatch):
    from dataclasses import replace
    from PySide6.QtWidgets import QInputDialog
    from dienstplan.v2.term_ui import add_missing_lb
    w=lb_window
    w.inputs=replace(w.inputs,people=w.inputs.people[:1],candidates=tuple(b for b in w.inputs.candidates if b.person_id=='A'))
    monkeypatch.setattr(QInputDialog,'getItem',lambda *args:pytest.fail('Kein leerer Personen-Dialog'))
    with pytest.raises(DomainError,match='zwei unterschiedliche'):add_missing_lb(w)
    assert not w.change_terms.called
