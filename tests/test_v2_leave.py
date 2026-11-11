"""Nur ausdrücklich anrechenbare Urlaubstage und Anspruchsmonate, synthetisch."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from fractions import Fraction
import pytest

from dienstplan.v2.accounting import round_minutes
from dienstplan.v2.contracts import Contract, Contracts, DateRange, Employment
from dienstplan.v2.entries import Entry
from dienstplan.v2.errors import DomainError
from dienstplan.v2.people import Person,Eligibility
from dienstplan.v2.leave import monthly_leave_rows, leave_balance
from dienstplan.v2.time import Interval


def person():
    span=DateRange(date(2026,1,1),date(2028,1,1))
    return Person('P01','Fiktive Person',Employment('P01',span),Contracts('P01',(Contract('P01',span,'25'),)),(Eligibility.from_exclusions(span),))


def entry(pid='P01', start='2026-11-01', end='2026-12-01', days=(), ident='u'):
    return Entry(ident, pid, 'urlaub', Interval.local(start+'T00:00',end+'T00:00'),frozenset(date.fromisoformat(d) for d in days))


def test_25_hours_contract_gives_five_hours_each_explicit_day():
    row, = monthly_leave_rows((person(),),(entry(days=('2026-11-03','2026-11-04')),),2026,11)
    assert row.credit_minutes == 600 and row.raw_credit_minutes == 600
    assert row.used_days == 2 and row.credits_known


def test_contract_change_uses_hours_valid_on_each_leave_day():
    p=person()
    p=replace(p,contracts=Contracts(p.id,(Contract(p.id,DateRange(date(2026,1,1),date(2026,11,16)),'25'),Contract(p.id,DateRange(date(2026,11,16),date(2028,1,1)),'30'))))
    row, = monthly_leave_rows((p,),(entry(days=('2026-11-15','2026-11-16')),),2026,11)
    assert row.credit_minutes == 660


def test_round_once_after_monthly_sum_and_deduplicate_overlap():
    p=person();p=replace(p,contracts=Contracts(p.id,(replace(p.contracts.versions[0],weekly_hours='0.125'),)))
    a=entry(days=('2026-11-03','2026-11-04'))
    b=entry(days=('2026-11-04',),ident='other')
    row, = monthly_leave_rows((p,),(a,a,b),2026,11)
    assert row.used_days == 2 and row.raw_credit_minutes == 3 and row.credit_minutes == 3
    assert 2*round_minutes(Fraction(3,2)) == 4


def test_explicit_weekend_day_counts_without_inventing_other_days():
    row, = monthly_leave_rows((person(),),(entry(start='2026-11-06',end='2026-11-10',days=('2026-11-08',)),),2026,11)
    assert row.credit_minutes == 300 and row.used_days == 1


def test_month_boundary_separates_credit_days_but_keeps_day_unique():
    e=entry(start='2026-11-30',end='2026-12-02',days=('2026-11-30','2026-12-01'))
    nov, = monthly_leave_rows((person(),),(e,),2026,11)
    dec, = monthly_leave_rows((person(),),(e,),2026,12)
    assert nov.used_days == dec.used_days == 1
    assert nov.credit_days == frozenset((date(2026,11,30),))
    assert dec.credit_days == frozenset((date(2026,12,1),))


def test_missing_selection_stays_unknown_with_person_and_readable_dates():
    e=entry(start='2026-11-15',end='2026-11-17')
    row, = monthly_leave_rows((person(),),(e,),2026,11)
    assert not row.credits_known and row.credit_minutes is None and row.unknown_entry_ids == ('u',)
    assert 'P01' in row.diagnostics[0] and '15.11.2026' in row.diagnostics[0]
    assert 'Tage auswählen' in row.diagnostics[0]
    known, = monthly_leave_rows((person(),),(e,),2026,12)
    assert known.credit_minutes == 0 and known.credits_known


def test_known_partial_credit_is_not_reported_as_complete_when_other_entry_is_unknown():
    rows=monthly_leave_rows((person(),),(entry(days=('2026-11-03',)),entry(start='2026-11-20',end='2026-11-21',ident='missing')),2026,11)
    assert rows[0].raw_credit_minutes == 300 and rows[0].credit_minutes is None


def test_contract_gap_is_an_error_not_a_zero_credit():
    p=person();p=replace(p,contracts=Contracts(p.id,()))
    with pytest.raises(DomainError,match='Vertragslücke'):
        monthly_leave_rows((p,),(entry(days=('2026-11-03',)),),2026,11)


def test_entitlement_accrues_only_explicit_months_and_can_carry():
    row=leave_balance('5',6,months=('2026-11','2026-12'),carry_forward=True)
    assert row.earned_days == 4 and row.projected_days == 3
    missing=leave_balance(None,1,months=('2026-11',),carry_forward=True)
    assert missing.projected_days is None and missing.diagnostics


def test_monthly_entitlement_is_not_hard_consumption_limit():
    row=leave_balance(None,3,months=('2026-11',),carry_forward=False)
    assert row.earned_days == 2 and row.projected_days == -1 and row.diagnostics


@pytest.mark.parametrize('kwargs',[
    dict(opening_days=0.5,used_days=0,months=('2026-11',),carry_forward=True),
    dict(opening_days='NaN',used_days=0,months=('2026-11',),carry_forward=True),
    dict(opening_days=0,used_days=0,months=('2026-11','2026-11'),carry_forward=True),
    dict(opening_days=0,used_days=0,months=('2026-13',),carry_forward=True),
    dict(opening_days=0,used_days=-1,months=('2026-11',),carry_forward=True),
    dict(opening_days=0,used_days=1,months=('2026-11',),carry_forward=None),
    dict(opening_days=2,used_days=1,months=('2026-11',),carry_forward=False),
    dict(opening_days=0,used_days=1,months=('2026-11','2026-12'),carry_forward=False),
])
def test_bad_or_implicit_leave_account_inputs_are_rejected(kwargs):
    with pytest.raises(DomainError):leave_balance(**kwargs)


@pytest.mark.parametrize('year,month,length',[(2026,1,31),(2026,11,30),(2024,2,29),(2026,2,28)])
def test_partial_month_entitlement_uses_actual_month_length(year,month,length):
    from dienstplan.v2.leave import monthly_leave_entitlement
    from dienstplan.v2.contracts import Employment
    end=date(year+int(month==12),month%12+1,1)
    employment=Employment('p',DateRange(date(year,month,17),end))
    assert monthly_leave_entitlement(employment,year,month)==Fraction(2*(length-16),length)


def test_employment_boundaries_for_entitlement_are_inclusive_exclusive():
    from dienstplan.v2.leave import monthly_leave_entitlement
    from dienstplan.v2.contracts import Employment
    employment=Employment('p',DateRange(date(2026,1,31),date(2026,2,2)))
    assert monthly_leave_entitlement(employment,2026,1)==Fraction(2,31)
    assert monthly_leave_entitlement(employment,2026,2)==Fraction(2,28)
    assert monthly_leave_entitlement(employment,2026,3)==0
    full=Employment('p',DateRange(date(2026,1,1),date(2026,2,1)))
    assert monthly_leave_entitlement(full,2026,1)==2
    assert monthly_leave_entitlement(full,2026,2)==0


def test_monthly_fractions_are_summed_exactly_without_early_rounding():
    from dienstplan.v2.contracts import Employment
    employment=Employment('p',DateRange(date(2026,1,31),date(2026,2,2)))
    balance=leave_balance('1/3',0,months=('2026-01','2026-02'),carry_forward=True,employment=employment)
    assert balance.earned_days==Fraction(2,31)+Fraction(2,28)
    assert balance.projected_days==Fraction(1,3)+Fraction(2,31)+Fraction(2,28)
    assert balance.earned_days!=Fraction(6,100)+Fraction(7,100)  # falsch: Monatswerte vorab auf 2 Nachkommastellen


def test_fraction_text_is_exact_and_nonfinite_or_zero_denominator_remains_invalid():
    assert leave_balance('1/3',0,months=('2026-11',),carry_forward=True).projected_days==Fraction(7,3)
    for text in ('1/0','NaN','Infinity','1/NaN'):
        with pytest.raises(DomainError):leave_balance(text,0,months=('2026-11',),carry_forward=True)
