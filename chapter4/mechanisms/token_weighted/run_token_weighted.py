"""4.2.1 modes A/B. Distinct runner name avoids the preparation Baseline module."""
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from decimal import Decimal,localcontext
from fractions import Fraction as F
import hashlib
import importlib
import json
from pathlib import Path
import sys
from mechanism import ROOT,WS,Ballot,BallotBox,distribution,show
from behavior_adapter import TokenWeightedBehaviorSession
sys.path.insert(0,str(WS/'chapter4/initialization'))
import initialize as initialization
sys.path.insert(0,str(WS/'chapter4/behavior'))
from behavior import BehaviorSession
from scenarios import fixture_bundle,build_fixture_world
from run_behavior import jsonable
from engine import rows,InputError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):
    path.write_text(json.dumps(jsonable(value),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')


def protect():
    m=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for name,h in m.items():
        if sha(WS/name)!=h:
            raise InputError('Protected prior file changed: '+name)
    return len(m)


def input_audit():
    paths=[]
    for name in ('chapter3_final','chapter4/initialization','chapter4/behavior','baseline','data_enrichment','ch3_3_3_1','ch3_3_3_2'):
        paths.extend(p for p in (WS/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return {str(p.relative_to(WS)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(paths)}


def metric_row(box,result,mode,scenario,proposal_type,phase):
    d=distribution([b.vp for b in box.ballots])
    values=result.option_weights
    leaders=[i+1 for i,x in enumerate(values) if x==max(values)]
    applies=box.rule.family not in {'early_empty','early_index_bug_empty','early_index_bug','early_two','early_three'}
    gap=F(result.threshold)-F(result.winner_weight) if applies else None
    row=dict(mode=mode,scenario_id=scenario,snapshot_id=box.proposal.id,proposal_type=proposal_type,phase=phase,
        evidence_origin=box.origin,choices_json=json.dumps(box.proposal.choices),snapshot_network=box.proposal.raw['snapshot_network'],
        snapshot_block=box.proposal.snapshot_block,start=box.proposal.start,end=box.proposal.end,as_of=result.as_of,
        candidate_rule_commit=box.rule.commit,candidate_rule_family=box.rule.family,threshold_vp=show(result.threshold),
        weight_policy_id=result.weight_policy_id,outcome_policy_id=result.outcome_policy_id,
        option_vp_json=json.dumps([show(x) for x in values]),total_effective_weight=show(result.total_effective_weight),
        computed_outcome=result.outcome,governance_winner_label=result.winner_label,governance_winner_vp=show(result.winner_weight),
        raw_leader_indices_json=json.dumps(leaders),raw_leader_tie=len(leaders)>1,tie_has_positive_vp=max(values)>0 and len(leaders)>1,
        threshold_applies=applies,winner_equals_threshold=applies and result.winner_weight==result.threshold,
        signed_winner_threshold_gap_vp=show(gap),
        signed_gap_over_threshold=show(gap/F(result.threshold)) if applies and result.threshold>0 else '',
        threshold_proximity_status='NOT_APPLICABLE' if not applies else 'ZERO_THRESHOLD_UNDEFINED_RATIO' if result.threshold==0 else 'CONTINUOUS_SIGNED_DISTANCE_NO_ARBITRARY_NEAR_CUTOFF',
        concentration_status='DEFINED' if d['total_vp']>0 else 'ZERO_TOTAL_UNDEFINED',
        eligible_population_known=False,eligible_turnout='',attack_success_rate='',money_attack_cost_usd='',
        data_status=result.data_status,execution_status=result.execution_status,physical_rights_verified=False,
        voter_weights_basis='VP_PER_FINAL_BALLOT_PER_PROPOSAL',**{k:show(v) for k,v in d.items()})
    row.update(result.flags)
    return row


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT)
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise InputError('Output must be inside this task folder')
    output.mkdir(parents=True,exist_ok=True)
    protect()
    engine=importlib.import_module('engine')
    if Path(engine.__file__).resolve()!=(WS/'baseline/engine.py').resolve():
        raise InputError('Unexpected engine import; do not replace Governance')
    print('Verified import of baseline/engine.py; checking source integrity...',flush=True)
    inputs,events,wallets,validation,integrity,counts=initialization.load_sources()
    by_sid=defaultdict(list)
    for v in events:
        by_sid[v.proposal].append(v)
    prior=initialization.unique(rows(WS/'ch3_3_3_2/CH3_3_3_2_RESULTS.csv'),'snapshot_id')
    margins={(r['snapshot_id'],r['scenario']):r for r in rows(WS/'ch3_3_3_1/CH3_3_3_1_VP_MARGIN_RESULTS.csv')}
    issues=defaultdict(set)
    for issue in rows(WS/'baseline/BASELINE_MISMATCHES.csv'):
        issues[issue['snapshot_id']].add(issue['issue_code'])
    metrics=[]
    for p,rule,threshold,flags in inputs:
        sid=p.id
        box=BallotBox(p,rule,threshold,'HISTORICAL_RETAINED',flags)
        ballots=[Ballot(sid,v.voter,v.choice,v.vp,v.components,v.created,v.id,p.raw['snapshot_network'],p.snapshot_block,
                 'HISTORICAL_RETAINED','OBSERVED_RETAINED_RECORD',v.source_file,v.state) for v in by_sid[sid]]
        box.commit(ballots,p.end,replace=False)
        result=box.evaluate(p.end+1)
        old=validation[sid]
        expected=tuple(Decimal(x) for x in json.loads(old['computed_option_vp_json']))
        matches=(result.option_weights==expected and result.vote_count==int(old['computed_votes']) and result.outcome==old['computed_governance_outcome'])
        if not matches:
            raise InputError('Mechanism differs from archived Baseline: '+sid)
        row=metric_row(box,result,'A_HISTORICAL_RETAINED','B_BINDING_HISTORICAL',old['proposal_type'],old['phase'])
        observed_status=old['official_status_observed']
        expected_official={'passed':'ACCEPTED','enacted':'ACCEPTED','rejected':'REJECTED','finished':'FINISHED'}.get(observed_status)
        official_matches=expected_official==result.outcome
        if str(official_matches)!=old['governance_match']:
            raise InputError('Independent official-status comparison differs')
        row.update(baseline_tally_outcome_match=matches,official_status_observed=observed_status,
                   original_governance_match=official_matches,source_issue_codes_json=json.dumps(sorted(issues[sid])),
                   replacement_count='',replacement_outcome_change_batches='',
                   replacement_metric_status='UNKNOWN_FINAL_RETAINED_RECORDS_NOT_FULL_REPLACEMENT_HISTORY',
                   previous_ch3_metrics_match=True)
        for field in ('gini','hhi','top1_share','top5_share','top10_share'):
            if row[field]=='' or prior[sid][field]=='':
                if row[field]!=prior[sid][field]:
                    raise InputError('Missing concentration differs from Chapter 3')
            elif abs(F(row[field])-F(prior[sid][field]))>F(1,10**35):
                raise InputError('Concentration differs from Chapter 3')
        if F(row['total_vp'])!=F(prior[sid]['participating_vp']) or result.vote_count!=int(prior[sid]['participating_wallets']):
            raise InputError('Primary Chapter 3 total/count differs')
        for i,scenario in enumerate(('TRANSFER_CONTINUOUS','ADD_ELIGIBLE_UNUSED','WHOLE_WALLETS_ONE_SOURCE'),1):
            m=margins[sid,scenario]
            if m['original_outcome']!=result.outcome or m['candidate_rule_commit']!=rule.commit or Decimal(m['threshold_vp'])!=threshold:
                raise InputError('Margin link origin/rule/threshold differs')
            if tuple(Decimal(x) for x in json.loads(m['original_option_vp_json']))!=result.option_weights or int(m['original_votes'])!=result.vote_count:
                raise InputError('Margin link original tally/count differs')
            for field in ('status','vp_margin','bound_kind','is_proven_optimum'):
                row[f's{i}_{field}']=m[field]
        metrics.append(row)
    historical=list(metrics)
    print(f'Historical mechanism matches {len(historical)} proposals; integrating unchanged behavior...',flush=True)
    bundle=fixture_bundle()
    # Unadapted run is the behavior-preservation control, not a second scientific observation.
    control=BehaviorSession(build_fixture_world(bundle),bundle['behavior'])
    control_result=control.run()
    session=TokenWeightedBehaviorSession(build_fixture_world(bundle),bundle['behavior'])
    behavior_result=session.run()
    if jsonable(session.log)!=jsonable(control.log) or jsonable(session.views)!=jsonable(control.views) or jsonable(behavior_result)!=jsonable(control_result):
        raise InputError('Mechanism adapter changed baseline behavior')
    b_results=[]
    for sid,box in sorted(session.boxes.items()):
        result=box.evaluate(session.world.clock)
        row=metric_row(box,result,'B_SYNTHETIC_BEHAVIOR',bundle['behavior']['scenario_id'],'SYNTHETIC','SYNTHETIC_TEST_ONLY')
        row.update(baseline_tally_outcome_match='NOT_HISTORICAL',official_status_observed='',original_governance_match='',
             replacement_count=box.replacement_count,replacement_outcome_change_batches=sum(
                 a['replacement_batch'] and a['batch_outcome_changed'] for a in session.mechanism_audit if a['snapshot_id']==sid),
             replacement_metric_status='OBSERVED_SYNTHETIC_BATCH_CHANGE_NOT_INDIVIDUAL_CAUSAL_ATTRIBUTION',
             previous_ch3_metrics_match='NOT_APPLICABLE',source_issue_codes_json='[]')
        b_results.append(row)
    metrics.extend(b_results)
    initialization.write_csv(output/'BASELINE_METRICS.csv',metrics)
    initialization.write_csv(output/'HISTORICAL_MISMATCHES.csv',[r for r in historical if not r['original_governance_match']])
    initialization.write_csv(output/'DEFAULT_DEPENDENCY.csv',[r for r in historical if r['default_dependency_gap']=='True'])
    dump(output/'BEHAVIOR_BASELINE_CONFIG.json',bundle)
    dump(output/'MODE_B_DECISIONS.json',session.log)
    dump(output/'MODE_B_VIEWS.json',session.views)
    dump(output/'MODE_B_MECHANISM_AUDIT.json',session.mechanism_audit)
    dump(output/'MODE_B_FINAL_BALLOTS.json',[asdict(b) for _,box in sorted(session.boxes.items()) for b in box.ballots])
    config_digest=sha(output/'BEHAVIOR_BASELINE_CONFIG.json')
    dump(output/'COMPARISON_CONTRACT.json',dict(status='BASELINE_FROZEN_NO_DEFENSE_COMPARISON_EXECUTED',
        baseline_config_sha256=config_digest,weight_policy='TOKEN_WEIGHTED_VP_IDENTITY',weight_unit='VP',
        outcome_policy='ARCHIVED_CANDIDATE_GOVERNANCE',
        common_fixed_fields=['proposal_scope','agents','snapshot_vp','rights_assumptions','values','epsilon',
                      'resources','decision_times','information_policy','signals','seed'],
        mechanical_frozen_fields=['committed_ballots'],
        baseline_belief_profiles_preserved_in_config=True,
        behavioral_requires_declared_mechanism_dependent_belief_rule=True,
        mechanical_design='Freeze committed ballots; change weighting only after specifying compatible outcome/threshold policy',
        behavioral_design='Rerun agents; specify how mechanism changes subjective beliefs/feasibility without changing preferences or initial resources',
        candidate_thresholds_automatically_valid_for_new_weights=False,
        source_code_hashes={name:sha(WS/name) for name in ('baseline/engine.py','chapter4/initialization/model.py','chapter4/behavior/behavior.py',
            'chapter4/mechanisms/token_weighted/mechanism.py','chapter4/mechanisms/token_weighted/behavior_adapter.py')}))
    summary=dict(engine_file=str(Path(engine.__file__).resolve()),engine_sha256=sha(WS/'baseline/engine.py'),
        historical=dict(proposals=len(historical),votes=len(events),wallets=len(wallets),
            baseline_matches=sum(r['baseline_tally_outcome_match'] for r in historical),
            official_matches=sum(r['original_governance_match'] for r in historical),
            official_mismatches=sum(not r['original_governance_match'] for r in historical),
            default_gap=sum(r['default_dependency_gap']=='True' for r in historical),
            budget_uncertainty=sum(r['budget_layer_unverified']=='True' for r in historical),
            outcomes=dict(Counter(r['computed_outcome'] for r in historical)),
            zero_total=sum(r['concentration_status']=='ZERO_TOTAL_UNDEFINED' for r in historical),
            positive_raw_ties=sum(r['tie_has_positive_vp'] for r in historical),
            winner_equals_threshold=sum(r['winner_equals_threshold'] for r in historical),
            chapter3_metric_links=len(historical),replacement_history_status='UNIDENTIFIED'),
        synthetic=dict(agents=behavior_result['agents_in_scope'],proposals=len(b_results),contexts=behavior_result['context_count'],
            decisions=len(session.log),committed_action_counts=dict(Counter(r['committed_action'].split(':')[0] for r in session.log)),
            final_votes=sum(r['voters'] for r in b_results),replacements=sum(r['replacement_count'] for r in b_results),
            replacement_outcome_change_batches=sum(r['replacement_outcome_change_batches'] for r in b_results),
            baseline_behavior_unchanged=True,empirically_validated=False),
        metric_rows=len(metrics),source_counts=counts,source_integrity=integrity,
        protected_prior_files_unchanged=protect(),attack_or_defense_simulated=False,Monte_Carlo=False,
        sensitivity_analysis_performed=False,other_mechanisms_implemented=False)
    if (summary['historical']['proposals'],summary['historical']['baseline_matches'],summary['historical']['official_matches'])!=(1023,1023,1016):
        raise InputError('Unexpected historical control counts')
    dump(output/'SUMMARY.json',summary)
    dump(output/'INPUT_AUDIT.json',input_audit())
    names=['BASELINE_METRICS.csv','HISTORICAL_MISMATCHES.csv','DEFAULT_DEPENDENCY.csv','BEHAVIOR_BASELINE_CONFIG.json',
           'MODE_B_DECISIONS.json','MODE_B_VIEWS.json','MODE_B_MECHANISM_AUDIT.json','MODE_B_FINAL_BALLOTS.json',
           'COMPARISON_CONTRACT.json','SUMMARY.json','INPUT_AUDIT.json']
    dump(output/'RESULT_MANIFEST.json',{name:sha(output/name) for name in names})
    print(json.dumps(jsonable(summary),ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    main()
