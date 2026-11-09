"""Reine UTC-Intervalle und explizite Ortszeitauflösung mit paketierter tzdb."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from importlib.resources import files
from zoneinfo import ZoneInfo
from tzdata import IANA_VERSION, __version__ as TZDATA_VERSION

from .errors import DomainError

UTC = timezone.utc


@lru_cache
def vienna() -> ZoneInfo:
    # Absichtlich unabhängig von TZPATH und der Zeitzonendatenbank des Systems.
    with files("tzdata.zoneinfo").joinpath("Europe/Vienna").open("rb") as stream:
        return ZoneInfo.from_file(stream, key="Europe/Vienna")


def _minute(value: datetime):
    if not isinstance(value, datetime) or value.second or value.microsecond:
        raise DomainError("Zeitpunkte müssen minutengenau angegeben werden.")


def instant(value: datetime) -> datetime:
    _minute(value)
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainError("Ein eindeutiger Zeitpunkt mit UTC-Offset wird benötigt.")
    result = value.astimezone(UTC)
    _minute(result)
    return result


def local_instant(value: datetime, *, fold: int | None = None,
                  offset: timedelta | None = None) -> datetime:
    """Naive Wiener Ortszeit auflösen; Herbstvariante niemals implizit wählen."""
    _minute(value)
    if value.tzinfo is not None:
        raise DomainError("Ortszeit ohne tzinfo angeben; Offset separat auswählen.")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise DomainError("fold muss 0 oder 1 sein.")
    candidates = {}
    for choice in (0, 1):
        utc = value.replace(tzinfo=vienna(), fold=choice).astimezone(UTC)
        back = utc.astimezone(vienna())
        if back.replace(tzinfo=None, fold=0) == value.replace(fold=0):
            candidates[utc] = (back.fold, back.utcoffset())
    if not candidates:
        raise DomainError(f"Die Wiener Ortszeit {value.isoformat()} existiert wegen der Zeitumstellung nicht.")
    if len(candidates) > 1 and fold is None and offset is None:
        raise DomainError(f"Die Wiener Ortszeit {value.isoformat()} ist mehrdeutig; Offset oder fold auswählen.")
    selected = [utc for utc, (f, off) in candidates.items()
                if (fold is None or fold == f) and (offset is None or offset == off)]
    if len(selected) != 1:
        raise DomainError("Die gewählte Herbstvariante bzw. der Offset passt nicht zur Ortszeit.")
    return selected[0]


def parse_local(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise DomainError("Datum und Uhrzeit müssen im ISO-Format angegeben werden.") from exc
    return local_instant(parsed.replace(tzinfo=None), offset=parsed.utcoffset())


def midnight(day: date) -> datetime:
    return local_instant(datetime.combine(day, time()))


@dataclass(frozen=True, slots=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self):
        object.__setattr__(self, "start", instant(self.start))
        object.__setattr__(self, "end", instant(self.end))
        if self.end <= self.start:
            raise DomainError("Ein Zeitintervall benötigt ein Ende nach seinem Beginn.")

    @classmethod
    def local(cls, start: str, end: str):
        return cls(parse_local(start), parse_local(end))

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    @property
    def start_day(self) -> date:
        return self.start.astimezone(vienna()).date()

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Interval") -> bool:
        return self.start <= other.start and other.end <= self.end

    def intersection(self, other: "Interval") -> "Interval | None":
        start, end = max(self.start, other.start), min(self.end, other.end)
        return Interval(start, end) if start < end else None

    def difference(self, cuts) -> tuple["Interval", ...]:
        result = [self]
        for cut in sorted(tuple(cuts), key=lambda x: x.start):
            remaining = []
            for part in result:
                hit = part.intersection(cut)
                if hit is None:
                    remaining.append(part)
                else:
                    if part.start < hit.start:
                        remaining.append(Interval(part.start, hit.start))
                    if hit.end < part.end:
                        remaining.append(Interval(hit.end, part.end))
            result = remaining
        return tuple(result)


def rest_minutes(previous: Interval, following: Interval) -> int:
    return int((following.start - previous.end).total_seconds() // 60)


def day_segments(span: Interval) -> tuple[tuple[date, Interval], ...]:
    result = []
    cursor = span.start
    while cursor < span.end:
        day = cursor.astimezone(vienna()).date()
        end = min(span.end, midnight(day + timedelta(days=1)))
        result.append((day, Interval(cursor, end)))
        cursor = end
    return tuple(result)
