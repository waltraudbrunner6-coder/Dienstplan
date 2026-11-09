"""Beschäftigung und exakte, zeitgültige Vertragswerte ohne Infrastruktur."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from .errors import DomainError
from .time import Interval, midnight


def exact_hours(value) -> Fraction:
    if isinstance(value, float) or isinstance(value, bool):
        raise DomainError("Wochenstunden als exakten Dezimaltext, Decimal oder Fraction angeben.")
    try:
        result = value if isinstance(value, Fraction) else Fraction(Decimal(str(value).replace(",", ".")))
    except (ValueError, InvalidOperation, OverflowError, ZeroDivisionError) as exc:
        raise DomainError("Wochenstunden müssen eine endliche, nicht negative Zahl sein.") from exc
    if result < 0:
        raise DomainError("Wochenstunden dürfen nicht negativ sein.")
    return result


@dataclass(frozen=True, slots=True)
class DateRange:
    """Start eingeschlossen, Ende ausgeschlossen."""
    start: date
    end: date

    def __post_init__(self):
        if type(self.start) is not date or type(self.end) is not date or self.end <= self.start:
            raise DomainError("Datumsbereich benötigt ein exklusives Ende nach seinem Start.")

    def includes(self, day: date) -> bool:
        return self.start <= day < self.end


@dataclass(frozen=True, slots=True)
class Employment:
    person_id: str
    dates: DateRange

    def __post_init__(self):
        if not self.person_id:
            raise DomainError("Die Beschäftigung benötigt eine stabile Personenkennung.")

    @classmethod
    def inclusive(cls, person_id: str, first: date, last: date):
        return cls(person_id, DateRange(first, last + timedelta(days=1)))

    def contains(self, span: Interval) -> bool:
        return midnight(self.dates.start) <= span.start and span.end <= midnight(self.dates.end)


@dataclass(frozen=True, slots=True)
class Contract:
    person_id: str
    dates: DateRange
    weekly_hours: Fraction

    def __post_init__(self):
        if not self.person_id:
            raise DomainError("Der Vertrag benötigt eine stabile Personenkennung.")
        object.__setattr__(self, "weekly_hours", exact_hours(self.weekly_hours))


@dataclass(frozen=True, slots=True)
class Contracts:
    person_id: str
    versions: tuple[Contract, ...]

    def __post_init__(self):
        versions = tuple(sorted(self.versions, key=lambda v: v.dates.start))
        object.__setattr__(self, "versions", versions)
        if not self.person_id or any(v.person_id != self.person_id for v in versions):
            raise DomainError("Alle Vertragsversionen müssen dieselbe Person referenzieren.")
        if any(a.dates.end > b.dates.start for a, b in zip(versions, versions[1:])):
            raise DomainError("Vertragsversionen dürfen sich nicht überlappen.")

    def at(self, day: date) -> Contract:
        for version in self.versions:
            if version.dates.includes(day):
                return version
        raise DomainError(f"Vertragslücke am {day.isoformat()} für {self.person_id}.")
