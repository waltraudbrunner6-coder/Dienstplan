"""Reine Datenmodelle und zeitliche Konventionen, ohne UI/SQLite/Solver."""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction
from uuid import uuid4


class ValidationError(ValueError):
    """Verständliche Meldung für ungültige Benutzereingaben."""


def new_id() -> str:
    return uuid4().hex


def decimal_hours(value: str | Decimal | float | int) -> Decimal:
    try:
        result = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValidationError("Stunden müssen eine gültige Zahl sein.") from exc
    if not result.is_finite():
        raise ValidationError("Stunden müssen eine endliche Zahl sein.")
    return result


def to_minutes(value: str | Decimal | float | int) -> int:
    hours = decimal_hours(value)
    if abs(hours) > 10000:
        raise ValidationError("Stundenangaben dürfen höchstens 10.000 Stunden betragen.")
    return int((hours * 60).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def format_hours(minutes: int) -> str:
    return f"{minutes / 60:.2f}".replace(".", ",")


def month_days(year: int, month: int) -> int:
    if not 1900 <= year <= 2200 or not 1 <= month <= 12:
        raise ValidationError("Bitte einen Monat zwischen Januar 1900 und Dezember 2200 wählen.")
    return calendar.monthrange(year, month)[1]


@dataclass
class Employee:
    id: str
    name: str
    weekly_hours: Decimal
    opening_minutes: int = 0
    desired_minutes: int | None = None

    def __post_init__(self):
        self.weekly_hours = decimal_hours(self.weekly_hours)
        if self.desired_minutes is None:
            self.desired_minutes = self.opening_minutes

    def validate(self):
        if not self.id or not self.name.strip():
            raise ValidationError("Jede Person benötigt einen Namen und eine eindeutige Kennung.")
        if not 0 <= self.weekly_hours <= 168:
            raise ValidationError(f"{self.name}: Wochenstunden müssen zwischen 0 und 168 liegen.")
        if not isinstance(self.opening_minutes, int) or not isinstance(self.desired_minutes, int):
            raise ValidationError(f"{self.name}: Stundensalden müssen intern auf ganze Minuten gerundet sein.")
        if abs(self.opening_minutes) > 600_000 or abs(self.desired_minutes) > 600_000:
            raise ValidationError(f"{self.name}: Ein Stundensaldo darf höchstens 10.000 Stunden betragen.")


@dataclass
class ShiftType:
    id: str
    name: str
    start: time
    end: time
    pause_minutes: int = 0
    staff_required: int = 2
    weekday: int | None = None

    @property
    def special(self) -> bool:
        return self.weekday is not None

    @property
    def duration_minutes(self) -> int:
        a = self.start.hour * 60 + self.start.minute
        b = self.end.hour * 60 + self.end.minute
        return (b - a) if b > a else (b - a + 1440)

    @property
    def paid_minutes(self) -> int:
        return self.duration_minutes - self.pause_minutes

    def validate(self):
        if not self.id or not self.name.strip():
            raise ValidationError("Jede Schicht benötigt einen Namen und eine Kennung.")
        if any(t.second or t.microsecond or t.tzinfo is not None for t in (self.start, self.end)):
            raise ValidationError(f"{self.name}: Bitte lokale Schichtzeiten in ganzen Minuten verwenden.")
        if not isinstance(self.staff_required, int) or not 1 <= self.staff_required <= 100:
            raise ValidationError(f"{self.name}: Besetzung muss zwischen 1 und 100 liegen.")
        if not isinstance(self.pause_minutes, int) or not 0 <= self.pause_minutes < self.duration_minutes:
            raise ValidationError(f"{self.name}: Pause muss kürzer als die Schicht und mindestens null sein.")
        if self.weekday is not None and self.weekday not in range(7):
            raise ValidationError("Ungültiger Wochentag für die besondere Schicht.")


@dataclass
class Blocker:
    id: str
    employee_id: str
    start: datetime
    end: datetime
    priority: int
    comment: str = ""

    @property
    def identity(self) -> tuple:
        return self.employee_id, self.start, self.end, self.priority

    def validate(self):
        if self.priority not in (1, 2):
            raise ValidationError("Die Priorität muss 1 oder 2 sein.")
        if not self.employee_id or self.start.tzinfo or self.end.tzinfo:
            raise ValidationError("Sperren benötigen eine Person und lokale Zeitangaben ohne Zeitzone.")
        if self.start.second or self.end.second or self.start.microsecond or self.end.microsecond:
            raise ValidationError("Sperrzeiten müssen auf ganze Minuten angegeben werden.")
        if not timedelta(0) < self.end - self.start <= timedelta(days=1):
            raise ValidationError("Ein Blocker muss länger als null und höchstens 24 Stunden sein.")


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def blocker_months(blocker: Blocker) -> set[tuple[int, int]]:
    last = blocker.end - timedelta(microseconds=1)
    return {(blocker.start.year, blocker.start.month), (last.year, last.month)}


def validate_blockers(blockers: list[Blocker]) -> list[Blocker]:
    unique = {}
    for b in blockers:
        b.validate()
        unique.setdefault(b.identity, b)
    counts = {}
    for b in unique.values():
        if b.priority == 1:
            for y, m in blocker_months(b):
                key = (b.employee_id, y, m)
                counts[key] = counts.get(key, 0) + 1
                if counts[key] > 4:
                    raise ValidationError(f"Höchstens vier Priorität-1-Blocker pro Person und Monat erlaubt ({m:02d}/{y}). Die Änderung wurde abgelehnt.")
    return list(unique.values())


@dataclass
class Rules:
    rest_minutes: int | None = None
    max_day_minutes: int | None = None
    max_week_minutes: int | None = None
    max_consecutive_days: int | None = None

    def validate(self):
        limits = {"Ruhezeit": (self.rest_minutes, 0, 10080), "Tagesstunden": (self.max_day_minutes, 1, 1440),
                  "Wochenstunden": (self.max_week_minutes, 1, 10080), "Aufeinanderfolgende Arbeitstage": (self.max_consecutive_days, 1, 366)}
        for label, (value, low, high) in limits.items():
            if value is not None and (not isinstance(value, int) or not low <= value <= high):
                raise ValidationError(f"{label}: Wert außerhalb des zulässigen Bereichs.")


@dataclass
class ShiftOccurrence:
    id: str
    type_id: str
    name: str
    start: datetime
    end: datetime
    paid_minutes: int
    staff_required: int
    special: bool = False


@dataclass
class Assignment:
    shift_id: str
    employee_id: str
    fixed: bool = False


@dataclass
class MonthData:
    year: int
    month: int
    employees: list[Employee] = field(default_factory=list)
    shift_types: list[ShiftType] = field(default_factory=list)
    blockers: list[Blocker] = field(default_factory=list)
    rules: Rules = field(default_factory=Rules)
    assignments: list[Assignment] = field(default_factory=list)
    confirmed: bool = False
    exceptions: set[str] = field(default_factory=set)
    wish_snapshot: dict | None = None

    @property
    def key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def validate(self):
        month_days(self.year, self.month)
        if not self.employees:
            raise ValidationError("Bitte mindestens eine Person erfassen.")
        if len({e.id for e in self.employees}) != len(self.employees):
            raise ValidationError("Personenkennungen müssen eindeutig sein.")
        for e in self.employees:
            e.validate()
            from .hours import planning_target
            planning_target(e, self.year, self.month)
        if len(self.shift_types) != 4 or sum(s.special for s in self.shift_types) != 1:
            raise ValidationError("Bitte genau drei tägliche und eine wöchentliche Schicht erfassen.")
        if len({s.id for s in self.shift_types}) != 4:
            raise ValidationError("Schichtkennungen müssen eindeutig sein.")
        for s in self.shift_types:
            s.validate()
        daily_ids = {s.id for s in self.shift_types if not s.special}
        for occurrence_id in self.exceptions:
            try:
                day_text, type_id = occurrence_id.split("/", 1)
                day = date.fromisoformat(day_text)
            except (ValueError, AttributeError) as exc:
                raise ValidationError("Ein Ausnahmetag enthält ein ungültiges Datum oder eine ungültige Schicht.") from exc
            if day_text != day.isoformat() or (day.year, day.month) != (self.year, self.month) or type_id not in daily_ids:
                raise ValidationError("Ausnahmen gelten nur für tägliche Schichten im ausgewählten Monat.")
        self.rules.validate()
        validate_blockers(self.blockers)


def generate_shifts(data: MonthData) -> list[ShiftOccurrence]:
    result = []
    for day in range(1, month_days(data.year, data.month) + 1):
        d = date(data.year, data.month, day)
        for s in data.shift_types:
            if s.special and s.weekday != d.weekday():
                continue
            occurrence_id = f"{d.isoformat()}/{s.id}"
            if not s.special and occurrence_id in data.exceptions:
                continue
            start = datetime.combine(d, s.start)
            end = start + timedelta(minutes=s.duration_minutes)
            result.append(ShiftOccurrence(occurrence_id, s.id, s.name, start, end,
                                          s.paid_minutes, s.staff_required, s.special))
    return sorted(result, key=lambda s: (s.start, s.type_id))


def inactive_shifts(data: MonthData) -> list[ShiftOccurrence]:
    """Entfallene tägliche Termine für Anzeige/Export, ohne offenen Bedarf."""
    from dataclasses import replace
    return [s for s in generate_shifts(replace(data, exceptions=set()))
            if not s.special and s.id in data.exceptions]


@dataclass
class HistoryEntry:
    employee_id: str
    special_count: int = 0
    special_minutes: int = 0
    expected_count: Fraction = Fraction(0)
    expected_minutes: Fraction = Fraction(0)


@dataclass
class WishHistoryEntry:
    employee_id: str
    violated_keys: set[str] = field(default_factory=set)
    missing_months: list[str] = field(default_factory=list)

    @property
    def violations(self) -> int:
        return len(self.violated_keys)


@dataclass
class PlanResult:
    status: str
    assignments: list[Assignment] = field(default_factory=list)
    open_slots: dict[str, int] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    optimal_stages: list[bool] = field(default_factory=list)
    elapsed_seconds: float = 0
    stage_names: list[str] = field(default_factory=list)
    objective_values: list[int] = field(default_factory=list)
    improvements: int = 0


def default_shifts() -> list[ShiftType]:
    return [ShiftType("frueh", "Frühdienst", time(6), time(14)),
            ShiftType("spaet", "Spätdienst", time(14), time(22)),
            ShiftType("nacht", "Nachtdienst", time(22), time(6)),
            ShiftType("sonder", "Besonderer Dienst", time(8), time(20), weekday=2)]
