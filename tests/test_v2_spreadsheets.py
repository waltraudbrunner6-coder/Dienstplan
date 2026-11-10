"""Nur synthetische Tabellen; keine hochgeladenen Personaldaten in Regressionen."""
from dataclasses import replace
from datetime import date,datetime
from pathlib import Path
import pytest
from openpyxl import Workbook,load_workbook
from openpyxl.styles import PatternFill

from dienstplan.v2.spreadsheets import read_import,write_import_template,export_month_grid,COLUMNS
from dienstplan.v2.plan_import import prepare_plan_import,selected_events
from dienstplan.v2.automatic_weekly import automatic_weekly
from dienstplan.v2.application import demonstration_month,standard_month
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.catalog import event
from dienstplan.v2.entries import WishBudget
from dienstplan.v2.pauses import automatic_pause_choices
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.solver import verify,solve_feasibility
from dienstplan.v2.time import vienna
from dienstplan.v2.errors import DomainError


def row(day='2026-11-10',kind='dienst',code='W17',pid='P01',**extra):
    return dict(quelle='Test!B4',person_ref='Zeile 4',person_id=pid,datum=day,art=kind,dienst=code,fixiert='ja',**extra)


def test_colored_wishes_and_fixed_services_are_distinct_and_sources_preserved(tmp_path):
    path=tmp_path/'wishes.xlsx';b=Workbook();s=b.active
    for col in range(1,5):s.cell(1,col,datetime(2026,12,col))
    s['A4']='x';s['A4'].fill=PatternFill('solid',fgColor='FFFFFF00')
    s['B4']='x';s['B4'].fill=PatternFill('solid',fgColor='FF00FF00')
    s['C4']='W17';s['D4']='U';b.save(path);before=path.read_bytes()
    rows,mapping,notes=read_import(path,source_kind='wishes')
    assert [r['art'] for r in rows]==['freiwunschtag','dienst','u_zuordnung_offen']
    assert rows[1]['dienst']=='W17' and rows[1]['fixiert']=='ja' and mapping=={'Zeile 4':''}
    assert path.read_bytes()==before
    target=tmp_path/'normal.xlsx';write_import_template(target,rows,mapping,notes)
    b=load_workbook(target);b['Personen']['B2']='P01';b.save(target)
    reread,_,_=read_import(target)
    assert all(r['person_id']=='P01' for r in reread)


def test_plan_x_does_not_create_wish_and_nh_is_explicitly_ignored(tmp_path):
    p=tmp_path/'plan.xlsx';b=Workbook();s=b.active;s['A1']=datetime(2026,11,1);s['B1']=datetime(2026,11,2);s['A4']='x';s['B4']='NH';b.save(p)
    rows,_,notes=read_import(p)
    assert not rows and any('NH' in n for n in notes)


def test_template_roundtrip_never_executes_cell_formulas(tmp_path):
    path=tmp_path/'template.xlsx';write_import_template(path,[row(kommentar='=HYPERLINK("bad")')],{'Zeile 4':'P01'})
    b=load_workbook(path,data_only=False)
    assert b['Import'].cell(2,COLUMNS.index('kommentar')+1).data_type=='s'
    rows,_,_=read_import(path);assert rows[0]['kommentar'].startswith('=HYPERLINK')
    b['Import']['A2']='=1+1';b.save(path)
    with pytest.raises(DomainError,match='Formeln'):read_import(path)


def test_fixed_assignment_and_term_import_preserve_two_distinct_slots_and_pauses():
    data,p,_=demonstration_month()
    result=prepare_plan_import(data,[row(),row(pid='P02'),row(kind='termin',code='BK',pid='')])
    assert result.ready,result.errors
    assert len(result.blocks)==len(result.inputs.locked)==2
    assert all(b.breaks[0].end.astimezone(vienna()).hour<22 for b in result.blocks)
    assert not verify(result.inputs,result.blocks,active_events=result.events)[0].issues
    duplicate=prepare_plan_import(result.inputs,[row()],blocks=result.blocks,events=result.events)
    assert duplicate.ready and len(duplicate.blocks)==2


def test_invalid_import_has_precise_errors_and_does_not_touch_store(tmp_path):
    data,p,_=demonstration_month();path=tmp_path/'db.sqlite3'
    with V2Store(path,create=True) as store:
        store.save_workspace(data,p,expected_revision=0);before=store.load_workspace(2026,11)
        rows=[row(),row(pid='missing'),row(code='KC15'),row(day='2026-12-01')]
        store.save_sheet_stage(rows,{'Zeile 4':'P01'})
        proposal=prepare_plan_import(data,rows)
        assert not proposal.ready and any('unbekannt' in e.lower() for e in proposal.errors)
        with pytest.raises(DomainError,match='Teilübernahme'):store.apply_sheet_import(proposal,p,expected_revision=store.input_revision)
        assert store.load_workspace(2026,11)==before and store.sheet_stage()


