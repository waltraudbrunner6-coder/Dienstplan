"""Stundenrechnung und transparente Ergebnisübersichten in Minuten."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

from .model import Employee, MonthData, Assignment, HistoryEntry, ValidationError, generate_shifts, month_days


def monthly_target(employee: Employee, year: int, month: int) -> int:
    raw = employee.weekly_hours * Decimal(month_days(year, month)) * 60 / 7
    return int(raw.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def planning_target(employee: Employee, year: int, month: int) -> int:
    target = monthly_target(employee, year, month) + employee.desired_minutes - employee.opening_minutes
    if target < 0:
        raise ValidationError(f"{employee.name}: Das Planungsziel ist negativ. Bitte Wochenstunden oder Salden korrigieren.")
    return target


@dataclass
class HourRow:
    employee_id: str
    name: str
    weekly_hours: Decimal
    target_minutes: int
    opening_minutes: int
    desired_minutes: int
    planning_minutes: int
    planned_minutes: int
    new_balance_minutes: int
    projected_balance_minutes: int
    deviation_minutes: int


def hour_rows(data: MonthData, assignments: list[Assignment] | None = None) -> list[HourRow]:
    shifts = {s.id: s for s in generate_shifts(data)}
    totals = {e.id: 0 for e in data.employees}
    for a in data.assignments if assignments is None else assignments:
        if a.shift_id in shifts and a.employee_id in totals:
            totals[a.employee_id] += shifts[a.shift_id].paid_minutes
    result = []
    for e in data.employees:
        s, p = monthly_target(e, data.year, data.month), totals[e.id]
        goal = planning_target(e, data.year, data.month)
        result.append(HourRow(e.id, e.name, e.weekly_hours, s, e.opening_minutes, e.desired_minutes,
                              goal, p, p-s, e.opening_minutes+p-s, p-goal))
    return result


def demand_minutes(data: MonthData) -> int:
    return sum(s.paid_minutes * s.staff_required for s in generate_shifts(data))


def fairness_rows(data: MonthData, assignments: list[Assignment] | None = None,
                  history: list[HistoryEntry] | None = None) -> list[dict]:
    assignments = data.assignments if assignments is None else assignments
    shifts = {s.id: s for s in generate_shifts(data)}
    total_w = sum((Fraction(e.weekly_hours) for e in data.employees), Fraction(0))
    hist = {h.employee_id: h for h in history or []}
    result = []
    for st in data.shift_types:
        chosen = [a for a in assignments if a.shift_id in shifts and shifts[a.shift_id].type_id == st.id]
        total_n = len(chosen)
        total_m = sum(shifts[a.shift_id].paid_minutes for a in chosen)
        for e in data.employees:
            ratio = Fraction(e.weekly_hours) / total_w if total_w else Fraction(1, len(data.employees))
            mine = [a for a in chosen if a.employee_id == e.id]
            n = len(mine); m = sum(shifts[a.shift_id].paid_minutes for a in mine)
            h = hist.get(e.id, HistoryEntry(e.id))
            result.append(dict(employee_id=e.id, name=e.name, type_id=st.id, shift_name=st.name,
                               count=n, minutes=m, expected_count=float(total_n*ratio),
                               count_deviation=float(n-total_n*ratio), expected_minutes=float(total_m*ratio),
                               minute_deviation=float(m-total_m*ratio),
                               historical_count=h.special_count if st.special else 0,
                               historical_expected=float(h.expected_count) if st.special else 0,
                               historical_minutes=h.special_minutes if st.special else 0,
                               historical_expected_minutes=float(h.expected_minutes) if st.special else 0,
                               cumulative_minute_deviation=float(m-total_m*ratio+h.special_minutes-h.expected_minutes) if st.special else 0,
                               cumulative_deviation=float(n-total_n*ratio+h.special_count-h.expected_count) if st.special else 0))
    return result
