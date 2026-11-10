import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from fractions import Fraction

import pytest
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox,QInputDialog,QDialog,QTableWidget,QPushButton,QLineEdit

from dienstplan.v2.entries import preview
from dienstplan.v2.errors import DomainError
from dienstplan.v2.ui import Workbench


@pytest.fixture
def workbench(monkeypatch,tmp_path):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    from dienstplan.v2.demo import technical_demo
    monkeypatch.setattr(Workbench,'confirm_override',lambda self,messages:False)
    w=Workbench(database=tmp_path/'ui.sqlite3',initial=technical_demo(),year=2026,month=11)
    yield w
    if w.worker and w.worker.isRunning():w.worker.cancel.set();w.worker.wait(5000)
    w.close();app.processEvents()


def wait_worker(w):
    loop=QEventLoop();w.worker.finished.connect(loop.quit);QTimer.singleShot(10000,loop.quit);loop.exec()
    QApplication.processEvents()
    assert not w.worker.isRunning()


def test_real_qt_input_solver_explicit_acceptance_storage_and_export(workbench,tmp_path,monkeypatch):
    w=workbench
    assert w.team.rowCount()==12 and w.plan.rowCount()==8
    w.team.item(0,2).setText('25,04');w.team.item(0,3).setText('10,00');w.team.item(0,4).setText('0')
    w.save()
    assert w.inputs.people[0].contracts.versions[0].weekly_hours==Fraction(626,25)
    w.seconds.setValue(1);w.start();wait_worker(w)
    assert w.pending and not w.blocks
    assert w.tabs.currentWidget() is w.plan.parentWidget()
    assert all(w.plan.item(row,3).text()!='OFFEN' for row in range(w.plan.rowCount()))
    assert 'VORSCHLAG' in w.plan_state.text()
    assert w.store.load_workspace(2026,11)[2]==()
    assert any(w.hours.item(row,6).text()!='0,00' for row in range(w.hours.rowCount()))
    w.apply_result()
    assert len(w.blocks)==8 and w.store.load_workspace(2026,11)[2]==w.blocks
    assert 'VORSCHLAG' not in w.plan_state.text()
    target=tmp_path/'export.zip'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(target),'ZIP'))
    w.export();assert target.is_file()


def test_changes_during_background_search_make_result_stale(workbench):
    w=workbench;w.seconds.setValue(1);w.start()
    w.team.item(0,1).setText('Geänderter Testname')
    wait_worker(w)
    assert w.pending is None and 'veraltet' in w.status.text()


def test_manual_change_and_individual_fixation_use_independent_rules(workbench):
    w=workbench;first=w.blocks[0]
    w.manual(w.blocks,locked=(first,))
    assert first in w.inputs.locked
    w.manual(tuple(b for b in w.blocks if b!=first))  # Warnung abgelehnt: unverändert
    assert first in w.blocks and first in w.store.load_workspace(2026,11)[2]


def test_thursday_csv_stays_editable_then_atomic_application_after_correction(workbench):
    w=workbench
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;A;wish;freiwunschtag;2026-11-12T00:00;2026-11-13T00:00;;Korrigieren\n'
    w.batch=preview(text,existing=(),budgets=w.budgets(),month='2026-11')
    w.store.save_correction('ui-current',w.batch);w.fill_batch()
    w.promote()  # Warnung abgelehnt: unverändert
    assert not w.store.entries() and w.batch and not w.batch.ready
    fields=w.correction_fields
    w.corrections.item(0,fields.index('von')+1).setText('2026-11-11T00:00')
    w.corrections.item(0,fields.index('bis')+1).setText('2026-11-12T00:00')
    w.promote()
    assert len(w.store.entries())==len(w.inputs.absences)==1 and w.batch is None
    assert w.store.load_workspace(2026,11)[0]==w.inputs and w.events is None


def test_invalid_term_does_not_remove_current_valid_draft(workbench):
    w=workbench;before=w.blocks
    w.code.setCurrentText('KC10');w.day.setText('2026-11-12')
    with pytest.raises(ValueError,match='Teamvariante'):w.add_term()
    assert w.blocks==before


