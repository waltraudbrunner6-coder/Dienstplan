"""Neue bekannte Regeln nur auf offene normale Altentwürfe anwenden."""
from dataclasses import replace
from datetime import date
from dienstplan.v2.application import demonstration_month
from dienstplan.v2.fallback import dissolve_fallback_groups
from dienstplan.v2.pauses import automatic_pause_choices
from dienstplan.v2.persistence import V2Store
from dienstplan.v2.reporting import hours_rows


def old_normal_month():
    inputs,profile,_=demonstration_month()
    inputs=dissolve_fallback_groups(inputs,{id for g in inputs.fallbacks for id in g.members})
    inputs=replace(inputs,weekend_policy=None,people=tuple(replace(p,rights=tuple(replace(r,codes=r.codes-{'KC15'}) for r in p.rights)) for p in inputs.people))
    term=next(e for e in inputs.events if e.id=='2026-11-30/W17')
    blocks=(automatic_pause_choices(term,'P01')[0],)
    return inputs,replace(profile,month_profile='M0'),blocks


def test_open_old_month_uses_m1_without_writing_or_losing_plan(tmp_path):
    inputs,profile,blocks=old_normal_month()
    with V2Store(tmp_path/'db',create=True) as store:
        store.save_workspace(inputs,profile,blocks,inputs.events,expected_revision=0)
        before=store.connection.total_changes;revision=store.input_revision
        current,policy,planned,active=store.load_workspace(2026,11)
        assert planned==blocks and active==inputs.events
        assert policy.month_profile=='M1' and current.weekend_policy.owner=='sunday'
        assert current.fallbacks and 'KC15' in current.people[0].rights[0].codes
        assert store.connection.total_changes==before and store.input_revision==revision
        row=hours_rows(current.people,planned,current.absences,2026,11,accounts=policy.accounts,target_profile=policy.target_profile,month_profile=policy.month_profile)[0]
        assert row.work==450


def test_confirmed_old_m0_month_stays_byte_identical(tmp_path):
    inputs,profile,blocks=old_normal_month()
    with V2Store(tmp_path/'db',create=True) as store:
        store.save_workspace(inputs,profile,blocks,inputs.events,expected_revision=0)
        store.confirm('confirmed',inputs,blocks,inputs.events,accounts=profile.accounts,wish_policy=profile.wish_policy,fairness_policy=profile.fairness_policy,target_profile='S0',month_profile='M0',expected_revision=store.input_revision,allow_violations=True,synthetic=True)
        raw=store.connection.execute('SELECT payload FROM v2_revisions ORDER BY id').fetchall()
        assert store.load_workspace(2026,11)==(inputs,profile,blocks,inputs.events)
        assert raw==store.connection.execute('SELECT payload FROM v2_revisions ORDER BY id').fetchall()


def test_open_old_reserve_month_gets_work_candidates_without_sql_writes(tmp_path):
    inputs,profile,_=demonstration_month(2026,12)
    inputs=replace(inputs,candidates=tuple(b for b in inputs.candidates if b.code!='R'),
                   unchecked=inputs.unchecked+('F02: Reservebewertung ungeklärt.',))
    with V2Store(tmp_path/'db',create=True) as store:
        store.save_workspace(inputs,profile,expected_revision=0)
        before=store.connection.total_changes
        restored,_,blocks,_=store.load_workspace(2026,12)
        reserve=next(e for e in restored.events if e.id=='2026-12-24/R_early')
        assert any(b.id==reserve.id and b.work_minutes==360 for b in restored.candidates)
        assert not blocks and 'F02: Reservebewertung ungeklärt.' not in restored.unchecked
        assert store.connection.total_changes==before


def test_open_explicit_saturday_policy_and_old_weekend_wishes_upgrade_together(tmp_path):
    from dienstplan.v2.calendar_rules import WeekendPolicy
    inputs,profile,blocks=old_normal_month()
    inputs=replace(inputs,weekend_policy=WeekendPolicy('saturday','Alte Zuordnung'))
    profile=replace(profile,wish_policy=replace(profile.wish_policy,weekend_friday_exception=False))
    with V2Store(tmp_path/'db',create=True) as store:
        store.save_workspace(inputs,profile,blocks,inputs.events,expected_revision=0)
        raw=store.connection.execute('SELECT payload FROM v2_revisions').fetchall()
        current,policy,planned,active=store.load_workspace(2026,11)
        assert current.weekend_policy.owner=='sunday' and policy.wish_policy.weekend_friday_exception
        assert planned==blocks and active==inputs.events
        assert raw==store.connection.execute('SELECT payload FROM v2_revisions').fetchall()
