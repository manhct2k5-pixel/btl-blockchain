"""Baseline voting only: evidence/scenario adapter, pure choice rule, atomic scheduler."""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[1]
sys.path.insert(0,str(WS/'chapter4/initialization'))
from model import AgentProposalState, InputError, normalize_wallet
from engine import number, govern


class NotReady(InputError):
    def __init__(self,issues):
        self.issues=issues
        super().__init__('Scenario is not ready: '+'; '.join(issues))


def require(condition,message):
    if not condition:
        raise InputError(message)


def rational(x,nonnegative=False):
    require(x is not None and type(x) is not bool,'Missing/bool utility or probability parameter')
    try:
        value=F(str(x))
    except (ValueError,ZeroDivisionError) as exc:
        raise InputError('Invalid finite rational parameter') from exc
    require(not nonnegative or value>=0,'Negative cost/probability/epsilon')
    return value


def action_keys(n):
    return {'WAIT'}|{f'{kind}:{k}' for kind in ('KEEP','VOTE','REPLACE') for k in range(1,n+1)}


def parse_profile(profile,values,keys,conversions):
    require(isinstance(profile,dict) and set(profile)==keys,'Action profile must explicitly cover every indexed action')
    parsed={}
    for key,spec in profile.items():
        require(isinstance(spec,dict) and set(spec)=={'beliefs','resource_cost_utility','risk_loss_utility','cash_outflow'},
                'Action utility/cost schema mismatch')
        beliefs=spec['beliefs']
        require(isinstance(beliefs,dict) and set(beliefs)==set(values),'Beliefs must cover declared states')
        beliefs={z:rational(p,True) for z,p in beliefs.items()}
        require(sum(beliefs.values())==1,'Belief probabilities must sum exactly to one')
        cash=spec['cash_outflow']
        require(isinstance(cash,dict) and all(isinstance(c,str) and c for c in cash),'Cash outflow must be explicit currency mapping')
        cash={c:number(v) for c,v in cash.items()}
        require(all(c.upper()!='VP' for c in cash),'VP is not a money currency')
        require(not (key=='WAIT' or key.startswith('KEEP:')) or not cash,'WAIT/KEEP has no new cash payment in this baseline')
        require(all(c in conversions for c,v in cash.items() if v>0),'Missing cash-to-utility conversion')
        parsed[key]=dict(beliefs=beliefs,resource=rational(spec['resource_cost_utility'],True),
                         loss=rational(spec['risk_loss_utility'],True),cash=cash)
    return parsed


@dataclass(frozen=True)
class ActionEvaluation:
    action: str
    feasibility: str
    reason: str
    utility: F | None
    delta: F | None
    cash: dict


def expected_utility(values,spec,conversions):
    # State-independent C,D are an explicit special case of Chapter 3.
    cash_cost=sum(conversions[c]*F(v) for c,v in spec['cash'].items() if v>0)
    return sum(p*values[z] for z,p in spec['beliefs'].items())-spec['resource']-spec['loss']-cash_cost


def decide(view):
    """Pure function. Receives only the controlled decision view, never world/archive."""
    current=view['current_choice']
    baseline='WAIT' if current is None else f'KEEP:{current}'
    profile=view['profile']
    values,conversions=view['values'],view['cash_to_utility']
    u0=expected_utility(values,profile[baseline],conversions)
    keys=[baseline]+[f'{"VOTE" if current is None else "REPLACE"}:{k}'
                     for k in range(1,len(view['choices'])+1) if k!=current]
    evaluations=[]
    for action in keys:
        status,reason='VALID','BASELINE_ACTION'
        spec=profile[action]
        if action!=baseline:
            if not view['start']<=view['clock']<=view['end'] or not view['valid_from']<=view['clock']<=view['valid_until']:
                status,reason='INVALID','OUTSIDE_ACTION_WINDOW'
            elif view['scenario_rights']=='DENIED' or view['vp']<=0:
                status,reason='INVALID','NO_SCENARIO_VOTING_RIGHT_OR_POSITIVE_VP'
            elif view['scenario_rights']!='GRANTED' or not view['allow_assumed_rights']:
                status,reason='UNKNOWN','ASSUMED_RIGHT_NOT_ENABLED'
            elif current is not None and not view['can_replace']:
                status,reason='INVALID','REPLACEMENT_NOT_ALLOWED'
            else:
                for currency,amount in spec['cash'].items():
                    if amount==0:
                        continue
                    if view['balances'] is None or currency not in view['balances']:
                        status,reason='UNKNOWN','MISSING_BUDGET'
                        break
                    if amount>view['balances'][currency]:
                        status,reason='INVALID','INSUFFICIENT_KNOWN_BUDGET'
                        break
        utility=expected_utility(values,spec,conversions) if status=='VALID' else None
        evaluations.append(ActionEvaluation(action,status,reason,utility,None if utility is None else utility-u0,dict(spec['cash'])))
    # Unknown is never silently treated as false or automatically turned into abstention.
    if any(e.feasibility=='UNKNOWN' for e in evaluations):
        return dict(baseline=baseline,selected=None,reason='UNRESOLVED_ESSENTIAL_INPUT',evaluations=evaluations)
    alternatives=[e for e in evaluations if e.feasibility=='VALID' and e.delta>view['epsilon']]
    if not alternatives:
        return dict(baseline=baseline,selected=baseline,reason='NO_IMPROVEMENT_STRICTLY_ABOVE_EPSILON',evaluations=evaluations)
    best=max(e.utility for e in alternatives)
    tied=[e for e in alternatives if e.utility==best]
    selected=min(tied,key=lambda e:int(e.action.split(':')[1])).action
    return dict(baseline=baseline,selected=selected,reason='MAX_EXPECTED_INCREMENT_METADATA_ORDER_TIEBREAK',evaluations=evaluations)


