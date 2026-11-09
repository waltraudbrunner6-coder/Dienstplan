"""Expliziter JSON-Reader für lokale V2-Testarbeitsstände, keine Legacy-Umdeutung."""
from datetime import date,datetime
from fractions import Fraction

from .accounting import MonthAccount
from .calendar_rules import WeekPolicy,WeekQuota,WeekendPolicy
from .catalog import Event,template
from .contracts import Contract,Contracts,DateRange,Employment
from .entries import Entry
from .errors import DomainError
from .objectives import ObjectiveProfile
from .pauses import CoverageRule
from .people import Eligibility,Person
from .reporting import FairnessPolicy,ShareRow
from .serialization import fingerprint,plain
from .solver import PlanningInput,verify
from .time import IANA_VERSION,TZDATA_VERSION,Interval
from .wishes import WishHistory,WishPolicy
from .work import WorkBlock


def fraction(v):return Fraction(v['numerator'],v['denominator'])
def interval(v):return Interval(datetime.fromisoformat(v['start']),datetime.fromisoformat(v['end']))
def date_range(v):return DateRange(date.fromisoformat(v['start']),date.fromisoformat(v['end']))
def block(v):return WorkBlock(v['id'],v['person_id'],v['code'],interval(v['attendance']),tuple(map(interval,v['breaks'])),tuple(map(interval,v['protected'])))


def term(v):
    service=template(v['service']['key'])
    if plain(service)!=v['service']:raise DomainError('Gespeicherte Dienstvorlage stimmt nicht mit der Katalogversion überein.')
    return Event(v['id'],service,interval(v['attendance']),tuple(v['fixed_people']),v['replacement_reason'])


def planning_input(v):
    people=[]
    for p in v['people']:
        people.append(Person(p['id'],p['name'],Employment(p['id'],date_range(p['employment']['dates'])),
                             Contracts(p['id'],tuple(Contract(p['id'],date_range(c['dates']),fraction(c['weekly_hours'])) for c in p['contracts']['versions'])),
                             tuple(Eligibility(date_range(e['dates']),frozenset(e['codes']),e['driving_license']) for e in p['rights'])))
    absences=tuple(Entry(e['id'],e['person_id'],e['kind'],interval(e['span']),frozenset(date.fromisoformat(d) for d in e['credit_days']),e['comment'],e['budget_month']) for e in v['absences'])
    return PlanningInput(tuple(people),tuple(map(term,v['events'])),tuple(map(block,v['candidates'])),v['year'],v['month'],
            frozenset((pid,date.fromisoformat(d)) for pid,d in v['known_days']),WeekendPolicy(**v['weekend_policy']) if v['weekend_policy'] else None,
            v['profile_label'],absences,tuple(map(block,v['boundary'])),tuple(v['unchecked']),frozenset(v['optional_ids']),
            tuple(WeekQuota(q['id'],q['code'],date_range(q['dates']),q['required'],q['owner_month']) for q in v['quotas']),
            WeekPolicy(**v['week_policy']) if v['week_policy'] else None,tuple(CoverageRule(**r) for r in v['coverage']),tuple(map(block,v.get('locked',()))))


def objective_profile(v):
    values=dict(v)
    values['accounts']=tuple(MonthAccount(**a) for a in v['accounts'])
    values['wish_policy']=WishPolicy(**v['wish_policy']);values['fairness_policy']=FairnessPolicy(**v['fairness_policy'])
    values['history']=WishHistory(frozenset(tuple(k) for k in v['history']['violated']),tuple(v['history']['confirmation_ids']),tuple(v['history']['missing']))
    values['historical_shares']=tuple(ShareRow(r['person_id'],r['code'],r['count'],r['work_minutes'],fraction(r['expected_count']),fraction(r['expected_minutes'])) for r in v['historical_shares'])
    return ObjectiveProfile(**values)


def workspace(inputs,profile,blocks=(),events=None):
    blocks=tuple(blocks);events=None if events is None else tuple(events)
    if events is not None:
        core,calendar=verify(inputs,blocks,active_events=events)
        if not core.hard_ok or not calendar.hard_ok:raise DomainError('; '.join(i.message for i in core.issues+calendar.issues))
    snapshot=plain(dict(inputs=inputs,profile=profile,blocks=blocks,events=events,
                        versions=dict(tzdata=TZDATA_VERSION,iana=IANA_VERSION,catalog='v2-draft-1')))
    return dict(format='v2-workspace-1',revision_id=fingerprint(snapshot),snapshot=snapshot)


def restore_workspace(value):
    try:
        if value['format']!='v2-workspace-1' or fingerprint(value['snapshot'])!=value['revision_id']:
            raise DomainError('Unbekanntes oder beschädigtes V2-Arbeitsformat.')
        v=value['snapshot']
        if v['versions']!=dict(tzdata=TZDATA_VERSION,iana=IANA_VERSION,catalog='v2-draft-1'):
            raise DomainError('Zeit-/Katalogversion abweichend; keine stille Neubewertung eines gespeicherten Standes.')
        inputs=planning_input(v['inputs']);profile=objective_profile(v['profile'])
        blocks=tuple(map(block,v['blocks']));events=None if v['events'] is None else tuple(map(term,v['events']))
        workspace(inputs,profile,blocks,events)
        return inputs,profile,blocks,events
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:
        if isinstance(exc,DomainError):raise
        raise DomainError('V2-Arbeitsstand kann nicht gelesen werden: '+str(exc)) from exc
