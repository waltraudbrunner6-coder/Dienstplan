"""V2-Katalog und Monatsereignisse; keine Wochenquoten oder Personen erfinden."""
import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .errors import DomainError
from .time import Interval, local_instant
from .work import WorkBlock


@dataclass(frozen=True, slots=True)
class Template:
    key: str
    code: str
    start: time | None
    end: time | None
    staff: int | None
    participation: str | None = None

    def on(self, day: date) -> Interval:
        if self.start is None or self.end is None:
            raise DomainError("Diese Vorlage benötigt konkrete Zeitangaben.")
        end_day = day + timedelta(days=int(self.end <= self.start))
        return Interval(local_instant(datetime.combine(day, self.start)),
                        local_instant(datetime.combine(end_day, self.end)))


CATALOG = (
    Template("T","T",time(14,30),time(17,30),None,"T"),
    Template("KC10","KC10",time(10,15),time(16,15),1),
    Template("KCT10","KCT10",time(10,15),time(17,30),1,"T"),
    Template("KC16","KC16",time(16),time(0),1),
    Template("KCT","KCT",time(14,30),time(0),1,"T"),
    Template("TS","TS",time(14,30),time(19,30),None,"TS"),
    Template("W17","W17",time(17),time(1),2),
    Template("TW","TW",time(14,30),time(0),2,"T"),
    Template("W16","W16",time(16),time(0),2),
    Template("WL","WL",time(18),time(2),2),
    Template("BK","BK",time(20),time(4),2),
    Template("VN","VN",time(10),time(12),1),
    Template("LB","LB",time(12),time(17,30),2,"T"),
    Template("LB_TS","LB",time(12),time(19,30),2,"TS"),
    Template("INT","INT",time(16),time(0),1),
    Template("N17","N17",time(17),time(1),1),
    Template("R_early","R",time(10,15),time(16,15),1),
    Template("R_late","R",time(16),time(0),1),
    Template("FK","FK",None,None,1),
)


def template(key: str) -> Template:
    for value in CATALOG:
        if value.key == key:
            return value
    raise DomainError(f"Unbekannte Dienstvorlage: {key}.")


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    service: Template
    attendance: Interval
    fixed_people: tuple[str, ...] = ()
    replacement_reason: str = ""

    def __post_init__(self):
        object.__setattr__(self, "fixed_people", tuple(self.fixed_people))
        if not self.id or len(set(self.fixed_people)) != len(self.fixed_people):
            raise DomainError("Termin benötigt Kennung und unterschiedliche feste Personen.")
        if self.fixed_people and len(self.fixed_people) != self.service.staff:
            raise DomainError("Feste Personenzahl passt nicht zur Besetzung.")
        if self.service.code in {"LB","VN","INT","N17","FK"} and len(self.fixed_people)!=self.service.staff:
            raise DomainError("Dieser Sondertermin benötigt alle festen Personen.")
        if any(not p for p in self.fixed_people):
            raise DomainError("Feste Personen benötigen Kennungen.")
        if self.service not in CATALOG:
            raise DomainError("Die Dienstvorlage ist nicht im bestätigten Katalog enthalten.")
        day=self.attendance.start_day
        if self.service.code!="FK" and self.attendance!=self.service.on(day):
            raise DomainError("Terminzeiten passen nicht zur Vorlage.")
        if self.service.code in {"T","TS","KCT10","KCT","TW","LB"} and day.weekday()!=3:
            raise DomainError("Diese Dienstvorlage gilt nur donnerstags.")
        if self.service.code in {"KC10","KC16","W17","W16"} and day.weekday()==3:
            raise DomainError("Donnerstags ist die Teamvariante erforderlich.")
        if self.service.code=="R" and not ((day.month==12 and day.day>=24) or (day.month==1 and day.day<=6)):
            raise DomainError("Reservedienste gelten ausschließlich vom 24.12. bis 06.01.")
        if self.service.code == "W16" and not self.replacement_reason.strip():
            raise DomainError("W16 benötigt eine dokumentierte Ersatzbegründung.")

    @property
    def protected(self) -> tuple[Interval, ...]:
        if not self.service.participation:
            return ()
        return (template(self.service.participation).on(self.attendance.start_day),)

    @property
    def coverage_id(self) -> str:
        return (f"{self.attendance.start_day}/outside" if self.service.code in {"W17","W16"} else self.id)

    def assign(self, person_id: str, breaks=(), *, reserve_profile: str | None = None) -> WorkBlock:
        if self.fixed_people and person_id not in self.fixed_people:
            raise DomainError("Diese Person entspricht nicht der festen Terminzuteilung.")
        if self.service.code == "R" and reserve_profile != "full_work_test":
            raise DomainError("Reservebewertung F02 fehlt; volle Arbeit nur mit ausdrücklich gewähltem Testprofil.")
        return WorkBlock(self.id,person_id,self.service.code,self.attendance,tuple(breaks),self.protected)


