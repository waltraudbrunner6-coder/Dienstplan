"""Reproduzierbare, ausschließlich fiktive Beispieldaten."""
from datetime import datetime, timedelta

from .model import Blocker, Employee, MonthData, Rules, default_shifts


def demo_month(year: int = 2026, month: int = 11) -> MonthData:
    names = ["Anna Beispiel", "Ben Muster", "Clara Test", "David Demo", "Eva Beispiel",
             "Felix Muster", "Greta Test", "Hannes Demo", "Ida Beispiel", "Jonas Muster",
             "Klara Test", "Leon Demo"]
    weekly = [40, 40, 36, 36, 32, 32, 30, 30, 28, 28, 24, 24]
    people = [Employee(f"demo-{i+1:02}", name, str(w)) for i, (name, w) in enumerate(zip(names, weekly))]
    people[0].opening_minutes = 600
    people[0].desired_minutes = 0
    people[1].opening_minutes = -480
    people[1].desired_minutes = 0
    a = datetime(year, month, 3)
    b = datetime(year, month, 10, 8)
    c = datetime(year, month, 15, 22)
    blockers = [Blocker(f"demo-{year}-{month}-a", people[0].id, a, a+timedelta(days=1), 1, "Ganztägiger privater Termin"),
                Blocker(f"demo-{year}-{month}-b", people[1].id, b, b+timedelta(hours=4), 2, "Vormittag möglichst frei"),
                Blocker(f"demo-{year}-{month}-c", people[2].id, c, c+timedelta(hours=8), 1, "Nacht nicht verfügbar")]
    return MonthData(year, month, people, default_shifts(), blockers,
                     Rules(rest_minutes=480, max_day_minutes=720, max_week_minutes=2880, max_consecutive_days=5))
