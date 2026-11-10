"""Dauerhafte Monatsanwendung: Katalogstandard statt des Vier-Termine-Teststands."""
from datetime import date

from .accounting import MonthAccount
from .calendar_rules import dates
from .catalog import CalendarInput, month_calendar
from .contracts import DateRange
from .objectives import ObjectiveProfile
from .reporting import FairnessPolicy
from .wishes import WishPolicy
from .pauses import PausePolicy, pause_candidates
from .solver import PlanningInput


OPEN_PROFILE = 'Monatsplanung – Rechenannahmen noch nicht ausgewählt'
SELECTED_PROFILE = 'Monatsplanung – ausdrücklich gewähltes technisches Rechenprofil S0/M0/E0'


def service_candidates(terms, people):
    """Konkrete halbstündliche Pausenvarianten; keine erfundene R-Bewertung."""
    return tuple(block for term in terms for person in people
                 if term.service.code != 'R'
                 and not person.eligibility_errors(term.service.code, term.attendance)
                 and (not term.fixed_people or person.id in term.fixed_people)
                 for block in pause_candidates(term, person.id,
                     policy=PausePolicy('Pausenraster 0,5 h; Abdeckungsprofil ungeklärt', (term.attendance,), 30)))


def standard_month(year, month, *, people=(), accounts=(), settings=None, absences=()):
    """Bestätigte Tagesmuster automatisch; unbekannte Sonderdaten bleiben sichtbar."""
    calendar = month_calendar(year, month, settings or CalendarInput())
    # Nur das aktuelle, hier vollständig bearbeitete Fenster gilt als bekannt.
    # Eine fehlende Nachbarmonatsplanung wird ausdrücklich NICHT als frei gesetzt.
    span = DateRange(date(year, month, 1), date(year + int(month == 12), month % 12 + 1, 1))
    inputs = PlanningInput(tuple(people), calendar.events, service_candidates(calendar.events, people),
                           year, month, frozenset((p.id, d) for p in people for d in dates(span)),
                           None, OPEN_PROFILE, absences=tuple(absences),
                           unchecked=calendar.missing + ('F01/F03/F04/F10/F12/F13: Rechts-, Abdeckungs-, Abrechnungs- und Optimierungsprofile nicht freigegeben.',))
    # Die vorhandene benannte Rechenvariante bleibt technisch unverändert.
    # Die Oberfläche verlangt ihre ausdrückliche Auswahl vor einer Berechnung.
    old_accounts = {a.person_id: a for a in accounts}
    profile = ObjectiveProfile('E0 – technisches Vergleichsprofil',
                  ('wishes','groups','burden','hours_max','hours_spread','shifts','late_break'),
                  tuple(old_accounts.get(p.id, MonthAccount(p.id, 0)) for p in people),
                  WishPolicy('W0','2026-01',False,True,1),FairnessPolicy('F0','contract'))
    return inputs, profile, ()


def demonstration_month(year=2026, month=11):
    """Opt-in-Beispiel, niemals still als echte Teamdaten erzeugt."""
    from .contracts import Contract, Contracts, Employment
    from .people import Eligibility, Person
    span=DateRange(date(year,1,1),date(year+2,1,1))
    people=tuple(Person(f'P{i+1:02d}',f'Beispielperson {i+1} (fiktiv)',
                        Employment(f'P{i+1:02d}',span),
                        Contracts(f'P{i+1:02d}',(Contract(f'P{i+1:02d}',span,'25'),)),
                        (Eligibility.from_exclusions(span),)) for i in range(12))
    return standard_month(year,month,people=people)
