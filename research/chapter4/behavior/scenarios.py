"""Small explicit synthetic fixtures. No historical vote choices or estimated parameters."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
from behavior import ROOT,WS,action_keys,require
sys.path.insert(0,str(WS/'chapter4/initialization'))
from model import Proposal,build_world
from catalog import load_catalog

T=1700000000
WALLETS=['0x'+format(i,'040x') for i in range(1,5)]


def action_profile(n,scores,resource_cost='0'):
    # Helper constructs an explicit fixture. Its constants are not engine defaults.
    states=['zero','favorable','unfavorable']
    out={}
    for key in sorted(action_keys(n)):
        value=scores.get(key,0)
        beliefs=dict.fromkeys(states,'0')
        beliefs['favorable' if value>0 else 'unfavorable' if value<0 else 'zero']='1'
        out[key]=dict(beliefs=beliefs,resource_cost_utility=resource_cost if key.startswith(('VOTE:','REPLACE:')) else '0',
                      risk_loss_utility='0',cash_outflow={})
    return out


def context(wallet,sid,n,vp,scores):
    return dict(wallet_id=wallet,snapshot_id=sid,basis='SCENARIO_ASSUMPTION',
        vp=str(vp),components=[str(vp)],network='1',snapshot_block=42,scenario_rights='GRANTED',
        can_replace=True,valid_from=T,valid_until=T+100,decision_times=[T+1],
        review_on_signal=True,epsilon='0',utility_unit='individual_chi',
        utility_scope='DECLARED_EXPRESSIVE_STATES_NO_EXECUTION_CLAIM',
        values={'zero':'0','favorable':'3','unfavorable':'-3'},cash_to_utility={},
        profiles={'initial':action_profile(n,scores)})


def fixture_bundle():
    c1=context(WALLETS[0],'SYNTHETIC_BINARY',2,10,{'VOTE:1':1,'KEEP:1':1})
    c1['decision_times']=[T+1,T+20]
    c2=context(WALLETS[1],'SYNTHETIC_BINARY',2,5,{'VOTE:1':-1,'VOTE:2':-1})
    c3=context(WALLETS[2],'SYNTHETIC_BINARY',2,3,{'VOTE:1':1,'VOTE:2':1,'KEEP:1':1,'KEEP:2':1})
    c4=context(WALLETS[3],'SYNTHETIC_MULTI',3,6,{'VOTE:1':1,'KEEP:1':1,'VOTE:3':-1})
    c5=context(WALLETS[1],'SYNTHETIC_MULTI',3,0,{'VOTE:1':1})
    c5['scenario_rights']='DENIED'
    for c in (c1,c2,c3,c4,c5):
        c['profiles']['news']=deepcopy(c['profiles']['initial'])
    c3['profiles']['news']=action_profile(2,{'VOTE:2':1,'REPLACE:2':1,'KEEP:2':1})
    behavior=dict(scenario_id='BASELINE_SMALL_SYNTHETIC_TEST',data_label='SYNTHETIC_TEST_ONLY',seed=19,
         allow_assumed_rights=True,information_policy='EXOGENOUS_TAGS_STRICT_RECEIPT',
         budget_conflict_policy='CANCEL_ALL_SPENDING_OF_OVERBOOKED_PRINCIPAL',transfers_policy='NONE_BASELINE',
         positive_vp_policy='REQUIRE_POSITIVE_VP_FOR_ACTIVE_BALLOT',
         contexts=[c1,c2,c3,c4,c5],signals=[dict(signal_id='synthetic_news',snapshot_id='SYNTHETIC_BINARY',
             published_at=T+9,received_at=T+10,priority=1,tag='news',source_id='EXOGENOUS_TEST_INPUT',basis='SCENARIO_ASSUMPTION')])
    return dict(schema_version='4.1.2-synthetic-v1',source_label='SYNTHETIC_TEST_ONLY',
        proposals=[dict(snapshot_id='SYNTHETIC_BINARY',choices=['Yes','No'],start=T,end=T+100,created=T-10,
                       snapshot_block=42,snapshot_timestamp=T-20,network='1',threshold='10',rule_family='threshold'),
                   dict(snapshot_id='SYNTHETIC_MULTI',choices=['for','against','invalid question/options'],
                       start=T,end=T+100,created=T-10,snapshot_block=42,snapshot_timestamp=T-20,network='1',
                       threshold='5',rule_family='invalid_votes')],
        agents=WALLETS,resources=dict(owner_map={},budgets_by_principal={}),behavior=behavior)


def build_fixture_world(bundle):
    require(set(bundle)=={'schema_version','source_label','proposals','agents','resources','behavior'},'Synthetic bundle schema mismatch')
    require(bundle['source_label']=='SYNTHETIC_TEST_ONLY','This factory only builds marked synthetic test worlds')
    rules=load_catalog(WS/'data_enrichment')
    inputs=[]
    for raw in bundle['proposals']:
        rule=next((r for r in rules if r.family==raw['rule_family']),None)
        require(rule is not None,'Unsupported candidate family')
        p=Proposal(raw['snapshot_id'],tuple(raw['choices']),({'name':'synthetic_test_component','network':raw['network']},),
                   raw['created'],raw['start'],raw['end'],raw['snapshot_block'],raw['snapshot_timestamp'],
                   {'snapshot_network':raw['network'],'snapshot_block_hash':'SYNTHETIC_NOT_CHAIN_EVIDENCE'})
        flags=dict(production_deployment_verified=False,default_dependency_gap=rule.uses_default,
                   governance_match='NOT_APPLICABLE_SYNTHETIC',budget_layer_unverified=True,
                   data_label='SYNTHETIC_TEST_ONLY',scoring_runtime_verified=False)
        inputs.append((p,rule,Decimal(raw['threshold']),flags))
    resource_input=bundle['resources']
    require(set(resource_input)=={'owner_map','budgets_by_principal'},'Resource schema mismatch')
    return build_world('B',inputs,[],bundle['agents'],dict(scenario_label='SYNTHETIC_TEST_ONLY',
                       owner_map=resource_input['owner_map'],budgets_by_principal=resource_input['budgets_by_principal']),
                       bundle['behavior']['seed'])
