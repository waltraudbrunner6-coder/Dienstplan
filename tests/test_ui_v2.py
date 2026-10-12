"""Qt-Regressionen für Ausnahmetage, Freiwünsche und unveränderte Monatsstände."""
import copy
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, time
from decimal import Decimal

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTime, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QInputDialog, QMessageBox

from dienstplan.hours import demand_minutes, fairness_rows
from dienstplan.model import Assignment, Blocker, PlanResult, WishHistoryEntry, generate_shifts
from dienstplan.storage import Store
from dienstplan.ui import MainWindow
from dienstplan.wishes import wish_key


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, app):
    store = Store(tmp_path / "dienstplan.sqlite3")
    instance = MainWindow(store, 2026, 11)
    instance.test_errors = []
    instance._error = instance.test_errors.append
    yield instance
    instance.dirty = False
    instance.close(); instance.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents(); store.close()


def november_fixture(window):
    for employee in window.data.employees:
        employee.weekly_hours = Decimal("25")
        employee.opening_minutes = employee.desired_minutes = 0
    for shift, start, end, pause in zip(window.data.shift_types,
                                        [time(10), time(16), time(17), time(19)],
                                        [time(16), time(22), time(1), time(4)], [0, 0, 30, 30]):
        shift.start, shift.end, shift.pause_minutes = start, end, pause
    window._fill()


def complete_short_month(window):
    for index, shift in enumerate(window.data.shift_types):
        shift.start = time(0, index); shift.end = time(0, index + 1)
    window.data.assignments = [Assignment(shift.id, employee.id)
                               for shift in generate_shifts(window.data) for employee in window.data.employees[:2]]
    window._fill()


def test_exception_updates_real_demand_slots_fairness_and_wishes(window):
    november_fixture(window)
    employee = window.data.employees[0]
    wish = Blocker("only-early", employee.id, datetime(2026, 11, 16, 10), datetime(2026, 11, 16, 16), 2)
    window.data.blockers = [wish]; window._refresh_summaries()
    assert window.wishes_table.item(0, 1).text() == "1"
    assert demand_minutes(window.data) == 1238 * 60
    assert sum(shift.staff_required for shift in generate_shifts(window.data)) == 188
    key = "2026-11-16/frueh"
    window._exception_widgets[key].setChecked(True)
    assert window.data.exceptions == {key}
    assert demand_minutes(window.data) == 1226 * 60
    assert sum(shift.staff_required for shift in generate_shifts(window.data)) == 186
    assert window.plan_table.rowCount() == 93
    assert "Frühdienst" in window.exception_table.item(15, 5).text()
    assert "Entfällt" in window.exception_table.item(15, 5).text()
    assert "1226,00" in window.conflicts.toPlainText()
    assert window.wishes_table.item(0, 1).text() == "0"
    # Fairness bezieht sich auf wirklich zugeteilte Dienste. Entfallene
    # Termine liefern weder Bedarf noch mögliche Zuteilungen/Sollanteile.
    chosen = [Assignment(shift.id, employee.id) for shift in generate_shifts(window.data)
              if shift.type_id == "frueh" for employee in window.data.employees[:2]]
    fair = [row for row in fairness_rows(window.data, chosen) if row["type_id"] == "frueh"]
    assert sum(row["expected_count"] for row in fair) == pytest.approx(58)
    assert all(row["expected_count"] == pytest.approx(58 / 12) for row in fair)
    active = {shift.id for shift in generate_shifts(window.data)}
    assert {"2026-11-16/spaet", "2026-11-16/nacht", "2026-11-15/nacht"} <= active
    window._exception_widgets[key].setChecked(False)
    assert demand_minutes(window.data) == 1238 * 60
    assert window.wishes_table.item(0, 1).text() == "1"
    assert "wieder aktiviert" in window.conflicts.toPlainText()


def test_all_daily_exceptions_leave_special_and_previous_night(window):
    november_fixture(window)
    window.exception_table.selectRow(3)  # Mittwoch, 4. November
    window.deactivate_selected_days()
    assert window.data.exceptions == {f"2026-11-04/{kind}" for kind in ("frueh", "spaet", "nacht")}
    active = {shift.id for shift in generate_shifts(window.data)}
    assert {"2026-11-04/sonder", "2026-11-03/nacht"} <= active
    assert not {f"2026-11-04/{kind}" for kind in ("frueh", "spaet", "nacht")} & active
    window.exception_table.selectRow(3)
    window.restore_selected_days()
    assert not window.data.exceptions
    window.set_exceptions({"2026-11-30/nacht", "2026-11-04/frueh"})
    assert "2026-11-29/nacht" in {shift.id for shift in generate_shifts(window.data)}
    window.restore_all_exceptions()
    assert not window.data.exceptions and window.plan_table.rowCount() == 94


