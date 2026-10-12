"""Deutsche Qt-Widgets-Oberfläche; Fachregeln bleiben in den Kernmodulen."""
from __future__ import annotations

import copy
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Event

from PySide6.QtCore import QDate, QObject, QThread, QTime, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDateEdit,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)

from .hours import demand_minutes, fairness_rows, hour_rows, monthly_target
from .model import (
    Assignment, Blocker, Employee, MonthData, Rules, ShiftType, ValidationError,
    decimal_hours, default_shifts, format_hours, generate_shifts, new_id,
    to_minutes, validate_blockers, overlaps, month_days,
)

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
STATUS = {"optimal": "Nachweislich optimal", "feasible": "Gültiges Ergebnis ohne Optimalitätsnachweis",
          "incomplete": "Unvollständiger Entwurf – offene Plätze", "unknown": "Noch kein Ergebnis innerhalb des Zeitlimits",
          "invalid": "Ungültige Eingaben", "cancelled": "Berechnung abgebrochen"}


def _item(text, editable=False):
    item = QTableWidgetItem(str(text))
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    return table


class SolverWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, data, history, boundary, limit, cancel, wish_history=None):
        super().__init__()
        self.data, self.history, self.boundary = data, history, boundary
        self.limit, self.cancel = limit, cancel
        self.wish_history = wish_history or []

    @Slot()
    def run(self):
        try:
            from .planner import solve
            self.finished.emit(solve(self.data, history=self.history, boundary=self.boundary,
                                     time_limit=self.limit, cancel=self.cancel,
                                     wish_history=self.wish_history))
        except Exception as exc:
            self.failed.emit(f"Die Planung konnte nicht ausgeführt werden: {exc}")


