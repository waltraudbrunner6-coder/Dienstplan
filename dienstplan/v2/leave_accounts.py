"""Lokale Urlaubskonten auf Schema 3, ohne implizite Bestände oder Migration.

Zwei Urlaubstage je vollem Beschäftigungsmonat; Teilmonate exakt anteilig nach
beschäftigten Kalendertagen. Die Zuordnung tatsächlicher
Urlaubstage kommt aus expliziten Datumsangaben; eine Stunde entspricht keinem
Urlaubstag. Bestätigte Monate haben Vorrang vor später veränderten Entwürfen.
"""
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction
import json

from .contracts import DateRange, Employment
from .entries import Entry
from .errors import DomainError
from .leave import _exact_days, _month, monthly_leave_entitlement
from .serialization import fingerprint, plain
from .time import Interval, midnight

_META_KEY = 'leave-accounts'
_FORMAT = 'v2-leave-accounts-1'


@dataclass(frozen=True, slots=True)
class LeaveAccountSetting:
    person_id: str
    start_month: str
    opening_days: Fraction

    def __post_init__(self):
        if not isinstance(self.person_id,str) or not self.person_id.strip():
            raise DomainError('Urlaubskonto benötigt eine eindeutige Personenkennung.')
        _month(self.start_month)
        object.__setattr__(self,'opening_days',_exact_days(self.opening_days))


def _fraction(value):
    if value is None:return None
    if isinstance(value,dict):
        try:
            a,b=value['numerator'],value['denominator']
            if type(a) is not int or type(b) is not int:raise ValueError
            return Fraction(a,b)
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:
            raise DomainError('Gespeicherter Urlaubsbestand ist beschädigt.') from exc
    return _exact_days(value)


def leave_account_settings(store):
    row=store.connection.execute('SELECT value FROM v2_meta WHERE key=?',(_META_KEY,)).fetchone()
    if row is None:return {}
    try:
        value=json.loads(row[0])
        if value.get('format')!=_FORMAT:raise DomainError('Unbekanntes Format der Urlaubskonten.')
        result={}
        for pid,item in value['accounts'].items():
            if item['person_id']!=pid:raise DomainError('Widersprüchliche Personenkennung im Urlaubskonto.')
            result[pid]=LeaveAccountSetting(pid,item['start_month'],_fraction(item['opening_days']))
        return result
    except (KeyError,TypeError,ValueError) as exc:
        if isinstance(exc,DomainError):raise
        raise DomainError('Urlaubskonten können nicht gelesen werden.') from exc