class BehaviorSession:
    """Adapter around unchanged initialization B; only declared proposal scopes may act."""
    def __init__(self,world,config):
        self.world=world
        self.config=deepcopy(config)
        self.contexts={}
        self.log=[]
        self.views=[]
        self.executed=False
        self.evidence={}
        self.readiness=self._prepare()
        if not self.readiness['ready']:
            raise NotReady(self.readiness['issues'])
        self.initial_balances={p:deepcopy(a.balances) for p,a in world.accounts.items()}
        self.cash_spent=defaultdict(lambda:defaultdict(lambda:Decimal(0)))

    def _prepare(self):
        issues=[]
        try:
            require(self.world.mode=='B' and not self.world._events,'Only empty-event mode B can receive behavior')
            require(all(e.votes_count==0 and not any(e.totals) for e in self.world.environments.values()),'Start from an uncast initialized world')
            require(not any(s.choice is not None for s in self.world.states.values()),'Initial ballots require a separate documented migration')
            require(isinstance(self.config,dict),'Behavior config must be an object')
            required={'scenario_id','data_label','seed','allow_assumed_rights','information_policy',
                      'budget_conflict_policy','transfers_policy','positive_vp_policy','contexts','signals'}
            require(set(self.config)==required,'Behavior config schema mismatch')
            require(isinstance(self.config['scenario_id'],str) and self.config['scenario_id'],'Missing scenario id')
            require(self.config['data_label'] in ('SYNTHETIC_TEST_ONLY','DECLARED_SCENARIO_NOT_FORECAST'),'Missing scenario scope label')
            require(type(self.config['seed']) is int and self.config['seed']==self.world.seed,'Seed/config mismatch')
            require(type(self.config['allow_assumed_rights']) is bool,'Explicit assumed-rights policy required')
            require(self.config['information_policy']=='EXOGENOUS_TAGS_STRICT_RECEIPT','Unsupported information policy')
            require(self.config['budget_conflict_policy']=='CANCEL_ALL_SPENDING_OF_OVERBOOKED_PRINCIPAL','Explicit batch budget policy required')
            require(self.config['transfers_policy']=='NONE_BASELINE','Transfers/strategic actions are not implemented')
            require(self.config['positive_vp_policy']=='REQUIRE_POSITIVE_VP_FOR_ACTIVE_BALLOT','Positive-VP action policy must be declared')
            require(isinstance(self.config['contexts'],list) and self.config['contexts'],'Proposal-specific population scopes required')
            require(isinstance(self.config['signals'],list),'Signals must be explicit list')
        except (InputError,KeyError,TypeError) as exc:
            return dict(ready=False,issues=[str(exc)],physical_rights_certified=False)
        context_fields={'wallet_id','snapshot_id','basis','vp','components','network','snapshot_block','scenario_rights',
            'can_replace','valid_from','valid_until','decision_times','review_on_signal','epsilon','utility_unit',
            'utility_scope','values','cash_to_utility','profiles'}
        for raw in self.config['contexts']:
            try:
                require(isinstance(raw,dict) and set(raw)==context_fields,'Context schema mismatch')
                wallet=normalize_wallet(raw['wallet_id'])
                sid=raw['snapshot_id']
                key=wallet,sid
                require(wallet in self.world.agents and sid in self.world.environments and key not in self.contexts,'Context FK/duplicate failure')
                p=self.world.environments[sid].proposal
                require(p.choices and all(isinstance(x,str) and x for x in p.choices),'Proposal choices missing/invalid')
                env=self.world.environments[sid]
                # Administrative preflight only; this value never enters the actor view.
                govern(p.choices,[Decimal(0) for _ in p.choices],0,env.threshold,env.rule)
                require(raw['basis']=='SCENARIO_ASSUMPTION','No scenario value can self-certify empirical rights')
                require(str(raw['network'])==p.raw['snapshot_network'] and type(raw['snapshot_block']) is int and raw['snapshot_block']==p.snapshot_block,
                        'Context VP belongs to wrong network/block')
                require(raw['scenario_rights'] in ('GRANTED','DENIED'),'Unknown scenario right is an essential missing input')
                require(raw['scenario_rights']!='GRANTED' or self.config['allow_assumed_rights'],'Policy does not enable declared assumed rights')
                require(type(raw['can_replace']) is bool and type(raw['review_on_signal']) is bool,'Explicit boolean replacement/review policy required')
                require(type(raw['valid_from']) is int and type(raw['valid_until']) is int and p.start<=raw['valid_from']<=raw['valid_until']<=p.end,'Invalid action validity window')
                times=raw['decision_times']
                require(isinstance(times,list) and times and all(type(t) is int and raw['valid_from']<=t<=raw['valid_until'] for t in times) and len(set(times))==len(times),'Invalid/missing decision schedule')
                vp=number(raw['vp'])
                require(isinstance(raw['components'],list),'Missing VP components')
                parts=tuple(number(x) for x in raw['components'])
                require(len(parts)==len(p.strategies) and sum(parts)==vp,'Scenario components must sum exactly to VP')
                existing=self.world.states.get(key)
                require(existing is None or existing.vp is None or existing.vp==vp,
                        'Conflicting initial/scenario VP; rebuild the declared initialization')
                require(isinstance(raw['utility_unit'],str) and raw['utility_unit'],'Explicit utility unit required')
                require(raw['utility_unit'].upper()!='VP','Utility cannot be added directly in VP')
                require(raw['utility_scope'] in ('DECLARED_EXPRESSIVE_STATES_NO_EXECUTION_CLAIM','DECLARED_SUBJECTIVE_OUTCOME_BELIEFS'),'Explicit utility interpretation required')
                require(isinstance(raw['values'],dict) and raw['values'],'Declared subjective state values required')
                values={z:rational(v) for z,v in raw['values'].items()}
                require(isinstance(raw['cash_to_utility'],dict),'Explicit cash conversion mapping required')
                conversions={c:rational(v,True) for c,v in raw['cash_to_utility'].items()}
                require(all(isinstance(c,str) and c and c.upper()!='VP' for c in conversions),'Invalid money conversion currency')
                require(all(x>0 for x in conversions.values()),'Cash conversion must be positive')
                require(isinstance(raw['profiles'],dict) and 'initial' in raw['profiles'],'Initial belief profile missing')
                profiles={tag:parse_profile(v,values,action_keys(len(p.choices)),conversions) for tag,v in raw['profiles'].items()}
                account=self.world.agents[wallet].account
                for profile in profiles.values():
                    for action,spec in profile.items():
                        if raw['scenario_rights']=='DENIED' or vp==0 or action.startswith('REPLACE:') and not raw['can_replace']:
                            continue
                        for currency,amount in spec['cash'].items():
                            require(amount==0 or account.balances is not None and currency in account.balances,
                                    'Essential budget missing for action requiring money')
                ctx=dict(raw,wallet_id=wallet,vp=vp,components=parts,epsilon=rational(raw['epsilon'],True),
                         values=values,cash_to_utility=conversions,profiles=profiles)
                self.contexts[key]=ctx
                original=self.world.states.get(key)
                self.evidence[key]=dict(original_initial_state=None if original is None else asdict(original),
                                        physical_rights='UNVERIFIED',scenario_basis='SCENARIO_ASSUMPTION')
            except (InputError,KeyError,TypeError,ValueError) as exc:
                issues.append(str(exc))
        signal_ids=set()
        same_priority={}
        for signal in self.config['signals']:
            try:
                fields={'signal_id','snapshot_id','published_at','received_at','priority','tag','source_id','basis'}
                require(isinstance(signal,dict) and set(signal)==fields,'Signal schema mismatch')
                require(signal['signal_id'] not in signal_ids and signal['basis']=='SCENARIO_ASSUMPTION','Signal id/basis invalid')
                signal_ids.add(signal['signal_id'])
                require(signal['snapshot_id'] in self.world.environments and type(signal['published_at']) is int and
                        type(signal['received_at']) is int and type(signal['priority']) is int and
                        signal['published_at']<=signal['received_at'],'Signal publication/reception invalid')
                require(isinstance(signal['source_id'],str) and signal['source_id'],'Signal source required')
                tie=(signal['snapshot_id'],signal['received_at'],signal['priority'])
                require(tie not in same_priority or same_priority[tie]==signal['tag'],'Simultaneous conflicting tags need distinct declared priority')
                same_priority[tie]=signal['tag']
                for (_,sid),ctx in self.contexts.items():
                    if sid==signal['snapshot_id']:
                        require(signal['tag'] in ctx['profiles'],'No response profile for received public signal')
            except (InputError,KeyError,TypeError) as exc:
                issues.append(str(exc))
        return dict(ready=not issues,issues=issues,contexts=len(self.contexts),
                    physical_rights_certified=False,assumptions_enabled=self.config['allow_assumed_rights'])

    def decision_view(self,key,t):
        """Controlled extension of old agent_view; no raw metadata or final-data access."""
        ctx=self.contexts[key]
        base=self.world.agent_view(*key)
        require(base is not None and self.world.clock==t,'View requested at wrong time')
        received=[s for s in self.config['signals'] if s['snapshot_id']==key[1] and s['published_at']<=s['received_at']<t]
        received.sort(key=lambda s:(s['received_at'],s['priority'],s['signal_id']))
        tag=received[-1]['tag'] if received else 'initial'
        return dict(wallet_id=key[0],snapshot_id=key[1],clock=t,choices=tuple(base['proposal']['choices']),
            start=base['proposal']['start'],end=base['proposal']['end'],current_choice=base['own_state']['choice'],
            balances=deepcopy(base['own_budget']),vp=ctx['vp'],components=ctx['components'],
            scenario_rights=ctx['scenario_rights'],physical_rights='UNVERIFIED',allow_assumed_rights=self.config['allow_assumed_rights'],
            valid_from=ctx['valid_from'],valid_until=ctx['valid_until'],can_replace=ctx['can_replace'],
            epsilon=ctx['epsilon'],utility_unit=ctx['utility_unit'],values=dict(ctx['values']),
            cash_to_utility=dict(ctx['cash_to_utility']),profile=deepcopy(ctx['profiles'][tag]),
            received_signal_ids=tuple(s['signal_id'] for s in received),profile_tag=tag,
            population_basis='DECLARED_PROPOSAL_SCOPE_NOT_PREDICTED_TURNOUT',transfers_policy='NONE_BASELINE',
            positive_vp_policy=self.config['positive_vp_policy'])

    def _check_invariants(self):
        for sid,e in self.world.environments.items():
            totals=[Decimal(0) for _ in e.proposal.choices]
            count=0
            for (_,pid),state in self.world.states.items():
                if pid==sid and state.choice is not None:
                    require(1<=state.choice<=len(totals),'Ballot choice outside metadata')
                    totals[state.choice-1]+=state.vp
                    count+=1
            require(totals==e.totals and count==e.votes_count and all(x>=0 for x in totals),'VP/count invariant failed')
        for principal,account in self.world.accounts.items():
            initial=self.initial_balances[principal]
            if initial is None:
                require(account.balances is None,'Unknown budget became money')
            else:
                for c,value in initial.items():
                    require(account.balances[c]>=0 and account.balances[c]+self.cash_spent[principal][c]==value,
                            'Cash account conservation failed')

    def run(self):
        require(not self.executed,'A session can run only once')
        self.executed=True
        schedule=defaultdict(set)
        active_proposals={sid for _,sid in self.contexts}
        for key,ctx in self.contexts.items():
            schedule_keys=set(ctx['decision_times'])
            if ctx['review_on_signal']:
                schedule_keys|={s['received_at']+1 for s in self.config['signals'] if s['snapshot_id']==key[1]
                                and ctx['valid_from']<=s['received_at']+1<=ctx['valid_until']}
            for t in schedule_keys:
                schedule[t].add(key)
        with localcontext() as arithmetic:
            arithmetic.prec=120
            for t in sorted(schedule):
                require(t>=self.world.clock,'Clock moved backwards')
                self.world.clock=t
                for sid in active_proposals:
                    self.world.environments[sid].update_lifecycle(t)
                batch=[]
                for key in sorted(schedule[t]):
                    view=self.decision_view(key,t)
                    decision=decide(view)
                    if decision['selected'] is None:
                        raise NotReady([decision['reason']])
                    self.views.append(deepcopy(view))
                    selected=next(e for e in decision['evaluations'] if e.action==decision['selected'])
                    batch.append(dict(key=key,view=view,decision=decision,candidate=selected,committed=selected.action))
                # Reconcile shared cash against the same pre-batch balances, never CSV order.
                requests=defaultdict(lambda:defaultdict(lambda:Decimal(0)))
                for item in batch:
                    principal=self.world.agents[item['key'][0]].account.principal_id
                    for c,amount in item['candidate'].cash.items():
                        requests[principal][c]+=amount
                conflict={p for p,outflows in requests.items() if any(amount>0 and amount>self.world.accounts[p].balances[c]
                                                                      for c,amount in outflows.items())}
                for item in batch:
                    key=item['key']
                    account=self.world.agents[key[0]].account
                    blocked=account.principal_id in conflict and any(x>0 for x in item['candidate'].cash.values())
                    if blocked:
                        item['committed']=item['decision']['baseline']
                    action=item['committed']
                    actual=next(e for e in item['decision']['evaluations'] if e.action==action)
                    if action.startswith(('VOTE:','REPLACE:')):
                        ctx=self.contexts[key]
                        state=self.world.states.get(key)
                        e=self.world.environments[key[1]]
                        new_choice=int(action.split(':')[1])
                        if state is not None and state.choice is not None:
                            require(state.vp==ctx['vp'],'Replacement cannot silently change snapshot VP')
                            e.totals[state.choice-1]-=state.vp
                        else:
                            e.votes_count+=1
                        e.totals[new_choice-1]+=ctx['vp']
                        self.world.states[key]=AgentProposalState(key[0],key[1],ctx['vp'],ctx['components'],new_choice,t,
                            'SCENARIO_ASSUMPTION','SCENARIO_ACTION_PHYSICAL_UNVERIFIED',
                            'SCENARIO_ALLOWED' if ctx['can_replace'] else 'SCENARIO_DENIED')
                    for c,amount in actual.cash.items():
                        if amount:
                            account.balances[c]-=amount
                            self.cash_spent[account.principal_id][c]+=amount
                    self.log.append(dict(wallet_id=key[0],snapshot_id=key[1],time=t,baseline=item['decision']['baseline'],
                        proposed_action=item['candidate'].action,committed_action=action,
                        reason='SHARED_BUDGET_BATCH_CONFLICT' if blocked else item['decision']['reason'],
                        profile_tag=item['view']['profile_tag'],received_signal_ids=item['view']['received_signal_ids'],
                        evaluations=[asdict(x) for x in item['decision']['evaluations']],committed_delta=actual.delta,
                        physical_rights='UNVERIFIED',scenario_basis='SCENARIO_ASSUMPTION',
                        principal_id=account.principal_id,cash_outflow=actual.cash))
                self._check_invariants()
            self.world.clock=max(self.world.environments[sid].proposal.end for sid in active_proposals)+1
            results=[]
            for sid,e in sorted(self.world.environments.items()):
                if sid not in active_proposals:
                    continue
                e.update_lifecycle(self.world.clock)
                results.append(dict(snapshot_id=sid,choices=e.proposal.choices,option_vp=e.totals,votes=e.votes_count,
                    computed_outcome=e.voting_outcome,rule_commit=e.rule.commit,rule_family=e.rule.family,
                    threshold=e.threshold,execution_state=e.execution_state,quality_flags=e.flags))
            self._check_invariants()
        return dict(scenario_id=self.config['scenario_id'],data_label=self.config['data_label'],seed=self.world.seed,
             randomness_used=False,agents_in_scope=len({w for w,_ in self.contexts}),proposal_scopes=len({p for _,p in self.contexts}),
             context_count=len(self.contexts),decision_count=len(self.log),results=results,
             final_accounts={p:a.balances for p,a in self.world.accounts.items()},empirically_validated=False,
             attack_or_defense_simulated=False,Monte_Carlo=False)


def strategic_extension(*args,**kwargs):
    raise NotImplementedError('4.2 strategic behavior is out of scope; no registered attack or defense implementation')
