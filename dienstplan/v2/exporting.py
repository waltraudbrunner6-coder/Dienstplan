"""Ein atomar veröffentlichtes ZIP mit konsistenten Tabellen und Prüfmanifest."""
from dataclasses import asdict
from hashlib import sha256
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

from .codec import workspace
from .objectives import evaluate
from .reporting import hours_rows,quantity_rows,shares
from .serialization import fingerprint,plain
from .solver import verify
from .time import vienna
from .presentation import hours_text
from .wishes import wish_rows


def _csv(header,rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter=';');writer.writerow(header);writer.writerows(rows)
    return ('\ufeff'+stream.getvalue()).encode('utf-8')


def export_package(target,inputs,profile,blocks,events,*,proofs=(),holidays=None,fault=None):
    target=Path(target);blocks=tuple(blocks);events=tuple(events)
    holidays=None if holidays is None else frozenset(holidays)
    saved=workspace(inputs,profile,blocks,events)
    if holidays is not None:
        saved['snapshot']['holiday_calendar']=sorted(d.isoformat() for d in holidays)
        saved['revision_id']=fingerprint(saved['snapshot'])
    revision=saved['revision_id']
    core,calendar=verify(inputs,blocks,active_events=events)
    terms={e.id:e for e in events};plan=[]
    for e in events:
        assigned=sorted((b for b in blocks if b.id==e.id),key=lambda b:b.person_id)
        slots=max(e.service.staff or 0,len(assigned))
        for i in range(slots):
            b=assigned[i] if i<len(assigned) else None
            plan.append((revision,e.attendance.start.astimezone(vienna()).isoformat(),e.attendance.end.astimezone(vienna()).isoformat(),e.service.code,
                         i+1,b.person_id if b else '',hours_text(b.work_minutes) if b else '', 'zugeteilt' if b else 'OFFEN',e.replacement_reason))
    files={'dienstplan.csv':_csv(('revision_id','beginn','ende','dienst','platz','person_id','arbeitsstunden','status','w16_grund'),plan)}
    report_rows={
        'stunden.csv':hours_rows(inputs.people,tuple({(b.id,b.person_id):b for b in inputs.boundary+blocks}.values()),inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,target_profile=profile.target_profile,month_profile=profile.month_profile),
        'verteilung.csv':shares(inputs.people,events,blocks,policy=profile.fairness_policy,absences=inputs.absences),
        'wuensche.csv':wish_rows(inputs.people,inputs.absences,events,blocks+inputs.boundary,policy=profile.wish_policy,history=profile.history),
        'zeitmengen.csv':quantity_rows(blocks,frozenset() if holidays is None else frozenset(holidays)),
    }
    for name,rows in report_rows.items():
        rows=tuple(rows)
        header=tuple(asdict(rows[0])) if rows else ('person_id',)
        time_keys = ({'target','opening','desired','credits','goal','work','projected','deviation','raw_target','raw_credits'} if name=='stunden.csv'
                     else {'work_minutes','expected_minutes'} if name=='verteilung.csv'
                     else {'work_minutes','night_minutes','sunday_minutes','holiday_minutes'} if name=='zeitmengen.csv' else set())
        def column(key):
            return (key.removesuffix('_minutes')+'_hours') if key in time_keys else key
        def field(row,key):
            if name=='stunden.csv' and not row.credits_known and key in {'credits','goal','projected','deviation','raw_credits'}:return None
            if name=='zeitmengen.csv' and holidays is None and key=='holiday_minutes':return None
            return getattr(row,key)
        def cell(row,key):
            value=field(row,key)
            return hours_text(value) if key in time_keys and value is not None else json.dumps(plain(value),ensure_ascii=False)
        files[name]=_csv(('revision_id',)+tuple(map(column,header)),[(revision,)+tuple(cell(r,key) for key in header) for r in rows])
    invalid=not core.hard_ok or not calendar.hard_ok
    unknown_credits=any(not r.credits_known for r in report_rows['stunden.csv'])
    manifest=dict(manual_override=inputs.manual_override,override_notes=list(inputs.override_notes),revision_id=revision,scope=inputs.profile_label,input_fingerprint=inputs.fingerprint,
                  versions=saved['snapshot']['versions'],objective_profile=plain(profile),objectives=[] if unknown_credits or invalid else plain(evaluate(inputs,blocks,events,profile)),
                  objective_status='Regelabweichung; keine Optimierungsbewertung' if invalid else 'Urlaubsgutschrifttage ungeklärt' if unknown_credits else 'bewertet',
                  proofs=[] if unknown_credits or invalid else plain(proofs),issues=plain(core.issues+calendar.issues),open_slots=plain(core.open_slots),
                  unchecked=list(dict.fromkeys(inputs.unchecked+calendar.unchecked+profile.history.missing)),
                  euro_status='ungeklärt – kein freigegebener KV-/BV-Tarif',
                  csv_format_version=2,csv_time_unit='Stunden, Dezimalkomma, zwei Nachkommastellen; Arbeitsstand-JSON weiterhin exakte Minuten',
                  holiday_calendar='ungeklärt' if holidays is None else sorted(d.isoformat() for d in holidays),
                  files={name:sha256(content).hexdigest() for name,content in files.items()})
    if unknown_credits:manifest['unchecked'].append('Urlaubsgutschrifttage ungeklärt; keine angenommene Nullgutschrift.')
    if holidays is None:manifest['unchecked'].append('Feiertagsmenge nicht übergeben; keine angenommene Nullmenge.')
    files['arbeitsstand.json']=(json.dumps(saved,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    manifest['files']['arbeitsstand.json']=sha256(files['arbeitsstand.json']).hexdigest()
    files['pruefmanifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    descriptor,temporary=tempfile.mkstemp(prefix='.dienstplan-export-',suffix='.zip',dir=target.parent);os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,content in sorted(files.items()):
                archive.writestr(name,content)
                if fault:fault(name)
        # Windows _commit/fsync benötigt einen schreibbar geöffneten Handle.
        with open(temporary,'r+b') as stream:os.fsync(stream.fileno())
        os.link(temporary,target)  # atomar, fremdes Ziel niemals überschreiben
    finally:Path(temporary).unlink(missing_ok=True)
    return manifest
