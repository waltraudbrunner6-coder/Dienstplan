import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QDialog,QCheckBox,QPushButton,QMessageBox
from dienstplan.v2.ui import Workbench
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.import_ui import import_dialog


def test_u_import_uses_confirmed_day_rule_and_keeps_existing_plan(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    w=Workbench(database=tmp_path/'db',initial=technical_demo(),year=2026,month=11)
    old=w.blocks
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:(_ for _ in ()).throw(AssertionError(str(a))))
    def drive(dialog):
        check=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Vorschau prüfen und vormerken')
        check.click()
        assert w.store.sheet_stage()['rows'][0]['art']=='urlaub'
        assert w.store.sheet_stage()['rows'][0]['gutschrifttage']=='2026-11-17'
        next(b for b in dialog.findChildren(QPushButton) if b.text()=='Gesamten Import übernehmen').click()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',drive)
    try:
        import_dialog(w,[dict(art='u_zuordnung_offen',datum='2026-11-17',person_id='A',dienst='U')],{})
        assert w.blocks==old and w.inputs.absences[0].credit_days
        assert w.store.load_workspace(2026,11)[2]==old
    finally:w.close();app.processEvents()
