"""Reine Rohbeträge und Salden, ohne implizite Rechts-/Tarifprofile."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction

from .contracts import Contracts, Employment
from .errors import DomainError


def round_minutes(value: Fraction) -> int:
    value = Fraction(value)
    sign = -1 if value < 0 else 1
    value = abs(value)
    return sign * ((2 * value.numerator + value.denominator) // (2 * value.denominator))


@dataclass(frozen=True, slots=True)
class MonthlyAmount:
    month: str
    raw_minutes: Fraction
    profile: str

    def __post_init__(self):
        if isinstance(self.raw_minutes, float) or not self.profile:
            raise DomainError("Monatsbeträge benötigen exakte Rohminuten und eine Profilbezeichnung.")
        object.__setattr__(self, "raw_minutes", Fraction(self.raw_minutes))

    @property
    def minutes(self) -> int:
        return round_minutes(self.raw_minutes)


def _same_person(contracts, employment):
    if contracts.person_id != employment.person_id:
        raise DomainError("Vertrag und Beschäftigung müssen dieselbe Person betreffen.")


def s0_target(contracts: Contracts, employment: Employment, year: int, month: int, *, profile: str) -> MonthlyAmount:
    if profile != "S0":
        raise DomainError("Nur das ausdrücklich gewählte technische Testprofil S0 ist hier verfügbar.")
    _same_person(contracts, employment)
    raw = Fraction(0)
    for number in range(1, calendar.monthrange(year, month)[1] + 1):
        day = date(year, month, number)
        if employment.dates.includes(day):
            raw += contracts.at(day).weekly_hours * 60 / 7
    return MonthlyAmount(f"{year:04d}-{month:02d}", raw, "S0 – technisches Testprofil")


def leave_credits(contracts: Contracts, employment: Employment, credit_days) -> tuple[MonthlyAmount, ...]:
    """Nur explizite Tage; doppelte Tage zählen einmal, Summierung vor Rundung."""
    _same_person(contracts, employment)
    totals = {}
    for day in sorted(frozenset(credit_days)):
        if type(day) is not date:
            raise DomainError("Gutschrifttage müssen eindeutige Kalenderdaten sein.")
        if not employment.dates.includes(day):
            raise DomainError(f"Urlaubsgutschrift {day} liegt außerhalb der Beschäftigung.")
        key = day.strftime("%Y-%m")
        totals[key] = totals.get(key, Fraction(0)) + contracts.at(day).weekly_hours * 60 / 5
    return tuple(MonthlyAmount(k, v, "Urlaub: explizite Tage × gültiges W/5") for k, v in sorted(totals.items()))


@dataclass(frozen=True, slots=True)
class WorkGoal:
    raw_minutes: int

    @property
    def minimum_nonnegative(self) -> int:
        return max(0, self.raw_minutes)

    @property
    def overcoverage_minutes(self) -> int:
        return max(0, -self.raw_minutes)


@dataclass(frozen=True, slots=True)
class MonthAccount:
    person_id: str
    opening_minutes: int
    desired_minutes: int = 0

    def __post_init__(self):
        if not self.person_id or any(type(v) is not int for v in (self.opening_minutes, self.desired_minutes)):
            raise DomainError("Monatskonto benötigt Person und ganzzahlige Minutensalden.")

    def goal(self, target_minutes: int, credits_minutes: int) -> WorkGoal:
        _nonnegative(target_minutes, credits_minutes)
        return WorkGoal(target_minutes + self.desired_minutes - self.opening_minutes - credits_minutes)

    def projected(self, target_minutes: int, work_minutes: int, credits_minutes: int) -> int:
        _nonnegative(target_minutes, work_minutes, credits_minutes)
        return self.opening_minutes + work_minutes + credits_minutes - target_minutes


def _nonnegative(*values):
    if any(type(v) is not int or v < 0 for v in values):
        raise DomainError("Soll, Arbeit und Gutschriften müssen nicht negative ganze Minuten sein.")
