"""Explizite Schema-3-Dateien und Kopienmigration; kein Legacy-Auto-Upgrade."""
from contextlib import contextmanager, closing
from dataclasses import dataclass, asdict
from datetime import date, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .contracts import DateRange
from .entries import Entry, CorrectionBatch, DraftRow, _check_rows
from .errors import DomainError
from .profiles import Profile, Source
from .time import Interval

SCHEMA_VERSION=3
DDL=(
    'CREATE TABLE v2_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
    'CREATE TABLE v2_profiles (id TEXT PRIMARY KEY, payload TEXT NOT NULL)',
    'CREATE TABLE v2_entries (id TEXT PRIMARY KEY, identity TEXT NOT NULL UNIQUE, payload TEXT NOT NULL)',
    'CREATE TABLE v2_corrections (id TEXT PRIMARY KEY, payload TEXT NOT NULL)',
    'CREATE TABLE v2_revisions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)',
)


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)


def _legacy_snapshot(connection):
    tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'months' not in tables:
        raise DomainError("Kein unterstützter Legacy-Monatsbestand.")
    return dict(months=list(connection.execute('SELECT month_key,payload FROM months ORDER BY month_key')),
                blockers=list(connection.execute('SELECT * FROM blockers ORDER BY id')) if 'blockers' in tables else [])


class LegacyReader:
    def __init__(self,path):
        self.connection=_readonly(path)
        version=self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (1,2,3):
            self.close();raise DomainError("Unbekannte Legacy-Datenversion.")

    def snapshots(self):
        """Gibt rohe Kopien zurück; keine naive Zeit als belegte UTC-Zeit umdeuten."""
        return _legacy_snapshot(self.connection)

    def close(self):self.connection.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def _schema(connection):
    for sql in DDL:connection.execute(sql)
    connection.execute("INSERT INTO v2_meta VALUES('input_revision','0')")


def migrate_copy(source, target, *, fault=None):
    """Quelle nur lesen; geprüftes Ziel erst nach Commit atomar bereitstellen."""
    source,target=Path(source).resolve(),Path(target).resolve()
    if source==target:
        raise DomainError("Migration benötigt eine getrennte Zieldatei, niemals das Original.")
    with closing(_readonly(source)) as original:
        version=original.execute('PRAGMA user_version').fetchone()[0]
        if version not in (1,2):raise DomainError("Kopienmigration unterstützt nur Legacy-Schema 1/2.")
        snapshot=_legacy_snapshot(original)
        fingerprint=sha256(encoded(snapshot).encode()).hexdigest()
        if target.exists():
            with closing(_readonly(target)) as current:
                if current.execute('PRAGMA user_version').fetchone()[0]!=3:
                    raise DomainError("Zieldatei existiert bereits und wird nicht überschrieben.")
                provenance=current.execute("SELECT value FROM v2_meta WHERE key='legacy_fingerprint'").fetchone()
                if not provenance or provenance[0]!=fingerprint or _legacy_snapshot(current)!=snapshot:
                    raise DomainError("Zieldatei gehört nicht unverändert zu dieser Legacy-Kopie.")
            return fingerprint
        target.parent.mkdir(parents=True,exist_ok=True)
        descriptor,temporary=tempfile.mkstemp(prefix='.'+target.name+'.',suffix='.migration',dir=target.parent)
        os.close(descriptor)
        copy=None
        try:
            copy=sqlite3.connect(temporary)
            original.backup(copy)
            if fault:fault('after_backup')
            copy.execute('PRAGMA foreign_keys=ON')
            copy.execute('BEGIN IMMEDIATE')
            _schema(copy)
            if fault:fault('after_ddl')
            copy.execute('INSERT INTO v2_meta VALUES(?,?)',('legacy_fingerprint',fingerprint))
            copy.execute('INSERT INTO v2_meta VALUES(?,?)',('legacy_semantics','P1 bleibt allgemeine Sperre; Sonderdienst bleibt Legacy; keine Zulagenhistorie erfunden.'))
            if _legacy_snapshot(copy)!=snapshot:raise DomainError("Legacy-Daten wurden während Migration verändert.")
            if list(copy.execute('PRAGMA foreign_key_check')) or copy.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise DomainError("Integritätsprüfung der Kopie fehlgeschlagen.")
            copy.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            if fault:fault('before_commit')
            copy.commit();copy.close();copy=None
            # Nicht os.replace: ein zwischenzeitlich angelegtes Ziel nicht überschreiben.
            os.link(temporary,target)
            return fingerprint
        finally:
            if copy is not None:copy.close()
            Path(temporary).unlink(missing_ok=True)
            Path(temporary+'-journal').unlink(missing_ok=True)


