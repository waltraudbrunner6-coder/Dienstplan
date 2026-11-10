"""Zeitgültige Rechte; Wochenstunden verleihen keine Qualifikation."""
from dataclasses import dataclass

from .contracts import DateRange, Employment, Contracts
from .errors import DomainError
from .time import Interval, day_segments

OUTSIDE_CODES=frozenset({"W17","W16","BK","WL","N17","TW","T","TS"})


@dataclass(frozen=True, slots=True)
class Eligibility:
    dates: DateRange
    codes: frozenset[str]
    driving_license: bool | None = None

    def __post_init__(self):
        object.__setattr__(self,"codes",frozenset(self.codes))

    @property
    def excluded_codes(self) -> frozenset[str]:
        from .catalog import CATALOG
        return frozenset(t.code for t in CATALOG) - self.codes

    @classmethod
    def from_exclusions(cls, dates, excluded_codes=(), driving_license=None):
        from .catalog import CATALOG
        codes = frozenset(t.code for t in CATALOG)
        excluded = frozenset(excluded_codes)
        if not excluded <= codes:
            raise DomainError('Unbekannte ausgeschlossene Dienste: ' + ', '.join(sorted(excluded - codes)))
        return cls(dates, codes - excluded, driving_license)


@dataclass(frozen=True, slots=True)
class Person:
    id: str
    name: str
    employment: Employment
    contracts: Contracts
    rights: tuple[Eligibility, ...]

    def __post_init__(self):
        object.__setattr__(self,"rights",tuple(sorted(self.rights,key=lambda r:r.dates.start)))
        if not self.id or not self.name.strip() or self.employment.person_id!=self.id or self.contracts.person_id!=self.id:
            raise DomainError("Person, Beschäftigung und Verträge benötigen dieselbe stabile Kennung.")
        if any(a.dates.end>b.dates.start for a,b in zip(self.rights,self.rights[1:])):
            raise DomainError("Zeitgültige Berechtigungen dürfen sich nicht überlappen.")

    def eligibility_errors(self, code: str, span: Interval) -> tuple[str, ...]:
        errors=[]
        if not self.employment.contains(span):
            errors.append("Dienst liegt außerhalb der Beschäftigung.")
        for day,_ in day_segments(span):
            valid=[r for r in self.rights if r.dates.includes(day)]
            if not valid or code not in valid[0].codes:
                errors.append(f"Keine Dienstberechtigung für {code} am {day}.")
            elif code=="N17" and valid[0].driving_license is not True:
                errors.append(f"N17 benötigt einen bestätigten Führerschein am {day}.")
        return tuple(dict.fromkeys(errors))
