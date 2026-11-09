"""Typisierte Abwesenheiten/Wünsche und vollständige CSV-Korrekturstapel."""
import csv
from dataclasses import dataclass, replace
from datetime import date, timedelta
from hashlib import sha256
import io
import json

from .errors import DomainError
from .time import Interval, day_segments, midnight

KINDS=frozenset({"urlaub","freiwunschtag","wochenendwunsch"})
HEADER=("format_version","person_id","entry_id","typ","von","bis","gutschrifttage","kommentar")


@dataclass(frozen=True, slots=True)
class Entry:
    id: str
    person_id: str
    kind: str
    span: Interval
    credit_days: frozenset[date] = frozenset()
    comment: str = ""
    budget_month: str | None = None

    def __post_init__(self):
        object.__setattr__(self,"credit_days",frozenset(self.credit_days))
        if not self.id or not self.person_id or self.kind not in KINDS:
            raise DomainError("Eintrag benötigt Kennung, Person und eindeutigen V2-Typ.")
        days=tuple(d for d,_ in day_segments(self.span))
        if self.kind!="urlaub":
            if self.credit_days:
                raise DomainError("Nur Urlaub darf Gutschrifttage enthalten.")
            if any(d.weekday()==3 for d in days):
                raise DomainError("Freiwunsch enthält einen Donnerstag; zur Korrektur vormerken.")
            if self.kind=="freiwunschtag" and len(days)!=1:
                raise DomainError("Ein einzelner Freiwunschtag darf nur einen Kalendertag betreffen.")
            if self.kind=="wochenendwunsch" and (len(days)!=2 or days[0].weekday()!=5 or
                    self.span.start!=midnight(days[0]) or self.span.end!=midnight(days[-1]+timedelta(days=1))):
                raise DomainError("Wochenendwunsch muss das vollständige Samstag/Sonntag-Wochenende umfassen.")
            owner=self.budget_month or (days[0].strftime('%Y-%m') if self.kind=='freiwunschtag' else None)
            if owner not in {d.strftime('%Y-%m') for d in days}:
                raise DomainError("Wunsch benötigt einen ausdrücklich passenden Budgetmonat.")
            object.__setattr__(self,'budget_month',owner)
        if any(type(d) is not date or d not in days for d in self.credit_days):
            raise DomainError("Gutschrifttag liegt nicht im Urlaubszeitraum.")

    @property
    def identity(self):
        return (self.person_id,self.kind,self.span.start.isoformat(),self.span.end.isoformat())


@dataclass(frozen=True, slots=True)
class WishBudget:
    single_days: int
    weekends: int = 1

    def __post_init__(self):
        if any(type(n) is not int or n<0 for n in (self.single_days,self.weekends)):
            raise DomainError("Wunschbudgets müssen nicht negative ganze Zahlen sein.")


@dataclass(frozen=True, slots=True)
class DraftRow:
    line: int
    fields: tuple[tuple[str,str], ...]
    errors: tuple[str, ...] = ()
    proposed: Entry | None = None


@dataclass(frozen=True, slots=True)
class CorrectionBatch:
    original_text: str
    rows: tuple[DraftRow, ...]
    errors: tuple[str, ...] = ()
    parse_errors: tuple[str, ...] = ()

    @property
    def ready(self):
        return not self.errors and all(not r.errors and r.proposed is not None for r in self.rows)

    def promote(self) -> tuple[Entry, ...]:
        if not self.ready:
            raise DomainError("Stapel zur Korrektur vorgemerkt; keine aktive Teilübernahme erlaubt.")
        return tuple({r.proposed.identity:r.proposed for r in self.rows}.values())


