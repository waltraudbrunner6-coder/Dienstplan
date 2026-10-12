"""Transaktionale lokale Speicherung mit unabhängigen Monatsschnappschüssen."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime, time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from .model import (Assignment, Blocker, Employee, HistoryEntry, MonthData, Rules,
                    ShiftType, ValidationError, generate_shifts, month_days,
                    overlaps, validate_blockers)


SCHEMA_VERSION = 1


def _encode(data: MonthData) -> str:
    """Sperren liegen global; alle übrigen Werte gehören zum Monatsstand."""
    return json.dumps({
        "year": data.year, "month": data.month, "confirmed": data.confirmed,
        "employees": [dict(id=e.id, name=e.name, weekly_hours=str(e.weekly_hours),
                           opening_minutes=e.opening_minutes, desired_minutes=e.desired_minutes)
                      for e in data.employees],
        "shift_types": [dict(id=s.id, name=s.name, start=s.start.isoformat(timespec="minutes"),
                             end=s.end.isoformat(timespec="minutes"), pause_minutes=s.pause_minutes,
                             staff_required=s.staff_required, weekday=s.weekday)
                        for s in data.shift_types],
        "rules": vars(data.rules),
        "assignments": [vars(a) for a in data.assignments],
    }, ensure_ascii=False, separators=(",", ":"))


def _decode(payload: str) -> MonthData:
    raw = json.loads(payload)
    return MonthData(
        year=raw["year"], month=raw["month"],
        employees=[Employee(**{**e, "weekly_hours": Decimal(e["weekly_hours"])})
                   for e in raw["employees"]],
        shift_types=[ShiftType(**{**s, "start": time.fromisoformat(s["start"]),
                                "end": time.fromisoformat(s["end"])})
                     for s in raw["shift_types"]],
        rules=Rules(**raw["rules"]),
        assignments=[Assignment(**a) for a in raw["assignments"]],
        confirmed=raw.get("confirmed", False),
    )


def _validate_assignments(data: MonthData, boundary: list) -> None:
    # Der Speicher bleibt ohne Qt nutzbar. Import erst beim Speichern, damit das
    # Datenmodell und die CSV-Vorschau keine Solver-Abhängigkeit benötigen.
    try:
        from .planner import validate_assignments
    except ModuleNotFoundError as exc:
        if exc.name != "dienstplan.planner":
            raise
        validate_assignments = None
    if validate_assignments is not None:
        errors = validate_assignments(data, boundary=boundary)
        if errors:
            raise ValidationError("Der Dienstplan ist ungültig: " + "\n".join(errors))
        return
    # Struktur- und Sperrprüfung für das frühe Datenmodell ohne Planungsmodul.
    shifts = {s.id: s for s in generate_shifts(data)}
    employees = {e.id for e in data.employees}
    seen: set[tuple[str, str]] = set()
    counts: dict[str, int] = {}
    occupied = list(boundary)
    for assignment in data.assignments:
        if assignment.shift_id not in shifts or assignment.employee_id not in employees:
            raise ValidationError("Eine Zuteilung verweist auf eine unbekannte Person oder Schicht.")
        key = (assignment.shift_id, assignment.employee_id)
        if key in seen:
            raise ValidationError("Dieselbe Person darf einen Schichttermin nur einmal übernehmen.")
        seen.add(key)
        shift = shifts[assignment.shift_id]
        counts[shift.id] = counts.get(shift.id, 0) + 1
        if counts[shift.id] > shift.staff_required:
            raise ValidationError("Ein Schichttermin hat mehr Zuteilungen als Besetzungsplätze.")
        for blocker in data.blockers:
            if (blocker.priority == 1 and blocker.employee_id == assignment.employee_id
                    and overlaps(shift.start, shift.end, blocker.start, blocker.end)):
                raise ValidationError("Eine Zuteilung verletzt eine verbindliche Priorität-1-Sperre.")
        for previous, other in occupied:
            if (previous.employee_id == assignment.employee_id
                    and overlaps(shift.start, shift.end, other.start, other.end)):
                raise ValidationError("Eine Person darf keine zeitlich überlappenden Schichten übernehmen.")
        occupied.append((assignment, shift))


def _require_complete(data: MonthData) -> None:
    counts: dict[str, int] = {}
    for assignment in data.assignments:
        counts[assignment.shift_id] = counts.get(assignment.shift_id, 0) + 1
    if any(counts.get(s.id, 0) != s.staff_required for s in generate_shifts(data)):
        raise ValidationError("Ein unvollständiger Entwurf kann nicht als Planungshistorie bestätigt werden. Bitte alle offenen Plätze besetzen.")


class Store:
    """SQLite-Store. Änderungen werden vollständig oder gar nicht übernommen."""

    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=10000")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            self.close()
            raise ValidationError("Diese Datendatei stammt aus einer neueren Programmversion.")
        with self.connection:
            self.connection.execute("CREATE TABLE IF NOT EXISTS months (month_key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS blockers (
                id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, start TEXT NOT NULL,
                end TEXT NOT NULL, priority INTEGER NOT NULL CHECK(priority IN (1,2)),
                comment TEXT NOT NULL DEFAULT '', UNIQUE(employee_id,start,end,priority))""")
            self.connection.execute("CREATE INDEX IF NOT EXISTS blockers_employee ON blockers(employee_id)")
            self.connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def _snapshots(self) -> list[MonthData]:
        return [_decode(row[0]) for row in self.connection.execute(
            "SELECT payload FROM months ORDER BY month_key")]

    def _with_blockers(self, data: MonthData, blockers: list[Blocker]) -> MonthData:
        ids = {e.id for e in data.employees}
        return replace(data, blockers=[b for b in blockers if b.employee_id in ids])

    def _protect_confirmed(self, blockers: list[Blocker], replacement: MonthData | None = None) -> None:
        for saved in self._snapshots():
            if saved.confirmed and (replacement is None or saved.key != replacement.key):
                candidate = self._with_blockers(saved, blockers)
                boundary = self.boundary(saved.year, saved.month)
                if replacement is not None:
                    # Die DB enthält bis zum erfolgreichen Commit noch den alten
                    # Stand des Ersatzmonats. Auch die Regeln des bestätigten
                    # Nachbarmonats müssen gegen die neuen Zuteilungen bestehen.
                    boundary = [(a, s) for a, s in boundary
                                if (s.start.year, s.start.month) != (replacement.year, replacement.month)]
                    shifts = {s.id: s for s in generate_shifts(replacement)}
                    boundary.extend((a, shifts[a.shift_id]) for a in replacement.assignments)
                try:
                    _validate_assignments(candidate, boundary)
                except ValidationError as exc:
                    raise ValidationError(f"Die Änderung würde den bestätigten Dienstplan {saved.key} ungültig machen. Bitte zuerst dessen Bestätigung aufheben. {exc}") from exc

    def _write_blockers(self, blockers: list[Blocker]) -> None:
        self.connection.execute("DELETE FROM blockers")
        try:
            self.connection.executemany(
                "INSERT INTO blockers(id,employee_id,start,end,priority,comment) VALUES(?,?,?,?,?,?)",
                [(b.id, b.employee_id, b.start.isoformat(timespec="minutes"),
                  b.end.isoformat(timespec="minutes"), b.priority, b.comment) for b in blockers])
        except sqlite3.IntegrityError as exc:
            raise ValidationError("Sperren benötigen eindeutige Kennungen. Die Änderung wurde nicht gespeichert.") from exc

    def get_blockers(self, employee_id: str | None = None) -> list[Blocker]:
        query = "SELECT id,employee_id,start,end,priority,comment FROM blockers"
        params: tuple = ()
        if employee_id is not None:
            query += " WHERE employee_id=?"
            params = (employee_id,)
        query += " ORDER BY start,employee_id,priority,id"
        return [Blocker(row["id"], row["employee_id"], datetime.fromisoformat(row["start"]),
                        datetime.fromisoformat(row["end"]), row["priority"], row["comment"])
                for row in self.connection.execute(query, params)]

    def replace_blockers(self, employee_id: str, blockers: list[Blocker]) -> None:
        if not employee_id or any(b.employee_id != employee_id for b in blockers):
            raise ValidationError("Alle Sperren müssen zur ausgewählten Person gehören.")
        with self.connection:
            combined = validate_blockers([b for b in self.get_blockers() if b.employee_id != employee_id] + blockers)
            self._protect_confirmed(combined)
            self._write_blockers(combined)

    def save_month(self, data: MonthData) -> None:
        self._save_month(data)

    def save_month_with_blockers(self, data: MonthData, employee_id: str,
                                 blockers: list[Blocker]) -> None:
        """Speichert Monat und genaue Personen-Sperren gemeinsam atomar.

        Auch die erste Sperre benötigt einen persistenten Teamstand mit stabilen
        Personenkennungen. Bei Fehlern bleibt beides vollständig unverändert.
        """
        if not employee_id or employee_id not in {e.id for e in data.employees}:
            raise ValidationError("Die ausgewählte Person muss zum gespeicherten Monat gehören.")
        if any(b.employee_id != employee_id for b in blockers):
            raise ValidationError("Alle Sperren müssen zur ausgewählten Person gehören.")
        candidate = replace(data, blockers=[b for b in data.blockers if b.employee_id != employee_id] + blockers)
        self._save_month(candidate, replaced_employee_id=employee_id)

    def _save_month(self, data: MonthData, replaced_employee_id: str | None = None) -> None:
        data.validate()
        with self.connection:
            saved = self.connection.execute("SELECT payload FROM months WHERE month_key=?", (data.key,)).fetchone()
            if saved is not None and _decode(saved[0]).confirmed:
                raise ValidationError("Dieser Monat ist bestätigt. Bitte vor Änderungen die Bestätigung ausdrücklich aufheben.")
            # Additives Speichern macht die gesamte Eingabekette auch per API
            # nutzbar. Löschen/Bearbeiten von Sperren erfolgt ausdrücklich über
            # replace_blockers, damit das Speichern eines Monats nichts entfernt.
            existing = [b for b in self.get_blockers() if b.employee_id != replaced_employee_id]
            combined = validate_blockers(existing + data.blockers)
            candidate = self._with_blockers(data, combined)
            _validate_assignments(candidate, self.boundary(data.year, data.month))
            if data.confirmed:
                _require_complete(candidate)
            self._protect_confirmed(combined, replacement=candidate)
            self._write_blockers(combined)
            self.connection.execute("INSERT INTO months(month_key,payload) VALUES(?,?) ON CONFLICT(month_key) DO UPDATE SET payload=excluded.payload",
                                    (candidate.key, _encode(candidate)))

    def load_month(self, year: int, month: int) -> MonthData | None:
        month_days(year, month)
        row = self.connection.execute("SELECT payload FROM months WHERE month_key=?", (f"{year:04d}-{month:02d}",)).fetchone()
        return None if row is None else self._with_blockers(_decode(row[0]), self.get_blockers())

    def list_months(self) -> list[str]:
        return [row[0] for row in self.connection.execute("SELECT month_key FROM months ORDER BY month_key")]

    def set_confirmed(self, year: int, month: int, confirmed: bool) -> None:
        month_days(year, month)
        with self.connection:
            data = self.load_month(year, month)
            if data is None:
                raise ValidationError("Dieser Monat wurde noch nicht gespeichert.")
            if confirmed:
                data.validate()
                _validate_assignments(data, self.boundary(year, month))
                _require_complete(data)
            data.confirmed = bool(confirmed)
            self.connection.execute("UPDATE months SET payload=? WHERE month_key=?", (_encode(data), data.key))

    def boundary(self, year: int, month: int) -> list[tuple]:
        month_days(year, month)
        key = f"{year:04d}-{month:02d}"
        result = []
        for saved in self._snapshots():
            if saved.key == key:
                continue
            shifts = {s.id: s for s in generate_shifts(saved)}
            result.extend((a, shifts[a.shift_id]) for a in saved.assignments if a.shift_id in shifts)
        return result

    def history(self, before_year: int, before_month: int) -> list[HistoryEntry]:
        month_days(before_year, before_month)
        key = f"{before_year:04d}-{before_month:02d}"
        aggregate: dict[str, HistoryEntry] = {}
        for saved in self._snapshots():
            if not saved.confirmed or saved.key >= key:
                continue
            shifts = {s.id: s for s in generate_shifts(saved) if s.special}
            chosen = [a for a in saved.assignments if a.shift_id in shifts]
            total_count = len(chosen)
            total_minutes = sum(shifts[a.shift_id].paid_minutes for a in chosen)
            total_weekly = sum((Fraction(e.weekly_hours) for e in saved.employees), Fraction())
            for employee in saved.employees:
                entry = aggregate.setdefault(employee.id, HistoryEntry(employee.id))
                ratio = Fraction(employee.weekly_hours) / total_weekly if total_weekly else Fraction(1, len(saved.employees))
                mine = [a for a in chosen if a.employee_id == employee.id]
                entry.special_count += len(mine)
                entry.special_minutes += sum(shifts[a.shift_id].paid_minutes for a in mine)
                entry.expected_count += total_count * ratio
                entry.expected_minutes += total_minutes * ratio
        return list(aggregate.values())
