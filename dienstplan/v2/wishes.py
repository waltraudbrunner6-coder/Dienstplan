"""Relevante Wunschmengen und eingefrorene Historie, ohne Zielrang vorzugeben."""
from dataclasses import dataclass
from datetime import date,timedelta

from .errors import DomainError


@dataclass(frozen=True, slots=True)
class WishPolicy:
    label: str
    history_start: str
    weekend_friday_exception: bool
    small_groups: bool
    weekend_weight: int
    synthetic: bool = True

    def __post_init__(self):
        try:valid=date.fromisoformat(self.history_start+'-01')
        except (ValueError,TypeError) as exc:raise DomainError('Historienbeginn als YYYY-MM angeben.') from exc
        if not self.label or valid.strftime('%Y-%m')!=self.history_start:
            raise DomainError('Wunschprofil benötigt Bezeichnung und Historienbeginn.')
        if any(type(v) is not bool for v in (self.weekend_friday_exception,self.small_groups,self.synthetic)):
            raise DomainError('Wunschprofil benötigt ausdrückliche Ja/Nein-Entscheidungen.')
        if type(self.weekend_weight) is not int or self.weekend_weight<1:
            raise DomainError('Wochenendwunschgewicht muss eine positive ganze Zahl sein.')


@dataclass(frozen=True, slots=True)
class WishHistory:
    violated: frozenset[tuple] = frozenset()
    confirmation_ids: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self,'violated',frozenset(tuple(k) for k in self.violated))
        object.__setattr__(self,'confirmation_ids',tuple(self.confirmation_ids))
        object.__setattr__(self,'missing',tuple(self.missing))


@dataclass(frozen=True, slots=True)
class WishRow:
    person_id: str
    relevant: tuple[tuple, ...]
    violated: tuple[tuple, ...]
    historical: tuple[tuple, ...]
    cumulative: tuple[tuple, ...]

    @property
    def fulfilled_count(self):return len(self.relevant)-len(self.violated)


def relevant_wishes(entries,events):
    terms=tuple(events)
    unique={e.identity:e for e in entries if e.kind!='urlaub' and any(e.span.overlaps(t.attendance) for t in terms)}
    return tuple(unique[k] for k in sorted(unique))


def violated(wish,blocks,*,policy: WishPolicy):
    hits=[b for b in blocks if b.person_id==wish.person_id and b.attendance.overlaps(wish.span)]
    if wish.kind=='wochenendwunsch' and policy.weekend_friday_exception and hits:
        saturday=wish.span.start_day
        if all(b.code=='W17' and b.attendance.start_day==saturday-timedelta(days=1)
               and b.occupied_days<={saturday-timedelta(days=1),saturday} for b in hits):
            return False
    return bool(hits)


def wish_rows(people,entries,events,blocks,*,policy: WishPolicy,history=WishHistory()):
    relevant=relevant_wishes(entries,events);blocks=tuple(blocks);rows=[]
    for p in people:
        mine=tuple(e for e in relevant if e.person_id==p.id)
        current=frozenset(e.identity for e in mine if violated(e,blocks,policy=policy))
        past=frozenset(k for k in history.violated if k[0]==p.id)
        rows.append(WishRow(p.id,tuple(e.identity for e in mine),tuple(sorted(current)),
                            tuple(sorted(past)),tuple(sorted(past|current))))
    return tuple(rows)
