"""CSV-Vorschau ohne Seiteneffekte und deutsche, tabellenfähige Exporte."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import tempfile
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

from .hours import fairness_rows, hour_rows
from .model import (Blocker, HistoryEntry, MonthData, ValidationError, WishHistoryEntry, format_hours,
                    generate_shifts, new_id, overlaps, validate_blockers)
from .wishes import relevant_wishes, wish_rows


@dataclass
class ImportPreview:
    blockers: list[Blocker] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_TIME = re.compile(r"\d{2}:\d{2}\Z")
_REQUIRED = {"datum", "von", "bis", "prioritaet"}


def _parse_time(value: str) -> time:
    if not _TIME.fullmatch(value):
        raise ValidationError("Uhrzeiten müssen im Format HH:MM stehen.")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Ungültige Uhrzeit; erlaubt sind 00:00 bis 23:59.") from exc


def preview_csv(path: Path | str, employee_id: str) -> ImportPreview:
    """Liest UTF-8/BOM. Auch bei Fehlern werden alle lesbaren Zeilen geprüft."""
    preview = ImportPreview()
    if not employee_id:
        preview.errors.append("Bitte vor dem Import eine Person auswählen.")
        return preview
    try:
        content = Path(path).read_text(encoding="utf-8-sig")
    except UnicodeError:
        preview.errors.append("Die Datei muss in UTF-8 gespeichert sein; UTF-8 mit BOM ist ebenfalls erlaubt.")
        return preview
    except OSError as exc:
        preview.errors.append(f"Die CSV-Datei konnte nicht gelesen werden: {exc}")
        return preview
    if not content.strip():
        preview.errors.append("Zeile 1: Die Datei enthält keine Kopfzeile.")
        return preview
    # Die dokumentierten Kopfzeilen enthalten weder Kommas noch Semikolons in
    # Feldnamen. Daher ist ihre Trennzeichenbestimmung auch bei nur einer Zeile
    # zuverlässig; Werte mit Trennzeichen bleiben normal CSV-quotiert.
    first_line = content.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(content, newline=""), delimiter=delimiter, strict=True)
    try:
        header = [field.strip() for field in next(reader)]
    except (StopIteration, csv.Error) as exc:
        preview.errors.append(f"Zeile 1: Ungültige CSV-Kopfzeile: {exc}")
        return preview
    if (len(set(header)) != len(header) or not _REQUIRED.issubset(header)
            or not set(header).issubset(_REQUIRED | {"kommentar"})):
        preview.errors.append("Zeile 1: Erwartete Kopfzeile: datum;von;bis;prioritaet;kommentar (kommentar ist optional).")
        return preview
    while True:
        line = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            preview.errors.append(f"Zeile {line}: Ungültiges CSV-Format: {exc}")
            # csv.reader ist nach den üblichen Fehlern weiter lesbar. Ein
            # abgeschlossenes Feld am Dateiende endet beim nächsten Durchlauf.
            continue
        if not row or all(not value.strip() for value in row):
            continue
        if len(row) != len(header):
            preview.errors.append(f"Zeile {line}: Erwartet werden {len(header)} Spalten, gefunden wurden {len(row)}.")
            continue
        values = {key: value.strip() for key, value in zip(header, row)}
        try:
            if not _DATE.fullmatch(values["datum"]):
                raise ValidationError("Das Datum muss im Format YYYY-MM-DD stehen.")
            try:
                day = date.fromisoformat(values["datum"])
            except ValueError as exc:
                raise ValidationError("Das Datum ist kein gültiger Kalendertag.") from exc
            if values["prioritaet"] not in ("1", "2"):
                raise ValidationError("Die Priorität darf ausschließlich 1 oder 2 sein.")
            begin, end = values["von"], values["bis"]
            if bool(begin) != bool(end):
                raise ValidationError("Bitte beide Uhrzeiten angeben oder beide für einen ganzen Tag leer lassen.")
            if not begin:
                start = datetime.combine(day, time())
                finish = start + timedelta(days=1)
            else:
                start = datetime.combine(day, _parse_time(begin))
                finish = datetime.combine(day, _parse_time(end))
                if finish <= start:
                    finish += timedelta(days=1)
            blocker = Blocker(new_id(), employee_id, start, finish,
                              int(values["prioritaet"]), values.get("kommentar", ""))
            # Prüft die Grenze schon für diese Datei, vorhandene Sperren prüft
            # danach der Store gemeinsam mit der vollständig gültigen Vorschau.
            candidate = validate_blockers(preview.blockers + [blocker])
            preview.blockers = candidate
        except OverflowError:
            preview.errors.append(f"Zeile {line}: Der Zeitraum liegt außerhalb des unterstützten Datumsbereichs.")
        except ValidationError as exc:
            preview.errors.append(f"Zeile {line}: {exc}")
    return preview


def _write_csv(path: Path | str, header: list[str], rows: list[list]) -> None:
    """Ein Export ersetzt die Zieldatei erst nach erfolgreichem Schreiben."""
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                         dir=target.parent, prefix=f".{target.name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.writer(stream, delimiter=";", lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


_WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def _plan_wish_intervals(data: MonthData) -> dict[str, list[tuple[datetime, datetime, str]]]:
    """Bestätigte Konfliktmarkierungen folgen dem damaligen Wunschstand.

    Der Schnappschuss speichert stabile Zeiträume, keine veränderlichen Kommentare.
    Ein später gelöschter oder neu importierter Wunsch ändert damit auch den
    Dienstplanexport eines bestätigten Monats nicht rückwirkend.
    """
    result: dict[str, list[tuple[datetime, datetime, str]]] = {}
    if data.confirmed and data.wish_snapshot is not None:
        for employee_id, row in data.wish_snapshot.items():
            for key in sorted(set(row.get("violated", []))):
                person, start, end = json.loads(key)
                if person == employee_id:
                    result.setdefault(employee_id, []).append(
                        (datetime.fromisoformat(start), datetime.fromisoformat(end),
                         "Wunsch (bestätigter Stand)"))
    else:
        for blocker in relevant_wishes(data):
            result.setdefault(blocker.employee_id, []).append(
                (blocker.start, blocker.end, blocker.comment or "Wunsch"))
    return result


def export_plan(path: Path | str, data: MonthData) -> None:
    names = {e.id: e.name for e in data.employees}
    wish_intervals = _plan_wish_intervals(data)
    hint = "Dienstplan-Prognose"
    if data.confirmed and data.wish_snapshot is None:
        hint += "; damals bestätigte Wunschstatistik fehlt; Wunschkonflikte anhand aktueller Sperren"
    rows = []
    active = {s.id for s in generate_shifts(data)}
    # Ausgefallene tägliche Termine erhalten eine einzige Statuszeile. Sie sind
    # weder offene Plätze noch bezahlte Einsätze und werden nicht vervielfacht.
    for shift in generate_shifts(replace(data, exceptions=set())):
        if shift.id not in active:
            rows.append([shift.start.date().isoformat(), _WEEKDAYS[shift.start.weekday()], shift.name,
                         shift.start.strftime("%Y-%m-%d %H:%M"), shift.end.strftime("%Y-%m-%d %H:%M"),
                         "", "", "ENTFÄLLT", "", "", "", "Ausnahmetag; keine Mitarbeiterstunden"])
            continue
        assigned = [a for a in data.assignments if a.shift_id == shift.id]
        for slot in range(shift.staff_required):
            assignment = assigned[slot] if slot < len(assigned) else None
            wishes = [] if assignment is None else [b for b in wish_intervals.get(assignment.employee_id, [])
                if overlaps(shift.start, shift.end, b[0], b[1])]
            wishes_text = " | ".join(f"{start:%Y-%m-%d %H:%M}–{end:%Y-%m-%d %H:%M}: {comment}"
                                      for start, end, comment in wishes)
            rows.append([shift.start.date().isoformat(), _WEEKDAYS[shift.start.weekday()], shift.name,
                         shift.start.strftime("%Y-%m-%d %H:%M"), shift.end.strftime("%Y-%m-%d %H:%M"),
                         slot + 1, names.get(assignment.employee_id, assignment.employee_id) if assignment else "OFFEN",
                         "Offener Platz" if assignment is None else ("Priorität-2-Wunsch übergangen" if wishes else "Besetzt"),
                         "Ja" if assignment and assignment.fixed else "Nein", wishes_text,
                         format_hours(shift.paid_minutes), hint])
    _write_csv(path, ["Datum", "Wochentag", "Schicht", "Beginn", "Ende", "Besetzungsplatz", "Person",
                      "Status", "Fixiert", "Übergangene Priorität-2-Wünsche", "Bezahlte Stunden", "Hinweis"], rows)


def export_hours(path: Path | str, data: MonthData) -> None:
    rows = [[r.name, str(r.weekly_hours).replace(".", ","), format_hours(r.target_minutes),
             format_hours(r.opening_minutes), format_hours(r.desired_minutes), format_hours(r.planning_minutes),
             format_hours(r.planned_minutes), format_hours(r.new_balance_minutes),
             format_hours(r.projected_balance_minutes), format_hours(r.deviation_minutes), "Dienstplan-Prognose"]
            for r in hour_rows(data)]
    _write_csv(path, ["Person", "Vertragliche Wochenstunden", "Monatssoll", "Anfangssaldo", "Gewünschter Endsaldo",
                      "Planungsziel", "Eingeplante Stunden", "Neue Plus-/Minusstunden", "Voraussichtlicher Endsaldo",
                      "Abweichung vom Planungsziel", "Hinweis"], rows)


def _decimal(value: int | float) -> str:
    return f"{value:.2f}".replace(".", ",")


def export_fairness(path: Path | str, data: MonthData, history: list[HistoryEntry] | None = None) -> None:
    rows = [[r["name"], r["shift_name"], r["count"], format_hours(r["minutes"]),
             _decimal(r["expected_count"]), _decimal(r["count_deviation"]),
             _decimal(r["expected_minutes"] / 60), _decimal(r["minute_deviation"] / 60),
             r["historical_count"], _decimal(r["historical_expected"]),
             format_hours(r["historical_minutes"]), _decimal(r["historical_expected_minutes"] / 60),
             _decimal(r["cumulative_deviation"]), _decimal(r["cumulative_minute_deviation"] / 60)]
            for r in fairness_rows(data, history=history)]
    _write_csv(path, ["Person", "Schichttyp", "Einsätze im Monat", "Stunden im Monat", "Fairer Anteil Einsätze",
                      "Abweichung Einsätze", "Fairer Anteil Stunden", "Abweichung Stunden",
                      "Besondere Einsätze Historie", "Fairer Anteil Historie", "Besondere Stunden Historie",
                      "Fairer Stundenanteil Historie", "Besondere Abweichung einschließlich Historie",
                      "Besondere Stundenabweichung einschließlich Historie"], rows)


def export_wishes(path: Path | str, data: MonthData,
                  wish_history: list[WishHistoryEntry] | None = None) -> None:
    """Exportiert die eingefrorene/aktuelle Statistik ohne erfundene Althistorie."""
    rows = [[r["name"], r["relevant"], r["fulfilled"], r["violated"],
             r["historical"], r["cumulative"],
             ", ".join(r["missing_months"]) or "Keine",
             ("Damals bestätigte Wunschstatistik fehlt; angezeigte Monatszahlen aus aktuellen Sperren"
              if r.get("snapshot_missing") else ("Bestätigter Wunschstand" if data.confirmed else "Aktueller Entwurf")),
             "Dienstplan-Prognose"]
            for r in wish_rows(data, wish_history=wish_history)]
    _write_csv(path, ["Person", "Relevante Priorität-2-Wünsche", "Erfüllte Wünsche im Monat",
                      "Übergangene Wünsche im Monat", "Historische Übergehungen",
                      "Kumulierte Belastung", "Fehlende bestätigte Althistorie", "Statistikstatus", "Hinweis"], rows)
