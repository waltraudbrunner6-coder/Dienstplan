"""Speicher-, Historien- und CSV-Verträge ohne Oberfläche."""
import csv
import json
import sqlite3
from datetime import datetime, time, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from dienstplan.csvio import export_fairness, export_hours, export_plan, export_wishes, preview_csv
from dienstplan.hours import demand_minutes, monthly_target
from dienstplan.model import (Assignment, Blocker, Employee, MonthData, ValidationError,
                             default_shifts, generate_shifts)
from dienstplan.storage import SCHEMA_VERSION, Store, _encode


def month(year=2026, number=11, complete=False):
    data = MonthData(year, number,
                     [Employee(f"p{i}", f"Person {i + 1}", Decimal("40")) for i in range(12)],
                     default_shifts())
    if complete:
        groups = {"frueh": (0, 1), "spaet": (2, 3), "nacht": (4, 5), "sonder": (6, 7)}
        data.assignments = [Assignment(s.id, f"p{i}", i == 0)
                            for s in generate_shifts(data) for i in groups[s.type_id]]
    return data


def blocker(day, priority=1, employee="p0", name=None, hour=0, duration=24):
    start = datetime.fromisoformat(day) + timedelta(hours=hour)
    return Blocker(name or f"{employee}-{day}-{hour}-{priority}", employee, start,
                   start + timedelta(hours=duration), priority, "Privater Termin")


def test_save_load_keeps_decimal_snapshots_rules_and_fixes(tmp_path):
    path = tmp_path / "daten.sqlite"
    data = month(complete=True)
    data.employees[0].weekly_hours = Decimal("37.125")
    data.employees[0].opening_minutes = 600
    data.employees[0].desired_minutes = 0
    data.blockers = [blocker("2026-11-10", priority=2)]
    with Store(path) as store:
        store.save_month(data)
        data.employees[0].name = "Nachträgliche Änderung"
    with Store(path) as store:
        loaded = store.load_month(2026, 11)
        assert loaded.employees[0].name == "Person 1"
        assert loaded.employees[0].weekly_hours == Decimal("37.125")
        assert loaded.employees[0].opening_minutes == 600
        assert loaded.employees[0].desired_minutes == 0
        assert loaded.assignments == data.assignments
        assert loaded.blockers == data.blockers
        assert store.list_months() == ["2026-11"]
        assert store.load_month(2026, 12) is None


