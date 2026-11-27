"""Small deterministic synthetic attack ABM. No chain access, historical targeting or MC."""
from copy import deepcopy
from dataclasses import dataclass,replace
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import sys
from qv_numeric_v2 import ROOT,WS,WalletSqrtNumericV2,PATCH_ID
from policies import (CommonBox,TokenWeighted,CappingWeightPolicy,VoteEscrowWeightPolicy,
    Ballot,InputError,distribution,show)
from escrow import EscrowLedger,LockEvent
sys.path.insert(0,str(WS/'chapter4/behavior'))
from behavior import expected_utility,rational
from engine import Proposal
from catalog import load_catalog

CURRENCY='TEST_COIN'
OUTCOMES={'ACCEPTED','REJECTED'}
class NotReady(InputError):pass
def require(condition,reason):
    if not condition:raise InputError(reason)
def money(x):
    if x is None:raise NotReady('Missing money parameter')
    require(isinstance(x,(str,D)),'Money must be an explicit finite decimal string')
    try:v=D(x)
    except Exception as e:raise InputError('Invalid money') from e
    require(v.is_finite() and v>=0,'Money must be finite and nonnegative')
    return F(v)
def number(x):
    if x is None:raise NotReady('Missing economic/behavior parameter')
    return rational(x)
def natural(x):
    require(type(x) is int and x>=0,'Expected nonnegative integer timestamp/seed')
    return x
def belief(x):
    if x is None:raise NotReady('Missing beliefs')
    require(set(x)==OUTCOMES,'Beliefs must cover both computed outcomes')
    out={k:number(v) for k,v in x.items()}
    require(all(v>=0 for v in out.values()) and sum(out.values())==1,'Invalid probability simplex')
    return out
def profile_utility(principal,probabilities,resource=F(0),risk=F(0),cash=F(0),transfer=F(0)):
    values={k:number(principal['governance_values'][k])+number(principal['success_values'][k]) for k in OUTCOMES}
    conversion=number(principal['money_to_utility'])
    require(conversion>0 and resource>=0 and risk>=0,'Invalid cost/conversion')
    spec={'beliefs':belief(probabilities),'resource':resource,'loss':risk,'cash':{CURRENCY:cash}}
    # Reuse 4.1.2 expected utility; positive transfer is accounted exactly once.
    return expected_utility(values,spec,{CURRENCY:conversion})+conversion*transfer

class ResourceLedger:
    def __init__(self,balances):
        self.initial={p:money(v) for p,v in balances.items()}
        self.liquid=dict(self.initial);self.escrow={p:F(0) for p in balances}
        self.peak={p:F(0) for p in balances}
        self.paid={p:F(0) for p in balances};self.received={p:F(0) for p in balances}
        self.fees={p:F(0) for p in balances};self.refunds={p:F(0) for p in balances}
        self.locked_total={p:F(0) for p in balances}
    def check(self):
        for p in self.initial:
            require(self.liquid[p]>=0 and self.escrow[p]>=0,'Negative cash/escrow')
            require(self.liquid[p]+self.escrow[p]==self.initial[p]-self.fees[p]-self.paid[p]+self.received[p],
                    'Principal cash identity failed')
        require(sum(self.liquid.values())+sum(self.escrow.values())+sum(self.fees.values())==sum(self.initial.values()),
                'System cash conservation failed')
    def fund(self,p,liability,fee):
        require(liability>=0 and fee>=0 and liability+fee<=self.liquid[p],'Insufficient peak cash')
        self.liquid[p]-=liability+fee;self.escrow[p]+=liability;self.fees[p]+=fee
        self.locked_total[p]+=liability;self.peak[p]=max(self.peak[p],self.escrow[p]);self.check()
    def charge(self,p,fee):
        require(fee>=0 and fee<=self.liquid[p],'Insufficient action cash before settlement')
        self.liquid[p]-=fee;self.fees[p]+=fee;self.check()
    def pay(self,p,recipient,amount):
        require(amount>=0 and amount<=self.escrow[p] and p!=recipient,'Bad escrow transfer')
        self.escrow[p]-=amount;self.liquid[recipient]+=amount;self.paid[p]+=amount;self.received[recipient]+=amount
        self.check()
    def refund(self,p):
        x=self.escrow[p];self.escrow[p]=F(0);self.liquid[p]+=x;self.refunds[p]+=x;self.check()
    def report(self):
        return {p:dict(initial=self.initial[p],liquid=self.liquid[p],escrow=self.escrow[p],peak_escrow=self.peak[p],
            total_funded=self.locked_total[p],paid=self.paid[p],received=self.received[p],
            external_fees=self.fees[p],refund=self.refunds[p]) for p in self.initial}

