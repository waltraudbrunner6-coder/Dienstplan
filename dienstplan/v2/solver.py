"""Kleine V2-Machbarkeitsmodelle; keine produktive Profilfreigabe."""
from dataclasses import dataclass,replace
from datetime import timedelta
from math import isfinite
from threading import Event as StopEvent,Thread
from time import monotonic

from ortools.sat.python import cp_model

from .calendar_rules import check_calendar,check_quotas,extra_events_conflict,dates,horizon
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
    locked: tuple = ()

    def __post_init__(self):
        if not self.profile_label:raise DomainError('Das Machbarkeitsmodell benötigt eine explizite Profilbezeichnung.')
        for key in ('people','events','absences','boundary'):
            object.__setattr__(self,key,tuple(sorted(getattr(self,key),key=lambda v:getattr(v,'id',repr(v)))))
        object.__setattr__(self,'candidates',tuple(sorted(set(self.candidates),key=lambda b:(b.id,b.person_id,tuple(p.start for p in b.breaks)))))
        object.__setattr__(self,'known_days',frozenset(self.known_days))
        object.__setattr__(self,'unchecked',tuple(self.unchecked))
        object.__setattr__(self,'optional_ids',frozenset(self.optional_ids))
        object.__setattr__(self,'locked',tuple(self.locked))
        if len({(b.id,b.person_id) for b in self.locked})!=len(self.locked):raise DomainError('Doppelte manuelle Fixierung.')
        for key in ('quotas','coverage'):
            object.__setattr__(self,key,tuple(sorted(getattr(self,key),key=lambda v:getattr(v,'id',getattr(v,'event_id','')))))
        terms={e.id:e for e in self.events}
        if any(e.person_id not in {p.id for p in self.people} for e in self.absences):raise DomainError('Abwesenheit/Wunsch verweist auf unbekannte Person.')
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
    objectives: tuple = ()
    proofs: tuple = ()
    global_optimal: bool = False


@dataclass(frozen=True, slots=True)
class StageProof:
    name: str
    value: int
    proven: bool
    prefix: tuple
    conditional: bool


def _reduce_pause_choices(inputs,candidates,profile,protected=()):
    """Dominanz nur ohne Arbeitsabdeckungsrolle; Eingabekandidaten bleiben erhalten.

    Gleiche Anwesenheit/Person hat dieselben Kern-, Wunsch- und Kalenderregeln.
    Bei gleichen Monats-/Gesamtarbeitsmengen unterscheiden die vorhandenen
    Zielklassen nur die letzte Pausenpräferenz. Vertretungsrollen und vorhandene
    beziehungsweise fixierte konkrete Pausen sind von der Reduktion ausgenommen.
    """
    from .objectives import _night_pause
    from .work import quantities
    coverage={id for r in inputs.coverage for id in (r.event_id,)+r.relief_event_ids}
    protected=set(protected);selected={};untouched=[]
    for block in candidates:
        if block.id in coverage or block in protected:
            untouched.append(block);continue
        monthly=sum(q.work_minutes for q in quantities(block) if (q.day.year,q.day.month)==(inputs.year,inputs.month))
        key=block.id,block.person_id,block.work_minutes,monthly
        cost=_night_pause(block) if profile is not None and 'late_break' in profile.order else 0
        rank=(cost,tuple(p.start for p in block.breaks))
        if key not in selected or rank<selected[key][0]:selected[key]=(rank,block)
    return tuple(dict.fromkeys(untouched+[block for _,block in selected.values()]))


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
    if check_fixed:
        for fixed in inputs.locked:
            if fixed not in blocks:configuration.append(Issue('manual_fixed',fixed.person_id,fixed.id,'Die manuell fixierte Zuteilung einschließlich Pause fehlt oder wurde geändert.'))
    if configuration:core=replace(core,issues=core.issues+tuple(configuration))
    calendar=check_calendar(inputs.people,tuple(blocks)+inputs.boundary,inputs.year,inputs.month,
                            known_days=inputs.known_days,policy=inputs.weekend_policy)
    return core,calendar