def test_later_month_changes_do_not_change_previous_month(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        old = month()
        store.save_month(old)
        new = month(number=12)
        new.employees[0].weekly_hours = Decimal("20")
        new.shift_types[0].staff_required = 3
        store.save_month(new)
        assert store.load_month(2026, 11).employees[0].weekly_hours == 40
        assert store.load_month(2026, 11).shift_types[0].staff_required == 2
        assert store.load_month(2026, 12).shift_types[0].staff_required == 3


def test_blocker_duplicates_ignore_comments_and_cap_is_atomic(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        original = blocker("2026-11-01")
        dupe = blocker("2026-11-01", name="second-id")
        dupe.comment = "Anderer Kommentar"
        store.replace_blockers("p0", [original, dupe])
        assert len(store.get_blockers("p0")) == 1
        with pytest.raises(ValidationError, match="vier"):
            store.replace_blockers("p0", [blocker(f"2026-11-{d:02}") for d in range(1, 6)])
        assert store.get_blockers("p0") == [original]
        other = blocker("2026-11-01", employee="p1")
        store.replace_blockers("p1", [other])
        store.replace_blockers("p0", [])
        assert store.get_blockers() == [other]


def test_cap_counts_overnight_in_both_months_but_midnight_once(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        crossing = blocker("2026-01-31", hour=20, duration=6)
        jan = [blocker(f"2026-01-{d:02}") for d in (1, 2, 3)]
        feb = [blocker(f"2026-02-{d:02}") for d in (2, 3, 4)]
        store.replace_blockers("p0", jan + feb + [crossing])
        with pytest.raises(ValidationError, match="02/2026"):
            store.replace_blockers("p0", jan + feb + [crossing, blocker("2026-02-05")])
        assert len(store.get_blockers("p0")) == 7
        store.replace_blockers("p0", feb + [blocker("2026-01-31"), blocker("2026-02-05")])
        assert len(store.get_blockers("p0")) == 5


def test_sqlite_conflicting_ids_rollback_without_deleting_old_data(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        original = blocker("2026-11-01")
        store.replace_blockers("p0", [original])
        with pytest.raises(ValidationError, match="Kennungen"):
            store.replace_blockers("p0", [blocker("2026-11-02", name="same"),
                                          blocker("2026-11-03", name="same")])
        assert store.get_blockers("p0") == [original]


def test_save_month_adds_blockers_and_rejects_invalid_plan_atomically(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        data = month()
        store.save_month(data)
        shift = generate_shifts(data)[0]
        data.assignments = [Assignment(shift.id, "p0")]
        data.blockers = [blocker("2026-11-01")]
        with pytest.raises(ValidationError):
            store.save_month(data)
        assert not store.get_blockers()
        assert not store.load_month(2026, 11).assignments
        data.blockers[0].priority = 2
        store.save_month(data)
        assert store.load_month(2026, 11).assignments == data.assignments


def test_history_only_confirmed_once_and_uses_old_weekly_hours(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        first = month(number=2, complete=True)
        first.employees[6].weekly_hours = Decimal("20")
        store.save_month(first)
        assert store.history(2026, 3) == []
        store.set_confirmed(2026, 2, True)
        store.set_confirmed(2026, 2, True)
        historical = {h.employee_id: h for h in store.history(2026, 3)}
        assert historical["p6"].special_count == 4
        assert historical["p6"].special_minutes == 4 * 12 * 60
        assert historical["p6"].expected_count == Fraction(8 * 20, 460)
        assert historical["p6"].expected_minutes == Fraction(8 * 12 * 60 * 20, 460)
        later = month(number=3, complete=True)
        later.employees[6].weekly_hours = Decimal("80")
        store.save_month(later)
        assert {h.employee_id: h for h in store.history(2026, 4)}["p6"].expected_count == Fraction(8 * 20, 460)
        assert store.history(2026, 2) == []
        with pytest.raises(ValidationError, match="bestätigt"):
            store.save_month(first)
        store.set_confirmed(2026, 2, False)
        assert store.history(2026, 4) == []
        first.employees[6].weekly_hours = Decimal("25")
        store.save_month(first)


def test_confirmation_requires_full_valid_plan_and_blocks_new_hard_sperre(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        data = month()
        store.save_month(data)
        with pytest.raises(ValidationError, match="unvollständig"):
            store.set_confirmed(2026, 11, True)
        data = month(complete=True)
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        with pytest.raises(ValidationError, match="bestätigten Dienstplan"):
            store.replace_blockers("p0", [blocker("2026-11-01")])
        assert store.get_blockers("p0") == []
        store.replace_blockers("p0", [blocker("2026-11-01", priority=2)])
        assert len(store.get_blockers("p0")) == 1


def test_boundary_returns_original_occurrences_from_other_months(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        previous = month(number=10)
        overnight = next(s for s in generate_shifts(previous)
                         if s.start.day == 31 and s.type_id == "nacht")
        previous.assignments = [Assignment(overnight.id, "p0", True)]
        store.save_month(previous)
        pairs = store.boundary(2026, 11)
        assert len(pairs) == 1
        assert pairs[0][0].fixed
        assert pairs[0][1].end == datetime(2026, 11, 1, 6)
        assert store.boundary(2026, 10) == []


def test_new_month_assignment_preserves_confirmed_neighbor_rest_rule(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        november = month()
        store.save_month(november)
        december = month(number=12, complete=True)
        december.rules.rest_minutes = 8 * 60
        store.save_month(december)
        store.set_confirmed(2026, 12, True)
        overnight = next(s for s in generate_shifts(november)
                         if s.start.day == 30 and s.type_id == "nacht")
        november.assignments = [Assignment(overnight.id, "p0")]
        with pytest.raises(ValidationError, match="bestätigten Dienstplan 2026-12"):
            store.save_month(november)
        assert store.load_month(2026, 11).assignments == []
        assert store.load_month(2026, 12).confirmed


@pytest.mark.parametrize("delimiter,bom", [(";", True), (",", False)])
def test_csv_import_delimiters_bom_whole_day_midnight_and_dupes(tmp_path, delimiter, bom):
    path = tmp_path / "sperren.csv"
    rows = [["datum", "von", "bis", "prioritaet", "kommentar"],
            ["2026-11-03", "", "", "1", "Ganztägig, nicht verfügbar"],
            ["2026-11-03", "", "", "1", "Anderer Kommentar"],
            ["2026-11-10", "22:00", "02:00", "2", "Privater Termin"],
            ["2026-11-11", "08:00", "08:00", "2", "24 Stunden"]]
    with path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as stream:
        csv.writer(stream, delimiter=delimiter).writerows(rows)
    preview = preview_csv(path, "p0")
    assert preview.valid, preview.errors
    assert len(preview.blockers) == 3
    assert preview.blockers[0].start == datetime(2026, 11, 3)
    assert preview.blockers[0].end == datetime(2026, 11, 4)
    assert preview.blockers[1].end == datetime(2026, 11, 11, 2)
    assert preview.blockers[2].end - preview.blockers[2].start == timedelta(days=1)


def test_csv_optional_comment_and_empty_body(tmp_path):
    path = tmp_path / "sperren.csv"
    path.write_text("datum;von;bis;prioritaet\n2026-11-03;;;1\n", encoding="utf-8")
    preview = preview_csv(path, "p0")
    assert preview.valid
    assert preview.blockers[0].comment == ""
    path.write_text("datum;von;bis;prioritaet\n", encoding="utf-8")
    assert preview_csv(path, "p0").valid


def test_csv_error_lines_all_reported_and_no_storage_side_effect(tmp_path):
    path = tmp_path / "falsch.csv"
    path.write_text("datum;von;bis;prioritaet;kommentar\n"
                    "2026-11-03;08:00;;1;Fehlende Zeit\n"
                    "2026-02-30;;;1;Ungültiges Datum\n"
                    "2026-11-05;;;3;Ungültige Priorität\n"
                    "2026-11-06;8:00;12:00;2;Uhrzeitformat\n"
                    "2026-11-07;24:00;12:00;2;Uhrzeit ungültig\n"
                    "2026-11-08;;;1;zu;viele\n"
                    "2026-11-09;;;2;gültig\n", encoding="utf-8")
    with Store(tmp_path / "daten.sqlite") as store:
        original = blocker("2026-11-01")
        store.replace_blockers("p0", [original])
        preview = preview_csv(path, "p0")
        assert not preview.valid
        assert len(preview.errors) == 6
        assert all(error.startswith(f"Zeile {line}:") for error, line in zip(preview.errors, range(2, 8)))
        assert len(preview.blockers) == 1
        assert store.get_blockers("p0") == [original]


def test_csv_preview_cap_header_and_encoding_errors(tmp_path):
    path = tmp_path / "sperren.csv"
    path.write_text("datum;von;bis;prioritaet\n" + "".join(f"2026-11-{day:02};;;1\n" for day in range(1, 6)), encoding="utf-8")
    preview = preview_csv(path, "p0")
    assert not preview.valid
    assert preview.errors[0].startswith("Zeile 6:")
    path.write_text("Datum;von;bis;prioritaet\n", encoding="utf-8")
    assert "Kopfzeile" in preview_csv(path, "p0").errors[0]
    path.write_bytes(b"datum;von;bis;prioritaet\n\xff")
    assert "UTF-8" in preview_csv(path, "p0").errors[0]


def test_exports_show_slots_fixes_wishes_forecast_and_fairness(tmp_path):
    data = month()
    first = generate_shifts(data)[0]
    data.assignments = [Assignment(first.id, "p0", True)]
    data.blockers = [blocker("2026-11-01", priority=2)]
    plan, hours, fairness = [tmp_path / name for name in ("plan.csv", "stunden.csv", "verteilung.csv")]
    export_plan(plan, data)
    export_hours(hours, data)
    export_fairness(fairness, data)
    assert all(path.read_bytes().startswith(b"\xef\xbb\xbf") for path in (plan, hours, fairness))
    with plan.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert rows[0]["Person"] == "Person 1"
    assert rows[0]["Fixiert"] == "Ja"
    assert rows[0]["Status"] == "Priorität-2-Wunsch übergangen"
    assert rows[1]["Besetzungsplatz"] == "2"
    assert rows[1]["Person"] == "OFFEN"
    assert len(rows) == sum(s.staff_required for s in generate_shifts(data))
    with hours.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert rows[0]["Eingeplante Stunden"] == "8,00"
    assert rows[0]["Hinweis"] == "Dienstplan-Prognose"
    with fairness.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert len(rows) == 4 * 12
    assert rows[0]["Einsätze im Monat"] == "1"


@pytest.mark.parametrize("end", [time(12), time(16), time(20)])
def test_short_equal_or_long_special_shift_plan_roundtrip(tmp_path, end):
    data = month(complete=True)
    data.shift_types[3].end = end
    path = tmp_path / "daten.sqlite"
    with Store(path) as store:
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
    with Store(path) as store:
        loaded = store.load_month(2026, 11)
        loaded.validate()
        assert loaded.confirmed
        assert loaded.shift_types[3].end == end
        assert loaded.assignments == data.assignments
        assert store.history(2026, 12)[6].special_minutes == 4 * (end.hour - 8) * 60


def test_exceptions_roundtrip_preserves_original_shifts_and_reactivates(tmp_path):
    data = month(complete=True)
    exceptions = {"2026-11-16/frueh", "2026-11-16/nacht", "2026-11-30/nacht"}
    data.exceptions = exceptions
    data.assignments = [a for a in data.assignments if a.shift_id not in exceptions]
    before = demand_minutes(data)
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        loaded = store.load_month(2026, 11)
        assert loaded.exceptions == exceptions
        assert loaded.assignments == data.assignments
        assert demand_minutes(loaded) == before
        ids = {s.id for s in generate_shifts(loaded)}
        assert "2026-11-15/nacht" in ids
        assert "2026-11-16/spaet" in ids
        assert not ids & exceptions
        loaded.exceptions.remove("2026-11-30/nacht")
        store.save_month(loaded)
        reloaded = store.load_month(2026, 11)
        restored = next(s for s in generate_shifts(reloaded) if s.id == "2026-11-30/nacht")
        assert restored.end == datetime(2026, 12, 1, 6)
        assert demand_minutes(reloaded) == before + 16 * 60


def test_version_one_migration_preserves_payload_and_decimal_hours(tmp_path):
    data = month(complete=True)
    for employee, hours in zip(data.employees, ("37.125", "12.345", "0", "40.0001")):
        employee.weekly_hours = Decimal(hours)
    data.employees[0].opening_minutes = 321
    data.employees[0].desired_minutes = -67
    raw = json.loads(_encode(data))
    raw.pop("exceptions")
    raw.pop("wish_snapshot")
    payload = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
    path = tmp_path / "version1.sqlite"
    old_blocker = blocker("2026-11-02", employee="p3", priority=2, name="existing-blocker-id")
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE months (month_key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute("INSERT INTO months VALUES(?,?)", (data.key, payload))
        connection.execute("""CREATE TABLE blockers (
            id TEXT PRIMARY KEY, employee_id TEXT NOT NULL, start TEXT NOT NULL,
            end TEXT NOT NULL, priority INTEGER NOT NULL CHECK(priority IN (1,2)),
            comment TEXT NOT NULL DEFAULT '', UNIQUE(employee_id,start,end,priority))""")
        connection.execute("INSERT INTO blockers VALUES(?,?,?,?,?,?)",
                           (old_blocker.id, old_blocker.employee_id, old_blocker.start.isoformat(timespec="minutes"),
                            old_blocker.end.isoformat(timespec="minutes"), old_blocker.priority, old_blocker.comment))
        connection.execute("PRAGMA user_version=1")
    with Store(path) as store:
        loaded = store.load_month(2026, 11)
        assert loaded.exceptions == set()
        assert loaded.wish_snapshot is None
        assert loaded.employees == data.employees
        assert loaded.assignments == data.assignments
        assert loaded.blockers == [old_blocker]
        assert [monthly_target(e, 2026, 11) for e in loaded.employees] == [
            monthly_target(e, 2026, 11) for e in data.employees]
        assert store.connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION == 2
        assert store.connection.execute("SELECT payload FROM months").fetchone()[0] == payload
        store.save_month(loaded)
    with Store(path) as store:
        assert store.load_month(2026, 11).employees == data.employees
        assert store.get_blockers() == [old_blocker]


def test_confirmed_exception_change_and_stale_assignment_are_rejected_atomically(tmp_path):
    data = month(complete=True)
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        data.exceptions.add("2026-11-16/frueh")
        with pytest.raises(ValidationError, match="unbekannt"):
            store.save_month(data)
        assert store.load_month(2026, 11).exceptions == set()
        assert store.load_month(2026, 11).assignments == data.assignments
        store.set_confirmed(2026, 11, True)
        data.assignments = [a for a in data.assignments if a.shift_id not in data.exceptions]
        with pytest.raises(ValidationError, match="bestätigt"):
            store.save_month(data)
        assert store.load_month(2026, 11).exceptions == set()


def test_export_exceptions_have_one_status_row_and_no_demand_or_open_place(tmp_path):
    data = month()
    data.exceptions = {"2026-11-16/frueh", "2026-11-16/nacht"}
    path = tmp_path / "plan.csv"
    export_plan(path, data)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    inactive = [r for r in rows if r["Status"] == "ENTFÄLLT"]
    assert len(inactive) == 2
    assert all(r["Datum"] == "2026-11-16" for r in inactive)
    assert {r["Schicht"] for r in inactive} == {"Frühdienst", "Nachtdienst"}
    assert all(r["Bezahlte Stunden"] == r["Besetzungsplatz"] == r["Person"] == "" for r in inactive)
    assert sum(r["Person"] == "OFFEN" for r in rows) == sum(s.staff_required for s in generate_shifts(data))
    overnight = next(r for r in inactive if r["Schicht"] == "Nachtdienst")
    assert overnight["Ende"] == "2026-11-17 06:00"


def test_export_wish_statistics_contains_unique_current_historic_and_missing_data(tmp_path):
    from dienstplan.model import WishHistoryEntry
    from dienstplan.wishes import wish_key
    data = month()
    wish = blocker("2026-11-01", priority=2)
    data.blockers = [wish, blocker("2026-11-01", priority=2, name="duplicate")]
    data.assignments = [Assignment("2026-11-01/frueh", "p0"), Assignment("2026-11-01/spaet", "p0")]
    history = [WishHistoryEntry("p0", {wish_key(wish), "old-key"}, ["2026-10"])]
    path = tmp_path / "wuensche.csv"
    export_wishes(path, data, history)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert rows[0]["Relevante Priorität-2-Wünsche"] == "1"
    assert rows[0]["Erfüllte Wünsche im Monat"] == "0"
    assert rows[0]["Übergangene Wünsche im Monat"] == "1"
    assert rows[0]["Historische Übergehungen"] == "2"
    assert rows[0]["Kumulierte Belastung"] == "2"
    assert rows[0]["Fehlende bestätigte Althistorie"] == "2026-10"
