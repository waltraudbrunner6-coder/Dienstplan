"""Kleine V2-Machbarkeitsmodelle; keine produktive Profilfreigabe."""
from dataclasses import dataclass,replace
from datetime import timedelta
from math import isfinite
from threading import Event as StopEvent,Thread
from time import monotonic

from ortools.sat.python import cp_model

from .calendar_rules import check_calendar,check_quotas,extra_events_conflict
from .errors import DomainError
from .serialization import fingerprint
from .pauses import check_coverage,coverage_segments
from .time import rest_minutes,TZDATA_VERSION
from .validation import Issue,check_core


@dataclass(frozen=True, slots=True)
class PlanningInput:
    people: tuple
    events: tuple
    candidates: tuple
    year: int
    month: int
    known_days: frozenset
    weekend_policy: object | None
    profile_label: str
    absences: tuple = ()
    boundary: tuple = ()
    unchecked: tuple[str, ...] = ()
    optional_ids: frozenset[str] = frozenset()
    quotas: tuple = ()
    week_policy: object | None = None
    coverage: tuple = ()

    def __post_init__(self):
        if not self.profile_label:raise DomainError('Das Machbarkeitsmodell benötigt eine explizite Profilbezeichnung.')
        for key in ('people','events','absences','boundary'):
            object.__setattr__(self,key,tuple(sorted(getattr(self,key),key=lambda v:getattr(v,'id',repr(v)))))
        object.__setattr__(self,'candidates',tuple(sorted(set(self.candidates),key=lambda b:(b.id,b.person_id,tuple(p.start for p in b.breaks)))))
        object.__setattr__(self,'known_days',frozenset(self.known_days))
        object.__setattr__(self,'unchecked',tuple(self.unchecked))
        object.__setattr__(self,'optional_ids',frozenset(self.optional_ids))
        for key in ('quotas','coverage'):
            object.__setattr__(self,key,tuple(sorted(getattr(self,key),key=lambda v:getattr(v,'id',getattr(v,'event_id','')))))
        terms={e.id:e for e in self.events}
        if not self.optional_ids<=terms.keys():raise DomainError('Unbekannte optionale Terminkennung.')
        if self.quotas and self.week_policy is None:raise DomainError('Wochenquoten benötigen ein ausdrückliches Wochenprofil.')
        if len({q.id for q in self.quotas})!=len(self.quotas):raise DomainError('Doppelte Wochenquoten.')
        for key in self.optional_ids:
            e=terms[key]
            if e.service.code not in {'WL','BK'} or sum(q.code==e.service.code and q.dates.includes(e.attendance.start_day) for q in self.quotas)!=1:
                raise DomainError('Optionale WL/BK-Termine müssen genau einer Wochenquote zugeordnet sein.')
        if len({r.event_id for r in self.coverage})!=len(self.coverage):raise DomainError('Doppelte Abdeckungsprofile.')
        for rule in self.coverage:
            term=terms.get(rule.event_id)
            if term is None or term.service.staff is None or rule.minimum_working>term.service.staff:
                raise DomainError('Abdeckungsprofil passt nicht zum operativen Bedarf.')
            if not set(rule.relief_event_ids)<=terms.keys():raise DomainError('Unbekannter Vertretungstermin.')
        for i,a in enumerate(self.coverage):
            for b in self.coverage[i+1:]:
                roles_a={a.event_id,*a.relief_event_ids};roles_b={b.event_id,*b.relief_event_ids}
                if roles_a&roles_b and terms[a.event_id].attendance.overlaps(terms[b.event_id].attendance):
                    raise DomainError('Dieselbe Vertretungsrolle darf nicht zwei gleichzeitige Bedarfe decken.')

    @property
    def fingerprint(self):return fingerprint((TZDATA_VERSION,self))


@dataclass(frozen=True, slots=True)
class FeasibilityResult:
    status: str
    blocks: tuple
    open_slots: tuple
    issues: tuple
    unchecked: tuple[str, ...]
    coverage_optimal: bool
    elapsed_seconds: float
    input_fingerprint: str
    profile_label: str
    events: tuple = ()


