"""Mehrmonatiger technischer Teststand, ausdrücklich kein voller Betriebsdienstplan."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dienstplan.v2.accounting import MonthAccount
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.exporting import export_package
from dienstplan.v2.history import historical_shares
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.serialization import plain
from dienstplan.v2.solver import solve_feasibility


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--seconds',type=float,default=5)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False);summary=[];balances={}
    with V2Store(args.output/'test.sqlite3',create=True) as store:
        for year,month in ((2026,11),(2026,12),(2027,1)):
            data,p,old=technical_demo(year,month);key=f'{year:04d}-{month:02d}'
            p=replace(p,accounts=tuple(MonthAccount(a.person_id,balances.get(a.person_id,0)) for a in p.accounts),
                       history=store.wish_history(key,policy=p.wish_policy),
                       historical_shares=historical_shares(store.confirmations(),start=p.wish_policy.history_start,month=key))
            result=solve_feasibility(data,time_limit=args.seconds,existing=old,objective_profile=p)
            if result.open_slots:raise RuntimeError('Technischer Beispieldatensatz unvollständig; keine Bestätigung.')
            store.save_workspace(data,p,result.blocks,result.events,expected_revision=store.input_revision)
            value=store.confirm(key,data,result.blocks,result.events,accounts=p.accounts,wish_policy=p.wish_policy,fairness_policy=p.fairness_policy,
                                target_profile='S0',month_profile='M0',expected_revision=store.input_revision,synthetic=True)
            # Wiederholung ist absichtlich derselbe Aufruf: keine Zusatzhistorie.
            again=store.confirm(key,data,result.blocks,result.events,accounts=p.accounts,wish_policy=p.wish_policy,fairness_policy=p.fairness_policy,
                                target_profile='S0',month_profile='M0',expected_revision=store.input_revision,synthetic=True)
            assert again==value
            balances={r['person_id']:r['projected'] for r in value['hours']}
            export_package(args.output/(key+'.zip'),data,p,result.blocks,result.events,proofs=result.proofs)
            summary.append(dict(month=key,scope=data.profile_label,objectives=plain(result.objectives),global_optimal=result.global_optimal,
                                shares=value['shares'],hours=value['hours'],history_basis=value['history_basis'],confirmation_count=len(store.confirmations())))
    (args.output/'zusammenfassung.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(args.output)


if __name__=='__main__':main()
