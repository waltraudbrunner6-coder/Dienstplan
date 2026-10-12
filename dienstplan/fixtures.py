"""Fiktive, reproduzierbare Fachfixtures für November 2026.

Die früheren externen Testgrenzen sind unbekannt. Diese Daten verwenden
ausdrücklich 11 Stunden Ruhezeit, 12 Stunden pro Tag, 40 Stunden je
ISO-Kalenderwoche und höchstens sechs tatsächliche Arbeitstage in Folge.
Sie bilden keine Behauptung über identische frühere Testläufe.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal

from .model import Assignment, Blocker, Employee, MonthData, Rules, ShiftType, generate_shifts


NOVEMBER_BLOCKERS = {
    1: {1: (3, 8, 14, 25), 2: (1, 7, 15, 18, 22, 29)},
    2: {1: (5, 9, 17, 28), 2: (2, 7, 14, 22, 30)},
    3: {1: (2, 11, 18, 26), 2: (1, 8, 15, 22, 27, 29)},
    4: {1: (6, 12, 20, 29), 2: (4, 7, 15, 22, 28)},
    5: {1: (1, 10, 19, 24), 2: (5, 8, 14, 22, 27, 29)},
    6: {1: (4, 13, 21, 27), 2: (2, 8, 15, 22, 30)},
    7: {1: (7, 15, 23), 2: (1, 6, 14, 18, 22, 28)},
    8: {1: (8, 16, 30), 2: (2, 7, 14, 22, 27)},
}


def test_rules() -> Rules:
    """Dokumentierte Testparameter, keine impliziten gesetzlichen Grenzen."""
    return Rules(rest_minutes=660, max_day_minutes=720,
                 max_week_minutes=2400, max_consecutive_days=6)


def november_shifts() -> list[ShiftType]:
    return [ShiftType("frueh", "Frühdienst", time(10), time(16)),
            ShiftType("spaet", "Spätdienst", time(16), time(22)),
            ShiftType("nacht", "Nachtdienst", time(17), time(1), 30),
            ShiftType("sonder", "Besonderer Dienst", time(19), time(4), 30, weekday=2)]


def november_2026() -> MonthData:
    """Vollständige neue Monatsfixture aus dem fachlichen Änderungsauftrag."""
    people = [Employee(f"person-{i:02d}", f"Person {i}", Decimal(25))
              for i in range(1, 13)]
    blockers = []
    for person, priorities in NOVEMBER_BLOCKERS.items():
        for priority, days in priorities.items():
            for day in days:
                start = datetime(2026, 11, day)
                blockers.append(Blocker(f"nov-{person:02d}-p{priority}-{day:02d}",
                                       f"person-{person:02d}", start,
                                       start + timedelta(days=1), priority,
                                       "Fiktive verbindliche Sperre" if priority == 1 else "Fiktiver Freiwunsch"))
    return MonthData(2026, 11, people, november_shifts(), blockers, test_rules())


def _focused_month() -> MonthData:
    # Die Wochenstunden der unbeteiligten Personen werden nach der vollständigen
    # festen Besetzung auf deren eingeplante Minuten abgestimmt. Damit prüft die
    # Regression den allgemeinen Transfer/Tausch ohne offene Plätze und ohne
    # künstliche Stundenabweichungen bei den übrigen zehn Personen.
    return MonthData(2026, 11,
                     [Employee(f"person-{i:02d}", f"Person {i}", 0) for i in range(1, 13)],
                     november_shifts(), rules=test_rules())


def _assign(data: MonthData, person: int, type_id: str, days: tuple[int, ...]):
    data.assignments.extend(Assignment(f"2026-11-{day:02d}/{type_id}",
                                      f"person-{person:02d}", True) for day in days)


def _complete_fixed_fixture(data: MonthData, focus_people: set[int]) -> MonthData:
    """Eine vollständige, feste Regressionfixture deterministisch konstruieren.

    Dies erstellt Testdaten, keinen automatischen Monatsplan. Die beiden
    Fokuspersonen behalten exakt ihre vorgegebenen Dienste. Jeder zusätzliche
    Einsatz wird mit denselben aktivierten Regeln geprüft und danach fixiert.
    """
    from .planner import validate_assignments

    focus_ids = {f"person-{number:02d}" for number in focus_people}
    shifts = generate_shifts(data)
    by_id = {s.id: s for s in shifts}
    minutes = Counter()
    type_counts = Counter()
    for assignment in data.assignments:
        shift = by_id[assignment.shift_id]
        minutes[assignment.employee_id] += shift.paid_minutes
        type_counts[assignment.employee_id, shift.type_id] += 1
    for shift in shifts:
        missing = shift.staff_required - sum(a.shift_id == shift.id for a in data.assignments)
        for _ in range(missing):
            candidates = sorted(
                (e.id for e in data.employees if e.id not in focus_ids),
                key=lambda person: (minutes[person], type_counts[person, shift.type_id], person))
            for person in candidates:
                assignment = Assignment(shift.id, person, True)
                if not validate_assignments(data, data.assignments + [assignment]):
                    data.assignments.append(assignment)
                    minutes[person] += shift.paid_minutes
                    type_counts[person, shift.type_id] += 1
                    break
            else:
                raise ValueError(f"Regressionfixture kann {shift.id} nicht regelgültig besetzen.")
    for employee in data.employees:
        if employee.id not in focus_ids:
            employee.weekly_hours = Decimal(minutes[employee.id]) * 7 / (30 * 60)
    return data


def night_transfer_case() -> MonthData:
    """Fall A: 10.11. Nachtdienst von Person 10 auf Person 6.

    Die ursprünglichen Verträge des Gegenbeispiels fehlen. 24,9833333333
    Wochenstunden ergeben für Person 10 das passende Monatssoll von 6424
    Minuten; Person 6 hat 25 Wochenstunden und 6429 Minuten. Anfangs- und
    Wunschsaldo sind null. Andere Termine wurden so gewählt, dass sämtliche
    aktivierten Grenzen vor und nach dem Transfer gelten. Die exakten
    16-Stunden-Abstände von Person 6 vor/nach dem Zieldienst bleiben erhalten.
    Der restliche Monat ist vollständig und regelgültig mit den anderen zehn
    Personen besetzt. Deren Wochenstunden entsprechen ihren eingeplanten
    Minuten. Alle übrigen Einsätze sind fixiert, damit der einzelne Wechsel
    isoliert geprüft wird; dies ist kein Sonderfall im Suchverfahren.
    """
    data = _focused_month()
    data.employees[9].weekly_hours = Decimal("24.9833333333")
    data.employees[5].weekly_hours = Decimal(25)
    _assign(data, 10, "nacht", (1, 4, 7, 10, 13, 16, 19, 22, 25))
    _assign(data, 10, "frueh", (3, 24, 27, 29, 30))
    _assign(data, 10, "sonder", (11, 18))
    _assign(data, 6, "nacht", (9, 11, 24))
    _assign(data, 6, "frueh", (1, 2, 3, 5, 7, 13, 15, 17, 19, 21, 28))
    _assign(data, 6, "sonder", (25,))
    for assignment in data.assignments:
        if assignment.shift_id == "2026-11-10/nacht":
            assignment.fixed = False
    return _complete_fixed_fixture(data, {6, 10})


def daily_swap_case() -> MonthData:
    """Fall B: Früh-/Spätdienst am 16.11. tauschen, Stunden bleiben gleich.

    Beide Personen haben 19,6 Wochenstunden und exakt 84 Monatssollstunden.
    Drei zusätzliche achtstündige Nächte von Person 4 gleichen ihre geringere
    Zahl sechsstündiger Dienste aus. Der restliche Monat ist vollständig mit
    den übrigen zehn Personen besetzt; deren Soll entspricht den eingeplanten
    Stunden. Alle anderen Einsätze sind fixiert.
    """
    data = _focused_month()
    for person in (2, 4):
        data.employees[person-1].weekly_hours = Decimal("19.6")
    night = next(s for s in data.shift_types if s.id == "nacht")
    night.start, night.end, night.pause_minutes = time(22), time(6), 0
    _assign(data, 2, "frueh", (1, 3, 5, 7, 9, 11, 13, 16, 18, 20, 22, 24))
    _assign(data, 2, "spaet", (2, 26))
    _assign(data, 4, "frueh", (15, 17, 21))
    _assign(data, 4, "spaet", (6, 8, 12, 14, 16, 19, 23))
    _assign(data, 4, "nacht", (4, 10, 28))
    for assignment in data.assignments:
        if assignment.shift_id in {"2026-11-16/frueh", "2026-11-16/spaet"}:
            assignment.fixed = False
    return _complete_fixed_fixture(data, {2, 4})
