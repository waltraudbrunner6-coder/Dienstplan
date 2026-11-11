"""Unveränderliche, unabhängig geprüfte Bestätigungsfakten für Test-/Reviewstände."""
from datetime import date
import json

from .errors import DomainError
from .reporting import hours_rows,quantity_rows,shares
from .serialization import fingerprint,plain
from .wishes import WishHistory,wish_rows


def month_keys(start,end):
    current=date.fromisoformat(start+'-01');stop=date.fromisoformat(end+'-01');result=[]
    while current<stop:
        result.append(current.strftime('%Y-%m'))
        current=date(current.year+int(current.month==12),current.month%12+1,1)
    return tuple(result)


def request_key(inputs,blocks,events,accounts,wish_policy,fairness_policy,holidays,target_profile,month_profile,allow_violations=False):
    base=(inputs,tuple(blocks),tuple(events),tuple(accounts),wish_policy,fairness_policy,
                        frozenset(holidays),target_profile,month_profile)
    return fingerprint((base,"confirmation_override",True) if allow_violations else base)


def confirmation(inputs,blocks,events,*,accounts,wish_policy,fairness_policy,holidays,
                 history,target_profile,month_profile,synthetic,allow_violations=False):
    # F01/F02/F04/F14 sind nicht durch technische Rechenbeispiele entschieden.
    if synthetic is not True or not wish_policy.synthetic or not fairness_policy.synthetic:
        raise DomainError('Produktive V2-Bestätigung ist noch nicht freigegeben; nur ausdrückliche Testbestätigung.')
    from .solver import verify
    blocks=tuple(blocks);events=tuple(events);accounts=tuple(accounts);holidays=frozenset(holidays)
    core,calendar=verify(inputs,blocks,active_events=events)
    if any(i.rule in {'identity','reference','duplicate','template'} for i in core.issues):raise DomainError('Technisch widersprüchliche Kennungen oder Zuteilungen können nicht bestätigt werden.')
    if not allow_violations and (core.issues or calendar.issues):raise DomainError('Bestätigung wegen verbindlicher Konflikte abgelehnt: '+ '; '.join(i.message for i in core.issues+calendar.issues))
    if not allow_violations and core.open_slots:raise DomainError('Offene Plätze können hier nur als Entwurf gespeichert werden.')
    year,month=inputs.year,inputs.month;month_key=f'{year:04d}-{month:02d}'
    current_events=tuple(e for e in events if (e.attendance.start_day.year,e.attendance.start_day.month)==(year,month))
    current_ids={e.id for e in current_events};current_blocks=tuple(b for b in blocks if b.id in current_ids)
    all_blocks=tuple({(b.id,b.person_id):b for b in inputs.boundary+blocks}.values())
    facts=dict(format='v2-confirmation-1',month=month_key,scope='Synthetischer Teststand; keine produktive V2-Umschaltung',
               request_fingerprint=request_key(inputs,blocks,events,accounts,wish_policy,fairness_policy,holidays,target_profile,month_profile,allow_violations),
               confirmation_override=allow_violations,
               warnings=list(dict.fromkeys(tuple(i.message for i in core.issues+calendar.issues)+tuple(f'{id}: {count} offene Plätze' for id,count in core.open_slots)+inputs.unchecked+calendar.unchecked+inputs.override_notes)),
               issues=plain(core.issues+calendar.issues),open_slots=plain(core.open_slots),
               input_fingerprint=inputs.fingerprint,inputs=plain(inputs),events=plain(current_events),blocks=plain(current_blocks),
               accounts=plain(accounts),wish_policy=plain(wish_policy),fairness_policy=plain(fairness_policy),
               target_profile=target_profile,month_profile=month_profile,
               history_basis=dict(confirmations=history.confirmation_ids,missing=history.missing),
               wishes=plain(wish_rows(inputs.people,inputs.absences,current_events,all_blocks,policy=wish_policy,history=history)),
               hours=plain(hours_rows(inputs.people,all_blocks,inputs.absences,year,month,accounts=accounts,
                                      target_profile=target_profile,month_profile=month_profile)),
               shares=plain(shares(inputs.people,current_events,current_blocks,policy=fairness_policy,absences=inputs.absences)),
               quantities=plain(tuple(q for q in quantity_rows(all_blocks,holidays) if (q.day.year,q.day.month)==(year,month))),
               unchecked=tuple(dict.fromkeys(inputs.unchecked+calendar.unchecked)),
               quota_reservations={q.id:sorted(e.id for e in events if e.service.code==q.code and q.dates.includes(e.attendance.start_day)) for q in inputs.quotas})
    if any(not r['credits_known'] for r in facts['hours']):
        raise DomainError('Urlaubsgutschrifttage sind ungeklärt; keine Bestätigung mit angenommener Nullgutschrift.')
    from .presentation import hours_text
    facts['warnings']+= [f"{r['person_id']}: Abweichung vom Arbeitsziel {hours_text(r['deviation'])} h" for r in facts['hours'] if r['credits_known'] and r['deviation']]
    facts=plain(facts)
    facts['content_fingerprint']=fingerprint(facts)
    return facts


def checked_payload(text):
    value=json.loads(text)
    if value.get('format')!='v2-confirmation-1':raise DomainError('Unbekanntes Bestätigungsformat.')
    expected=value.pop('content_fingerprint',None)
    if fingerprint(value)!=expected:raise DomainError('Bestätigungsdaten stimmen nicht mit ihrem Fingerprint überein.')
    value['content_fingerprint']=expected
    return value


def wish_history(records,month,*,policy,legacy_missing=()):
    chosen=tuple((id,value) for id,value in records if policy.history_start<=value['month']<month)
    keys=frozenset(tuple(k) for _,v in chosen for row in v['wishes'] for k in row['violated'])
    present={v['month'] for _,v in chosen}
    missing=tuple(f'{m}: kein bestätigter V2-Wunschstand' for m in month_keys(policy.history_start,month) if m not in present)
    return WishHistory(keys,tuple(id for id,_ in chosen),tuple(legacy_missing)+missing)


def historical_shares(records,*,start,month):
    """Nur eingefrorene alte Anteile summieren, niemals neue Verträge anwenden."""
    from fractions import Fraction
    from .reporting import ShareRow
    totals={}
    for _,record in records:
        if not start<=record['month']<month:continue
        for row in record['shares']:
            key=row['person_id'],row['code'];values=totals.setdefault(key,[0,0,Fraction(0),Fraction(0)])
            values[0]+=row['count'];values[1]+=row['work_minutes']
            for index,name in ((2,'expected_count'),(3,'expected_minutes')):
                raw=row[name];values[index]+=Fraction(raw['numerator'],raw['denominator'])
    return tuple(ShareRow(*key,*values) for key,values in sorted(totals.items()))