def save_leave_account(store,person_id,start_month,opening_days,*,expected_revision=None):
    """Expliziten Anfangsbestand speichern; ein unveränderter Wert ist ein No-op."""
    setting=LeaveAccountSetting(person_id,start_month,opening_days)
    with store.transaction():
        if expected_revision is not None and store.input_revision!=expected_revision:
            raise DomainError('Eingaben geändert; Urlaubskonto erneut öffnen.')
        settings=leave_account_settings(store)
        if settings.get(person_id)==setting:return setting
        settings[person_id]=setting
        payload=json.dumps(dict(format=_FORMAT,accounts=plain(settings)),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        store.connection.execute('INSERT INTO v2_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(_META_KEY,payload))
        store.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")
    return setting


@dataclass(frozen=True, slots=True)
class LeaveAccountRow:
    person_id: str
    month: str
    start_month: str | None
    opening_days: Fraction | None
    earned_days: Fraction | None
    used_days: int | None
    projected_days: Fraction | None
    monthly_earned_days: Fraction | None = None
    monthly_used_days: int | None = None
    known_earned_days: Fraction = Fraction(0)
    known_used_days: int = 0
    diagnostics: tuple[str,...] = ()
    confirmed: bool = False
    reconstructed: bool = False


def _entry(value):
    return Entry(value['id'],value['person_id'],value['kind'],
                 Interval(datetime.fromisoformat(value['span']['start']),datetime.fromisoformat(value['span']['end'])),
                 frozenset(date.fromisoformat(d) for d in value['credit_days']),value.get('comment',''),value.get('budget_month'),value.get('rule_override',False))


def _workspace_inputs(store):
    """Nur benötigte Daten lesen; keine tausenden Pausenkandidaten rekonstruieren."""
    result={}
    for key,payload in store.connection.execute("SELECT m.key,r.payload FROM v2_meta m JOIN v2_revisions r ON r.id=m.value WHERE m.key LIKE 'workspace:%'"):
        try:
            value=json.loads(payload)
            if value.get('format')!='v2-workspace-1' or fingerprint(value['snapshot'])!=value['revision_id']:
                raise DomainError('Ein Monatsstand für das Urlaubskonto ist beschädigt.')
            inputs=value['snapshot']['inputs']
            owner=f"{inputs['year']:04d}-{inputs['month']:02d}"
            if owner!=key.removeprefix('workspace:'):raise DomainError('Monat und gespeicherter Urlaubskonten-Arbeitsstand widersprechen einander.')
            result[owner]=inputs
        except (KeyError,TypeError,ValueError) as exc:
            if isinstance(exc,DomainError):raise
            raise DomainError('Monatsdaten für das Urlaubskonto sind nicht lesbar.') from exc
    return result


def _months(first,last):
    current=_month(first);stop=_month(last)
    while current<=stop:
        yield f'{current.year:04d}-{current.month:02d}'
        current=date(current.year+int(current.month==12),current.month%12+1,1)


def _frozen_row(raw):
    return LeaveAccountRow(raw['person_id'],raw['month'],raw.get('start_month'),_fraction(raw.get('opening_days')),
                           _fraction(raw.get('earned_days')),raw.get('used_days'),_fraction(raw.get('projected_days')),
                           _fraction(raw.get('monthly_earned_days')),raw.get('monthly_used_days'),_fraction(raw.get('known_earned_days',0)),raw.get('known_used_days',0),
                           tuple(raw.get('diagnostics',())),True,raw.get('reconstructed',False))


def leave_account_rows(store,people,year,month,*,current_entries=None):
    """Prognose vom expliziten Kontenstart bis zum Ende des gewählten Monats.

    Quelle je Monat: unveränderliche Bestätigung, aktueller übergebener Entwurf,
    eigener gespeicherter Monatsstand, sonst explizite globale/cross-month Daten.
    Ohne Monatsstand ist ein vergangener Verbrauch nicht als vollständig belegt;
    ein fehlender Monat wird nicht als erwiesen urlaubsfrei behandelt.
    """
    target=f'{year:04d}-{month:02d}';_month(target)
    people=tuple(people)
    if len({p.id for p in people})!=len(people):raise DomainError('Urlaubskonten benötigen eindeutige Personenkennungen.')
    settings=leave_account_settings(store)
    records={value['month']:value for _,value in store.confirmations()}
    workspaces=_workspace_inputs(store)
    global_entries=tuple(store.entries())
    current=None if current_entries is None else tuple(current_entries)
    cross=tuple(_entry(e) for value in workspaces.values() for e in value.get('absences',()) if e['kind']=='urlaub')
    result=[]
    for p in people:
        frozen=next((r for r in records.get(target,{}).get('leave_accounts',()) if r['person_id']==p.id),None)
        if frozen is not None:
            result.append(_frozen_row(frozen));continue
        setting=settings.get(p.id)
        if setting is None:
            result.append(LeaveAccountRow(p.id,target,None,None,None,None,None,diagnostics=('Urlaubskonto noch nicht eingerichtet: Anfangsbestand und Startmonat eingeben.',),confirmed=target in records,reconstructed=target in records));continue
        if setting.start_month>target:
            result.append(LeaveAccountRow(p.id,target,setting.start_month,setting.opening_days,None,None,None,diagnostics=(f'Urlaubskonto beginnt erst im Monat {setting.start_month}.',),confirmed=target in records,reconstructed=target in records));continue
        earned=Fraction(0);used=0;used_known=True;monthly_earned=monthly_used=None;notes=[];reconstructed=False;legacy_stats_missing=False
        for key in _months(setting.start_month,target):
            first=_month(key);last=date(first.year+int(first.month==12),first.month%12+1,1)
            span=Interval(midnight(first),midnight(last))
            confirmed=records.get(key)
            source=confirmed.get('inputs') if confirmed is not None else workspaces.get(key)
            missing_month=False
            if confirmed is not None:
                entries=tuple(_entry(e) for e in source.get('absences',()))
                if not any(r.get('person_id')==p.id for r in confirmed.get('leave_accounts',())):
                    reconstructed=True;legacy_stats_missing=True
            elif key==target and current is not None:entries=current
            elif source is not None:entries=tuple(_entry(e) for e in source.get('absences',()))
            else:
                entries=global_entries+cross;missing_month=True
            historic=next((person for person in (source or {}).get('people',()) if person['id']==p.id),None)
            employment=p.employment.dates if historic is None else DateRange(date.fromisoformat(historic['employment']['dates']['start']),date.fromisoformat(historic['employment']['dates']['end']))
            month_earned=monthly_leave_entitlement(Employment(p.id,employment),first.year,first.month)
            earned+=month_earned
            frozen_month=next((r for r in (confirmed or {}).get('leave_accounts',()) if r.get('person_id')==p.id),None)
            if frozen_month is not None and _fraction(frozen_month.get('monthly_earned_days')) != month_earned:
                reconstructed=True
                notes.append(f'{key}: Anspruch für die aktuelle Prognose anhand bestätigter Beschäftigungsdaten nach der geklärten Teilmonatsregel rekonstruiert; der alte Bestätigungsstand bleibt unverändert.')
            mine=tuple(e for e in entries if e.person_id==p.id and e.kind=='urlaub')
            days=frozenset(d for e in mine for d in e.credit_days if d.strftime('%Y-%m')==key)
            month_used=len(days);used+=month_used
            inactive=employment.end<=first or last<=employment.start
            if missing_month and not (inactive and not days):
                used_known=False;month_used=None;notes.append(f'{key}: kein gespeicherter Monatsstand; vollständiger Urlaubsverbrauch nicht belegt.')
            if any(not e.credit_days and e.span.overlaps(span) for e in mine):
                used_known=False;month_used=None;notes.append(f'{key}: Urlaubstage noch nicht ausgewählt; Verbrauch und Resturlaub sind unvollständig.')
            if key==target:monthly_earned,monthly_used=month_earned,month_used
        projected=setting.opening_days+earned-used if used_known else None
        if projected is not None and projected<0:notes.append('Geplanter Urlaub übersteigt den angegebenen Anspruch; negativer Rest ist eine Prognose, kein automatisches Buchungsverbot.')
        if legacy_stats_missing:notes.append('Alte Bestätigung ohne eingefrorenen Urlaubskontostand: anhand gespeicherter Urlaubstage und aktueller Kontovorgabe rekonstruiert.')
        result.append(LeaveAccountRow(p.id,target,setting.start_month,setting.opening_days,earned,used if used_known else None,projected,monthly_earned,monthly_used,earned,used,tuple(dict.fromkeys(notes)),target in records,reconstructed))
    return tuple(result)
