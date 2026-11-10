"""Tatsächliche native Messwerte über die reguläre GitHub-API sammeln."""
import argparse
import json
from pathlib import Path
import subprocess


def api(repository,path):
    result=subprocess.run(['gh','api',f'repos/{repository}/'+path],check=True,capture_output=True,text=True,encoding='utf-8')
    return json.loads(result.stdout)


def collect(repository,run_id):
    run=api(repository,f'actions/runs/{run_id}')
    if run['status']!='completed':raise ValueError('Nativer Lauf ist noch nicht abgeschlossen; kein fertiger Nachweis.')
    report=dict(run_id=run_id,commit=run['head_sha'],url=run['html_url'],conclusion=run['conclusion'],jobs=[],
                limits=['Automatisierte native Qt-Prüfung; keine vollständige manuelle Bedienabnahme.',
                        'Keine OS-weite Netzabschaltung, Signierung oder Notarisierung nachgewiesen.',
                        'Hauptoberfläche geprüft; Rechenkette mit synthetischer Fixture, keine Rechts-/Tariffreigabe.'])
    for job in api(repository,f'actions/runs/{run_id}/jobs?per_page=100')['jobs']:
        row=dict(name=job['name'],job_id=job['id'],conclusion=job['conclusion'])
        for annotation in api(repository,f'check-runs/{job["id"]}/annotations?per_page=100'):
            try:value=json.loads(annotation['message'])
            except (ValueError,TypeError):continue
            if isinstance(value,dict) and 'bytes' in value and 'architecture' in value:row['build']=value
            if isinstance(value,dict) and 'selbsttest' in value:row['v2_self_test']=value
        if job['conclusion']=='success' and ('build' not in row or row.get('v2_self_test',{}).get('selbsttest')!='bestanden'):
            raise ValueError('Erfolgsstatus ohne vollständige Mess-/Paketnachweise; nicht als geprüft übernehmen.')
        report['jobs'].append(row)
    report['artifacts']=[dict(id=a['id'],name=a['name'],bytes=a['size_in_bytes'],expired=a['expired'],
                url=f'https://github.com/{repository}/actions/runs/{run_id}/artifacts/{a["id"]}')
                for a in api(repository,f'actions/runs/{run_id}/artifacts?per_page=100')['artifacts']]
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',default='waltraudbrunner6-coder/Dienstplan');parser.add_argument('--run',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=collect(args.repo,args.run)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(args.output)


if __name__=='__main__':main()
