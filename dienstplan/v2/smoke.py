"""Paketprobe der Hauptoberfläche und der Rechenkette mit isolierten Testdaten."""
import json
from pathlib import Path
import tempfile
import traceback


def run(report_path=None):
    values={}
    try:
        from datetime import datetime,timedelta
        from .time import local_instant,TZDATA_VERSION,IANA_VERSION
        from .errors import DomainError
        spring_rejected=False
        try:local_instant(datetime(2026,3,29,2,30))
        except DomainError:spring_rejected=True
        assert spring_rejected
        early=local_instant(datetime(2026,10,25,2,30),fold=0)
        late=local_instant(datetime(2026,10,25,2,30),fold=1)
        assert late-early==timedelta(hours=1)
        from .demo import technical_demo
        from .solver import solve_feasibility,verify
        from .persistence import V2Store
        from .exporting import export_package
        from .codec import workspace,restore_workspace
        from PySide6.QtWidgets import QApplication
        from .ui import Workbench
        from ..build_info import build_info
        import sys
        identity=build_info()
        if getattr(sys,'frozen',False):assert identity['commit'], 'Paketkennung fehlt im gebauten Programm.'
        with tempfile.TemporaryDirectory(prefix='dienstplan-v2-paket-') as directory:
            inputs,profile,old=technical_demo()
            result=solve_feasibility(inputs,time_limit=3,existing=old,objective_profile=profile)
            assert len(result.blocks)==8 and not result.open_slots
            core,calendar=verify(inputs,result.blocks,active_events=result.events)
            assert core.hard_ok and calendar.hard_ok
            path=Path(directory)/'test.sqlite3'
            with V2Store(path,create=True) as store:
                store.save_workspace(inputs,profile,result.blocks,result.events,expected_revision=0)
                assert store.load_workspace(2026,11)[2]==result.blocks
            manifest=export_package(Path(directory)/'export.zip',inputs,profile,result.blocks,result.events)
            assert manifest['revision_id']==workspace(inputs,profile,result.blocks,result.events)['revision_id']
            assert restore_workspace(workspace(inputs,profile,result.blocks,result.events))[0]==inputs
            app=QApplication.instance() or QApplication([])
            from .application import demonstration_month
            window=Workbench(database=Path(directory)/'hauptoberflaeche.sqlite3',initial=demonstration_month(),year=2026,month=11)
            window.show();app.processEvents()
            assert window.isVisible() and window.team.rowCount()==12
            assert 'Prüfbereich' not in window.windowTitle()
            assert window.catalog_table.rowCount()==19 and len(window.inputs.events)==94
            assert window.team.horizontalHeaderItem(6).text()=='Ausgeschlossene Dienste'
            assert window.team.horizontalHeaderItem(3).text()=='Anfang (h)'
            assert window.inputs.people[0].rights[0].excluded_codes==frozenset()
            window.team.item(0,1).setText('Dauerhaft gespeicherte Beispielperson')
            window.save();window.close();app.processEvents()
            reopened=Workbench(database=Path(directory)/'hauptoberflaeche.sqlite3')
            assert reopened.inputs.people[0].name=='Dauerhaft gespeicherte Beispielperson'
            assert len(reopened.inputs.events)==94
            reopened.close()
            preview_window=Workbench(database=Path(directory)/'vorschau.sqlite3',initial=(inputs,profile,old),year=2026,month=11)
            from .serialization import fingerprint
            token=(preview_window.generation,preview_window.store.input_revision,inputs.fingerprint,fingerprint(profile))
            preview_window.on_worker_completed(result,token)
            assert preview_window.pending and preview_window.tabs.currentWidget() is preview_window.plan.parentWidget()
            assert preview_window.plan.rowCount()==8
            assert all(preview_window.plan.item(row,3).text()!='OFFEN' for row in range(8))
            assert 'VORSCHLAG' in preview_window.plan_state.text()
            preview_window.accept.click()
            assert preview_window.store.load_workspace(2026,11)[2]==result.blocks
            preview_window.close()
        values=dict(selbsttest='bestanden',scope='Hauptoberfläche mit Standardmonat; Rechenkette separat mit synthetischer Fixture',
                    personen=12,zuteilungen=8,tzdata=TZDATA_VERSION,iana=IANA_VERSION,
                    dst=True,solver_pruefer=True,sqlite=True,exportpaket=True,qt=True,
                    hauptoberflaeche=True,standarddienste=True,ausschlussliste=True,stundenanzeige=True,dauerhafte_datei=True,vorschau_anzeige=True,build=identity)
        code=0
    except Exception as exc:
        values=dict(selbsttest='fehlgeschlagen',fehler=str(exc),details=traceback.format_exc());code=1
    if report_path is not None:Path(report_path).write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(values,ensure_ascii=False))
    return code
