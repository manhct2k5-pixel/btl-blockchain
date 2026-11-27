"""Explain original duration-only sensitivity, then separate registered two-factor supplement."""
import csv,socket,math,datetime
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from unittest.mock import patch
from audit_common import *
from main_generator import decimal_text
from information_v2 import audited_simulate
from replay_type_b import legacy_duration_variant,compact,world_row,FIELDS,require_gate

def supplement_variant(config,remaining_fraction,amount_fraction):
    c=deepcopy(config);s=c['proposal']['snapshot_time'];v=c['ve']
    for e in v['events']:
        if e['kind']=='CREATE':
            age=s-e['time'];max_remaining=v['max_seconds']-age
            if not 0<max_remaining:raise ValueError('No feasible remaining interval')
            remaining=int(F(str(remaining_fraction))*max_remaining)
            e['end']=s+remaining
            e['amount']=decimal_text(F(v['balances_mana'][e['wallet']])*F(str(amount_fraction)))
            if not e['time']<s<e['end'] or e['end']-e['time']>v['max_seconds']:
                raise ValueError('Invalid supplemental lock timing')
    current_end={e['wallet']:e['end'] for e in v['events'] if e['kind']=='CREATE'}
    kept=[]
    for e in v['events']:
        if e['kind']=='EXTEND':
            if e['time']<=s:raise ValueError('Supplement requires explicit audit for past extension')
            if e['end']<=current_end[e['wallet']]:continue
            current_end[e['wallet']]=e['end']
        kept.append(e)
    v['events']=kept
    return c

def lock_table(c):
    s=c['proposal']['snapshot_time'];v=c['ve']
    return [dict(wallet=e['wallet'],amount=e['amount'],create=e['time'],end=e['end'],
        duration=e['end']-e['time'],remaining=e['end']-s,
        remaining_fraction=str(F(e['end']-s,v['max_seconds'])),
        amount_fraction=str(F(e['amount'])/F(v['balances_mana'][e['wallet']])))
        for e in v['events'] if e['kind']=='CREATE']

def diagnose_original():
    path=ROOT/'TYPE_B_WORLD_LEVEL_RESULTS.csv'
    if not path.is_file():raise FileNotFoundError(path)
    with path.open(encoding='utf-8-sig',newline='') as f:
        variants=[r for r in csv.DictReader(f) if r['experiment_name']=='VOTE_ESCROW_LOCK_TIME']
    worlds={w['world_id']:w for w in read(MAIN/'WORLDS.json') if w['group']=='VE'}
    original={r['world_id']:r for r in read(MAIN/'MC_RESULT_DETAILS.json') if r['mechanism']=='VE'}
    changes=[];summary={}
    for factor in ('0.25','0.5','1.0'):
        rows=[r for r in variants if r['factor_value']==factor]
        s=Counter(eligible=0,attempted=0,policy_success=0,changed_no_attack=0,changed_attack=0,
            gained_success=0,lost_success=0,responses_changed=0,decision_changed=0)
        details=[]
        for r in rows:
            o=original[r['world_id']];c=worlds[r['world_id']]['config'];new=legacy_duration_variant(c,factor)
            before=o['policy_success'] is True;after=r['policy_success']=='True'
            response_same=r['responses_hash']==digest(o.get('responses',[]))
            dec_same=r['attacker_decision_hash']==digest(next((v.get('decision') for v in o.get('views',[]) if v.get('role')=='ATTACKER'),None))
            s['eligible']+=r['eligible']=='True';s['attempted']+=r['attempted']=='True';s['policy_success']+=after
            s['changed_no_attack']+=o['no_attack']['outcome']!=r['no_attack_outcome']
            s['changed_attack']+=o['with_attack']['outcome']!=r['attack_outcome']
            s['gained_success']+=not before and after;s['lost_success']+=before and not after
            s['responses_changed']+=not response_same;s['decision_changed']+=not dec_same
            record=dict(world_id=r['world_id'],factor=factor,family=o['family'],actual_master_seed=worlds[r['world_id']]['master_seed'],
                baseline_no_attack=o['no_attack']['outcome'],variant_no_attack=r['no_attack_outcome'],
                baseline_attack=o['with_attack']['outcome'],variant_attack=r['attack_outcome'],
                legacy_baseline_policy_success=o['policy_success'],
                baseline_eligible=o['eligible'],variant_eligible=(r['eligible']=='True'),
                baseline_attempted=o['attempted'],variant_attempted=(r['attempted']=='True'),
                baseline_policy_success=o['policy_success'] if o['eligible'] is True else None,
                variant_policy_success=None if r['policy_success']=='' else after,
                eligible_unchanged=(o['eligible']==(r['eligible']=='True')),attempted_unchanged=(o['attempted']==(r['attempted']=='True')),
                responses_unchanged=response_same,attacker_decision_unchanged=dec_same,
                baseline_locks_json=canonical(lock_table(c)),variant_locks_json=canonical(lock_table(new)),
                baseline_options_json=canonical(o['no_attack']['options']),variant_options_json=r['no_attack_options_json'],
                baseline_attack_options_json=canonical(o['with_attack']['options']),variant_attack_options_json=r['attack_options_json'])
            changes.append(record)
            if before!=after or record['baseline_no_attack']!=record['variant_no_attack'] or record['baseline_attack']!=record['variant_attack']:
                details.append({k:record[k] for k in ('world_id','family','baseline_no_attack','variant_no_attack',
                    'baseline_attack','variant_attack','baseline_policy_success','variant_policy_success')})
        summary[factor]=dict(s,worlds=len(rows),changed_worlds=details)
    import initialize
    initialize.write_csv(ROOT/'VE_WORLD_CHANGE_AUDIT.csv',changes)
    result=dict(original_43=dict(eligible=sum(r['eligible'] is True for r in original.values()),
        attempted=sum(r['attempted'] is True for r in original.values()),
        policy_success=sum(r['policy_success'] is True for r in original.values())),
        original_44_duration_only=summary,amount_sensitivity_in_original_code=False,
        formula='end=create+fraction*Tmax; actual_remaining=fraction*Tmax-(snapshot-create)',
        source_create_age_seconds=sorted({c['config']['proposal']['snapshot_time']-e['time'] for c in worlds.values()
            for e in c['config']['ve']['events'] if e['kind']=='CREATE'}))
    dump(ROOT/'VE_DIFFERENCE_EXPLANATION.json',result);return result

