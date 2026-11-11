"""Urlaubstage, Stunden und explizite Anspruchskonten ohne Kalenderannahmen.

Ein angerechneter Tag bringt den an diesem Datum gültigen Wochenvertrag / 5.
Aus einem Abwesenheitsintervall wird keine Urlaubs-Tagesmenge abgeleitet.
Anspruchsmonate und Übertrag werden ausdrücklich übergeben, nicht aus lückenhafter
Historie erraten. Teilmonate werden nach bestätigter Vorgabe exakt anhand
der beschäftigten Kalendertage angerechnet.
"""
from dataclasses import dataclass
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from .accounting import leave_credits, round_minutes
from .errors import DomainError
from .time import Interval, day_segments, midnight

MONTHLY_ENTITLEMENT_DAYS = 2


def _month(value):
    try:
        first = date.fromisoformat(value + '-01')
    except (TypeError, ValueError) as exc:
        raise DomainError('Urlaubsmonat im Format YYYY-MM angeben.') from exc
    if value != f'{first.year:04d}-{first.month:02d}':
        raise DomainError('Urlaubsmonat im Format YYYY-MM angeben.')
    return first


def _month_span(year, month):
    if type(year) is not int or type(month) is not int:
        raise DomainError('Gültiges Jahr und gültigen Monat auswählen.')
    try:
        first = date(year, month, 1)
        end = date(year + int(month == 12), month % 12 + 1, 1)
    except (TypeError, ValueError) as exc:
        raise DomainError('Gültiges Jahr und gültigen Monat auswählen.') from exc
    return Interval(midnight(first), midnight(end))


def monthly_leave_entitlement(employment, year, month):
    """Exakte Urlaubstage: 2 × beschäftigte Kalendertage / Kalendertage im Monat.

    Beschäftigungsstart ist eingeschlossen und das Ende ausgeschlossen. Weder
    Vertragswochenstunden noch Wochentage/Feiertage verändern diese Tagesmenge.
    Die Rückgabe bleibt ungerundet, damit mehrmonatige Summen exakt bleiben.
    """
    _month_span(year, month)  # dieselbe strenge Validierung der Monatsgrenzen
    first = date(year, month, 1)
    end = date(year + int(month == 12), month % 12 + 1, 1)
    dates = employment.dates
    days = max(0, (min(end, dates.end) - max(first, dates.start)).days)
    return Fraction(MONTHLY_ENTITLEMENT_DAYS * days, calendar.monthrange(year, month)[1])


@dataclass(frozen=True, slots=True)
class LeaveMonthRow:
    person_id: str
    person_name: str
    month: str
    credit_days: frozenset[date]
    raw_credit_minutes: Fraction
    unknown_entry_ids: tuple[str, ...] = ()
    unknown_days: frozenset[date] = frozenset()
    diagnostics: tuple[str, ...] = ()

    @property
    def used_days(self):
        """Bekannte Tage; bei fehlenden Angaben ausdrücklich nur ein Teilbetrag."""
        return len(self.credit_days)

    @property
    def credits_known(self):
        return not self.unknown_entry_ids

    @property
    def credit_minutes(self):
        return round_minutes(self.raw_credit_minutes) if self.credits_known else None


def monthly_leave_rows(people, entries, year, month):
    """Je Person bekannte Tagesmengen und fehlende Auswahl sichtbar machen.

    Explizite Wochenend-/Feiertagsdaten zählen wie jedes explizite Datum. Ob sie
    ausgewählt werden sollen, entscheidet der Aufrufer anhand bestätigter Regeln.
    Überlappende Einträge zählen denselben Personen-/Kalendertag genau einmal.
    Ein leeres ``credit_days`` bedeutet nach dem bisherigen Datenmodell
    »Tagesauswahl fehlt« und niemals stillschweigend null Urlaubsgutschrift.
    """
    span = _month_span(year, month)
    key = f'{year:04d}-{month:02d}'
    people, entries = tuple(people), tuple(entries)
    persons = {p.id: p for p in people}
    if len(persons) != len(people):
        raise DomainError('Urlaubsübersicht benötigt eindeutige Personenkennungen.')
    leaves = tuple(e for e in entries if e.kind == 'urlaub')
    if any(e.person_id not in persons for e in leaves):
        raise DomainError('Urlaub verweist auf eine unbekannte Person.')
    rows = []
    for person in people:
        mine = tuple(e for e in leaves if e.person_id == person.id)
        days = frozenset(d for e in mine for d in e.credit_days
                         if (d.year, d.month) == (year, month))
        amounts = leave_credits(person.contracts, person.employment, days)
        raw = next((a.raw_minutes for a in amounts if a.month == key), Fraction(0))
        unknown_entries = tuple(e for e in mine if not e.credit_days and e.span.overlaps(span))
        unknown = tuple(sorted({e.id for e in unknown_entries}))
        missing_days = frozenset(d for e in unknown_entries
                                 for d, _ in day_segments(e.span) if (d.year, d.month) == (year, month))
        diagnostics = ()
        if unknown:
            dates = ', '.join(d.strftime('%d.%m.%Y') for d in sorted(missing_days))
            diagnostics = (f'{person.name} ({person.id}): Für den Urlaub am {dates} fehlen '
                           'die angerechneten Urlaubstage. Urlaub bearbeiten und die Tage auswählen; '
                           'pro ausgewähltem Tag werden die dort gültigen Wochenstunden ÷ 5 gutgeschrieben.',)
        rows.append(LeaveMonthRow(person.id, person.name, key, days, raw, unknown, missing_days, diagnostics))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class LeaveBalance:
    months: tuple[str, ...]
    opening_days: Fraction | None
    earned_days: Fraction
    used_days: int
    projected_days: Fraction | None
    carry_forward: bool
    diagnostics: tuple[str, ...] = ()


