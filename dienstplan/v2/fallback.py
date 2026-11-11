"""KC15 als explizit geprüfte Ersatzwahl für ein KC10-/KC16-Tagespaar.

Ein Ersatz ist kein vollständig besetztes reguläres Tagespaar. Er benötigt eine
reale Zuteilung; eine leere Alternative darf keinen Bedarf verschwinden lassen.
Die Zahl gewählter Ersatztermine folgt direkt nach der offenen Besetzung und
vor Wünschen/Stundenfairness. Nur ein bewiesenes Optimum dieser Stufe beweist,
dass bei gleicher Besetzung keine Lösung mit weniger Ersatzterminen existiert.
"""
from dataclasses import dataclass,replace
from .errors import DomainError
from .validation import Issue


@dataclass(frozen=True,slots=True)
class FallbackGroup:
    id: str
    regular_ids: tuple[str,...]
    replacement_id: str

    def __post_init__(self):
        object.__setattr__(self,'regular_ids',tuple(sorted(self.regular_ids)))
        if not self.id or len(self.regular_ids)!=2 or len(set(self.regular_ids))!=2 or self.replacement_id in self.regular_ids:
            raise DomainError('KC15-Ersatz benötigt ein eindeutiges KC10-/KC16-Paar.')

    @property
    def members(self):return self.regular_ids+(self.replacement_id,)


def with_kc15_fallbacks(inputs):
    """Reguläre vorhandene Paare erhalten und passende Ersatzoptionen ergänzen.

    Einzelne ausdrücklich deaktivierte KC10/16-Termine bilden kein Paar und
    werden nicht durch einen neuen Dienst wiederhergestellt. Fixierte reguläre
    Zuteilungen erzwingen im Solver weiterhin die reguläre Wahl.
    """
    from .catalog import event
    from .application import service_candidates
    terms={e.id:e for e in inputs.events};groups={g.id:g for g in inputs.fallbacks}
    by_day={}
    for term in inputs.events:
        if term.service.code in {'KC10','KC16'}:by_day.setdefault(term.attendance.start_day,{})[term.service.code]=term
    additions=[]
    for day,values in sorted(by_day.items()):
        if set(values)!={'KC10','KC16'} or any(e.fixed_people for e in values.values()):continue
        extra=event('KC15',day)
        if extra.id in terms and not any(g.replacement_id==extra.id for g in inputs.fallbacks):
            raise DomainError('KC15 und reguläre KC10/KC16 stehen bereits gleichzeitig fest; vor Planung korrigieren.')
        group=FallbackGroup(str(day)+'/KC15-Ersatz',(values['KC10'].id,values['KC16'].id),extra.id)
        groups[group.id]=group
        if extra.id not in terms:terms[extra.id]=extra;additions.append(extra)
    optional=set(inputs.optional_ids)
    for group in groups.values():optional.update(group.members)
    return replace(inputs,events=tuple(terms.values()),optional_ids=frozenset(optional),fallbacks=tuple(groups.values()),
                   candidates=inputs.candidates+service_candidates(tuple(additions),inputs.people))


def validate_groups(inputs):
    terms={e.id:e for e in inputs.events};seen=set()
    if len({g.id for g in inputs.fallbacks})!=len(inputs.fallbacks):raise DomainError('Doppelte KC15-Ersatzgruppe.')
    for group in inputs.fallbacks:
        if seen&set(group.members):raise DomainError('Ein Dienst gehört zu mehreren KC15-Ersatzgruppen.')
        seen.update(group.members)
        if not set(group.members)<=terms.keys() or not set(group.members)<=inputs.optional_ids:
            raise DomainError('KC15-Ersatzoptionen fehlen oder sind nicht als Alternativen markiert.')
        a,b,c=(terms[k] for k in group.members)
        if {a.service.code,b.service.code}!={'KC10','KC16'} or c.service.code!='KC15' or len({e.attendance.start_day for e in (a,b,c)})!=1:
            raise DomainError('KC15 ersetzt ausschließlich KC10 und KC16 desselben Startdatums.')
        if (a.service.staff,b.service.staff,c.service.staff)!=(1,1,1):raise DomainError('KC15-Ersatz passt nicht zu den Besetzungszahlen.')
    return frozenset(seen)


