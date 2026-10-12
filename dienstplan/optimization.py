"""Nachprüfbare lexikografische Bewertung und gültige lokale Verbesserungen.

Alle Zahlen sind ganzzahlig. Wunschbelastung zählt die Vereinigung der
unveränderlichen Wunschschlüssel, damit monatsübergreifende Wünsche einmal
zählen. Die abschließende Fairnessfunktion entspricht der CP-SAT-Funktion.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from math import isfinite
from time import monotonic

from .hours import monthly_target, planning_target
from .model import Assignment, HistoryEntry, MonthData, overlaps, generate_shifts
from .wishes import relevant_wishes, wish_key

FAIR_SCALE = 1000
HOURS_WEIGHT = 10_000
REGULAR_WEIGHT = 1
SPECIAL_WEIGHT = 4
HISTORY_WEIGHT = 8


def ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def round_fraction(value: Fraction) -> int:
    """Symmetrisches kaufmännisches Runden ohne Gleitkommazahlen."""
    value = Fraction(value)
    sign = -1 if value < 0 else 1
    value = abs(value)
    return sign * ((2 * value.numerator + value.denominator) // (2 * value.denominator))


def shares(data: MonthData) -> dict[str, int]:
    """Wochenstundenanteile in Tausendsteln; größte Reste mit stabilen IDs."""
    weights = {e.id: Fraction(e.weekly_hours) for e in data.employees}
    total = sum(weights.values(), Fraction(0))
    if not weights:
        return {}
    raw = {key: FAIR_SCALE * (value / total if total else Fraction(1, len(weights)))
           for key, value in weights.items()}
    result = {key: value.numerator // value.denominator for key, value in raw.items()}
    order = sorted(raw, key=lambda key: (-(raw[key] - result[key]), key))
    for key in order[:FAIR_SCALE - sum(result.values())]:
        result[key] += 1
    return result


def history_totals(history: list[HistoryEntry] | None) -> dict[str, HistoryEntry]:
    result = {}
    for h in history or []:
        value = result.setdefault(h.employee_id, HistoryEntry(h.employee_id))
        value.special_count += h.special_count
        value.special_minutes += h.special_minutes
        value.expected_count += h.expected_count
        value.expected_minutes += h.expected_minutes
    return result


def history_wish_keys(wish_history) -> dict[str, set[str]]:
    result = defaultdict(set)
    for h in wish_history or []:
        result[h.employee_id].update(h.violated_keys)
    return dict(result)


class ObjectiveContext:
    """Teure Zeit-/Wunschzuordnungen einmal je Optimierung vorbereiten."""

    def __init__(self, data: MonthData, history=None, wish_history=None):
        self.data = data
        self.shifts = generate_shifts(data)
        self.by_id = {s.id: s for s in self.shifts}
        self.shares = shares(data)
        self.hist = history_totals(history)
        self.historical_wishes = history_wish_keys(wish_history)
        self.people = sorted(e.id for e in data.employees)
        self.targets = {e.id: planning_target(e, data.year, data.month) for e in data.employees}
        self.denominators = {e.id: max(monthly_target(e, data.year, data.month), 60)
                             for e in data.employees}
        self.wishes = relevant_wishes(data)
        self.wish_keys = {e.id: set() for e in data.employees}
        self.wish_matches = defaultdict(set)
        for b in self.wishes:
            key = wish_key(b)
            self.wish_keys[b.employee_id].add(key)
            for s in self.shifts:
                if overlaps(b.start, b.end, s.start, s.end):
                    self.wish_matches[(s.id, b.employee_id)].add(key)
        self.wish_groups = defaultdict(list)
        for employee_id in self.people:
            count = len(self.wish_keys[employee_id])
            if count:
                self.wish_groups[count].append(employee_id)
        self.wish_groups = dict(sorted(self.wish_groups.items()))
        self.required_slots = sum(s.staff_required for s in self.shifts)
        self.type_ids = [s.id for s in data.shift_types]
        self.special_types = {s.id for s in data.shift_types if s.special}
        self.historical_count_balance = {
            e: FAIR_SCALE * h.special_count - round_fraction(h.expected_count * FAIR_SCALE)
            for e, h in self.hist.items()}
        self.historical_minute_balance = {
            e: FAIR_SCALE * h.special_minutes - round_fraction(h.expected_minutes * FAIR_SCALE)
            for e, h in self.hist.items()}

    def stage_names(self) -> list[str]:
        names = ["Offene Besetzungsplätze", "Übergangene Priorität-2-Wünsche insgesamt"]
        names += [f"Übergangene Wünsche: Gruppe mit {n} Wünschen" for n in self.wish_groups]
        for n in self.wish_groups:
            names += [f"Gruppe mit {n} Wünschen: größte kumulierte Belastung",
                      f"Gruppe mit {n} Wünschen: quadratische kumulierte Belastung"]
        return names + ["Größte relative Stundenabweichung (Promille)",
                        "Quadratische Stunden- und Schichtfairness"]

    def evaluate(self, assignments: list[Assignment]) -> tuple[int, ...]:
        return _PlanState(self, assignments).score()


def stage_names(data: MonthData, wish_history=None) -> list[str]:
    return ObjectiveContext(data, wish_history=wish_history).stage_names()


objective_stage_names = stage_names


def evaluate_plan(data: MonthData, assignments: list[Assignment], history=None,
                  wish_history=None) -> tuple[int, ...]:
    """Kleinere Tupel sind besser; harte Gültigkeit separat prüfen."""
    return ObjectiveContext(data, history, wish_history).evaluate(assignments)


class _PlanState:
    """Summen lassen sich für Kandidaten ändern und verlustfrei zurücksetzen."""

    def __init__(self, context: ObjectiveContext, assignments: list[Assignment]):
        self.context = context
        self.planned = dict.fromkeys(context.people, 0)
        self.counts = defaultdict(int)
        self.minutes = defaultdict(int)
        self.type_counts = defaultdict(int)
        self.type_minutes = defaultdict(int)
        self.wish_counts = defaultdict(int)
        self.keys = {(a.shift_id, a.employee_id) for a in assignments
                     if a.shift_id in context.by_id and a.employee_id in self.planned}
        self.size = 0
        for shift_id, employee_id in self.keys:
            self.adjust(shift_id, employee_id, 1)

    def adjust(self, shift_id: str, employee_id: str, sign: int):
        shift = self.context.by_id[shift_id]
        self.size += sign
        self.planned[employee_id] += sign * shift.paid_minutes
        self.counts[(employee_id, shift.type_id)] += sign
        self.minutes[(employee_id, shift.type_id)] += sign * shift.paid_minutes
        self.type_counts[shift.type_id] += sign
        self.type_minutes[shift.type_id] += sign * shift.paid_minutes
        for key in self.context.wish_matches.get((shift_id, employee_id), ()):
            self.wish_counts[key] += sign

    def score(self) -> tuple[int, ...]:
        c = self.context
        violated = {key for key, count in self.wish_counts.items() if count > 0}
        current = {e: len(c.wish_keys[e] & violated) for e in c.people}
        result = [max(0, c.required_slots - self.size), len(violated)]
        result.extend(sum(current[e] for e in group) for group in c.wish_groups.values())
        for group in c.wish_groups.values():
            burdens = [len(c.historical_wishes.get(e, set()) | (c.wish_keys[e] & violated))
                       for e in group]
            result.extend((max(burdens, default=0), sum(v * v for v in burdens)))
        norms = {e: ceil_div(FAIR_SCALE * abs(self.planned[e] - c.targets[e]),
                             c.denominators[e]) for e in c.people}
        result.append(max(norms.values(), default=0))
        final = HOURS_WEIGHT * sum(n * n for n in norms.values())
        for type_id in c.type_ids:
            for e in c.people:
                final += self.type_penalty(e, type_id)
        result.append(final)
        return tuple(result)

    def type_penalty(self, employee_id: str, type_id: str, count_delta=0, minutes_delta=0) -> int:
        """Einzelterm für exakte lokale Differenzen bei unveränderten Typsummen."""
        c = self.context
        special = type_id in c.special_types
        factor = SPECIAL_WEIGHT if special else REGULAR_WEIGHT
        count_balance = FAIR_SCALE * (self.counts[(employee_id, type_id)] + count_delta) - c.shares[employee_id] * self.type_counts[type_id]
        minute_balance = FAIR_SCALE * (self.minutes[(employee_id, type_id)] + minutes_delta) - c.shares[employee_id] * self.type_minutes[type_id]
        minute_norm = ceil_div(abs(minute_balance), 60)
        value = factor * (count_balance * count_balance + minute_norm * minute_norm)
        if special and employee_id in c.hist:
            cumulative_count = count_balance + c.historical_count_balance.get(employee_id, 0)
            cumulative_minutes = minute_balance + c.historical_minute_balance.get(employee_id, 0)
            cumulative_minute_norm = ceil_div(abs(cumulative_minutes), 60)
            value += HISTORY_WEIGHT * (cumulative_count * cumulative_count +
                                       cumulative_minute_norm * cumulative_minute_norm)
        return value


def improve_plan(data: MonthData, assignments: list[Assignment], history=None,
                 wish_history=None, boundary=None, time_limit: float = 2,
                 cancel=None) -> list[Assignment]:
    """Einzelzuweisungen und Zweiertausche; nur strikt bessere gültige Pläne.

    Die ursprünglichen Objekte werden nicht geändert. Fixierungen im gespeicherten
    Entwurf und im übergebenen Plan gelten gemeinsam. Das Zeitlimit umfasst die
    Vorbereitung; nach Ablauf beginnt keine weitere Kandidatenprüfung.
    """
    from .planner import validate_assignments

    started = monotonic()
    original = list(assignments)
    if not isfinite(time_limit) or time_limit <= 0:
        return original
    deadline = started + time_limit

    def stopped():
        return monotonic() >= deadline or (cancel is not None and cancel.is_set())

    if stopped() or validate_assignments(data, original, boundary):
        return original
    fixed_keys = {(a.shift_id, a.employee_id) for a in data.assignments if a.fixed}
    fixed_keys.update((a.shift_id, a.employee_id) for a in original if a.fixed)
    if not fixed_keys.issubset({(a.shift_id, a.employee_id) for a in original}):
        return original
    context = ObjectiveContext(data, history, wish_history)
    current = sorted([Assignment(a.shift_id, a.employee_id,
                                 (a.shift_id, a.employee_id) in fixed_keys) for a in original],
                     key=lambda a: (a.shift_id, a.employee_id))
    while not stopped():
        state = _PlanState(context, current)
        best_score = state.score()
        best = None
        chosen_keys = {(a.shift_id, a.employee_id) for a in current}
        occupied = defaultdict(int)
        for a in current:
            occupied[a.shift_id] += 1

        def consider(candidate):
            nonlocal best, best_score
            score = state.score()
            if score < best_score and not stopped():
                result = candidate()
                if not validate_assignments(data, result, boundary):
                    best, best_score = result, score

        # Zuerst offene Plätze ergänzen; danach vorhandene Einsätze übertragen.
        for shift in context.shifts:
            if occupied[shift.id] >= shift.staff_required:
                continue
            for e in context.people:
                if stopped():
                    break
                if (shift.id, e) in chosen_keys:
                    continue
                state.adjust(shift.id, e, 1)
                consider(lambda sid=shift.id, eid=e: current + [Assignment(sid, eid)])
                state.adjust(shift.id, e, -1)
            if stopped():
                break
        movable = [(i, a) for i, a in enumerate(current) if not a.fixed]
        for i, a in movable:
            if stopped():
                break
            for e in context.people:
                if stopped():
                    break
                if e == a.employee_id or (a.shift_id, e) in chosen_keys:
                    continue
                state.adjust(a.shift_id, a.employee_id, -1)
                state.adjust(a.shift_id, e, 1)

                def transfer(index=i, sid=a.shift_id, eid=e):
                    result = list(current)
                    result[index] = Assignment(sid, eid)
                    return result

                consider(transfer)
                state.adjust(a.shift_id, e, -1)
                state.adjust(a.shift_id, a.employee_id, 1)
        for pos, (i, a) in enumerate(movable):
            if stopped():
                break
            for j, b in movable[pos + 1:]:
                if stopped():
                    break
                if a.employee_id == b.employee_id or a.shift_id == b.shift_id:
                    continue
                if (a.shift_id, b.employee_id) in chosen_keys or (b.shift_id, a.employee_id) in chosen_keys:
                    continue
                state.adjust(a.shift_id, a.employee_id, -1)
                state.adjust(b.shift_id, b.employee_id, -1)
                state.adjust(a.shift_id, b.employee_id, 1)
                state.adjust(b.shift_id, a.employee_id, 1)

                def swap(left=i, right=j, x=a, y=b):
                    result = list(current)
                    result[left] = Assignment(x.shift_id, y.employee_id)
                    result[right] = Assignment(y.shift_id, x.employee_id)
                    return result

                consider(swap)
                state.adjust(a.shift_id, b.employee_id, -1)
                state.adjust(b.shift_id, a.employee_id, -1)
                state.adjust(a.shift_id, a.employee_id, 1)
                state.adjust(b.shift_id, b.employee_id, 1)
        if best is None:
            break
        current = sorted(best, key=lambda a: (a.shift_id, a.employee_id))
    return current