@dataclass
class AttackerAgent:
    principal_id:str
    profile:dict
    def decide(self,view):
        p=self.profile
        keep=profile_utility(p,p['beliefs_keep'])
        act=profile_utility(p,p['beliefs_act'],number(view['resource_utility'])+
            number(view['opportunity_utility'])+number(view['capital_utility']),
            number(view['risk_utility']),money(view['setup_fee'])+money(view['expected_paid']))
        delta=act-keep
        return dict(utility_keep=keep,utility_act=act,delta=delta,epsilon=number(p['epsilon']),
                    choose_attack=delta>number(p['epsilon']),
                    rule='STRICT_DELTA_GT_EPSILON_KEEP_ON_TIE_NOT_SPNE')

def parse_config(config):
    c=deepcopy(config)
    require(set(c)=={'schema','scenario_id','data_label','seed','mechanism','cap_vp','proposal','principals',
        'attacker','voters','attack','rho','ve'},'Root schema mismatch')
    require(c['schema']=='4.3-attack-v1' and c['data_label']=='SYNTHETIC_TEST_ONLY','Synthetic v1 input required')
    natural(c['seed'])
    require(c['rho']=='FIXED_BASELINE_OUTSIDERS_NO_EXTRA_REACTION','Unspecified outsider reaction')
    require(c['mechanism'] in {'TW','QV','CAP','VE'},'Unknown mechanism')
    money(c['cap_vp'])
    require(c['attacker'] in c['principals'],'Missing attacker principal')
    p=c['proposal'];require(set(p)=={'id','choices','snapshot_time','created','start','end','network','block'},'Proposal schema')
    for key in ('snapshot_time','created','start','end','block'):natural(p[key])
    require(p['choices']==['Yes','No'] and p['network']=='1' and p['block']>0,'Binary synthetic network 1 only')
    require(p['snapshot_time']<=p['created']<p['start']<p['end'],'Temporal metadata inconsistency')
    for principal,s in c['principals'].items():
        require(set(s)=={'budget','governance_values','success_values','beliefs_keep','beliefs_act','money_to_utility','epsilon','utility_unit'},'Principal schema')
        money(s['budget']);belief(s['beliefs_keep']);belief(s['beliefs_act'])
        for k in ('governance_values','success_values'):
            require(set(s[k])==OUTCOMES,'State value scope mismatch')
            for v in s[k].values():number(v)
        require(number(s['epsilon'])>=0 and number(s['money_to_utility'])>0,'Bad epsilon/conversion')
        require(s['utility_unit'] not in ('VP','MANA',CURRENCY),'Personal utility must have its own unit')
    require(len(c['voters'])>0,'Empty declared population')
    from model import normalize_wallet
    for w,s in c['voters'].items():
        require(w==normalize_wallet(w),'Noncanonical wallet')
        require(set(s)=={'principal','vp','choice','rights','rights_at','can_replace',
            'beliefs_keep','beliefs_act','resource_utility','risk_utility','cash_fee'},'Voter schema')
        require(s['principal'] in c['principals'],'Missing shared principal')
        money(s['vp'])
        if s['rights'] is None or s['rights']=='UNKNOWN':raise NotReady('Unknown snapshot rights')
        require(s['rights'] in ('GRANTED','DENIED') and type(s['can_replace']) is bool,'Invalid rights/replace flag')
        natural(s['rights_at'])
        require(s['choice'] is None or type(s['choice']) is int and s['choice'] in (1,2),'Invalid baseline choice')
        if s['choice'] is not None:
            require(s['rights']=='GRANTED' and s['rights_at']<=p['snapshot_time'] and money(s['vp'])>0,'Baseline ballot lacks rights')
        belief(s['beliefs_keep']);belief(s['beliefs_act'])
        for k in ('resource_utility','risk_utility'):require(number(s[k])>=0,'Negative utility cost')
        money(s['cash_fee'])
    a=c['attack']
    require(set(a)=={'family','target_outcome','target_choice','published_at','decision_at','targets','payments',
        'setup_fee','expected_paid','resource_utility','opportunity_utility','capital_utility','risk_utility',
        'split','allocation_at','snapshot_state_unchanged'},'Attack schema mismatch')
    require(a['family'] in ('SWITCH','BRIBE_E','MOBILIZE','SPLIT','FLASH','HELD_LOAN'),'Unknown attack family')
    require(a['target_outcome'] in OUTCOMES and type(a['target_choice']) is int and a['target_choice'] in (1,2),'Target must be predeclared')
    for k in ('published_at','decision_at','allocation_at'):natural(a[k])
    for k in ('setup_fee','expected_paid'):money(a[k])
    for k in ('resource_utility','opportunity_utility','capital_utility','risk_utility'):
        require(number(a[k])>=0,'Negative attacker utility cost')
    require(len(set(a['targets']))==len(a['targets']) and all(w in c['voters'] for w in a['targets']),'Unknown/repeated target')
    require(set(a['payments'])==set(a['targets']),'Payment coverage required, including explicit zero')
    for v in a['payments'].values():money(v)
    if a['family']!='BRIBE_E':require(all(money(v)==0 for v in a['payments'].values()),'Transfers only supported by BRIBE_E')
    liability=sum((money(v) for v in a['payments'].values()),F(0))
    require(money(a['expected_paid'])<=liability,'Expected paid cannot exceed full liability')
    return c

