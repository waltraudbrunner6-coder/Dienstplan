"""Reproduzierbarer kleiner V2-Vergleich; kein historischer Betriebsbenchmark."""
import argparse
import json
from pathlib import Path
import platform
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dienstplan.v2.demo import technical_demo
from dienstplan.v2.objectives import evaluate
from dienstplan.v2.reporting import hours_rows,quantity_rows
from dienstplan.v2.serialization import fingerprint,plain
from dienstplan.v2.solver import solve_feasibility
import ortools


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,nargs='+',default=[5,20,60])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();inputs,profile,incumbent=technical_demo()
    manifest=dict(scope=inputs.profile_label,python=platform.python_version(),platform=platform.platform(),
                  processor=platform.processor(),ortools=ortools.__version__,seed=202611,workers=1,
                  input_fingerprint=inputs.fingerprint,profile_fingerprint=fingerprint(profile),
                  starting_objectives=plain(evaluate(inputs,incumbent,inputs.events,profile)),runs=[])
    for seconds in args.seconds:
        result=solve_feasibility(inputs,time_limit=seconds,existing=incumbent,objective_profile=profile)
        manifest['runs'].append(dict(limit_seconds=str(seconds),elapsed_seconds=str(result.elapsed_seconds),status=result.status,
                open_slots=plain(result.open_slots),objectives=plain(result.objectives),proofs=plain(result.proofs),global_optimal=result.global_optimal,
                assignments=plain(result.blocks),quantities=plain(quantity_rows(result.blocks)),
                hours=plain(hours_rows(inputs.people,result.blocks,inputs.absences,inputs.year,inputs.month,accounts=profile.accounts,target_profile='S0',month_profile='M0'))))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(manifest,stream,ensure_ascii=False,indent=2)
    print(args.output)


if __name__=='__main__':main()