def test_mixed_wishes_leave_and_fixed_assignment_save_atomically_and_reload(tmp_path):
    data,p,_=demonstration_month();rows=[row(),row(day='2026-11-11',kind='freiwunschtag',code=''),row(day='2026-11-23',kind='urlaub',code='')]
    result=prepare_plan_import(data,rows,budgets={('P01','2026-11'):WishBudget(3)})
    assert result.ready,result.errors
    path=tmp_path/'db.sqlite3'
    with V2Store(path,create=True) as store:
        store.save_workspace(data,p,expected_revision=0);store.save_sheet_stage(rows,{})
        store.apply_sheet_import(result,p,expected_revision=store.input_revision)
        assert len(store.entries())==2 and store.sheet_stage() is None
    with V2Store(path) as store:
        loaded=store.load_workspace(2026,11)
        assert loaded[0]==result.inputs and loaded[2]==result.blocks


def test_sql_failure_rolls_back_whole_mixed_import_and_retains_corrections(tmp_path):
    data,p,_=demonstration_month();rows=[row(),row(day='2026-11-23',kind='urlaub',code='')]
    result=prepare_plan_import(data,rows);assert result.ready
    with V2Store(tmp_path/'db.sqlite3',create=True) as store:
        store.save_workspace(data,p,expected_revision=0);rev=store.input_revision;old=store.load_workspace(2026,11)
        store.save_sheet_stage(rows,{})
        store.connection.execute("CREATE TRIGGER stop_sheet BEFORE INSERT ON v2_entries BEGIN SELECT RAISE(ABORT,'rollback-sheet'); END")
        with pytest.raises(Exception,match='rollback-sheet'):store.apply_sheet_import(result,p,expected_revision=rev)
        assert store.input_revision==rev and not store.entries() and store.sheet_stage()
        assert store.load_workspace(2026,11)==old


def test_wish_budget_hard_leave_capacity_and_eligibility_are_not_bypassed():
    data,p,_=demonstration_month()
    assert not prepare_plan_import(data,[row(),row(pid='P02'),row(pid='P03')]).ready
    assert not prepare_plan_import(data,[row(),row(kind='urlaub',code='')]).ready
    wish=row(kind='freiwunschtag',code='')
    assert not prepare_plan_import(data,[wish],budgets={('P01','2026-11'):WishBudget(0)}).ready
    restricted=replace(data.people[0],rights=(replace(data.people[0].rights[0],codes=frozenset({'T'})),))
    assert not prepare_plan_import(replace(data,people=(restricted,)+data.people[1:]),[row()]).ready


def test_automatic_pause_before_22_and_middle_when_impossible():
    term=event('BK',date(2026,11,10));choice=automatic_pause_choices(term,'P01')[0]
    assert choice.breaks[0].end.astimezone(vienna()).strftime('%H:%M')=='22:00'
    term=event('FK',date(2026,11,10),people=('P01',),attendance=__import__('dienstplan.v2.time',fromlist=['Interval']).Interval.local('2026-11-10T23:00','2026-11-11T07:00'))
    choice=automatic_pause_choices(term,'P01')[0]
    assert choice.breaks[0].start.astimezone(vienna()).strftime('%H:%M')=='02:45'
    short=event('KC10',date(2026,11,10));assert not automatic_pause_choices(short,'P01')[0].breaks
    team=event('KCT10',date(2026,11,12));assert all(not p.overlaps(team.protected[0]) for p in automatic_pause_choices(team,'P01')[0].breaks)


def test_excel_month_grid_has_weekdays_person_rows_open_slots_and_reimport(tmp_path):
    data,p,old=technical_demo();path=tmp_path/'export.xlsx'
    export_month_grid(path,data,p,old,data.events)
    book=load_workbook(path)
    assert book['Monatsübersicht']['C2'].value=='So'
    assert book['Monatsübersicht']['D3'].value=='WL'
    assert book['Monatsübersicht'].freeze_panes=='C3'
    rows,_,_=read_import(path);proposal=prepare_plan_import(data,rows)
    assert proposal.ready,proposal.errors
    assert set(proposal.blocks)==set(old)
    assert proposal.inputs.locked==data.locked
    with pytest.raises(FileExistsError):export_month_grid(path,data,p,old,data.events)