def _exact_days(value):
    if isinstance(value, (float, bool)):
        raise DomainError('Urlaubsbestand als exakten Dezimaltext, Decimal oder Fraction eingeben.')
    try:
        if isinstance(value, Fraction):return value
        if isinstance(value, str) and '/' in value:return Fraction(value.strip())
        return Fraction(Decimal(str(value).replace(',', '.')))
    except (InvalidOperation, ValueError, OverflowError, ZeroDivisionError) as exc:
        raise DomainError('Urlaubsbestand muss eine endliche Zahl sein.') from exc


def leave_balance(opening_days, used_days, *, months, carry_forward, employment=None):
    """Zwei Tage je ausdrücklich anrechenbarem Monat; kein Verbrauchs-Hartlimit.

    Die Liste ``months`` ist eine ausdrückliche Gutschriftvorgabe. Insbesondere
    werden keine fehlenden Monate ergänzt. Mit ausdrücklich übergebener
    Beschäftigung werden Teilmonate anteilig
    berücksichtigt; ohne diese Angabe sind die Monate ausdrücklich als volle
    Anspruchsmonate vorgegeben. Bei fehlendem Anfangsbestand mit Übertrag bleibt
    der Endbestand unbekannt. Negative Bestände sind darstellbar und werden als Hinweis ausgewiesen.
    """
    try:
        months = tuple(months)
    except TypeError as exc:
        raise DomainError('Anrechenbare Urlaubsmonate ausdrücklich angeben.') from exc
    if not months or any(not isinstance(m, str) for m in months):
        raise DomainError('Anrechenbare Urlaubsmonate ausdrücklich angeben.')
    for month in months:
        _month(month)
    if len(set(months)) != len(months):
        raise DomainError('Urlaubsmonate dürfen nicht doppelt gutgeschrieben werden.')
    if type(carry_forward) is not bool:
        raise DomainError('Urlaubsübertrag ausdrücklich auswählen.')
    if type(used_days) is not int or used_days < 0:
        raise DomainError('Verbrauchte Urlaubstage müssen eine nicht negative ganze Zahl sein.')
    opening = None if opening_days is None else _exact_days(opening_days)
    if not carry_forward:
        if len(months) != 1 or opening not in (None, Fraction(0)):
            raise DomainError('Ohne Übertrag genau einen Monat und keinen Anfangsbestand verwenden.')
        opening = Fraction(0)
    earned = (Fraction(MONTHLY_ENTITLEMENT_DAYS * len(months)) if employment is None else
              sum((monthly_leave_entitlement(employment, _month(key).year, _month(key).month) for key in months), Fraction(0)))
    projected = None if opening is None else opening + earned - used_days
    diagnostics = ()
    if projected is None:
        diagnostics = ('Urlaubsanfangsbestand fehlt; der voraussichtliche Resturlaub ist noch unbekannt.',)
    elif projected < 0:
        diagnostics = ('Die geplanten Urlaubstage übersteigen den angegebenen Anspruch. '
                       'Der negative Bestand ist eine Prognose und kein automatisches Buchungsverbot.',)
    return LeaveBalance(tuple(sorted(months)), opening, earned, used_days, projected, carry_forward, diagnostics)


def missing_leave_message(people, entries, year, month):
    """Handlungsfähige Diagnose statt einer vermeintlichen Nullgutschrift."""
    details=tuple(message for row in monthly_leave_rows(people,entries,year,month) for message in row.diagnostics)
    return 'Urlaubsangaben noch ungeklärt. '+ '\n'.join(details) if details else ''
