"""Wochenend-/Randprüfung und ausdrücklich parametrisierte Wochenquoten."""
import calendar
from dataclasses import dataclass
from datetime import date,timedelta

from .contracts import DateRange
from .errors import DomainError
from .validation import Issue


def dates(span: DateRange):
    return tuple(span.start+timedelta(days=i) for i in range((span.end-span.start).days))


def horizon(year: int,month: int) -> DateRange:
    first=date(year,month,1);last=date(year,month,calendar.monthrange(year,month)[1])
    return DateRange(first-timedelta(days=first.weekday()+7),last+timedelta(days=14-last.weekday()))


@dataclass(frozen=True, slots=True)
class WeekendPolicy:
    owner: str
    label: str
    partial_quota: int | None = None
    synthetic: bool = True
    partial_membership: str | None = None

    def __post_init__(self):
        if self.owner not in {'saturday','sunday'} or not self.label:
            raise DomainError("Wochenendprofil benötigt expliziten Besitzer und Profilbezeichnung.")
        if self.partial_quota is not None and (type(self.partial_quota) is not int or self.partial_quota<0):
            raise DomainError("Teilmonatsquote muss ausdrücklich nicht negativ sein.")
        if self.partial_membership not in {None,'fully_employed','overlap_employment'}:
            raise DomainError("Unbekannte Teilwochenend-Zuordnung.")


def weekend_free(blocks,person_id,saturday,known_days) -> bool | None:
    sunday=saturday+timedelta(days=1)
    touched=[b for b in blocks if b.person_id==person_id and b.occupied_days&{saturday,sunday}]
    for b in touched:
        if (sunday in b.occupied_days or b.code!='W17' or b.attendance.start_day!=saturday-timedelta(days=1)):
            return False
    # Beobachtete Arbeit beweist nicht, dass daneben keine weitere Arbeit existiert.
    if not {(person_id,saturday),(person_id,sunday)}<=known_days:return None
    return True


@dataclass(frozen=True, slots=True)
class CalendarReport:
    issues: tuple[Issue, ...]
    unchecked: tuple[str, ...]
    free_weekends: tuple[tuple[str,int], ...]

    @property
    def hard_ok(self):return not self.issues

    @property
    def fully_checked(self):return not self.unchecked


def check_calendar(people,blocks,year,month,*,known_days,policy: WeekendPolicy | None) -> CalendarReport:
    blocks=tuple(blocks);known=frozenset(known_days)
    window=horizon(year,month);days=dates(window)
    issues=[];unchecked=[];counts=[]
    for p in people:
        mine=[b for b in blocks if b.person_id==p.id]
        occupied=set().union(*(b.occupied_days for b in mine)) if mine else set()
        current_days=set().union(*(b.occupied_days for b in mine if (b.attendance.start_day.year,b.attendance.start_day.month)==(year,month)))
        required={d for d in days if p.employment.dates.includes(d)}
        missing={d for d in required if (p.id,d) not in known}
        if missing:unchecked.append(f'Randdaten {p.id}: {min(missing)} bis {max(missing)} nicht vollständig bekannt.')
        def state(day):
            if day in occupied:return 'work'
            if (p.id,day) in known or not p.employment.dates.includes(day):return 'free'
            return 'unknown'
        # Jede beobachtete Wochenendarbeit benötigt das unmittelbar vorige Freipaar,
        # auch wenn Freitags-W17 für die Monatsquote ausnahmsweise frei zählt.
        for saturday in (d for d in days if d.weekday()==5):
            sunday=saturday+timedelta(days=1)
            if not occupied&{saturday,sunday}:continue
            previous=[saturday-timedelta(days=5-i) for i in range(5)]
            if not current_days&set(previous+[saturday,sunday]):continue
            values=[state(d) for d in previous]
            if not any(values[i]==values[i+1]=='free' for i in range(4)):
                if 'unknown' in values:
                    unchecked.append(f'Vorwochen-Freipaar {p.id} vor {saturday}: notwendige Randdaten fehlen.')
                else:
                    issues.append(Issue('preceding_free_pair',p.id,'',f'Vor {saturday}/{sunday} fehlen zwei zusammenhängende vollständig freie Tage im unmittelbar vorherigen Montag–Freitag.'))
        if policy is None:
            unchecked.append(f'F10: Wochenend-Zählprofil für {p.id} fehlt.');continue
        selected=[]
        for saturday in (d for d in days if d.weekday()==5):
            owner=saturday if policy.owner=='saturday' else saturday+timedelta(days=1)
            if (owner.year,owner.month)==(year,month):selected.append(saturday)
        full=p.employment.dates.start<=date(year,month,1) and p.employment.dates.end>date(year,month,calendar.monthrange(year,month)[1])
        quota=2 if full else policy.partial_quota
        if quota is None:
            unchecked.append(f'F10: Teilmonatsquote für {p.id} fehlt.');continue
        partial_weekend=any(not (p.employment.dates.includes(d) and p.employment.dates.includes(d+timedelta(days=1))) for d in selected)
        if partial_weekend and policy.partial_membership is None:
            unchecked.append(f'F10: Zuordnung aktiver Teilwochenenden für {p.id} fehlt.');continue
        if policy.partial_membership=='fully_employed':
            selected=[d for d in selected if p.employment.dates.includes(d) and p.employment.dates.includes(d+timedelta(days=1))]
        elif policy.partial_membership=='overlap_employment':
            selected=[d for d in selected if p.employment.dates.includes(d) or p.employment.dates.includes(d+timedelta(days=1))]
        statuses=[weekend_free(blocks,p.id,d,known) for d in selected]
        count=sum(s is True for s in statuses);counts.append((p.id,count))
        if count<quota:
            if count+sum(s is None for s in statuses)<quota:
                issues.append(Issue('free_weekends',p.id,'',f'Nur {count} nachgewiesene freie Wochenenden; benötigt {quota}.'))
            else:unchecked.append(f'Freie Wochenenden {p.id}: wegen Randdaten nicht nachgewiesen.')
    return CalendarReport(tuple(issues),tuple(dict.fromkeys(unchecked)),tuple(counts))


