"""Inklusive Kalendergrenzen, exakter Vertrags-Rundlauf und Planerhalt."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from datetime import date
from fractions import Fraction
import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication,QDialog,QDateEdit,QLineEdit,QTableWidget,QPushButton,QMessageBox
from dienstplan.v2.ui import Workbench
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.person_ui import InclusiveDateDelegate,displayed_date,parsed_date


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'person.sqlite3',initial=technical_demo(),year=2026,month=11)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:pytest.fail(str(a)))
    yield w
    w.close();app.processEvents()


def button(dialog):return next(b for b in dialog.findChildren(QPushButton) if b.text()=='Personendaten prüfen und übernehmen')


def test_unchanged_person_roundtrip_shows_inclusive_dates_and_preserves_domain_and_plan(window,monkeypatch):
    w=window;before=(w.inputs,w.blocks,w.events);p=w.inputs.people[0]
    def edit(d):
        first=d.findChild(QDateEdit,'person_employment_first');last=d.findChild(QDateEdit,'person_employment_last')
        assert first.date().toPython()==p.employment.dates.start
        assert last.date().toPython()==date(2027,12,31)
        table=d.findChild(QTableWidget,'person_contract_versions')
        assert table.item(0,1).text()=='31.12.2027' and isinstance(table.itemDelegateForColumn(1),InclusiveDateDelegate)
        button(d).click();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',edit);w.edit_person(p)
    assert (w.inputs,w.blocks,w.events)==before
    assert w.store.load_workspace(2026,11)[2:]==before[1:]


def test_inclusive_end_updates_domain_by_one_day_and_preserves_plan(window,monkeypatch):
    w=window;p=w.inputs.people[0];before=w.blocks
    def edit(d):
        d.findChild(QDateEdit,'person_employment_last').setDate(QDate(2026,11,30))
        table=d.findChild(QTableWidget,'person_contract_versions');table.item(0,2).setText('31,125')
        button(d).click();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',edit);w.edit_person(p)
    assert w.inputs.people[0].employment.dates.end==date(2026,12,1)
    assert w.inputs.people[0].contracts.versions[0].weekly_hours==Fraction(249,8)
    assert w.blocks==before


def test_rejected_person_rule_conflict_keeps_person_and_plan(window,monkeypatch):
    w=window;p=w.inputs.people[0];before=(w.inputs,w.blocks,w.events,w.store.input_revision);messages=[]
    monkeypatch.setattr(w,'confirm_override',lambda found:messages.extend(found) or False)
    def edit(d):
        d.findChild(QDateEdit,'person_employment_last').setDate(QDate(2026,11,1))
        button(d).click();return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog,'exec',edit);w.edit_person(p)
    assert messages and (w.inputs,w.blocks,w.events,w.store.input_revision)==before


def test_new_person_enters_calendar_hours_and_exclusions_in_single_dialog(window,monkeypatch):
    w=window;before=w.blocks
    def edit(d):
        d.findChild(QLineEdit,'person_name').setText('Neue Person')
        first=d.findChild(QDateEdit,'person_employment_first');last=d.findChild(QDateEdit,'person_employment_last')
        assert first.date()==first.minimumDate() and last.date()==last.minimumDate()
        first.setDate(QDate(2026,11,1));last.setDate(QDate(2027,12,31))
        contracts=d.findChild(QTableWidget,'person_contract_versions');rights=d.findChild(QTableWidget,'person_exclusion_versions')
        assert contracts.item(0,0).text()=='01.11.2026' and contracts.item(0,1).text()=='31.12.2027'
        contracts.item(0,2).setText('25,5');rights.item(0,2).setText('N17');assert rights.item(0,3).text()=='unbekannt'
        button(d).click();return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',edit);w.edit_person(None,'NEW')
    added=next(p for p in w.inputs.people if p.id=='NEW')
    assert added.name=='Neue Person' and added.employment.dates.end==date(2028,1,1)
    assert added.contracts.versions[0].weekly_hours==Fraction(51,2)
    assert 'N17' in added.rights[0].excluded_codes and added.rights[0].driving_license is None
    assert w.blocks==before


def test_deleting_automatic_row_never_makes_shifted_manual_dates_automatic(window,monkeypatch):
    w=window
    def edit(d):
        first=d.findChild(QDateEdit,'person_employment_first');last=d.findChild(QDateEdit,'person_employment_last')
        first.setDate(QDate(2026,11,1));last.setDate(QDate(2027,12,31))
        table=d.findChild(QTableWidget,'person_contract_versions')
        next(b for b in d.findChildren(QPushButton) if b.text()=='Version ergänzen').click()
        table.item(1,0).setText('15.11.2026');table.item(1,1).setText('30.11.2026');table.item(1,2).setText('20')
        table.setCurrentCell(0,0)
        next(b for b in d.findChildren(QPushButton) if b.text()=='Gewählte Version entfernen').click()
        assert table.rowCount()==1
        first.setDate(QDate(2026,11,2))
        assert table.item(0,0).text()=='15.11.2026' and table.item(0,1).text()=='30.11.2026'
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog,'exec',edit);w.edit_person(None,'NEW')
