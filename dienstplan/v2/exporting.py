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
from .serialization import plain
from .solver import verify
from .time import vienna
from .wishes import wish_rows


def _csv(header,rows):
    stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter=';');writer.writerow(header);writer.writerows(rows)
    return ('\ufeff'+stream.getvalue()).encode('utf-8')


def export_package(target,inputs,profile,blocks,events,*,proofs=(),fault=None):
    target=Path(target);blocks=tuple(blocks);events=tuple(events)
    saved=workspace(inputs,profile,blocks,events);revision=saved['revision_id']
    core,calendar=verify(inputs,blocks,active_events=events)
    terms={e.id:e for e in events};plan=[]
    for e in events:
        assigned=sorted((b for b in blocks if b.id==e.id),key=lambda b:b.person_id)
        slots=max(e.service.staff or 0,len(assigned))
        for i in range(slots):
            b=assigned[i] if i<len(assigned) else None
            plan.append((revision,e.attendance.start.astimezone(vienna()).isoformat(),e.attendance.end.astimezone(vienna()).isoformat(),e.service.code,
                         i+1,b.person_id if b else '',b.work_minutes if b else '', 'zugeteilt' if b else 'OFFEN',e.replacement_reason))
    files={'dienstplan.csv':_csv(('revision_id','beginn','ende','dienst','platz','person_id','arbeitsminuten','status','w16_grund'),plan)}
    report_rows={
        'stunden.csv':hours_rows(inputs.people,tuple({(b.id,b.person_id):b for b in inputs.boundary+blocks}.values()),inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,target_profile=profile.target_profile,month_profile=profile.month_profile),
        'verteilung.csv':shares(inputs.people,events,blocks,policy=profile.fairness_policy,absences=inputs.absences),
        'wuensche.csv':wish_rows(inputs.people,inputs.absences,events,blocks+inputs.boundary,policy=profile.wish_policy,history=profile.history),
        'zeitmengen.csv':quantity_rows(blocks),
    }
    for name,rows in report_rows.items():
        rows=tuple(rows)
        header=tuple(asdict(rows[0])) if rows else ('person_id',)
        files[name]=_csv(('revision_id',)+header,[(revision,)+tuple(json.dumps(plain(getattr(r,key)),ensure_ascii=False) for key in header) for r in rows])
    manifest=dict(revision_id=revision,scope=inputs.profile_label,input_fingerprint=inputs.fingerprint,
                  versions=saved['snapshot']['versions'],objective_profile=plain(profile),objectives=plain(evaluate(inputs,blocks,events,profile)),
                  proofs=plain(proofs),issues=plain(core.issues+calendar.issues),open_slots=plain(core.open_slots),
                  unchecked=list(dict.fromkeys(inputs.unchecked+calendar.unchecked+profile.history.missing)),
                  euro_status='ungeklärt – kein freigegebener KV-/BV-Tarif',
                  files={name:sha256(content).hexdigest() for name,content in files.items()})
    files['arbeitsstand.json']=(json.dumps(saved,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    manifest['files']['arbeitsstand.json']=sha256(files['arbeitsstand.json']).hexdigest()
    files['pruefmanifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    descriptor,temporary=tempfile.mkstemp(prefix='.dienstplan-export-',suffix='.zip',dir=target.parent);os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,content in sorted(files.items()):
                archive.writestr(name,content)
                if fault:fault(name)
        with open(temporary,'rb') as stream:os.fsync(stream.fileno())
        os.link(temporary,target)  # atomar, fremdes Ziel niemals überschreiben
    finally:Path(temporary).unlink(missing_ok=True)
    return manifest
