"""Historical capping, synthetic escrow and fixed-policy comparisons; no attack model."""
import argparse,hashlib,json,sys
from dataclasses import asdict
from collections import defaultdict,Counter
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
from policies import *
from scenario_fixtures import ve_specs,build_ve_case
from behavior_sidecar import CappingMechanicalBehaviorSession
from run_behavior import jsonable
from behavior import BehaviorSession
from scenarios import fixture_bundle,build_fixture_world
import initialize
from engine import rows

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def protect():
    m=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for n,h in m.items():
        if sha(WS/n)!=h:raise InputError('Previous artifact modified: '+n)
    return len(m)
def record(box,result):
    weights=([box.weight_policy.weight(b,box.context(result.as_of)) for b in box.ballots]
        if box.weight_policy.policy_id==VARIANT else box.exact_weights(result.as_of))
    dist=distribution(weights)
    return dict(outcome=result.outcome,total_effective=show(result.total_effective_weight),
        option_weights_json=json.dumps([show(v) for v in result.option_weights]),
        weight_unit=result.weight_unit,gini=show(dist['gini']),hhi=show(dist['hhi']),
        certificate=json.dumps(box.certificate,sort_keys=True))
def put(prefix,d,row):row.update({prefix+'_'+k:v for k,v in d.items()})

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT)
    output=parser.parse_args(argv).output.resolve()
    if not output.is_relative_to(ROOT):raise InputError('Output must stay inside 4.2.3')
    output.mkdir(parents=True,exist_ok=True);protected=protect()
    import engine,mechanism,qv_mechanism
    for m,p in [(engine,WS/'baseline/engine.py'),(mechanism,WS/'chapter4/mechanisms/token_weighted/mechanism.py'),
                (qv_mechanism,WS/'chapter4/mechanisms/quadratic_voting/qv_mechanism.py')]:
        if Path(m.__file__).resolve()!=p.resolve():raise InputError('Wrong imported module')
    cfg=json.loads((ROOT/'CONFIG.json').read_text(encoding='utf-8'))
    if sha(ROOT/'CONFIG.json')!='48f37e2351e81b98e2e8b1165fa75dec4c12a6bfbf8dea4f6ed2ecd8807f56db':
        raise InputError('Fixed pre-outcome configuration changed; new design version required')
    cap=D(cfg['cap']['amount_vp'])
    freeze_record=json.loads((ROOT/'DESIGN_FREEZE.json').read_text(encoding='utf-8'))
    assert freeze_record['config_sha256']==sha(ROOT/'CONFIG.json')
    print('Imports verified; checking historical source integrity...',flush=True)
    inputs,events,wallets,validation,integrity,counts=initialize.load_sources()
    assert (len(inputs),len(events),len(wallets))==(1023,63662,6004)
    group=defaultdict(list)
    for v in events:group[v.proposal].append(v)
    old_qv={r['snapshot_id']:r for r in rows(WS/'chapter4/mechanisms/quadratic_voting/QV_RESULTS.csv')}
    old_tw={r['snapshot_id']:r for r in rows(WS/'chapter4/mechanisms/token_weighted/BASELINE_METRICS.csv')
        if r['mode']=='A_HISTORICAL_RETAINED'}
    historical=[]
    for p,rule,threshold,flags in inputs:
        bs=[Ballot(p.id,v.voter,v.choice,v.vp,v.components,v.created,v.id,p.raw['snapshot_network'],p.snapshot_block,
            'HISTORICAL_RETAINED','OBSERVED_RETAINED_RECORD',v.source_file,v.state) for v in group[p.id]]
        # Same metadata-only eligibility screen as frozen QV. Retain excluded rows.
        row=dict(snapshot_id=p.id,evidence='OBSERVED_BALLOTS_HYPOTHETICAL_WEIGHT_RULES',
            choices_json=json.dumps(p.choices),status='UNASSESSED_SEMANTICS' if exclusion(p,rule) else 'ASSESSED',
            exclusion_reason=exclusion(p,rule),wallets=len(bs),cap_vp=show(cap),cap_source=cfg['cap']['source'],
            cap_determined=cfg['cap']['determination'],cap_preannounced_in_history=False,
            cap_parameter_determined_at_utc=freeze_record['parameter_determined_at_utc'],
            cap_parameter_time_basis=freeze_record['timestamp_basis'],
            cap_after='TOTAL_RETAINED_VP_ALREADY_INCLUDES_STRATEGIES_AND_DELEGATION',
            redistribution='NONE',historical_outcome=old_tw[p.id]['computed_outcome'],
            historical_threshold_vp=show(threshold),common_outcome_policy=CommonBinaryOutcomePolicy.policy_id,
            quorum='NONE_EXPLICIT_HYPOTHETICAL',difference_boundary='0_WITHIN_EACH_MECHANISM_UNIT',
            candidate_rule_family=rule.family,candidate_rule_commit=rule.commit,
            source_vp=show(sum((F(b.vp) for b in bs),F(0))),ve_outcome='UNASSESSED_MISSING_LOCK_DATA',
            ve_lock_rights_verified=False,identity_verified=False,physical_rights_verified=False,
            source_scope='B_BINDING_1023_NOT_OUTCOME_SELECTED_C',snapshot_time=p.block_timestamp,
            snapshot_block=p.snapshot_block,network=p.raw['snapshot_network'],
            attack_success_rate='',attack_cost_usd='',replacement_history='UNKNOWN_FINAL_RETAINED_ONLY')
        for name,policy in [('tw',TokenWeighted()),('qv',WalletSqrt()),('cap',CappingWeightPolicy(cap))]:
            box=CommonBox(p,rule,'HISTORICAL_RETAINED',policy,flags)
            box.commit(bs,p.end)
            result=box.evaluate(p.end+1)
            assert F(result.total_source_vp)==F(row['source_vp'])
            if name=='tw':
                assert [F(x) for x in json.loads(old_tw[p.id]['option_vp_json'])]==[F(x) for x in result.option_weights]
                assert box.exclusion_reason==old_qv[p.id]['pre_outcome_semantic_screen']
                assert result.outcome==old_qv[p.id]['token_same_new_outcome_policy']
            if name=='qv':assert result.outcome==old_qv[p.id]['qv_outcome']
            put(name,record(box,result),row)
        raw=distribution([b.vp for b in bs])
        row.update(source_gini=show(raw['gini']),source_hhi=show(raw['hhi']),
            concentration_population='SAME_FINAL_BALLOT_WALLETS_INCLUDING_ZERO_NOT_ELIGIBLE_POPULATION',
            cap_removed_vp=show(F(row['source_vp'])-F(row['cap_total_effective'])),
            baseline_raw_tally_match=True,qv_frozen_outcome_match=True,
            changed_cap_vs_tw_common=row['cap_outcome']!=row['tw_outcome'] if row['status']=='ASSESSED' else '',
            changed_cap_vs_historical=row['cap_outcome']!=row['historical_outcome'] if row['status']=='ASSESSED' else '',
            changed_cap_vs_qv_common=row['cap_outcome']!=row['qv_outcome'] if row['status']=='ASSESSED' else '')
        for key in ('default_dependency_gap','budget_layer_unverified','governance_match','production_deployment_verified'):
            row[key]=flags.get(key,'UNVERIFIED')
        historical.append(row)
    print('Historical comparison complete; evaluating declared lock-action scenarios...',flush=True)
    scenario_rows=[];lock_audit=[];specs=ve_specs()
    for spec in specs:
        ledger,frozen,p,rule,bs=build_ve_case(spec)
        row=dict(scenario_id=spec['id'],evidence='SYNTHETIC_TEST_ONLY_NOT_DECENTRALAND_HISTORY',
            snapshot_time=frozen.time,network=frozen.network,block=frozen.block,asset='MANA',
            total_source_asset_mana='180',source_vp_reference='180',
            source_vp_mapping='DECLARED_1_REFERENCE_VP_PER_MANA_NOT_HISTORICAL_TOTAL_VP',
            ve_mapping='1_VE_MANA_POINT_PER_MANA_TIMES_REMAINING_OVER_31536000_SECONDS',
            max_lock_seconds=31536000,min_lock_seconds=86400,cap_vp=show(cap),wallets=2,
            action_selection='SCRIPTED_EXPLICIT_LOCK_EVENTS_NO_BEHAVIOR_INFERENCE',
            lock_rights='SYNTHETIC_DECLARATION_ONLY',identity='DECLARED_ALICE_BOB_NOT_REAL_IDENTITIES',
            outcome_policy=CommonBinaryOutcomePolicy.policy_id,quorum='NONE_DECLARED',
            strategic_response_modelled=False,attack_success_rate='',attack_cost_usd='')
        for name,policy in [('tw',TokenWeighted()),('qv',WalletSqrt()),('cap',CappingWeightPolicy(cap)),('ve',VoteEscrowWeightPolicy(frozen))]:
            box=CommonBox(p,rule,'SCENARIO_ASSUMED',policy,allow_assumed_rights=True)
            box.commit(bs,p.end)
            result=box.evaluate(p.end+1)
            put(name,record(box,result),row)
            if name=='ve':
                row['ve_exact_weights_json']=json.dumps([str(x) for x in box.exact_weights(p.end+1)])
                row['locked_asset_at_snapshot']=show(sum((s.locked for s in frozen.states.values()),F(0)))
                row['liquid_asset_at_snapshot']=show(sum((s.liquid for s in frozen.states.values()),F(0)))
        row['ve_changed_vs_tw_common']=row['ve_outcome']!=row['tw_outcome']
        scenario_rows.append(row)
        lock_audit.append(dict(scenario=spec['id'],events=[asdict(e) for e in ledger.events],
            frozen_states={w:asdict(s) for w,s in frozen.states.items()},
            snapshot=frozen.time,known_at=p.created,position_ids_unique=True,
            future_events_excluded_from_snapshot=True))
    bundle=fixture_bundle()
    control=BehaviorSession(build_fixture_world(bundle),bundle['behavior']);a=control.run()
    session=CappingMechanicalBehaviorSession(build_fixture_world(bundle),bundle['behavior'],cap);b=session.run()
    assert jsonable(a)==jsonable(b) and jsonable(control.log)==jsonable(session.log) and jsonable(control.views)==jsonable(session.views)
    for name,value in [('DECISION_HISTORY.json',session.log),('DECISION_VIEWS.json',session.views)]:
        assert json.loads((WS/'chapter4/behavior/outputs'/name).read_text(encoding='utf-8'))==jsonable(value)
    initialize.write_csv(output/'CAPPING_RESULTS.csv',historical)
    initialize.write_csv(output/'VE_SCENARIO_RESULTS.csv',scenario_rows)
    from scenario_fixtures import A,B,G
    dump(output/'VE_SCENARIO_CONFIG.json',dict(schema='4.2.3-ve-synthetic-v1',genesis=G,
        evidence='SYNTHETIC_ONLY',asset='MANA',network='1',max_lock_seconds=31536000,min_lock_seconds=86400,
        initial_balances_mana={A:'100',B:'80'},controllers={A:'alice',B:'bob'},
        vote_choices={A:1,B:2},reference_vp_per_mana='1',ve_points_per_mana='1',
        cases=[dict(**{k:v for k,v in s.items() if k!='events'},events=[asdict(e) for e in s['events']]) for s in specs]))
    dump(output/'VE_LOCK_AUDIT.json',lock_audit)
    dump(output/'CAPPING_BEHAVIOR_CONFIG.json',bundle)
    dump(output/'CAPPING_BEHAVIOR_DECISIONS.json',session.log)
    dump(output/'CAPPING_BEHAVIOR_VIEWS.json',session.views)
    dump(output/'CAPPING_BEHAVIOR_AUDIT.json',session.cap_audit)
    assessed=[r for r in historical if r['status']=='ASSESSED']
    summary=dict(historical=dict(proposals=1023,votes=63662,wallets=6004,assessed=len(assessed),
        excluded=1023-len(assessed),exclusion_combinations=dict(Counter(r['exclusion_reason'] for r in historical if r['status']!='ASSESSED')),
        cap_changed_vs_tw_common=sum(r['changed_cap_vs_tw_common'] for r in assessed),
        cap_changed_vs_historical=sum(r['changed_cap_vs_historical'] for r in assessed),
        cap_changed_vs_qv_common=sum(r['changed_cap_vs_qv_common'] for r in assessed),
        cap_outcomes=dict(Counter(r['cap_outcome'] for r in assessed)),
        tw_common_outcomes=dict(Counter(r['tw_outcome'] for r in assessed)),
        qv_common_outcomes=dict(Counter(r['qv_outcome'] for r in assessed)),
        cap_transition=dict(Counter(r['tw_outcome']+' -> '+r['cap_outcome'] for r in assessed)),
        cap_gini_lower=sum(F(r['cap_gini'])<F(r['source_gini']) for r in assessed if r['cap_gini']),
        zero_total_undefined=sum(not r['cap_gini'] for r in assessed),
        matches_prior_raw_tallies=1023,matches_prior_qv_outcomes=1023,
        ve_historical_assessed=0,ve_missing_lock_data=1023),
        synthetic=dict(scenarios=len(scenario_rows),ve_outcomes=dict(Counter(r['ve_outcome'] for r in scenario_rows)),
            ve_changed_vs_tw=sum(r['ve_changed_vs_tw_common'] for r in scenario_rows),
            fixed_behavior_decisions=len(session.log),replacements=sum(x.replacement_count for x in session.cap_boxes.values()),
            fixed_behavior_unchanged=True,strategic_response_modelled=False),
        cap_config=cfg['cap'],source_integrity=integrity,source_counts=counts,
        prior_files_unchanged=protect(),Monte_Carlo=False,sensitivity=False,attack_success_evaluated=False)
    dump(output/'SUMMARY.json',summary)
    parents=[WS/'chapter4/mechanisms'/folder/'COMPARISON_CONTRACT.json' for folder in ('token_weighted','quadratic_voting')]
    contract=json.loads(parents[1].read_text(encoding='utf-8'))
    contract.update(status='4.2.3_MECHANICAL_ONLY_NO_DEFENSE_CLAIM',
        parent_contracts={p.relative_to(WS).as_posix():sha(p) for p in parents},
        common_policy_id=CommonBinaryOutcomePolicy.policy_id,
        common_policy_semantics='Strict Yes>No within each declared unit, tie/empty/zero reject, no absolute quorum',
        compatible_historical_population='EXACT_QV_943_SCREEN_WITH_80_UNASSESSED_ROWS_RETAINED',
        cap=cfg['cap'],ve=cfg['ve'],config_sha256=sha(ROOT/'CONFIG.json'),
        normalization='NONE_NO_CROSS_MECHANISM_POINT_TOTAL_COMPARISON',
        historical_ve='NOT_COMPARABLE_MISSING_LOCK_DATA',
        synthetic_ve_resources='MANA_ONLY_100_AND_80_WITH_EXPLICIT_LOCK_ACTIONS',
        fixed_behavior_only=True,mechanism_dependent_beliefs_implemented=False,
        lock_action_selection='SCRIPTED_FEASIBLE_ACTIONS_NOT_UTILITY_OPTIMIZATION',
        identity_policy='NO_VERIFIED_REAL_CONTROLLERS; SYNTHETIC_CONTROLLERS_EXPLICIT',
        source_code_hashes={**contract['source_code_hashes'],**{
            p.relative_to(WS).as_posix():sha(p) for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts}})
    # Remove inherited QV-only active fields; retain explicit nested reference instead.
    for key in ('variant','weight_policy','weight_unit','formula','reference_vp','threshold','outcome_policy','credit_scope','outcome_assumptions','differences_from_historical','parent_contract','parent_contract_sha256'):
        contract.pop(key,None)
    contract['policies']={'token':'TOKEN_WEIGHTED_VP_IDENTITY','qv':VARIANT,'cap':CAP_ID,'ve':VE_ID}
    contract['weight_units']={'token':'VP','qv':'SQRT_CREDIT_POINT','cap':'VP','ve':'VE_MANA_POINT'}
    dump(output/'COMPARISON_CONTRACT.json',contract)
    names=['CAPPING_RESULTS.csv','VE_SCENARIO_RESULTS.csv','VE_SCENARIO_CONFIG.json','VE_LOCK_AUDIT.json',
        'CAPPING_BEHAVIOR_CONFIG.json','CAPPING_BEHAVIOR_DECISIONS.json','CAPPING_BEHAVIOR_VIEWS.json',
        'CAPPING_BEHAVIOR_AUDIT.json','SUMMARY.json','COMPARISON_CONTRACT.json']
    dump(output/'RESULT_MANIFEST.json',{n:sha(output/n) for n in names})
    assert protect()==protected
    print(json.dumps(summary,indent=2),flush=True)
    return summary
if __name__=='__main__':main()
