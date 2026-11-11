"""Startauswahl darf die bisherige Benutzerdatenbank nicht unbemerkt öffnen."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer,QStandardPaths
from PySide6.QtWidgets import QApplication,QMessageBox

from dienstplan import __main__ as entry
from dienstplan.build_info import build_info,build_label
from dienstplan.startup import StartDialog


@pytest.fixture
def app():return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('direct',[False,True])
def test_v2_entrypoint_real_event_loop_does_not_touch_legacy_database(app,tmp_path,monkeypatch,direct):
    from dienstplan import startup,storage
    from dienstplan.v2.ui import Workbench
    database=tmp_path/'dienstplan.sqlite3'
    with storage.Store(database) as store:
        store.connection.execute("INSERT INTO months VALUES('sentinel','original user data')")
        store.connection.commit()
    before=database.read_bytes()
    monkeypatch.setattr(QStandardPaths,'writableLocation',lambda *_:str(tmp_path))
    def forbidden(*_):raise AssertionError('V2 darf die bisherige Datenbank nicht öffnen.')
    monkeypatch.setattr(storage,'Store',forbidden)
    def fail_message(*args):raise AssertionError(str(args))
    monkeypatch.setattr(QMessageBox,'critical',fail_message)
    seen=[];timer=QTimer();timeout=QTimer();timeout.setSingleShot(True)
    def inspect():
        for widget in app.topLevelWidgets():
            if isinstance(widget,startup.StartDialog) and widget.isVisible():raise AssertionError('Keine zweite Startoberfläche erlaubt.')
            if isinstance(widget,Workbench) and widget.isVisible():
                seen.append(widget.catalog_table.rowCount());widget.close()
    timer.timeout.connect(inspect);timer.start(20);timeout.timeout.connect(app.quit);timeout.start(10000)
    try:
        assert entry.main(['--v2'] if direct else [])==0
        assert seen==[20]
        assert (tmp_path/'dienstplan-v2.sqlite3').is_file()
        assert database.read_bytes()==before
    finally:
        timer.stop();timeout.stop()
        for widget in app.topLevelWidgets():
            if isinstance(widget,(StartDialog,Workbench)):widget.close()


def test_legacy_launch_is_rejected_before_opening_data(tmp_path):
    with pytest.raises(SystemExit) as exc:entry.main(['--legacy','--database',str(tmp_path/'old.sqlite3')])
    assert exc.value.code==2 and not list(tmp_path.iterdir())


def test_build_identity_reads_offline_resource_and_rejects_invalid_values(tmp_path,monkeypatch):
    from dienstplan import build_info as module
    monkeypatch.setattr(module,'files',lambda *_:tmp_path)
    assert build_info()['commit'] is None
    from dienstplan import __version__
    valid=dict(version=__version__,commit='a'*40,dirty=False,build_time_utc='2026-11-10T00:00:00+00:00')
    (tmp_path/'build-info.json').write_text(json.dumps(valid),encoding='utf-8')
    assert build_info()==valid and 'Build aaaaaaa' in build_label()
    (tmp_path/'build-info.json').write_text('{bad',encoding='utf-8')
    assert 'kein Paketbuild' in build_label()
