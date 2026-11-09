"""Physische Kalender-/Zulagenmengen und optionale belegte Einzelraten."""
from dataclasses import dataclass
from datetime import date,timedelta
from fractions import Fraction

from .contracts import exact_hours
from .errors import DomainError


def austrian_holidays(year,*,profile):
    if profile!='AT_TEST':raise DomainError('Nationaler Rechenkalender hier nur ausdrücklich als AT_TEST verfügbar; Quellenfreigabe offen.')
    # Gregorianischer Osteralgorithmus; technische Kalenderprüfung, kein
    # Nachweis einer betrieblichen/KV-Feiertags- oder Vergütungsregel.
    a=year%19;b=year//100;c=year%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
    n=h+l-7*m+114;easter=date(year,n//31,n%31+1)
    fixed={(1,1),(1,6),(5,1),(8,15),(10,26),(11,1),(12,8),(12,25),(12,26)}
    return frozenset({date(year,month,day) for month,day in fixed}|{easter+timedelta(days=delta) for delta in (1,39,50,60)})


@dataclass(frozen=True, slots=True)
class AllowanceRow:
    person_id: str
    day: date
    category: str
    minutes: int
    euros: Fraction | None
    profile_id: str | None
    explanation: str


def allowances(rows,*,profiles,scope,allow_synthetic=False):
    result=[]
    for row in rows:
        for category,minutes in (('night',row.night_minutes),('sunday',row.sunday_minutes),('holiday',row.holiday_minutes)):
            if not minutes:continue
            try:
                profile=profiles.select(category+'_rate',scope,row.day,allow_synthetic=allow_synthetic)
                rate=exact_hours(profile.parameters['euros_per_hour'])
            except (DomainError,KeyError) as exc:
                result.append(AllowanceRow(row.person_id,row.day,category,minutes,None,None,f'Euro ungeklärt: {exc}'))
            else:
                result.append(AllowanceRow(row.person_id,row.day,category,minutes,Fraction(minutes,60)*rate,profile.id,
                                           'Synthetischer Einzelbetrag; keine KV-Freigabe/Kumulationsregel.' if profile.synthetic else 'Einzelbetrag; Kumulation separat prüfen.'))
    return tuple(result)
