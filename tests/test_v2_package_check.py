import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.check_package import check_v2_package


@pytest.mark.parametrize('missing,exitcode,expected',[(False,0,0),(True,0,1),(False,1,1),('startup',0,1),('build',0,1),('different_commit',0,1)])
def test_v2_package_requires_actual_process_and_complete_report(tmp_path,monkeypatch,missing,exitcode,expected):
    def run(command,env):
        assert command[1:3]==['--self-test-v2','--self-test-report'] and env['PYTHONTZPATH']==''
        if missing is not True:
            values=dict(selbsttest='bestanden',personen=12,zuteilungen=8,
                    dst=True,solver_pruefer=True,sqlite=True,exportpaket=True,qt=True,
                    startauswahl=True,build={'commit':'a'*40})
            if missing in ('startup','build'):values.pop('startauswahl' if missing=='startup' else 'build')
            Path(command[3]).write_text(json.dumps(values),encoding='utf-8')
        return SimpleNamespace(returncode=exitcode)
    monkeypatch.setattr('scripts.check_package.subprocess.run',run)
    assert check_v2_package(tmp_path/'Dienstplan',expected_commit='b'*40 if missing=='different_commit' else None)==expected
