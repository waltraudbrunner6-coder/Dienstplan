"""Benannte Testziele, getrennte direkte Bewertung und CP-SAT-Kompilierung."""
from dataclasses import dataclass
from fractions import Fraction

from .accounting import round_minutes
from .catalog import participation
from .errors import DomainError
from .reporting import hours_rows,shares
from .work import quantities
from .wishes import WishHistory,relevant_wishes,violated,wish_rows

FAMILIES=('participation','wishes','groups','burden','hours_max','hours_spread','shifts','weekday','late_break')


@dataclass(frozen=True, slots=True)
class ObjectiveProfile:
    label: str
    order: tuple[str, ...]
    accounts: tuple
    wish_policy: object
    fairness_policy: object
    history: WishHistory = WishHistory()
    historical_shares: tuple = ()
    scale: int = 1000
    minimum_denominator: int = 60
    special_weight: int = 4
    target_profile: str = 'S0'
    month_profile: str = 'M0'
    synthetic: bool = True

    def __post_init__(self):
        for key in ('order','accounts','historical_shares'):object.__setattr__(self,key,tuple(getattr(self,key)))
        if not self.label or self.synthetic is not True or not self.wish_policy.synthetic or not self.fairness_policy.synthetic:
            raise DomainError('Optimierung derzeit nur mit ausdrücklich synthetischem Testprofil.')
        if len(set(self.order))!=len(self.order) or not set(self.order)<=set(FAMILIES):raise DomainError('Unbekannte/doppelte Zielstufe.')
        if any(type(n) is not int or n<1 for n in (self.scale,self.minimum_denominator,self.special_weight)):
            raise DomainError('Skalierung, Mindestnenner und Sondergewicht müssen positive ganze Zahlen sein.')
        if self.scale>1000:raise DomainError('Zu große technische Zielskalierung.')
        if self.target_profile!='S0' or self.month_profile!='M0':raise DomainError('Soll-/Monatsprofil nicht implementiert; ausdrücklich S0/M0 wählen.')
        if ('groups' in self.order and not self.wish_policy.small_groups):raise DomainError('Gruppenschutz ist im Wunschprofil nicht aktiviert.')


def _ceil(n,d):return (n+d-1)//d


def share_targets(inputs,events,profile):
    result={}
    # Je Termin gerundete Tausendstel/Hundertstel; kein Float und kein
    # nachträglicher Wechsel der Rundungsgrenze zwischen Compiler und Bericht.
    for event in events:
        for row in shares(inputs.people,(event,),(),policy=profile.fairness_policy,absences=inputs.absences):
            key=row.person_id,row.code;old=result.get(key,(0,0))
            result[key]=(old[0]+round_minutes(row.expected_count*profile.scale),
                         old[1]+round_minutes(row.expected_minutes*profile.scale))
    return result


def evaluate(inputs,blocks,events,profile):
    from .solver import verify
    blocks,events=tuple(blocks),tuple(events)
    core,calendar=verify(inputs,blocks,active_events=events)
    if not core.hard_ok or not calendar.hard_ok:raise DomainError('Ungültiger Plan kann nicht als besseres Ergebnis bewertet werden.')
    values={'coverage':sum(n for _,n in core.open_slots)}
    values['participation']=sum(state=='fehlt' for _,_,state in core.participation)
    rows=wish_rows(inputs.people,inputs.absences,events,blocks+inputs.boundary,policy=profile.wish_policy,history=profile.history)
    wishes=relevant_wishes(inputs.absences,events)
    weights={w.identity:profile.wish_policy.weekend_weight if w.kind=='wochenendwunsch' else 1 for w in wishes}
    values['wishes']=sum(weights[k] for row in rows for k in row.violated)
    max_group=max((len([w for w in relevant_wishes(inputs.absences,inputs.events) if w.person_id==p.id]) for p in inputs.people),default=0)
    for n in range(1,max_group+1):
        group=[r for r in rows if len(r.relevant)==n]
        values[f'groups/{n}']=sum(len(r.violated) for r in group)
        burdens=[len(r.cumulative) for r in group]
        values[f'burden/{n}/max']=max(burdens,default=0)
        values[f'burden/{n}/squares']=sum(b*b for b in burdens)
    all_blocks=tuple({(b.id,b.person_id):b for b in inputs.boundary+blocks}.values())
    hours=hours_rows(inputs.people,all_blocks,inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,
                     target_profile=profile.target_profile,month_profile=profile.month_profile)
    if any(not r.credits_known for r in hours) and any(f.startswith('hours_') for f in profile.order):
        raise DomainError('Anrechenbare Urlaubstage sind ungeklärt; Stundenoptimierung benötigt ausdrückliche Gutschrifttage.')
    errors=[_ceil(abs(r.deviation)*profile.scale,max(r.target,profile.minimum_denominator)) for r in hours]
    values['hours_max']=max(errors,default=0);values['hours_spread']=sum(e*e for e in errors)
    targets=share_targets(inputs,events,profile)
    historical={(r.person_id,r.code):r for r in profile.historical_shares}
    codes={e.service.code for e in inputs.events if e.service.staff is not None}|{r.code for r in profile.historical_shares}
    fairness=0
    for p in inputs.people:
        for code in sorted(codes):
            target_count,target_minutes=targets.get((p.id,code),(0,0));old=historical.get((p.id,code))
            chosen=[b for b in blocks if b.person_id==p.id and b.code==code]
            c=len(chosen)*profile.scale-target_count;h=sum(b.work_minutes for b in chosen)*profile.scale-target_minutes
            if old is not None:
                c+=old.count*profile.scale-round_minutes(old.expected_count*profile.scale)
                h+=old.work_minutes*profile.scale-round_minutes(old.expected_minutes*profile.scale)
            fairness+=(profile.special_weight if code in {'WL','BK'} else 1)*(c*c+_ceil(abs(h),60)**2)
    values['shifts']=fairness
    values['weekday']=sum(e.service.code=='WL' and e.attendance.start_day.weekday()!=1 for e in events)
    values['late_break']=sum(_night_pause(b) for b in blocks)
    names=['coverage']
    for family in profile.order:
        if family=='groups':names.extend(f'groups/{n}' for n in range(1,max_group+1))
        elif family=='burden':names.extend(f'burden/{n}/{kind}' for n in range(1,max_group+1) for kind in ('max','squares'))
        else:names.append(family)
    return tuple((name,values[name]) for name in names)


