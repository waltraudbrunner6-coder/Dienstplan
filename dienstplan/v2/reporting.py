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


def month_booking_description(month_profile):
    if month_profile=='M0':return 'M0: tatsächliche Arbeitszeit im jeweiligen Kalendermonat'
    if month_profile=='M1':return 'M1: gesamte bezahlte Dienstzeit im Monat des lokalen Dienstbeginns'
    raise DomainError('Unbekannte Monatsbuchung; M0 (Kalendermonat) oder M1 (Dienstbeginn) erforderlich.')


def booked_work_minutes(block,year,month,*,month_profile):
    """Buchungsmenge; physische Tages-/Nacht-/Feiertagsmengen bleiben unverändert."""
    month_booking_description(month_profile)
    date(year,month,1)  # Auch für M1 ungültige Monatsangaben nicht still akzeptieren.
    if month_profile=='M1':
        return block.work_minutes if (block.attendance.start_day.year,block.attendance.start_day.month)==(year,month) else 0
    return sum(q.work_minutes for q in quantities(block) if (q.day.year,q.day.month)==(year,month))


def hours_rows(people,blocks,entries,year,month,*,accounts,target_profile,month_profile):
    if target_profile!='S0':raise DomainError('Diese Sollrechnung benötigt ausdrücklich das Profil S0.')
    month_booking_description(month_profile)
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
        work=sum(booked_work_minutes(b,year,month,month_profile=month_profile) for b in blocks if b.person_id==p.id)
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


def required_work_range(events,blocks,year,month,*,boundary=(),include_reserve=False):
    """Operativer Monatsbedarf; noch freie Pausen über Monatsgrenzen als Bandbreite.

    Freiwillige T/TS-Teilnahme ist ausgenommen. R zählt bei ausdrücklich gesetztem
    include_reserve=True als normaler Dienst; False erhält die frühere API-Semantik.
    Bereits bekannte, hineinragende Randdienste werden einmal berücksichtigt.
    """
    events=tuple(events);blocks=tuple(blocks)
    span=Interval(midnight(date(year,month,1)),midnight(date(year+int(month==12),month%12+1,1)))
    minimum=maximum=0;event_ids={e.id for e in events}
    for term in events:
        if term.service.staff is None or (term.service.code=='R' and not include_reserve):continue
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
        if b.id in event_ids or b.code in {'T','TS'} or (b.code=='R' and not include_reserve) or (b.id,b.person_id) in seen:continue
        seen.add((b.id,b.person_id))
        value=sum(hit.minutes for part in b.work if (hit:=part.intersection(span)) is not None)
        minimum+=value;maximum+=value
    return minimum,maximum


def booked_required_work_range(events,blocks,year,month,*,month_profile,boundary=(),include_reserve=True):
    """Mitarbeiterstundenbedarf passend zur expliziten Monatsbuchung.

    M0 bleibt kalendarisch geteilt, M1 bucht Dienste vollständig beim Beginn.
    Nicht zugeteilte normale Dienste verwenden die enthaltene Standardpause;
    konkrete übersteuerte Pausen zugeteilter Dienste verwenden deren echte Dauer.
    """
    month_booking_description(month_profile)
    date(year,month,1)
    events,blocks,boundary=tuple(events),tuple(blocks),tuple(boundary)
    if month_profile=='M0':
        return required_work_range(events,blocks,year,month,boundary=boundary,include_reserve=include_reserve)
    event_ids={e.id for e in events};total=0
    for term in events:
        if term.service.staff is None or (term.service.code=='R' and not include_reserve):continue
        if (term.attendance.start_day.year,term.attendance.start_day.month)!=(year,month):continue
        selected={}
        for block in blocks:
            if block.id!=term.id:continue
            prior=selected.get(block.person_id)
            if prior is not None and prior!=block:raise DomainError('Widersprüchliche Versionen desselben Dienstes im Monatsbedarf.')
            selected[block.person_id]=block
        total+=sum(booked_work_minutes(b,year,month,month_profile=month_profile) for b in selected.values())
        paid=term.attendance.minutes-(30 if term.attendance.minutes>360 else 0)
        total+=max(0,term.service.staff-len(selected))*paid
    seen={}
    for block in boundary:
        if block.id in event_ids or block.code in {'T','TS'} or (block.code=='R' and not include_reserve):continue
        key=block.id,block.person_id
        prior=seen.get(key)
        if prior is not None:
            if prior!=block:raise DomainError('Widersprüchliche Randdienste im Monatsbedarf.')
            continue
        seen[key]=block
        total+=booked_work_minutes(block,year,month,month_profile=month_profile)
    return total,total
