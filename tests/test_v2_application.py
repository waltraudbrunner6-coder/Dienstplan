"""Regressionen für den neuen tatsächlichen Programmeinstieg, keine Attrappen."""
import csv
from dataclasses import replace
from datetime import date
from fractions import Fraction
import io
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import zipfile

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QDialog,QPushButton,QTableWidget,QInputDialog,QListWidget,QDialogButtonBox

from dienstplan.v2.accounting import MonthAccount
from dienstplan.v2.application import standard_month,demonstration_month,OPEN_PROFILE
from dienstplan.v2.catalog import CATALOG,event,lb_dates
from dienstplan.v2.plan_import import selected_events
from dienstplan.v2.contracts import DateRange
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.errors import DomainError
from dienstplan.v2.exporting import export_package
from dienstplan.v2.people import Eligibility
from dienstplan.v2.presentation import hours_minutes,hours_text,contract_text
from dienstplan.v2.solver import solve_feasibility,verify
from dienstplan.v2.ui import Workbench


@pytest.fixture
def app():return QApplication.instance() or QApplication([])


def test_new_month_has_whole_standard_catalog_and_actual_daily_events():
    data,profile,blocks=standard_month(2026,11)
    assert not data.people and not blocks and not data.candidates
    assert len({t.code for t in CATALOG})==18
    active=selected_events(data)
    assert len(data.events)==120 and len(active)==94 and sum(e.service.staff or 0 for e in active)==120
    assert sum((e.service.staff or 0)*(e.attendance.minutes-(30 if e.attendance.minutes>360 else 0)) for e in active)==876*60
    assert {e.service.code for e in data.events if e.attendance.start_day==date(2026,11,12)}=={'KCT10','KCT','TW','T'}
    assert {e.service.code for e in active if e.attendance.start_day==date(2026,11,16)}=={'KC10','KC16','W17'}
    assert data.profile_label==OPEN_PROFILE and data.weekend_policy.owner=='sunday' and profile.month_profile=='M1'
    assert any('WL/BK' in s for s in data.unchecked) and not lb_dates(2026,11)


@pytest.mark.parametrize('year,month',[(2026,12),(2027,1),(2028,2)])
def test_standard_calendar_lengths_and_reserve_period(year,month):
    from calendar import monthrange
    data,_,_=standard_month(year,month)
    for day in range(1,monthrange(year,month)[1]+1):
        terms=[e for e in data.events if e.attendance.start_day==date(year,month,day)]
        if (month==12 and day>=24) or (month==1 and day<=6):
            assert {e.service.key for e in terms if e.service.code=='R'}=={'R_early','R_late'}
        else:assert not any(e.service.code=='R' for e in terms)
    assert not data.candidates  # Kein R-Profil erfunden, keine fiktiven Personen.


@pytest.mark.parametrize('value,expected',[(450,'7,50'),(-135,'-2,25'),(1,'0,02'),(-1,'-0,02'),(6429,'107,15')])
def test_hours_display_and_lossless_unchanged_input(value,expected):
    assert hours_text(value)==expected
    assert hours_minutes(expected,previous=value)==value
    assert hours_minutes('7,5')==450 and hours_minutes('-2.25')==-135


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity','foo',''])
def test_invalid_hours_are_rejected(value):
    with pytest.raises(DomainError):hours_minutes(value)


def test_exact_contract_display_and_minute_roundtrip():
    assert contract_text(Fraction(241,8))=='30,125'
    assert contract_text(Fraction(1,3))=='1/3'
    for value in range(-120,121):assert hours_minutes(hours_text(value),previous=value)==value


def test_exclusions_preserve_existing_rights_and_do_not_invent_license():
    span=DateRange(date(2026,1,1),date(2028,1,1))
    old=Eligibility(span,frozenset({'WL','BK','T','TS'}),None)
    assert Eligibility.from_exclusions(span,old.excluded_codes,None)==old
    normal=Eligibility.from_exclusions(span,{'KC10','WL'})
    assert 'W17' in normal.codes and 'WL' not in normal.codes
    person=demonstration_month()[0].people[0]
    person=replace(person,rights=(normal,))
    assert person.eligibility_errors('WL',event('WL',date(2026,11,10)).attendance)
    assert person.eligibility_errors('N17',event('N17',date(2026,11,10),people=(person.id,)).attendance)
    with pytest.raises(DomainError):Eligibility.from_exclusions(span,{'unknown'})


def test_person_editor_edits_exclusions_and_persists_hours(app,tmp_path,monkeypatch):
    data,profile,old=technical_demo()
    profile=replace(profile,accounts=(MonthAccount('A',1,-1),)+profile.accounts[1:])
    w=Workbench(database=tmp_path/'people.sqlite3',initial=(data,profile,old),year=2026,month=11)
    monkeypatch.setattr(w,'confirm_override',lambda messages,**kw:True)
    monkeypatch.setattr('dienstplan.v2.ui.QMessageBox.question',lambda *_:__import__('PySide6.QtWidgets',fromlist=['QMessageBox']).QMessageBox.StandardButton.Yes)
    def edit(dialog):
        if dialog.windowTitle()=='Dienste ausschließen':
            choices=dialog.findChild(QListWidget)
            for i in range(choices.count()):
                item=choices.item(i)
                if item.text()=='WL':item.setCheckState(Qt.CheckState.Checked)
            dialog.findChild(QDialogButtonBox).accepted.emit()
            return QDialog.DialogCode.Accepted
        rights=next(t for t in dialog.findChildren(QTableWidget) if t.columnCount()==4)
        assert rights.horizontalHeaderItem(2).text().startswith('Ausgeschlossene')
        next(b for b in dialog.findChildren(QPushButton) if b.text()=='Ausgeschlossene Dienste auswählen').click()
        next(b for b in dialog.findChildren(QPushButton) if b.text()=='Personendaten prüfen und übernehmen').click()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',edit)
    w.team.setCurrentCell(0,0);w.person_details()
    assert w.inputs.people[0].rights[0].codes==frozenset({'BK','T','TS'})
    assert not any(c.person_id=='A' and c.code=='WL' for c in w.inputs.candidates)
    assert w.profile.accounts[0].opening_minutes==1 and w.profile.accounts[0].desired_minutes==-1
    w.team.item(0,3).setText('7,5');w.save();w.close()
    reopened=Workbench(database=tmp_path/'people.sqlite3')
    assert reopened.profile.accounts[0].opening_minutes==450
    assert reopened.inputs.people[0].rights[0].excluded_codes==data.people[0].rights[0].excluded_codes|{'WL'}
    reopened.close()


