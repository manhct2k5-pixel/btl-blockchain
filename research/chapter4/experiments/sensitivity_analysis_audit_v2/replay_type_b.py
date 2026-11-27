"""Replay all 56 original cells, export every world, correct metadata without changing old files."""
import csv,datetime,math,socket,time
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from unittest.mock import patch
from audit_common import *
from main_generator import load_contract,generate_world,decimal_text
from sensitivity_simulator import modify_alias_count,modify_budget
from information_v2 import audited_simulate,declared_grant,declared_block

FIELDS=['experiment_name','factor_name','factor_value','mechanism','world_id','replicate_id','family',
    'actual_master_seed','world_seed','source_world_hash','parameter_input_hash','information_condition',
    'information_authorization','grant_hash','eligible','attempted','success','policy_success',
    'status','execution','governance_execution','no_attack_outcome','attack_outcome','weight_unit',
    'registry_source_vp','no_attack_source_vp','attack_source_vp','no_attack_options_json','attack_options_json',
    'paid','external_fees','refund','peak_escrow','cash_expense','opportunity_utility','capital_utility',
    'time_to_decision','time_to_action_completion','time_to_final_evaluation','no_attack_wallet_gini',
    'attack_wallet_gini','attack_wallet_hhi','model_version','unknown_state','actual_usd_cost',
    'evidence','parameter_semantics','responses_hash','attacker_decision_hash']

def legacy_duration_variant(c,fraction):
    cfg=deepcopy(c)
    for e in cfg['ve']['events']:
        if e['kind']=='CREATE':e['end']=e['time']+int(F(str(fraction))*cfg['ve']['max_seconds'])
    return cfg

