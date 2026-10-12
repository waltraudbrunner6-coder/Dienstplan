"""Vollständige Tests mit öffentlich sichtbaren CI-Fehlerdiagnosen ausführen."""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    report = Path("build/test-results.xml")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={report}"])
    if result.returncode and report.exists():
        for case in ET.parse(report).iter("testcase"):
            for failure in list(case.findall("failure")) + list(case.findall("error")):
                message = f"{case.get('classname')}::{case.get('name')}\n{failure.text or failure.get('message', '')}"
                escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print("::error title=Automatisierter Regressionstest fehlgeschlagen::" + escaped)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