def test_new_month_keeps_people_hours_exclusions_and_account_opening(app,tmp_path,monkeypatch):
    data,profile,old=technical_demo()
    profile=replace(profile,accounts=(MonthAccount('A',123,90),)+profile.accounts[1:])
    w=Workbench(database=tmp_path/'months.sqlite3',initial=(data,profile,old),year=2026,month=11)
    monkeypatch.setattr(QInputDialog,'getText',lambda *_:('2026-12',True))
    w.new_month()
    assert w.inputs.people==data.people and len(w.inputs.events)>90
    assert w.profile.accounts[0]==MonthAccount('A',123,0)
    assert w.store.load_workspace(2026,11)==(data,profile,old,data.events)
    assert not any(d.year==2027 for _,d in w.inputs.known_days)
    assert not any(c.code=='R' for c in w.inputs.candidates)
    w.close()


def test_hours_exports_are_readable_and_exact_workspace_is_retained(tmp_path):
    data,profile,old=technical_demo();path=tmp_path/'export.zip'
    export_package(path,data,profile,old,data.events)
    with zipfile.ZipFile(path) as archive:
        def rows(name):return list(csv.DictReader(io.StringIO(archive.read(name).decode('utf-8-sig')),delimiter=';'))
        plan=rows('dienstplan.csv');hours=rows('stunden.csv');distribution=rows('verteilung.csv')
        assert plan[0]['arbeitsstunden']=='7,50' and 'arbeitsminuten' not in plan[0]
        assert hours[0]['target_hours']=='107,15'
        assert distribution[0]['work_hours']=='30,00'
        assert b'work_minutes' not in archive.read('zeitmengen.csv')
        from dienstplan.v2.codec import restore_workspace
        import json
        assert restore_workspace(json.loads(archive.read('arbeitsstand.json')))==(data,profile,old,data.events)


def test_standard_day_replacements_are_atomic_not_duplicate_needs(app,tmp_path,monkeypatch):
    w=Workbench(database=tmp_path/'standard.sqlite3',year=2026,month=11)
    w.code.setCurrentText('TS');w.day.setText('2026-11-12');w.add_term()
    assert {e.service.code for e in w.inputs.events if e.attendance.start_day==date(2026,11,12)}=={'KCT10','KCT','TW','TS'}
    w.code.setCurrentText('W16');w.day.setText('2026-11-16')
    monkeypatch.setattr(QInputDialog,'getText',lambda *_:('Dokumentierter Ausnahmegrund',True))
    w.add_term()
    assert {e.service.code for e in __import__('dienstplan.v2.plan_import',fromlist=['selected_events']).selected_events(w.inputs) if e.attendance.start_day==date(2026,11,16)}=={'KC10','KC16','W16'}
    w.save();w.close()
    reopened=Workbench(database=tmp_path/'standard.sqlite3')
    assert any(e.service.code=='W16' for e in reopened.inputs.events)
    assert verify(reopened.inputs,(),active_events=__import__('dienstplan.v2.plan_import',fromlist=['selected_events']).selected_events(reopened.inputs))[0].hard_ok
    reopened.close()


def test_pause_reduction_preserves_month_quantities_fixed_pauses_and_coverage():
    from dienstplan.v2.application import service_candidates
    from dienstplan.v2.solver import _reduce_pause_choices
    from dienstplan.v2.pauses import CoverageRule
    from dienstplan.v2.objectives import _night_pause
    data,profile,_=demonstration_month()
    term=next(e for e in data.events if e.service.code=='W17' and e.attendance.start_day==date(2026,11,30))
    candidates=service_candidates((term,),data.people[:1])
    data=replace(data,events=(term,),candidates=candidates,optional_ids=frozenset(),fallbacks=())
    reduced=_reduce_pause_choices(data,candidates,profile)
    from dienstplan.v2.work import quantities
    def monthly(b):return sum(q.work_minutes for q in quantities(b) if q.day.month==11)
    for candidate in candidates:
        assert any(other.work_minutes==candidate.work_minutes and monthly(other)==monthly(candidate) and _night_pause(other)<=_night_pause(candidate) for other in reduced)
    assert len(reduced)<len(candidates)
    assert candidates[-1] in _reduce_pause_choices(data,candidates,profile,(candidates[-1],))
    covered=replace(data,coverage=(CoverageRule(term.id,1,'ausdrückliches Abdeckungsprofil'),))
    assert set(_reduce_pause_choices(covered,candidates,profile))==set(candidates)
