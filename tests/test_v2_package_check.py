import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.check_package import check_v2_package


@pytest.mark.parametrize('missing,exitcode,expected',[(False,0,0),(True,0,1),(False,1,1),('main',0,1),('standarddienste',0,1),('ausschlussliste',0,1),('stundenanzeige',0,1),('dauerhafte_datei',0,1),('build',0,1),('different_commit',0,1)])
def test_v2_package_requires_actual_process_and_complete_report(tmp_path,monkeypatch,missing,exitcode,expected):
    def run(command,env):
        assert command[1:3]==['--self-test-v2','--self-test-report'] and env['PYTHONTZPATH']==''
        if missing is not True:
            values=dict(selbsttest='bestanden',personen=12,zuteilungen=8,
                    dst=True,solver_pruefer=True,sqlite=True,exportpaket=True,qt=True,
                    hauptoberflaeche=True,standarddienste=True,ausschlussliste=True,stundenanzeige=True,dauerhafte_datei=True,build={'commit':'a'*40})
            if isinstance(missing,str) and missing!='different_commit':values.pop('hauptoberflaeche' if missing=='main' else missing)
            Path(command[3]).write_text(json.dumps(values),encoding='utf-8')
        return SimpleNamespace(returncode=exitcode)
    monkeypatch.setattr('scripts.check_package.subprocess.run',run)
    assert check_v2_package(tmp_path/'Dienstplan',expected_commit='b'*40 if missing=='different_commit' else None)==expected
