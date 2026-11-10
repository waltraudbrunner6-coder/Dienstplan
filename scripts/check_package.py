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


def check_v2_package(executable: Path,expected_commit=None) -> int:
    with tempfile.TemporaryDirectory(prefix='dienstplan-v2-paketpruefung-') as directory:
        report=Path(directory)/'v2-selbsttest.json'
        environment=os.environ.copy();environment['PYTHONTZPATH']=''
        result=subprocess.run([str(executable.resolve()),'--self-test-v2','--self-test-report',str(report)],env=environment)
        if not report.exists():
            error_annotation('Kein V2-Paketbericht; Programmstart/Zeitzonendaten prüfen.');return result.returncode or 1
        values=json.loads(report.read_text(encoding='utf-8'));print(json.dumps(values,ensure_ascii=False,indent=2))
        commit=values.get('build',{}).get('commit')
        valid=(values.get('selbsttest')=='bestanden' and values.get('personen')==12 and values.get('zuteilungen')==8
               and all(values.get(key) is True for key in ('dst','solver_pruefer','sqlite','exportpaket','qt','hauptoberflaeche','standarddienste','ausschlussliste','stundenanzeige','dauerhafte_datei','vorschau_anzeige','excel_import_export','automatic_pause','weekly_configuration','manual_assignment'))
               and isinstance(commit,str) and len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
               and (expected_commit is None or commit==expected_commit))
        if result.returncode or not valid:error_annotation(values.get('details') or 'V2-Paketprüfung unvollständig/fehlgeschlagen.')
        elif os.environ.get('GITHUB_ACTIONS')=='true':
            print('::notice title=V2-Paketprüfung bestanden::'+json.dumps(values,ensure_ascii=False).replace('%','%25'))
        return result.returncode or (0 if valid else 1)


def check_package(executable: Path) -> int:
    """Kompatibler Aufrufname, prüft ausschließlich die neue Hauptanwendung."""
    return check_v2_package(executable)


if __name__ == "__main__":
    path = ("dist/Dienstplan.app/Contents/MacOS/Dienstplan" if sys.platform == "darwin" else
            "dist/Dienstplan/Dienstplan.exe" if sys.platform == "win32" else "dist/Dienstplan/Dienstplan")
    report=Path(__file__).resolve().parents[1]/'dist'/'build-report.json'
    expected=json.loads(report.read_text(encoding='utf-8'))['commit']
    raise SystemExit(check_v2_package(Path(path),expected))
