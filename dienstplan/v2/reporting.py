"""Exakte Prognosemengen und Sollanteile; keine implizite Tarif-/Sollwahl."""
from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from .accounting import MonthAccount,leave_credits,s0_target
from .errors import DomainError
from .work import quantities
from .time import Interval,midnight


@dataclass(frozen=True, slots=True)
class HoursRow:
    person_id: str
    target: int
    opening: int
    desired: int
    credits: int
    goal: int
    work: int
    projected: int
    deviation: int
    raw_target: Fraction
    raw_credits: Fraction
    credits_known: bool = True


def hours_rows(people,blocks,entries,year,month,*,accounts,target_profile,month_profile):
    if target_profile!='S0' or month_profile!='M0':
        raise DomainError('Diese Rechenfunktion benötigt ausdrücklich S0 und M0 als Testprofile.')
    people=tuple(people);entries=tuple(entries);accounts=tuple(accounts)
    unique={}
    for b in blocks:
        key=b.id,b.person_id
        if key in unique and unique[key]!=b:raise DomainError('Widersprüchliche Versionen desselben Dienstes in der Stundenrechnung.')
        unique[key]=b
    blocks=tuple(unique.values())
    account_map={a.person_id:a for a in accounts}
    if len(account_map)!=len(accounts) or set(account_map)!={p.id for p in people}:
        raise DomainError('Für jede Person genau ein ausdrückliches Monatskonto angeben.')
    rows=[];key=f'{year:04d}-{month:02d}'
    month_span=Interval(midnight(date(year,month,1)),midnight(date(year+int(month==12),month%12+1,1)))
    for p in people:
        account=account_map[p.id];target=s0_target(p.contracts,p.employment,year,month,profile=target_profile)
        credit_days=frozenset(d for e in entries if e.person_id==p.id and e.kind=='urlaub' for d in e.credit_days)
        credits=next((v for v in leave_credits(p.contracts,p.employment,credit_days) if v.month==key),None)
        raw_g=credits.raw_minutes if credits else Fraction(0);g=credits.minutes if credits else 0
        work=sum(q.work_minutes for b in blocks if b.person_id==p.id for q in quantities(b) if (q.day.year,q.day.month)==(year,month))
        goal=account.goal(target.minutes,g).raw_minutes
        known=not any(e.person_id==p.id and e.kind=='urlaub' and not e.credit_days and e.span.overlaps(month_span) for e in entries)
        rows.append(HoursRow(p.id,target.minutes,account.opening_minutes,account.desired_minutes,g,goal,work,
                             account.projected(target.minutes,work,g),work-goal,target.raw_minutes,raw_g,known))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class FairnessPolicy:
    label: str
    mode: str
    synthetic: bool = True

    def __post_init__(self):
        if not self.label or self.mode not in {'absolute','contract'}:
            raise DomainError('Fairness benötigt benanntes absolutes oder Vertragsstundenprofil.')


@dataclass(frozen=True, slots=True)
class ShareRow:
    person_id: str
    code: str
    count: int
    work_minutes: int
    expected_count: Fraction
    expected_minutes: Fraction


def shares(people,events,blocks,*,policy: FairnessPolicy,absences=()):
    people=tuple(people);events=tuple(events);blocks=tuple(blocks);expected={}
    for e in events:
        if e.service.staff is None:continue
        eligible=[p for p in people if not p.eligibility_errors(e.service.code,e.attendance)
                  and (not e.fixed_people or p.id in e.fixed_people)
                  and not any(a.kind=='urlaub' and a.person_id==p.id and a.span.overlaps(e.attendance) for a in absences)]
        weights={p.id:(Fraction(1) if policy.mode=='absolute' else p.contracts.at(e.attendance.start_day).weekly_hours) for p in eligible}
        total=sum(weights.values(),Fraction(0))
        # Nullstunden erzeugen keinen erfundenen Vertragsanteil. Ein absoluter
        # Vergleich kann stattdessen ausdrücklich ausgewählt werden.
        for pid,weight in weights.items():
            count=Fraction(e.service.staff)*weight/total if total else Fraction(0)
            work=e.attendance.minutes-(30 if e.attendance.minutes>360 else 0)
            key=pid,e.service.code;old=expected.get(key,(Fraction(0),Fraction(0)))
            expected[key]=(old[0]+count,old[1]+count*work)
    codes=sorted({e.service.code for e in events if e.service.staff is not None})
    return tuple(ShareRow(p.id,code,sum(b.person_id==p.id and b.code==code for b in blocks),
                           sum(b.work_minutes for b in blocks if b.person_id==p.id and b.code==code),
                           *expected.get((p.id,code),(Fraction(0),Fraction(0)))) for p in people for code in codes)


@dataclass(frozen=True, slots=True)
class QuantityRow:
    person_id: str
    day: object
    work_minutes: int
    night_minutes: int
    sunday_minutes: int
    holiday_minutes: int


def quantity_rows(blocks,holidays=frozenset()):
    totals={}
    for b in blocks:
        for q in quantities(b,holidays):
            key=b.person_id,q.day;values=totals.setdefault(key,[0,0,0,0])
            for i,n in enumerate((q.work_minutes,q.night_minutes,q.sunday_minutes,q.holiday_minutes)):values[i]+=n
    return tuple(QuantityRow(*key,*values) for key,values in sorted(totals.items()))


def required_work_range(events,blocks,year,month,*,boundary=()):
    """Operativer Monatsbedarf; noch freie Pausen über Monatsgrenzen als Bandbreite.

    Freiwillige T/TS-Teilnahme und ungeklärte Reservebewertung sind ausgenommen.
    Bereits bekannte, hineinragende Randdienste werden einmal berücksichtigt.
    """
    events=tuple(events);blocks=tuple(blocks)
    span=Interval(midnight(date(year,month,1)),midnight(date(year+int(month==12),month%12+1,1)))
    minimum=maximum=0;event_ids={e.id for e in events}
    for term in events:
        if term.service.staff is None or term.service.code=='R':continue
        assigned={b.person_id:b for b in blocks if b.id==term.id}
        known=sum(hit.minutes for b in assigned.values() for part in b.work if (hit:=part.intersection(span)) is not None)
        minimum+=known;maximum+=known
        hit=term.attendance.intersection(span)
        inside=hit.minutes if hit else 0
        pause=30 if term.attendance.minutes>360 else 0
        if inside==term.attendance.minutes:low=high=inside-pause
        elif inside==0:low=high=0
        else:
            outside=max((p.minutes for p in term.attendance.difference((span,))),default=0)
            low=max(0,inside-min(pause,inside));high=inside-max(0,pause-outside)
        missing=max(0,term.service.staff-len(assigned))
        minimum+=missing*low;maximum+=missing*high
    seen=set()
    for b in boundary:
        if b.id in event_ids or b.code in {'R','T','TS'} or (b.id,b.person_id) in seen:continue
        seen.add((b.id,b.person_id))
        value=sum(hit.minutes for part in b.work if (hit:=part.intersection(span)) is not None)
        minimum+=value;maximum+=value
    return minimum,maximum
