from dataclasses import replace
from datetime import date
from fractions import Fraction
from hashlib import sha256
import json
import zipfile

import pytest

from dienstplan.v2.codec import restore_workspace,workspace
from dienstplan.v2.contracts import Contract,Contracts,DateRange
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.errors import DomainError
from dienstplan.v2.exporting import export_package
from dienstplan.v2.persistence import V2Store


def test_full_typed_workspace_roundtrip_preserves_contracts_and_datetimes():
    data,profile,old=technical_demo();a=data.people[0]
    versions=(Contract(a.id,DateRange(date(2026,1,1),date(2026,11,16)),'25.04'),
              Contract(a.id,DateRange(date(2026,11,16),date(2028,1,1)),'30.125'))
    data=replace(data,people=(replace(a,contracts=Contracts(a.id,versions)),)+data.people[1:],locked=(old[0],))
    saved=workspace(data,profile,old,data.events)
    restored=restore_workspace(json.loads(json.dumps(saved)))
    assert restored==(data,profile,old,data.events)
    assert restored[0].people[0].contracts.at(date(2026,11,16)).weekly_hours==Fraction(241,8)


def test_workspace_revisions_survive_restart_and_reject_stale_updates(tmp_path):
    path=tmp_path/'test.sqlite3';data,p,old=technical_demo()
    with V2Store(path,create=True) as store:
        first=store.save_workspace(data,p,old,data.events,expected_revision=0)
        revision=store.input_revision
        assert first==store.save_workspace(data,p,old,data.events,expected_revision=revision) and revision==store.input_revision
        changed=replace(data,profile_label='Andere technische Eingaben')
        store.save_workspace(changed,p,expected_revision=revision)
        with pytest.raises(DomainError,match='geändert'):store.save_workspace(data,p,expected_revision=revision)
        # Zurück zu einem schon gespeicherten Snapshot ist ebenfalls eine Änderung.
        before=store.input_revision
        store.save_workspace(data,p,old,data.events,expected_revision=before)
        assert store.input_revision==before+1
    with V2Store(path) as store:assert store.load_workspace(2026,11)==(data,p,old,data.events)


def test_corruption_version_changes_and_invalid_manual_plan_rejected():
    data,p,old=technical_demo();saved=workspace(data,p,old,data.events)
    saved['snapshot']['inputs']['people'][0]['name']='Manipuliert'
    with pytest.raises(DomainError,match='beschädigt'):restore_workspace(saved)
    saved=workspace(data,p,old,data.events)
    with pytest.raises(DomainError,match='doppelt|Mehr Personen|Mehr als ein|überschneid|Ruhe|Doppel|gleichzeitig'):
        workspace(data,p,old+(old[0],),data.events)


def test_export_atomic_csvs_share_revision_and_manifest_hashes(tmp_path):
    data,p,old=technical_demo();target=tmp_path/'export.zip'
    manifest=export_package(target,data,p,old,data.events)
    with zipfile.ZipFile(target) as archive:
        saved_manifest=json.loads(archive.read('pruefmanifest.json'))
        assert saved_manifest==manifest and saved_manifest['euro_status'].startswith('ungeklärt')
        for name,digest in manifest['files'].items():
            assert sha256(archive.read(name)).hexdigest()==digest
            if name.endswith('.csv'):
                lines=archive.read(name).decode('utf-8-sig').splitlines()
                assert all(line.startswith(manifest['revision_id']+';') for line in lines[1:])
        restored=restore_workspace(json.loads(archive.read('arbeitsstand.json')))
        assert restored==(data,p,old,data.events)
    before=target.read_bytes()
    with pytest.raises(FileExistsError):export_package(target,data,p,old,data.events)
    assert target.read_bytes()==before


def test_export_mid_write_failure_publishes_nothing_and_cleans_temporary_files(tmp_path):
    data,p,old=technical_demo()
    def fail(name):raise OSError('Test: Medium voll')
    with pytest.raises(OSError,match='Medium voll'):export_package(tmp_path/'export.zip',data,p,old,data.events,fault=fail)
    assert list(tmp_path.iterdir())==[]


def test_invalid_credit_cannot_be_promoted_even_when_csv_structure_is_valid(tmp_path):
    from dienstplan.v2.entries import preview
    data,p,old=technical_demo()
    text='format_version;person_id;entry_id;typ;von;bis;gutschrifttage;kommentar\n2;A;vac;urlaub;2025-11-10T00:00;2025-11-11T00:00;2025-11-10;vor Beschäftigung\n'
    batch=preview(text,existing=(),budgets={},month='2026-11')
    assert batch.ready
    with V2Store(tmp_path/'test.sqlite3',create=True) as store:
        store.save_correction('invalid-credit',batch)
        with pytest.raises(DomainError,match='Beschäftigung'):
            store.apply_correction('invalid-credit',data,p,budgets={},expected_revision=0)
        assert store.input_revision==0 and not store.entries()
        assert store.load_correction('invalid-credit',budgets={},month='2026-11').ready


def test_atomic_export_flush_uses_writable_descriptor_on_all_platforms(tmp_path,monkeypatch):
    import os
    original=os.fsync;checked=[]
    def fsync(fd):
        # Auch auf Linux die Windows-Voraussetzung erzwingen: dieser Handle
        # muss schreibbar sein. Der Nullbyte-Schreibaufruf verändert die ZIP nicht.
        assert os.write(fd,b'')==0;checked.append(True);original(fd)
    monkeypatch.setattr(os,'fsync',fsync)
    data,p,old=technical_demo();export_package(tmp_path/'export.zip',data,p,old,data.events)
    assert checked==[True]
