"""Speicher-, Historien- und CSV-Verträge ohne Oberfläche."""
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from dienstplan.csvio import export_fairness, export_hours, export_plan, preview_csv
from dienstplan.model import (Assignment, Blocker, Employee, MonthData, ValidationError,
                             default_shifts, generate_shifts)
from dienstplan.storage import Store


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