def test_deactivation_removes_assignments_and_fixed_only_after_named_confirmation(window, monkeypatch):
    key = "2026-11-16/frueh"
    first, second = window.data.employees[:2]
    original = [Assignment(key, first.id, True), Assignment(key, second.id), Assignment("2026-11-17/spaet", first.id)]
    window.data.assignments = original.copy(); window._fill()
    questions = []
    def refuse(*args, **kwargs):
        questions.append(args[2]); return QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", refuse)
    window._exception_widgets[key].setChecked(True)
    assert window.data.assignments == original and not window.data.exceptions
    assert not window._exception_widgets[key].isChecked()
    assert first.name in questions[-1] and second.name in questions[-1]
    assert "fixiert" in questions[-1] and "2 zugeteilte Einsätze" in questions[-1]
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window._exception_widgets[key].setChecked(True)
    assert window.data.assignments == [original[-1]]
    assert window.data.exceptions == {key}
    assert first.name in window.conflicts.toPlainText() and "fixiert" in window.conflicts.toPlainText()
    assert "2 Einsätze" in window.statusBar().currentMessage()
    window.restore_all_exceptions()
    assert window.data.assignments == [original[-1]]  # frühere Zuteilungen bleiben bewusst entfernt


def test_confirmed_month_rejects_exception_and_solver_result(window, monkeypatch):
    complete_short_month(window)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window.toggle_confirmed()
    before = copy.deepcopy(window.data)
    assert before.confirmed and before.wish_snapshot is not None
    assert not window.exception_table.isEnabled()
    assert not window.set_exceptions({"2026-11-16/frueh"})
    window.start_planning()
    window._receive_result(PlanResult("feasible", []))
    assert window.data == before
    assert window.store.load_month(2026, 11) == before
    assert window._thread is None
    assert any("bestätigten" in error.lower() for error in window.test_errors)


def test_exception_storage_new_month_and_copy_templates_are_independent(window, monkeypatch):
    window.team_table.item(0, 1).setText("17,75")
    window.set_exceptions({"2026-11-16/frueh"})
    assert window.save_month()
    assert window.store.load_month(2026, 11).employees[0].weekly_hours == Decimal("17.75")
    assert window.store.load_month(2026, 11).exceptions == {"2026-11-16/frueh"}
    window.month_combo.setCurrentIndex(11)
    assert window.data.month == 12 and not window.data.exceptions
    assert window.data.employees[0].weekly_hours == Decimal("17.75")
    window.set_exceptions({"2026-12-17/nacht"})
    assert window.save_month()
    monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("November 2026", True))
    window.copy_shifts()
    assert window.data.exceptions == {"2026-12-17/nacht"}
    assert window.store.load_month(2026, 11).exceptions == {"2026-11-16/frueh"}
    assert window.save_month()
    window.month_combo.setCurrentIndex(10)
    assert window._exception_widgets["2026-11-16/frueh"].isChecked()


def test_wishes_overview_counts_unique_relevant_p2_refreshes_manual_and_history(window, monkeypatch):
    employee = window.data.employees[0]
    shift = generate_shifts(window.data)[0]
    wish = Blocker("wish", employee.id, shift.start, shift.end, 2, "Privat")
    duplicate = Blocker("duplicate", employee.id, shift.start, shift.end, 2, "Anderer Kommentar")
    hard = Blocker("hard", employee.id, datetime(2026, 11, 5), datetime(2026, 11, 6), 1)
    irrelevant = Blocker("irrelevant", employee.id, datetime(2026, 12, 5), datetime(2026, 12, 6), 2)
    window.data.blockers = [wish, duplicate, hard, irrelevant]
    monkeypatch.setattr(window.store, "wish_history", lambda *args: [WishHistoryEntry(employee.id, {wish_key(wish), "previous"}, ["2026-10"])])
    window._fill()
    assert [window.wishes_table.item(0, index).text() for index in range(1, 6)] == ["1", "1", "0", "2", "2"]
    assert "2026-10" in window.wishes_table.item(0, 6).text()
    window._slot_widgets[(shift.id, 0)][0].setCurrentIndex(1)
    assert [window.wishes_table.item(0, index).text() for index in range(1, 6)] == ["1", "0", "1", "2", "2"]
    assert "Privat" in window.conflicts.toPlainText()
    window._slot_widgets[(shift.id, 0)][0].setCurrentIndex(0)
    assert window.wishes_table.item(0, 2).text() == "1"
    assert window.wishes_table.item(0, 3).text() == "0"


