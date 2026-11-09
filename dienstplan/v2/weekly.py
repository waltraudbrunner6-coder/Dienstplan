"""Datumsoptionen, keine vorgezogene Personen- oder Wochentagsentscheidung."""
from dataclasses import dataclass

from .calendar_rules import dates, merge_quotas
from .catalog import event
from .errors import DomainError
from .validation import Issue


@dataclass(frozen=True, slots=True)
class WeeklyOptions:
    events: tuple
    rejected: tuple[Issue, ...]


def weekly_options(quotas, *, allowed_dates=None):
    terms = {}; rejected = []
    allowed = None if allowed_dates is None else {k: frozenset(v) for k, v in allowed_dates.items()}
    for quota in merge_quotas(quotas):
        if quota.code not in {'WL', 'BK'}:
            raise DomainError('Automatische Wochenoptionen unterstützen WL und BK.')
        if allowed is not None and quota.id not in allowed:
            raise DomainError(f'Datumsfilter für {quota.id} fehlt; nicht stillschweigend ergänzen.')
        for day in dates(quota.dates):
            if allowed is None or day in allowed[quota.id]:
                try:
                    term = event(quota.code, day)
                except DomainError as exc:
                    rejected.append(Issue('local_time', '', f'{day}/{quota.code}', str(exc)))
                    continue
                terms[term.id] = term
    return WeeklyOptions(tuple(terms[k] for k in sorted(terms)), tuple(rejected))
