"""Wunschhistorie bleibt am bestätigten Monatsstand und zählt Zeiträume einmal."""
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal

from dienstplan.csvio import export_plan, export_wishes
from dienstplan.model import Assignment, Blocker, Employee, MonthData, default_shifts, generate_shifts
from dienstplan.storage import Store, _encode
from dienstplan.wishes import relevant_wishes, wish_key, wish_rows


def full_month(number=11):
    data = MonthData(2026, number,
                     [Employee(f"p{i}", f"Person {i + 1}", Decimal("25")) for i in range(12)],
                     default_shifts())
    groups = {"frueh": (0, 1), "spaet": (2, 3), "nacht": (4, 5), "sonder": (6, 7)}
    data.assignments = [Assignment(s.id, f"p{i}")
                        for s in generate_shifts(data) for i in groups[s.type_id]]
    return data


def wish(day, employee="p0", hours=24, hour=0, key="wish", priority=2):
    start = datetime.fromisoformat(day) + timedelta(hours=hour)
    return Blocker(key, employee, start, start + timedelta(hours=hours), priority)


def entries(store, year=2026, number=12):
    return {h.employee_id: h for h in store.wish_history(year, number)}


def test_only_confirmed_prior_months_count_and_repeat_save_or_confirmation_does_not_add(tmp_path):
    data = full_month()
    b = wish("2026-11-02")
    data.blockers = [b]
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        store.save_month(data)
        assert store.wish_history(2026, 12) == []
        store.set_confirmed(2026, 11, True)
        store.set_confirmed(2026, 11, True)
        assert entries(store)["p0"].violated_keys == {wish_key(b)}
        assert entries(store)["p0"].violations == 1
        assert store.wish_history(2026, 11) == []
        later = full_month(12)
        later.blockers = [wish("2026-12-02", key="next-month")]
        store.save_month(later)
        store.set_confirmed(2026, 12, True)
        assert entries(store)["p0"].violations == 1
        assert entries(store, 2027, 1)["p0"].violations == 2


def test_confirmed_statistics_survive_global_deletion_change_and_restart(tmp_path):
    data = full_month()
    first = wish("2026-11-02")
    second = wish("2026-11-03", key="other")
    data.blockers = [first, second]
    path = tmp_path / "daten.sqlite"
    with Store(path) as store:
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        original = store.load_month(2026, 11).wish_snapshot
        store.replace_blockers("p0", [])
        store.replace_blockers("p0", [wish("2026-11-04", key="changed")])
        store.set_confirmed(2026, 11, True)
        assert store.load_month(2026, 11).wish_snapshot == original
    with Store(path) as store:
        assert entries(store)["p0"].violated_keys == {wish_key(first), wish_key(second)}
        loaded = store.load_month(2026, 11)
        row = wish_rows(loaded)[0]
        assert row["relevant"] == row["violated"] == 2
        assert len(loaded.blockers) == 1  # Live-Sperren bleiben unabhängig bearbeitbar.
        output = tmp_path / "wuensche.csv"
        export_wishes(output, loaded)
        assert "Bestätigter Wunschstand" in output.read_text(encoding="utf-8-sig")


def test_confirmed_plan_export_keeps_original_wish_conflicts_after_global_edits(tmp_path):
    data = full_month()
    data.blockers = [wish("2026-11-02")]
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        before, after = tmp_path / "vorher.csv", tmp_path / "nachher.csv"
        export_plan(before, store.load_month(2026, 11))
        store.replace_blockers("p0", [wish("2026-11-03", key="new-time")])
        export_plan(after, store.load_month(2026, 11))
        assert before.read_bytes() == after.read_bytes()
        with after.open(encoding="utf-8-sig", newline="") as stream:
            mine = [r for r in csv.DictReader(stream, delimiter=";") if r["Person"] == "Person 1"]
        assert all(r["Status"] == "Priorität-2-Wunsch übergangen"
                   for r in mine if r["Datum"] == "2026-11-02")
        assert all(r["Status"] == "Besetzt" for r in mine if r["Datum"] == "2026-11-03")
        assert "Wunsch (bestätigter Stand)" in after.read_text(encoding="utf-8-sig")


def test_draft_plan_export_lists_duplicate_wish_once_per_conflicting_assignment(tmp_path):
    data = full_month()
    duplicate = wish("2026-11-02", key="second-id")
    duplicate.comment = "Anderer Kommentar"
    data.blockers = [wish("2026-11-02"), duplicate]
    output = tmp_path / "dienstplan.csv"
    export_plan(output, data)
    with output.open(encoding="utf-8-sig", newline="") as stream:
        row = next(r for r in csv.DictReader(stream, delimiter=";")
                   if r["Datum"] == "2026-11-02" and r["Person"] == "Person 1")
    assert row["Status"] == "Priorität-2-Wunsch übergangen"
    assert row["Übergangene Priorität-2-Wünsche"].count("2026-11-02") == 1
    assert " | " not in row["Übergangene Priorität-2-Wünsche"]


