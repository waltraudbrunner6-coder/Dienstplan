"""Kleine vollständige technische Datensätze, ausdrücklich kein Betriebsmonat."""
from datetime import date

from .accounting import MonthAccount
from .calendar_rules import WeekendPolicy,dates,horizon
from .catalog import event
from .contracts import Contract,Contracts,DateRange,Employment
from .objectives import ObjectiveProfile
from .people import Eligibility,Person
from .reporting import FairnessPolicy
from .solver import PlanningInput
from .time import Interval
from .wishes import WishPolicy


def technical_demo(year=2026,month=11):
    span=DateRange(date(year,1,1),date(year+2,1,1))
    people=tuple(Person(chr(65+i),f'Testperson {i+1}',Employment(chr(65+i),span),
                        Contracts(chr(65+i),(Contract(chr(65+i),span,'25'),)),
                        (Eligibility(span,frozenset({'WL','BK','T','TS'}),True),)) for i in range(12))
    weekdays=[d for d in dates(DateRange(date(year,month,1),date(year+int(month==12),month%12+1,1))) if d.weekday() in (0,2)]
    terms=tuple(event('WL',d) for d in weekdays[:4])
    candidates=tuple(e.assign(p.id,(Interval.local(f'{e.attendance.start_day}T21:00',f'{e.attendance.start_day}T21:30'),)) for e in terms for p in people)
    known=frozenset((p.id,d) for p in people for d in dates(horizon(year,month)))
    inputs=PlanningInput(people,terms,candidates,year,month,known,WeekendPolicy('saturday','WE0 – Testprofil'),
                         'Synthetischer Vier-Termine-Test; kein vollständiger Betriebsmonat',unchecked=('Betriebliche Profile F01–F14 nicht freigegeben.',))
    profile=ObjectiveProfile('E0 – technisches Vergleichsprofil',('wishes','groups','burden','hours_max','hours_spread','shifts','late_break'),
                             tuple(MonthAccount(p.id,0) for p in people),WishPolicy('W0','2026-01',False,True,1),FairnessPolicy('F0','contract'))
    incumbent=tuple(c for c in candidates if c.person_id in {'A','B'})
    return inputs,profile,incumbent
