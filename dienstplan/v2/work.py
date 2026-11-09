"""Konkrete Dienstanwesenheit, reale Pausen und physische Zeitmengen."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .errors import DomainError
from .time import Interval, day_segments, local_instant, midnight


@dataclass(frozen=True, slots=True)
class WorkBlock:
    id: str
    person_id: str
    code: str
    attendance: Interval
    breaks: tuple[Interval, ...] = ()
    protected: tuple[Interval, ...] = ()

    def __post_init__(self):
        if not self.id or not self.person_id or not self.code:
            raise DomainError("Ein Dienst benötigt Kennung, Person und Dienstkürzel.")
        pauses = tuple(sorted(self.breaks, key=lambda x: x.start))
        object.__setattr__(self, "breaks", pauses)
        object.__setattr__(self, "protected", tuple(self.protected))
        if any(not self.attendance.contains(p) for p in pauses):
            raise DomainError("Jede Pause muss vollständig innerhalb des Dienstblocks liegen.")
        if any(a.overlaps(b) for a, b in zip(pauses, pauses[1:])):
            raise DomainError("Pausen dürfen sich weder überlappen noch doppelt vorkommen.")
        if self.attendance.minutes > 360 and (len(pauses) != 1 or pauses[0].minutes != 30):
            raise DomainError("Ein Dienst über sechs Stunden benötigt genau eine enthaltene 30-Minuten-Pause.")
        for window in self.protected:
            if not self.attendance.contains(window) or any(p.overlaps(window) for p in pauses):
                raise DomainError("Das geschützte Zeitfenster muss vollständig als Arbeitszeit erhalten bleiben.")
        if self.work_minutes + sum(p.minutes for p in pauses) != self.attendance.minutes:
            raise DomainError("Arbeits- und Pausenabschnitte zerlegen den Dienst nicht vollständig.")

    @property
    def work(self) -> tuple[Interval, ...]:
        return self.attendance.difference(self.breaks)

    @property
    def work_minutes(self) -> int:
        return sum(p.minutes for p in self.work)

    @property
    def occupied_days(self) -> frozenset[date]:
        return frozenset(day for day, _ in day_segments(self.attendance))


@dataclass(frozen=True, slots=True)
class DayQuantities:
    day: date
    work_minutes: int
    night_minutes: int
    sunday_minutes: int
    holiday_minutes: int


def quantities(block: WorkBlock, holidays: frozenset[date] = frozenset()) -> tuple[DayQuantities, ...]:
    """Physische Mengen; weder Tarif noch Monatsabrechnungsprofil wird gewählt."""
    totals = {}
    for work in block.work:
        for day, part in day_segments(work):
            windows = (Interval(midnight(day), local_instant(datetime.combine(day, time(6)))),
                       Interval(local_instant(datetime.combine(day, time(22))), midnight(day + timedelta(days=1))))
            night = sum(hit.minutes for w in windows if (hit := part.intersection(w)) is not None)
            values = totals.setdefault(day, [0, 0, 0, 0])
            for i, value in enumerate((part.minutes, night, part.minutes if day.weekday() == 6 else 0,
                                       part.minutes if day in holidays else 0)):
                values[i] += value
    return tuple(DayQuantities(day, *values) for day, values in sorted(totals.items()))


def physical_months(block: WorkBlock) -> tuple[tuple[str, int], ...]:
    totals = {}
    for row in quantities(block):
        key = row.day.strftime("%Y-%m")
        totals[key] = totals.get(key, 0) + row.work_minutes
    return tuple(sorted(totals.items()))
