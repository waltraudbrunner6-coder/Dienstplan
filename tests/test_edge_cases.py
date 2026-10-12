"""Regressionen für persistente Personen und monatsübergreifende Sperren."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

from dienstplan.model import Assignment, Blocker, ValidationError, generate_shifts
from dienstplan.storage import Store
from dienstplan.ui import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, app):
    store = Store(tmp_path / "dienstplan.sqlite")
    instance = MainWindow(store, 2026, 11)
    errors = []
    instance._error = errors.append
    yield instance
    instance.dirty = False
    instance.close()
    app.processEvents()
    store.close()


def blocked(employee_id, day=3, identifier=None):
    return Blocker(identifier or f"block-{day}", employee_id,
                   datetime(2026, 11, day), datetime(2026, 11, day + 1), 1)


def test_first_blocker_change_keeps_person_and_sperre_after_restart(window):
    employee = window.data.employees[0]
    blocker = blocked(employee.id)
    window._replace_blockers(window.collect_data(), employee, [blocker])
    persisted = window.store.load_month(2026, 11)
    assert persisted is not None, "Gespeicherte Sperren benötigen einen erreichbaren Teamstand."
    assert employee.id in {e.id for e in persisted.employees}
    assert persisted.blockers == [blocker]
    reopened = MainWindow(window.store, 2026, 11)
    assert employee.id in {e.id for e in reopened.data.employees}
    assert reopened.data.blockers == [blocker]
    reopened.dirty = False
    reopened.close()


def test_earlier_unsaved_month_keeps_existing_team_ids_and_global_blockers(window):
    employee = window.data.employees[0]
    blocker = Blocker("october", employee.id, datetime(2026, 10, 3), datetime(2026, 10, 4), 1)
    data = window.collect_data()
    window.store.save_month_with_blockers(data, employee.id, [blocker])
    earlier = window._get_month(2026, 10)
    assert {e.id for e in earlier.employees} == {e.id for e in data.employees}
    assert blocker in earlier.blockers
    assert earlier.month == 10
    assert not earlier.assignments


def test_atomic_month_and_blockers_rejects_cap_without_partial_snapshot(window):
    employee = window.data.employees[0]
    data = window.collect_data()
    data.employees[0].name = "Nicht speichern"
    with pytest.raises(ValidationError, match="vier"):
        window.store.save_month_with_blockers(data, employee.id,
                                             [blocked(employee.id, day) for day in range(1, 6)])
    assert window.store.load_month(2026, 11) is None
    assert not window.store.get_blockers()
    original = blocked(employee.id)
    window.store.save_month_with_blockers(window.collect_data(), employee.id, [original])
    data = window.collect_data()
    data.employees[0].name = "Weiterhin nicht speichern"
    with pytest.raises(ValidationError, match="vier"):
        window.store.save_month_with_blockers(data, employee.id,
                                             [blocked(employee.id, day) for day in range(1, 6)])
    assert window.store.load_month(2026, 11).employees[0].name != "Weiterhin nicht speichern"
    assert window.store.get_blockers(employee.id) == [original]


def test_atomic_month_and_blockers_supports_edits_deletions_and_rejects_bad_ids(window):
    employee = window.data.employees[0]
    data = window.collect_data()
    original = blocked(employee.id)
    window.store.save_month_with_blockers(data, employee.id, [original])
    edited = blocked(employee.id, 4, original.id)
    window.store.save_month_with_blockers(data, employee.id, [edited])
    assert window.store.get_blockers(employee.id) == [edited]
    window.store.save_month_with_blockers(data, employee.id, [])
    assert not window.store.get_blockers(employee.id)
    with pytest.raises(ValidationError, match="Person"):
        window.store.save_month_with_blockers(data, "unknown-person", [])
    assert not window.store.get_blockers()


def test_changed_neighbor_blocker_marks_existing_unconfirmed_plan_invalid(window):
    november = window.collect_data()
    employee = november.employees[0]
    overnight = next(s for s in generate_shifts(november)
                     if s.type_id == "nacht" and s.start.day == 30)
    november.assignments = [Assignment(overnight.id, employee.id)]
    window.store.save_month(november)
    december = MainWindow(window.store, 2026, 12)
    blocker = Blocker("december", employee.id, datetime(2026, 12, 1), datetime(2026, 12, 1, 4), 1)
    december._replace_blockers(december.collect_data(), december.data.employees[0], [blocker])
    reopened = MainWindow(window.store, 2026, 11)
    assert "Ungültiger Entwurf" in reopened.result_status.text()
    assert "Priorität-1-Sperre" in reopened.conflicts.toPlainText()
    assert reopened.data.assignments == november.assignments
    reopened.dirty = False
    reopened.close()
    december.dirty = False
    december.close()
