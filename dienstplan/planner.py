"""CP-SAT-Planung und dieselbe harte Regelprüfung für manuelle Änderungen.

Ziele werden einzeln gelöst; eine Folgestufe beginnt nur nach bewiesenem Optimum.
Stufe 3: 10 * individuelle absolute Minutenabweichung; je Schichttyp
1 * (60 * absolute Anzahlabweichung + absolute Minutenabweichung), Sondertyp
mit Faktor 4. Zusätzlich wird seine kumulierte historische Bilanz mit Faktor 8
bewertet. Faire Anteile werden auf 1/1000 aufgeteilt (größte Reste, Summe = 1000).
Alle Zielterme werden mit 1000 skaliert, ohne Zwischenrundung der Iststunden.
Historische Fraction-Sollanteile werden erst hier auf 1/1000 gerundet.

Ein Worker und Seed 202611 sorgen bei gleicher OR-Tools-Version für stabile
Gleichstandsentscheidungen. Bei Zeitlimit kann der Suchfortschritt variieren.
Zeitangaben sind lokale naive Uhrzeiten: keine automatische Sommerzeitkorrektur.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from fractions import Fraction
from math import isfinite
from threading import Event, Lock, Thread
from time import monotonic

from ortools.sat.python import cp_model, cp_model_helper

from .hours import demand_minutes, planning_target
from .model import (
    Assignment, HistoryEntry, MonthData, PlanResult, ShiftOccurrence,
    ValidationError, generate_shifts, overlaps,
)

FAIR_SCALE = 1000
HOURS_WEIGHT = 10
REGULAR_WEIGHT = 1
SPECIAL_WEIGHT = 4
HISTORY_WEIGHT = 8
COUNT_MINUTE_EQUIVALENT = 60


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
    for b in data.blockers:
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


def _fair_objective(model: cp_model.CpModel, data: MonthData, shifts, x, history, hint_values=None):
    shares = _shares(data)
    hist = _history_totals(history)
    terms = []
    demand = demand_minutes(data)

    def absolute(expression, bound: int, name: str):
        value = model.new_int_var(0, max(1, bound), name)
        model.add_abs_equality(value, expression)
        if hint_values is not None:
            flat = cp_model_helper.FlatIntExpr(expression)
            hint = flat.offset + sum(coefficient * hint_values[var.index]
                                     for var, coefficient in zip(flat.vars, flat.coeffs))
            model.add_hint(value, abs(hint))
        return value

    for e in data.employees:
        planned = sum(s.paid_minutes * x[(s.id, e.id)] for s in shifts)
        goal = planning_target(e, data.year, data.month)
        deviation = absolute(planned - goal, demand + goal, f"Stundenziel_{e.id}")
        terms.append(HOURS_WEIGHT * FAIR_SCALE * deviation)
    for st in data.shift_types:
        occurrences = [s for s in shifts if s.type_id == st.id]
        max_count = sum(s.staff_required for s in occurrences)
        max_minutes = sum(s.staff_required * s.paid_minutes for s in occurrences)
        total_count = sum(x[(s.id, e.id)] for s in occurrences for e in data.employees)
        total_minutes = sum(s.paid_minutes * x[(s.id, e.id)] for s in occurrences for e in data.employees)
        factor = SPECIAL_WEIGHT if st.special else REGULAR_WEIGHT
        for e in data.employees:
            mine_count = sum(x[(s.id, e.id)] for s in occurrences)
            mine_minutes = sum(s.paid_minutes * x[(s.id, e.id)] for s in occurrences)
            count_balance = FAIR_SCALE * mine_count - shares[e.id] * total_count
            minute_balance = FAIR_SCALE * mine_minutes - shares[e.id] * total_minutes
            count_dev = absolute(count_balance, FAIR_SCALE * max_count, f"Fair_Anzahl_{st.id}_{e.id}")
            minute_dev = absolute(minute_balance, FAIR_SCALE * max_minutes, f"Fair_Minuten_{st.id}_{e.id}")
            terms.extend((factor * COUNT_MINUTE_EQUIVALENT * count_dev, factor * minute_dev))
            if st.special and e.id in hist:
                old = hist[e.id]
                count_offset = FAIR_SCALE * old.special_count - _round_fraction(old.expected_count * FAIR_SCALE)
                minute_offset = FAIR_SCALE * old.special_minutes - _round_fraction(old.expected_minutes * FAIR_SCALE)
                cum_count = absolute(count_balance + count_offset,
                                     FAIR_SCALE * max_count + abs(count_offset), f"Historie_Anzahl_{e.id}")
                cum_minute = absolute(minute_balance + minute_offset,
                                      FAIR_SCALE * max_minutes + abs(minute_offset), f"Historie_Minuten_{e.id}")
                terms.extend((HISTORY_WEIGHT * COUNT_MINUTE_EQUIVALENT * cum_count, HISTORY_WEIGHT * cum_minute))
    return sum(terms)


def _balanced_hint(data, shifts, history, boundary, fallback, deadline, cancel):
    """Zulässiger Startpunkt, danach verbessert CP-SAT die gesamte Zielfunktion.

    Dieser Vorschlag wird nur verwendet, wenn er beide bereits bewiesenen Ziele
    exakt beibehält. Er verändert niemals die lexikografische Optimierung.
    """
    chosen = [a for a in data.assignments if a.fixed]
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
    for s in shifts:
        total_type[s.type_id] += s.staff_required
    for a in chosen:
        by_employee[a.employee_id].append(a)
        selected[a.shift_id].add(a.employee_id)
        minutes[a.employee_id] += by_id[a.shift_id].paid_minutes
        counts[(a.employee_id, by_id[a.shift_id].type_id)] += 1
    breached = {b.identity for b in data.blockers if b.priority == 2
                and any(a.employee_id == b.employee_id
                        and overlaps(by_id[a.shift_id].start, by_id[a.shift_id].end, b.start, b.end)
                        for a in chosen)}
    for s in sorted(shifts, key=lambda occurrence: (not occurrence.special, occurrence.start, occurrence.type_id)):
        for _ in range(s.staff_required - len(selected[s.id])):
            if monotonic() >= deadline or (cancel is not None and cancel.is_set()):
                return fallback
            options = []
            for e in data.employees:
                if e.id in selected[s.id]:
                    continue
                assignment = Assignment(s.id, e.id)
                if validate_assignments(data, by_employee[e.id] + [assignment], old_by_employee[e.id]):
                    continue
                wishes = {b.identity for b in data.blockers if b.priority == 2 and b.employee_id == e.id
                          and overlaps(s.start, s.end, b.start, b.end)}
                expected = total_type[s.type_id] * shares[e.id] / FAIR_SCALE
                if s.special:
                    old = hist.get(e.id, HistoryEntry(e.id))
                    debt = old.special_count - float(old.expected_count)
                    score = (counts[(e.id, s.type_id)] + debt + 1) / max(expected, 0.001)
                    score += 0.1 * (minutes[e.id] + s.paid_minutes) / max(goals[e.id], 1)
                else:
                    score = (minutes[e.id] + s.paid_minutes) / max(goals[e.id], 1)
                    score += 0.25 * (counts[(e.id, s.type_id)] + 1) / max(expected, 0.001)
                options.append((len(wishes - breached), score, e.id, assignment, wishes))
            if not options:
                return fallback
            _, _, employee_id, assignment, wishes = min(options, key=lambda item: item[:3])
            chosen.append(assignment)
            by_employee[employee_id].append(assignment)
            selected[s.id].add(employee_id)
            minutes[employee_id] += s.paid_minutes
            counts[(employee_id, s.type_id)] += 1
            breached.update(wishes)
    if len(chosen) != len(fallback) or len(preference_violations(data, chosen)) != len(preference_violations(data, fallback)):
        return fallback
    if validate_assignments(data, chosen, boundary):
        return fallback
    return chosen


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
    elif not all(optimal_stages) or len(optimal_stages) < 3:
        messages.append("Gültiger Entwurf ohne vollständigen Optimalitätsnachweis; Zeitlimit oder Abbruch begrenzte die Suche.")
    else:
        messages.append("Alle drei Optimierungsstufen sind nachweislich optimal für die dokumentierte Zielfunktion.")
    return messages


def solve(data: MonthData, history: list[HistoryEntry] | None = None,
          boundary: list[tuple[Assignment, ShiftOccurrence]] | None = None,
          time_limit: float = 20, cancel: Event | None = None) -> PlanResult:
    """Optimiert einen neuen Entwurf, ohne MonthData oder gespeicherte Pläne zu ändern."""
    started = monotonic()
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
    wishes = []
    wish_flags = []
    seen = set()
    people = {e.id for e in data.employees}
    for b in data.blockers:
        if b.priority != 2 or b.identity in seen or b.employee_id not in people:
            continue
        seen.add(b.identity)
        matching = [x[(s.id, b.employee_id)] for s in shifts if overlaps(s.start, s.end, b.start, b.end)]
        if matching:
            flag = model.new_bool_var(f"Wunsch_{len(wishes)}")
            model.add_max_equality(flag, matching)
            wishes.append(flag)
            wish_flags.append((flag, matching))
    objectives = [sum(x.values()), sum(wishes)]
    previous = {(a.shift_id, a.employee_id) for a in data.assignments}
    for key, variable in x.items():
        model.add_hint(variable, int(key in previous))
    completed = Event()
    lock = Lock()
    active = [None]

    def watch():
        while not completed.wait(0.025):
            if cancel is not None and cancel.is_set():
                with lock:
                    solver = active[0]
                    if solver is not None:
                        solver.stop_search()

    watcher = Thread(target=watch, daemon=True)
    if cancel is not None:
        watcher.start()
    assignments = []
    optimal_stages = []
    has_solution = False
    fixed_keys = {(a.shift_id, a.employee_id) for a in fixed}
    model_status = None
    reference_solver = None
    try:
        for stage in range(3):
            remaining = time_limit - (monotonic() - started)
            if remaining <= 0 or (cancel is not None and cancel.is_set()):
                break
            if stage == 2:
                warm = _balanced_hint(data, shifts, history, boundary, assignments,
                                      min(started + time_limit * 0.25, monotonic() + 2), cancel)
                warm_keys = {(a.shift_id, a.employee_id) for a in warm}
                hint_values = {index: int(reference_solver.value(model.get_int_var_from_proto_index(index)))
                               for index in range(len(model.proto.variables))}
                for key, variable in x.items():
                    hint_values[variable.index] = int(key in warm_keys)
                for flag, matching in day_flags + wish_flags:
                    hint_values[flag.index] = max(hint_values[variable.index] for variable in matching)
                model.clear_hints()
                for index, value in hint_values.items():
                    model.add_hint(model.get_int_var_from_proto_index(index), value)
                objective = _fair_objective(model, data, shifts, x, history, hint_values)
                remaining = time_limit - (monotonic() - started)
                if remaining <= 0 or (cancel is not None and cancel.is_set()):
                    break
            else:
                objective = objectives[stage]
            if stage == 1 and not wishes:
                optimal_stages.append(True)
                continue
            # Erste zwei Stufen sind meistens schnell; eine Reserve lässt Fairness zu.
            stage_limit = remaining if stage == 2 else min(remaining, max(0.05, time_limit * (0.50 if stage == 0 else 0.20)))
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = stage_limit
            solver.parameters.num_search_workers = 1
            solver.parameters.random_seed = 202611
            solver.parameters.cp_model_probing_level = 0
            if stage == 2:
                # Skalierte absolute Fairnessausdrücke erzeugen beim Presolve
                # riesige dünn besetzte Domänen. Der vollständige gültige Hint
                # startet hier direkt die CP-SAT-Suche und bleibt als Rückfall.
                solver.parameters.cp_model_presolve = False
            if stage == 0:
                model.maximize(objective)
            else:
                model.minimize(objective)
            with lock:
                active[0] = solver
            if cancel is not None and cancel.is_set():
                break
            model_status = solver.solve(model)
            with lock:
                active[0] = None
            if model_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                break
            has_solution = True
            reference_solver = solver
            assignments = [Assignment(s.id, e.id, (s.id, e.id) in fixed_keys)
                           for s in shifts for e in data.employees if solver.boolean_value(x[(s.id, e.id)])]
            optimal = model_status == cp_model.OPTIMAL
            optimal_stages.append(optimal)
            if not optimal:
                break
            if stage < 2:
                optimum = int(solver.value(objective))
                model.add(objective == optimum)
                if stage == 0 and optimum == sum(s.staff_required for s in shifts):
                    for s in shifts:
                        model.add(sum(x[(s.id, e.id)] for e in data.employees) == s.staff_required)
                model.clear_hints()
                for index in range(len(model.proto.variables)):
                    variable = model.get_int_var_from_proto_index(index)
                    model.add_hint(variable, solver.value(variable))
    finally:
        completed.set()
        if watcher.is_alive():
            watcher.join(timeout=0.1)
    cancelled = cancel is not None and cancel.is_set()
    if not has_solution:
        status = "cancelled" if cancelled else "unknown"
        if model_status == cp_model.INFEASIBLE:
            return PlanResult("invalid", messages=["Die fixierten Zuteilungen und aktivierten Regeln "
                                                    "lassen keinen gültigen Entwurf zu."],
                              elapsed_seconds=monotonic() - started)
        if model_status == cp_model.MODEL_INVALID:
            return PlanResult("invalid", messages=["Das Optimierungsmodell konnte nicht verarbeitet werden. "
                                                    "Bitte Stunden und historische Daten prüfen."],
                              elapsed_seconds=monotonic() - started)
    else:
        errors = validate_assignments(data, assignments, boundary)
        if errors:
            return PlanResult("invalid", messages=["Interne Regelprüfung hat den Entwurf zurückgewiesen:"] + errors,
                              elapsed_seconds=monotonic() - started)
        status = "incomplete" if coverage(data, assignments) else (
            "optimal" if len(optimal_stages) == 3 and all(optimal_stages) else "feasible")
    messages = _result_messages(data, shifts, assignments, boundary, status, optimal_stages, cancelled)
    return PlanResult(status, assignments, coverage(data, assignments), preference_violations(data, assignments),
                      messages, optimal_stages, monotonic() - started)
