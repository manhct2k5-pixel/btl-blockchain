"""Offline initializer CLI. Historical events are replayed only for validation."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
import sys

from model import WS, InputError, build_world
sys.path.insert(0,str(WS/'baseline'))
from engine import Proposal, tally, rows, select_rule, number, BINDING_TYPES, level_b_eligibility, snapshot_time_valid, compare_snapshot
from catalog import load_catalog
from integrity import verify_existing, check_provenance

ROOT=Path(__file__).resolve().parent
SCHEMA_VERSION='4.1.1-init-v1'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def safe_json(value):
    if isinstance(value,Decimal):
        return format(value,'f')
    if isinstance(value,dict):
        return {str(k):safe_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [safe_json(v) for v in value]
    return value


def dump(p,value):
    p.write_text(json.dumps(safe_json(value),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')


def write_csv(path,records):
    records=list(records)
    fields=list(dict.fromkeys(k for r in records for k in r))
    if not fields:
        raise InputError('Empty CSV schema')
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(safe_json(records))


def unique(records,key):
    result={}
    for r in records:
        if not r.get(key) or r[key] in result:
            raise InputError('Missing/duplicate primary key: '+key)
        result[r[key]]=r
    return result


def protect():
    manifest=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for name,h in manifest.items():
        if sha(WS/name)!=h:
            raise InputError('Protected prior file changed: '+name)
    return len(manifest)


def read_audit():
    files=list((WS/'chapter3_final').rglob('*'))
    for folder in ('baseline','data_enrichment','ch3_3_3_1','ch3_3_3_2'):
        files+=list((WS/folder).rglob('*'))
    return {str(p.relative_to(WS)):dict(bytes=len(p.read_bytes()),sha256=sha(p))
            for p in sorted(set(files)) if p.is_file() and '__pycache__' not in p.parts}


def load_sources():
    source=WS/'data_enrichment'
    integrity=verify_existing(source)
    log=integrity.pop('source_log')
    metadata=rows(source/'proposal_metadata.csv')+rows(source/'recent/proposal_metadata.csv')
    for r in metadata:
        check_provenance(r,log,r['snapshot_id'])
    proposals={sid:Proposal.parse(r) for sid,r in unique(metadata,'snapshot_id').items()}
    validation=unique(rows(WS/'baseline/BASELINE_VALIDATION.csv'),'snapshot_id')
    margin=rows(WS/'ch3_3_3_1/CH3_3_3_1_VP_MARGIN_RESULTS.csv')
    selected={r['snapshot_id'] for r in margin if r['primary_binding_B']=='True'}
    if set(proposals)!=set(validation) or selected!={sid for sid,r in validation.items()
           if r['level_b_eligible_pre_outcome']=='True' and r['proposal_type'] in BINDING_TYPES}:
        raise InputError('Scope/proposal FK differs from B binding')
    def vote_rows():
        for name in ('votes_recovered.csv','recent/votes_recovered.csv'):
            for r in rows(source/name):
                check_provenance(r,log,r['vote_id'])
                yield r
    all_tallies=tally(proposals,vote_rows())
    rules=load_catalog(source)
    archive_paths=list((source/'raw_downloads').glob('transparency_archive_proposals_json_*'))
    if len(archive_paths)!=1:
        raise InputError('Ambiguous Governance archive')
    archive=unique(json.loads(archive_paths[0].read_text(encoding='utf-8')),'snapshot_id')
    inputs,events=[],[]
    for sid in sorted(selected):
        p,t,v=proposals[sid],all_tallies[sid],validation[sid]
        ref=compare_snapshot(p,t)
        a_ready=(all(ref[k] for k in ('count_match','option_match','total_match')) and
                 all(x.state=='final' for x in t.votes) and p.raw['snapshot_state']=='closed' and p.raw['scores_state']=='final')
        rule=select_rule(rules,p.end,p.raw['cohort'])
        b,reason=level_b_eligibility(p,a_ready,rule,archive.get(sid),1682850399,snapshot_time_valid(p))
        if not b or rule.commit!=v['candidate_rule_commit']:
            raise InputError('Independent B binding eligibility differs: '+reason)
        threshold=number(archive[sid]['required_to_pass'])
        if threshold!=number(v['threshold_effective']) or len(t.votes)!=int(v['computed_votes']):
            raise InputError('Threshold/vote count differs')
        flags={k:v[k] for k in ('phase','default_dependency_gap','production_deployment_verified',
               'governance_match','budget_layer_unverified','manual_adjustment_fields_present_current','level_c_source_selected')}
        flags.update(scoring_runtime_verified=False,eligible_universe_known=False,
                     retained_vote_history_complete=False,rule_knowledge_before_close_verified=False)
        inputs.append((p,rule,threshold,flags))
        events.extend(t.votes)
    wallets=sorted({v.voter for v in events})
    c_ids={sid for sid,r in validation.items() if r['level_c_source_selected']=='True'}
    c_wallets={v.voter for sid in c_ids for v in all_tallies[sid].votes}
    c_votes=sum(len(all_tallies[sid].votes) for sid in c_ids)
    counts=dict(source_proposals=len(proposals),source_votes=sum(len(t.votes) for t in all_tallies.values()),
                B_binding=len(inputs),B_binding_votes=len(events),B_binding_wallets=len(wallets),
                C_proposals=len(c_ids),C_votes=c_votes,C_wallets=len(c_wallets),
                B_binding_outside_C=len(selected-c_ids),
                current_delegation_rows_ignored=len(rows(source/'delegation_current_observations.csv')),
                historical_delegation_edges_verified=0,influence_edges_verified=0)
    if (counts['source_proposals'],counts['source_votes'],len(inputs),len(events),len(wallets),
        len(c_ids),c_votes,len(c_wallets))!=(2852,177729,1023,63662,6004,1006,60804,5921):
        raise InputError('Population count mismatch')
    return inputs,events,wallets,validation,integrity,counts


def export_initial(world,path,scenario):
    path.mkdir(parents=True,exist_ok=True)
    config=dict(schema_version=SCHEMA_VERSION,mode=world.mode,seed=world.seed,randomness_used=False,
                population='RETROSPECTIVE_REGISTRY' if world.mode=='A' else 'ASSUMED_FIXED_ARCHIVE_POOL_NO_ELIGIBILITY_INFERENCE',
                start_time_utc_seconds=world.t0,clock_semantics='PRE_DECISION_EVENTS_STRICTLY_BEFORE_T',
                network='SHARED_VOTING_ENVIRONMENT_NO_SOCIAL_GRAPH',
                deployment_certified=False,behavior_implemented=False,scenario=scenario)
    dump(path/'CONFIG.json',config)
    dump(path/'AGENTS_INITIAL.json',[dict(wallet_id=w,principal_id=a.account.principal_id,role=a.role,
         population_basis=a.population_basis,preferences=None,utility_parameters=None,
         eligible_proposals=None) for w,a in sorted(world.agents.items())])
    dump(path/'RESOURCE_ACCOUNTS.json',[asdict(a) for _,a in sorted(world.accounts.items())])
    dump(path/'PROPOSALS_INITIAL.json',[dict(snapshot_id=sid,choices=e.proposal.choices,start=e.proposal.start,end=e.proposal.end,
         snapshot_references=e.snapshot_references,strategies=e.proposal.strategies,threshold_vp=e.threshold,
         candidate_rule_commit=e.rule.commit,candidate_rule_family=e.rule.family,quality_flags=e.flags,
         totals=e.totals,vote_count=e.votes_count,lifecycle=e.lifecycle,voting_outcome=e.voting_outcome,
         execution_state=e.execution_state,visibility='ADMINISTRATIVE_SETUP_NOT_AGENT_INFORMATION')
         for sid,e in sorted(world.environments.items())])
    dump(path/'CONTEXT_STATES_INITIAL.json',[asdict(s) for _,s in sorted(world.states.items())])
    dump(path/'NETWORK_POLICY.json',dict(historical_delegation_edges=[],influence_edges=[],
         observed_incidence='EVALUATOR_ONLY_ARCHIVE' if world.mode=='A' else 'NOT_IMPORTED',
         missing_edges_mean='UNVERIFIED_NOT_PROOF_OF_NO_REAL_RELATIONSHIPS'))
    return dict(agents=len(world.agents),proposals=len(world.environments),accounts=len(world.accounts),
                materialized_agent_proposal_states=len(world.states),initial_votes=sum(e.votes_count for e in world.environments.values()),
                historical_event_queue=len(world._events),known_budget_accounts=sum(a.balances is not None for a in world.accounts.values()),
                historical_delegation_edges=0,influence_edges=0,seed=world.seed,randomness_used=False)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--scenario',type=Path)
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise InputError('Outputs must be below chapter4/initialization')
    output.mkdir(parents=True,exist_ok=True)
    protected=protect()
    scenario=json.loads(args.scenario.read_text(encoding='utf-8'),parse_float=Decimal) if args.scenario else {}
    if not isinstance(scenario,dict):
        raise InputError('Scenario configuration must be a JSON object')
    audit=read_audit()
    inputs,events,wallets,baseline,integrity,counts=load_sources()
    a=build_world('A',inputs,events,wallets,seed=args.seed)
    b=build_world('B',inputs,[],wallets,scenario,args.seed)
    initial_a=export_initial(a,output/'mode_A',{})
    initial_b=export_initial(b,output/'mode_B',scenario)
    archive=output/'evaluation_archive'
    archive.mkdir(exist_ok=True)
    write_csv(archive/'OBSERVED_INCIDENCE.csv',[
        dict(wallet_id=v.voter,snapshot_id=v.proposal,vote_id=v.id,event_utc_seconds=v.created,
             relationship='OBSERVED_RETAINED_VOTE',knowledge='RETROSPECTIVE_NOT_ELIGIBILITY_OR_COORDINATION',
             source_raw_file=v.source_file) for v in sorted(events,key=lambda v:(v.proposal,v.voter))])
    write_csv(archive/'RETAINED_VOTE_EVENTS.csv',[
        dict(vote_id=v.id,wallet_id=v.voter,snapshot_id=v.proposal,created=v.created,choice_index=v.choice,
             vp=v.vp,components_json=json.dumps([format(x,'f') for x in v.components]),
             source_raw_file=v.source_file,visibility='EVALUATOR_ONLY_FUTURE_EVENT_QUEUE')
        for v in a._events])
    before_first=a.clock
    assert not a.states and all(e.votes_count==0 for e in a.environments.values())
    a.advance_before(max(e.proposal.end for e in a.environments.values())+1)
    comparisons=[]
    for sid,e in sorted(a.environments.items()):
        ref=baseline[sid]
        expected=list(map(Decimal,json.loads(ref['computed_option_vp_json'])))
        match=(e.totals==expected and e.votes_count==int(ref['computed_votes']) and
               e.voting_outcome==ref['computed_governance_outcome'])
        if not match:
            raise InputError('Retained replay differs from Baseline: '+sid)
        comparisons.append(dict(snapshot_id=sid,votes_count=e.votes_count,option_vp_json=json.dumps([format(x,'f') for x in e.totals]),
             computed_outcome=e.voting_outcome,baseline_match=match,
             official_status_observed=ref['official_status_observed'],governance_match=ref['governance_match'],
             default_dependency_gap=ref['default_dependency_gap'],production_deployment_verified=False,
             budget_layer_unverified=ref['budget_layer_unverified'],execution_state='UNKNOWN_NOT_REPLAYED'))
    write_csv(archive/'REPLAY_BASELINE_COMPARISON.csv',comparisons)
    summary=dict(counts=counts,mode_A_initial=initial_a,mode_B_initial=initial_b,
         replay_validation=dict(proposals_matched=len(comparisons),retained_votes_applied=len(a._applied),
             same_second_batches=a._batch_count,agent_proposal_states_after_replay=len(a.states),
             original_official_matches=sum(r['governance_match']=='True' for r in comparisons),
             original_official_mismatches=sum(r['governance_match']=='False' for r in comparisons),
             default_gap=sum(r['default_dependency_gap']=='True' for r in comparisons),
             budget_uncertainty=sum(r['budget_layer_unverified']=='True' for r in comparisons),
             full_historical_replacement_trace_reconstructed=False,initial_time=before_first),
         source_integrity=integrity,protected_files_unchanged=protect(),behavior_or_attack_simulated=False,
         Monte_Carlo_executed=False)
    dump(output/'SUMMARY.json',summary)
    dump(output/'INPUT_AUDIT.json',audit)
    dump(output/'OUTPUT_MANIFEST.json',{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*'))
                                      if p.is_file() and p.name!='OUTPUT_MANIFEST.json'})
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    main()