def make_policy(c):
    if c['mechanism']=='TW':return TokenWeighted()
    if c['mechanism']=='QV':return WalletSqrtNumericV2()
    if c['mechanism']=='CAP':return CappingWeightPolicy(D(c['cap_vp']))
    if c['ve'] is None:raise NotReady('Missing declared MANA balances/lock history')
    v=c['ve'];p=c['proposal']
    require(set(v)=={'asset','network','balances_mana','genesis','max_seconds','min_seconds','events'},'VE schema')
    require(v['asset']=='MANA' and v['network']=='1' and set(v['balances_mana'])==set(c['voters']),'MANA-only resource coverage')
    controls={w:s['principal'] for w,s in c['voters'].items()}
    l=EscrowLedger({w:D(x) for w,x in v['balances_mana'].items()},controls,v['genesis'],v['max_seconds'],v['min_seconds'])
    for e in v['events']:l.apply(LockEvent(**{**e,'amount':D(e['amount'])}))
    frozen=l.freeze(p['id'],p['snapshot_time'],p['block'],p['created'])
    return VoteEscrowWeightPolicy(frozen)

def tally(c,population,policy):
    meta=c['proposal']
    p=Proposal(meta['id'],tuple(meta['choices']),({'name':'DECLARED_SYNTHETIC_SNAPSHOT_VP','network':'1'},),
        meta['created'],meta['start'],meta['end'],meta['block'],meta['snapshot_time'],{'snapshot_network':'1'})
    rule=next(r for r in load_catalog(WS/'data_enrichment') if r.family=='threshold')
    box=CommonBox(p,rule,'SCENARIO_ASSUMED',policy,allow_assumed_rights=True)
    votes=[]
    for w,s in sorted(population.items()):
        if s['choice'] is None:continue
        require(s['rights']=='GRANTED' and s['rights_at']<=meta['snapshot_time'],'No valid synthetic snapshot rights')
        vp=D(s['vp'])
        votes.append(Ballot(p.id,w,s['choice'],vp,(vp,),s.get('_action_at',meta['start']+1),p.id+':'+w,'1',p.snapshot_block,
            'SCENARIO_ASSUMED','SCENARIO_GRANTED','EXPLICIT_SYNTHETIC_RESOURCE_REGISTRY'))
    box.commit(votes,p.end);result=box.evaluate(p.end+1)
    weights=[policy.weight(b,box.context(p.end+1)) for b in box.ballots]
    dw=distribution(weights)
    principal_weights={}
    for b,w in zip(box.ballots,weights):
        owner=population[b.wallet_id]['principal']
        principal_weights[owner]=principal_weights.get(owner,F(0))+F(w)
    dp=distribution(principal_weights.values())
    return dict(outcome=result.outcome,options=[show(v) for v in result.option_weights],unit=result.weight_unit,
        source_vp=show(result.total_source_vp),effective_total=show(result.total_effective_weight),votes=result.vote_count,
        wallet_gini=show(dw['gini']),wallet_hhi=show(dw['hhi']),wallet_top1=show(dw['top1_share']),
        controller_gini=show(dp['gini']),controller_hhi=show(dp['hhi']),
        concentration_population='POSITIVE_OR_ZERO_FINAL_BALLOTS_ONLY_DECLARED_CONTROLLERS_NOT_REAL_IDENTITIES',
        certificate=box.certificate,execution='UNKNOWN_NOT_INFERRED')