def entry_payload(entry):
    return dict(id=entry.id,person_id=entry.person_id,kind=entry.kind,start=entry.span.start.isoformat(),
                end=entry.span.end.isoformat(),credit_days=sorted(d.isoformat() for d in entry.credit_days),
                comment=entry.comment,budget_month=entry.budget_month)


def restore_entry(value):
    return Entry(value['id'],value['person_id'],value['kind'],Interval(datetime.fromisoformat(value['start']),datetime.fromisoformat(value['end'])),
                 frozenset(date.fromisoformat(d) for d in value['credit_days']),value['comment'],value.get('budget_month'))


class V2Store:
    """Öffnet ausschließlich bereits explizit vorbereitete V2-Dateien."""
    def __init__(self,path,*,create=False):
        self.path=Path(path)
        if create:
            descriptor=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(descriptor)
        elif not self.path.exists():raise DomainError("Die V2-Datendatei fehlt.")
        self.connection=sqlite3.connect(self.path,isolation_level=None)
        self.connection.execute('PRAGMA foreign_keys=ON')
        if create:
            with self.transaction():
                _schema(self.connection)
                self.connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
        elif self.connection.execute('PRAGMA user_version').fetchone()[0]!=SCHEMA_VERSION:
            self.close();raise DomainError("V2-Datei benötigt Schema 3; keine automatische Originalmigration.")

    def close(self):self.connection.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

    @contextmanager
    def transaction(self):
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback();raise

    @property
    def input_revision(self):
        return int(self.connection.execute("SELECT value FROM v2_meta WHERE key='input_revision'").fetchone()[0])

    def entries(self):
        return tuple(restore_entry(json.loads(r[0])) for r in self.connection.execute('SELECT payload FROM v2_entries ORDER BY id'))

    def save_correction(self,id,batch,*,replaces=None):
        if replaces is None:replaces=self.correction_replaces(id)
        value=dict(original_text=batch.original_text,parse_errors=batch.parse_errors,
                   rows=[dict(line=r.line,fields=r.fields) for r in batch.rows],replaces=replaces or None)
        with self.transaction():
            self.connection.execute('INSERT INTO v2_corrections VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(id,encoded(value)))

    def correction_replaces(self,id):
        row=self.connection.execute('SELECT payload FROM v2_corrections WHERE id=?',(id,)).fetchone()
        return json.loads(row[0]).get('replaces') if row else None

    def correction_existing(self,id,additional=()):
        old=self.correction_replaces(id)
        return tuple(e for e in self.entries()+tuple(additional) if e.id!=old)

    def load_correction(self,id,*,budgets,month,additional_existing=()):
        row=self.connection.execute('SELECT payload FROM v2_corrections WHERE id=?',(id,)).fetchone()
        if not row:raise DomainError("Korrekturstapel fehlt oder wurde bereits übernommen.")
        value=json.loads(row[0]);rows=tuple(DraftRow(r['line'],tuple(tuple(x) for x in r['fields'])) for r in value['rows'])
        return _check_rows(value['original_text'],rows,self.correction_existing(id,additional_existing),budgets,month,tuple(value['parse_errors']))

    def discard_correction(self,id):
        with self.transaction():self.connection.execute('DELETE FROM v2_corrections WHERE id=?',(id,))

    def promote(self,id,*,budgets,month,expected_revision):
        with self.transaction():
            if self.correction_replaces(id):raise DomainError('Eintragsersetzung benötigt den geprüften Arbeitsstand und apply_correction.')
            if expected_revision!=self.input_revision:
                raise DomainError("Eingaben wurden geändert; Stapel erneut prüfen.")
            batch=self.load_correction(id,budgets=budgets,month=month)
            for entry in batch.promote():
                self.connection.execute('INSERT INTO v2_entries VALUES(?,?,?) ON CONFLICT(id) DO NOTHING',
                                        (entry.id,encoded(entry.identity),encoded(entry_payload(entry))))
            self.connection.execute('DELETE FROM v2_corrections WHERE id=?',(id,))
            self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")

    def save_profile(self,profile):
        payload=encoded(dict(id=profile.id,kind=profile.kind,scope=profile.scope,
                             start=profile.dates.start.isoformat(),end=profile.dates.end.isoformat(),
                             parameters=profile.parameters_json,sources=[asdict(s) for s in profile.sources],
                             confirmed=profile.confirmed,synthetic=profile.synthetic))
        with self.transaction():
            if self._immutable('v2_profiles',profile.id,payload):
                self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")

    def profiles(self):
        result=[]
        for row in self.connection.execute('SELECT payload FROM v2_profiles ORDER BY id'):
            v=json.loads(row[0]);result.append(Profile(v['id'],v['kind'],v['scope'],DateRange(date.fromisoformat(v['start']),date.fromisoformat(v['end'])),
                v['parameters'],tuple(Source(**s) for s in v['sources']),v['confirmed'],v['synthetic']))
        return tuple(result)

    def _immutable(self,table,id,payload):
        if table not in {'v2_profiles','v2_revisions'}:raise DomainError("Unbekannter unveränderlicher Speicherbereich.")
        row=self.connection.execute(f'SELECT payload FROM {table} WHERE id=?',(id,)).fetchone()
        if row and row[0]!=payload:raise DomainError("Gespeicherte Version ist unveränderlich; neue Kennung erforderlich.")
        self.connection.execute(f'INSERT OR IGNORE INTO {table} VALUES(?,?)',(id,payload))
        return row is None

    def save_draft_revision(self,id,payload):
        with self.transaction():self._immutable('v2_revisions',id,encoded(payload))

    def load_workspace(self,year,month):
        from .codec import restore_workspace
        key=f'workspace:{year:04d}-{month:02d}'
        row=self.connection.execute('SELECT r.payload FROM v2_meta m JOIN v2_revisions r ON m.value=r.id WHERE m.key=?',(key,)).fetchone()
        return restore_workspace(json.loads(row[0])) if row else None

    def month_snapshots(self,year=None,month=None):
        keys=[r[0].removeprefix('workspace:') for r in self.connection.execute("SELECT key FROM v2_meta WHERE key LIKE 'workspace:%' ORDER BY key")]
        if year is not None:
            serial=year*12+month
            keys=[k for k in keys if abs(int(k[:4])*12+int(k[5:])-serial)<=1]
        return tuple(self.load_workspace(*map(int,key.split('-'))) for key in keys)

    def _save_workspace(self,inputs,profile,blocks=(),events=None,*,expected_revision):
        from .codec import workspace
        if self.input_revision!=expected_revision:raise DomainError('Eingaben/Historie geändert; Arbeitsstand erneut laden.')
        month=f'{inputs.year:04d}-{inputs.month:02d}'
        if self.connection.execute('SELECT 1 FROM v2_meta WHERE key=?',('confirmation:'+month,)).fetchone():
            raise DomainError('Bestätigter Testmonat bleibt geschützt; keine stille Bearbeitung.')
        from .automatic_weekly import check_shared_weeks
        if events is not None and inputs.week_policy is not None:
            check_shared_weeks(inputs,blocks,events,self.month_snapshots(inputs.year,inputs.month))
        value=workspace(inputs,profile,blocks,events);id='workspace/'+value['revision_id']
        previous=self.connection.execute('SELECT value FROM v2_meta WHERE key=?',('workspace:'+month,)).fetchone()
        changed=previous is None or previous[0]!=id
        self._immutable('v2_revisions',id,encoded(value))
        self.connection.execute('INSERT INTO v2_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('workspace:'+month,id))
        if changed:self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")
        return value['revision_id']

    def save_workspace(self,inputs,profile,blocks=(),events=None,*,expected_revision):
        with self.transaction():
            return self._save_workspace(inputs,profile,blocks,events,expected_revision=expected_revision)

    def save_sheet_stage(self,rows,mapping,notes=()):
        with self.transaction():
            payload=encoded(dict(rows=rows,mapping=mapping,notes=notes))
            self.connection.execute("INSERT INTO v2_meta VALUES('sheet-stage',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(payload,))

    def sheet_stage(self):
        row=self.connection.execute("SELECT value FROM v2_meta WHERE key='sheet-stage'").fetchone()
        return json.loads(row[0]) if row else None

    def apply_sheet_import(self,proposal,profile,*,expected_revision):
        if not proposal.ready:raise DomainError('Import enthält Fehler; keine Teilübernahme.')
        from dataclasses import replace
        with self.transaction():
            canonical=[]
            for entry in proposal.inputs.absences:
                old=self.connection.execute('SELECT payload FROM v2_entries WHERE identity=?',(encoded(entry.identity),)).fetchone()
                if old is not None:
                    previous=restore_entry(json.loads(old[0]))
                    if previous.credit_days!=entry.credit_days:raise DomainError('Identischer Zeitraum hat andere Gutschrifttage; Änderung ausdrücklich korrigieren.')
                    entry=previous
                canonical.append(entry)
            proposal=replace(proposal,inputs=replace(proposal.inputs,absences=tuple(canonical)))
            self._save_workspace(proposal.inputs,profile,proposal.blocks,proposal.events,expected_revision=expected_revision)
            for entry in proposal.inputs.absences:
                old=self.connection.execute('SELECT payload FROM v2_entries WHERE id=?',(entry.id,)).fetchone()
                payload=encoded(entry_payload(entry))
                if old is not None and old[0]!=payload:raise DomainError('Vorhandene Abwesenheitskennung hat anderen Inhalt.')
                self.connection.execute('INSERT INTO v2_entries VALUES(?,?,?) ON CONFLICT(id) DO NOTHING',(entry.id,encoded(entry.identity),payload))
            self.connection.execute("DELETE FROM v2_meta WHERE key='sheet-stage'")
            return proposal

    def apply_correction(self,id,inputs,profile,*,budgets,expected_revision):
        """Stapel, aktive Eingaben und verworfener Altentwurf atomar aktualisieren."""
        from dataclasses import replace
        from .codec import workspace
        month=f'{inputs.year:04d}-{inputs.month:02d}'
        with self.transaction():
            if self.input_revision!=expected_revision:raise DomainError('Eingaben/Historie geändert; Korrekturen erneut prüfen.')
            if self.connection.execute('SELECT 1 FROM v2_meta WHERE key=?',('confirmation:'+month,)).fetchone():raise DomainError('Bestätigter Testmonat bleibt geschützt.')
            batch=self.load_correction(id,budgets=budgets,month=month,additional_existing=inputs.absences)
            entries=batch.promote()
            replaces=self.correction_replaces(id)
            if replaces:
                old=next((e for e in inputs.absences if e.id==replaces),None)
                if old is None or len(entries)!=1 or entries[0].person_id!=old.person_id:
                    raise DomainError('Ersetzter Eintrag fehlt oder Person wurde geändert; Korrektur erneut vormerken.')
                self.connection.execute('DELETE FROM v2_entries WHERE id=?',(replaces,))
            for entry in entries:
                self.connection.execute('INSERT INTO v2_entries VALUES(?,?,?) ON CONFLICT(id) DO NOTHING',(entry.id,encoded(entry.identity),encoded(entry_payload(entry))))
            merged={e.identity:e for e in tuple(e for e in inputs.absences if e.id!=replaces)+entries}
            updated=replace(inputs,absences=tuple(merged.values()))
            value=workspace(updated,profile);revision_id='workspace/'+value['revision_id']
            self._immutable('v2_revisions',revision_id,encoded(value))
            self.connection.execute('INSERT INTO v2_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('workspace:'+month,revision_id))
            self.connection.execute('DELETE FROM v2_corrections WHERE id=?',(id,))
            self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")
            return updated

    def delete_entry(self,id,inputs,profile,*,expected_revision):
        from dataclasses import replace
        from .codec import workspace
        month=f'{inputs.year:04d}-{inputs.month:02d}'
        with self.transaction():
            if self.input_revision!=expected_revision:raise DomainError('Eingaben geändert; aktiven Eintrag erneut laden.')
            if self.connection.execute('SELECT 1 FROM v2_meta WHERE key=?',('confirmation:'+month,)).fetchone():raise DomainError('Bestätigter Testmonat bleibt geschützt.')
            if not any(e.id==id for e in inputs.absences):raise DomainError('Aktiver Eintrag fehlt.')
            updated=replace(inputs,absences=tuple(e for e in inputs.absences if e.id!=id))
            value=workspace(updated,profile);revision='workspace/'+value['revision_id']
            self.connection.execute('DELETE FROM v2_entries WHERE id=?',(id,))
            self._immutable('v2_revisions',revision,encoded(value))
            self.connection.execute('INSERT INTO v2_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('workspace:'+month,revision))
            self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")
            return updated

    def confirmations(self):
        from .history import checked_payload
        result=[]
        for key,id in self.connection.execute("SELECT key,value FROM v2_meta WHERE key LIKE 'confirmation:%' ORDER BY key"):
            row=self.connection.execute('SELECT payload FROM v2_revisions WHERE id=?',(id,)).fetchone()
            if row is None:raise DomainError('Bestätigte Revision fehlt.')
            value=checked_payload(row[0])
            if value['month']!=key.removeprefix('confirmation:'):raise DomainError('Bestätigungsmonat ist widersprüchlich.')
            result.append((id,value))
        return tuple(result)

    def wish_history(self,month,*,policy):
        from .history import wish_history
        legacy=self.connection.execute("SELECT value FROM v2_meta WHERE key='legacy_fingerprint'").fetchone()
        return wish_history(self.confirmations(),month,policy=policy,
                            legacy_missing=('Legacy-Wunsch-/Zulagenhistorie nicht belegt; keine Umdeutung.',) if legacy else ())

    def confirm(self,id,inputs,blocks,events,*,accounts,wish_policy,fairness_policy,holidays=frozenset(),
                target_profile,month_profile,expected_revision,synthetic=False):
        from .history import confirmation,request_key
        month=f'{inputs.year:04d}-{inputs.month:02d}';key='confirmation:'+month
        blocks,events,accounts=tuple(blocks),tuple(events),tuple(accounts)
        request=request_key(inputs,blocks,events,accounts,wish_policy,fairness_policy,holidays,target_profile,month_profile)
        with self.transaction():
            current=dict((v['month'],(rid,v)) for rid,v in self.confirmations())
            if month in current:
                rid,value=current[month]
                if rid==id and value['request_fingerprint']==request:return value
                raise DomainError('Der Monat ist bereits unveränderlich bestätigt; keine stille Ersetzung.')
            if expected_revision!=self.input_revision:raise DomainError('Eingaben/Historie geändert; vor Bestätigung erneut prüfen.')
            value=confirmation(inputs,blocks,events,accounts=accounts,wish_policy=wish_policy,fairness_policy=fairness_policy,
                               holidays=holidays,history=self.wish_history(month,policy=wish_policy),target_profile=target_profile,
                               month_profile=month_profile,synthetic=synthetic)
            for _,old in self.confirmations():
                for quota,choices in value['quota_reservations'].items():
                    prior=old.get('quota_reservations',{}).get(quota)
                    if prior is not None and prior!=choices:raise DomainError(f'Bestätigte Randwochenbindung {quota} widerspricht der neuen Terminwahl.')
            self._immutable('v2_revisions',id,encoded(value))
            self.connection.execute('INSERT INTO v2_meta VALUES(?,?)',(key,id))
            self.connection.execute("UPDATE v2_meta SET value=CAST(value AS INTEGER)+1 WHERE key='input_revision'")
            return value