def test_correction_sql_failure_rolls_back_inputs_and_keeps_staging(workbench):
    w=workbench
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;A;wish;freiwunschtag;2026-11-11T00:00;2026-11-12T00:00;;test\n'
    w.batch=preview(text,existing=(),budgets=w.budgets(),month='2026-11')
    w.store.save_correction('ui-current',w.batch);w.fill_batch();before=w.blocks
    w.store.connection.execute("CREATE TRIGGER stop_workspace BEFORE INSERT ON v2_revisions BEGIN SELECT RAISE(ABORT,'test rollback'); END")
    with pytest.raises(Exception,match='test rollback'):w.promote()
    assert w.blocks==before and not w.inputs.absences and not w.store.entries()
    assert w.store.load_correction('ui-current',budgets=w.budgets(),month='2026-11').ready


def test_person_contract_editor_and_following_month_use_confirmed_facts(workbench,monkeypatch):
    w=workbench;w.save();w.confirm()
    monkeypatch.setattr(QInputDialog,'getText',lambda *a:('2026-12',True))
    w.new_month()
    assert w.inputs.month==12 and len(w.profile.history.confirmation_ids)==1
    assert any(a.opening_minutes<0 for a in w.profile.accounts)
    w.team.setCurrentCell(0,0)
    def edit(dialog):
        contracts=next(t for t in dialog.findChildren(QTableWidget) if t.columnCount()==3)
        contracts.item(0,2).setText('37.125')
        commit=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Personendaten prüfen und übernehmen')
        commit.click();return 1
    monkeypatch.setattr(QDialog,'exec',edit)
    w.person_details()
    assert w.inputs.people[0].contracts.versions[0].weekly_hours==Fraction(297,8)
    assert w.store.load_workspace(2026,12)[0]==w.inputs


def test_manual_wish_edit_stays_staged_then_replaces_without_double_budget(workbench,monkeypatch):
    w=workbench
    def stage_dates(start,end):
        def edit(dialog):
            lines=dialog.findChildren(QLineEdit);lines[0].setText(start);lines[1].setText(end)
            next(b for b in dialog.findChildren(QPushButton) if b.text()=='Zur Korrektur/Übernahme vormerken').click()
            return 1
        monkeypatch.setattr(QDialog,'exec',edit)
    w.day_budget.setValue(1)
    stage_dates('2026-11-10T00:00','2026-11-11T00:00');w.manual_entry();w.promote()
    old=w.inputs.absences[0];w.active.setCurrentCell(0,0)
    stage_dates('2026-11-12T00:00','2026-11-13T00:00');w.edit_entry()
    assert w.inputs.absences==(old,) and not w.batch.ready
    assert w.store.correction_replaces('ui-current')==old.id
    fields=w.correction_fields
    w.corrections.item(0,fields.index('von')+1).setText('2026-11-11T00:00')
    w.corrections.item(0,fields.index('bis')+1).setText('2026-11-12T00:00')
    w.promote()
    assert len(w.store.entries())==len(w.inputs.absences)==1 and w.inputs.absences[0].id!=old.id
    assert w.inputs.absences[0].span.start_day.isoformat()=='2026-11-11'
    w.active.setCurrentCell(0,0);w.delete_entry()
    assert not w.inputs.absences and not w.store.entries() and not w.store.load_workspace(2026,11)[0].absences


def preview_result(w,blocks=None):
    from dienstplan.v2.solver import FeasibilityResult
    from dienstplan.v2.serialization import fingerprint
    selected=blocks if blocks is not None else tuple(b for b in w.inputs.candidates if b.person_id in {'C','D'})
    result=FeasibilityResult('feasible',selected,(),(),(),False,0,w.inputs.fingerprint,w.inputs.profile_label,events=w.inputs.events)
    token=(w.generation,w.store.input_revision,w.inputs.fingerprint,fingerprint(w.profile))
    w.on_worker_completed(result,token)
    return result