def feasible(c,ledger):
    a=c['attack'];p=c['proposal'];voters=c['voters'];att=c['attacker']
    if a['family']=='HELD_LOAN':return 'NOT_READY_HELD_LOAN_CONTRACT_AND_DEBT_SCHEDULE_NOT_IMPLEMENTED'
    if a['family']=='FLASH':
        if a['snapshot_state_unchanged'] is not True:return 'NOT_READY_UNVERIFIED_SCORING_PATH'
        return 'INFEASIBLE_PURE_FLASH_RETURNED_BALANCE_NO_NEW_SNAPSHOT_VP'
    if not a['targets']:return 'INFEASIBLE_EMPTY_ACTION_SCOPE'
    if a['family']=='SPLIT':
        if c['mechanism']=='VE':return 'NOT_READY_VE_PRE_SNAPSHOT_ASSET_REDISTRIBUTION_NOT_IMPLEMENTED'
        if not a['published_at']<=a['decision_at']<=a['allocation_at']<=p['snapshot_time']:
            return 'INFEASIBLE_SPLIT_AFTER_RIGHTS_SNAPSHOT'
        if len(a['targets'])!=1:return 'INFEASIBLE_SINGLE_SOURCE_SPLIT_REQUIRED'
        source=voters[a['targets'][0]]
        if source['principal']!=att or source['choice']!=a['target_choice']:return 'INFEASIBLE_SPLIT_REQUIRES_OWN_SAME_CHOICE_SOURCE'
        if not a['split'] or len({x['wallet'] for x in a['split']})!=len(a['split']):return 'INFEASIBLE_BAD_PARTITION'
        for x in a['split']:
            if x['wallet'] not in voters:return 'INFEASIBLE_UNDECLARED_ALIAS'
            s=voters[x['wallet']]
            if s['principal']!=att or (x['wallet']!=a['targets'][0] and money(s['vp'])!=0):
                return 'INFEASIBLE_ALIAS_NOT_EMPTY_SHARED_PRINCIPAL'
            if s['rights']!='GRANTED' or s['rights_at']>p['snapshot_time']:return 'INFEASIBLE_ALIAS_RIGHTS'
        if sum((money(x['vp']) for x in a['split']),F(0))!=money(source['vp']):return 'INFEASIBLE_SPLIT_SOURCE_NOT_CONSERVED'
    else:
        if not p['start']+1<a['published_at']<a['decision_at']<=p['end']:
            return 'INFEASIBLE_ACTION_WINDOW_OR_STRICT_RECEIPT'
        for w in a['targets']:
            s=voters[w]
            if s['rights']!='GRANTED' or s['rights_at']>p['snapshot_time'] or money(s['vp'])<=0:
                return 'INFEASIBLE_NO_SNAPSHOT_RIGHTS'
            if s['choice'] is not None and s['choice']!=a['target_choice'] and not s['can_replace']:
                return 'INFEASIBLE_REPLACEMENT_DENIED'
            if a['family']=='MOBILIZE' and s['choice'] is not None:return 'INFEASIBLE_NOT_UNUSED_ELIGIBLE_RIGHTS'
            if a['family']=='SWITCH' and s['principal']!=att:return 'INFEASIBLE_NOT_ATTACKER_CONTROLLED'
            if a['family']=='BRIBE_E' and s['principal']==att:return 'INFEASIBLE_SELF_PAYMENT_EXCLUDED'
    liability=sum((money(v) for v in a['payments'].values()),F(0))
    if money(a['setup_fee'])+liability>ledger.liquid[att]:return 'INFEASIBLE_INSUFFICIENT_PEAK_BUDGET'
    return 'VALID'