def original_cells():
    with (ORIGINAL/'SENSITIVITY_RESULTS.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if len(rows)!=56:raise AssertionError('Expected all 56 original cells')
    keys=[tuple(r[k] for k in ('experiment_name','factor_name','factor_value','mechanism')) for r in rows]
    if len(set(keys))!=56:raise AssertionError('Duplicate original cells')
    return rows

def source_worlds():
    worlds=read(MAIN/'WORLDS.json')
    if len(worlds)!=1200 or len({w['world_id'] for w in worlds})!=1200:raise AssertionError('Wrong world source')
    return worlds
def generator_contract():
    return deepcopy(load_contract())
def seed_probe(generator=generate_world):
    c=generator_contract()
    return generator(c,'MAIN',0)

def verify_seeds(worlds):
    c=generator_contract();records=[]
    for w in worlds:
        regenerated=generate_world(c,w['group'],w['replicate_id'])
        match=regenerated['config']==w['config']
        if not match:raise AssertionError('Stored world and effective generator disagree: '+w['world_id'])
        if w['master_seed']!=c['master_seed']:raise AssertionError('World master seed differs')
        records.append(dict(world_id=w['world_id'],group=w['group'],replicate_id=w['replicate_id'],
            actual_master_seed=c['master_seed'],world_seed=w['config']['seed'],regenerated_config_equal=match,
            input_hash=digest(w['config'])))
    dump(ROOT/'MASTER_SEED_REEXECUTION.json',dict(actual_master_seed=c['master_seed'],
        sensitivity_declared_seed=read(ORIGINAL/'SENSITIVITY_EXPERIMENT_CONTRACT.json')['master_seed'],
        original_runner_did_not_assign_declared_seed=True,worlds_verified=len(records),records=records))
    return c

def cell_configs(cell,worlds,contract):
    name=cell['experiment_name'];factor=cell['factor_value']
    selected=[w for w in worlds if w['group']==('VE' if name=='VOTE_ESCROW_LOCK_TIME' else 'MAIN')]
    if name in ('INFORMATION_CONDITION','ALIAS_COUNT','INTERACTION_ALIAS_CAP'):
        selected=[w for w in selected if w['family']=='SPLIT']
    for w in selected:
        cfg=deepcopy(w['config']);cfg['mechanism']=cell['mechanism'];semantics='ORIGINAL_V1_PARAMETER_RULE_REPLAYED'
        condition='INFORMED_PROPOSER'
        if name=='INFORMATION_CONDITION':condition=factor
        elif name=='ALIAS_COUNT':cfg=modify_alias_count(cfg,int(factor),contract['base_voters'])
        elif name=='CAPPING_THRESHOLD':cfg['cap_vp']=factor
        elif name=='ATTACK_BUDGET':cfg=modify_budget(cfg,float(factor.rstrip('x')))
        elif name=='INTERACTION_ALIAS_CAP':
            k,cap=map(int,factor.split('_'));cfg=modify_alias_count(cfg,k,contract['base_voters']);cfg['cap_vp']=str(cap)
        elif name=='VOTE_ESCROW_LOCK_TIME':
            cfg=legacy_duration_variant(cfg,factor)
            semantics='LOCK_DURATION_FROM_CREATE_NOT_EXACT_REMAINING_FRACTION_AT_SNAPSHOT;AMOUNTS_UNCHANGED'
        else:raise ValueError(name)
        grant=declared_grant(cfg) if cfg['attack']['family']=='SPLIT' and condition=='INFORMED_PROPOSER' else None
        block=declared_block(cfg) if cfg['attack']['family']=='SPLIT' and condition=='BLOCKED' else None
        yield w,cfg,condition,grant,block,semantics

def compact(result):
    out={k:result.get(k) for k in ('eligible','attempted','success','policy_success','status','execution',
        'governance_execution','no_attack','with_attack','resources','net_cash_expense',
        'opportunity_cost_utility','capital_cost_utility','time_to_decision','time_to_action_completion',
        'time_to_final_evaluation','model_version','information_authorization')}
    out['responses_hash']=digest(result.get('responses',[]))
    out['attacker_decision_hash']=digest(next((v.get('decision') for v in result.get('views',[]) if v.get('role')=='ATTACKER'),None))
    return out
def world_row(cell,w,cfg,condition,grant,result,semantics):
    no=result.get('no_attack') or {};yes=result.get('with_attack') or {}
    acc=(result.get('resources') or {}).get(cfg['attacker'],{})
    if result.get('attempted') is False and result.get('success') is not None:raise AssertionError('No attempt cannot fail')
    if result.get('eligible') is not True and result.get('policy_success') is not None:raise AssertionError('Ineligible policy is not false')
    registry=sum((F(v['vp']) for v in cfg['voters'].values()),F(0))
    if no and yes:
        if not 0<=F(no['source_vp'])<=registry or not 0<=F(yes['source_vp'])<=registry:raise AssertionError('VP outside registry')
        if cfg['attack']['family']!='MOBILIZE' and F(no['source_vp'])!=F(yes['source_vp']):raise AssertionError('Source VP changed')
    for p,a in (result.get('resources') or {}).items():
        if F(a['initial'])!=F(cfg['principals'][p]['budget']):raise AssertionError('Principal budget cloned or changed')
        if F(a['liquid'])+F(a['escrow'])!=F(a['initial'])-F(a['external_fees'])-F(a['paid'])+F(a['received']):
            raise AssertionError('Cash identity')
    return dict(experiment_name=cell['experiment_name'],factor_name=cell['factor_name'],factor_value=cell['factor_value'],
        mechanism=cell['mechanism'],world_id=w['world_id'],replicate_id=w['replicate_id'],family=w['family'],
        actual_master_seed=w['master_seed'],world_seed=cfg['seed'],source_world_hash=digest(w['config']),
        parameter_input_hash=digest(cfg),information_condition=condition,
        information_authorization=result.get('information_authorization'),grant_hash=digest(grant) if grant else None,
        eligible=result.get('eligible'),attempted=result.get('attempted'),success=result.get('success'),
        policy_success=result.get('policy_success'),status=result.get('status'),execution=result.get('execution'),
        governance_execution=result.get('governance_execution'),no_attack_outcome=no.get('outcome'),
        attack_outcome=yes.get('outcome'),weight_unit=yes.get('unit'),registry_source_vp=str(registry),
        no_attack_source_vp=no.get('source_vp'),attack_source_vp=yes.get('source_vp'),
        no_attack_options_json=canonical(no.get('options')),attack_options_json=canonical(yes.get('options')),
        paid=str(acc['paid']) if acc else None,external_fees=str(acc['external_fees']) if acc else None,
        refund=str(acc['refund']) if acc else None,peak_escrow=str(acc['peak_escrow']) if acc else None,
        cash_expense=str(result['net_cash_expense']) if result.get('net_cash_expense') is not None else None,
        opportunity_utility=str(result['opportunity_cost_utility']) if result.get('opportunity_cost_utility') is not None else None,
        capital_utility=str(result['capital_cost_utility']) if result.get('capital_cost_utility') is not None else None,
        time_to_decision=result.get('time_to_decision'),time_to_action_completion=result.get('time_to_action_completion'),
        time_to_final_evaluation=result.get('time_to_final_evaluation'),no_attack_wallet_gini=no.get('wallet_gini'),
        attack_wallet_gini=yes.get('wallet_gini'),attack_wallet_hhi=yes.get('wallet_hhi'),
        model_version='SENSITIVITY_INFORMATION_AUDIT_V2',unknown_state=result.get('eligible') is None or
            (result.get('attempted') is True and result.get('success') is None),actual_usd_cost=None,
        evidence='SYNTHETIC_ASSUMPTION',parameter_semantics=semantics,
        responses_hash=result['responses_hash'],attacker_decision_hash=result['attacker_decision_hash'])

def require_gate():
    gate=read(ROOT/'VERIFICATION.json')
    if gate['legacy_scopes']!=13 or gate['new_audit_tests']<=0 or gate['failures'] or gate['errors']:
        raise RuntimeError('Audit tests have not passed')
    if gate['code_manifest_sha256']!=digest(audit_code_manifest()) or gate['audit_contract_sha256']!=sha(ROOT/'AUDIT_CONTRACT.json'):
        raise RuntimeError('Audit gate stale after code/contract change')

def main():
    require_gate();protected=protect();worlds=source_worlds();contract=verify_seeds(worlds)
    cells=original_cells();summaries=[];cache={};nrows=0;start=time.time()
    output=ROOT/'TYPE_B_WORLD_LEVEL_RESULTS.csv'
    with patch.object(socket,'socket',side_effect=RuntimeError('Audit replay offline')),output.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
        for i,cell in enumerate(cells):
            stats=Counter(worlds=0,eligible=0,attempted=0,success=0,declined=0,infeasible=0,not_ready=0,unknown_outcome=0)
            for w,cfg,condition,grant,block,semantics in cell_configs(cell,worlds,contract):
                key=digest([cfg,condition,grant,block])
                if key not in cache:cache[key]=compact(audited_simulate(cfg,condition,grant,block))
                result=cache[key];row=world_row(cell,w,cfg,condition,grant,result,semantics)
                writer.writerow(row);nrows+=1
                stats['worlds']+=1;stats['eligible']+=result['eligible'] is True
                stats['attempted']+=result['attempted'] is True;stats['success']+=result['policy_success'] is True
                stats['declined']+=result['eligible'] is True and not result['attempted']
                stats['infeasible']+=result['eligible'] is False
                stats['not_ready']+=result['eligible'] is None
                stats['unknown_outcome']+=result['attempted'] is True and result['success'] is None
                stats['failure']+=result['attempted'] is True and result['success'] is False
            match=(stats['worlds']==int(cell['n_worlds']) and stats['eligible']==int(cell['n_eligible']) and
                   stats['attempted']==int(cell['n_attempted']) and stats['success']==int(cell['n_success']))
            summaries.append(dict(**{k:cell[k] for k in ('experiment_name','factor_name','factor_value','mechanism')},
                **stats,original_counts_match=match,
                corrected_success_rate_eligible=stats['success']/stats['eligible'] if stats['eligible'] else None,
                corrected_success_rate_attempted=stats['success']/stats['attempted'] if stats['attempted'] else None))
            f.flush()
            print(f"{i+1}/56 {cell['experiment_name']} {cell['factor_value']} {cell['mechanism']}: "
                f"eligible={stats['eligible']} attempted={stats['attempted']} success={stats['success']} match={match} "
                f"elapsed={time.time()-start:.1f}s",flush=True)
    dump(ROOT/'TYPE_B_RECALCULATED_SUMMARY.json',summaries)
    grants={w['world_id']:declared_grant(w['config']) for w in worlds if w['family']=='SPLIT'}
    dump(ROOT/'DECLARED_INFORMATION_GRANTS.json',grants)
    dump(ROOT/'TYPE_B_REPLAY_LOG.json',dict(world_rows=nrows,unique_source_worlds=len(worlds),cells=len(summaries),
        all_original_counts_match=all(s['original_counts_match'] for s in summaries),cached_configs=len(cache),
        actual_master_seed=contract['master_seed'],original_files_unchanged=protect(),offline=True,
        sha256_world_results=sha(output),parameter_rules_reexecuted=True,
        metadata_corrected_without_modifying_original=True,seconds=time.time()-start))
    if protect()!=protected:raise AssertionError('Original data changed')
    return summaries
if __name__=='__main__':main()
