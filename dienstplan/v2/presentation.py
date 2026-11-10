"""Stunden an der Bediengrenze; die Domäne speichert weiterhin ganze Minuten."""
from decimal import Decimal, localcontext
from fractions import Fraction

from .accounting import round_minutes
from .errors import DomainError


def hours_text(minutes) -> str:
    """Zwei Dezimalstellen, kaufmännisch, einschließlich negativer Salden."""
    hundredths = round_minutes(Fraction(minutes) * 100 / 60)
    sign = '-' if hundredths < 0 else ''
    return f'{sign}{abs(hundredths)//100},{abs(hundredths)%100:02d}'


def hours_minutes(text: str, *, previous: int | None = None) -> int:
    # Unveränderte Anzeige darf die ursprüngliche ganze Minute nicht verlieren.
    if previous is not None and text.strip() == hours_text(previous):
        return previous
    try:
        value = Decimal(text.strip().replace(',', '.'))
        if not value.is_finite():
            raise ValueError()
        return round_minutes(Fraction(value) * 60)
    except (ValueError, ArithmeticError) as exc:
        raise DomainError('Stunden als endliche Dezimalzahl eingeben, zum Beispiel 7,5 oder −2,25 (Minuszeichen -).') from exc


def contract_text(hours) -> str:
    value = Fraction(hours)
    # Vertragswerte bleiben exakt; periodische Werte behalten ihre Bruchform.
    denominator = value.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1:
        return str(value)
    with localcontext() as context:
        context.prec = max(28, len(str(abs(value.numerator))) + len(str(value.denominator)) + 2)
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f').replace('.', ',')
