"""Reiner, atomar übernehmbarer Vorschlag für Termine, Dienste und Abwesenheiten."""
from dataclasses import dataclass, replace
from datetime import date, timedelta
from hashlib import sha256
from itertools import combinations

from .application import service_candidates
from .catalog import event, template
from .entries import Entry, preview as absence_preview, HEADER
from .errors import DomainError
from .pauses import automatic_pause_choices
from .solver import verify
from .time import Interval, midnight, day_segments
from .calendar_rules import extra_events_conflict


@dataclass(frozen=True)
class PlanImport:
    inputs: object
    blocks: tuple
    events: tuple
    errors: tuple[str,...]
    notes: tuple[str,...]

    @property
    def ready(self):return not self.errors


def selected_events(inputs, preferred=()):
    """Konkreter offener Startentwurf mit erfüllten Terminquoten, ohne Personenwahl."""
    mandatory=[e for e in inputs.events if e.id not in inputs.optional_ids]
    from .fallback import default_fallback_events
    selected=list(mandatory)+list(default_fallback_events(inputs,preferred))
    if inputs.week_policy is not None and any(extra_events_conflict(a,b,inputs.week_policy) for i,a in enumerate(selected) for b in selected[i+1:]):raise DomainError('Feste BK/WL-Termine liegen am selben ausgeschlossenen Tag.')
    preferred_ids={e.id for e in preferred}
    weeks={}
    for quota in inputs.quotas:weeks.setdefault(quota.dates,[]).append(quota)
    for span,quotas in weeks.items():
        def search(index,chosen):
            if index==len(quotas):return chosen
            q=quotas[index]
            current=[e for e in selected+chosen if e.service.code==q.code and q.dates.includes(e.attendance.start_day)]
            needed=q.required-len(current)
            if needed<0:return None
            options=[e for e in inputs.events if e.id in inputs.optional_ids and e.service.code==q.code and q.dates.includes(e.attendance.start_day)]
            options.sort(key=lambda e:(e.id not in preferred_ids,e.attendance.start))
            for group in combinations(options,needed):
                if any(extra_events_conflict(a,b,inputs.week_policy) for a in group for b in selected+chosen):continue
                result=search(index+1,chosen+list(group))
                if result is not None:return result
            return None
        chosen=search(0,[])
        if chosen is None:raise DomainError(f'Woche ab {span.start}: keine mit festen Terminen vereinbare BK/WL-Datumswahl.')
        selected.extend(chosen)
    return tuple(sorted(selected,key=lambda e:(e.attendance.start,e.id)))


