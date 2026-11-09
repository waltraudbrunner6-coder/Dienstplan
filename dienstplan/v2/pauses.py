"""Konkrete Pausen- und Abdeckungsvarianten nur aus expliziten Profilangaben."""
from dataclasses import dataclass
from datetime import timedelta

from .errors import DomainError
from .time import Interval
from .validation import Issue


@dataclass(frozen=True, slots=True)
class PausePolicy:
    label: str
    windows: tuple[Interval, ...]
    step_minutes: int
    synthetic: bool = True

    def __post_init__(self):
        object.__setattr__(self, 'windows', tuple(self.windows))
        if not self.label or type(self.step_minutes) is not int or self.step_minutes < 1:
            raise DomainError('Pausenprofil benötigt Bezeichnung und positive Minutenauflösung.')


def pause_candidates(term, person_id, *, policy: PausePolicy, reserve_profile=None):
    if term.attendance.minutes <= 360:
        return (term.assign(person_id, reserve_profile=reserve_profile),)
    choices = set()
    for window in policy.windows:
        if not term.attendance.contains(window):
            raise DomainError('Das Pausenfenster liegt außerhalb des Dienstes.')
        start = window.start
        while start + timedelta(minutes=30) <= window.end:
            pause = Interval(start, start + timedelta(minutes=30))
            if not any(pause.overlaps(w) for w in term.protected):
                choices.add(term.assign(person_id, (pause,), reserve_profile=reserve_profile))
            start += timedelta(minutes=policy.step_minutes)
    return tuple(sorted(choices, key=lambda b: b.breaks[0].start))


@dataclass(frozen=True, slots=True)
class CoverageRule:
    event_id: str
    minimum_working: int
    label: str
    relief_event_ids: tuple[str, ...] = ()
    synthetic: bool = True

    def __post_init__(self):
        object.__setattr__(self, 'relief_event_ids', tuple(self.relief_event_ids))
        if (not self.event_id or not self.label or type(self.minimum_working) is not int
                or self.minimum_working < 1 or self.event_id in self.relief_event_ids
                or len(set(self.relief_event_ids)) != len(self.relief_event_ids)):
            raise DomainError('Abdeckungsprofil benötigt eindeutige Rollen, Mindestzahl und Bezeichnung.')


def coverage_segments(term, blocks):
    points = {term.attendance.start, term.attendance.end}
    for block in blocks:
        for part in block.work:
            hit = part.intersection(term.attendance)
            if hit is not None:
                points.update((hit.start, hit.end))
    ordered = sorted(points)
    return tuple(Interval(a, b) for a, b in zip(ordered, ordered[1:]))


def check_coverage(events, blocks, rules):
    terms = {e.id: e for e in events}
    blocks = tuple(blocks)
    issues = []
    for rule in rules:
        term = terms.get(rule.event_id)
        if term is None:
            continue  # Nicht gewählter optionaler Termin hat keinen Bedarf.
        selected = [b for b in blocks if b.id == term.id]
        missing = term.service.staff - len({b.person_id for b in selected})
        # Im offenen Entwurf wird je offenem Platz auch ein fehlender Arbeiter
        # ausgewiesen. Erst Vollbesetzung belegt die volle Mindestabdeckung.
        required = max(0, rule.minimum_working - missing)
        support = [b for b in blocks if b.id in (term.id,) + rule.relief_event_ids]
        for segment in coverage_segments(term, support):
            working = {b.person_id for b in support if any(p.contains(segment) for p in b.work)}
            if len(working) < required:
                issues.append(Issue('working_coverage', '', term.id,
                                    f'{segment.start.isoformat()} bis {segment.end.isoformat()}: '
                                    f'{len(working)} tatsächlich arbeitend; benötigt {required} '
                                    f'bei {missing} offenem Platz. Profil: {rule.label}.'))
    return tuple(issues)
