"""Finite hand-answer fixtures, not random draws or historical attack labels."""
from copy import deepcopy
from attack_core import *

G=1700000000
W=['0x'+format(i,'040x') for i in range(1,8)]
def probabilities(yes):
    return {'ACCEPTED':str(yes),'REJECTED':str(1-F(str(yes)))}
def person(budget,gov_yes=0,gov_no=0,benefit_yes=0,keep='0',act='0'):
    return dict(budget=str(budget),governance_values={'ACCEPTED':str(gov_yes),'REJECTED':str(gov_no)},
        success_values={'ACCEPTED':str(benefit_yes),'REJECTED':'0'},money_to_utility='1',epsilon='0',
        utility_unit='INDIVIDUAL_CHI',beliefs_keep=probabilities(keep),beliefs_act=probabilities(act))
def voter(principal,vp,choice,act='1',keep='0'):
    return dict(principal=principal,vp=str(vp),choice=choice,rights='GRANTED',rights_at=G,
        can_replace=True,beliefs_keep=probabilities(keep),beliefs_act=probabilities(act),
        resource_utility='0',risk_utility='0',cash_fee='0')
def base():
    return dict(schema='4.3-attack-v1',scenario_id='BRIBE_FLIP',data_label='SYNTHETIC_TEST_ONLY',seed=19,
        mechanism='TW',cap_vp='100000',proposal=dict(id='SYNTHETIC_ATTACK_PROPOSAL',choices=['Yes','No'],
            snapshot_time=G,created=G+10,start=G+20,end=G+100,network='1',block=42),
        principals={'attacker':person(10,benefit_yes=20,act='1'),
            'alice':person(0,gov_no=2),'bob':person(0,gov_no=4),'carol':person(0,gov_yes=3)},
        attacker='attacker',voters={W[0]:voter('alice',6,2),W[1]:voter('bob',4,2),W[2]:voter('carol',3,1)},
        attack=dict(family='BRIBE_E',target_outcome='ACCEPTED',target_choice=1,published_at=G+22,
            decision_at=G+23,targets=[W[0]],payments={W[0]:'3'},setup_fee='0',expected_paid='3',
            resource_utility='0',opportunity_utility='0',capital_utility='0',risk_utility='0',
            split=[],allocation_at=G,snapshot_state_unchanged=True),
        rho='FIXED_BASELINE_OUTSIDERS_NO_EXTRA_REACTION',ve=None)

def scenarios():
    out=[]
    def add(name,mutate=None):
        c=base();c['scenario_id']=name
        if mutate:mutate(c)
        out.append(c);return c
    add('BRIBE_FLIP')
    add('INSUFFICIENT_BUDGET',lambda c:c['principals']['attacker'].update(budget='2'))
    add('RECIPIENT_REFUSES',lambda c:c['principals']['alice']['governance_values'].update(REJECTED='10'))
    x=add('PAID_BUT_OUTCOME_FAILS');x['voters'][W[1]]['vp']='20'
    x=add('OWN_SWITCH');x['attack'].update(family='SWITCH',payments={W[0]:'0'},expected_paid='0');x['voters'][W[0]]['principal']='attacker'
    add('AFTER_CLOSE',lambda c:c['attack'].update(published_at=G+101,decision_at=G+102))
    x=add('RIGHT_NOT_AT_SNAPSHOT');x['voters'][W[0]].update(choice=None,rights_at=G+1)
    x=add('ATTACKER_DECLINES');x['principals']['attacker']['success_values']['ACCEPTED']='1'
    x=add('MOBILIZE_DECLARED_NONVOTER');x['attack'].update(family='MOBILIZE',payments={W[0]:'0'},expected_paid='0')
    x['voters'][W[0]].update(choice=None,vp='12');x['principals']['alice']['governance_values'].update(ACCEPTED='4',REJECTED='0')
    x=add('SHARED_RECIPIENT_PRINCIPAL');x['attack'].update(targets=[W[0],W[1]],payments={W[0]:'3',W[1]:'3'},expected_paid='6')
    x['voters'][W[1]]['principal']='alice'
    x=add('SHARED_PRINCIPAL_OVERBOOKED_FEES');x['attack'].update(targets=[W[0],W[1]],payments={W[0]:'5',W[1]:'5'},expected_paid='10')
    x['voters'][W[1]]['principal']='alice';x['principals']['alice']['budget']='1'
    x['voters'][W[0]]['cash_fee']='1';x['voters'][W[1]]['cash_fee']='1'
    x=add('FLASH_SNAPSHOT_UNCHANGED');x['attack'].update(family='FLASH',payments={W[0]:'0'},expected_paid='0')
    x=add('HELD_LOAN_UNSPECIFIED');x['attack'].update(family='HELD_LOAN',payments={W[0]:'0'},expected_paid='0')
    for mech in ('TW','QV','CAP'):
        x=add('FIXED_SOURCE_SPLIT_'+mech);x['mechanism']=mech;x['cap_vp']='30'
        x['voters']={W[0]:voter('attacker',100,1),W[1]:voter('bob',144,2),W[2]:voter('carol',0,None),
            **{W[i]:voter('attacker',0,None) for i in (3,4,5)}}
        x['attack'].update(family='SPLIT',targets=[W[0]],payments={W[0]:'0'},expected_paid='0',
            published_at=G-2,decision_at=G-1,allocation_at=G,
            split=[dict(wallet=W[i],vp='25') for i in (0,3,4,5)])
        for v in x['voters'].values():v['rights_at']=G-3
    for mech in ('QV','CAP','VE'):
        x=add('BRIBE_FLIP_'+mech);x['mechanism']=mech
        if mech=='VE':
            x['ve']=dict(asset='MANA',network='1',balances_mana={w:s['vp'] for w,s in x['voters'].items()},
                genesis=G,max_seconds=31536000,min_seconds=86400,events=[
                    dict(event_id='lock:'+w,kind='CREATE',time=G,wallet=w,actor=s['principal'],amount=s['vp'],
                         end=G+31536000,asset='MANA',network='1') for w,s in x['voters'].items()])
    x=add('MISSING_ECONOMIC_INPUT');x['principals']['attacker']['budget']=None
    x=add('PARTIAL_ESCROW_REFUND');x['attack'].update(targets=[W[0],W[1]],payments={W[0]:'3',W[1]:'1'},expected_paid='4')
    x=add('ALREADY_TARGET_PAID_NO_MARGINAL_CHANGE');x['attack'].update(targets=[W[2]],payments={W[2]:'3'})
    return out
