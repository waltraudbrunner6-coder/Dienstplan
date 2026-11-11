"""Normale Monatsoberfläche mit synthetischem Import statt isoliertem Testprofil."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from datetime import date
import pytest
from PySide6.QtWidgets import QApplication,QInputDialog,QMessageBox,QFileDialog,QPushButton
from dienstplan.v2.application import demonstration_month,OPEN_PROFILE
from dienstplan.v2.plan_import import prepare_plan_import,selected_events
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.ui import Workbench
from dienstplan.v2.solver import verify


@pytest.fixture
def imported_month(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    data,profile,_=demonstration_month()
    rows=[dict(art='dienst',datum='2026-11-10',dienst=code,person_id=pid) for code,pid in [('KC10','P01'),('KC16','P02')]]
    rows+=[dict(art='dienst',datum='2026-11-11',dienst='BK',person_id='P03')]
    proposal=prepare_plan_import(data,rows)
    assert proposal.ready,proposal.errors
    path=tmp_path/'imported.sqlite3'
    with V2Store(path,create=True) as s:s.apply_sheet_import(proposal,profile,expected_revision=0)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:pytest.fail('Unerwartete Warnung: '+str(a)))
    w=Workbench(database=path,year=2026,month=11)
    monkeypatch.setattr(w,'configure_weekly',lambda:pytest.fail('Manuelle Aktion darf BK/WL-Konfiguration nicht öffnen'))
    monkeypatch.setattr(w,'confirm_override',lambda issues:pytest.fail('Unerwarteter Regelverstoß: '+str(issues)))
    assert w.inputs.week_policy is None and w.inputs.profile_label==OPEN_PROFILE
    yield w
    w.close();app.processEvents()


def select(w,person='P01'):
    index=next(i for i,(_,b) in enumerate(w.plan_rows) if b and b.person_id==person)
    w.plan.setCurrentCell(index,0)
    return w.plan_rows[index][1]


def choose_person(monkeypatch,pid='P05',accept=True):
    def get(parent,title,label,items,*args):
        assert title=='Zuteilung'
        return next(v for v in items if f'({pid})' in v),accept
    monkeypatch.setattr(QInputDialog,'getItem',get)


def assert_saved(w):
    assert w.store.load_workspace(2026,11)==(w.inputs,w.profile,w.blocks,w.events)
    core,calendar=verify(w.inputs,w.blocks,active_events=w.events)
    assert core.hard_ok and calendar.hard_ok


def test_imported_month_change_opens_person_picker_and_transfers_fixation(imported_month,monkeypatch):
    w=imported_month;old=select(w);others=tuple(b for b in w.blocks if b!=old);events=w.events
    choose_person(monkeypatch)
    next(b for b in w.findChildren(QPushButton) if b.text()=='Zuteilung ändern').click()
    changed=next(b for b in w.blocks if b.id==old.id)
    assert changed.person_id=='P05' and changed in w.inputs.locked and old not in w.inputs.locked
    assert set(others)<=set(w.blocks) and w.events==events and w.inputs.week_policy is None
    assert_saved(w)


@pytest.mark.parametrize('action',['remove_assignment','lock_assignment','unlock_all'])
def test_manual_controls_do_not_require_weekly_profile(imported_month,action):
    w=imported_month;old=select(w);events=w.events
    getattr(w,action)()
    if action=='remove_assignment':assert old not in w.blocks and old not in w.inputs.locked
    elif action=='lock_assignment':assert old in w.blocks and old not in w.inputs.locked
    else:assert not w.inputs.locked
    assert w.events==events and w.inputs.week_policy is None
    assert_saved(w)


def test_cancel_manual_assignment_keeps_database_and_plan(imported_month,monkeypatch):
    w=imported_month;select(w);before=(w.inputs,w.blocks,w.events,w.store.input_revision)
    choose_person(monkeypatch,accept=False);w.change_assignment()
    assert (w.inputs,w.blocks,w.events,w.store.input_revision)==before
    assert_saved(w)


def test_explicit_weekly_configuration_preserves_imported_assignments(imported_month,monkeypatch):
    w=imported_month;old=w.blocks
    monkeypatch.setattr(QInputDialog,'getItem',lambda parent,title,label,items,*_:(items[0],True))
    Workbench.configure_weekly(w)
    assert w.blocks==old and w.inputs.week_policy is not None
    assert {b.id for b in old}<={e.id for e in w.events}
    assert_saved(w)


def test_edit_keeps_existing_weekly_dates_and_optional_choices(imported_month,monkeypatch):
    from dienstplan.v2.automatic_weekly import automatic_weekly
    w=imported_month
    w.inputs=automatic_weekly(w.inputs)
    w.events=selected_events(w.inputs,tuple(e for e in reversed(w.inputs.events) if e.service.code in {'BK','WL'}))
    w.store.save_workspace(w.inputs,w.profile,w.blocks,w.events,expected_revision=w.store.input_revision)
    w.fill();events=w.events;options=w.inputs.optional_ids;select(w)
    choose_person(monkeypatch);w.change_assignment()
    assert w.events==events and w.inputs.optional_ids==options
    assert_saved(w)


def test_declining_fixation_change_keeps_original(imported_month,monkeypatch):
    w=imported_month;select(w);before=(w.inputs,w.blocks,w.events,w.store.input_revision)
    choose_person(monkeypatch)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.No)
    w.change_assignment()
    assert (w.inputs,w.blocks,w.events,w.store.input_revision)==before


def test_same_person_is_noop_and_retains_pause(imported_month,monkeypatch):
    w=imported_month;old=select(w,'P02');before=(w.inputs,w.blocks,w.events,w.store.input_revision)
    choose_person(monkeypatch,'P02');w.change_assignment()
    assert (w.inputs,w.blocks,w.events,w.store.input_revision)==before
    assert old.breaks


def test_manual_edit_save_exports_copy_open_and_month_navigation(imported_month,monkeypatch,tmp_path):
    from openpyxl import load_workbook
    from dienstplan.v2.codec import restore_workspace
    import json,zipfile
    w=imported_month;select(w);choose_person(monkeypatch);w.change_assignment()
    original=w.store.path if hasattr(w.store,'path') else w.location.text()
    before=(w.inputs,w.profile,w.blocks,w.events)
    assert w.save()
    for method,name in [('export_grid','grid.xlsx'),('export','plan.zip'),('new_file','copy.sqlite3')]:
        target=tmp_path/name
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,p=target:(str(p),''))
        getattr(w,method)();assert target.exists()
        assert (w.inputs,w.profile,w.blocks,w.events)==before
    assert load_workbook(tmp_path/'grid.xlsx')['Monatsübersicht'].max_row==14
    with zipfile.ZipFile(tmp_path/'plan.zip') as z:
        assert restore_workspace(json.loads(z.read('arbeitsstand.json')))==before
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a:(str(original),''))
    monkeypatch.setattr(QInputDialog,'getItem',lambda parent,title,label,items,*_:(items[0],True))
    w.open_file();assert (w.inputs,w.profile,w.blocks,w.events)==before
    for month in ('2026-12','2026-11'):
        monkeypatch.setattr(QInputDialog,'getText',lambda *a,m=month:(m,True));w.new_month()
        assert (w.inputs.year,w.inputs.month)==tuple(map(int,month.split('-')))
    assert (w.inputs,w.profile,w.blocks,w.events)==before
    assert_saved(w)


def test_copy_does_not_keep_correction_from_original_database(imported_month,monkeypatch,tmp_path):
    from dienstplan.v2.entries import preview
    w=imported_month
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;P01;w;freiwunschtag;2026-11-15T00:00;2026-11-16T00:00;;Test\n'
    w.batch=preview(text,budgets=w.budgets(),month='2026-11')
    w.store.save_correction('ui-current',w.batch);w.fill_batch()
    original=w.location.text()
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(tmp_path/'copy.sqlite3'),''))
    w.new_file()
    assert w.batch is None and w.corrections.rowCount()==0
    with V2Store(original) as s:assert s.load_correction('ui-current',budgets=w.budgets(),month='2026-11').ready


def test_copy_requires_preview_decision(imported_month,monkeypatch):
    w=imported_month;w.pending=object()
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:pytest.fail('Keine Kopie hinter dem sichtbaren Vorschlag'))
    try:
        with pytest.raises(ValueError,match='Ergebnis übernehmen'):w.new_file()
    finally:w.pending=None


def test_open_second_slot_excludes_person_already_in_same_event(imported_month,monkeypatch):
    w=imported_month
    row=next(i for i,(e,b) in enumerate(w.plan_rows) if e.service.code=='BK' and b is None)
    w.plan.setCurrentCell(row,0)
    def choose(parent,title,label,items,*_):
        assert title=='Zuteilung' and not any('(P03)' in value for value in items)
        return next(value for value in items if '(P04)' in value),True
    monkeypatch.setattr(QInputDialog,'getItem',choose);w.change_assignment()
    assert {b.person_id for b in w.blocks if b.id=='2026-11-11/BK'}=={'P03','P04'}
    assert_saved(w)


def test_weekly_reconfiguration_preserves_unfixed_dates_without_freezing_future_solver(imported_month,monkeypatch):
    from dienstplan.v2.automatic_weekly import automatic_weekly
    from dienstplan.v2.pauses import automatic_pause_choices
    w=imported_month;w.inputs=automatic_weekly(w.inputs);w.events=selected_events(w.inputs)
    term=next(e for e in w.events if e.id in w.inputs.optional_ids and e.service.code=='WL')
    block=automatic_pause_choices(term,'P04')[0]
    w.blocks+=(block,);w.fill();options=w.inputs.optional_ids;old=w.blocks
    monkeypatch.setattr(QInputDialog,'getItem',lambda parent,title,label,items,*_:(items[0],True))
    Workbench.configure_weekly(w)
    assert w.blocks==old and w.inputs.optional_ids==options
    assert term.id in {e.id for e in w.events}
    assert_saved(w)


@pytest.mark.parametrize('action',['lock_assignment','remove_assignment','change_assignment'])
def test_fixation_identity_ignores_override_metadata(imported_month,monkeypatch,action):
    w=imported_month;old=select(w)
    w.inputs=replace(w.inputs,locked=tuple(replace(b,rule_override=True) if (b.id,b.person_id)==(old.id,old.person_id) else b for b in w.inputs.locked))
    assert w.is_locked(old)
    choose_person(monkeypatch);getattr(w,action)()
    assert not any((b.id,b.person_id)==(old.id,old.person_id) for b in w.inputs.locked)
    assert_saved(w)
