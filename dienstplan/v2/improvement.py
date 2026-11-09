"""Geprüfte Transfers, Tausche, Dreierzyklen und konkrete Pausenwechsel."""
from itertools import combinations,product
from time import monotonic

from .errors import DomainError
from .objectives import evaluate
from .solver import verify


def improve(inputs,blocks,events,profile,*,deadline,cancel=None):
    best=tuple(blocks);value=tuple(v for _,v in evaluate(inputs,best,events,profile))
    pool=tuple(dict.fromkeys(inputs.candidates+best))
    def running():return monotonic()<deadline and not (cancel is not None and cancel.is_set())
    def accept(proposal):
        nonlocal best,value
        if not running():return False
        core,calendar=verify(inputs,proposal,active_events=events)
        if not core.hard_ok or not calendar.hard_ok:return False
        score=tuple(v for _,v in evaluate(inputs,proposal,events,profile))
        if score>=value:return False
        best,value=tuple(proposal),score;return True
    while running():
        improved=False
        # Beliebige Person oder konkrete Pause für einen vorhandenen Dienst.
        for old in best:
            for new in pool:
                if not running():return best
                if new.id==old.id and new!=old and accept(tuple(b for b in best if b!=old)+(new,)):
                    improved=True;break
            if improved:break
        if improved:continue
        # Tausche und größere Rotationen ändern keine Platzanzahl/Termine.
        for size in (2,3):
            for chosen in combinations(best,size):
                if not running():return best
                if len({b.person_id for b in chosen})!=size:continue
                for direction in (1,-1) if size==3 else (1,):
                    choices=[tuple(c for c in pool if c.id==old.id and c.person_id==chosen[(i+direction)%size].person_id) for i,old in enumerate(chosen)]
                    for replacement in product(*choices):
                        if not running():return best
                        if accept(tuple(b for b in best if b not in chosen)+replacement):improved=True;break
                    if improved:break
                if improved:break
            if improved:break
        if not improved:break
    return best
