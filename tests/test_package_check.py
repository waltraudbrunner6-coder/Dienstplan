"""Native GUI-Pakete müssen ohne Konsole belastbare Prüfergebnisse liefern."""
import builtins
import json
from types import SimpleNamespace

import pytest

from dienstplan.smoke import run_smoke_test
from scripts.check_package import check_package


def test_import_failure_is_recorded_without_standard_output(tmp_path, monkeypatch):
    original = builtins.__import__
    def importing(name, *args, **kwargs):
        if name == "csvio":
            raise ImportError("Fehlende Test-DLL")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", importing)
    monkeypatch.setattr("sys.stdout", None)
    report = tmp_path / "report.json"
    assert run_smoke_test(report) == 1
    values = json.loads(report.read_text(encoding="utf-8"))
    assert values["selbsttest"] == "fehlgeschlagen"
    assert values["fehler"] == "Fehlende Test-DLL"
    assert "ImportError" in values["details"]


@pytest.mark.parametrize("exit_code,report_kind,expected", [
    (0, "valid", 0), (1, "valid", 1), (0, "missing", 1),
    (0, "failed", 1), (0, "incomplete", 1),
])
def test_package_check_requires_exit_status_and_full_report(tmp_path, monkeypatch, exit_code, report_kind, expected):
    from scripts import check_package as checker
    # Dieser Test simuliert ausschließlich den Programmprozess. Ein echter
    # GitHub-Step-Bericht gehört zum nachfolgenden nativen Build, nicht zur
    # Testphase vor Existenz von dist/build-report.json.
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    def run(command):
        assert command[1:3] == ["--self-test", "--self-test-report"]
        if report_kind != "missing":
            values = dict(selbsttest="bestanden", personen=12, zuteilungen=186,
                          csv_sqlite_solver_qt=True, ausnahmetage=True,
                          kurzer_sonderdienst=True, freiwunschhistorie=True)
            if report_kind == "failed":
                values["selbsttest"] = "fehlgeschlagen"
            if report_kind == "incomplete":
                values.pop("freiwunschhistorie")
            from pathlib import Path
            Path(command[3]).write_text(json.dumps(values), encoding="utf-8")
        return SimpleNamespace(returncode=exit_code)
    monkeypatch.setattr(checker.subprocess, "run", run)
    assert check_package(tmp_path / "Dienstplan") == expected
