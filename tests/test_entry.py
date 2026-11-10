"""Der einzige Programmeinstieg erhält existierende V2-Monatsstände."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from PySide6.QtWidgets import QApplication

from dienstplan.v2.application import demonstration_month
from dienstplan.v2.persistence import V2Store


def test_demo_entry_reopens_existing_plan(tmp_path,monkeypatch):
    from dienstplan import __main__ as entry
    from dienstplan.v2 import ui
    app=QApplication.instance() or QApplication([])
    database=tmp_path/'demo.sqlite3'
    inputs,profile,blocks=demonstration_month()
    inputs=replace(inputs,people=(replace(inputs.people[0],name='Gespeicherte Beispielperson'),)+inputs.people[1:])
    with V2Store(database,create=True) as store:
        store.save_workspace(inputs,profile,blocks,None,expected_revision=0)
    original=ui.Workbench;seen=[]
    class Window(original):
        def show(self):seen.append((self.inputs,self.blocks))
    monkeypatch.setattr(ui,'Workbench',Window)
    monkeypatch.setattr(QApplication,'exec',lambda *_:0)
    assert entry.main(['--demo','--database',str(database)])==0
    assert seen==[(inputs,blocks)]