def simulate(config):
    try:
        c=parse_config(config);policy=make_policy(c)
    except NotReady as e:
        return dict(scenario_id=config.get('scenario_id'),status='NOT_READY',reason=str(e),eligible=None,
                    attempted=False,success=None,no_attack=None,with_attack=None)
    ledger=ResourceLedger({p:s['budget'] for p,s in c['principals'].items()})
    a=c['attack'];att=c['attacker'];population=deepcopy(c['voters']);reason=feasible(c,ledger)
    events=[];views=[];responses=[]
    base_record=dict(scenario_id=c['scenario_id'],mechanism=c['mechanism'],seed=c['seed'],
        target_outcome=a['target_outcome'],target_choice=a['target_choice'],family=a['family'],
        data_label=c['data_label'],rho=c['rho'],rng_used=False,Monte_Carlo=False,
        numeric_patch=PATCH_ID,execution_claim=False)
    if reason!='VALID':
        return dict(**base_record,status='NOT_READY' if reason.startswith('NOT_READY') else 'INFEASIBLE',
            reason=reason,eligible=None if reason.startswith('NOT_READY') else False,attempted=False,success=None,
            no_attack=tally(c,population,policy),with_attack=tally(c,population,policy),resources=ledger.report(),events=events,views=views,responses=responses)
    view=dict(clock=a['published_at'],information_basis='DECLARED_EX_ANTE_BELIEFS_NO_FINAL_TALLY',
        own_principal=att,own_budget=ledger.liquid[att],mechanism=c['mechanism'],
        target_outcome=a['target_outcome'],target_choice=a['target_choice'],
        **{k:a[k] for k in ('resource_utility','opportunity_utility','capital_utility','risk_utility','setup_fee','expected_paid')})
    # No counterfactual outcome has been computed or included at decision time.
    decision=AttackerAgent(att,c['principals'][att]).decide(view);views.append({'role':'ATTACKER','view':view,'decision':decision})
    attempted=decision['choose_attack'];qualified=[]
    if attempted:
        liability=sum((money(v) for v in a['payments'].values()),F(0))
        ledger.fund(att,liability,money(a['setup_fee']))
        events.append(dict(time=a['published_at'],phase=0,kind='PUBLIC_FUNDED_OFFER_OR_PLAN',liability=liability,setup_fee=money(a['setup_fee'])))
        if a['family']=='SPLIT':
            original=money(population[a['targets'][0]]['vp'])
            population[a['targets'][0]]['vp']='0';population[a['targets'][0]]['choice']=None
            for x in a['split']:
                population[x['wallet']]['vp']=x['vp'];population[x['wallet']]['choice']=a['target_choice']
            require(sum((money(s['vp']) for s in population.values() if s['principal']==att),F(0))==
                sum((money(s['vp']) for s in c['voters'].values() if s['principal']==att),F(0)),'Split minted source VP')
            events.append(dict(time=a['allocation_at'],phase=1,kind='PRE_SNAPSHOT_FIXED_SOURCE_PARTITION',source=original))
        elif a['family']=='SWITCH':
            for w in a['targets']:
                population[w]['choice']=a['target_choice'];population[w]['_action_at']=a['decision_at']
            events.append(dict(time=a['decision_at'],phase=1,kind='OWN_CONTROLLED_BALLOT_ACTION',wallets=a['targets']))
        else:
            # Every recipient sees the same pre-batch state. No action of a peer leaks.
            for w in sorted(a['targets']):
                s=c['voters'][w];p=c['principals'][s['principal']]
                eta=money(a['payments'][w])
                keep=profile_utility(p,s['beliefs_keep'])
                act=profile_utility(p,s['beliefs_act'],number(s['resource_utility']),number(s['risk_utility']),
                    money(s['cash_fee']),eta)
                delta=act-keep
                v=dict(clock=a['decision_at'],proposal_id=c['proposal']['id'],mechanism=c['mechanism'],
                    wallet=w,own_principal=s['principal'],own_vp=s['vp'],own_choice=s['choice'],
                    own_budget=ledger.liquid[s['principal']],public_offer={'published_at':a['published_at'],
                        'target_choice':a['target_choice'],'payment':eta,'fully_funded':True,
                        'condition':'OPT_IN_ACTION_AND_VALID_FINAL_TARGET_BALLOT_NOT_OUTCOME'},
                    utility_keep=keep,utility_act=act,epsilon=number(p['epsilon']),
                    information_basis='EXOGENOUS_ACTION_BELIEFS_NOT_STRATEGIC_EQUILIBRIUM')
                require(v['public_offer']['published_at']<v['clock'],'No same-second receipt')
                accepted=delta>number(p['epsilon'])
                responses.append(dict(wallet=w,principal=s['principal'],delta=delta,accepted=accepted,
                    fee=money(s['cash_fee']),reason='STRICT_DELTA_GT_EPSILON' if accepted else 'KEEP_ON_WEAK_BOUNDARY'))
                views.append({'role':'RECIPIENT','view':v})
            fees=defaultdict_fraction()
            for r in responses:
                if r['accepted']:fees[r['principal']]+=r['fee']
            over={p for p,x in fees.items() if x>ledger.liquid[p]}
            for r in responses:
                if r['accepted'] and r['principal'] in over:
                    r['accepted']=False;r['reason']='CANCEL_ALL_SPENDERS_OF_OVERBOOKED_SHARED_PRINCIPAL'
                if r['accepted']:
                    ledger.charge(r['principal'],r['fee'])
                    population[r['wallet']]['choice']=a['target_choice']
                    population[r['wallet']]['_action_at']=a['decision_at'];qualified.append(r['wallet'])
            events.append(dict(time=a['decision_at'],phase=1,kind='SIMULTANEOUS_RESPONSE_ATOMIC_BATCH',
                accepted_wallets=qualified,overbooked_principals=sorted(over)))
        # Settlement checks final action, not computed outcome; no result is consulted.
        for w in qualified:
            if population[w]['choice']==a['target_choice']:
                ledger.pay(att,population[w]['principal'],money(a['payments'][w]))
        ledger.refund(att)
        events.append(dict(time=c['proposal']['end']+1,phase=2,kind='VERIFY_FINAL_ACTION_PAY_AND_REFUND',
            paid=ledger.paid[att],refund=ledger.refunds[att],success_not_a_payment_condition=True))
    ledger.check()
    no_attack=tally(c,c['voters'],policy);with_attack=tally(c,population,policy)
    known=no_attack['outcome'] in OUTCOMES and with_attack['outcome'] in OUTCOMES
    success=(with_attack['outcome']==a['target_outcome'] and with_attack['outcome']!=no_attack['outcome']) if known and attempted else False if known else None
    status='ATTEMPTED_SUCCESS' if success else 'ATTEMPTED_FAILURE' if attempted and known else 'ELIGIBLE_DECLINED' if not attempted else 'UNASSESSED_OUTCOME'
    p=c['principals'][att]
    realized=None
    if attempted and known:
        realized=number(p['governance_values'][with_attack['outcome']])+number(p['success_values'][with_attack['outcome']])-number(p['money_to_utility'])*(ledger.paid[att]+ledger.fees[att])-sum(number(a[k]) for k in ('resource_utility','opportunity_utility','capital_utility','risk_utility'))
    return dict(**base_record,status=status,reason='DECLARED_ABM_POLICY_NOT_NASH_OR_SPNE',eligible=True,
        attempted=attempted,success=success,no_attack=no_attack,with_attack=with_attack,
        target_already_in_no_attack=no_attack['outcome']==a['target_outcome'],
        choice_changes=sum(population[w]['choice']!=s['choice'] for w,s in c['voters'].items()),
        resources=ledger.report(),events=sorted(events,key=lambda e:(e['time'],e['phase'])),views=views,responses=responses,
        nominal_money_cost=ledger.paid[att]+ledger.fees[att],net_cash_expense=ledger.paid[att]+ledger.fees[att],
        opportunity_cost_utility=number(a['opportunity_utility']) if attempted else F(0),
        capital_cost_utility=number(a['capital_utility']) if attempted else F(0),
        realized_attacker_utility=realized,
        time_to_action_completion=a['decision_at']-a['published_at'] if attempted else None,
        time_to_final_evaluation=c['proposal']['end']+1-a['published_at'] if attempted else None,
        first_target_time=None,first_target_time_status='NOT_ESTIMATED_FROM_FINAL_OUTCOME',
        monetary_unit=CURRENCY,actual_usd_cost=None,empirical_success_probability=None)

def defaultdict_fraction():
    from collections import defaultdict
    return defaultdict(F)