class BlockerDialog(QDialog):
    def __init__(self, employee, year, month, blocker=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.blocker_id = blocker.id if blocker else new_id()
        self.setWindowTitle(f"Sperre für {employee.name}")
        layout = QFormLayout(self)
        self.day = QDateEdit(QDate(year, month, 1))
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd.MM.yyyy")
        self.whole = QCheckBox("Ganzer Tag (00:00 bis Folgetag 00:00)")
        self.whole.setChecked(True)
        self.start = QTimeEdit(QTime(8, 0)); self.end = QTimeEdit(QTime(12, 0))
        self.start.setDisplayFormat("HH:mm"); self.end.setDisplayFormat("HH:mm")
        self.end_note = QLabel()
        self.priority = QComboBox()
        self.priority.addItem("1 – verbindlich (max. vier pro Monat)", 1)
        self.priority.addItem("2 – Wunsch, ggf. mit Hinweis übergehbar", 2)
        self.comment = QLineEdit()
        for label, widget in [("Datum", self.day), ("", self.whole), ("Von", self.start),
                              ("Bis", self.end), ("Enddatum", self.end_note),
                              ("Priorität", self.priority), ("Kommentar (optional)", self.comment)]:
            layout.addRow(label, widget)
        if blocker:
            self.day.setDate(QDate(blocker.start.date()))
            self.start.setTime(QTime(blocker.start.hour, blocker.start.minute))
            self.end.setTime(QTime(blocker.end.hour, blocker.end.minute))
            self.whole.setChecked(blocker.start.time() == time() and blocker.end.time() == time()
                                  and blocker.end - blocker.start == timedelta(days=1))
            self.priority.setCurrentIndex(blocker.priority - 1)
            self.comment.setText(blocker.comment)
        self.whole.toggled.connect(self._update)
        self.start.timeChanged.connect(self._update); self.end.timeChanged.connect(self._update)
        self.day.dateChanged.connect(self._update)
        self._update()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _update(self, *_):
        whole = self.whole.isChecked()
        self.start.setEnabled(not whole); self.end.setEnabled(not whole)
        d = self.day.date().toPython()
        overnight = whole or self.end.time() <= self.start.time()
        self.end_note.setText((d + timedelta(days=overnight)).strftime("%d.%m.%Y")
                              + (" (Folgetag)" if overnight else " (gleicher Tag)"))

    def value(self):
        d = self.day.date().toPython()
        if self.whole.isChecked():
            start = datetime.combine(d, time()); end = start + timedelta(days=1)
        else:
            start = datetime.combine(d, self.start.time().toPython())
            end = datetime.combine(d, self.end.time().toPython())
            if end <= start:
                end += timedelta(days=1)
        return Blocker(self.blocker_id, self.employee.id, start, end,
                       self.priority.currentData(), self.comment.text())


class MainWindow(QMainWindow):
    def __init__(self, store, year=None, month=None, data=None):
        super().__init__()
        today = date.today()
        year, month = year or today.year, month or today.month
        self.store = store
        self.data = data or self._get_month(year, month)
        self.dirty = bool(data and store.load_month(data.year, data.month) is None)
        self._desired_explicit_ids = set()
        try:
            self.database_path = store.connection.execute("PRAGMA database_list").fetchone()[2] or "Arbeitsspeicher (nicht dauerhaft)"
        except (AttributeError, IndexError):
            self.database_path = "Lokale SQLite-Datei"
        self._loading = True
        self._thread = None; self._worker = None; self._cancel = None
        self._last_status = "Gespeicherter Plan" if self.data.assignments else "Noch kein Dienstplan"
        self._exception_notice = ""
        self._proof_text = ""
        self.setWindowTitle("Dienstplan – lokale Monatsplanung")
        self.resize(1320, 850)
        central = QWidget(); layout = QVBoxLayout(central); self.setCentralWidget(central)
        top = QHBoxLayout()
        top.addWidget(QLabel("Monat"))
        self.month_combo = QComboBox(); self.month_combo.addItems(MONTHS)
        self.year_spin = QSpinBox(); self.year_spin.setRange(1900, 2200)
        top.addWidget(self.month_combo); top.addWidget(self.year_spin)
        self.save_button = QPushButton("Monat speichern")
        self.confirm_button = QPushButton("Plan bestätigen")
        self.help_button = QPushButton("Anleitung")
        top.addStretch(); top.addWidget(self.save_button); top.addWidget(self.confirm_button); top.addWidget(self.help_button)
        layout.addLayout(top)
        self.banner = QLabel(); self.banner.setWordWrap(True); layout.addWidget(self.banner)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs, 1)
        self._build_team(); self._build_shifts(); self._build_exceptions(); self._build_blockers(); self._build_result()
        footer = QHBoxLayout()
        footer.addWidget(QLabel("Zeitlimit (Sekunden)"))
        self.limit_spin = QSpinBox(); self.limit_spin.setRange(1, 600); self.limit_spin.setValue(20)
        footer.addWidget(self.limit_spin)
        self.plan_button = QPushButton("Dienstplan erstellen")
        self.cancel_button = QPushButton("Berechnung abbrechen"); self.cancel_button.setEnabled(False)
        footer.addWidget(self.plan_button); footer.addWidget(self.cancel_button); footer.addStretch()
        footer.addWidget(QLabel("Alle Daten bleiben lokal. Arbeitszeit = Planprognose."))
        layout.addLayout(footer)
        self.save_button.clicked.connect(self.save_month)
        self.confirm_button.clicked.connect(self.toggle_confirmed)
        self.help_button.clicked.connect(self.show_help)
        self.plan_button.clicked.connect(self.start_planning)
        self.cancel_button.clicked.connect(self.cancel_planning)
        self.month_combo.currentIndexChanged.connect(self.change_month)
        self.year_spin.valueChanged.connect(self.change_month)
        self._fill()
        self.statusBar().showMessage(f"Speicherort: {self.database_path}")

    @staticmethod
    def _new_month(year, month):
        return MonthData(year, month, [Employee(new_id(), f"Person {i + 1}", Decimal(40)) for i in range(12)], default_shifts())

    def _stored_months(self):
        return [tuple(map(int, key.split("-"))) if isinstance(key, str) else tuple(key) for key in self.store.list_months()]

    def _get_month(self, year, month):
        saved = self.store.load_month(year, month)
        if saved is not None: return saved
        known = self._stored_months()
        previous = [key for key in known if key < (year, month)]
        if not known: return self._new_month(year, month)
        source = self.store.load_month(*(max(previous) if previous else min(known)))
        # Stabile Personenkennungen verbinden die Fairnesshistorie über Monate.
        ids = {e.id for e in source.employees}
        employees = copy.deepcopy(source.employees)
        projected = {row.employee_id: row.projected_balance_minutes for row in hour_rows(source)} if previous and source.confirmed else {}
        for employee in employees:
            employee.opening_minutes = projected.get(employee.id, employee.opening_minutes)
            employee.desired_minutes = employee.opening_minutes
        return MonthData(year, month, employees, copy.deepcopy(source.shift_types),
                         [b for b in self.store.get_blockers() if b.employee_id in ids], copy.deepcopy(source.rules))

    def _build_team(self):
        page = QWidget(); layout = QVBoxLayout(page)
        note = QLabel("Wochenstunden × tatsächliche Kalendertage ÷ 7; einmal auf ganze Minuten gerundet. "
                      "Endsaldo = Anfangssaldo lässt bestehende Stunden unverändert. Endsaldo 0 baut sie ab.")
        note.setWordWrap(True); layout.addWidget(note)
        self.team_table = _table(["Name", "Wochenstunden", "Anfangssaldo (h)", "Gewünschter Endsaldo (h)", "Monatssoll (h)"])
        layout.addWidget(self.team_table)
        row = QHBoxLayout(); self.add_employee_button = QPushButton("Person hinzufügen")
        self.remove_employee_button = QPushButton("Gewählte Person entfernen")
        row.addWidget(self.add_employee_button); row.addWidget(self.remove_employee_button); row.addStretch(); layout.addLayout(row)
        self.add_employee_button.clicked.connect(self.add_employee)
        self.remove_employee_button.clicked.connect(self.remove_employee)
        self.team_table.itemChanged.connect(self._team_changed)
        self.tabs.addTab(page, "1 · Team und Stunden")

    def _build_shifts(self):
        page = QWidget(); layout = QVBoxLayout(page)
        note = QLabel("Drei tägliche Dienste und ein besonderer wöchentlicher Dienst mit frei wählbarer Dauer. Ende ≤ Start bedeutet Folgetag "
                      "(gleiche Uhrzeiten = 24 Stunden). Schichten zählen zum Monat ihres Startdatums.")
        note.setWordWrap(True); layout.addWidget(note)
        self.shift_table = _table(["Name", "Start", "Ende", "Enddatum", "Pause (Min.)", "Personenzahl", "Wochentag"])
        self.shift_table.setRowCount(4); layout.addWidget(self.shift_table)
        self.copy_shifts_button = QPushButton("Schichten aus gespeichertem Monat kopieren")
        self.copy_shifts_button.clicked.connect(self.copy_shifts); layout.addWidget(self.copy_shifts_button)
        group = QGroupBox("Optionale Grenzen – ausgeschaltete Regeln werden nicht geprüft")
        form = QFormLayout(group); self.rule_controls = {}
        for key, title, max_value in [("rest_minutes", "Mindestabstand zwischen Schichten (h)", 168),
                                       ("max_day_minutes", "Maximale Tagesstunden", 24),
                                       ("max_week_minutes", "Maximale Wochenstunden (Mo–So)", 168),
                                       ("max_consecutive_days", "Max. aufeinanderfolgende Arbeitstage", 366)]:
            enabled = QCheckBox("Prüfen")
            value = QSpinBox() if key == "max_consecutive_days" else QDoubleSpinBox()
            value.setRange(1 if key == "max_consecutive_days" else 0.02, max_value)
            if isinstance(value, QDoubleSpinBox): value.setDecimals(2)
            value.setValue(5 if key == "max_consecutive_days" else 8)
            value.setEnabled(False)
            row = QWidget(); horizontal = QHBoxLayout(row); horizontal.setContentsMargins(0, 0, 0, 0)
            horizontal.addWidget(enabled); horizontal.addWidget(value); horizontal.addStretch()
            form.addRow(title, row); self.rule_controls[key] = (enabled, value)
            enabled.toggled.connect(value.setEnabled); enabled.toggled.connect(self._settings_changed)
            value.valueChanged.connect(self._settings_changed)
        layout.addWidget(group)
        self.tabs.addTab(page, "2 · Schichten und Grenzen")

    def _build_exceptions(self):
        page = QWidget(); layout = QVBoxLayout(page)
        note = QLabel("Haken gesetzt = dieser tägliche Dienst entfällt am angezeigten Startdatum. "
                      "Ein am Vortag begonnener Nachtdienst bleibt bestehen. Der besondere wöchentliche Dienst bleibt immer unverändert. "
                      "Datumsbezogene Ausnahmen werden nicht in einen neuen Monat übernommen.")
        note.setWordWrap(True); layout.addWidget(note)
        self.exception_table = _table(["Datum", "Wochentag", "Täglicher Dienst 1", "Täglicher Dienst 2", "Täglicher Dienst 3", "Hinweis"])
        self.exception_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.exception_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.exception_table)
        row = QHBoxLayout(); self.exception_buttons = []
        for title, slot in [("Gewählte Tage: alle täglichen Dienste entfallen", self.deactivate_selected_days),
                            ("Gewählte Tage: Ausnahmen aufheben", self.restore_selected_days),
                            ("Alle Monatsausnahmen aufheben", self.restore_all_exceptions)]:
            button = QPushButton(title); button.clicked.connect(slot); row.addWidget(button); self.exception_buttons.append(button)
        row.addStretch(); layout.addLayout(row)
        self.tabs.addTab(page, "3 · Ausnahmetage")

    def _fill_exceptions(self):
        daily = [shift for shift in self.data.shift_types if not shift.special]
        self.exception_table.setHorizontalHeaderLabels(["Datum", "Wochentag", *[s.name for s in daily], "Hinweis"])
        self.exception_table.setRowCount(month_days(self.data.year, self.data.month))
        self._exception_widgets = {}
        self._exception_dates = []
        for row in range(self.exception_table.rowCount()):
            day = date(self.data.year, self.data.month, row + 1)
            self._exception_dates.append(day)
            self.exception_table.setItem(row, 0, _item(day.strftime("%d.%m.%Y")))
            self.exception_table.setItem(row, 1, _item(WEEKDAYS[day.weekday()]))
            inactive = []
            for col, shift in enumerate(daily, 2):
                occurrence_id = f"{day.isoformat()}/{shift.id}"
                checkbox = QCheckBox("entfällt")
                checkbox.setChecked(occurrence_id in self.data.exceptions)
                checkbox.setToolTip(f"{shift.name} am {day:%d.%m.%Y}: Haken = entfällt")
                if checkbox.isChecked(): inactive.append(shift.name)
                self.exception_table.setCellWidget(row, col, checkbox)
                self._exception_widgets[occurrence_id] = checkbox
                checkbox.toggled.connect(lambda checked, key=occurrence_id: self._exception_changed(key, checked))
            self.exception_table.setItem(row, 5, _item("Entfällt: " + ", ".join(inactive) if inactive else "Alle täglichen Dienste aktiv"))

    def _exception_changed(self, occurrence_id, inactive):
        if self._loading: return
        desired = set(self.data.exceptions)
        if inactive: desired.add(occurrence_id)
        else: desired.discard(occurrence_id)
        self.set_exceptions(desired)

    def _selected_exception_days(self):
        return [self._exception_dates[index.row()] for index in self.exception_table.selectionModel().selectedRows()]

    def deactivate_selected_days(self):
        days = self._selected_exception_days()
        if not days:
            self.statusBar().showMessage("Bitte zuerst eine oder mehrere Datumszeilen auswählen.", 5000); return
        desired = set(self.data.exceptions)
        desired.update(f"{day.isoformat()}/{shift.id}" for day in days for shift in self.data.shift_types if not shift.special)
        self.set_exceptions(desired)

    def restore_selected_days(self):
        prefixes = {day.isoformat() + "/" for day in self._selected_exception_days()}
        if not prefixes:
            self.statusBar().showMessage("Bitte zuerst eine oder mehrere Datumszeilen auswählen.", 5000); return
        self.set_exceptions({key for key in self.data.exceptions if not any(key.startswith(prefix) for prefix in prefixes)})

    def restore_all_exceptions(self):
        self.set_exceptions(set())

    def set_exceptions(self, desired):
        """Ändert einen Monatsentwurf atomar; feste Zuteilungen werden ausdrücklich benannt."""
        if self.data.confirmed or self._thread is not None:
            self._loading = True; self._fill_exceptions(); self._loading = False; self._update_enabled()
            self._error("Bestätigte Monate können nicht geändert werden. Bitte zuerst die Bestätigung aufheben." if self.data.confirmed
                        else "Bitte die laufende Berechnung zuerst beenden.")
            return False
        try:
            draft = self.collect_data()
            desired = set(desired)
            if desired == draft.exceptions: return True
            removed_keys = desired - draft.exceptions
            removed = [assignment for assignment in draft.assignments if assignment.shift_id in removed_keys]
            shifts = {shift.id: shift for shift in generate_shifts(draft)}
            names = {employee.id: employee.name for employee in draft.employees}
            details = [f"{shifts[a.shift_id].start:%d.%m.%Y} · {shifts[a.shift_id].name} · {names[a.employee_id]}"
                       + (" (fixiert)" if a.fixed else "") for a in removed]
            if removed:
                text = f"{len(removed)} zugeteilte Einsätze entfallen aus dem bearbeiteten Entwurf:\n" + "\n".join(details)
                text += "\n\nAuch aufgeführte fixierte Zuteilungen werden entfernt, weil der Schichttermin entfällt. Fortfahren?"
                if QMessageBox.question(self, "Zugewiesene Dienste entfallen", text,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    self._loading = True; self._fill_exceptions(); self._loading = False; self._update_enabled(); return False
            draft.exceptions = desired
            draft.assignments = [assignment for assignment in draft.assignments if assignment.shift_id not in removed_keys]
            draft.validate()
            restored = self.data.exceptions - desired
            self.data = draft; self.dirty = True
            self._proof_text = ""
            self._last_status = "Entwurf mit geänderten Ausnahmetagen – vor Bestätigung erneut prüfen"
            self._exception_notice = (f"{len(removed)} Einsätze durch Ausnahmen entfernt: " + "; ".join(details)) if removed else (
                f"{len(restored)} tägliche Schichttermine wieder aktiviert; neue Besetzungsplätze sind offen." if restored
                else f"{len(removed_keys)} tägliche Schichttermine entfallen; Bedarf und faire Sollanteile sind aktualisiert.")
            self._loading = True; self._fill_exceptions(); self._fill_plan(); self._loading = False
            self._refresh_summaries(); self._update_banner(); self._update_enabled()
            self.statusBar().showMessage(self._exception_notice, 10000)
            return True
        except Exception as exc:
            self._loading = True; self._fill_exceptions(); self._loading = False; self._update_enabled()
            self._error(f"Die Ausnahmen wurden nicht geändert. {exc}"); return False

    def _build_blockers(self):
        page = QWidget(); layout = QVBoxLayout(page)
        note = QLabel("Priorität 1: verbindlich, maximal vier eindeutige Blocker je Person und Monat. "
                      "Priorität 2: Wunsch. Angezeigt werden alle gespeicherten Sperren der gewählten Person, auch in Randmonaten. "
                      "Sperrenänderungen speichern auch die aktuellen Monatseingaben und den aktuellen Plan.")
        note.setWordWrap(True); layout.addWidget(note)
        self.blocker_person = QComboBox(); layout.addWidget(self.blocker_person)
        self.blocker_table = _table(["Beginn", "Ende", "Priorität", "Kommentar"])
        self.blocker_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.blocker_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.blocker_table)
        row = QHBoxLayout(); self.blocker_buttons = []
        for title, slot in [("CSV importieren …", self.import_csv), ("Sperre hinzufügen", self.add_blocker),
                            ("Sperre bearbeiten", self.edit_blocker), ("Sperre löschen", self.delete_blocker)]:
            button = QPushButton(title); button.clicked.connect(slot); row.addWidget(button); self.blocker_buttons.append(button)
        row.addStretch(); layout.addLayout(row)
        self.blocker_person.currentIndexChanged.connect(self._fill_blockers)
        self.tabs.addTab(page, "4 · Sperren und CSV")

    def _build_result(self):
        page = QWidget(); layout = QVBoxLayout(page)
        self.result_status = QLabel(); self.result_status.setWordWrap(True); layout.addWidget(self.result_status)
        self.summary_tabs = QTabWidget(); layout.addWidget(self.summary_tabs, 1)
        self.plan_table = _table(["Datum", "Wochentag", "Schicht", "Zeitraum / bezahlt", "Besetzungsplätze / fixieren", "Hinweis"])
        self.summary_tabs.addTab(self.plan_table, "Monatsdienstplan")
        self.hours_table = _table(["Person", "Woche (h)", "Monatssoll", "Anfangssaldo", "Gew. Endsaldo", "Planungsziel",
                                   "Eingeplant", "Neue +/-", "Endsaldo-Prognose", "Zielabweichung"])
        self.summary_tabs.addTab(self.hours_table, "Stundenprognose (alle Werte in h)")
        self.fairness_table = _table(["Person", "Schicht", "Anzahl", "Stunden", "Fairer Anteil besetzter Einsätze", "Abweichung Anzahl",
                                      "Fairer Anteil (h)", "Abweichung (h)", "Sonder-Historie Anzahl", "Hist. Sollanteil Anzahl",
                                      "Sonder-Historie (h)", "Hist. Sollanteil (h)", "Sonder-Abweichung Anzahl gesamt", "Sonder-Abweichung (h) gesamt"])
        self.summary_tabs.addTab(self.fairness_table, "Schichtverteilung")
        wishes_page = QWidget(); wishes_layout = QVBoxLayout(wishes_page)
        wishes_note = QLabel("Nur eindeutige Priorität-2-Wünsche mit Überschneidung zu aktiven Diensten zählen. "
                             "Nach möglichst vollständiger Besetzung und minimaler Gesamtzahl an Übergehungen werden zuerst Personen mit weniger Wünschen geschützt; "
                             "innerhalb gleicher Wunschanzahl wird die kumulierte Belastung ausgeglichen. "
                             "Besetzung und verbindliche Regeln können Wünsche einschränken; ohne Optimalitätsnachweis bleibt Verbesserung möglich.")
        wishes_note.setWordWrap(True); wishes_layout.addWidget(wishes_note)
        self.wishes_table = _table(["Person", "Relevante Wünsche", "Erfüllt (Entwurf)", "Übergangen (Entwurf)",
                                    "Historische Übergehungen", "Kumulierte Belastung", "Fehlende Althistorie"])
        wishes_layout.addWidget(self.wishes_table)
        self.summary_tabs.addTab(wishes_page, "Freiwünsche")
        self.conflicts = QTextEdit(); self.conflicts.setReadOnly(True); self.conflicts.setMaximumHeight(155)
        layout.addWidget(self.conflicts)
        buttons = QHBoxLayout(); self.export_buttons = []
        for title, kind in [("Dienstplan als CSV …", "plan"), ("Stunden als CSV …", "hours"), ("Verteilung als CSV …", "fairness"), ("Freiwünsche als CSV …", "wishes")]:
            button = QPushButton(title); button.clicked.connect(lambda checked=False, k=kind: self.export_csv(k))
            buttons.addWidget(button); self.export_buttons.append(button)
        buttons.addStretch(); layout.addLayout(buttons)
        self.result_page = page
        self.tabs.addTab(page, "5 · Ergebnis und Export")

    def _fill(self):
        self._loading = True
        self.year_spin.setValue(self.data.year); self.month_combo.setCurrentIndex(self.data.month - 1)
        self.team_table.setRowCount(len(self.data.employees))
        for row, e in enumerate(self.data.employees):
            for col, value in enumerate([e.name, str(e.weekly_hours).replace(".", ","), format_hours(e.opening_minutes),
                                         format_hours(e.desired_minutes), format_hours(monthly_target(e, self.data.year, self.data.month))]):
                cell = _item(value, col < 4)
                if col == 0: cell.setData(Qt.ItemDataRole.UserRole, e.id)
                if col == 2: cell.setData(Qt.ItemDataRole.UserRole, cell.text())
                if col == 3: cell.setData(Qt.ItemDataRole.UserRole, e.id not in self._desired_explicit_ids and e.desired_minutes == e.opening_minutes)
                self.team_table.setItem(row, col, cell)
        ordered_shifts = [s for s in self.data.shift_types if not s.special] + [s for s in self.data.shift_types if s.special]
        for row, shift in enumerate(ordered_shifts):
            name = QLineEdit(shift.name); name.setProperty("shift_id", shift.id)
            start = QTimeEdit(QTime(shift.start)); end = QTimeEdit(QTime(shift.end))
            start.setDisplayFormat("HH:mm"); end.setDisplayFormat("HH:mm")
            next_day = QLabel(); pause = QSpinBox(); pause.setRange(0, 1439); pause.setValue(shift.pause_minutes)
            count = QSpinBox(); count.setRange(1, 100); count.setValue(shift.staff_required)
            weekday = QComboBox()
            if shift.special:
                weekday.addItems(WEEKDAYS); weekday.setCurrentIndex(shift.weekday)
            else: weekday.addItem("Täglich, auch Wochenende"); weekday.setEnabled(False)
            for col, widget in enumerate([name, start, end, next_day, pause, count, weekday]):
                self.shift_table.setCellWidget(row, col, widget)
            name.textChanged.connect(self._settings_changed); pause.valueChanged.connect(self._settings_changed); count.valueChanged.connect(self._settings_changed)
            weekday.currentIndexChanged.connect(self._settings_changed)
            start.timeChanged.connect(lambda *_, r=row: self._shift_time_changed(r))
            end.timeChanged.connect(lambda *_, r=row: self._shift_time_changed(r))
            self._shift_time_changed(row)
        for key, (enabled, value) in self.rule_controls.items():
            raw = getattr(self.data.rules, key); enabled.setChecked(raw is not None)
            if raw is not None: value.setValue(raw if key == "max_consecutive_days" else raw / 60)
        self._fill_people(); self._fill_blockers(); self._fill_exceptions(); self._fill_plan(); self._refresh_summaries()
        self._loading = False; self._update_enabled(); self._update_banner()

    def _fill_people(self):
        selected = self.blocker_person.currentData()
        self.blocker_person.blockSignals(True); self.blocker_person.clear()
        for e in self.data.employees: self.blocker_person.addItem(e.name, e.id)
        index = self.blocker_person.findData(selected)
        if index >= 0: self.blocker_person.setCurrentIndex(index)
        self.blocker_person.blockSignals(False)

    def _fill_blockers(self, *_):
        employee_id = self.blocker_person.currentData()
        self._visible_blockers = sorted([b for b in self.data.blockers if b.employee_id == employee_id], key=lambda b: (b.start, b.priority))
        self.blocker_table.setRowCount(len(self._visible_blockers))
        for row, b in enumerate(self._visible_blockers):
            values = [b.start.strftime("%d.%m.%Y %H:%M"), b.end.strftime("%d.%m.%Y %H:%M"),
                      "1 – verbindlich" if b.priority == 1 else "2 – Wunsch", b.comment]
            for col, value in enumerate(values): self.blocker_table.setItem(row, col, _item(value))

    def _shift_time_changed(self, row):
        start = self.shift_table.cellWidget(row, 1).time(); end = self.shift_table.cellWidget(row, 2).time()
        self.shift_table.cellWidget(row, 3).setText("Folgetag (+1 Tag)" if end <= start else "Gleicher Tag")
        self._settings_changed()

    def _team_changed(self, item):
        if self._loading: return
        if item.column() == 2:
            desired = self.team_table.item(item.row(), 3)
            if desired.data(Qt.ItemDataRole.UserRole):
                self.team_table.blockSignals(True); desired.setText(item.text()); self.team_table.blockSignals(False)
            item.setData(Qt.ItemDataRole.UserRole, item.text())
        elif item.column() == 3:
            self._desired_explicit_ids.add(self.team_table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole))
            item.setData(Qt.ItemDataRole.UserRole, False)
        self._changed()
        try:
            draft = self.collect_data(validate=False)
            self.team_table.blockSignals(True)
            for row, e in enumerate(draft.employees):
                self.team_table.item(row, 4).setText(format_hours(monthly_target(e, draft.year, draft.month)))
            self.team_table.blockSignals(False)
            self._refresh_summaries(draft)
        except (ValueError, ArithmeticError):
            self.team_table.blockSignals(False)

    def _changed(self, *_):
        if not self._loading:
            self.dirty = True
            self._proof_text = ""
            self._last_status = "Entwurf mit geänderten Eingaben – erneut prüfen"
            self._update_banner()

    def _settings_changed(self, *_):
        """Gültige Schichteingaben aktualisieren Bedarf, Wunschrelevanz und Plätze sofort."""
        if self._loading: return
        self._changed()
        try:
            draft = self.collect_data()
        except (ValueError, ArithmeticError) as exc:
            # Ein vorübergehend leerer Name oder eine zu lange Pause darf weiter
            # bearbeitet werden. Speichern/Planen prüft die Eingaben erneut.
            self.result_status.setText("Eingaben noch nicht gültig – bitte korrigieren")
            self.conflicts.setPlainText(f"Bitte die Eingaben korrigieren: {exc}")
            return
        self.data = draft
        self._loading = True
        try:
            self._fill_exceptions(); self._fill_plan(); self._refresh_summaries()
        finally:
            self._loading = False
        self._update_enabled()

    def _update_banner(self):
        state = "Bestätigter Monat – zum Bearbeiten zuerst Bestätigung aufheben." if self.data.confirmed else "Entwurf"
        self.banner.setText(f"{MONTHS[self.data.month - 1]} {self.data.year} · {state}"
                            + (" · Ungespeicherte Änderungen" if self.dirty else "")
                            + "\nSoll = Wochenstunden × Kalendertage ÷ 7. Geleistete Arbeitszeit wird nicht erfasst.")

    def _update_enabled(self):
        editing = not self.data.confirmed and self._thread is None
        self.team_table.setEnabled(editing); self.shift_table.setEnabled(editing)
        self.exception_table.setEnabled(editing)
        for button in [self.add_employee_button, self.remove_employee_button, self.copy_shifts_button, *self.blocker_buttons, *self.exception_buttons]: button.setEnabled(editing)
        for enabled, value in self.rule_controls.values():
            enabled.setEnabled(editing); value.setEnabled(editing and enabled.isChecked())
        for combo, fixed in getattr(self, "_slot_widgets", {}).values():
            combo.setEnabled(editing); fixed.setEnabled(editing and bool(combo.currentData()))
        self.plan_button.setEnabled(editing); self.save_button.setEnabled(editing)
        self.confirm_button.setEnabled(self._thread is None and bool(self.data.assignments))
        self.confirm_button.setText("Bestätigung aufheben" if self.data.confirmed else "Plan bestätigen")
        self.month_combo.setEnabled(self._thread is None); self.year_spin.setEnabled(self._thread is None)

    def collect_data(self, validate=True):
        draft = copy.deepcopy(self.data); draft.employees = []
        for row in range(self.team_table.rowCount()):
            cells = [self.team_table.item(row, col) for col in range(4)]
            draft.employees.append(Employee(cells[0].data(Qt.ItemDataRole.UserRole), cells[0].text().strip(),
                                            decimal_hours(cells[1].text()), to_minutes(cells[2].text()), to_minutes(cells[3].text())))
        draft.shift_types = []
        for row in range(4):
            name = self.shift_table.cellWidget(row, 0)
            draft.shift_types.append(ShiftType(name.property("shift_id"), name.text().strip(),
                                              self.shift_table.cellWidget(row, 1).time().toPython(),
                                              self.shift_table.cellWidget(row, 2).time().toPython(),
                                              self.shift_table.cellWidget(row, 4).value(), self.shift_table.cellWidget(row, 5).value(),
                                              self.shift_table.cellWidget(row, 6).currentIndex() if row == 3 else None))
        rules = {}
        for key, (enabled, value) in self.rule_controls.items():
            rules[key] = (value.value() if key == "max_consecutive_days" else to_minutes(value.value())) if enabled.isChecked() else None
        draft.rules = Rules(**rules)
        if validate: draft.validate()
        return draft

    def _validate_plan(self, data, assignments=None):
        from .planner import validate_assignments
        errors = validate_assignments(data, data.assignments if assignments is None else assignments,
                                      boundary=self.store.boundary(data.year, data.month))
        if errors: raise ValidationError("\n".join(errors))

    def _error(self, message):
        QMessageBox.warning(self, "Eingabe oder Aktion nicht möglich", str(message))

    def add_employee(self):
        try:
            self.data = self.collect_data(False)
            self.data.employees.append(Employee(new_id(), f"Person {len(self.data.employees) + 1}", Decimal(40)))
            self._changed(); self._fill()
        except ValueError as exc: self._error(exc)

    def remove_employee(self):
        row = self.team_table.currentRow()
        if row < 0: return
        try:
            draft = self.collect_data(False); employee = draft.employees[row]
            if any(a.employee_id == employee.id for a in draft.assignments):
                raise ValidationError("Bitte zuerst die Zuteilungen dieser Person im Dienstplan entfernen.")
            del draft.employees[row]
            self.data = draft; self._changed(); self._fill()
        except ValueError as exc: self._error(exc)

    def save_month(self):
        try:
            draft = self.collect_data(); self._validate_plan(draft)
            self.store.save_month(draft); self.data = draft; self.dirty = False
            self._fill(); self.statusBar().showMessage("Monat lokal gespeichert.", 5000)
            return True
        except Exception as exc:
            self._error(f"Der Monat wurde nicht gespeichert. {exc}"); return False

    def _can_leave(self):
        if not self.dirty: return True
        box = QMessageBox(self); box.setWindowTitle("Ungespeicherte Änderungen")
        box.setText("Die Änderungen dieses Monats wurden noch nicht gespeichert.")
        save = box.addButton("Speichern", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Verwerfen", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole); box.exec()
        if box.clickedButton() is save: return self.save_month()
        return box.clickedButton() is discard

    def change_month(self, *_):
        if self._loading: return
        year, month = self.year_spin.value(), self.month_combo.currentIndex() + 1
        if (year, month) == (self.data.year, self.data.month): return
        if not self._can_leave():
            self._loading = True; self.year_spin.setValue(self.data.year); self.month_combo.setCurrentIndex(self.data.month - 1); self._loading = False
            return
        try:
            self.data = self._get_month(year, month)
            self.dirty = False; self._last_status = "Gespeicherter Plan" if self.data.assignments else "Noch kein Dienstplan"
            self._exception_notice = ""; self._proof_text = ""
            self._fill()
        except Exception as exc: self._error(f"Der Monat konnte nicht geladen werden. {exc}")

    def copy_shifts(self):
        if self.data.confirmed:
            self._error("Bestätigte Monate können nicht geändert werden. Bitte zuerst die Bestätigung aufheben."); return
        months = [m for m in self._stored_months() if m != (self.data.year, self.data.month)]
        if not months: self._error("Es ist noch kein anderer Monat gespeichert."); return
        labels = [f"{MONTHS[m - 1]} {y}" for y, m in months]
        label, accepted = QInputDialog.getItem(self, "Schichteinstellungen kopieren", "Quellmonat", labels, 0, False)
        if not accepted: return
        try:
            draft = self.collect_data(False); source = self.store.load_month(*months[labels.index(label)])
            if draft.assignments and QMessageBox.question(self, "Vorhandene Zuteilungen", "Beim Kopieren werden die Zuteilungen im aktuellen Entwurf entfernt. Fortfahren?",
                                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            draft.shift_types = copy.deepcopy(source.shift_types); draft.assignments = []
            # Nur Einstellungen übernehmen. Der Zielmonat behält seine eigenen
            # Datums-Ausnahmen, soweit die Schichtkennung in der Vorlage existiert.
            daily_ids = {shift.id for shift in draft.shift_types if not shift.special}
            draft.exceptions = {key for key in draft.exceptions if key.split("/", 1)[1] in daily_ids}
            self.data = draft; self._changed(); self._fill()
        except Exception as exc: self._error(f"Die Einstellungen konnten nicht kopiert werden. {exc}")

    def _selected_employee(self):
        draft = self.collect_data()
        employee_id = self.blocker_person.currentData()
        employee = next((e for e in draft.employees if e.id == employee_id), None)
        if employee is None: raise ValidationError("Bitte zuerst eine Person wählen.")
        return draft, employee

    def _replace_blockers(self, draft, employee, blockers):
        unique = validate_blockers(blockers)
        draft.blockers = [b for b in draft.blockers if b.employee_id != employee.id] + unique
        try:
            self._validate_plan(draft)
        except ValidationError as exc:
            raise ValidationError(f"Die neuen Sperren würden bestehende Zuteilungen ungültig machen. Bitte diese Zuteilungen zuerst im Dienstplan entfernen oder freigeben. {exc}") from exc
        # Personenkennungen und genaue Sperrenliste müssen gemeinsam erreichbar
        # bleiben, auch beim allerersten Import und anschließendem Neustart.
        self.store.save_month_with_blockers(draft, employee.id, unique)
        self.data = draft; self._changed(); self.dirty = False; self._fill()
        self.statusBar().showMessage("Sperren und aktuelle Monatseingaben gemeinsam lokal gespeichert.", 6000)

    def add_blocker(self):
        self._edit_blocker(None)

    def edit_blocker(self):
        row = self.blocker_table.currentRow()
        if row >= 0: self._edit_blocker(self._visible_blockers[row])

    def _edit_blocker(self, old):
        try:
            draft, employee = self._selected_employee()
            dialog = BlockerDialog(employee, draft.year, draft.month, old, self)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            mine = [b for b in draft.blockers if b.employee_id == employee.id and (old is None or b.id != old.id)]
            self._replace_blockers(draft, employee, mine + [dialog.value()])
        except Exception as exc: self._error(f"Die Sperre wurde nicht gespeichert. {exc}")

    def delete_blocker(self):
        row = self.blocker_table.currentRow()
        if row < 0: return
        try:
            draft, employee = self._selected_employee(); old = self._visible_blockers[row]
            if QMessageBox.question(self, "Sperre löschen", "Gewählte Sperre dauerhaft löschen?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            self._replace_blockers(draft, employee, [b for b in draft.blockers if b.employee_id == employee.id and b.id != old.id])
        except Exception as exc: self._error(f"Die Sperre wurde nicht gelöscht. {exc}")

    def import_csv(self):
        from .csvio import preview_csv
        path, _ = QFileDialog.getOpenFileName(self, "CSV-Sperren importieren", "", "CSV-Dateien (*.csv);;Alle Dateien (*)")
        if not path: return
        try:
            draft, employee = self._selected_employee(); preview = preview_csv(path, employee.id)
            dialog = QDialog(self); dialog.setWindowTitle(f"Importvorschau für {employee.name}"); dialog.resize(760, 500)
            layout = QVBoxLayout(dialog); info = QLabel("Noch keine Daten geändert. Nur ein vollständig fehlerfreier Import kann übernommen werden. "
                                                      "Die Übernahme speichert auch die aktuellen Monatseingaben und den aktuellen Plan.")
            info.setWordWrap(True); layout.addWidget(info)
            text = QTextEdit(); text.setReadOnly(True)
            lines = [f"{b.start:%d.%m.%Y %H:%M} bis {b.end:%d.%m.%Y %H:%M} · Priorität {b.priority} · {b.comment}" for b in preview.blockers]
            if preview.errors: lines = [str(error) for error in preview.errors] + [""] + lines
            text.setPlainText("\n".join(lines) or "Die Datei enthält keine Sperren."); layout.addWidget(text)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            buttons.button(QDialogButtonBox.StandardButton.Save).setText("Import übernehmen")
            buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(preview.valid)
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
            buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
            if dialog.exec() != QDialog.DialogCode.Accepted: return
            existing = [b for b in draft.blockers if b.employee_id == employee.id]
            self._replace_blockers(draft, employee, existing + preview.blockers)
            self.statusBar().showMessage("CSV-Sperren gespeichert; identische Duplikate wurden zusammengefasst.", 6000)
        except Exception as exc: self._error(f"Der Import hat keine Daten verändert. {exc}")

    def _fill_plan(self):
        self._slot_widgets = {}; self._shifts = generate_shifts(self.data)
        self.plan_table.setRowCount(len(self._shifts))
        for row, shift in enumerate(self._shifts):
            mine = sorted([a for a in self.data.assignments if a.shift_id == shift.id], key=lambda a: a.employee_id)
            values = [shift.start.strftime("%d.%m.%Y"), WEEKDAYS[shift.start.weekday()], shift.name,
                      f"{shift.start:%H:%M}–{shift.end:%H:%M}" + (" (+1 Tag)" if shift.end.date() > shift.start.date() else "") + f" / {format_hours(shift.paid_minutes)} h"]
            for col, value in enumerate(values): self.plan_table.setItem(row, col, _item(value))
            widget = QWidget(); slots = QVBoxLayout(widget); slots.setContentsMargins(2, 2, 2, 2)
            # Nach einer kleineren Besetzungszahl bleiben überzählige Einsätze
            # erreichbar, insbesondere zum ausdrücklichen Freigeben Fixierter.
            visible_slots = max(shift.staff_required, len(mine))
            for index in range(visible_slots):
                line = QHBoxLayout()
                line.addWidget(QLabel(f"Platz {index + 1}" + (" (überzählig)" if index >= shift.staff_required else "")))
                combo = QComboBox(); combo.addItem("— offen —", None)
                for e in self.data.employees: combo.addItem(e.name, e.id)
                fixed = QCheckBox("Fixiert")
                if index < len(mine):
                    combo.setCurrentIndex(combo.findData(mine[index].employee_id)); fixed.setChecked(mine[index].fixed)
                fixed.setEnabled(bool(combo.currentData()))
                line.addWidget(combo, 1); line.addWidget(fixed); slots.addLayout(line)
                self._slot_widgets[(shift.id, index)] = (combo, fixed)
                combo.currentIndexChanged.connect(lambda *_, s=shift.id, i=index: self._manual_changed(s, i))
                fixed.toggled.connect(lambda *_, s=shift.id, i=index: self._manual_changed(s, i))
            self.plan_table.setCellWidget(row, 4, widget)
            self.plan_table.setRowHeight(row, max(42, visible_slots * 36))
        self._update_enabled()

    def _manual_changed(self, shift_id, slot):
        if self._loading: return
        if self.data.confirmed:
            self._error("Bestätigte Monate können nicht geändert werden. Bitte zuerst die Bestätigung aufheben.")
            self._loading = True; self._fill_plan(); self._loading = False; return
        try:
            draft = self.collect_data()
            proposed = [Assignment(s, c.currentData(), f.isChecked()) for (s, _), (c, f) in self._slot_widgets.items() if c.currentData()]
            # Fixierte Zuteilungen werden vor der Änderung ausdrücklich freigegeben.
            old_fixed = {(a.shift_id, a.employee_id) for a in self.data.assignments if a.fixed}
            changed_combo, changed_fixed = self._slot_widgets[(shift_id, slot)]
            if any(s == shift_id and (s, e) not in {(a.shift_id, a.employee_id) for a in proposed} for s, e in old_fixed):
                raise ValidationError("Diese Zuteilung ist fixiert. Bitte zuerst den Haken „Fixiert“ entfernen.")
            old_pairs = {(a.shift_id, a.employee_id) for a in self.data.assignments}
            new_pairs = {(a.shift_id, a.employee_id) for a in proposed}
            new_fixed = {(a.shift_id, a.employee_id) for a in proposed if a.fixed}
            release_only = (old_pairs == new_pairs and len(proposed) == len(self.data.assignments)
                            and new_fixed < old_fixed)
            try:
                self._validate_plan(draft, proposed)
            except ValidationError:
                # Die Freigabe ändert keine Arbeitszeit/Zuteilung und muss auch
                # nach geänderten Grenzen möglich sein, damit erneut geplant
                # werden kann. Bestehende Konflikte bleiben deutlich sichtbar.
                if not release_only: raise
            draft.assignments = proposed; self.data = draft; self.dirty = True
            changed_fixed.setEnabled(bool(changed_combo.currentData()))
            if not changed_combo.currentData(): changed_fixed.setChecked(False)
            self._last_status = "Manuell bearbeiteter gültiger Entwurf"
            self._proof_text = ""
            self._refresh_summaries(); self._update_banner(); self._update_enabled()
        except Exception as exc:
            self._error(f"Die Änderung wurde abgelehnt. {exc}")
            self._loading = True; self._fill_plan(); self._loading = False

    def _refresh_summaries(self, data=None):
        from .planner import preference_violations, validate_assignments
        from .wishes import display_wishes, wish_rows
        data = data or self.data
        history = self.store.history(data.year, data.month)
        wish_history = self.store.wish_history(data.year, data.month)
        historical = {entry.employee_id: entry for entry in history}
        special_types = {shift.id for shift in data.shift_types if shift.special}
        rows = hour_rows(data); self.hours_table.setRowCount(len(rows))
        for row, h in enumerate(rows):
            values = [h.name, str(h.weekly_hours).replace(".", ",")] + [format_hours(getattr(h, key)) for key in
                       ["target_minutes", "opening_minutes", "desired_minutes", "planning_minutes", "planned_minutes",
                        "new_balance_minutes", "projected_balance_minutes", "deviation_minutes"]]
            for col, value in enumerate(values): self.hours_table.setItem(row, col, _item(value))
        fair = fairness_rows(data, history=history); self.fairness_table.setRowCount(len(fair))
        for row, h in enumerate(fair):
            past = historical.get(h["employee_id"]) if h["type_id"] in special_types else None
            past_minutes = past.special_minutes if past else 0
            past_expected = float(past.expected_minutes) if past else 0
            cumulative_minutes = past_minutes - past_expected + h["minute_deviation"] if h["type_id"] in special_types else 0
            number = lambda value, signed=False: (f"{value:+.2f}" if signed else f"{value:.2f}").replace(".", ",")
            values = [h["name"], h["shift_name"], h["count"], format_hours(h["minutes"]), number(h["expected_count"]),
                      number(h["count_deviation"], True), number(h["expected_minutes"] / 60), number(h["minute_deviation"] / 60, True),
                      h["historical_count"], number(h["historical_expected"]), format_hours(past_minutes), number(past_expected / 60),
                      number(h["cumulative_deviation"], True), number(cumulative_minutes / 60, True)]
            for col, value in enumerate(values): self.fairness_table.setItem(row, col, _item(value))
        wishes = wish_rows(data, wish_history=wish_history)
        self.wishes_table.setRowCount(len(wishes))
        missing_months = set()
        snapshot_missing = False
        for row, wish in enumerate(wishes):
            missing = wish["missing_months"]
            missing_months.update(missing)
            snapshot_missing = snapshot_missing or wish.get("snapshot_missing", False)
            history_note = ", ".join(missing) if missing else "keine"
            if wish.get("snapshot_missing", False): history_note += "; damals nicht erfasst: aktuelle Blockerzählung"
            values = [wish["name"], wish["relevant"], wish["fulfilled"], wish["violated"], wish["historical"],
                      wish["cumulative"], history_note]
            for col, value in enumerate(values): self.wishes_table.setItem(row, col, _item(value))
        needed = demand_minutes(data); target = sum(h.planning_minutes for h in rows)
        violations = preference_violations(data, data.assignments)
        displayed_wishes = display_wishes(data)
        hard_errors = validate_assignments(data, data.assignments, boundary=self.store.boundary(data.year, data.month))
        assigned_counts = {}
        for a in data.assignments: assigned_counts[a.shift_id] = assigned_counts.get(a.shift_id, 0) + 1
        open_n = 0
        for row, shift in enumerate(getattr(self, "_shifts", [])):
            count = max(0, shift.staff_required - assigned_counts.get(shift.id, 0)); open_n += count
            hints = ([f"⚠ {count} Platz/Plätze offen"] if count else ["✓ Besetzt"])
            assigned = {a.employee_id for a in data.assignments if a.shift_id == shift.id}
            if any(b.employee_id in assigned and overlaps(shift.start, shift.end, b.start, b.end) for b in displayed_wishes):
                hints.append("⚠ Wunsch übergangen")
            self.plan_table.setItem(row, 5, _item(" · ".join(hints)))
        label = "⚠ Ungültiger Entwurf – verbindliche Konflikte; bitte erneut planen" if hard_errors else self._last_status
        self.result_status.setText(f"{label} · {open_n} offene Plätze · {sum(w['violated'] for w in wishes)} übergangene Priorität-2-Wünsche")
        balance = needed - target
        lines = [f"Bedarf einschließlich Personenzahl: {format_hours(needed)} Mitarbeiterstunden. Summe Planungsziele: {format_hours(target)} h."]
        if balance > 0: lines.append(f"Der Bedarf übersteigt die Planungsziele um {format_hours(balance)} h. Bei vollständiger Besetzung entstehen gegenüber den individuellen Zielen Mehrstunden.")
        elif balance < 0: lines.append(f"Die Planungsziele übersteigen den Bedarf um {format_hours(-balance)} h. Die Ziele können allein mit diesen Schichten nicht vollständig erreicht werden.")
        else: lines.append("Bedarf und Ziele sind rechnerisch gleich; Sperren und Grenzen können die Besetzung trotzdem einschränken.")
        untested = [title for key, title in [("rest_minutes", "Ruhezeit"), ("max_day_minutes", "Tagesstunden"), ("max_week_minutes", "Wochenstunden"), ("max_consecutive_days", "Arbeitstage in Folge")] if getattr(data.rules, key) is None]
        lines.append("Nicht geprüft: " + (", ".join(untested) if untested else "keine der angebotenen Grenzen"))
        if data.exceptions:
            lines.append(f"{len(data.exceptions)} tägliche Schichttermine entfallen gemäß Ausnahmetagen; sie zählen nicht zu Bedarf und offenen Plätzen.")
        if self._exception_notice: lines.append(self._exception_notice)
        if missing_months:
            lines.append("Fehlende Freiwunsch-Althistorie in bestätigten Monaten: " + ", ".join(sorted(missing_months))
                         + ". Die kumulierte Belastung enthält ausschließlich bekannte eindeutige Übergehungen.")
        if snapshot_missing:
            lines.append("Freiwünsche dieses bestätigten Altmonats wurden damals nicht eingefroren. Die angezeigten aktuellen Blockerzahlen sind kein historischer Nachweis.")
        elif data.confirmed and data.wish_snapshot is not None:
            lines.append("Die Freiwunschübersicht verwendet den eingefrorenen bestätigten Monatsstand; spätere Sperrenänderungen verändern diese Zahlen nicht.")
        if self._proof_text: lines.append(self._proof_text)
        lines.append("Freiwünsche: gleiche Gesamtzahl → weniger relevante Wünsche zuerst schützen → Belastung innerhalb gleicher Wunschanzahl ausgleichen. "
                     "Verbindliche Regeln und Besetzung gelten vorrangig. Ohne vollständigen Optimalitätsnachweis ist weitere Verbesserung möglich.")
        if hard_errors: lines += ["Verbindliche Konflikte im angezeigten Entwurf:"] + hard_errors
        if violations: lines += ["Übergangene Wünsche:"] + [str(v) for v in violations]
        self.conflicts.setPlainText("\n".join(lines))

    def start_planning(self):
        if self._thread is not None: return
        if self.data.confirmed:
            self._error("Bestätigte Monate können nicht neu geplant werden. Bitte zuerst die Bestätigung aufheben."); return
        try:
            draft = self.collect_data(); self._validate_plan(draft, [a for a in draft.assignments if a.fixed])
            needed = demand_minutes(draft); target = sum(r.planning_minutes for r in hour_rows(draft))
            self.data = draft; self._fill_plan(); self._refresh_summaries()
            self._last_status = f"Berechnung läuft (Bedarf {format_hours(needed)} h, Planungsziele {format_hours(target)} h) …"
            self._proof_text = ""
            self.result_status.setText(self._last_status); self.tabs.setCurrentWidget(self.result_page)
            history = self.store.history(draft.year, draft.month)
            wish_history = self.store.wish_history(draft.year, draft.month)
            boundary = self.store.boundary(draft.year, draft.month)
            self._cancel = Event(); self._thread = QThread(self)
            self._worker = SolverWorker(copy.deepcopy(draft), history, boundary, self.limit_spin.value(), self._cancel, wish_history)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._receive_result)
            self._worker.failed.connect(self._solver_error)
            self._worker.finished.connect(self._thread.quit); self._worker.failed.connect(self._thread.quit)
            self._thread.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._solver_done)
            self.cancel_button.setEnabled(True); self._update_enabled(); self._thread.start()
        except Exception as exc: self._error(f"Die Planung konnte nicht gestartet werden. {exc}")

    def cancel_planning(self):
        if self._cancel: self._cancel.set()
        self.cancel_button.setEnabled(False); self.result_status.setText("Abbruch angefordert – letzter gültiger Entwurf wird geprüft …")

    @Slot(object)
    def _receive_result(self, result):
        label = STATUS.get(result.status, "Planung beendet")
        if self.data.confirmed:
            self._error("Ein berechneter Entwurf darf keinen bestätigten Monatsstand überschreiben."); return
        names = getattr(result, "stage_names", [])
        proofs = result.optimal_stages
        if result.status == "optimal" and proofs and not all(proofs):
            label = STATUS["incomplete" if any(result.open_slots.values()) else "feasible"]
        proof_parts = [f"{name}: {'bewiesen' if index < len(proofs) and proofs[index] else 'ohne Optimalitätsnachweis'}"
                       for index, name in enumerate(names)]
        proof_text = "Nachweis je Optimierungsstufe: " + "; ".join(proof_parts) if proof_parts else ""
        if result.status in {"unknown", "invalid", "cancelled"} and not result.assignments:
            self._last_status = label; self.result_status.setText(label)
            self.conflicts.append("\n".join(result.messages)); return
        if self.data.assignments:
            box = QMessageBox(self); box.setWindowTitle("Neuen Entwurf übernehmen?")
            box.setText(f"{label}\n{sum(result.open_slots.values())} offene Plätze. Der vorhandene Plan bleibt bis zur Übernahme erhalten.")
            accept = box.addButton("Neuen Entwurf übernehmen", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Verwerfen – vorhandenen Plan behalten", QMessageBox.ButtonRole.RejectRole); box.exec()
            if box.clickedButton() is not accept:
                self._last_status = "Vorhandener Plan behalten"; self._refresh_summaries(); return
        try:
            self._validate_plan(self.data, result.assignments)
            self.data.assignments = result.assignments; self.dirty = True; self._last_status = label
            self._proof_text = proof_text
            self._fill_plan(); self._refresh_summaries(); self._update_banner()
            if result.messages: self.conflicts.append("\n".join(result.messages))
        except Exception as exc: self._error(f"Der neue Entwurf wurde nicht übernommen. {exc}")

    @Slot(str)
    def _solver_error(self, message):
        self._last_status = "Berechnung fehlgeschlagen"; self.result_status.setText(self._last_status); self._error(message)

    @Slot()
    def _solver_done(self):
        thread = self._thread
        # finished wird vor der nativen Thread-Aufräumphase emittiert. Erst
        # warten, dann Python-/QObject-Referenzen für den nächsten Lauf lösen.
        if thread: thread.wait()
        self._thread = None; self._worker = None; self._cancel = None
        if thread: thread.deleteLater()
        self.cancel_button.setEnabled(False); self._update_enabled()

    def toggle_confirmed(self):
        try:
            if self.data.confirmed:
                if QMessageBox.question(self, "Bestätigung aufheben", "Der Monat wird wieder bearbeitbar und zählt vorerst nicht mehr zur bestätigten Historie. Fortfahren?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
                self.store.set_confirmed(self.data.year, self.data.month, False)
                self.data = self.store.load_month(self.data.year, self.data.month)
            else:
                if not self.save_month(): return
                if QMessageBox.question(self, "Plan bestätigen", "Diesen gespeicherten Monatsplan als bestätigte Planungshistorie verwenden? Der Monat wird anschließend gegen Bearbeitung geschützt.",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
                self.store.set_confirmed(self.data.year, self.data.month, True)
                self.data = self.store.load_month(self.data.year, self.data.month)
            self.dirty = False; self._update_enabled(); self._update_banner(); self._refresh_summaries()
        except Exception as exc: self._error(f"Die Bestätigung konnte nicht geändert werden. {exc}")

    def export_csv(self, kind):
        try:
            from . import csvio
            draft = self.collect_data(); self._validate_plan(draft)
            path, _ = QFileDialog.getSaveFileName(self, "CSV exportieren", f"{draft.key}-{kind}.csv", "CSV-Dateien (*.csv)")
            if not path: return
            if kind == "fairness": csvio.export_fairness(path, draft, self.store.history(draft.year, draft.month))
            elif kind == "wishes": csvio.export_wishes(path, draft, self.store.wish_history(draft.year, draft.month))
            else: getattr(csvio, f"export_{kind}")(path, draft)
            self.statusBar().showMessage("CSV-Datei gespeichert (UTF-8 mit BOM, Semikolon).", 5000)
        except Exception as exc: self._error(f"Der Export konnte nicht erstellt werden. {exc}")

    def show_help(self):
        candidates = [Path(getattr(sys, "_MEIPASS", "")) / "README.md", Path(__file__).resolve().parent.parent / "README.md"]
        content = next((p.read_text(encoding="utf-8") for p in candidates if p.is_file()),
                       "Monat wählen → Team und Stunden erfassen → Schichten einstellen → Ausnahmetage wählen → Sperren importieren → Dienstplan erstellen → prüfen und speichern.\n\n"
                       "CSV: datum;von;bis;prioritaet;kommentar. Datum YYYY-MM-DD, Zeiten HH:MM. Beide Zeiten leer = ganztägig. Bis ≤ Von = Folgetag. "
                       "Priorität 1 ist verbindlich, Priorität 2 ein Wunsch. Alle Stunden sind Prognosen.")
        content += (f"\n\n## Persönlicher Speicherort\n\n`{self.database_path}`\n\n"
                    "Ein neuer Monat übernimmt Team, Schichten und Grenzen aus dem zuletzt gespeicherten früheren Monat "
                    "(wenn keiner existiert: aus dem ersten gespeicherten späteren Monat). "
                    "Aus einem bestätigten Monat wird der prognostizierte Endsaldo als neuer Anfangssaldo übernommen; "
                    "bitte vor der Planung anhand der tatsächlichen Situation prüfen. Aus einem Entwurf bleibt der "
                    "bisherige Anfangssaldo erhalten. Der neue gewünschte Endsaldo entspricht zunächst dem Anfangssaldo. "
                    "Datumsbezogene Ausnahmen werden beim Anlegen eines neuen Monats nicht übernommen. "
                    "Beim Kopieren einer Vorlage in einen bereits geöffneten Monat bleiben dessen eigene Ausnahmen erhalten, "
                    "soweit die Schichtkennungen übereinstimmen.")
        dialog = QDialog(self); dialog.setWindowTitle("Dienstplan – deutsche Anleitung"); dialog.resize(850, 650)
        layout = QVBoxLayout(dialog); text = QTextEdit(); text.setReadOnly(True); text.setMarkdown(content); layout.addWidget(text)
        close = QPushButton("Schließen"); close.clicked.connect(dialog.accept); layout.addWidget(close); dialog.exec()

    def closeEvent(self, event):
        if self._thread is not None:
            self.cancel_planning(); self.statusBar().showMessage("Die Berechnung wird beendet. Bitte danach erneut schließen."); event.ignore(); return
        if self._can_leave(): event.accept()
        else: event.ignore()