def verify(inputs,blocks,*,check_fixed=True,active_events=None):
    blocks=tuple(blocks)
    if active_events is None:
        if inputs.optional_ids:raise DomainError('Optionale Planung benötigt die tatsächlich gewählten Termine.')
        active_events=inputs.events
    active_events=tuple(active_events)
    ids={e.id for e in active_events};all_terms={e.id:e for e in inputs.events}
    configuration=[]
    if len(ids)!=len(active_events) or not (all_terms.keys()-inputs.optional_ids)<=ids or any(all_terms.get(e.id)!=e for e in active_events):
        configuration.append(Issue('selected_events','','','Gewählte Termine entsprechen nicht dem Eingabesnapshot.'))
    core=check_core(inputs.people,active_events,blocks,absences=inputs.absences,boundary=inputs.boundary,check_fixed=check_fixed)
    if inputs.quotas:configuration.extend(check_quotas(inputs.quotas,active_events,policy=inputs.week_policy))
    configuration.extend(check_coverage(active_events,blocks,inputs.coverage))
    if configuration:core=replace(core,issues=core.issues+tuple(configuration))
    calendar=check_calendar(inputs.people,tuple(blocks)+inputs.boundary,inputs.year,inputs.month,
                            known_days=inputs.known_days,policy=inputs.weekend_policy)
    return core,calendar


