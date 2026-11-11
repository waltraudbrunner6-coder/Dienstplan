"""Explizite Nutzerentscheidung; technische Fehler bleiben atomar gesperrt."""
from dataclasses import replace
from datetime import date
import json
import zipfile
import pytest
from openpyxl import load_workbook
from dienstplan.v2.application import demonstration_month
from dienstplan.v2.catalog import event
from dienstplan.v2.entries import preview,WishBudget
from dienstplan.v2.errors import DomainError
from dienstplan.v2.plan_import import prepare_plan_import
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.solver import verify
from dienstplan.v2.spreadsheets import export_month_grid
from dienstplan.v2.exporting import export_package


def row(code='W17',day='2026-11-10',pid='P01',kind='dienst',**kw):
    return dict(art=kind,datum=day,dienst=code,person_id=pid,**kw)


def test_explicit_import_override_keeps_thursday_warning_after_restart_and_export(tmp_path):
    data,profile,_=demonstration_month()
    rows=[row('KC10','2026-11-12'),row('', '2026-11-12',kind='freiwunschtag')]
    assert not prepare_plan_import(data,rows).ready
    p=prepare_plan_import(data,rows,allow_rules=True)
    assert p.ready,p.errors
    assert p.inputs.manual_override and p.notes
    assert not verify(p.inputs,p.blocks,active_events=p.events)[0].hard_ok
    with V2Store(tmp_path/'db',create=True) as s:
        s.apply_sheet_import(p,profile,expected_revision=0)
    with V2Store(tmp_path/'db') as s:
        loaded,pr,blocks,events=s.load_workspace(2026,11)
        assert loaded.manual_override and loaded.override_notes==p.notes
        assert not verify(loaded,blocks,active_events=events)[0].hard_ok
        manifest=export_package(tmp_path/'export.zip',loaded,pr,blocks,events)
        assert manifest['manual_override'] and manifest['issues']
        export_month_grid(tmp_path/'export.xlsx',loaded,pr,blocks,events)
        assert 'REGELÜBERSTEUERUNG' in str(list(load_workbook(tmp_path/'export.xlsx')['Regelmeldungen'].values))


@pytest.mark.parametrize('bad',[row(pid='unknown'),row(code='KC99'),row(day='not-date'),row(pause_von='bad',pause_bis='bad')])
def test_override_never_activates_technically_invalid_partial_import(tmp_path,bad):
    data,profile,_=demonstration_month()
    p=prepare_plan_import(data,[row(),bad],allow_rules=True)
    assert not p.ready
    with V2Store(tmp_path/'db',create=True) as s:
        with pytest.raises(DomainError):s.apply_sheet_import(p,profile,expected_revision=0)
        assert s.load_workspace(2026,11) is None


def test_override_allows_same_day_bk_wl_but_reports_exclusion():
    data,_,_=demonstration_month()
    rows=[row('BK',kind='termin'),row('WL',kind='termin')]
    assert not prepare_plan_import(data,rows).ready
    p=prepare_plan_import(data,rows,allow_rules=True)
    assert p.ready
    assert 'wl_bk_exclusion' in {i.rule for i in verify(p.inputs,p.blocks,active_events=p.events)[0].issues}


def test_absence_csv_override_thursday_and_budget_still_rejects_bad_time(tmp_path):
    data,profile,_=demonstration_month()
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;P01;t;freiwunschtag;2026-11-12T00:00;2026-11-13T00:00;;Test\n'
    batch=preview(text,month='2026-11')
    assert not batch.ready
    with V2Store(tmp_path/'db',create=True) as s:
        s.save_correction('test',batch)
        updated=s.apply_correction('test',data,profile,budgets={},expected_revision=0,allow_rules=True)
        assert updated.manual_override and s.entries()[0].rule_override
        assert s.load_workspace(2026,11)[0].absences[0].rule_override
    assert not preview(text.replace('2026-11-12T00:00','bad'),month='2026-11',allow_rules=True).ready


def test_override_import_of_existing_term_is_not_a_conflicting_new_template():
    data,_,_=demonstration_month()
    p=prepare_plan_import(data,[row()],allow_rules=True)
    assert p.ready,p.errors
    assert len(p.blocks)==1
