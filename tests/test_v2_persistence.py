from dataclasses import replace
from datetime import date
from hashlib import sha256
import json
import sqlite3

import pytest

from dienstplan.fixtures import night_transfer_case
from dienstplan.storage import _encode
from dienstplan.v2.contracts import DateRange
from dienstplan.v2.entries import WishBudget, preview, correct
from dienstplan.v2.errors import DomainError
from dienstplan.v2.persistence import LegacyReader, V2Store, migrate_copy
from dienstplan.v2.profiles import Profile, Profiles

CSV='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n'
GOOD='2;A;first;freiwunschtag;2026-11-09T00:00;2026-11-10T00:00;;Frei\n'
BAD='2;A;thu;freiwunschtag;2026-11-12T00:00;2026-11-13T00:00;;Korrigieren\n'
BUDGET={('A','2026-11'):WishBudget(2)}


def legacy(path,version=2,wal=False):
    data=night_transfer_case();data.confirmed=True
    raw=json.loads(_encode(data))
    if version==1:
        raw.pop('exceptions');raw.pop('wish_snapshot')
    payload=json.dumps(raw,ensure_ascii=False,indent=2)
    c=sqlite3.connect(path)
    if wal:c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE months(month_key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    c.execute('CREATE TABLE blockers(id TEXT PRIMARY KEY,employee_id TEXT,start TEXT,end TEXT,priority INTEGER,comment TEXT)')
    c.execute('INSERT INTO months VALUES(?,?)',('2026-11',payload))
    c.execute('INSERT INTO blockers VALUES(?,?,?,?,?,?)',('old','person-01','2026-11-02T00:00','2026-11-03T00:00',1,'Keine belegte Urlaubsgutschrift'))
    c.execute(f'PRAGMA user_version={version}');c.commit()
    if wal:return payload,c
    c.close();return payload,None


@pytest.mark.parametrize('version',[1,2])
def test_migration_preserves_raw_legacy_and_original_hash(tmp_path,version):
    source,target=tmp_path/'old.sqlite',tmp_path/'v2.sqlite'
    payload,_=legacy(source,version)
    before=sha256(source.read_bytes()).hexdigest()
    fingerprint=migrate_copy(source,target)
    assert sha256(source.read_bytes()).hexdigest()==before
    with LegacyReader(target) as reader:
        snapshot=reader.snapshots()
        assert snapshot['months']==[('2026-11',payload)]
        assert snapshot['blockers'][0][4:]==(1,'Keine belegte Urlaubsgutschrift')
        assert reader.connection.execute('PRAGMA user_version').fetchone()[0]==3
    with V2Store(target) as store:
        assert store.entries()==() and store.profiles()==()
        assert not list(store.connection.execute('PRAGMA foreign_key_check'))
        assert store.connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    target_hash=sha256(target.read_bytes()).hexdigest()
    assert migrate_copy(source,target)==fingerprint
    assert sha256(target.read_bytes()).hexdigest()==target_hash
    with pytest.raises(DomainError):V2Store(source)
    assert sha256(source.read_bytes()).hexdigest()==before


@pytest.mark.parametrize('point',['after_backup','after_ddl','before_commit'])
def test_migration_fault_rollback_and_cleanup(tmp_path,point):
    source,target=tmp_path/'old.sqlite',tmp_path/'v2.sqlite';legacy(source)
    before=source.read_bytes()
    def fail(stage):
        if stage==point:raise KeyboardInterrupt('Gezielter Abbruch')
    with pytest.raises(KeyboardInterrupt):migrate_copy(source,target,fault=fail)
    assert not target.exists() and source.read_bytes()==before
    assert not list(tmp_path.glob('*.migration')) and not list(tmp_path.glob('.*.migration'))
    migrate_copy(source,target)
    with V2Store(target) as store:assert store.entries()==()


def test_backup_includes_committed_wal_and_reader_cannot_write(tmp_path):
    source,target=tmp_path/'old.sqlite',tmp_path/'v2.sqlite'
    payload,writer=legacy(source,wal=True)
    try:
        assert (tmp_path/'old.sqlite-wal').exists()
        migrate_copy(source,target)
        with LegacyReader(target) as reader:
            assert reader.snapshots()['months'][0][1]==payload
            with pytest.raises(sqlite3.OperationalError):reader.connection.execute('DELETE FROM months')
    finally:writer.close()


def test_no_original_or_unrelated_target_overwrite(tmp_path):
    source,target=tmp_path/'old.sqlite',tmp_path/'target.sqlite';legacy(source)
    target.write_text('Nicht überschreiben')
    with pytest.raises(DomainError):migrate_copy(source,source)
    with pytest.raises(sqlite3.DatabaseError):migrate_copy(source,target)
    assert target.read_text()=='Nicht überschreiben'


def test_correction_survives_restart_then_atomic_promotion(tmp_path):
    path=tmp_path/'v2.sqlite'
    initial=preview(CSV+GOOD+BAD,budgets=BUDGET,month='2026-11')
    with V2Store(path,create=True) as store:
        store.save_correction('batch',initial)
        with pytest.raises(DomainError):store.promote('batch',budgets=BUDGET,month='2026-11',expected_revision=0)
        assert store.entries()==() and store.input_revision==0
    with V2Store(path) as store:
        loaded=store.load_correction('batch',budgets=BUDGET,month='2026-11')
        assert loaded.original_text==CSV+GOOD+BAD and not loaded.ready
        fixed=correct(loaded,3,{'von':'2026-11-11T00:00','bis':'2026-11-12T00:00'},budgets=BUDGET,month='2026-11')
        store.save_correction('batch',fixed)
        store.promote('batch',budgets=BUDGET,month='2026-11',expected_revision=0)
        assert len(store.entries())==2 and store.input_revision==1
        with pytest.raises(DomainError):store.load_correction('batch',budgets=BUDGET,month='2026-11')
    with V2Store(path) as store:assert len(store.entries())==2


def test_promotion_rechecks_revision_and_budget_and_rolls_back_sql_failure(tmp_path):
    with V2Store(tmp_path/'v2.sqlite',create=True) as store:
        batch=preview(CSV+GOOD+BAD.replace('2026-11-12T00:00','2026-11-11T00:00').replace('2026-11-13T00:00','2026-11-12T00:00'),budgets=BUDGET,month='2026-11')
        store.save_correction('batch',batch)
        with pytest.raises(DomainError):store.promote('batch',budgets=BUDGET,month='2026-11',expected_revision=1)
        with pytest.raises(DomainError):store.promote('batch',budgets={('A','2026-11'):WishBudget(1)},month='2026-11',expected_revision=0)
        store.connection.execute("CREATE TRIGGER fail_second BEFORE INSERT ON v2_entries WHEN NEW.id='thu' BEGIN SELECT RAISE(ABORT,'Fehlerinjektion'); END")
        with pytest.raises(sqlite3.IntegrityError):store.promote('batch',budgets=BUDGET,month='2026-11',expected_revision=0)
        assert store.entries()==() and store.input_revision==0
        assert store.load_correction('batch',budgets=BUDGET,month='2026-11').ready
        store.discard_correction('batch')
        assert store.entries()==()


def test_versioned_profiles_are_explicit_immutable_and_not_productive_by_default(tmp_path):
    a=Profile('a','night','test',DateRange(date(2026,1,1),date(2027,1,1)),'{"eur_per_hour":"2"}',synthetic=True)
    b=replace(a,id='b',dates=DateRange(date(2027,1,1),date(2028,1,1)),parameters_json='{"eur_per_hour":"3"}')
    profiles=Profiles((a,b))
    with pytest.raises(DomainError):profiles.select('night','test',date(2026,12,31))
    assert profiles.select('night','test',date(2026,12,31),allow_synthetic=True).id=='a'
    assert profiles.select('night','test',date(2027,1,1),allow_synthetic=True).id=='b'
    with pytest.raises(DomainError):profiles.select('night','test',date(2028,1,1),allow_synthetic=True)
    with pytest.raises(DomainError):Profiles((a,replace(a,id='overlap')))
    with pytest.raises(DomainError):replace(a,synthetic=False,confirmed=True)
    with pytest.raises(DomainError):replace(a,parameters_json='{"rate":2.2}')
    with V2Store(tmp_path/'profiles.sqlite',create=True) as store:
        store.save_profile(a);store.save_profile(a);assert store.input_revision==1
        with pytest.raises(DomainError):store.save_profile(replace(a,parameters_json='{"rate":"99"}'))
    with V2Store(tmp_path/'profiles.sqlite') as store:assert store.profiles()==(a,)


def test_draft_revisions_cannot_be_overwritten(tmp_path):
    with V2Store(tmp_path/'v2.sqlite',create=True) as store:
        store.save_draft_revision('r1',{'status':'ungeprüfter Entwurf'})
        store.save_draft_revision('r1',{'status':'ungeprüfter Entwurf'})
        with pytest.raises(DomainError):store.save_draft_revision('r1',{'status':'andere Eingabe'})