def solve_feasibility(inputs: PlanningInput, *, time_limit=5.0, cancel=None, existing=(),existing_events=None) -> FeasibilityResult:
    started=monotonic()
    if type(time_limit) not in (int,float) or not isfinite(time_limit) or time_limit<=0:raise DomainError('Zeitlimit muss endlich und größer null sein.')
    deadline=started+time_limit;existing=tuple(existing)
    key=inputs.fingerprint
    best=None;best_events=None;best_open=None;proved=False;last_issues=();last_unchecked=tuple(inputs.unchecked)

    def consider(blocks,events=None):
        nonlocal best,best_events,best_open,last_issues,last_unchecked
        core,calendar=verify(inputs,blocks,active_events=events)
        last_issues=core.issues+calendar.issues
        last_unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        if last_issues:return False
        missing=sum(n for _,n in core.open_slots)
        if best is None or missing<best_open:
            best,best_open=tuple(blocks),missing
            best_events=tuple(inputs.events if events is None else events)
        return True

    def finish(fallback_status):
        if best is None:
            return FeasibilityResult(fallback_status,(),(),last_issues,last_unchecked,False,monotonic()-started,key,inputs.profile_label)
        core,calendar=verify(inputs,best,active_events=best_events)
        if core.issues or calendar.issues:raise DomainError('Der beste Zwischenstand bestand die abschließende Prüfung nicht.')
        unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        status='incomplete' if core.open_slots else 'conditional' if unchecked else 'feasible'
        return FeasibilityResult(status,best,core.open_slots,(),unchecked,proved or best_open==0,monotonic()-started,key,inputs.profile_label,best_events)

    if existing or existing_events is not None:consider(existing,existing_events)
    if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
    structural=check_core(inputs.people,inputs.events,(),check_fixed=False)
    if structural.issues:
        last_issues=structural.issues;return finish('invalid')
    terms={e.id:e for e in inputs.events};persons={p.id:p for p in inputs.people}
    candidates=[]
    # Auch ein Altentwurf mit einer anderen gültigen konkreten Pausenlage bleibt
    # Startpunkt; er wird nicht nur wegen begrenzter neuer Kandidaten verworfen.
    for b in dict.fromkeys(inputs.candidates+tuple(existing)):
        if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
        if b.person_id not in persons or b.id not in terms:continue
        local=check_core((persons[b.person_id],),(terms[b.id],),(b,),absences=inputs.absences,
                         boundary=tuple(p for p in inputs.boundary if p.person_id==b.person_id),check_fixed=False)
        if local.hard_ok:candidates.append(b)
    model=cp_model.CpModel();x=[model.new_bool_var(f'candidate_{i}') for i in range(len(candidates))]
    y={e.id:model.new_bool_var(f'term_{e.id}') for e in inputs.events}
    for e in inputs.events:
        if e.id not in inputs.optional_ids:model.add(y[e.id]==1)
    for q in inputs.quotas:
        model.add(sum(y[e.id] for e in inputs.events if e.service.code==q.code and q.dates.includes(e.attendance.start_day))==q.required)
    if inputs.week_policy is not None:
        for i,a in enumerate(inputs.events):
            for b in inputs.events[i+1:]:
                if extra_events_conflict(a,b,inputs.week_policy):model.add(y[a.id]+y[b.id]<=1)
    for term in inputs.events:
        indices=[i for i,b in enumerate(candidates) if b.id==term.id]
        for i in indices:model.add(x[i]<=y[term.id])
        if term.service.staff is not None:model.add(sum(x[i] for i in indices)<=term.service.staff*y[term.id])
        for person in inputs.people:
            mine=[i for i in indices if candidates[i].person_id==person.id]
            model.add(sum(x[i] for i in mine)<=1)
        for person in term.fixed_people:
            fixed=[i for i in indices if candidates[i].person_id==person]
            if not fixed and term.id not in inputs.optional_ids:
                local=tuple(b for b in inputs.candidates+existing if b.id==term.id and b.person_id==person)
                detail=check_core(inputs.people,(term,),local,absences=inputs.absences,boundary=inputs.boundary,check_fixed=False)
                last_issues=detail.issues or (Issue('fixed_candidate',person,term.id,'Für die feste Person liegt keine gültige konkrete Zuteilung einschließlich Pause vor.'),)
                return finish('infeasible')
            model.add(sum(x[i] for i in fixed)==y[term.id])
    for i,a in enumerate(candidates):
        if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
        for j in range(i+1,len(candidates)):
            b=candidates[j]
            if a.person_id!=b.person_id:continue
            left,right=sorted((a.attendance,b.attendance),key=lambda span:span.start)
            if (left.start_day==right.start_day or left.overlaps(right) or rest_minutes(left,right)<660):
                model.add(x[i]+x[j]<=1)
    for person in inputs.people:
        indices=[i for i,b in enumerate(candidates) if b.person_id==person.id]
        past=set().union(*(b.occupied_days for b in inputs.boundary if b.person_id==person.id))
        occupied=set().union(*(candidates[i].occupied_days for i in indices))
        flags={}
        for day in occupied-past:
            flag=model.new_bool_var(f'day_{person.id}_{day}');flags[day]=flag
            model.add_max_equality(flag,[x[i] for i in indices if day in candidates[i].occupied_days])
        starts={d-timedelta(days=k) for d in occupied for k in range(6)}
        for start in starts:
            window={start+timedelta(days=k) for k in range(6)}
            old=len(window&past)
            if old>5:model.add(sum(x[i] for i in indices if candidates[i].occupied_days&window)==0)
            else:model.add(sum(flags[d] for d in flags if d in window)<=5-old)
    for rule in inputs.coverage:
        term=terms[rule.event_id]
        roles={rule.event_id,*rule.relief_event_ids}
        support=[i for i,b in enumerate(candidates) if b.id in roles]
        filled=sum(x[i] for i,b in enumerate(candidates) if b.id==term.id)
        for segment in coverage_segments(term,[candidates[i] for i in support]):
            working=[i for i in support if any(w.contains(segment) for w in candidates[i].work)]
            model.add(sum(x[i] for i in working)>=filled-(term.service.staff-rule.minimum_working)*y[term.id])
    required=sum((e.service.staff or 0)*y[e.id] for e in inputs.events)
    assigned=sum(x[i] for i,b in enumerate(candidates) if terms[b.id].service.staff is not None)
    model.minimize(required-assigned)
    if best is not None:
        for i,b in enumerate(candidates):model.add_hint(x[i],int(b in best))
        for e in inputs.events:model.add_hint(y[e.id],int(e in best_events))
    stopped=StopEvent();active=[None]
    def watch():
        while not stopped.wait(.02):
            if cancel is not None and cancel.is_set() and active[0] is not None:active[0].stop_search()
    thread=Thread(target=watch,daemon=True)
    if cancel is not None:thread.start()
    fallback='unknown'
    try:
        while monotonic()<deadline and not (cancel is not None and cancel.is_set()):
            solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=max(.00001,deadline-monotonic())
            solver.parameters.num_search_workers=1;solver.parameters.random_seed=202611
            active[0]=solver;status=solver.solve(model);active[0]=None
            if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
                selected=tuple(b for i,b in enumerate(candidates) if solver.boolean_value(x[i]))
                active_events=tuple(e for e in inputs.events if solver.boolean_value(y[e.id]))
                if consider(selected,active_events):
                    proved=status==cp_model.OPTIMAL
                    break
                # Kalenderregeln werden unabhängig direkt am Ergebnis geprüft.
                # Der Schnitt entfernt genau dieses ungültige Ergebnis, keine
                # gültige Lösung. Für große Modelle folgt ein eigener Compiler.
                variables=x+list(y.values())
                model.add(sum((1-v) if solver.boolean_value(v) else v for v in variables)>=1)
            elif status==cp_model.INFEASIBLE:
                fallback='infeasible';break
            elif status==cp_model.MODEL_INVALID:
                fallback='invalid';break
            else:break
    finally:
        stopped.set()
        if thread.is_alive():thread.join(timeout=.1)
    if cancel is not None and cancel.is_set() and best is None:fallback='cancelled'
    return finish(fallback)
