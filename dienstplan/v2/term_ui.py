"""Kalender, konkrete Uhrzeiten und Namensauswahl für einzelne Monatstermine."""
import calendar
from datetime import date, datetime, time, timedelta

from PySide6.QtCore import QDate, QLocale, Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTimeEdit,
    QInputDialog, QMessageBox,
    QDateEdit, QVBoxLayout,
)

from .catalog import CATALOG, template
from .errors import DomainError
from .presentation import hours_text
from .time import Interval, local_instant, vienna

FIXED_CODES = frozenset({'LB', 'VN', 'INT', 'N17', 'FK'})


def _qdate(value):
    return QDate(value.year, value.month, value.day)


def _label(service):
    if service.start is None:
        return 'FK · Individueller Dienst mit eigenen Uhrzeiten · 1 Person'
    name = {'R_early': 'R früh', 'R_late': 'R spät'}.get(service.key, service.key)
    following = ' am Folgetag' if service.end <= service.start else ''
    staffing = ('Teilnahme freiwillig' if service.staff is None else
                f'{service.staff} Person' + ('en' if service.staff != 1 else ''))
    return f'{name} · {service.start:%H:%M}–{service.end:%H:%M}{following} · {staffing}'


class TermDialog(QDialog):
    """Erfasst konkrete Vorgaben, ohne feste Personen oder Herbstzeiten zu raten."""
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._updating = False
        self.setWindowTitle('Termin hinzufügen')
        self.resize(760, 610)
        layout = QVBoxLayout(self)
        intro = QLabel('Datum und Dienst auswählen. Feste Personen werden mit Namen ausgewählt; '
                       'reguläre Dienste können später im Dienstplan zugeteilt werden.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        first = date(window.inputs.year, window.inputs.month, 1)
        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        self.day = QDateEdit(_qdate(first))
        self.day.setObjectName('term_date')
        self.day.setLocale(QLocale('de_AT'))
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat('ddd, dd.MM.yyyy')
        self.day.setDateRange(_qdate(first), _qdate(last))
        # Wenn die bisherige Monatsauswahl schon auf einem Tag steht, erhalten.
        try:
            previous = date.fromisoformat(window.day.text())
            if first <= previous <= last:
                self.day.setDate(_qdate(previous))
        except (AttributeError, ValueError):
            pass
        self.service = QComboBox()
        self.service.setObjectName('term_service')
        for item in CATALOG:
            self.service.addItem(_label(item), item.key)
        key = 'KCT10' if self.day.date().toPython().weekday() == 3 else 'KC10'
        self.service.setCurrentIndex(self.service.findData(key))
        self.start_time = QTimeEdit(QTime(10, 0))
        self.start_time.setObjectName('term_start_time')
        self.end_time = QTimeEdit(QTime(18, 0))
        self.end_time.setObjectName('term_end_time')
        for field in (self.start_time, self.end_time):
            field.setDisplayFormat('HH:mm')
        self.next_day = QCheckBox('Ende am folgenden Kalendertag')
        self.next_day.setObjectName('term_next_day')
        self.start_fold, self.end_fold = QComboBox(), QComboBox()
        for field, name in ((self.start_fold, 'term_start_fold'), (self.end_fold, 'term_end_fold')):
            field.setObjectName(name)
            field.addItem('Bitte Uhrzeitvariante auswählen', None)
            field.addItem('Erstes Auftreten (vor Zeitumstellung)', 0)
            field.addItem('Zweites Auftreten (nach Zeitumstellung)', 1)
        self.reason = QLineEdit()
        self.reason.setObjectName('term_replacement_reason')
        self.reason.setPlaceholderText('Warum ersetzt W16 den regulären W17-Dienst?')
        self.form.addRow('Datum im gewählten Monat', self.day)
        self.form.addRow('Dienst', self.service)
        self.form.addRow('Beginn (Wiener Ortszeit)', self.start_time)
        self.form.addRow('Ende (Wiener Ortszeit)', self.end_time)
        self.form.addRow('', self.next_day)
        self.form.addRow('Beginn bei Herbst-Zeitumstellung', self.start_fold)
        self.form.addRow('Ende bei Herbst-Zeitumstellung', self.end_fold)
        self.form.addRow('Begründung für W16', self.reason)
        self.people_label = QLabel()
        self.people_label.setWordWrap(True)
        layout.addWidget(self.people_label)
        self.people = QListWidget()
        self.people.setObjectName('term_fixed_people')
        for person in window.inputs.people:
            item = QListWidgetItem(f'{person.name} ({person.id})')
            item.setData(Qt.ItemDataRole.UserRole, person.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.people.addItem(item)
        layout.addWidget(self.people)
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        layout.addWidget(self.explanation)
        self.summary = QLabel()
        self.summary.setObjectName('term_duration_summary')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.problem = QLabel()
        self.problem.setObjectName('term_validation')
        self.problem.setWordWrap(True)
        layout.addWidget(self.problem)
        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        self.save = QPushButton('Termin hinzufügen')
        self.save.setObjectName('term_save')
        cancel = QPushButton('Abbrechen')
        buttons.addWidget(self.save)
        buttons.addWidget(cancel)
        cancel.clicked.connect(self.reject)
        self.save.clicked.connect(self.accept)
        self.day.dateChanged.connect(self.refresh)
        self.service.currentIndexChanged.connect(self.refresh)
        self.next_day.toggled.connect(self.refresh)
        self.start_time.timeChanged.connect(self.refresh)
        self.end_time.timeChanged.connect(self.refresh)
        self.start_fold.currentIndexChanged.connect(self.refresh)
        self.end_fold.currentIndexChanged.connect(self.refresh)
        self.reason.textChanged.connect(self.refresh)
        self.people.itemChanged.connect(self.refresh)
        self.refresh()

    def selected_people(self):
        return tuple(self.people.item(i).data(Qt.ItemDataRole.UserRole)
                     for i in range(self.people.count())
                     if self.people.item(i).checkState() == Qt.CheckState.Checked)

    def _local_values(self):
        day = self.day.date().toPython()
        end_day = day + timedelta(days=int(self.next_day.isChecked()))
        return (datetime.combine(day, self.start_time.time().toPython()),
                datetime.combine(end_day, self.end_time.time().toPython()))

    def _ambiguous(self, value):
        try:
            return local_instant(value, fold=0) != local_instant(value, fold=1)
        except DomainError:
            return False

    def values(self):
        key = self.service.currentData()
        service = template(key)
        day = self.day.date().toPython()
        if (day.year, day.month) != (self.window.inputs.year, self.window.inputs.month):
            raise DomainError('Bitte ein Datum aus dem geöffneten Monat auswählen.')
        people = self.selected_people() if service.code in FIXED_CODES else ()
        if service.code in FIXED_CODES and len(people) != service.staff:
            raise DomainError(f'Bitte genau {service.staff} feste Person' +
                              ('en' if service.staff != 1 else '') + ' auswählen.')
        if not set(people) <= {p.id for p in self.window.inputs.people}:
            raise DomainError('Die ausgewählte Person gehört nicht zum aktuellen Team.')
        reason = self.reason.text().strip() if key == 'W16' else ''
        if key == 'W16' and not reason:
            raise DomainError('Bitte den Ersatzgrund für W16 eintragen.')
        attendance = None
        if key == 'FK':
            start, end = self._local_values()
            attendance = Interval(local_instant(start, fold=self.start_fold.currentData()),
                                  local_instant(end, fold=self.end_fold.currentData()))
        return dict(key=key, day=day, people=people, reason=reason, attendance=attendance)

    def refresh(self, *_):
        if self._updating:
            return
        self._updating = True
        try:
            service = template(self.service.currentData())
            custom = service.key == 'FK'
            for field in (self.start_time, self.end_time, self.next_day):
                self.form.setRowVisible(field, custom)
            for moment, field in zip(self._local_values(), (self.start_fold, self.end_fold)):
                ambiguous = custom and self._ambiguous(moment)
                self.form.setRowVisible(field, ambiguous)
                if not ambiguous:
                    field.setCurrentIndex(0)
            self.form.setRowVisible(self.reason, service.key == 'W16')
            fixed = service.code in FIXED_CODES
            self.people.setVisible(fixed)
            self.people_label.setText(
                f'Genau {service.staff} feste Person' + ('en' if service.staff != 1 else '') + ' auswählen:'
                if fixed else 'Personen werden anschließend im Dienstplan zugeordnet.')
            if service.key == 'KC15':
                explanation = 'KC15 ist ein Ersatzdienst: An diesem Datum entfallen KC10 und KC16.'
            elif service.code == 'R':
                explanation = 'Reserve zählt wie normale Arbeit. Bei mehr als sechs Stunden gilt die übliche halbstündige Pause.'
            elif service.key == 'LB' or service.key == 'LB_TS':
                explanation = 'LB hat zwei ausdrücklich ausgewählte feste Personen; es werden keine Personen geraten.'
            elif custom:
                explanation = 'Bei einem Dienst über Mitternacht „Ende am folgenden Kalendertag“ markieren. Herbstzeiten müssen eindeutig gewählt werden.'
            else:
                explanation = 'Die Uhrzeiten und Besetzung stammen aus dem Dienstkatalog. Zugeordnete Personen lassen sich später im Dienstplan ändern.'
            self.explanation.setText(explanation)
            if custom:
                start, end = self._local_values()
                span = Interval(local_instant(start, fold=self.start_fold.currentData()),
                                local_instant(end, fold=self.end_fold.currentData()))
            else:
                span = service.on(self.day.date().toPython())
            pause = 30 if span.minutes > 360 else 0
            end_text = span.end.astimezone(vienna()).strftime('%d.%m.%Y %H:%M')
            self.summary.setText(f'Ende: {end_text} · Anwesenheit {hours_text(span.minutes)} h · '
                                 f'Pause {hours_text(pause)} h · bezahlte Dauer {hours_text(span.minutes - pause)} h. '
                                 'Die konkrete Pause wird bei der Zuteilung gesetzt.')
            try:
                self.values()
                self.problem.clear()
                self.save.setEnabled(True)
            except DomainError as exc:
                self.problem.setText(str(exc))
                self.save.setEnabled(False)
        except DomainError as exc:
            self.summary.clear()
            self.problem.setText(str(exc))
            self.save.setEnabled(False)
        finally:
            self._updating = False

    def apply_to(self, window):
        """Kompatibilitätsadapter zu den bisherigen erprobten Terminaktionen."""
        value = self.values()
        window.code.setCurrentText(value['key'])
        window.day.setText(value['day'].isoformat())
        window.fixed.setText(','.join(value['people']))
        if value['attendance'] is not None:
            window.fk_start.setText(value['attendance'].start.astimezone(vienna()).isoformat())
            window.fk_end.setText(value['attendance'].end.astimezone(vienna()).isoformat())
        if value['key'] == 'W16':
            return window.add_term(reason=value['reason'])
        return window.add_term()


def add_missing_lb(window):
    """Fehlende LB-Rhythmustermine gemeinsam mit einem ausdrücklich gewählten Paar ergänzen."""
    from .catalog import event, lb_dates
    for check in ('require_accepted_result', 'ensure_team_saved'):
        method = getattr(window, check, None)
        if method is not None:
            method()
    inputs = window.inputs
    expected = lb_dates(inputs.year, inputs.month)
    existing = tuple(e for e in inputs.events if e.service.code == 'LB')
    present = {e.attendance.start_day for e in existing}
    missing = tuple(day for day in expected if day not in present)
    if not expected:
        QMessageBox.information(window, 'LB-Termine ergänzen',
                                'In diesem Monat sind keine LB-Termine vorgesehen. '
                                'Der 14-tägige Rhythmus beginnt am 03.12.2026.')
        return None
    if not missing:
        QMessageBox.information(window, 'LB-Termine ergänzen',
                                'Alle LB-Termine dieses Monats sind bereits vorhanden. '
                                'Ihre Personen und Zuteilungen bleiben unverändert.')
        return None
    people = tuple(inputs.people)
    ids = tuple(p.id for p in people)
    if len(set(ids)) != len(ids) or any(not pid for pid in ids):
        raise DomainError('Die Personenkennungen des Teams sind nicht eindeutig.')
    if len(people) < 2:
        raise DomainError('LB benötigt zwei unterschiedliche feste Personen. '
                          'Bitte zuerst mindestens zwei Personen erfassen.')
    labels = [f'{p.name} ({p.id})' for p in people]
    by_id = {p.id: label for p, label in zip(people, labels)}
    pairs = tuple(e.fixed_people for e in existing if len(e.fixed_people) == 2
                  and set(e.fixed_people) <= set(ids))
    suggested = pairs[0] if pairs else ()
    dates_text = ', '.join(day.strftime('%d.%m.%Y') for day in missing)
    context = (f'Fehlende Termine: {dates_text}.\n'
               'Nur diese fehlenden Termine erhalten das jetzt gewählte Paar. '
               'Bereits vorhandene LB-Termine, ihre Personen und ihre Zuteilungen bleiben unverändert.')
    if suggested:
        context += '\nBisheriges Paar als Vorschlag: ' + ', '.join(by_id[pid] for pid in suggested) + '.'
        context += ' Ein anderes gewähltes Paar gilt ausschließlich für die noch fehlenden Termine.'
        if len({frozenset(pair) for pair in pairs})>1:
            context += '\nDie vorhandenen LB-Termine haben unterschiedliche Paare; diese bleiben jeweils bestehen.'
    first_index = ids.index(suggested[0]) if suggested else 0
    first, ok = QInputDialog.getItem(window, 'LB-Termine ergänzen',
                                    context + '\nErste feste Person:', labels, first_index, False)
    if not ok:
        return None
    if first not in labels:
        raise DomainError('Bitte eine Person aus der Liste auswählen.')
    first_id = ids[labels.index(first)]
    remaining = tuple(p for p in people if p.id != first_id)
    second_labels = [by_id[p.id] for p in remaining]
    second_index = next((i for i, p in enumerate(remaining)
                         if suggested and p.id == suggested[1]), 0)
    second, ok = QInputDialog.getItem(window, 'LB-Termine ergänzen',
                                     context + '\nErste Person: ' + first +
                                     '\nZweite feste Person (muss eine andere sein):',
                                     second_labels, second_index, False)
    if not ok:
        return None
    if second not in second_labels:
        raise DomainError('Bitte eine andere Person aus der Liste auswählen.')
    second_id = remaining[second_labels.index(second)].id
    active = getattr(window, 'events', None)
    active = inputs.events if active is None else active
    ts_days = {e.attendance.start_day for e in active if e.service.code == 'TS'}
    additions = tuple(event('LB_TS' if day in ts_days else 'LB', day,
                            people=(first_id, second_id)) for day in missing)
    return window.change_terms(set(), additions)