def test_legacy_confirmed_wish_data_is_explicitly_unknown(window):
    window.data.confirmed = True
    window.data.wish_snapshot = None
    window._fill()
    assert "damals nicht erfasst" in window.wishes_table.item(0, 6).text()
    assert "kein historischer Nachweis" in window.conflicts.toPlainText()


def test_wishes_csv_export_matches_screen(window, tmp_path, monkeypatch):
    path = tmp_path / "freiwuensche.csv"
    employee = window.data.employees[0]
    shift = generate_shifts(window.data)[0]
    window.data.blockers = [Blocker("wish", employee.id, shift.start, shift.end, 2)]
    window.data.assignments = [Assignment(shift.id, employee.id)]
    window._fill()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), "CSV"))
    window.export_csv("wishes")
    assert path.exists() and path.read_bytes().startswith(b"\xef\xbb\xbf")
    import csv
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))
    assert len(rows) == 12
    assert rows[0]["Person"] == employee.name
    assert rows[0]["Übergangene Wünsche im Monat"] == "1"


def test_worker_passes_history_and_shows_actual_stage_proofs(window, monkeypatch):
    from dienstplan import planner
    employee = window.data.employees[0]
    history = [WishHistoryEntry(employee.id, {"old"})]
    monkeypatch.setattr(window.store, "wish_history", lambda *args: history)
    def fake_solve(data, wish_history=None, **kwargs):
        assert wish_history == history
        chosen = [Assignment(generate_shifts(data)[0].id, employee.id)]
        return PlanResult("incomplete", chosen, planner.coverage(data, chosen), optimal_stages=[True, False],
                          stage_names=["Besetzung", "Stunden und Fairness"])
    monkeypatch.setattr(planner, "solve", fake_solve)
    loop = QEventLoop(); window.start_planning()
    assert window.tabs.currentWidget() is window.result_page
    window._thread.finished.connect(loop.quit)
    timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(5000)
    loop.exec(); timeout.stop()
    assert window._thread is None
    assert "Besetzung: bewiesen" in window.conflicts.toPlainText()
    assert "Stunden und Fairness: ohne Optimalitätsnachweis" in window.conflicts.toPlainText()
    assert window.plan_button.isEnabled() and window.exception_table.isEnabled()


def test_changed_shift_input_updates_demand_slots_wish_relevance_and_exception_names(window):
    november_fixture(window)
    employee = window.data.employees[0]
    window.data.blockers = [Blocker("early-only", employee.id,
                                   datetime(2026, 11, 16, 10), datetime(2026, 11, 16, 11), 2)]
    window._fill()
    window.shift_table.cellWidget(0, 5).setValue(3)
    assert demand_minutes(window.data) == 1418 * 60
    assert ("2026-11-01/frueh", 2) in window._slot_widgets
    assert "1418,00" in window.conflicts.toPlainText()
    assert window.wishes_table.item(0, 1).text() == "1"
    window.shift_table.cellWidget(0, 1).setTime(QTime(12, 0))
    assert demand_minutes(window.data) == 1238 * 60
    assert window.wishes_table.item(0, 1).text() == "0"
    window.shift_table.cellWidget(0, 0).setText("Tagesdienst")
    assert window.exception_table.horizontalHeaderItem(2).text() == "Tagesdienst"
    assert window.plan_table.item(0, 2).text() == "Tagesdienst"


def test_shift_intermediate_invalid_input_remains_editable_and_removes_old_proof(window):
    original = copy.deepcopy(window.data)
    window._proof_text = "Nachweis je Optimierungsstufe: Besetzung: bewiesen"
    window._last_status = "Nachweislich optimal"
    window._refresh_summaries()
    name = window.shift_table.cellWidget(0, 0)
    name.setText("")
    assert window.data == original and name.isEnabled()
    assert "nicht gültig" in window.result_status.text()
    assert "Nachweis" not in window.conflicts.toPlainText()
    name.setText("Frühdienst neu")
    assert window.data.shift_types[0].name == "Frühdienst neu"
    assert "geänderten Eingaben" in window.result_status.text()
    assert "Nachweislich optimal" not in window.result_status.text()


def test_rule_toggle_revalidates_current_manual_draft_immediately(window):
    for index, shift in enumerate(window.data.shift_types):
        shift.start, shift.end = time(0, index), time(0, index + 1)
    employee = window.data.employees[0]
    shifts = generate_shifts(window.data)
    window.data.assignments = [Assignment(shifts[0].id, employee.id), Assignment(shifts[1].id, employee.id)]
    window._fill()
    assert "Ungültiger Entwurf" not in window.result_status.text()
    enabled, value = window.rule_controls["rest_minutes"]
    value.setValue(1)
    enabled.setChecked(True)
    assert window.data.rules.rest_minutes == 60
    assert "Ungültiger Entwurf" in window.result_status.text()
    assert "Ruhezeit" in window.conflicts.toPlainText()
    enabled.setChecked(False)
    assert window.data.rules.rest_minutes is None
    assert "Ungültiger Entwurf" not in window.result_status.text()


