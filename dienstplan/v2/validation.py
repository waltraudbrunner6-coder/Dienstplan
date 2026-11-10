"""Direkte Ergebnisprüfung, unabhängig von CP-SAT und dessen Hilfsvariablen."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from .catalog import participation
from .errors import DomainError
from .time import rest_minutes


@dataclass(frozen=True, slots=True)
class Issue:
    rule: str
    person_id: str
    event_id: str
    message: str


@dataclass(frozen=True, slots=True)
class CoreReport:
    issues: tuple[Issue, ...]
    open_slots: tuple[tuple[str,int], ...]
    participation: tuple[tuple[str,str,str], ...]
    scope: str = "Kernregeln; kein vollständiger V2-/Rechtsnachweis"

    @property
    def hard_ok(self):return not self.issues


def check_core(people, events, blocks, *, absences=(), boundary=(), check_fixed=True) -> CoreReport:
    people,events,blocks=tuple(people),tuple(events),tuple(blocks)
    persons={p.id:p for p in people};terms={e.id:e for e in events}
    issues=[]
    def error(rule,person,event,message):issues.append(Issue(rule,person,event,message))
    if len(persons)!=len(people):error('identity','','','Doppelte Personenkennung.')
    if len(terms)!=len(events):error('identity','','','Doppelte Terminkennung.')
    coverage=[e.coverage_id for e in events if e.service.staff is not None]
    if len(coverage)!=len(set(coverage)):error('coverage','','','Mehrere Varianten desselben operativen Bedarfs sind gleichzeitig aktiv.')
    extra_by_day=defaultdict(set)
    for e in events:
        if e.service.code in {'BK','WL'}:extra_by_day[e.attendance.start_day].add(e.service.code)
    for day,codes in extra_by_day.items():
        if codes=={'BK','WL'}:error('wl_bk_exclusion','',str(day),'BK und WL dürfen nicht am selben lokalen Startdatum stattfinden.')
    team_by_day=defaultdict(list)
    for e in events:
        if e.service.code in {'T','TS'}:team_by_day[e.attendance.start_day].append(e)
    if any(len(es)>1 for es in team_by_day.values()):error('team','','','T und TS dürfen am selben Tag nicht zwei Veranstaltungen bilden.')
    seen=set();present=defaultdict(set);mine=defaultdict(list)
    current_keys={(b.id,b.person_id):b for b in blocks}
    boundary_clean=[]
    for b in boundary:
        old=current_keys.get((b.id,b.person_id))
        if old is not None:
            if old!=b:error('boundary',b.person_id,b.id,'Widersprüchliche Randversion derselben Zuteilung.')
        else:boundary_clean.append(b)
    for b in blocks:
        key=b.id,b.person_id
        if key in seen:error('duplicate',b.person_id,b.id,'Person ist im selben Termin doppelt zugeteilt.')
        seen.add(key);mine[b.person_id].append(b)
        person,term=persons.get(b.person_id),terms.get(b.id)
        if person is None or term is None:
            error('reference',b.person_id,b.id,'Unbekannte Person oder unbekannter Termin.');continue
        before=len(issues)
        if term.attendance!=b.attendance or term.service.code!=b.code:
            error('template',b.person_id,b.id,'Zeit/Kürzel stimmt nicht mit dem vorgegebenen Termin überein.')
        for message in person.eligibility_errors(b.code,b.attendance):error('eligibility',b.person_id,b.id,message)
        for day in b.occupied_days:
            try:person.contracts.at(day)
            except DomainError as exc:error('contract',b.person_id,b.id,str(exc))
        for a in absences:
            if a.kind=='urlaub' and a.person_id==b.person_id and a.span.overlaps(b.attendance):
                error('leave',b.person_id,b.id,'Verbindlicher Urlaub überschneidet den Dienst einschließlich T/TS.')
        if term.fixed_people and b.person_id not in term.fixed_people:
            error('fixed',b.person_id,b.id,'Die festgelegte Personenzuteilung wurde verändert.')
        for window in term.protected:
            if sum(hit.minutes for part in b.work if (hit:=part.intersection(window)) is not None)!=window.minutes:
                error('team_window',b.person_id,b.id,'Enthaltene Teamzeit ist nicht vollständig als Arbeit erhalten.')
        if b.code=='LB' and term.service.key!='LB_TS' and any(e.service.code=='TS' for e in team_by_day[b.attendance.start_day]):
            error('team_window',b.person_id,b.id,'LB muss am TS-Tag bis 19:30 verlängert sein.')
        if len(issues)==before:present[b.id].add(b.person_id)
    for term in events:
        selected=present[term.id]
        if term.service.staff is not None and len(selected)>term.service.staff:
            error('capacity','',term.id,'Mehr Personen als operative Plätze zugeteilt.')
        if check_fixed:
            for person in set(term.fixed_people)-selected:
                error('fixed',person,term.id,'Eine festgelegte Personenzuteilung fehlt oder ist ungültig.')
    past=defaultdict(list)
    for b in boundary_clean:past[b.person_id].append(b)
    for pid,chosen in mine.items():
        starts=defaultdict(list)
        for b in chosen:starts[b.attendance.start_day].append(b)
        for day,values in starts.items():
            if len(values)>1:error('one_block',pid,values[0].id,f'Mehr als ein Dienstblock mit Startdatum {day}.')
        spans=sorted([(b,True) for b in chosen]+[(b,False) for b in past[pid]],key=lambda pair:pair[0].attendance.start)
        for i,(a,a_current) in enumerate(spans):
            for b,b_current in spans[i+1:]:
                if not (a_current or b_current):continue
                if a.attendance.overlaps(b.attendance):
                    error('overlap',pid,b.id,f'Echte Überschneidung mit {a.id}.')
                else:
                    rest=rest_minutes(a.attendance,b.attendance)
                    if rest<660:error('rest',pid,b.id,f'Nur {rest} Minuten Ruhe seit {a.id}; benötigt 660, fehlen {660-rest}.')
                if a.attendance.start_day==b.attendance.start_day and not (a_current and b_current):
                    error('one_block',pid,b.id,'Ein weiterer Randdienst hat dasselbe Startdatum.')
        current_days=set().union(*(b.occupied_days for b in chosen))
        all_days=current_days|set().union(*(b.occupied_days for b in past[pid])) if past[pid] else current_days
        runs=[]
        for day in sorted(all_days):
            if runs and runs[-1][-1]+timedelta(days=1)==day:runs[-1].append(day)
            else:runs.append([day])
        for run in runs:
            if len(run)>5 and set(run)&current_days:
                error('consecutive',pid,'',f'{len(run)} belegte Arbeitstage von {run[0]} bis {run[-1]}; höchstens fünf.')
    attendance=[]
    for day,occasions in sorted(team_by_day.items()):
        for occasion in occasions:
            for p in people:
                if not p.employment.contains(occasion.attendance):state='nicht beschäftigt'
                elif any(a.kind=='urlaub' and a.person_id==p.id and a.span.overlaps(occasion.attendance) for a in absences):state='Urlaub'
                else:
                    states={participation(b,occasion) for b in mine[p.id]+past[p.id]}
                    state=next((s for s in ('vollständig','T erfüllt; TS-Ausnahme','ausgenommen') if s in states),'fehlt')
                attendance.append((occasion.id,p.id,state))
    opened=tuple((e.id,e.service.staff-len(present[e.id])) for e in events
                 if e.service.staff is not None and len(present[e.id])<e.service.staff)
    return CoreReport(tuple(dict.fromkeys(issues)),opened,tuple(attendance))