def default_fallback_events(inputs,preferred=()):
    """Konkrete Vorschau: regulär, außer ein gespeicherter/gesperrter Ersatz gilt."""
    terms={e.id:e for e in inputs.events};preferred={e.id for e in preferred};locked={b.id for b in inputs.locked}
    selected=[]
    for group in inputs.fallbacks:
        replacement=(group.replacement_id in preferred or group.replacement_id in locked) and not (set(group.regular_ids)&locked)
        selected.extend(terms[k] for k in ((group.replacement_id,) if replacement else group.regular_ids))
    return tuple(selected)


def check_fallbacks(inputs,events,blocks):
    selected={e.id for e in events};issues=[]
    for group in inputs.fallbacks:
        chosen=selected&set(group.members)
        if chosen not in (set(group.regular_ids),{group.replacement_id}):
            issues.append(Issue('kc15_choice','',group.id,'Entweder KC10 und KC16 oder genau der Ersatzdienst KC15 müssen gewählt sein.'))
        if group.replacement_id in chosen and not any(b.id==group.replacement_id for b in blocks):
            issues.append(Issue('kc15_empty','',group.replacement_id,'Ein leerer KC15 darf die offenen regulären Dienste nicht verdecken.'))
    return tuple(issues)


def with_fallback_objective(inputs,events,values):
    values=tuple(values)
    if not inputs.fallbacks:return values
    ids={e.id for e in events};count=sum(g.replacement_id in ids for g in inputs.fallbacks)
    return values[:1]+(('kc15_replacements',count),)+values[1:]


def with_fallback_model_objective(inputs,y,goals):
    goals=tuple(goals)
    if not inputs.fallbacks:return goals
    return goals[:1]+(('kc15_replacements',sum(y[g.replacement_id] for g in inputs.fallbacks)),)+goals[1:]


def fallback_notes(inputs,events):
    ids={e.id for e in events}
    return tuple(f'{g.replacement_id}: KC15-Ersatz 15:00–00:00 mit einer Person statt KC10 und KC16; reguläre Tagesbesetzung ersetzt.' for g in inputs.fallbacks if g.replacement_id in ids)


def dissolve_fallback_groups(inputs,affected_ids,*,keep_replacement_ids=()):
    """Vor einer ausdrücklichen Terminänderung betroffene Alternativen auflösen.

    Standardmäßig wird die reguläre Variante behalten. Ein ausdrücklich
    übergebener gewählter Ersatz bleibt stattdessen als normaler fester Termin
    erhalten. Der Aufrufer führt danach seine eigentliche Terminänderung aus.
    """
    affected=set(affected_ids);keep=set(keep_replacement_ids)
    touched=tuple(g for g in inputs.fallbacks if affected&set(g.members))
    if not touched:return inputs
    remove=set();optional=set(inputs.optional_ids)
    for group in touched:
        optional.difference_update(group.members)
        remove.update(group.regular_ids if group.replacement_id in keep else (group.replacement_id,))
    coverage=tuple(replace(r,relief_event_ids=tuple(k for k in r.relief_event_ids if k not in remove))
                   for r in inputs.coverage if r.event_id not in remove)
    return replace(inputs,events=tuple(e for e in inputs.events if e.id not in remove),
                   candidates=tuple(b for b in inputs.candidates if b.id not in remove),
                   locked=tuple(b for b in inputs.locked if b.id not in remove),
                   optional_ids=frozenset(optional-remove),fallbacks=tuple(g for g in inputs.fallbacks if g not in touched),coverage=coverage)
