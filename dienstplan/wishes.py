"""Eindeutige Freiwünsche, unveränderliche Schlüssel und kumulierte Statistik."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime

from .model import Assignment, Blocker, MonthData, WishHistoryEntry, generate_shifts, overlaps


def wish_key(blocker: Blocker) -> str:
    """Identität bleibt bei erneutem Import und über Monatsgrenzen gleich."""
    return json.dumps([blocker.employee_id, blocker.start.isoformat(timespec="minutes"),
                       blocker.end.isoformat(timespec="minutes")], separators=(",", ":"), ensure_ascii=False)


def relevant_wishes(data: MonthData) -> list[Blocker]:
    shifts = generate_shifts(data)
    people = {e.id for e in data.employees}
    unique = {}
    for b in data.blockers:
        if b.priority == 2 and b.employee_id in people and any(overlaps(b.start,b.end,s.start,s.end) for s in shifts):
            unique.setdefault(wish_key(b), b)
    return sorted(unique.values(), key=lambda b: (b.employee_id,b.start,b.end))


def display_wishes(data: MonthData) -> list[Blocker]:
    """Bestätigte Markierungen passen zur eingefrorenen Wunschstatistik."""
    if not data.confirmed or data.wish_snapshot is None:
        return relevant_wishes(data)
    records = {}
    for stats in data.wish_snapshot.values():
        for key in stats.get("relevant", []):
            employee_id, start, end = json.loads(key)
            records.setdefault(key, Blocker(key,employee_id,datetime.fromisoformat(start),
                                            datetime.fromisoformat(end),2,"Bestätigter Freiwunsch"))
    return sorted(records.values(), key=lambda b: (b.employee_id,b.start,b.end))


def violated_wish_keys(data: MonthData, assignments: list[Assignment] | None = None) -> set[str]:
    shifts = {s.id: s for s in generate_shifts(data)}
    by_person = defaultdict(list)
    for a in data.assignments if assignments is None else assignments:
        if a.shift_id in shifts:
            by_person[a.employee_id].append(shifts[a.shift_id])
    return {wish_key(b) for b in relevant_wishes(data)
            if any(overlaps(b.start,b.end,s.start,s.end) for s in by_person[b.employee_id])}


def wish_rows(data: MonthData, assignments: list[Assignment] | None = None,
              wish_history: list[WishHistoryEntry] | None = None) -> list[dict]:
    relevant = defaultdict(set)
    frozen = data.confirmed and data.wish_snapshot is not None and (assignments is None or assignments == data.assignments)
    if frozen:
        violated = set()
        for employee_id, stats in data.wish_snapshot.items():
            relevant[employee_id].update(stats.get("relevant", []))
            violated.update(stats.get("violated", []))
    else:
        for b in relevant_wishes(data):
            relevant[b.employee_id].add(wish_key(b))
        violated = violated_wish_keys(data, assignments)
    historical = defaultdict(set)
    missing = defaultdict(set)
    for h in wish_history or []:
        historical[h.employee_id].update(h.violated_keys)
        missing[h.employee_id].update(h.missing_months)
    rows = []
    for e in data.employees:
        mine = relevant[e.id] & violated
        rows.append(dict(employee_id=e.id, name=e.name, relevant=len(relevant[e.id]),
                         fulfilled=len(relevant[e.id])-len(mine), violated=len(mine),
                         historical=len(historical[e.id]), cumulative=len(historical[e.id]|mine),
                         missing_months=sorted(missing[e.id]),
                         snapshot_missing=bool(data.confirmed and data.wish_snapshot is None)))
    return rows


def wish_snapshot(data: MonthData) -> dict:
    relevant = defaultdict(list)
    for b in relevant_wishes(data):
        relevant[b.employee_id].append(wish_key(b))
    violated = violated_wish_keys(data)
    return {e.id: {"relevant": relevant[e.id], "violated": [k for k in relevant[e.id] if k in violated]}
            for e in data.employees}