def test_confirmed_wish_overview_keeps_snapshot_when_current_blockers_change(window, monkeypatch):
    complete_short_month(window)
    employee = window.data.employees[0]
    shift = generate_shifts(window.data)[0]
    window.data.blockers = [Blocker("wish", employee.id, shift.start, shift.end, 2)]
    window._fill()
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    window.toggle_confirmed()
    assert window.data.confirmed
    before = [window.wishes_table.item(0, col).text() for col in range(1, 6)]
    assert before == ["1", "0", "1", "0", "1"]
    window.data.blockers = []
    window._refresh_summaries()
    assert [window.wishes_table.item(0, col).text() for col in range(1, 6)] == before
    assert "eingefrorenen bestätigten Monatsstand" in window.conflicts.toPlainText()


def test_input_csv_short_special_actual_solver_exception_save_reload_chain(window, tmp_path, monkeypatch):
    for index, shift in enumerate(window.data.shift_types):
        shift.start, shift.end = time(0, index * 2), time(0, index * 2 + (1 if shift.special else 2))
        shift.pause_minutes = 0
    # Ein kleiner echter CP-SAT-Lauf mit zwölf Personen und kurzer besonderer
    # Schicht. Alle täglichen Termine außer dem Frühdienst am 1. entfallen.
    window.data.exceptions = {f"2026-11-{day:02d}/{shift.id}"
                              for day in range(1, 31) for shift in window.data.shift_types
                              if not shift.special and (day != 1 or shift.id != "frueh")}
    window._fill()
    source = tmp_path / "wuensche.csv"
    source.write_text("datum;von;bis;prioritaet;kommentar\n2026-11-01;;;2;Privat\n", encoding="utf-8-sig")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(source), "CSV"))
    monkeypatch.setattr(QDialog, "exec", lambda dialog: QDialog.DialogCode.Accepted)
    window.import_csv()
    assert len(window.store.get_blockers()) == 1 and not window.test_errors
    window.limit_spin.setValue(2)
    loop = QEventLoop(); window.start_planning()
    assert window._thread is not None and not window.exception_table.isEnabled()
    window._thread.finished.connect(loop.quit)
    timeout = QTimer(); timeout.setSingleShot(True); timeout.timeout.connect(loop.quit); timeout.start(10000)
    loop.exec(); timeout.stop()
    assert window._thread is None and not window.test_errors
    assert len(window.data.assignments) == 10
    assert "0 offene Plätze" in window.result_status.text()
    assert window.save_month()
    loaded = window.store.load_month(2026, 11)
    assert loaded.exceptions == window.data.exceptions
    assert loaded.shift_types[3].paid_minutes == 1
    assert loaded.assignments == window.data.assignments
    reopened = MainWindow(window.store, 2026, 11)
    try:
        assert reopened.plan_table.rowCount() == 5
        assert reopened.wishes_table.item(0, 1).text() == "1"
        assert reopened._exception_widgets["2026-11-16/frueh"].isChecked()
        assert reopened.data.assignments == window.data.assignments
        assert reopened.hours_table.item(0, 6).text() == window.hours_table.item(0, 6).text()
    finally:
        reopened.dirty = False; reopened.close(); reopened.deleteLater()


def test_lower_staff_count_preserves_visible_fixed_excess_until_explicit_release(window):
    shift = generate_shifts(window.data)[0]
    first, second = sorted(window.data.employees[:2], key=lambda employee: employee.id)
    window.data.assignments = [Assignment(shift.id, first.id), Assignment(shift.id, second.id, True)]
    window._fill()
    window.shift_table.cellWidget(0, 5).setValue(1)
    assert len(window.data.assignments) == 2
    assert "Ungültiger Entwurf" in window.result_status.text()
    combo, fixed = window._slot_widgets[(shift.id, 1)]
    assert combo.currentData() == second.id and fixed.isChecked()
    fixed.setChecked(False)
    assert len(window.data.assignments) == 2 and not any(a.fixed for a in window.data.assignments)
    combo.setCurrentIndex(0)
    assert window.data.assignments == [Assignment(shift.id, first.id)]
    assert "Ungültiger Entwurf" not in window.result_status.text()
    assert not window.test_errors