def test_two_wl_one_bk_quotas_do_not_change_by_season_and_exclude_same_day():
    for month in (11,12,1):
        data,_,_=standard_month(2026,month)
        data=automatic_weekly(data)
        assert all(q.required==(2 if q.code=='WL' else 1) for q in data.quotas)
        chosen=selected_events(data)
        core,cal=verify(data,(),active_events=chosen)
        assert core.hard_ok
        wl={e.attendance.start_day for e in chosen if e.service.code=='WL'}
        bk={e.attendance.start_day for e in chosen if e.service.code=='BK'}
        assert not wl&bk


def test_shared_week_keeps_dates_people_and_history_is_not_double_counted(tmp_path):
    data,p,_=standard_month(2026,11)
    data=automatic_weekly(data);selected=selected_events(data)
    with V2Store(tmp_path/'db.sqlite3',create=True) as store:
        store.save_workspace(data,p,(),selected,expected_revision=0)
        dec,p2,_=standard_month(2026,12)
        dec=automatic_weekly(dec,snapshots=store.month_snapshots())
        chosen=selected_events(dec)
        shared=[q for q in dec.quotas if q.dates.start==date(2026,11,30)]
        assert len(shared)==2
        ids={e.id for e in selected if date(2026,11,30)<=e.attendance.start_day<date(2026,12,7) and e.service.code in {'BK','WL'}}
        assert ids<={e.id for e in chosen}
        assert not ids&dec.optional_ids
        store.save_workspace(dec,p2,(),chosen,expected_revision=store.input_revision)
        assert not store.confirmations()


def test_conflicting_fixed_weekly_dates_fail_and_no_manual_override_of_quotas():
    data,_,_=standard_month(2026,12);data=automatic_weekly(data)
    fixed={e.id for e in data.events if e.attendance.start_day==date(2026,12,8) and e.service.code in {'BK','WL'}}
    bad=replace(data,optional_ids=data.optional_ids-fixed)
    with pytest.raises(DomainError):selected_events(bad)


def test_later_month_cannot_silently_move_an_earlier_shared_week(tmp_path):
    nov,p,_=standard_month(2026,11);nov=automatic_weekly(nov);chosen=selected_events(nov)
    with V2Store(tmp_path/'db.sqlite3',create=True) as store:
        store.save_workspace(nov,p,(),chosen,expected_revision=0)
        dec,p2,_=standard_month(2026,12);dec=automatic_weekly(dec)
        moved=selected_events(dec,preferred=tuple(reversed(dec.events)))
        # Construct an alternative allowed day in the already reserved crossing week.
        old=next(e for e in chosen if e.service.code=='BK' and date(2026,11,30)<=e.attendance.start_day<date(2026,12,7))
        alternative=next(e for e in dec.events if e.service.code=='BK' and date(2026,11,30)<=e.attendance.start_day<date(2026,12,7) and e.id!=old.id)
        moved=tuple(alternative if e.id==old.id else e for e in moved)
        with pytest.raises(DomainError,match='Randwoche'):store.save_workspace(dec,p2,(),moved,expected_revision=store.input_revision)
        assert store.load_workspace(2026,12) is None


def test_duplicate_leave_preserves_existing_identity_and_is_idempotent(tmp_path):
    from dienstplan.v2.entries import Entry
    from dienstplan.v2.time import Interval
    data,p,_=demonstration_month()
    entry=Entry('original-entry','P01','urlaub',Interval.local('2026-11-23T00:00','2026-11-24T00:00'))
    data=replace(data,absences=(entry,))
    proposal=prepare_plan_import(data,[row(day='2026-11-23',kind='urlaub',code='')])
    assert proposal.ready and proposal.inputs.absences==(entry,)
    with V2Store(tmp_path/'db.sqlite3',create=True) as store:
        store.apply_sheet_import(proposal,p,expected_revision=0)
        store.apply_sheet_import(proposal,p,expected_revision=store.input_revision)
        assert store.entries()==(entry,)


def test_shared_week_work_is_not_counted_twice_between_boundary_and_assignments():
    from dienstplan.v2.reporting import hours_rows
    data,p,_=demonstration_month(2026,12)
    block=automatic_pause_choices(event('BK',date(2026,11,30)),'P01')[0]
    rows=hours_rows(data.people,(block,block),(),2026,12,accounts=p.accounts,target_profile='S0',month_profile='M0')
    assert next(r.work for r in rows if r.person_id=='P01')==240