def _check_rows(original, rows, existing, budgets, month, parse_errors=()):
    result=[]
    by_identity={e.identity:e for e in existing}
    by_id={e.id:e for e in existing}
    errors=list(parse_errors)
    for row in rows:
        values=dict(row.fields)
        try:
            if values.get('format_version')!='2':
                raise DomainError("Altformat bzw. unbekannte Formatversion; ausdrückliche Typzuordnung benötigt.")
            kind=values['typ'];person=values['person_id']
            span=Interval.local(values['von'],values['bis'])
            credits=frozenset(date.fromisoformat(d) for d in values.get('gutschrifttage','').split('|') if d)
            key=json.dumps([person,kind,span.start.isoformat(),span.end.isoformat()],ensure_ascii=False)
            ident=values.get('entry_id') or sha256(key.encode()).hexdigest()
            entry=Entry(ident,person,kind,span,credits,values.get('kommentar',''),month if kind=='wochenendwunsch' else None)
            old=by_id.get(ident)
            if old is not None and (old.identity!=entry.identity or old.credit_days!=entry.credit_days):
                raise DomainError("Vorhandene Kennung hat anderen Inhalt; Änderung ausdrücklich prüfen.")
            duplicate=by_identity.get(entry.identity)
            if duplicate is not None:
                if duplicate.credit_days!=entry.credit_days:
                    raise DomainError("Abweichende Gutschrifttage bei gleichem Zeitraum; Korrektur benötigt.")
                entry=duplicate
            by_identity[entry.identity]=entry;by_id[entry.id]=entry
            result.append(replace(row,errors=(),proposed=entry))
        except (DomainError,KeyError,ValueError,TypeError) as exc:
            result.append(replace(row,errors=(f"Zeile {row.line}: {exc}",),proposed=None))
    # Bestehende und neue aktive Identitäten gemeinsam; keine Teilaktivierung.
    touched={(r.proposed.person_id,r.proposed.budget_month) for r in result if r.proposed is not None and r.proposed.kind!='urlaub'}
    for person,owner in touched:
        relevant=[e for e in by_identity.values() if e.person_id==person and e.kind!='urlaub' and e.budget_month==owner]
        budget=budgets.get((person,owner))
        if budget is None:
            errors.append(f"Wunschbudget für {person}/{owner} fehlt.")
        elif (sum(e.kind=='freiwunschtag' for e in relevant)>budget.single_days or
              sum(e.kind=='wochenendwunsch' for e in relevant)>budget.weekends):
            errors.append(f"Gemeinsames Wunschbudget für {person}/{owner} überschritten.")
    return CorrectionBatch(original,tuple(result),tuple(errors),tuple(parse_errors))


def preview(text: str, *, existing: tuple[Entry, ...] = (), budgets=None, month: str) -> CorrectionBatch:
    original=text
    text=text.removeprefix('\ufeff')
    delimiter=';' if text.splitlines() and text.splitlines()[0].count(';')>text.splitlines()[0].count(',') else ','
    rows=[]
    try:
        reader=csv.DictReader(io.StringIO(text,newline=''),delimiter=delimiter,strict=True)
        if set(reader.fieldnames or ())!=set(HEADER) or len(reader.fieldnames or ())!=len(HEADER):
            errors=("Kopfzeile: CSV-Format 2 erforderlich; Altformat nicht automatisch in Urlaub umdeuten.",)
            return CorrectionBatch(original,(),errors,errors)
        for values in reader:
            if None in values or any(v is None for v in values.values()):
                errors=(f"Zeile {reader.line_num}: falsche Spaltenzahl; gesamter Stapel zur Korrektur.",)
                return CorrectionBatch(original,tuple(rows),errors,errors)
            rows.append(DraftRow(reader.line_num,tuple((k,v.strip()) for k,v in values.items())))
    except csv.Error as exc:
        errors=(f"CSV zur Korrektur: {exc}",)
        return CorrectionBatch(original,tuple(rows),errors,errors)
    return _check_rows(original,rows,existing,budgets or {},month)


def correct(batch: CorrectionBatch, line: int, changes: dict[str,str], *, existing=(), budgets=None, month: str) -> CorrectionBatch:
    if any(k not in HEADER for k in changes) or not any(r.line==line for r in batch.rows):
        raise DomainError("Unbekannte Korrekturzeile bzw. Spalte.")
    rows=[replace(r,fields=tuple({**dict(r.fields),**changes}.items())) if r.line==line else r for r in batch.rows]
    return _check_rows(batch.original_text,rows,existing,budgets or {},month,batch.parse_errors)