@dataclass(frozen=True, slots=True)
class WeekPolicy:
    anchor: str
    exclusion: str
    label: str
    synthetic: bool = True

    def __post_init__(self):
        if self.anchor not in {'week_start','week_end'} or self.exclusion not in {'start_day','overlap','both'} or not self.label:
            raise DomainError("Wochenprofil benötigt Bezugsanker, Ausschlussgrenze und Bezeichnung.")


@dataclass(frozen=True, slots=True)
class WeekQuota:
    id: str
    code: str
    dates: DateRange
    required: int
    owner_month: str

    def __post_init__(self):
        if not self.id or self.code not in {'WL','BK'} or type(self.required) is not int or self.required<0:
            raise DomainError('Wochenquote benötigt Kennung, WL/BK und nicht negative ganze Terminzahl.')
        if self.required>(self.dates.end-self.dates.start).days:
            raise DomainError('Mehr verschiedene Wochentermine als zulässige Kalendertage.')


def week_quotas(year,month,*,policy: WeekPolicy) -> tuple[WeekQuota, ...]:
    first=date(year,month,1);last=date(year,month,calendar.monthrange(year,month)[1])
    monday=first-timedelta(days=first.weekday());result=[]
    while monday<=last:
        end=monday+timedelta(days=7);anchor=monday if policy.anchor=='week_start' else end-timedelta(days=1)
        iso=monday.isocalendar();owner=anchor.strftime('%Y-%m')
        for code,count in (('WL',2 if anchor.month in (12,1) else 1),('BK',1)):
            result.append(WeekQuota(f'{iso.year}-W{iso.week:02d}/{code}',code,DateRange(monday,end),count,owner))
        monday=end
    return tuple(result)


def merge_quotas(*groups):
    values={}
    for group in groups:
        for q in group:
            if q.id in values and values[q.id]!=q:raise DomainError("Widersprüchliche Randwochenprofile für dieselbe Quoten-ID.")
            values[q.id]=q
    return tuple(values[k] for k in sorted(values))


def extra_events_conflict(a,b,policy):
    if {a.service.code,b.service.code}!={'WL','BK'}:return False
    same=a.attendance.start_day==b.attendance.start_day
    overlap=a.attendance.overlaps(b.attendance)
    return same if policy.exclusion=='start_day' else overlap if policy.exclusion=='overlap' else same or overlap


def check_quotas(quotas,events,*,policy: WeekPolicy):
    issues=[];events=tuple(events)
    for q in quotas:
        chosen=[e for e in events if e.service.code==q.code and q.dates.includes(e.attendance.start_day)]
        count=len({e.attendance.start_day for e in chosen})
        if count!=q.required or len(chosen)!=count:
            issues.append(Issue('weekly_quota','',q.id,f'{q.code}: {count} verschiedene Termine; benötigt {q.required}, keine doppelten WL-Tage.'))
    for i,a in enumerate(events):
        for b in events[i+1:]:
            if extra_events_conflict(a,b,policy):issues.append(Issue('wl_bk_exclusion','',a.id,f'WL/BK-Konflikt mit {b.id}.'))
    return tuple(issues)
