"""Gebautes GUI-Programm prüfen, auch ohne Windows-Standardausgabe."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile


def error_annotation(message: str):
    # GitHub stellt Annotationen auch in der öffentlichen Laufübersicht bereit.
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::error title=Paket-Selbsttest fehlgeschlagen::" + escaped)


def check_package(executable: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="dienstplan-paketpruefung-") as directory:
        report = Path(directory) / "selbsttest.json"
        result = subprocess.run([str(executable.resolve()), "--self-test", "--self-test-report", str(report)])
        if not report.exists():
            error_annotation(f"Kein Selbsttest-Bericht; Programmstart fehlgeschlagen (Exitcode {result.returncode}).")
            return result.returncode or 1
        values = json.loads(report.read_text(encoding="utf-8"))
        print(json.dumps(values, ensure_ascii=False, indent=2))
        checks = ("csv_sqlite_solver_qt", "ausnahmetage", "kurzer_sonderdienst", "freiwunschhistorie")
        valid = (values.get("selbsttest") == "bestanden"
                 and all(values.get(key) is True for key in checks)
                 and values.get("personen") == 12 and values.get("zuteilungen") == 186)
        if result.returncode or not valid:
            error_annotation(values.get("details") or values.get("fehler") or
                             f"Unvollständiger Selbsttest-Nachweis (Exitcode {result.returncode}).")
        elif os.environ.get("GITHUB_STEP_SUMMARY"):
            # Die öffentlich sichtbare Jobübersicht dokumentiert auch die
            # tatsächlich gemessenen Paketgrößen ohne Artefaktdownload.
            build_report = Path(__file__).resolve().parents[1] / "dist" / "build-report.json"
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
                summary.write("## Paket und bestandener Selbsttest\n\n```json\n")
                summary.write(build_report.read_text(encoding="utf-8"))
                summary.write("\n```\n\n```json\n" + json.dumps(values, ensure_ascii=False, indent=2) + "\n```\n")
        return result.returncode or (0 if valid else 1)


if __name__ == "__main__":
    path = ("dist/Dienstplan.app/Contents/MacOS/Dienstplan" if sys.platform == "darwin" else
            "dist/Dienstplan/Dienstplan.exe" if sys.platform == "win32" else "dist/Dienstplan/Dienstplan")
    raise SystemExit(check_package(Path(path)))
