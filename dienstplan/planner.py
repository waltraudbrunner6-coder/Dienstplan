"""CP-SAT-Planung und dieselbe harte Regelprüfung für manuelle Änderungen.

Strenge lexikografische Ziele und gemeinsame Auswertung mit lokaler Verbesserung.
Eine Folgestufe hält den besten gefundenen Wert der höheren Stufen unverändert;
bei fehlendem Beweis bleibt der Gesamtnachweis ausdrücklich offen. Die genaue
Zielfunktion steht in optimization.py und in der deutschen Anleitung.

Ein Worker und Seed 202611 sorgen bei gleicher OR-Tools-Version für stabile
Gleichstandsentscheidungen. Bei Zeitlimit kann der Suchfortschritt variieren.
Zeitangaben sind lokale naive Uhrzeiten: keine automatische Sommerzeitkorrektur.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from fractions import Fraction
from math import isfinite
from threading import Event, Lock, Thread
from time import monotonic

from ortools.sat.python import cp_model, cp_model_helper

from .hours import demand_minutes, planning_target, monthly_target
from .optimization import evaluate_plan, improve_plan
from .model import (
    Assignment, HistoryEntry, MonthData, PlanResult, ShiftOccurrence,
    ValidationError, WishHistoryEntry, generate_shifts, overlaps,
)

FAIR_SCALE = 1000


def paid_segments(shift: ShiftOccurrence) -> dict[date, int]:
    """Bezahlte Minuten je tatsächlichem Tag; die Pause liegt am Schichtende."""
    result: dict[date, int] = {}
    cursor = shift.start
    paid_end = shift.start + timedelta(minutes=shift.paid_minutes)
    while cursor < paid_end:
        next_day = datetime.combine(cursor.date() + timedelta(days=1), time())
        stop = min(next_day, paid_end)
        result[cursor.date()] = int((stop - cursor).total_seconds() // 60)
        cursor = stop
    return result


def _attendance_days(shift: ShiftOccurrence) -> set[date]:
    last = (shift.end - timedelta(microseconds=1)).date()
    first = shift.start.date()
    return {first + timedelta(days=i) for i in range((last - first).days + 1)}


def _week(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return iso.year, iso.week


def _boundary(data: MonthData, shifts: list[ShiftOccurrence], boundary) -> list[tuple[Assignment, ShiftOccurrence]]:
    current = {s.id for s in shifts}
    people = {e.id for e in data.employees}
    unique = {}
    for assignment, occurrence in boundary or []:
        if assignment.employee_id in people and occurrence.id not in current:
            unique.setdefault((occurrence.id, assignment.employee_id), (assignment, occurrence))
    return list(unique.values())


def coverage(data: MonthData, assignments: list[Assignment] | None = None) -> dict[str, int]:
    """Offene Plätze, je Termin; nur eindeutige bekannte Personen zählen."""
    shifts = generate_shifts(data)
    people = {e.id for e in data.employees}
    chosen = defaultdict(set)
    for a in data.assignments if assignments is None else assignments:
        if a.employee_id in people:
            chosen[a.shift_id].add(a.employee_id)
    return {s.id: s.staff_required - len(chosen[s.id]) for s in shifts
            if s.staff_required > len(chosen[s.id])}


def preference_violations(data: MonthData, assignments: list[Assignment] | None = None) -> list[str]:
    """Jeder übergangene eindeutige Priorität-2-Eintrag wird einmal ausgewiesen."""
    shifts = {s.id: s for s in generate_shifts(data)}
    people = {e.id: e.name for e in data.employees}
    chosen = data.assignments if assignments is None else assignments
    seen = set()
    result = []
    from .wishes import display_wishes
    for b in display_wishes(data):
        if b.priority != 2 or b.identity in seen:
            continue
        seen.add(b.identity)
        if any(a.employee_id == b.employee_id and a.shift_id in shifts
               and overlaps(shifts[a.shift_id].start, shifts[a.shift_id].end, b.start, b.end)
               for a in chosen):
            comment = f" – {b.comment}" if b.comment else ""
            result.append(f"Priorität-2-Wunsch übergangen: {people.get(b.employee_id, b.employee_id)}, "
                          f"{b.start:%d.%m.%Y %H:%M} bis {b.end:%d.%m.%Y %H:%M}{comment}")
    return result


def validate_assignments(data: MonthData, assignments: list[Assignment] | None = None,
                         boundary: list[tuple[Assignment, ShiftOccurrence]] | None = None) -> list[str]:
    """Harte Regeln für einen ganzen Entwurf (offene Plätze sind erlaubt).

    Historische Randzuteilungen beeinflussen Ruhezeiten, Tages-/ISO-Wochensummen
    und Arbeitstagsfolgen. Eigenständige alte Regelverletzungen ohne Beteiligung
    einer aktuellen Zuteilung werden dem aktuellen Entwurf nicht angelastet.
    """
    shifts = generate_shifts(data)
    by_id = {s.id: s for s in shifts}
    return _validate_prepared(data, assignments, boundary, shifts, by_id)


def _validate_prepared(data, assignments, boundary, shifts, by_id):
    """Dieselben Regeln mit vorbereiteten Terminen für viele Startvorschläge."""
    people = {e.id: e.name for e in data.employees}
    chosen = data.assignments if assignments is None else assignments
    errors = []
    current = []
    seen = set()
    counts = defaultdict(int)
    for a in chosen:
        if a.employee_id not in people:
            errors.append(f"Zuteilung enthält eine unbekannte Person: {a.employee_id}.")
            continue
        if a.shift_id not in by_id:
            errors.append(f"Zuteilung enthält einen unbekannten Schichttermin: {a.shift_id}.")
            continue
        key = (a.shift_id, a.employee_id)
        if key in seen:
            errors.append(f"{people[a.employee_id]} ist im Termin {a.shift_id} doppelt zugeteilt.")
            continue
        seen.add(key)
        counts[a.shift_id] += 1
        current.append((a, by_id[a.shift_id]))
    for sid, n in counts.items():
        if n > by_id[sid].staff_required:
            errors.append(f"{by_id[sid].name} am {by_id[sid].start:%d.%m.%Y}: "
                          f"{n} Personen überschreiten die Besetzung von {by_id[sid].staff_required}.")
    blockers = {b.identity: b for b in data.blockers if b.priority == 1}
    for a, s in current:
        for b in blockers.values():
            if a.employee_id == b.employee_id and overlaps(s.start, s.end, b.start, b.end):
                errors.append(f"Verbindliche Priorität-1-Sperre: {people[a.employee_id]}, "
                              f"{s.name} am {s.start:%d.%m.%Y %H:%M}.")
    old = _boundary(data, shifts, boundary)
    for employee_id, name in people.items():
        mine = [s for a, s in current if a.employee_id == employee_id]
        past = [s for a, s in old if a.employee_id == employee_id]
        intervals = sorted([(s, True) for s in mine] + [(s, False) for s in past], key=lambda item: item[0].start)
        for i, (left, is_current) in enumerate(intervals):
            for right, other_current in intervals[i + 1:]:
                if not (is_current or other_current):
                    continue
                if overlaps(left.start, left.end, right.start, right.end):
                    errors.append(f"Überschneidung bei {name}: {left.name} ({left.start:%d.%m. %H:%M}) "
                                  f"und {right.name} ({right.start:%d.%m. %H:%M}).")
                elif data.rules.rest_minutes is not None:
                    gap = int((right.start - left.end).total_seconds() // 60)
                    if gap < data.rules.rest_minutes:
                        errors.append(f"Ruhezeit bei {name}: nur {gap} Minuten zwischen "
                                      f"{left.start:%d.%m. %H:%M} und {right.start:%d.%m. %H:%M}; "
                                      f"mindestens {data.rules.rest_minutes} benötigt.")
        daily = defaultdict(int)
        weekly = defaultdict(int)
        current_days = set()
        current_weeks = set()
        for s in mine + past:
            for day, minutes in paid_segments(s).items():
                daily[day] += minutes
                weekly[_week(day)] += minutes
                if s in mine:
                    current_days.add(day)
                    current_weeks.add(_week(day))
        if data.rules.max_day_minutes is not None:
            for day in sorted(current_days):
                if daily[day] > data.rules.max_day_minutes:
                    errors.append(f"Tagesstunden bei {name} am {day:%d.%m.%Y}: "
                                  f"{daily[day]} Minuten überschreiten {data.rules.max_day_minutes}.")
        if data.rules.max_week_minutes is not None:
            for year, week in sorted(current_weeks):
                minutes = weekly[(year, week)]
                if minutes > data.rules.max_week_minutes:
                    errors.append(f"Wochenstunden bei {name}, ISO-Woche {week}/{year}: "
                                  f"{minutes} Minuten überschreiten {data.rules.max_week_minutes}.")
        if data.rules.max_consecutive_days is not None:
            mine_days = set().union(*(_attendance_days(s) for s in mine)) if mine else set()
            all_days = mine_days | (set().union(*(_attendance_days(s) for s in past)) if past else set())
            runs = []
            for day in sorted(all_days):
                if runs and day == runs[-1][-1] + timedelta(days=1):
                    runs[-1].append(day)
                else:
                    runs.append([day])
            for run in runs:
                if len(run) > data.rules.max_consecutive_days and mine_days.intersection(run):
                    errors.append(f"Aufeinanderfolgende Arbeitstage bei {name}: {len(run)} Tage "
                                  f"vom {run[0]:%d.%m.} bis {run[-1]:%d.%m.}; "
                                  f"höchstens {data.rules.max_consecutive_days} erlaubt.")
    return list(dict.fromkeys(errors))


def _shares(data: MonthData) -> dict[str, int]:
    weights = {e.id: Fraction(e.weekly_hours) for e in data.employees}
    total = sum(weights.values(), Fraction(0))
    fractions = {key: (value / total if total else Fraction(1, len(weights))) * FAIR_SCALE
                 for key, value in weights.items()}
    result = {key: value.numerator // value.denominator for key, value in fractions.items()}
    remainder = FAIR_SCALE - sum(result.values())
    # Stabile IDs entscheiden ausschließlich den Rundungsrest, niemals Namen.
    ordered = sorted(fractions, key=lambda key: (-(fractions[key] - result[key]), key))
    for key in ordered[:remainder]:
        result[key] += 1
    return result


def _round_fraction(value: Fraction) -> int:
    """Symmetrisches kaufmännisches Runden ohne float-Konvertierung."""
    sign = -1 if value < 0 else 1
    positive = abs(value)
    return sign * ((positive.numerator * 2 + positive.denominator) // (2 * positive.denominator))


def _history_totals(history: list[HistoryEntry] | None) -> dict[str, HistoryEntry]:
    result = {}
    for entry in history or []:
        previous = result.setdefault(entry.employee_id, HistoryEntry(entry.employee_id))
        previous.special_count += entry.special_count
        previous.special_minutes += entry.special_minutes
        previous.expected_count += entry.expected_count
        previous.expected_minutes += entry.expected_minutes
    return result


def _add_rules(model: cp_model.CpModel, data: MonthData, shifts: list[ShiftOccurrence], x, boundary):
    old = _boundary(data, shifts, boundary)
    day_flags = []
    for e in data.employees:
        past = [s for a, s in old if a.employee_id == e.id]
        for i, left in enumerate(shifts):
            for right in shifts[i + 1:]:
                collision = overlaps(left.start, left.end, right.start, right.end)
                gap = int((right.start - left.end).total_seconds() // 60)
                if collision or (data.rules.rest_minutes is not None and gap < data.rules.rest_minutes):
                    model.add(x[(left.id, e.id)] + x[(right.id, e.id)] <= 1)
            for other in past:
                collision = overlaps(left.start, left.end, other.start, other.end)
                first, second = sorted((left, other), key=lambda s: s.start)
                gap = int((second.start - first.end).total_seconds() // 60)
                if collision or (data.rules.rest_minutes is not None and gap < data.rules.rest_minutes):
                    model.add(x[(left.id, e.id)] == 0)
        daily = defaultdict(list)
        weekly = defaultdict(list)
        old_daily = defaultdict(int)
        old_weekly = defaultdict(int)
        for s in shifts:
            for day, minutes in paid_segments(s).items():
                daily[day].append(minutes * x[(s.id, e.id)])
                weekly[_week(day)].append(minutes * x[(s.id, e.id)])
        for s in past:
            for day, minutes in paid_segments(s).items():
                old_daily[day] += minutes
                old_weekly[_week(day)] += minutes
        if data.rules.max_day_minutes is not None:
            for day, terms in daily.items():
                model.add(sum(terms) <= max(0, data.rules.max_day_minutes - old_daily[day]))
        if data.rules.max_week_minutes is not None:
            for week, terms in weekly.items():
                model.add(sum(terms) <= max(0, data.rules.max_week_minutes - old_weekly[week]))
        limit = data.rules.max_consecutive_days
        if limit is not None:
            by_day = defaultdict(list)
            for s in shifts:
                for day in _attendance_days(s):
                    by_day[day].append(x[(s.id, e.id)])
            worked = {}
            for day, terms in by_day.items():
                flag = model.new_bool_var(f"Arbeitstag_{e.id}_{day}")
                model.add_max_equality(flag, terms)
                worked[day] = flag
                day_flags.append((flag, terms))
            old_days = set().union(*(_attendance_days(s) for s in past)) if past else set()
            starts = {day - timedelta(days=offset) for day in by_day for offset in range(limit + 1)}
            for start in starts:
                window = [start + timedelta(days=i) for i in range(limit + 1)]
                previous = sum(day in old_days for day in window)
                if previous > limit:
                    # Keine neue Teilnahme an einer bereits zu langen alten Folge.
                    model.add(sum(worked[day] for day in window if day in worked) == 0)
                else:
                    model.add(sum(worked[day] for day in window if day in worked and day not in old_days)
                              <= limit - previous)
    return day_flags


def _balance_seed_swaps(data, shifts, chosen, context, deadline, cancel, boundary=None):
    """Schnelle Startverbesserung durch regelgültige Tausche gleicher Dauer."""
    from .optimization import _PlanState
    by_id = {s.id: s for s in shifts}
    current = list(chosen)
    while monotonic() < deadline and not (cancel is not None and cancel.is_set()):
        state = _PlanState(context, current)
        before = state.score()
        keys = {(a.shift_id, a.employee_id) for a in current}
        movable = [(i, a) for i, a in enumerate(current) if not a.fixed]
        changed = False
        for pos, (i, a) in enumerate(movable):
            for j, b in movable[pos + 1:]:
                if monotonic() >= deadline or (cancel is not None and cancel.is_set()):
                    return current
                left, right = by_id[a.shift_id], by_id[b.shift_id]
                if (a.employee_id == b.employee_id or left.type_id == right.type_id
                        or left.paid_minutes != right.paid_minutes
                        or (a.shift_id, b.employee_id) in keys or (b.shift_id, a.employee_id) in keys):
                    continue
                for assignment, sign in ((a,-1),(b,-1),
                                         (Assignment(a.shift_id,b.employee_id),1),
                                         (Assignment(b.shift_id,a.employee_id),1)):
                    state.adjust(assignment.shift_id,assignment.employee_id,sign)
                better = state.score() < before
                for assignment, sign in ((Assignment(a.shift_id,b.employee_id),-1),
                                         (Assignment(b.shift_id,a.employee_id),-1),(a,1),(b,1)):
                    state.adjust(assignment.shift_id,assignment.employee_id,sign)
                if not better:
                    continue
                candidate = list(current)
                candidate[i] = Assignment(a.shift_id,b.employee_id)
                candidate[j] = Assignment(b.shift_id,a.employee_id)
                if not _validate_prepared(data,candidate,boundary,shifts,by_id):
                    current = candidate
                    changed = True
                    break
            if changed:
                break
        if not changed:
            break
    return current


def _balanced_hint(data, shifts, history, boundary, fallback, deadline, cancel, wish_history=None):
    """Zulässiger Startpunkt, danach verbessert CP-SAT die gesamte Zielfunktion.

    Kandidaten und Tausche verwenden dieselbe lexikografische Bewertung wie
    CP-SAT. Auch bei abgelaufener Startzeit bleibt der beste gültige Teilplan
    erhalten; die anschließende Optimierung hält ihre höheren Stufen fest.
    """
    from .optimization import ObjectiveContext, _PlanState
    chosen = [a for a in data.assignments if a.fixed]
    context = ObjectiveContext(data, history, wish_history)
    state = _PlanState(context, chosen)
    by_employee = defaultdict(list)
    selected = defaultdict(set)
    minutes = defaultdict(int)
    counts = defaultdict(int)
    hist = _history_totals(history)
    shares = _shares(data)
    goals = {e.id: planning_target(e, data.year, data.month) for e in data.employees}
    total_type = defaultdict(int)
    by_id = {s.id: s for s in shifts}
    old_by_employee = defaultdict(list)
    for assignment, occurrence in boundary or []:
        old_by_employee[assignment.employee_id].append((assignment, occurrence))
    personal_data = {e.id: replace(data, employees=[e], blockers=[b for b in data.blockers if b.employee_id == e.id])
                     for e in data.employees}

    def best_valid_start():
        required = {(a.shift_id, a.employee_id) for a in data.assignments if a.fixed}
        if (fallback and required.issubset({(a.shift_id, a.employee_id) for a in fallback})
                and not _validate_prepared(data, fallback, boundary, shifts, by_id)
                and context.evaluate(fallback) <= state.score()):
            return list(fallback)
        return list(chosen)
    for s in shifts:
        total_type[s.type_id] += s.staff_required
    for a in chosen:
        by_employee[a.employee_id].append(a)
        selected[a.shift_id].add(a.employee_id)
        minutes[a.employee_id] += by_id[a.shift_id].paid_minutes
        counts[(a.employee_id, by_id[a.shift_id].type_id)] += 1
    for s in sorted(shifts, key=lambda occurrence: (not occurrence.special, occurrence.start, occurrence.type_id)):
        for _ in range(s.staff_required - len(selected[s.id])):
            if monotonic() >= deadline or (cancel is not None and cancel.is_set()):
                return best_valid_start()
            options = []
            for e in data.employees:
                if e.id in selected[s.id]:
                    continue
                assignment = Assignment(s.id, e.id)
                if _validate_prepared(personal_data[e.id], by_employee[e.id] + [assignment],
                                      old_by_employee[e.id], shifts, by_id):
                    continue
                expected = total_type[s.type_id] * shares[e.id] / FAIR_SCALE
                if s.special:
                    old = hist.get(e.id, HistoryEntry(e.id))
                    debt = old.special_count - float(old.expected_count)
                    score = (counts[(e.id, s.type_id)] + debt + 1) / max(expected, 0.001)
                    score += 0.1 * (minutes[e.id] + s.paid_minutes) / max(goals[e.id], 1)
                else:
                    score = (minutes[e.id] + s.paid_minutes) / max(goals[e.id], 1)
                    score += 0.25 * (counts[(e.id, s.type_id)] + 1) / max(expected, 0.001)
                state.adjust(s.id, e.id, 1)
                objective_score = state.score()
                state.adjust(s.id, e.id, -1)
                options.append((objective_score, score, e.id, assignment))
            if not options:
                continue
            _, _, employee_id, assignment = min(options, key=lambda item: item[:3])
            chosen.append(assignment)
            by_employee[employee_id].append(assignment)
            selected[s.id].add(employee_id)
            minutes[employee_id] += s.paid_minutes
            counts[(employee_id, s.type_id)] += 1
            state.adjust(s.id, employee_id, 1)
    if _validate_prepared(data, chosen, boundary, shifts, by_id):
        return fallback
    chosen = _balance_seed_swaps(data, shifts, chosen, context, deadline, cancel, boundary)
    state = _PlanState(context, chosen)
    return best_valid_start()


def _result_messages(data, shifts, assignments, boundary, status, optimal_stages, cancelled):
    messages = []
    needed = demand_minutes(data)
    targets = sum(planning_target(e, data.year, data.month) for e in data.employees)
    difference = needed - targets
    if difference:
        direction = "über" if difference > 0 else "unter"
        messages.append(f"Rechnerischer Stundenvergleich: Der vollständige Bedarf von {needed / 60:.2f} "
                        f"Mitarbeiterstunden liegt {abs(difference) / 60:.2f} Stunden {direction} den "
                        f"individuellen Planungszielen ({targets / 60:.2f} Stunden). "
                        "Genaue Zielerreichung aller Personen bei voller Besetzung ist damit unmöglich.")
    unchecked = []
    for label, value in (("Ruhezeiten", data.rules.rest_minutes), ("Tagesstunden", data.rules.max_day_minutes),
                         ("ISO-Wochenstunden", data.rules.max_week_minutes),
                         ("aufeinanderfolgende Arbeitstage", data.rules.max_consecutive_days)):
        if value is None:
            unchecked.append(label)
    if unchecked:
        messages.append("Nicht geprüft (keine Grenze aktiviert): " + ", ".join(unchecked) + ".")
    open_slots = coverage(data, assignments)
    if open_slots and status not in {"unknown", "cancelled", "invalid"}:
        messages.append(f"Unvollständiger Entwurf: {sum(open_slots.values())} Schichtplätze bleiben offen. "
                        "Verbindliche Regeln wurden eingehalten.")
        old = _boundary(data, shifts, boundary)
        by_id = {s.id: s for s in shifts}
        for sid, missing in list(open_slots.items())[:8]:
            occurrence = by_id[sid]
            already = {a.employee_id for a in assignments if a.shift_id == sid}
            hard_blocked = sum(any(b.priority == 1 and b.employee_id == e.id
                                   and overlaps(occurrence.start, occurrence.end, b.start, b.end)
                                   for b in data.blockers) for e in data.employees if e.id not in already)
            individually_eligible = sum(not validate_assignments(data, [Assignment(sid, e.id)], old)
                                        for e in data.employees)
            messages.append(f"{occurrence.start:%d.%m.%Y %H:%M}, {occurrence.name}: {missing} offen; "
                            f"{hard_blocked} weitere Personen verbindlich gesperrt, "
                            f"{individually_eligible} grundsätzlich zulässig vor Berücksichtigung anderer "
                            "aktueller Zuteilungen. Weitere Ursachen können Besetzungszahlen, "
                            "Überschneidungen, Fixierungen oder aktivierte Grenzen sein.")
    if cancelled:
        messages.append("Berechnung abgebrochen. Ein bereits gefundenes gültiges Ergebnis bleibt als Entwurf prüfbar.")
    elif status == "unknown":
        messages.append("Innerhalb des Zeitlimits wurde noch kein Ergebnis gefunden. Das beweist keine Unlösbarkeit.")
    elif not optimal_stages or not all(optimal_stages):
        messages.append("Gültiger Entwurf ohne vollständigen Optimalitätsnachweis; Zeitlimit oder Abbruch begrenzte die Suche.")
    else:
        messages.append("Alle Optimierungsstufen sind nachweislich optimal für die dokumentierte Zielfunktion.")
    return messages


class _ObjectiveBuilder:
    """Exakte ganzzahlige CP-Ausdrücke, dieselbe Rechnung wie der externe Scorer."""

    def __init__(self, model, data, shifts, x, history, wish_history):
        from .optimization import ObjectiveContext, stage_names
        from .wishes import wish_key
        self.model, self.data, self.shifts, self.x = model, data, shifts, x
        self.context = ObjectiveContext(data, history, wish_history)
        self.names = stage_names(data, wish_history)
        self.hints = {}
        self.sequence = 0
        self.flags = {}
        self.wish_flags = []
        for b in self.context.wishes:
            terms = [x[(s.id, b.employee_id)] for s in shifts
                     if overlaps(s.start, s.end, b.start, b.end)]
            flag = model.new_bool_var(f"Wunsch_{len(self.flags)}")
            model.add_max_equality(flag, terms)
            self.flags[wish_key(b)] = flag
            self.wish_flags.append((flag, terms))
        self.current = {e.id: sum(self.flags[k] for k in self.context.wish_keys.get(e.id, set()))
                        for e in data.employees}
        self.cumulative = {}
        self.hour_norms = None
        groups = sorted(self.context.wish_groups)
        self.stages = [("coverage", None), ("wishes", None)]
        self.stages.extend(("group_count", group) for group in groups)
        for group in groups:
            self.stages.extend((("group_max", group), ("group_square", group)))
        self.stages.extend((("hours_max", None), ("fairness", None)))

    def expression_value(self, expression):
        if isinstance(expression, int):
            return expression
        flat = cp_model_helper.FlatIntExpr(expression)
        return int(flat.offset + sum(c * self.hints[v.index] for v, c in zip(flat.vars, flat.coeffs)))

    def seed(self, assignments, day_flags):
        chosen = {(a.shift_id, a.employee_id) for a in assignments}
        for key, variable in self.x.items():
            self.hints[variable.index] = int(key in chosen)
        for flag, terms in day_flags + self.wish_flags:
            self.hints[flag.index] = max((self.hints[v.index] for v in terms), default=0)

    def integer(self, low, high, label):
        self.sequence += 1
        return self.model.new_int_var(low, max(low, high), f"{label}_{self.sequence}")

    def absolute(self, expression, bound, label):
        var = self.integer(0, bound, label)
        self.model.add_abs_equality(var, expression)
        self.hints[var.index] = abs(self.expression_value(expression))
        return var

    def ceil_division(self, expression, bound, divisor, label):
        var = self.integer(0, (bound + divisor - 1) // divisor, label)
        self.model.add_division_equality(var, expression + divisor - 1, divisor)
        self.hints[var.index] = (self.expression_value(expression) + divisor - 1) // divisor
        return var

    def square(self, expression, bound, label):
        if isinstance(expression, int):
            return expression * expression
        var = self.integer(0, bound * bound, label)
        self.model.add_multiplication_equality(var, [expression, expression])
        self.hints[var.index] = self.expression_value(expression) ** 2
        return var

    def maximum(self, values, bound, label):
        var = self.integer(0, bound, label)
        self.model.add_max_equality(var, values)
        self.hints[var.index] = max((self.expression_value(v) for v in values), default=0)
        return var

    def group_cumulative(self, group):
        values = []
        for eid in self.context.wish_groups[group]:
            if eid not in self.cumulative:
                historical = self.context.historical_wishes.get(eid, set())
                expression = len(historical) + sum(self.flags[k] for k in self.context.wish_keys[eid]
                                                   if k not in historical)
                var = self.integer(0, len(historical) + group, f"Wunschbelastung_{eid}")
                self.model.add(var == expression)
                self.hints[var.index] = self.expression_value(expression)
                self.cumulative[eid] = (var, len(historical) + group)
            values.append(self.cumulative[eid])
        return values

    def hours(self):
        if self.hour_norms is None:
            self.hour_norms = []
            max_minutes = sum(s.paid_minutes for s in self.shifts)
            for e in self.data.employees:
                goal = planning_target(e, self.data.year, self.data.month)
                denominator = max(monthly_target(e, self.data.year, self.data.month), 60)
                planned = sum(s.paid_minutes * self.x[(s.id, e.id)] for s in self.shifts)
                bound = max(max_minutes, goal)
                absolute = self.absolute(planned - goal, bound, f"Stundenabweichung_{e.id}")
                normalized = self.ceil_division(1000 * absolute, 1000 * bound, denominator,
                                                f"Normierte_Stunden_{e.id}")
                self.hour_norms.append((normalized, (1000 * bound + denominator - 1) // denominator))
        return self.hour_norms

    def objective(self, index):
        kind, group = self.stages[index]
        if kind == "coverage":
            return sum(s.staff_required for s in self.shifts) - sum(self.x.values())
        if kind == "wishes":
            return sum(self.flags.values())
        if kind == "group_count":
            return sum(self.current[eid] for eid in self.context.wish_groups[group])
        if kind == "group_max":
            entries = self.group_cumulative(group)
            return self.maximum([v for v, _ in entries], max(b for _, b in entries), "Wunschmaximum")
        if kind == "group_square":
            return sum(self.square(v, b, "Wunschquadrate") for v, b in self.group_cumulative(group))
        if kind == "hours_max":
            values = self.hours()
            return self.maximum([v for v, _ in values], max(b for _, b in values), "Stundenmaximum")
        from .optimization import HOURS_WEIGHT, REGULAR_WEIGHT, SPECIAL_WEIGHT, HISTORY_WEIGHT, round_fraction
        terms = [HOURS_WEIGHT * self.square(v, b, "Stundenstreuung") for v, b in self.hours()]
        for st in self.data.shift_types:
            occurrences = [s for s in self.shifts if s.type_id == st.id]
            max_count = len(occurrences)
            max_total_count = sum(s.staff_required for s in occurrences)
            max_total_minutes = sum(s.staff_required * s.paid_minutes for s in occurrences)
            total_count = sum(self.x[(s.id, e.id)] for s in occurrences for e in self.data.employees)
            total_minutes = sum(s.paid_minutes * self.x[(s.id, e.id)] for s in occurrences for e in self.data.employees)
            factor = SPECIAL_WEIGHT if st.special else REGULAR_WEIGHT
            for e in self.data.employees:
                share = self.context.shares[e.id]
                count = sum(self.x[(s.id, e.id)] for s in occurrences)
                minutes = sum(s.paid_minutes * self.x[(s.id, e.id)] for s in occurrences)
                count_expression = 1000 * count - share * total_count
                minute_expression = 1000 * minutes - share * total_minutes
                count_bound = 1000 * max(max_count, max_total_count)
                minute_bound = 1000 * max_total_minutes
                count_abs = self.absolute(count_expression, count_bound, "Typanzahl")
                minute_abs = self.absolute(minute_expression, minute_bound, "Typminuten")
                minute_norm = self.ceil_division(minute_abs, minute_bound, 60, "Typstunden")
                terms.extend((factor * self.square(count_abs, count_bound, "Typanzahlquadrate"),
                              factor * self.square(minute_norm, (minute_bound + 59) // 60, "Typstundenquadrate")))
                if st.special and e.id in self.context.hist:
                    old = self.context.hist[e.id]
                    old_count = 1000 * old.special_count - round_fraction(old.expected_count * 1000)
                    old_minutes = 1000 * old.special_minutes - round_fraction(old.expected_minutes * 1000)
                    cumulative_count = self.absolute(count_expression + old_count,
                                                     count_bound + abs(old_count), "Historische_Anzahl")
                    cumulative_minute_bound = minute_bound + abs(old_minutes)
                    cumulative_minutes = self.absolute(minute_expression + old_minutes,
                                                       cumulative_minute_bound, "Historische_Minuten")
                    cumulative_hours = self.ceil_division(cumulative_minutes, cumulative_minute_bound, 60,
                                                          "Historische_Stunden")
                    terms.extend((HISTORY_WEIGHT * self.square(cumulative_count, count_bound + abs(old_count),
                                                              "Historische_Anzahlquadrate"),
                                  HISTORY_WEIGHT * self.square(cumulative_hours,
                                                              (cumulative_minute_bound + 59) // 60,
                                                              "Historische_Stundenquadrate")))
        return sum(terms)


def solve(data: MonthData, history: list[HistoryEntry] | None = None,
          boundary: list[tuple[Assignment, ShiftOccurrence]] | None = None,
          time_limit: float = 20, cancel: Event | None = None,
          wish_history: list[WishHistoryEntry] | None = None) -> PlanResult:
    """CP-SAT + geprüfte lokale Verbesserung; überschreibt keine Monatsdaten."""
    from .optimization import evaluate_plan, improve_plan, stage_names
    started = monotonic()
    deadline = started + time_limit if isinstance(time_limit, (int, float)) and isfinite(time_limit) else started
    try:
        data.validate()
        if not isfinite(time_limit) or time_limit <= 0:
            raise ValidationError("Das Zeitlimit muss eine endliche Zahl größer als null sein.")
    except (ValidationError, TypeError, ValueError) as exc:
        return PlanResult("invalid", messages=[str(exc)], elapsed_seconds=monotonic() - started)
    shifts = generate_shifts(data)
    fixed = [a for a in data.assignments if a.fixed]
    errors = validate_assignments(data, fixed, boundary)
    if errors:
        return PlanResult("invalid", messages=["Fixierte Zuteilungen sind ungültig:"] + errors,
                          elapsed_seconds=monotonic() - started)
    if cancel is not None and cancel.is_set():
        return PlanResult("cancelled", messages=["Berechnung vor dem Start abgebrochen."],
                          elapsed_seconds=monotonic() - started)
    names = stage_names(data, wish_history)
    optimal_stages = [False] * len(names)
    assignments = []
    best_score = None
    improvements = 0

    def consider(candidate):
        nonlocal assignments, best_score, improvements
        score = evaluate_plan(data, candidate, history, wish_history)
        if best_score is None or score < best_score:
            if best_score is not None:
                improvements += 1
            assignments, best_score = list(candidate), score
            return True
        return False

    if data.assignments and not validate_assignments(data, data.assignments, boundary):
        consider(data.assignments)
    if monotonic() < deadline and time_limit >= 0.05:
        greedy = _balanced_hint(data, shifts, history, boundary, [],
                                min(deadline, started + min(0.8, time_limit * 0.12)), cancel, wish_history)
        if greedy and not validate_assignments(data, greedy, boundary):
            consider(greedy)
    if monotonic() >= deadline:
        status = "feasible" if best_score is not None else "unknown"
        if best_score is not None and coverage(data, assignments):
            status = "incomplete"
        return PlanResult(status, assignments, coverage(data, assignments), preference_violations(data, assignments),
                          _result_messages(data, shifts, assignments, boundary, status, optimal_stages, False),
                          optimal_stages, monotonic() - started, names, list(best_score or []), improvements)
    model = cp_model.CpModel()
    x = {(s.id, e.id): model.new_bool_var(f"Z_{s.id}_{e.id}") for s in shifts for e in data.employees}
    for s in shifts:
        model.add(sum(x[(s.id, e.id)] for e in data.employees) <= s.staff_required)
    for e in data.employees:
        for s in shifts:
            if any(b.priority == 1 and b.employee_id == e.id
                   and overlaps(s.start, s.end, b.start, b.end) for b in data.blockers):
                model.add(x[(s.id, e.id)] == 0)
    for a in fixed:
        model.add(x[(a.shift_id, a.employee_id)] == 1)
    day_flags = _add_rules(model, data, shifts, x, boundary)
    builder = _ObjectiveBuilder(model, data, shifts, x, history, wish_history)
    builder.seed(assignments, day_flags)
    fixed_keys = {(a.shift_id, a.employee_id) for a in fixed}
    completed = Event()
    lock = Lock()
    active = [None]

    def watch():
        while not completed.wait(0.025):
            if cancel is not None and cancel.is_set():
                with lock:
                    if active[0] is not None:
                        active[0].stop_search()

    watcher = Thread(target=watch, daemon=True)
    if cancel is not None:
        watcher.start()
    model_status = None
    solver_warnings = []
    local_reserve = min(2.0, time_limit * 0.15)
    search_deadline = deadline - local_reserve
    group_stages = max(1, len(builder.stages) - 4)
    try:
        for index, (kind, group) in enumerate(builder.stages):
            remaining = search_deadline - monotonic()
            if remaining <= 0 or (cancel is not None and cancel.is_set()):
                break
            builder.seed(assignments, day_flags)
            objective = builder.objective(index)
            # Jeder Hilfswert wird aus dem aktuell besten gültigen Plan berechnet.
            # Alte Solverwerte werden nach lokaler Änderung vollständig ersetzt.
            if best_score is not None:
                builder.hints = _hint_values(model, builder, assignments, day_flags)
            model.clear_hints()
            for var_index, value in builder.hints.items():
                model.add_hint(model.get_int_var_from_proto_index(var_index), value)
            incumbent = None if best_score is None else best_score[index]
            if incumbent == 0:
                optimal_stages[index] = True  # sämtliche Ziele sind nichtnegativ
                model.add(objective == 0)
                continue
            if isinstance(objective, int):
                optimal_stages[index] = True
                continue
            if kind == "coverage":
                limit = min(remaining, time_limit * 0.17)
            elif kind == "wishes":
                limit = min(remaining, time_limit * 0.12)
            elif kind.startswith("group"):
                limit = min(remaining, time_limit * 0.21 / group_stages)
            elif kind == "hours_max":
                limit = min(remaining, time_limit * 0.18)
            else:
                limit = remaining
            if limit <= 0:
                break
            limit = min(limit, search_deadline - monotonic())
            if limit <= 0 or (cancel is not None and cancel.is_set()):
                break
            model.minimize(objective)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = limit
            solver.parameters.num_search_workers = 1
            solver.parameters.random_seed = 202611
            solver.parameters.cp_model_probing_level = 0
            if kind in {"hours_max", "fairness"}:
                solver.parameters.cp_model_presolve = False
            with lock:
                active[0] = solver
            model_status = solver.solve(model)
            with lock:
                active[0] = None
            if model_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                candidate = [Assignment(s.id, e.id, (s.id, e.id) in fixed_keys)
                             for s in shifts for e in data.employees if solver.boolean_value(x[(s.id, e.id)])]
                consider(candidate)
                optimal_stages[index] = model_status == cp_model.OPTIMAL
                # Verwendeter Beweis muss zum tatsächlich zurückgegebenen Wert passen.
                if optimal_stages[index] and int(solver.value(objective)) != best_score[index]:
                    optimal_stages[index] = False
                builder.hints = {v.index: int(solver.value(v))
                                 for v in [model.get_int_var_from_proto_index(i)
                                           for i in range(len(model.proto.variables))]}
            elif model_status == cp_model.MODEL_INVALID:
                errors = model.validate()
                if best_score is not None:
                    solver_warnings.append("Eine Optimierungsstufe konnte wegen numerischer Grenzen nicht verarbeitet werden. "
                                           "Der beste gültige Entwurf bleibt erhalten; für die restlichen Stufen fehlt der Optimalitätsnachweis. "
                                           "Bitte sehr große Stundensalden oder historische Belastungen prüfen.")
                    break
                return PlanResult("invalid", messages=["Das Optimierungsmodell konnte nicht verarbeitet werden. "
                                                       "Bitte Stunden und historische Daten prüfen.", errors],
                                  elapsed_seconds=monotonic() - started)
            elif model_status == cp_model.INFEASIBLE:
                # Ein bekannter zulässiger Entwurf schließt echte Unlösbarkeit aus.
                if best_score is None:
                    return PlanResult("invalid", messages=["Die fixierten Zuteilungen und aktivierten Regeln "
                                                           "lassen keinen gültigen Entwurf zu."],
                                      elapsed_seconds=monotonic() - started)
                break
            if best_score is None:
                break
            model.add(objective == best_score[index])
            if kind == "coverage" and best_score[index] == 0:
                for s in shifts:
                    model.add(sum(x[(s.id, e.id)] for e in data.employees) == s.staff_required)
    finally:
        completed.set()
        if watcher.is_alive():
            watcher.join(timeout=0.1)
    if best_score is not None and monotonic() < deadline and not (cancel is not None and cancel.is_set()):
        previous = best_score
        candidate = improve_plan(data, assignments, history, wish_history, boundary,
                                 time_limit=max(0.0, deadline - monotonic()), cancel=cancel)
        if consider(candidate):
            first_changed = next(i for i, (before, after) in enumerate(zip(previous, best_score)) if before != after)
            # Eine nachträgliche Verbesserung widerlegt ggf. einen bedingten alten
            # Nachweis; spätere Stufen wurden unter einem anderen Prefix bewiesen.
            for i in range(first_changed, len(optimal_stages)):
                optimal_stages[i] = False
    cancelled = cancel is not None and cancel.is_set()
    if best_score is None:
        status = "cancelled" if cancelled else "unknown"
    else:
        errors = validate_assignments(data, assignments, boundary)
        if errors:
            return PlanResult("invalid", messages=["Interne Regelprüfung hat den Entwurf zurückgewiesen:"] + errors,
                              elapsed_seconds=monotonic() - started)
        status = "incomplete" if coverage(data, assignments) else (
            "optimal" if all(optimal_stages) else "feasible")
    messages = _result_messages(data, shifts, assignments, boundary, status, optimal_stages, cancelled)
    messages.extend(solver_warnings)
    missing = sorted({month for entry in wish_history or [] for month in entry.missing_months})
    if missing:
        messages.append("Freiwunsch-Althistorie fehlt für bestätigte Monate: " + ", ".join(missing) +
                        ". Der Ausgleich berücksichtigt nur verfügbare bestätigte Wunschstände.")
    if improvements:
        messages.append(f"{improvements} Verbesserung(en) gegenüber gefundenen Startentwürfen; "
                        "der endgültige Plan wurde mit allen verbindlichen Regeln neu geprüft und bewertet.")
    return PlanResult(status, assignments, coverage(data, assignments), preference_violations(data, assignments),
                      messages, optimal_stages, monotonic() - started, names, list(best_score or []), improvements)


def _hint_values(model, builder, assignments, day_flags):
    """Hilfswerte nach einem neuen Incumbent durch die CP-Gleichungen rekonstruieren.

    Die Definitionen sind azyklisch und wurden in ihrer Berechnungsreihenfolge
    angelegt. Das hält einen gültigen Altplan einschließlich Quadratwerten bereit.
    """
    builder.seed(assignments, day_flags)
    values = builder.hints
    for constraint in model.proto.constraints:
        if constraint.has_lin_max():
            body = constraint.lin_max
            expr_values = [expr.offset + sum(c * values[v] for v, c in zip(expr.vars, expr.coeffs))
                           for expr in body.exprs]
            target = body.target
            if len(target.vars) == 1 and target.coeffs[0] == 1:
                values[target.vars[0]] = max(expr_values) - target.offset
        elif constraint.has_int_div():
            body = constraint.int_div
            numerator, denominator = body.exprs
            n = numerator.offset + sum(c * values[v] for v, c in zip(numerator.vars, numerator.coeffs))
            d = denominator.offset + sum(c * values[v] for v, c in zip(denominator.vars, denominator.coeffs))
            target = body.target
            values[target.vars[0]] = n // d
        elif constraint.has_int_prod():
            body = constraint.int_prod
            product = 1
            for expr in body.exprs:
                product *= expr.offset + sum(c * values[v] for v, c in zip(expr.vars, expr.coeffs))
            values[body.target.vars[0]] = product
        elif constraint.has_linear():
            body = constraint.linear
            if len(body.domain) != 2 or body.domain[0] != body.domain[1]:
                continue
            # Nur Hilfsdefinitionen: Ziel ist der zuletzt angelegte Index.
            if not body.vars:
                continue
            target = max(body.vars)
            if target in {v.index for v in builder.x.values()}:
                continue
            coefficient = body.coeffs[list(body.vars).index(target)]
            if coefficient not in (-1, 1):
                continue
            rest = sum(c * values[v] for v, c in zip(body.vars, body.coeffs) if v != target)
            values[target] = (body.domain[0] - rest) // coefficient
    return values