def run_supplement():
    require_gate()
    contract=read(ROOT/'VE_SUPPLEMENT_CONTRACT.json')
    dump(ROOT/'VE_SUPPLEMENT_ACTIVATION.json',dict(activated=True,contract_sha256=sha(ROOT/'VE_SUPPLEMENT_CONTRACT.json'),
        gate_sha256=sha(ROOT/'VERIFICATION.json'),at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    worlds=[w for w in read(MAIN/'WORLDS.json') if w['group']=='VE']
    summaries=[];n=0
    with patch.object(socket,'socket',side_effect=RuntimeError('VE audit offline')),(ROOT/'VE_SUPPLEMENT_WORLD_RESULTS.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
        for rem in contract['remaining_of_feasible_max_fractions']:
            for amount in contract['amount_fractions']:
                stats=Counter(worlds=0,eligible=0,attempted=0,success=0)
                cell=dict(experiment_name='VE_SUPPLEMENT_TWO_FACTOR',factor_name='remaining_feasible_max_and_amount',
                    factor_value=f'{rem}|{amount}',mechanism='VE')
                for w in worlds:
                    cfg=supplement_variant(w['config'],rem,amount);cfg['mechanism']='VE'
                    r=compact(audited_simulate(cfg));row=world_row(cell,w,cfg,'NOT_APPLICABLE_NON_SPLIT',None,r,
                        'NEW_REGISTERED_SUPPLEMENT:REMAINING_FRACTION_OF_FEASIBLE_MAX;AMOUNT_OF_DECLARED_MANA')
                    writer.writerow(row);n+=1
                    stats['worlds']+=1;stats['eligible']+=r['eligible'] is True
                    stats['attempted']+=r['attempted'] is True;stats['success']+=r['policy_success'] is True
                summaries.append(dict(remaining_of_feasible_max_fraction=rem,amount_fraction=amount,**stats))
                f.flush();print('VE supplement',summaries[-1],flush=True)
    dump(ROOT/'VE_SUPPLEMENT_SUMMARY.json',dict(contract=contract,world_rows=n,cells=summaries,
        all_original_sources_unchanged=protect(),separate_from_original_56_cells=True))
    return summaries
if __name__=='__main__':
    diagnose_original();run_supplement()