def prepare_plan_import(inputs,rows,*,blocks=(),events=None,budgets=None,discard_unfixed=False,allow_rules=False):
    errors=[];notes=[];groups={};new_entries=[]
    rows=tuple(rows)
    affected={f"{r.get('datum')}/{str(r.get('dienst','')).strip().upper()}" for r in rows
              if r.get('art','').strip().lower() in {'dienst','termin'} and str(r.get('dienst','')).strip().upper() in {'KC10','KC16','KC15'}}
    keep={key for key in affected if key.endswith('/KC15')}
    from .fallback import dissolve_fallback_groups
    prior=inputs
    inputs=dissolve_fallback_groups(inputs,affected,keep_replacement_ids=keep)
    dissolved_removed={e.id for e in prior.events}-{e.id for e in inputs.events}
    if not allow_rules and any(b.id in dissolved_removed for b in prior.locked):
        errors.append('Eine importierte Alternative würde einen fixierten Dienst entfernen; Fixierung ausdrücklich lösen.')
    if dissolved_removed:notes.append('Importierte Dienstwahl ersetzt ausschließlich die zugehörigen KC10/KC16/KC15-Alternativen; andere Termine bleiben erhalten.')
    people={p.id:p for p in inputs.people};terms={e.id:e for e in inputs.events}
    selected=set(e.id for e in (events or ()) if e.id in inputs.optional_ids)
    requested=set();removed=set(dissolved_removed);locks={(b.id,b.person_id):b for b in inputs.locked}
    retained=tuple(b for b in blocks if not discard_unfixed or b in locks.values())
    if not blocks and events is None and locks:
        retained=tuple(locks.values())
        notes.append(f'{len(retained)} vorhandene fixierte Zuteilungen aus dem vorherigen Arbeitsstand wiederhergestellt.')
    absences={e.identity:e for e in inputs.absences}
    for n,row in enumerate(rows,2):
        source=row.get('quelle') or f'Importzeile {n}'
        try:
            row=dict(row);kind=row.get('art','').strip().lower()
            if kind=='u_zuordnung_offen':
                kind='urlaub';row['gutschrifttage']=row.get('gutschrifttage') or row.get('datum','')
                notes.append(f'{source}: U als markierter Urlaubstag angerechnet (Wochenstunden ÷ 5).')
            row['art']=kind
            if kind=='ignorieren':notes.append(f'{source}: ausdrücklich ignoriert.');continue
            day=date.fromisoformat(row['datum'])
            if (day.year,day.month)!=(inputs.year,inputs.month) and kind not in {'freiwunschtag','urlaub','wochenendwunsch'}:raise DomainError('Datum liegt außerhalb des geöffneten Monats; im passenden Monat importieren.')
            pid=row.get('person_id','').strip()
            if kind in {'freiwunschtag','urlaub','wochenendwunsch'}:
                if pid not in people:raise DomainError('Personen-ID fehlt oder ist unbekannt.')
                start=row.get('beginn') or day.isoformat()+'T00:00'
                end=row.get('ende') or (day+timedelta(days=1)).isoformat()+'T00:00'
                span=Interval.local(start,end)
                month_span=Interval(midnight(date(inputs.year,inputs.month,1)),midnight(date(inputs.year+int(inputs.month==12),inputs.month%12+1,1)))
                if not span.overlaps(month_span):raise DomainError('Abwesenheit liegt außerhalb des geöffneten Monats.')
                credits=frozenset(date.fromisoformat(d) for d in row.get('gutschrifttage','').split('|') if d)
                if kind=='urlaub' and not credits:credits=frozenset(d for d,_ in day_segments(span))
                ident='sheet/'+sha256(str((pid,kind,span)).encode()).hexdigest()
                entry=Entry(ident,pid,kind,span,credits,row.get('kommentar',''),(row.get('budgetmonat') or f'{inputs.year:04d}-{inputs.month:02d}') if kind=='wochenendwunsch' else None,allow_rules)
                if entry.identity in absences and absences[entry.identity].credit_days!=credits:raise DomainError('Identischer Zeitraum hat andere Gutschrifttage.')
                entry=absences.get(entry.identity,entry)
                absences[entry.identity]=entry;new_entries.append(entry)
                if kind=='urlaub' and not credits:notes.append(f'{source}: verbindlicher Urlaub; Gutschrifttage noch ausdrücklich ergänzen.')
                continue
            if kind not in {'dienst','termin'}:raise DomainError('art muss dienst, termin, freiwunschtag, wochenendwunsch, urlaub oder ignorieren sein.')
            code=row.get('dienst','').strip().upper()
            if code=='NH':notes.append(f'{source}: NH wie beauftragt ignoriert.');continue
            if code=='R':
                if row.get('beginn') and row.get('ende'):
                    span=Interval.local(row['beginn'],row['ende'])
                    matches=[key for key in ('R_early','R_late') if template(key).on(day)==span]
                    if len(matches)==1:code=matches[0]
                if code=='R':raise DomainError('Reserve-Zeitfenster auswählen: R_early (10:15–16:15) oder R_late (16:00–00:00 Folgetag). Beide zählen als normale Arbeit.')
            if code=='KC10' and day.weekday()==3:
                code='KCT10';notes.append(f'{source}: Donnerstag KC10 als bestätigte Variante KCT10 bis 17:30 übernommen.')
            code={'R_EARLY':'R_early','R_LATE':'R_late'}.get(code,code)
            template(code)
            if kind=='dienst' and pid not in people:raise DomainError('Personen-ID fehlt oder ist unbekannt. Für reinen Termin art=termin verwenden.')
            key=(day,code);groups.setdefault(key,[]).append((source,pid,row))
        except (ValueError,KeyError,DomainError) as exc:errors.append(f'{source}: {exc}')
    for day in {d for d,c in groups if c=='KC15'}:
        if any((day,c) in groups for c in ('KC10','KC16')):errors.append(f'{day}: KC15 ersetzt KC10 und KC16; beide Varianten können nicht gleichzeitig importiert werden.')
    for (day,code),items in groups.items():
        try:
            service=template(code)
            assigned=tuple(dict.fromkeys(pid for _,pid,r in items if r['art']=='dienst'))
            fixed=assigned if service.code in {'LB','VN','INT','N17','FK'} else ()
            attendance=None
            if code=='FK':
                spans={Interval.local(r['beginn'],r['ende']) for _,_,r in items}
                if len(spans)!=1:raise DomainError('FK-Zeiten widersprechen einander.')
                attendance=spans.pop()
            replacements={'TS':{'T'},'T':{'TS'},'W16':{'W17'},'W17':{'W16'},'KC15':{'KC10','KC16'},'KC10':{'KC15'},'KC16':{'KC15'}}.get(code,set())
            for old in tuple(terms.values()):
                if old.attendance.start_day==day and old.service.key in replacements:removed.add(old.id);terms.pop(old.id)
                if code in {'TS','T'} and old.attendance.start_day==day and old.service.code=='LB':
                    removed.add(old.id);terms.pop(old.id)
                    changed=event('LB_TS' if code=='TS' else 'LB',day,people=old.fixed_people);terms[changed.id]=changed
            term=event(code,day,people=fixed,attendance=attendance,reason='Importierter dokumentierter W16-Ersatz' if code=='W16' else '',allow_rules=allow_rules)
            old=terms.get(term.id)
            if old is not None and old!=replace(term,rule_override=old.rule_override):raise DomainError('Vorhandener Termin hat abweichende feste Personen oder Zeiten.')
            if old is not None:term=old
            terms[term.id]=term;requested.add(term.id)
        except (ValueError,KeyError,DomainError) as exc:errors.append(f'{day}/{code}: {exc}')
    if not allow_rules and any(b.id in removed for b in locks.values()):errors.append('Eine importierte Alternative würde einen fixierten Dienst entfernen; Fixierung ausdrücklich lösen.')
    retained=tuple(b for b in retained if b.id not in removed)
    updated=replace(inputs,events=tuple(terms.values()),absences=tuple(absences.values()),optional_ids=inputs.optional_ids-removed-requested)
    for (day,code),items in groups.items():
        term=terms.get(f'{day}/{code}')
        if term is None:continue
        for source,pid,row in items:
            if row['art']!='dienst':continue
            try:
                if bool(row.get('pause_von')) != bool(row.get('pause_bis')):raise DomainError('Beide Pausenzeitfelder gemeinsam ausfüllen.')
                choices=(term.assign(pid,(Interval.local(row['pause_von'],row['pause_bis']),),allow_rules=allow_rules),) if row.get('pause_von') and row.get('pause_bis') else automatic_pause_choices(term,pid,allow_rules=allow_rules)
                if not choices:raise DomainError('Keine zulässige konkrete Pause möglich.')
                block=choices[0]
                prior=next((b for b in retained if b.id==block.id and b.person_id==pid),None) or locks.get((block.id,pid))
                if prior is not None:block=prior
                if not any(b.id==block.id and b.person_id==pid for b in retained):retained+=(block,)
                if row.get('fixiert','ja').strip().lower() not in {'nein','0','false'}:locks[(block.id,pid)]=block
            except (ValueError,DomainError) as exc:errors.append(f'{source}: {exc}')
    updated=replace(updated,locked=tuple(b for b in locks.values() if b.id not in removed))
    # Persönliche Budgets gemeinsam mit schon gespeicherten Wünschen prüfen.
    if budgets is not None:
        for pid,owner in {(e.person_id,e.budget_month) for e in new_entries if e.kind!='urlaub'}:
            budget=budgets.get((pid,owner))
            mine=[e for e in absences.values() if e.person_id==pid and e.budget_month==owner and e.kind!='urlaub']
            if budget is None or sum(e.kind=='freiwunschtag' for e in mine)>budget.single_days or sum(e.kind=='wochenendwunsch' for e in mine)>budget.weekends:
                (notes if allow_rules else errors).append(f'{pid}/{owner}: Wunschbudget überschritten oder fehlt; Budget vor Übernahme ausdrücklich anpassen.')
    active=()
    if not errors:
        try:
            # Konkrete importierte Pausen zusätzlich als Kandidaten erhalten.
            updated=replace(updated,candidates=service_candidates(updated.events,updated.people)+retained)
            try:active=selected_events(updated,events or ())
            except DomainError as exc:
                if not allow_rules:raise
                notes.append(str(exc))
                active=tuple(e for e in updated.events if e.id not in updated.optional_ids or e.id in selected)
            core,calendar=verify(updated,retained,active_events=active)
            (notes if allow_rules else errors).extend(f'{i.event_id or "Kalender"} / {i.person_id}: {i.message}' for i in core.issues+calendar.issues)
        except (DomainError,ValueError) as exc:errors.append(str(exc))
    return PlanImport(replace(updated,manual_override=allow_rules,override_notes=tuple(notes) if allow_rules else ()),retained,active,tuple(dict.fromkeys(errors)),tuple(notes))