def test_preview_preserves_old_plan_and_can_be_discarded(workbench):
    w=workbench;saved=w.store.load_workspace(2026,11);old=w.blocks
    preview_result(w)
    assert w.pending and w.blocks==old
    assert all('(C)' in w.plan.item(r,3).text() or '(D)' in w.plan.item(r,3).text() for r in range(w.plan.rowCount()))
    assert w.store.load_workspace(2026,11)==saved
    with pytest.raises(ValueError,match='übernehmen'):w.confirm()
    with pytest.raises(ValueError,match='übernehmen'):w.selected()
    w.discard_preview.click()
    assert w.pending is None and w.blocks==old
    assert all('(A)' in w.plan.item(r,3).text() or '(B)' in w.plan.item(r,3).text() for r in range(w.plan.rowCount()))
    assert w.store.load_workspace(2026,11)==saved


def test_export_and_acceptance_use_visible_preview_and_survive_restart(workbench,tmp_path,monkeypatch):
    import zipfile,json
    from dienstplan.v2.codec import restore_workspace
    w=workbench;result=preview_result(w);old=w.blocks
    target=tmp_path/'preview.zip'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(target),'ZIP'))
    w.export()
    with zipfile.ZipFile(target) as archive:
        assert restore_workspace(json.loads(archive.read('arbeitsstand.json')))[2]==result.blocks
    assert w.store.load_workspace(2026,11)[2]==old
    w.accept.click()
    assert w.blocks==result.blocks and w.pending is None
    reopened=Workbench(database=w.store.path)
    try:
        assert reopened.blocks==result.blocks
        assert '(C)' in reopened.plan.item(0,3).text() or '(D)' in reopened.plan.item(0,3).text()
    finally:reopened.close()


def test_editing_inputs_removes_preview_and_updates_visible_tables(workbench):
    w=workbench;preview_result(w)
    w.team.item(0,1).setText('Neue Eingabe')
    assert w.pending is None and not w.accept.isEnabled()
    assert 'VORSCHLAG' not in w.plan_state.text()
    assert all('(C)' not in w.plan.item(r,3).text() and '(D)' not in w.plan.item(r,3).text() for r in range(w.plan.rowCount()))


def test_partial_and_zero_assignment_results_are_visible_and_honest(workbench):
    from dataclasses import replace
    w=workbench
    result=preview_result(w,())
    assert all(w.plan.item(r,3).text()=='OFFEN' for r in range(w.plan.rowCount()))
    assert '8 offene Plätze' in w.status.text() and 'Noch keine Person' in w.status.text()
    w.discard_result()
    chosen=tuple(b for b in w.inputs.candidates if b.person_id=='C')[:1]
    preview_result(w,chosen)
    assert '7 offene Plätze' in w.status.text()
    assert sum(w.plan.item(r,3).text()!='OFFEN' for r in range(w.plan.rowCount()))==1


def test_invalid_result_is_not_shown_as_preview(workbench):
    w=workbench;old=w.blocks
    preview_result(w,old+(old[0],))
    assert w.pending is None and w.blocks==old
    assert 'verletzt verbindliche Regeln' in w.status.text()
    assert 'VORSCHLAG' not in w.plan_state.text()


def test_manual_person_selection_chooses_pause_without_pause_dialog(workbench,monkeypatch):
    w=workbench;w.plan.setCurrentCell(0,0);old=w.blocks[0]
    calls=[]
    def choose(*args):
        calls.append(args[2]);choices=args[3]
        return next(value for value in choices if '(C)' in value),True
    monkeypatch.setattr(QInputDialog,'getItem',choose)
    w.change_assignment()
    assert len(calls)==1 and 'Person wählen' in calls[0]
    assert any(b.id==old.id and b.person_id=='C' for b in w.blocks)
    assert all('Pause' not in w.plan.item(r,3).text() for r in range(w.plan.rowCount()))


