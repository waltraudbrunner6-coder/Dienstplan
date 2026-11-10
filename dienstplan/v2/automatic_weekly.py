"""Explizite Wochenkonfiguration und gemeinsame Reservierung von Randwochen."""
from dataclasses import replace
from datetime import date,timedelta
import calendar

from .calendar_rules import WeekPolicy,WeekQuota,dates,horizon
from .contracts import DateRange
from .weekly import weekly_options
from .application import service_candidates
from .errors import DomainError


def automatic_weekly(inputs,*,snapshots=(),full_weeks_only=False):
    first=date(inputs.year,inputs.month,1);end=date(inputs.year+int(inputs.month==12),inputs.month%12+1,1)
    monday=first-timedelta(days=first.weekday());quotas=[]
    while monday<end:
        last=monday+timedelta(days=7)
        if not full_weeks_only or (first<=monday and last<=end):
            iso=monday.isocalendar()
            for code,count in (('WL',2),('BK',1)):
                quotas.append(WeekQuota(f'{iso.year}-W{iso.week:02d}/{code}',code,DateRange(monday,last),count,monday.strftime('%Y-%m')))
        monday=last
    policy=WeekPolicy('week_start','start_day','Betriebliche Eingabe: ISO Mo–So, 2 WL / 1 BK; '+('nur volle Monatswochen' if full_weeks_only else 'gemeinsame Randwochen'))
    options=weekly_options(quotas)
    terms={e.id:e for e in inputs.events if e.service.code not in {'WL','BK'} or e.id not in inputs.optional_ids}
    options_by_id={e.id:e for e in options.events}
    optional=set(options_by_id)-terms.keys()
    terms.update(options_by_id)
    locks={(b.id,b.person_id):b for b in inputs.locked};boundary={(b.id,b.person_id):b for b in inputs.boundary}
    known=set(inputs.known_days);notes=[];people={p.id for p in inputs.people}
    for previous,_,blocks,active in snapshots:
        if active is None or (previous.year,previous.month)==(inputs.year,inputs.month):continue
        shared={q.id for q in quotas}&{q.id for q in previous.quotas}
        for q in (q for q in quotas if q.id in shared):
            chosen=[e for e in active if e.service.code==q.code and q.dates.includes(e.attendance.start_day)]
            if len(chosen)!=q.required:raise DomainError('Gespeicherte Randwochenquote passt nicht zur neuen Regel; zuerst abstimmen.')
            for id,e in tuple(terms.items()):
                if e.service.code==q.code and q.dates.includes(e.attendance.start_day) and id not in {v.id for v in chosen}:
                    if id not in optional:raise DomainError('Fester Termin widerspricht einer gespeicherten Randwoche.')
                    terms.pop(id);optional.discard(id)
            optional.difference_update(e.id for e in chosen)
            for b in blocks:
                if b.id in {e.id for e in chosen}:
                    if b.person_id not in people:raise DomainError('Person einer gemeinsamen Randwoche fehlt im aktuellen Team.')
                    prior=locks.get((b.id,b.person_id))
                    if prior is not None and prior!=b:raise DomainError('Widersprüchliche konkrete Randwochenpause.')
                    locks[b.id,b.person_id]=b
        # Auch Nachbarpläne ohne neues Wochenprofil enthalten verbindliche
        # beobachtete Dienste/Ruhezeiten. Nicht als unbekannte Freizeit behandeln.
        for term in active:
            relevant=any(q.code==term.service.code and q.dates.includes(term.attendance.start_day) for q in quotas)
            relevant=relevant or ((term.attendance.start_day.year,term.attendance.start_day.month)==(inputs.year,inputs.month) and term.service.code in {'BK','WL'})
            if relevant and term.service.code in {'BK','WL'}:
                terms[term.id]=term;optional.discard(term.id)
                for b in blocks:
                    if b.id==term.id:
                        if b.person_id not in people:raise DomainError('Person aus einem bekannten Randwochentermin fehlt im Team.')
                        locks[b.id,b.person_id]=b
        if shared:
            notes.append(f'Gemeinsame Randwoche aus {previous.year}-{previous.month:02d} übernommen; bestehende Termine und Zuteilungen bleiben fixiert.')
        for b in blocks:
            if b.person_id in people and any(horizon(inputs.year,inputs.month).includes(d) for d in b.occupied_days):
                boundary[b.id,b.person_id]=b
        known.update((p,d) for p,d in previous.known_days if p in people)
    errors=tuple(i.message for i in options.rejected)
    unchecked=tuple(n for n in inputs.unchecked if not n.startswith(('F06/F07:','F06:')))+tuple(notes)+errors
    if full_weeks_only:unchecked+=('Randwochen sind ausdrücklich aus der automatischen Quote ausgeschlossen.',)
    updated=replace(inputs,events=tuple(terms.values()),optional_ids=frozenset(optional),quotas=tuple(quotas),week_policy=policy,
                    locked=tuple(locks.values()),boundary=tuple(boundary.values()),known_days=frozenset(known),unchecked=unchecked)
    from .plan_import import selected_events
    selected_events(updated)  # Widersprüchliche feste Datumsquoten vor jeder Speicherung abweisen.
    return replace(updated,candidates=service_candidates(updated.events,updated.people)+updated.locked)


def check_shared_weeks(inputs,blocks,events,snapshots):
    if events is None:return
    for previous,_,old_blocks,active in snapshots:
        if active is None or (previous.year,previous.month)==(inputs.year,inputs.month):continue
        relevant={e.id for e in active if e.service.code in {'BK','WL'} and (
            (e.attendance.start_day.year,e.attendance.start_day.month)==(inputs.year,inputs.month)
            or any(q.code==e.service.code and q.dates.includes(e.attendance.start_day) for q in inputs.quotas))}
        current={e.id for e in events}
        if not relevant<=current or not {b for b in old_blocks if b.id in relevant}<=set(blocks):
            raise DomainError('Bekannte BK/WL-Dienste einer Randwoche des Nachbarmonats fehlen oder wurden verändert.')
        common={q.id for q in inputs.quotas}&{q.id for q in previous.quotas}
        for q in (q for q in inputs.quotas if q.id in common):
            old={e.id for e in active if e.service.code==q.code and q.dates.includes(e.attendance.start_day)}
            new={e.id for e in events if e.service.code==q.code and q.dates.includes(e.attendance.start_day)}
            if new!=old or not {b for b in old_blocks if b.id in old}<={b for b in blocks if b.id in new}:
                raise DomainError(f'Randwoche {q.id} widerspricht dem gespeicherten Nachbarmonat; gemeinsame Vorgaben über „BK/WL automatisch“ übernehmen.')