def test_fixed_month_assignment_is_a_real_solver_lock():
    data,p,_=demonstration_month()
    # Small genuine CP-SAT problem, explicitly synthetic; remaining month omitted.
    term=event('W17',date(2026,11,10));data=replace(data,events=(term,),candidates=())
    proposal=prepare_plan_import(data,[row()]);assert proposal.ready
    result=solve_feasibility(proposal.inputs,time_limit=3,existing=proposal.blocks,existing_events=proposal.events)
    assert any(b.person_id=='P01' for b in result.blocks) and not result.open_slots


def test_cross_month_weekend_wish_keeps_budget_owner_and_is_reimportable(tmp_path):
    from dienstplan.v2.entries import Entry
    from dienstplan.v2.time import Interval
    data,p,_=demonstration_month()
    entry=Entry('cross-weekend','P01','wochenendwunsch',Interval.local('2026-10-31T00:00','2026-11-02T00:00'),budget_month='2026-11')
    data=replace(data,absences=(entry,));path=tmp_path/'weekend.xlsx'
    export_month_grid(path,data,p,(),data.events)
    rows,_,_=read_import(path)
    assert rows[0]['budgetmonat']=='2026-11'
    proposal=prepare_plan_import(data,rows,budgets={('P01','2026-11'):WishBudget(2,1)})
    assert proposal.ready,proposal.errors
    assert proposal.inputs.absences==(entry,)


def test_same_day_wl_and_bk_are_rejected_even_without_week_configuration():
    data,_,_=demonstration_month()
    result=prepare_plan_import(data,[row(kind='termin',code='BK',pid=''),row(kind='termin',code='WL',pid='')])
    assert not result.ready and any('Startdatum' in error for error in result.errors)


def test_failed_excel_export_publishes_no_partial_target(tmp_path,monkeypatch):
    def fail(book,path):
        Path(path).write_bytes(b'partial')
        raise OSError('Medium voll')
    monkeypatch.setattr(Workbook,'save',fail)
    data,p,old=technical_demo()
    with pytest.raises(OSError,match='Medium voll'):export_month_grid(tmp_path/'fail.xlsx',data,p,old,data.events)
    assert not list(tmp_path.iterdir())


def test_duplicate_absence_from_another_workspace_keeps_global_id(tmp_path):
    from dienstplan.v2.entries import Entry
    from dienstplan.v2.time import Interval
    data,p,_=demonstration_month()
    entry=Entry('global-existing','P01','urlaub',Interval.local('2026-11-23T00:00','2026-11-24T00:00'))
    with V2Store(tmp_path/'db.sqlite3',create=True) as store:
        first=prepare_plan_import(replace(data,absences=(entry,)),[])
        store.apply_sheet_import(first,p,expected_revision=0)
        # A previously saved workspace need not already contain all global entries.
        second=prepare_plan_import(data,[row(day='2026-11-23',kind='urlaub',code='')])
        applied=store.apply_sheet_import(second,p,expected_revision=store.input_revision)
        assert applied.inputs.absences==(entry,) and store.entries()==(entry,)


@pytest.mark.parametrize('delimiter',[';',','])
def test_csv_import_supports_bom_and_quoted_comments(tmp_path,delimiter):
    import csv
    path=tmp_path/'import.csv'
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=COLUMNS,delimiter=delimiter)
        writer.writeheader();writer.writerow(row(kommentar='Termin; mit, Komma'))
    rows,_,_=read_import(path)
    assert rows[0]['person_id']=='P01' and rows[0]['kommentar']=='Termin; mit, Komma'


def test_empty_and_structurally_invalid_csv_have_readable_errors(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('')
    with pytest.raises(DomainError,match='leer'):read_import(p)
    p.write_text(';'.join(COLUMNS)+'\nx;y\n')
    with pytest.raises(DomainError,match='Spaltenzahl'):read_import(p)


def test_existing_neighbour_without_week_profile_supplies_real_rest_boundaries():
    nov,p,_=demonstration_month(2026,11)
    night=automatic_pause_choices(event('W17',date(2026,11,30)),'P01')[0]
    bk=event('BK',date(2026,11,30));fixed=tuple(automatic_pause_choices(bk,pid)[0] for pid in ('P02','P03'))
    nov=replace(nov,events=nov.events+(bk,),candidates=nov.candidates+fixed)
    dec,_,_=demonstration_month(2026,12)
    dec=automatic_weekly(dec,snapshots=((nov,p,(night,)+fixed,nov.events),))
    assert night in dec.boundary and set(fixed)<=set(dec.locked)
    assert bk.id not in dec.optional_ids
    # KC10 at 10:15 after W17 until 01:00 has only 9:15 actual rest.
    early=event('KC10',date(2026,12,1)).assign('P01')
    chosen=selected_events(dec)
    assert any(i.rule=='rest' for i in verify(dec,fixed+(early,),active_events=chosen)[0].issues)