def _night_pause(block):
    from .work import WorkBlock
    # Mengenfunktion für den Pauseabschnitt als eigener technischer Messblock,
    # ohne ihn als Dienst/Ruhe zu verwenden.
    return sum(q.night_minutes for pause in block.breaks
               for q in quantities(WorkBlock('quantity',block.person_id,'quantity',pause)))


class _Builder:
    def __init__(self,model):self.model=model;self.serial=0
    def var(self,bound):
        if bound>10**15:raise DomainError('Zielwerte überschreiten die sichere technische Modellgröße.')
        self.serial+=1;return self.model.new_int_var(0,bound,f'goal_{self.serial}')
    def absolute(self,expr,bound):
        var=self.var(bound);self.model.add_abs_equality(var,expr);return var
    def ceil(self,expr,denominator,bound):
        var=self.var(_ceil(bound,denominator));self.model.add(var*denominator>=expr)
        self.model.add(var*denominator<=expr+denominator-1);return var
    def square(self,expr,bound):
        var=self.var(bound*bound);self.model.add_multiplication_equality(var,[expr,expr]);return var
    def maximum(self,values,bound):
        var=self.var(bound)
        self.model.add_max_equality(var,values or [0]);return var
    def any(self,values):return self.maximum(values,1)


def compile_objectives(inputs,candidates,x,y,model,profile,coverage):
    """Compiler nutzt CP-Variablen; evaluate rekonstruiert direkt Ergebniswerte."""
    b=_Builder(model);values={'coverage':coverage};scale=profile.scale
    participation_missing=[]
    for occasion in (e for e in inputs.events if e.service.code in {'T','TS'}):
        for p in inputs.people:
            if not p.employment.contains(occasion.attendance) or any(a.kind=='urlaub' and a.person_id==p.id and a.span.overlaps(occasion.attendance) for a in inputs.absences):continue
            fulfilled=[x[i] for i,c in enumerate(candidates) if c.person_id==p.id and participation(c,occasion)!='fehlt']
            if any(c.person_id==p.id and participation(c,occasion)!='fehlt' for c in inputs.boundary):continue
            participation_missing.append(1-b.any(fulfilled))
    values['participation']=sum(participation_missing)
    wishes=relevant_wishes(inputs.absences,inputs.events);wvars={};rvars={}
    for w in wishes:
        relevant=b.any([y[e.id] for e in inputs.events if w.span.overlaps(e.attendance)]);rvars[w.identity]=relevant
        if violated(w,inputs.boundary,policy=profile.wish_policy):hit=relevant
        else:hit=b.any([x[i] for i,c in enumerate(candidates) if violated(w,(c,),policy=profile.wish_policy)])
        # Ein vom Vortag hineinragender Randdienst verletzt nur relevante Wünsche.
        v=b.var(1);model.add(v<=relevant);model.add(v<=hit);model.add(v>=relevant+hit-1);wvars[w.identity]=v
    values['wishes']=sum((profile.wish_policy.weekend_weight if w.kind=='wochenendwunsch' else 1)*wvars[w.identity] for w in wishes)
    max_group=max((sum(w.person_id==p.id for w in wishes) for p in inputs.people),default=0)
    for n in range(1,max_group+1):
        violations=[];burdens=[];squares=[]
        for p in inputs.people:
            mine=[w for w in wishes if w.person_id==p.id]
            group=b.var(1);model.add(sum(rvars[w.identity] for w in mine)==n).only_enforce_if(group)
            model.add(sum(rvars[w.identity] for w in mine)!=n).only_enforce_if(group.Not())
            current=sum(wvars[w.identity] for w in mine)
            count=b.var(len(mine));model.add(count==current).only_enforce_if(group);model.add(count==0).only_enforce_if(group.Not());violations.append(count)
            old=sum(k[0]==p.id for k in profile.history.violated)
            load=old+sum(wvars[w.identity] for w in mine if w.identity not in profile.history.violated)
            bound=old+len(mine);active=b.var(bound)
            model.add(active==load).only_enforce_if(group);model.add(active==0).only_enforce_if(group.Not())
            burdens.append(active);squares.append(b.square(active,bound))
        values[f'groups/{n}']=sum(violations)
        bound=len(profile.history.violated)+len(wishes)
        values[f'burden/{n}/max']=b.maximum(burdens,bound);values[f'burden/{n}/squares']=sum(squares)
    baseline=hours_rows(inputs.people,inputs.boundary,inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,target_profile=profile.target_profile,month_profile=profile.month_profile)
    if any(not r.credits_known for r in baseline) and any(f.startswith('hours_') for f in profile.order):
        raise DomainError('Anrechenbare Urlaubstage sind ungeklärt; Stundenoptimierung benötigt ausdrückliche Gutschrifttage.')
    normalized=[];squares=[];ratio_bounds=[]
    for row in baseline:
        amounts=[(i,sum(q.work_minutes for q in quantities(c) if (q.day.year,q.day.month)==(inputs.year,inputs.month))) for i,c in enumerate(candidates) if c.person_id==row.person_id and c not in inputs.boundary]
        bound=abs(row.deviation)+sum(v for _,v in amounts)
        error=b.absolute(row.deviation+sum(v*x[i] for i,v in amounts),bound)
        maximum=_ceil(bound*scale,max(row.target,profile.minimum_denominator))
        ratio=b.ceil(error*scale,max(row.target,profile.minimum_denominator),bound*scale)
        normalized.append(ratio);ratio_bounds.append(maximum);squares.append(b.square(ratio,maximum))
    values['hours_max']=b.maximum(normalized,max(ratio_bounds,default=0));values['hours_spread']=sum(squares)
    targets={e.id:share_targets(inputs,(e,),profile) for e in inputs.events}
    historical={(r.person_id,r.code):r for r in profile.historical_shares}
    codes={e.service.code for e in inputs.events if e.service.staff is not None}|{r.code for r in profile.historical_shares}
    fairness=[]
    for p in inputs.people:
        for code in sorted(codes):
            indices=[i for i,c in enumerate(candidates) if c.person_id==p.id and c.code==code]
            old=historical.get((p.id,code))
            for kind in (0,1):
                offset=0 if old is None else ((old.count if kind==0 else old.work_minutes)*scale-round_minutes((old.expected_count if kind==0 else old.expected_minutes)*scale))
                coefficients=[(i,scale*(1 if kind==0 else candidates[i].work_minutes)) for i in indices]
                expected=[(e.id,targets[e.id].get((p.id,code),(0,0))[kind]) for e in inputs.events]
                bound=abs(offset)+sum(v for _,v in coefficients)+sum(v for _,v in expected)
                error=b.absolute(offset+sum(v*x[i] for i,v in coefficients)-sum(v*y[id] for id,v in expected),bound)
                if kind==1:error=b.ceil(error,60,bound);bound=_ceil(bound,60)
                fairness.append((profile.special_weight if code in {'WL','BK'} else 1)*b.square(error,bound))
    values['shifts']=sum(fairness)
    values['weekday']=sum(y[e.id] for e in inputs.events if e.service.code=='WL' and e.attendance.start_day.weekday()!=1)
    values['late_break']=sum(_night_pause(c)*x[i] for i,c in enumerate(candidates))
    names=['coverage']
    for family in profile.order:
        if family=='groups':names.extend(f'groups/{n}' for n in range(1,max_group+1))
        elif family=='burden':names.extend(f'burden/{n}/{kind}' for n in range(1,max_group+1) for kind in ('max','squares'))
        else:names.append(family)
    error=model.validate()
    if error:raise DomainError('Optimierungsmodell überschreitet technische Grenzen: '+error)
    return tuple((name,values[name]) for name in names)
