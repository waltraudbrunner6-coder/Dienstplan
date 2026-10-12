"""Offscreen-Integration: dieselben Widgets, Fachregeln und SQLite wie im Paket."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, time, timedelta

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox, QPushButton

from dienstplan.model import Assignment, Blocker, PlanResult, ValidationError, generate_shifts
from dienstplan.storage import Store
from dienstplan.ui import BlockerDialog, MainWindow, SolverWorker


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, app):
    store = Store(tmp_path / "dienstplan.sqlite3")
    instance = MainWindow(store, 2026, 11)
    errors = []
    instance._error = errors.append
    instance.test_errors = errors
    yield instance
    instance.dirty = False
    instance.close()
    instance.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    store.close()


def test_complete_input_hour_and_save_chain(window):
    assert window.team_table.rowCount() == 12
    assert window.plan_table.rowCount() == 94
    assert window.fairness_table.rowCount() == 48
    window.team_table.item(0, 0).setText("Anna")
    window.team_table.item(0, 1).setText("37,5")
    window.team_table.item(0, 2).setText("10")
    assert window.team_table.item(0, 3).text() == "10"
    window.team_table.item(0, 3).setText("0")
    window.team_table.item(0, 2).setText("12")
    assert window.team_table.item(0, 3).text() == "0"
    assert window.team_table.item(0, 4).text() == "160,72"
    first_shift = generate_shifts(window.data)[0]
    combo, fixed = window._slot_widgets[(first_shift.id, 0)]
    combo.setCurrentIndex(1)
    assert len(window.data.assignments) == 1
    assert window.hours_table.item(0, 6).text() == "8,00"
    assert window.save_month()
    loaded = window.store.load_month(2026, 11)
    assert loaded.employees[0].name == "Anna"
    assert str(loaded.employees[0].weekly_hours) == "37.5"
    assert loaded.employees[0].opening_minutes == 720
    assert loaded.employees[0].desired_minutes == 0
    assert loaded.assignments == window.data.assignments
    assert not window.dirty


def test_manual_duplicate_and_fixed_assignment_rejected(window):
    shift = generate_shifts(window.data)[0]
    first, fixed = window._slot_widgets[(shift.id, 0)]
    first.setCurrentIndex(1)
    second, _ = window._slot_widgets[(shift.id, 1)]
    second.setCurrentIndex(1)
    assert len(window.data.assignments) == 1
    assert window.test_errors and "abgelehnt" in window.test_errors[-1]
    first, fixed = window._slot_widgets[(shift.id, 0)]
    fixed.setChecked(True)
    assert window.data.assignments[0].fixed
    first.setCurrentIndex(2)
    assert window.data.assignments[0].employee_id == window.data.employees[0].id
    assert "fixiert" in window.test_errors[-1]
    first, fixed = window._slot_widgets[(shift.id, 0)]
    fixed.setChecked(False)
    first.setCurrentIndex(2)
    assert window.data.assignments[0].employee_id == window.data.employees[1].id
    assert not window.data.assignments[0].fixed


def test_night_shift_and_blocker_next_day_labels(window):
    assert window.shift_table.cellWidget(2, 3).text() == "Folgetag (+1 Tag)"
    dialog = BlockerDialog(window.data.employees[0], 2026, 11, parent=window)
    dialog.whole.setChecked(False)
    from PySide6.QtCore import QTime
    dialog.start.setTime(QTime(22, 0)); dialog.end.setTime(QTime(6, 0))
    blocker = dialog.value()
    assert blocker.end - blocker.start == timedelta(hours=8)
    assert "Folgetag" in dialog.end_note.text()
    dialog.close()


def test_atomic_blocker_limit_and_visible_preference_conflict(window):
    employee = window.data.employees[0]
    blockers = [Blocker(str(day), employee.id, datetime(2026, 11, day), datetime(2026, 11, day + 1), 1)
                for day in range(1, 6)]
    with pytest.raises(ValidationError, match="vier"):
        window._replace_blockers(window.collect_data(), employee, blockers)
    assert not window.store.get_blockers(employee.id)
    shift = generate_shifts(window.data)[0]
    blocker = Blocker("wish", employee.id, shift.start, shift.end, 2, "Privater Termin")
    window._replace_blockers(window.collect_data(), employee, [blocker])
    window._slot_widgets[(shift.id, 0)][0].setCurrentIndex(1)
    assert "Wunsch übergangen" in window.plan_table.item(0, 5).text()
    assert "Privater Termin" in window.conflicts.toPlainText()
    hard = Blocker("hard", employee.id, shift.start, shift.end, 1)
    with pytest.raises(ValidationError, match="bestehende Zuteilungen"):
        window._replace_blockers(window.collect_data(), employee, [hard])
    assert window.store.get_blockers(employee.id)[0].priority == 2


def test_csv_error_preview_disables_save_without_mutating(window, tmp_path, monkeypatch):
    source = tmp_path / "fehler.csv"
    source.write_text("datum;von;bis;prioritaet;kommentar\n2026-11-10;08:00;;1;Fehler\n", encoding="utf-8-sig")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(source), "CSV"))
    seen = []
    def reject_preview(dialog):
        save = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Import übernehmen")
        seen.append(save.isEnabled())
        from PySide6.QtWidgets import QTextEdit
        assert "Zeile 2" in dialog.findChild(QTextEdit).toPlainText()
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog, "exec", reject_preview)
    window.import_csv()
    assert seen == [False]
    assert not window.store.get_blockers()
    assert not window.test_errors


def test_new_month_keeps_identity_and_independent_settings(window):
    assert window.save_month()
    previous_ids = [e.id for e in window.data.employees]
    window.month_combo.setCurrentIndex(11)
    assert window.data.month == 12
    assert [e.id for e in window.data.employees] == previous_ids
    assert not window.data.assignments
    window.shift_table.cellWidget(0, 0).setText("Neue Frühschicht")
    assert window.save_month()
    assert window.store.load_month(2026, 11).shift_types[0].name == "Frühdienst"
    assert window.store.load_month(2026, 12).shift_types[0].name == "Neue Frühschicht"


def test_confirmed_month_is_readonly_and_next_balance_is_forecast(window, monkeypatch):
    data = window.data
    for index, shift in enumerate(data.shift_types):
        shift.start = time(0, index)
        shift.end = time(0, index + (2 if shift.special else 1))
    data.assignments = [Assignment(s.id, e.id) for s in generate_shifts(data) for e in data.employees[:2]]
    window._fill()
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window.toggle_confirmed()
    assert window.data.confirmed
    assert not window.plan_button.isEnabled()
    assert not window.team_table.isEnabled()
    window.month_combo.setCurrentIndex(11)
    assert window.data.month == 12 and not window.data.confirmed
    from dienstplan.hours import hour_rows
    previous = window.store.load_month(2026, 11)
    expected = {row.employee_id: row.projected_balance_minutes for row in hour_rows(previous)}
    for employee in window.data.employees:
        assert employee.opening_minutes == expected[employee.id]
        assert employee.desired_minutes == employee.opening_minutes


def test_background_worker_result_and_cleanup(window, monkeypatch):
    from dienstplan import planner
    def fake_solve(data, history=None, boundary=None, time_limit=20, cancel=None, wish_history=None):
        assert cancel is not None and time_limit == 20
        assert wish_history == []
        shift = generate_shifts(data)[0]
        chosen = [Assignment(shift.id, data.employees[0].id)]
        return PlanResult("incomplete", chosen, planner.coverage(data, chosen))
    monkeypatch.setattr(planner, "solve", fake_solve)
    loop = QEventLoop()
    window.start_planning()
    assert window._thread is not None
    window._thread.finished.connect(loop.quit)
    timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
    loop.exec()
    timeout.stop()
    assert window._thread is None
    assert len(window.data.assignments) == 1
    assert "Unvollständiger Entwurf" in window.result_status.text()
    assert window.plan_button.isEnabled()
    assert not window.cancel_button.isEnabled()


def test_worker_error_is_german_and_ui_recovers(window, monkeypatch):
    from dienstplan import planner
    def fail(*args, **kwargs): raise RuntimeError("Testfehler")
    monkeypatch.setattr(planner, "solve", fail)
    loop = QEventLoop()
    window.start_planning()
    window._thread.finished.connect(loop.quit)
    timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
    loop.exec()
    timeout.stop()
    assert window._thread is None
    assert window.plan_button.isEnabled()
    assert "Die Planung konnte nicht ausgeführt werden" in window.test_errors[-1]
    assert "fehlgeschlagen" in window.result_status.text()


def test_repeated_solver_runs_keep_gui_callbacks_on_main_thread(window, monkeypatch, app):
    from PySide6.QtCore import QThread
    from dienstplan import planner
    main_thread = app.thread()
    def fake_solve(data, **kwargs):
        assert QThread.currentThread() != main_thread
        chosen = [Assignment(generate_shifts(data)[0].id, data.employees[0].id)]
        return PlanResult("incomplete", chosen, planner.coverage(data, chosen))
    monkeypatch.setattr(planner, "solve", fake_solve)
    original_refresh = window._refresh_summaries
    callback_threads = []
    def refresh(*args):
        callback_threads.append(QThread.currentThread() == main_thread)
        return original_refresh(*args)
    monkeypatch.setattr(window, "_refresh_summaries", refresh)
    for _ in range(5):
        window.data.assignments = []; window._fill_plan()
        loop = QEventLoop()
        window.start_planning()
        window._thread.finished.connect(loop.quit)
        timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
        loop.exec(); timeout.stop()
        assert window._thread is None and len(window.data.assignments) == 1
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert callback_threads and all(callback_threads)


def test_existing_plan_requires_explicit_result_adoption(window, monkeypatch):
    shift = generate_shifts(window.data)[0]
    original = Assignment(shift.id, window.data.employees[0].id)
    replacement = Assignment(shift.id, window.data.employees[1].id)
    window.data.assignments = [original]
    result = PlanResult("incomplete", [replacement], {shift.id: 1})
    monkeypatch.setattr(QMessageBox, "exec", lambda dialog: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda dialog: next(b for b in dialog.buttons()
                      if dialog.buttonRole(b) == QMessageBox.ButtonRole.RejectRole))
    window._receive_result(result)
    assert window.data.assignments == [original]
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda dialog: next(b for b in dialog.buttons()
                      if dialog.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole))
    window._receive_result(result)
    assert window.data.assignments == [replacement]


def test_cancel_is_requested_and_worker_is_cleaned_up(window, monkeypatch):
    from dienstplan import planner
    def fake_solve(data, cancel=None, **kwargs):
        assert cancel.wait(2)
        return PlanResult("cancelled")
    monkeypatch.setattr(planner, "solve", fake_solve)
    loop = QEventLoop()
    window.start_planning()
    window._thread.finished.connect(loop.quit)
    window.cancel_planning()
    timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
    loop.exec(); timeout.stop()
    assert window._thread is None
    assert window.plan_button.isEnabled()
    assert "abgebrochen" in window.result_status.text()


@pytest.mark.parametrize("fixed", [False, True])
def test_new_rest_limit_replans_unfixed_draft_but_protects_fixed(window, monkeypatch, fixed):
    from dienstplan import planner
    shifts = generate_shifts(window.data)
    employee = window.data.employees[0]
    window.data.assignments = [Assignment(shifts[0].id, employee.id, fixed), Assignment(shifts[1].id, employee.id, fixed)]
    window.data.rules.rest_minutes = 60
    window._fill()
    assert "Ungültiger Entwurf" in window.result_status.text()
    calls = []
    def fake_solve(data, **kwargs):
        calls.append(data)
        chosen = [Assignment(shifts[0].id, employee.id)]
        return PlanResult("incomplete", chosen, planner.coverage(data, chosen))
    monkeypatch.setattr(planner, "solve", fake_solve)
    monkeypatch.setattr(QMessageBox, "exec", lambda dialog: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda dialog: next(b for b in dialog.buttons()
                      if dialog.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole))
    loop = QEventLoop()
    window.start_planning()
    if fixed:
        assert window._thread is None and not calls
        assert "Ruhezeit" in window.test_errors[-1]
    else:
        assert window._thread is not None
        window._thread.finished.connect(loop.quit)
        timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
        loop.exec(); timeout.stop()
        assert window._thread is None and calls
        assert len(window.data.assignments) == 1
        assert not window.test_errors
