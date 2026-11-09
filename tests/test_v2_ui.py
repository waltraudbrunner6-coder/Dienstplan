import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from fractions import Fraction

import pytest
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox,QInputDialog,QDialog,QTableWidget,QPushButton

from dienstplan.v2.entries import preview
from dienstplan.v2.errors import DomainError
from dienstplan.v2.ui import Workbench


@pytest.fixture
def workbench(monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.StandardButton.Yes)
    w=Workbench()
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
    w.team.item(0,2).setText('25,04');w.team.item(0,3).setText('600');w.team.item(0,4).setText('0')
    w.save()
    assert w.inputs.people[0].contracts.versions[0].weekly_hours==Fraction(626,25)
    w.seconds.setValue(1);w.start();wait_worker(w)
    assert w.pending and not w.blocks
    w.apply_result()
    assert len(w.blocks)==8 and w.store.load_workspace(2026,11)[2]==w.blocks
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
    with pytest.raises(ValueError,match='fixierte'):
        w.manual(tuple(b for b in w.blocks if b!=first))
    assert first in w.blocks and first in w.store.load_workspace(2026,11)[2]


def test_thursday_csv_stays_editable_then_atomic_application_after_correction(workbench):
    w=workbench
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;A;wish;freiwunschtag;2026-11-12T00:00;2026-11-13T00:00;;Korrigieren\n'
    w.batch=preview(text,existing=(),budgets=w.budgets(),month='2026-11')
    w.store.save_correction('ui-current',w.batch);w.fill_batch()
    with pytest.raises(ValueError,match='Korrektur'):w.promote()
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