def event(key: str, day: date, *, people=(), reason="", attendance: Interval | None = None) -> Event:
    service = template(key)
    if key == "FK" and attendance is None:
        raise DomainError("FK benötigt konkrete Zeiten.")
    if key != "FK" and attendance is not None and attendance != service.on(day):
        raise DomainError("Abweichende Zeiten benötigen eine ausdrücklich versionierte Vorlage.")
    if attendance is not None and attendance.start_day != day:
        raise DomainError("Termindatum passt nicht zum Startdatum.")
    return Event(f"{day.isoformat()}/{key}",service,attendance or service.on(day),tuple(people),reason)


@dataclass(frozen=True, slots=True)
class FixedTerm:
    key: str
    day: date
    people: tuple[str, ...]
    attendance: Interval | None = None

    def __post_init__(self):
        object.__setattr__(self,"people",tuple(self.people))
        if self.key not in {"VN","INT","N17","FK"}:
            raise DomainError("Dieser feste Sondertermin wird nicht unterstützt.")


@dataclass(frozen=True, slots=True)
class CalendarInput:
    ts_days: frozenset[date] = frozenset()
    lb_anchor: date | None = None
    lb_people: tuple[str, ...] = ()
    fixed: tuple[FixedTerm, ...] = ()
    w16_reasons: tuple[tuple[date,str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self,"ts_days",frozenset(self.ts_days))
        for field in ("lb_people","fixed","w16_reasons"):
            object.__setattr__(self,field,tuple(getattr(self,field)))
        if any(day.weekday()!=3 for day in self.ts_days):
            raise DomainError("TS-Termine müssen Donnerstage sein.")
        if self.lb_anchor is not None and self.lb_anchor.weekday()!=3:
            raise DomainError("Das LB-Referenzdatum muss ein Donnerstag sein.")
        if self.lb_people and (len(self.lb_people)!=2 or len(set(self.lb_people))!=2):
            raise DomainError("LB benötigt zwei unterschiedliche feste Personen.")
        if len(dict(self.w16_reasons))!=len(self.w16_reasons):
            raise DomainError("Doppelte W16-Vorgaben.")


@dataclass(frozen=True, slots=True)
class CalendarResult:
    events: tuple[Event, ...]
    missing: tuple[str, ...]


def month_calendar(year: int, month: int, settings: CalendarInput) -> CalendarResult:
    days = [date(year,month,n) for n in range(1,calendar.monthrange(year,month)[1]+1)]
    events, missing = [], ["F06/F07: WL/BK-Wochenprofil fehlt; keine Wochenquote erzeugt."]
    changes = dict(settings.w16_reasons)
    if any(d not in days or d.weekday()==3 for d in changes):
        raise DomainError("W16 ersetzt nur einen W17-Termin des gewählten Monats.")
    for day in days:
        keys = ("KCT10","KCT","TW","TS" if day in settings.ts_days else "T") if day.weekday()==3 else ("KC10","KC16","W16" if day in changes else "W17")
        for key in keys:
            events.append(event(key,day,reason=changes.get(day,"")))
        if day.weekday()==3 and settings.lb_anchor is not None and settings.lb_people:
            delta=(day-settings.lb_anchor).days
            if delta>=0 and delta%14==0:
                events.append(event("LB_TS" if day in settings.ts_days else "LB",day,people=settings.lb_people))
        if (day.month==12 and day.day>=24) or (day.month==1 and day.day<=6):
            events.extend((event("R_early",day),event("R_late",day)))
    if settings.lb_anchor is None or not settings.lb_people:
        missing.append("F08: LB-Referenzdatum bzw. feste Personen fehlen.")
    for term in settings.fixed:
        if term.day not in days:
            raise DomainError("Sondertermin liegt außerhalb des gewählten Monats.")
        events.append(event(term.key,term.day,people=term.people,attendance=term.attendance))
    if len({e.id for e in events})!=len(events):
        raise DomainError("Ein Termin wurde mehrfach vorgegeben.")
    for code, count in (("INT",2),("N17",1)):
        if sum(e.service.code==code for e in events)!=count:
            missing.append(f"{code}: genau {count} feste Monatstermine benötigt.")
    missing.append("F09: FK-Wiederholungsprofil nicht festgelegt.")
    if any(e.service.code=="R" for e in events):
        missing.append("F02: Reservebewertung ungeklärt.")
    return CalendarResult(tuple(sorted(events,key=lambda e:(e.attendance.start,e.id))),tuple(missing))


def participation(block: WorkBlock, occasion: Event) -> str:
    """Eine Veranstaltung je Tag, keine Teilnahme allein aus Zeitüberschneidung."""
    if occasion.service.code not in {"T","TS"}:
        raise DomainError("Teilnahme wird nur für eine Teamveranstaltung geprüft.")
    day=occasion.attendance.start_day
    if block.code=="BK" and day in block.occupied_days:
        return "ausgenommen"
    if block.attendance.start_day!=day:
        return "fehlt"
    full_codes={"TS","LB"} if occasion.service.code=="TS" else {"T","KCT10","KCT","TW","LB"}
    required=occasion.attendance if block.code in full_codes else template("T").on(day)
    covered=sum(hit.minutes for part in block.work if (hit:=part.intersection(required)) is not None)==required.minutes
    if covered and block.code in full_codes:
        return "vollständig"
    if covered and occasion.service.code=="TS" and block.code in {"KCT10","KCT","TW"}:
        return "T erfüllt; TS-Ausnahme"
    return "fehlt"
