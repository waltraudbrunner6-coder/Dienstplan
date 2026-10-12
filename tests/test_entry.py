"""Wiederholtes Öffnen der Demo muss einen bestehenden Monatsplan bewahren."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from dienstplan.demo import demo_month
from dienstplan.model import Assignment, generate_shifts
from dienstplan.storage import Store


def test_demo_entry_reopens_existing_plan(tmp_path, monkeypatch):
    from dienstplan import __main__ as entry
    app=QApplication.instance() or QApplication([])
    database=tmp_path/"demo.sqlite3"
    data=demo_month()
    data.employees[0].name="Gespeicherte Beispielperson"
    data.assignments=[Assignment(generate_shifts(data)[0].id,data.employees[0].id,True)]
    with Store(database) as store:
        store.save_month(data)
    shown=[]
    class FakeWindow:
        def __init__(self,store,year,month,data):
            shown.append(data)
        def show(self):
            pass
    monkeypatch.setattr(entry,"MainWindow",FakeWindow)
    monkeypatch.setattr(QApplication,"exec",lambda *args:0)
    assert entry.main(["--demo","--database",str(database)])==0
    assert shown[0].assignments==data.assignments
    assert shown[0].employees[0].name=="Gespeicherte Beispielperson"