def test_explicit_reopen_clears_snapshot_and_new_confirmation_recomputes(tmp_path):
    with Store(tmp_path / "daten.sqlite") as store:
        data = full_month()
        data.blockers = [wish("2026-11-02")]
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        store.set_confirmed(2026, 11, False)
        assert store.load_month(2026, 11).wish_snapshot is None
        assert store.wish_history(2026, 12) == []
        store.replace_blockers("p0", [])
        store.set_confirmed(2026, 11, True)
        assert entries(store)["p0"].violations == 0
        assert store.load_month(2026, 11).wish_snapshot["p0"] == {"relevant": [], "violated": []}


def test_same_cross_month_wish_is_one_cumulative_violation(tmp_path):
    crossing = wish("2026-11-30", employee="p4", hour=23)
    november = full_month()
    november.blockers = [crossing]
    december = full_month(12)
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(november)
        store.set_confirmed(2026, 11, True)
        store.save_month(december)
        december = store.load_month(2026, 12)
        row = next(r for r in wish_rows(december, wish_history=store.wish_history(2026, 12))
                   if r["employee_id"] == "p4")
        assert row["relevant"] == row["violated"] == row["historical"] == row["cumulative"] == 1
        store.set_confirmed(2026, 12, True)
        assert entries(store, 2027, 1)["p4"].violated_keys == {wish_key(crossing)}
        assert entries(store, 2027, 1)["p4"].violations == 1


def test_duplicate_ids_comments_and_multiple_shift_conflicts_count_once(tmp_path):
    first = wish("2026-11-02")
    duplicate = wish("2026-11-02", key="new-import-id")
    duplicate.comment = "Anderer Kommentar nach erneutem Import"
    data = full_month()
    # Zwei nicht überlappende Tagesdienste verletzen denselben Wunsch.
    data.assignments = [Assignment(a.shift_id, "p0" if a.employee_id == "p2" and a.shift_id == "2026-11-02/spaet"
                                    else a.employee_id) for a in data.assignments]
    data.blockers = [first, duplicate]
    assert len(relevant_wishes(data)) == 1
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        saved = store.load_month(2026, 11)
        assert saved.wish_snapshot["p0"] == {"relevant": [wish_key(first)], "violated": [wish_key(first)]}
        assert entries(store)["p0"].violations == 1


def test_only_relevant_p2_enter_snapshot_after_daily_exceptions(tmp_path):
    data = full_month()
    data.exceptions = {f"2026-11-16/{s.id}" for s in data.shift_types if not s.special}
    data.assignments = [a for a in data.assignments if a.shift_id not in data.exceptions]
    irrelevant = wish("2026-11-16", hours=1, hour=12, key="disabled")
    outside = wish("2026-12-10", key="outside")
    active = wish("2026-11-15", hours=1, hour=22, key="active-overnight")
    hard = wish("2026-11-03", employee="p9", key="hard", priority=1)
    data.blockers = [irrelevant, outside, active, hard]
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        store.set_confirmed(2026, 11, True)
        saved = store.load_month(2026, 11)
        assert saved.wish_snapshot["p0"]["relevant"] == [wish_key(active)]
        assert saved.wish_snapshot["p9"] == {"relevant": [], "violated": []}
        assert entries(store)["p0"].violations == 0


def test_old_confirmed_payload_reports_missing_and_reconfirmation_does_not_invent_history(tmp_path):
    data = full_month()
    data.confirmed = True
    raw = json.loads(_encode(data))
    raw.pop("exceptions")
    raw.pop("wish_snapshot")
    payload = json.dumps(raw, ensure_ascii=False)
    with Store(tmp_path / "daten.sqlite") as store:
        with store.connection:
            store.connection.execute("INSERT INTO months VALUES(?,?)", (data.key, payload))
        store.replace_blockers("p0", [wish("2026-11-02")])
        store.set_confirmed(2026, 11, True)
        assert store.load_month(2026, 11).wish_snapshot is None
        for entry in store.wish_history(2026, 12):
            assert entry.violations == 0
            assert entry.missing_months == ["2026-11"]
        current = full_month(12)
        row = wish_rows(current, wish_history=store.wish_history(2026, 12))[0]
        assert row["missing_months"] == ["2026-11"]
        output = tmp_path / "alt-wuensche.csv"
        export_wishes(output, store.load_month(2026, 11))
        assert "Damals bestätigte Wunschstatistik fehlt" in output.read_text(encoding="utf-8-sig")
        plan_output = tmp_path / "alt-dienstplan.csv"
        export_plan(plan_output, store.load_month(2026, 11))
        assert "damals bestätigte Wunschstatistik fehlt; Wunschkonflikte anhand aktueller Sperren" in plan_output.read_text(encoding="utf-8-sig")
        store.set_confirmed(2026, 11, False)
        store.set_confirmed(2026, 11, True)
        assert entries(store)["p0"].missing_months == []
        assert entries(store)["p0"].violations == 1


def test_direct_confirmed_save_creates_snapshot_and_unconfirmed_snapshot_is_not_reused(tmp_path):
    data = full_month()
    data.blockers = [wish("2026-11-02")]
    data.wish_snapshot = {"p0": {"relevant": ["stale"], "violated": ["stale"]}}
    with Store(tmp_path / "daten.sqlite") as store:
        store.save_month(data)
        assert store.load_month(2026, 11).wish_snapshot is None
        data.confirmed = True
        store.save_month(data)
        assert entries(store)["p0"].violated_keys == {wish_key(data.blockers[0])}
