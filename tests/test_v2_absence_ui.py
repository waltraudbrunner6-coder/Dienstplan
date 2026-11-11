"""Echte Qt-Auswahl; keine Kalenderannahmen oder privaten Daten."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from datetime import date
from dataclasses import replace
import pytest
from PySide6.QtCore import Qt,QDate
from PySide6.QtWidgets import QApplication,QDialog,QPlainTextEdit,QMessageBox
from dienstplan.v2.ui import Workbench
from dienstplan.v2.absence_ui import AbsenceDialog
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.entries import Entry
from dienstplan.v2.time import Interval


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'ui.sqlite3',initial=technical_demo(),year=2026,month=11)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:pytest.fail(str(a)))
    yield w
    w.close();app.processEvents()


def leave_form(w,first='2026-11-17',last='2026-11-19'):
    d=AbsenceDialog(w);d.kind.setCurrentIndex(d.kind.findData('urlaub'))
    d.first.setDate(QDate.fromString(first,'yyyy-MM-dd'));d.last.setDate(QDate.fromString(last,'yyyy-MM-dd'))
    return d


def test_explicit_leave_period_counts_every_day_and_weekly_hours_divided_by_five(window):
    d=leave_form(window)
    assert d.selected_days()==frozenset((date(2026,11,17),date(2026,11,18),date(2026,11,19)))
    assert '15,00 h' in d.total.text() and d.save.isEnabled()
    assert not d.days.item(0,0).flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert d.fields()[4]=='2026-11-17|2026-11-18|2026-11-19'
    assert d.span().end.astimezone(__import__('dienstplan.v2.time',fromlist=['vienna']).vienna()).date()==date(2026,11,20)
    d.close()


def test_edit_explains_entire_period_but_does_not_mutate_old_entry(window):
    old=Entry('u','A','urlaub',Interval.local('2026-11-17T00:00','2026-11-20T00:00'),frozenset((date(2026,11,17),)), 'Reise')
    d=AbsenceDialog(window,old)
    assert len(d.selected_days())==3 and old.credit_days==frozenset((date(2026,11,17),)) and d.fields()[-1]=='Reise'
    assert d.last.date().toPython()==date(2026,11,19)
    assert '15,00 h' in d.total.text()
    d.close()


def test_unknown_leave_can_be_corrected_without_losing_plan(window,monkeypatch):
    w=window;old=Entry('u','A','urlaub',Interval.local('2026-11-17T00:00','2026-11-18T00:00'))
    w.inputs=replace(w.inputs,absences=(old,));w.store.save_workspace(w.inputs,w.profile,w.blocks,w.events,expected_revision=w.store.input_revision)
    w.fill();before=w.blocks;events=w.events
    def drive(d):
        assert isinstance(d,AbsenceDialog)
        assert d.save.isEnabled() and '5,00 h' in d.total.text()
        d.save.click();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',drive);w.manual_entry(old)
    assert w.blocks==before and w.events==events and w.batch is None
    assert w.inputs.absences[0].credit_days==frozenset((date(2026,11,17),))
    assert w.store.load_workspace(2026,11)[2:]==(before,events)
    assert not w.missing_leave_entries()


def test_confirmation_guides_to_missing_day_editor(window,monkeypatch):
    w=window;old=Entry('u','A','urlaub',Interval.local('2026-11-17T00:00','2026-11-18T00:00'))
    w.inputs=replace(w.inputs,absences=(old,));w.fill();selected=[]
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(w,'manual_entry',lambda item:selected.append(item))
    w.confirm()
    assert selected==[old] and not w.store.confirmations()


def test_status_details_keep_full_text_while_summary_stays_short(window,monkeypatch):
    w=window;text='3 Zuteilungen; 2 offene Plätze. | '+('Eine ausführliche Meldung. '*100)+' | Letzter vollständiger Hinweis'
    w.set_status(text)
    assert len(w.status.text())<450 and w.status_text==text
    def drive(d):
        content=d.findChild(QPlainTextEdit).toPlainText()
        assert 'Letzter vollständiger Hinweis' in content and content.count('Eine ausführliche Meldung.')==100
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',drive);w.show_status_details()


def test_leave_account_editor_saves_start_balance_and_copy_preserves_it(window,monkeypatch,tmp_path):
    from PySide6.QtWidgets import QDateEdit,QLineEdit,QPushButton,QFileDialog
    from dienstplan.v2.leave_accounts import leave_account_settings,leave_account_rows
    w=window;blocks=w.blocks
    def drive(d):
        d.findChild(QDateEdit,'leave_account_start_month').setDate(QDate(2026,11,1))
        d.findChild(QLineEdit,'leave_account_opening').setText('4,5')
        d.findChild(QPushButton,'leave_account_save').click();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',drive);w.edit_leave_account()
    assert leave_account_settings(w.store)['A'].opening_days==__import__('fractions').Fraction(9,2)
    rows=leave_account_rows(w.store,w.inputs.people,2026,11,current_entries=w.inputs.absences)
    assert rows[0].projected_days==__import__('fractions').Fraction(13,2) and w.blocks==blocks
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(tmp_path/'copy.sqlite3'),''));w.new_file()
    assert leave_account_settings(w.store)['A'].opening_days==__import__('fractions').Fraction(9,2)
    assert w.blocks==blocks


def test_save_metadata_keeps_plan_and_updates_hours(window):
    w=window;before=w.blocks
    w.team.item(0,1).setText('Geänderter Name');w.team.item(0,2).setText('30')
    assert w.save() and w.blocks==before
    assert w.inputs.people[0].name=='Geänderter Name' and w.inputs.people[0].contracts.versions[0].weekly_hours==30
    assert w.store.load_workspace(2026,11)[2]==before


def test_standard_calendar_options_can_be_manually_replaced_and_removed_without_invalid_groups(tmp_path):
    from dienstplan.v2.application import demonstration_month
    app=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'normal.sqlite3',initial=demonstration_month(),year=2026,month=11)
    try:
        assert len(w.inputs.fallbacks)>0 and not any(e.service.code=='KC15' for e in w.events)
        w.code.setCurrentText('KC15');w.day.setText('2026-11-10');w.add_term()
        assert any(e.id=='2026-11-10/KC15' for e in w.events)
        assert not any(e.id in {'2026-11-10/KC10','2026-11-10/KC16'} for e in w.events)
        assert 'KC15-Ersatztermine' in w.status_text
        assert not any('2026-11-10' in g.id for g in w.inputs.fallbacks)
        w.change_terms({'2026-11-11/KC10'})
        assert not any('2026-11-11' in g.id for g in w.inputs.fallbacks)
        assert any(e.id=='2026-11-11/KC16' for e in w.events)
    finally:w.close();app.processEvents()
