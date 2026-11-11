"""Enge, protokollierte Ausnahme für ausdrücklich bestätigte Wunschkonfiguration.

Die strenge Ergebnisprüfung bleibt unverändert. Eine genehmigte, unübliche
Wunsch-Datumsmenge ist kein harter Dienstkonflikt und darf weder fremde
Kandidaten noch die Optimierung sperren. Urlaub, Beschäftigung, Rechte, Ruhe,
Pausen und jede neue Zuteilung erhalten dadurch keine Ausnahme.
"""
from dataclasses import replace
from .errors import DomainError
from .validation import Issue
from .time import day_segments


def accepted_wish_warnings(inputs,issues):
    issues=tuple(issues)
    if not issues or not inputs.manual_override:return ()
    expected=set()
    for entry in inputs.absences:
        if entry.kind not in {'freiwunschtag','wochenendwunsch'} or not entry.rule_override:continue
        try:replace(entry,rule_override=False)
        except DomainError as exc:
            expected.add(Issue('overridden_rule',entry.person_id,entry.id,str(exc)))
    return tuple(issue for issue in issues if issue in expected)


def blocking_issues(inputs,issues):
    issues=tuple(issues)
    if not issues:return ()
    accepted=set(accepted_wish_warnings(inputs,issues))
    return tuple(issue for issue in issues if issue not in accepted)


def wish_warning_messages(inputs):
    if not inputs.manual_override:return ()
    names={p.id:p.name for p in inputs.people};messages=[]
    for entry in inputs.absences:
        if entry.kind not in {'freiwunschtag','wochenendwunsch'} or not entry.rule_override:continue
        try:replace(entry,rule_override=False)
        except DomainError as exc:
            reason=str(exc).replace("; zur Korrektur vormerken.",".")
            days=tuple(day for day,_ in day_segments(entry.span))
            dates=days[0].strftime('%d.%m.%Y')
            if len(days)>1:dates+=' bis '+days[-1].strftime('%d.%m.%Y')
            label='Freiwunsch' if entry.kind=='freiwunschtag' else 'Wochenendwunsch'
            messages.append(f'Genehmigte Wunsch-Ausnahme: {label} für {names.get(entry.person_id,entry.person_id)} ({entry.person_id}) am {dates}. Abweichung: {reason} Die Wunschkonfiguration bleibt aktiv; automatische Dienstregeln werden weiter geprüft.')
    return tuple(dict.fromkeys(messages))
