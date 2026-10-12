"""Native Desktop-Pakete mit PyInstaller; auf dem jeweiligen Zielsystem ausführen."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None, help="Ausgabeordner (Standard: dist)")
    parser.add_argument("--no-strip", action="store_true", help="Linux-Debugsymbole für Diagnose erhalten")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (args.output or root / "dist").resolve()
    working = root / "build" / "desktop"
    working.mkdir(parents=True, exist_ok=True)
    launcher = working / "desktop_entry.py"
    launcher.write_text('import runpy\nrunpy.run_module("dienstplan", run_name="__main__")\n', encoding="utf-8")
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--windowed", "--name", "Dienstplan",
        "--distpath", str(output), "--workpath", str(working / "analysis"),
        "--specpath", str(working), "--paths", str(root),
        "--collect-submodules", "dienstplan",
        "--add-data", str(root / "README.md") + os.pathsep + ".",
        "--add-data", str(root / "docs") + os.pathsep + "docs",
    ]
    # Die Linux-Bibliotheken enthalten große Debugsymboltabellen. PyInstaller
    # verwendet das native strip-Werkzeug, das benötigte Laufzeitsymbole erhält.
    # Windows/macOS bleiben unverändert, auch für spätere Signierung.
    stripped = sys.platform.startswith("linux") and not args.no_strip and shutil.which("strip") is not None
    if stripped:
        command.append("--strip")
    # Nur CP-SAT wird verwendet. Qt Widgets braucht weder WebEngine noch QML.
    for module in (
        "ortools.constraint_solver", "ortools.linear_solver", "ortools.graph",
        "ortools.math_opt", "ortools.scheduling", "ortools.pdlp",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets", "PySide6.QtTest", "tkinter",
        "matplotlib", "scipy", "IPython", "notebook", "jupyter", "pytest",
    ):
        command.extend(["--exclude-module", module])
    command.append(str(launcher))
    build_env = os.environ.copy()
    build_env["PYINSTALLER_CONFIG_DIR"] = str(working / "cache")
    subprocess.run(command, cwd=root, env=build_env, check=True)
    artifact = output / ("Dienstplan.app" if sys.platform == "darwin" else "Dienstplan")
    # Symlinks in macOS-Frameworks nicht mehrfach als kopierte Bibliotheken zählen.
    byte_count = sum(p.stat().st_size for p in artifact.rglob("*") if p.is_file() and not p.is_symlink())
    platform_name = platform.system()
    architecture = platform.machine()
    archive_base = output / f"Dienstplan-{platform_name}-{architecture}"
    if sys.platform == "win32":
        archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=output, base_dir=artifact.name))
    else:
        archive = Path(str(archive_base) + ".tar.gz")
        # tar erhält Ausführungsrechte und Symlinks von macOS-Frameworks;
        # rohe upload-artifact-Dateien würden diese Informationen verlieren.
        with tarfile.open(archive, "w:gz", compresslevel=6) as package:
            package.add(artifact, arcname=artifact.name)
    result = {
        "platform": platform_name, "architecture": architecture,
        "python": platform.python_version(), "artifact": str(artifact),
        "bytes": byte_count, "mib": round(byte_count / (1024 * 1024), 2),
        "archive": str(archive), "archive_bytes": archive.stat().st_size,
        "archive_mib": round(archive.stat().st_size / (1024 * 1024), 2),
        "signed": False, "stripped": stripped,
    }
    (output / "build-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Erstellt: {artifact}\nUnkomprimierte Paketgröße: {result['mib']:.2f} MiB ({byte_count} Bytes)"
          f"\nArchiv: {archive} ({result['archive_mib']:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