def test_qt_mixed_import_preview_applies_all_or_keeps_previous_plan(workbench,monkeypatch):
    from dienstplan.v2.import_ui import import_dialog
    from test_v2_spreadsheets import row
    w=workbench;old=w.blocks;warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:warnings.append(a[-1]))
    def drive(dialog):
        table=next(t for t in dialog.findChildren(QTableWidget) if t.columnCount()>10)
        assert table.item(0,4).text()=='dienst'
        check=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Vorschau prüfen und vormerken');check.click()
        assert w.blocks==old and w.store.sheet_stage()
        # The same existing slot is an idempotent import.
        next(b for b in dialog.findChildren(QPushButton) if b.text()=='Gesamten Import übernehmen').click()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',drive)
    import_dialog(w,[row(day='2026-11-02',code='WL',pid='A')],{})
    assert not warnings,warnings
    assert w.store.sheet_stage() is None and w.blocks==old
    assert w.tabs.currentWidget() is w.plan.parentWidget()
    assert 'Mo' in w.plan.item(0,7).text()
    assert w.month_grid.rowCount()==12 and 'So' in w.month_grid.horizontalHeaderItem(1).text()


def test_first_manual_assignment_uses_real_selected_week_dates(app=None):
    # Isolated normal application, not the four-term technical fixture.
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from dienstplan.v2.application import demonstration_month
    from dienstplan.v2.solver import verify
    from unittest.mock import patch
    qt=QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory:
        w=Workbench(database=Path(directory)/'normal.sqlite3',initial=demonstration_month(),year=2026,month=11)
        w.plan.setCurrentCell(0,0)
        def select(parent,title,label,items,*_):return (items[0] if title=='Automatische BK/WL-Termine' else next(v for v in items if '(P01)' in v)),True
        with patch.object(QInputDialog,'getItem',select):w.change_assignment()
        assert len(w.blocks)==1 and w.inputs.week_policy is not None
        assert verify(w.inputs,w.blocks,active_events=w.events)[0].hard_ok
        assert not any(a.service.code=='BK' and b.service.code=='WL' and a.attendance.start_day==b.attendance.start_day for a in w.events for b in w.events)
        w.close();qt.processEvents()


def test_unplanned_weekly_view_counts_required_slots_not_all_date_options(tmp_path):
    from dienstplan.v2.automatic_weekly import automatic_weekly
    qt=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'open-weekly.sqlite3',year=2026,month=11)
    w.inputs=automatic_weekly(w.inputs);w.fill()
    assert len(w.inputs.optional_ids)==84
    assert sum(e.service.code=='BK' for e,b in w.plan_rows)==12
    assert sum(e.service.code=='WL' for e,b in w.plan_rows)==24
    assert w.plan.rowCount()==156  # 120 regular slots + 6 weeks × 6 weekly slots.
    assert 'Vorläufige automatische Termine' in w.plan_state.text()
    assert any(w.term_table.item(i,6).text()=='Datumsoption (automatisch)' for i in range(w.term_table.rowCount()))
    w.close();qt.processEvents()


def test_manual_rule_override_requires_confirmation_and_survives_reload(workbench,monkeypatch):
    from dataclasses import replace
    from dienstplan.v2.pauses import automatic_pause_choices
    from dienstplan.v2.solver import verify
    w=workbench
    # Synthetic person has no entitlement; remains selectable with a warning.
    term=w.inputs.events[0]
    person=replace(w.inputs.people[0],rights=())
    w.inputs=replace(w.inputs,people=(person,)+w.inputs.people[1:])
    candidate=automatic_pause_choices(term,person.id,allow_rules=True)[0]
    monkeypatch.setattr(w,'confirm_override',lambda messages:False)
    before=w.blocks
    w.manual((candidate,))
    assert w.blocks==before
    seen=[]
    monkeypatch.setattr(w,'confirm_override',lambda messages:seen.extend(messages) or True)
    w.manual((candidate,))
    assert seen and w.inputs.manual_override and w.blocks==(candidate,)
    loaded=w.store.load_workspace(2026,11)
    assert loaded[0].manual_override and loaded[2]==w.blocks
    assert not verify(loaded[0],loaded[2],active_events=loaded[3])[0].hard_ok
    assert 'REGELÜBERSTEUERUNG' in w.status.text()