def solve_feasibility(inputs: PlanningInput, *, time_limit=5.0, cancel=None, existing=(),existing_events=None,objective_profile=None) -> FeasibilityResult:
    started=monotonic()
    if type(time_limit) not in (int,float) or not isfinite(time_limit) or time_limit<=0:raise DomainError('Zeitlimit muss endlich und größer null sein.')
    deadline=started+time_limit;existing=tuple(existing)
    key=inputs.fingerprint
    best=None;best_events=None;best_open=None;proved=False;last_issues=();last_unchecked=tuple(inputs.unchecked)
    best_values=None;proofs=[]

    def score(blocks,events):
        if objective_profile is None:
            core,_=verify(inputs,blocks,active_events=events)
            return (('coverage',sum(n for _,n in core.open_slots)),)
        from .objectives import evaluate
        return evaluate(inputs,blocks,events,objective_profile)

    def consider(blocks,events=None):
        nonlocal best,best_events,best_open,last_issues,last_unchecked,best_values
        core,calendar=verify(inputs,blocks,active_events=events)
        last_issues=core.issues+calendar.issues
        last_unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        if last_issues:return False
        missing=sum(n for _,n in core.open_slots)
        events=tuple(inputs.events if events is None else events)
        values=score(blocks,events)
        if best is None or tuple(v for _,v in values)<tuple(v for _,v in best_values):
            best,best_open=tuple(blocks),missing
            best_events=events;best_values=values
        return True

    def finish(fallback_status):
        if best is None:
            return FeasibilityResult(fallback_status,(),(),last_issues,last_unchecked,False,monotonic()-started,key,inputs.profile_label)
        core,calendar=verify(inputs,best,active_events=best_events)
        if core.issues or calendar.issues:raise DomainError('Der beste Zwischenstand bestand die abschließende Prüfung nicht.')
        unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked))
        status='incomplete' if core.open_slots else 'conditional' if unchecked else 'feasible'
        final_values=score(best,best_events)
        if final_values!=best_values:raise DomainError('Endgültige Zielwerte stimmen nicht mit dem besten Entwurf überein.')
        current_proofs=tuple(p for i,p in enumerate(proofs) if i<len(final_values) and (p.name,p.value)==final_values[i] and p.prefix==final_values[:i])
        global_optimal=len(current_proofs)==len(final_values) and all(p.proven and not p.conditional for p in current_proofs)
        return FeasibilityResult(status,best,core.open_slots,(),unchecked,proved or best_open==0,monotonic()-started,key,inputs.profile_label,best_events,final_values,current_proofs,global_optimal)

    if existing or existing_events is not None:consider(existing,existing_events)
    if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
    structural=check_core(inputs.people,inputs.events,(),check_fixed=False)
    if structural.issues:
        last_issues=structural.issues;return finish('invalid')
    terms={e.id:e for e in inputs.events};persons={p.id:p for p in inputs.people}
    candidates=[]
    # Auch ein Altentwurf mit einer anderen gültigen konkreten Pausenlage bleibt
    # Startpunkt; er wird nicht nur wegen begrenzter neuer Kandidaten verworfen.
    for b in dict.fromkeys(inputs.candidates+tuple(existing)+inputs.locked):
        if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
        if b.person_id not in persons or b.id not in terms:continue
        local=check_core((persons[b.person_id],),(terms[b.id],),(b,),absences=inputs.absences,
                         boundary=tuple(p for p in inputs.boundary if p.person_id==b.person_id),check_fixed=False)
        if local.hard_ok:candidates.append(b)
    candidates=_reduce_pause_choices(inputs,candidates,objective_profile,existing+inputs.locked)
    model=cp_model.CpModel();x=[model.new_bool_var(f'candidate_{i}') for i in range(len(candidates))]
    for fixed in inputs.locked:
        if fixed not in candidates:
            last_issues=(Issue('manual_fixed',fixed.person_id,fixed.id,'Manuelle Fixierung ist mit Beschäftigung, Rechten, Urlaub, Ruhe oder Pausenregeln unvereinbar.'),)
            return finish('infeasible')
        model.add(x[candidates.index(fixed)]==1)
    y={e.id:model.new_bool_var(f'term_{e.id}') for e in inputs.events}
    for e in inputs.events:
        if e.id not in inputs.optional_ids:model.add(y[e.id]==1)
    for q in inputs.quotas:
        model.add(sum(y[e.id] for e in inputs.events if e.service.code==q.code and q.dates.includes(e.attendance.start_day))==q.required)
    if inputs.week_policy is not None:
        for i,a in enumerate(inputs.events):
            for b in inputs.events[i+1:]:
                if extra_events_conflict(a,b,inputs.week_policy):model.add(y[a.id]+y[b.id]<=1)
    assignments={}
    for term in inputs.events:
        indices=[i for i,b in enumerate(candidates) if b.id==term.id]
        for i in indices:model.add(x[i]<=y[term.id])
        if term.service.staff is not None:model.add(sum(x[i] for i in indices)<=term.service.staff*y[term.id])
        for person in inputs.people:
            mine=[i for i in indices if candidates[i].person_id==person.id]
            if mine:
                chosen=model.new_bool_var(f'assignment_{term.id}_{person.id}')
                model.add(sum(x[i] for i in mine)==chosen)
                assignments[term.id,person.id]=(chosen,candidates[mine[0]])
        for person in term.fixed_people:
            fixed=[i for i in indices if candidates[i].person_id==person]
            if not fixed and term.id not in inputs.optional_ids:
                local=tuple(b for b in inputs.candidates+existing if b.id==term.id and b.person_id==person)
                detail=check_core(inputs.people,(term,),local,absences=inputs.absences,boundary=inputs.boundary,check_fixed=False)
                last_issues=detail.issues or (Issue('fixed_candidate',person,term.id,'Für die feste Person liegt keine gültige konkrete Zuteilung einschließlich Pause vor.'),)
                return finish('infeasible')
            model.add(sum(x[i] for i in fixed)==y[term.id])
    # Anwesenheit/Starttag/Ruhe hängen nicht von der konkreten Pausenlage ab.
    # Eine gemeinsame Zuordnungsvariable ersetzt das quadratische Kreuzprodukt
    # sämtlicher Pausenvarianten, ohne eine davon zu entfernen.
    for person in inputs.people:
        mine=[value for (_,pid),value in assignments.items() if pid==person.id]
        for i,(chosen,a) in enumerate(mine):
            if monotonic()>=deadline or (cancel is not None and cancel.is_set()):return finish('cancelled' if cancel is not None and cancel.is_set() else 'unknown')
            for other,b in mine[i+1:]:
                left,right=sorted((a.attendance,b.attendance),key=lambda span:span.start)
                if (left.start_day==right.start_day or left.overlaps(right) or rest_minutes(left,right)<660):
                    model.add(chosen+other<=1)
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
        def occupied(day):
            return 1 if day in past else flags.get(day,0)
        # Dieselbe Vorwochenregel wie im unabhängigen Prüfer, einschließlich
        # seiner ausdrücklichen Unbekannt-Behandlung für fehlende Randdaten.
        for saturday in (d for d in dates(horizon(inputs.year,inputs.month)) if d.weekday()==5):
            weekend=[saturday,saturday+timedelta(days=1)]
            previous=[saturday-timedelta(days=5-i) for i in range(5)]
            touched=model.new_bool_var(f'weekend_work_{person.id}_{saturday}')
            model.add_max_equality(touched,[occupied(d) for d in weekend])
            current=[chosen for (eid,pid),(chosen,b) in assignments.items() if pid==person.id
                     and (b.attendance.start_day.year,b.attendance.start_day.month)==(inputs.year,inputs.month)
                     and b.occupied_days&set(previous+weekend)]
            if not current:continue
            scope=model.new_bool_var(f'weekend_scope_{person.id}_{saturday}')
            model.add_max_equality(scope,current)
            free=[1-occupied(d) if (person.id,d) in inputs.known_days or not person.employment.dates.includes(d) else 0 for d in previous]
            pairs=[]
            for i in range(4):
                pair=model.new_bool_var(f'free_pair_{person.id}_{saturday}_{i}')
                model.add(pair<=free[i]);model.add(pair<=free[i+1]);model.add(pair>=free[i]+free[i+1]-1)
                pairs.append(pair)
            unknown=[1-occupied(d) for d in previous if (person.id,d) not in inputs.known_days and person.employment.dates.includes(d)]
            model.add(sum(pairs)+sum(unknown)>=touched+scope-1)
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
    if objective_profile is None:goals=(('coverage',required-assigned),)
    else:
        from .objectives import compile_objectives
        goals=compile_objectives(inputs,candidates,x,y,model,objective_profile,required-assigned)
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
      for stage,(name,expression) in enumerate(goals):
        if monotonic()>=deadline or (cancel is not None and cancel.is_set()):break
        model.minimize(expression)
        if best is not None:model.add(expression<=best_values[stage][1])
        # Späte Fairness erhält eigenes Budget; lokale Prüfung 15 Prozent.
        weights=[6 if n=='coverage' else 3 if n in {'hours_max','hours_spread','shifts'} else 1 for n,_ in goals[stage:]]
        local_reserve=.15*time_limit if objective_profile is not None else 0
        stage_deadline=min(deadline-local_reserve,monotonic()+max(0,deadline-local_reserve-monotonic())*weights[0]/sum(weights))
        stage_proved=False
        while monotonic()<stage_deadline and not (cancel is not None and cancel.is_set()):
            solver=cp_model.CpSolver()
            solver.parameters.max_time_in_seconds=max(.00001,stage_deadline-monotonic())
            solver.parameters.num_search_workers=1;solver.parameters.random_seed=202611
            active[0]=solver;status=solver.solve(model);active[0]=None
            if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
                selected=tuple(b for i,b in enumerate(candidates) if solver.boolean_value(x[i]))
                active_events=tuple(e for e in inputs.events if solver.boolean_value(y[e.id]))
                if consider(selected,active_events):
                    # Direkte Nachbewertung muss dieselben Ganzzahlwerte liefern.
                    evaluated=score(selected,active_events)
                    if solver.value(expression)!=evaluated[stage][1]:raise DomainError(f'Zielabweichung zwischen Modell und Ergebnis: {name}.')
                    stage_proved=status==cp_model.OPTIMAL
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
        if best is None:break
        value=best_values[stage][1]
        if stage==0:proved=stage_proved or value==0
        proofs.append(StageProof(name,value,stage_proved or (stage==0 and value==0),best_values[:stage],not all(p.proven and not p.conditional for p in proofs)))
        model.add(expression==value)
        model.clear_hints()
        for i,c in enumerate(candidates):model.add_hint(x[i],int(c in best))
        for e in inputs.events:model.add_hint(y[e.id],int(e in best_events))
        if fallback in {'invalid','infeasible'}:break
      if objective_profile is not None and best is not None and monotonic()<deadline and not (cancel is not None and cancel.is_set()):
        from .improvement import improve
        changed=improve(inputs,best,best_events,objective_profile,deadline=deadline,cancel=cancel)
        consider(changed,best_events)
    finally:
        stopped.set()
        if thread.is_alive():thread.join(timeout=.1)
    if cancel is not None and cancel.is_set() and best is None:fallback='cancelled'
    return finish(fallback)
