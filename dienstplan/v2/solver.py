"""Kleine V2-Machbarkeitsmodelle; keine produktive Profilfreigabe."""
from dataclasses import dataclass
from datetime import timedelta
from math import isfinite
from threading import Event as StopEvent,Thread
from time import monotonic

from ortools.sat.python import cp_model

from .calendar_rules import check_calendar
from .errors import DomainError
from .serialization import fingerprint
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

    def __post_init__(self):
        if not self.profile_label:raise DomainError('Das Machbarkeitsmodell benötigt eine explizite Profilbezeichnung.')
        for key in ('people','events','absences','boundary'):
            object.__setattr__(self,key,tuple(sorted(getattr(self,key),key=lambda v:getattr(v,'id',repr(v)))))
        object.__setattr__(self,'candidates',tuple(sorted(set(self.candidates),key=lambda b:(b.id,b.person_id,tuple(p.start for p in b.breaks)))))
        object.__setattr__(self,'known_days',frozenset(self.known_days))
        object.__setattr__(self,'unchecked',tuple(self.unchecked))

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


def verify(inputs,blocks,*,check_fixed=True):
    blocks=tuple(blocks)
    core=check_core(inputs.people,inputs.events,blocks,absences=inputs.absences,boundary=inputs.boundary,check_fixed=check_fixed)
    calendar=check_calendar(inputs.people,tuple(blocks)+inputs.boundary,inputs.year,inputs.month,
                            known_days=inputs.known_days,policy=inputs.weekend_policy)
    return core,calendar


def solve_feasibility(inputs: PlanningInput, *, time_limit=5.0, cancel=None, existing=()) -> FeasibilityResult:
    started=monotonic()
    if type(time_limit) not in (int,float) or not isfinite(time_limit) or time_limit<=0:raise DomainError('Zeitlimit muss endlich und größer null sein.')
    deadline=started+time_limit;existing=tuple(existing)
    key=inputs.fingerprint
    best=None;best_open=None;proved=False;last_issues=();last_unchecked=tuple(inputs.unchecked)

    def consider(blocks):
        nonlocal best,best_open,last_issues,last_unchecked
        core,calendar=verify(inputs,blocks)
        last_issues=core.issues+calendar.issues
        last_unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        if last_issues:return False
        missing=sum(n for _,n in core.open_slots)
        if best is None or missing<best_open:
            best,best_open=tuple(blocks),missing
        return True

    def finish(fallback_status):
        if best is None:
            return FeasibilityResult(fallback_status,(),(),last_issues,last_unchecked,False,monotonic()-started,key,inputs.profile_label)
        core,calendar=verify(inputs,best)
        if core.issues or calendar.issues:raise DomainError('Der beste Zwischenstand bestand die abschließende Prüfung nicht.')
        unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        status='incomplete' if core.open_slots else 'conditional' if unchecked else 'feasible'
        return FeasibilityResult(status,best,core.open_slots,(),unchecked,proved or best_open==0,monotonic()-started,key,inputs.profile_label)

    if existing:consider(existing)
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
    for term in inputs.events:
        indices=[i for i,b in enumerate(candidates) if b.id==term.id]
        if term.service.staff is not None:model.add(sum(x[i] for i in indices)<=term.service.staff)
        for person in inputs.people:
            mine=[i for i in indices if candidates[i].person_id==person.id]
            model.add(sum(x[i] for i in mine)<=1)
        for person in term.fixed_people:
            fixed=[i for i in indices if candidates[i].person_id==person]
            if not fixed:
                local=tuple(b for b in inputs.candidates+existing if b.id==term.id and b.person_id==person)
                detail=check_core(inputs.people,(term,),local,absences=inputs.absences,boundary=inputs.boundary,check_fixed=False)
                last_issues=detail.issues or (Issue('fixed_candidate',person,term.id,'Für die feste Person liegt keine gültige konkrete Zuteilung einschließlich Pause vor.'),)
                return finish('infeasible')
            model.add(sum(x[i] for i in fixed)==1)
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
    required=sum(e.service.staff or 0 for e in inputs.events)
    assigned=sum(x[i] for i,b in enumerate(candidates) if terms[b.id].service.staff is not None)
    model.minimize(required-assigned)
    if best is not None:
        for i,b in enumerate(candidates):model.add_hint(x[i],int(b in best))
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
                if consider(selected):
                    proved=status==cp_model.OPTIMAL
                    break
                # Kalenderregeln werden unabhängig direkt am Ergebnis geprüft.
                # Der Schnitt entfernt genau dieses ungültige Ergebnis, keine
                # gültige Lösung. Für große Modelle folgt ein eigener Compiler.
                model.add(sum((1-x[i]) if solver.boolean_value(x[i]) else x[i] for i in range(len(x)))>=1)
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
