"""Initialization and retained-event replay only. No agent decision rules."""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from pathlib import Path
import re
import sys

WS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WS/'baseline'))
from engine import InputError, Proposal, Rule, Vote, govern, number


def normalize_wallet(value):
    if not isinstance(value,str) or not re.fullmatch(r'0x[0-9a-fA-F]{40}',value):
        raise InputError('Invalid wallet identity')
    return value.lower()


@dataclass
class ResourceAccount:
    principal_id: str
    balances: dict[str,Decimal] | None = None
    provenance: str = 'UNKNOWN_NOT_ZERO'


@dataclass
class Agent:
    wallet_id: str
    account: ResourceAccount
    role: str
    preferences: dict | None = None
    utility_parameters: dict | None = None
    population_basis: str = ''


@dataclass
class AgentProposalState:
    wallet_id: str
    snapshot_id: str
    vp: Decimal | None = None
    components: tuple[Decimal,...] | None = None
    choice: int | None = None
    known_since: int | None = None
    vp_basis: str = 'UNKNOWN'
    permission_status: str = 'UNVERIFIED'
    replacement_permission: str = 'UNVERIFIED'


@dataclass
class ProposalEnvironment:
    proposal: Proposal
    rule: Rule
    threshold: Decimal
    flags: dict
    snapshot_references: dict
    totals: list[Decimal] = field(default_factory=list)
    votes_count: int = 0
    lifecycle: str = 'DORMANT'
    voting_outcome: str | None = None
    execution_state: str | None = None

    def __post_init__(self):
        p=self.proposal
        if not p.raw.get('snapshot_network','').isdigit() or p.snapshot_block<=0:
            raise InputError('Primary network/block not identified')
        if p.block_timestamp is None or p.block_timestamp>p.created:
            raise InputError('Snapshot timing unverified for primary replay scope')
        if self.rule.commit_timestamp>p.end:
            raise InputError('Future rule candidate')
        primary=self.snapshot_references.get(p.raw['snapshot_network'],{})
        if primary.get('block')!=p.snapshot_block:
            raise InputError('Snapshot block/network mismatch')
        if self.totals:
            raise InputError('Initialization must not preload final tally')
        self.totals=[Decimal(0) for _ in p.choices]

    def update_lifecycle(self,clock):
        p=self.proposal
        self.lifecycle='DORMANT' if clock<p.start else 'OPEN' if clock<=p.end else 'CLOSED'
        if self.lifecycle=='CLOSED':
            with localcontext() as ctx:
                ctx.prec=120
                self.voting_outcome=govern(p.choices,self.totals,self.votes_count,self.threshold,self.rule).outcome


def networks_in(value):
    result=set()
    if isinstance(value,dict):
        if 'network' in value:
            if not str(value['network']).isdigit():
                raise InputError('Invalid strategy network')
            result.add(str(value['network']))
        if isinstance(value.get('graphs'),dict):
            result.update(str(k) for k in value['graphs'] if str(k).isdigit())
        for v in value.values():
            result.update(networks_in(v))
    elif isinstance(value,(list,tuple)):
        for v in value:
            result.update(networks_in(v))
    return result


def snapshot_references(p):
    primary=p.raw['snapshot_network']
    result={n:dict(block=None,block_hash=None,verification='UNVERIFIED_AUXILIARY_BLOCK_MAPPING')
            for n in networks_in(p.strategies)|{primary}}
    result[primary]=dict(block=p.snapshot_block,block_hash=p.raw.get('snapshot_block_hash') or None,
                         block_timestamp=p.block_timestamp,verification='OBSERVED_HEADER_NOT_FULL_SCORING_REPLAY')
    return result


def build_agents(wallets,mode,scenario):
    normalized=[normalize_wallet(w) for w in wallets]
    if len(set(normalized))!=len(normalized):
        raise InputError('Duplicate normalized wallet')
    owner_map=scenario.get('owner_map',{})
    if not isinstance(owner_map,dict):
        raise InputError('owner_map must be an object')
    normalized_owners={}
    for wallet,principal in owner_map.items():
        key=normalize_wallet(wallet)
        if key in normalized_owners or key not in normalized or not isinstance(principal,str) or not principal:
            raise InputError('Invalid or duplicate owner assignment')
        normalized_owners[key]=principal
    owners={w:normalized_owners.get(w,'wallet_unit:'+w) for w in normalized}
    budgets=scenario.get('budgets_by_principal',{})
    if not isinstance(budgets,dict) or set(budgets)-set(owners.values()):
        raise InputError('Budget provided for nonexistent principal')
    accounts={}
    for principal in sorted(set(owners.values())):
        value=budgets.get(principal)
        if value is not None and (not isinstance(value,dict) or not value):
            raise InputError('Budget must be explicit nonempty currency mapping, or null')
        if value is not None and any(not isinstance(c,str) or not c for c in value):
            raise InputError('Invalid currency')
        accounts[principal]=ResourceAccount(principal,None if value is None else {c:number(v) for c,v in value.items()},
                                             'UNKNOWN_NOT_ZERO' if value is None else 'SCENARIO_DECLARED_NOT_OBSERVED')
    agents={w:Agent(w,accounts[owners[w]],'UNASSIGNED_ARCHIVE_ROLE' if mode=='A' else 'BASELINE_SCENARIO_ROLE',
                     population_basis='OBSERVED_AFTER_CLOSE_REGISTRY' if mode=='A' else 'ASSUMED_FIXED_ARCHIVE_WALLET_POOL')
            for w in sorted(normalized)}
    return agents,accounts


class InitializedWorld:
    """Archive fields are evaluator-only. Agent information is returned by agent_view."""
    def __init__(self,mode,agents,accounts,environments,events,seed=0):
        if mode not in ('A','B') or type(seed) is not int:
            raise InputError('Invalid mode or seed')
        if not environments or mode=='B' and events:
            raise InputError('Nonempty proposal catalog required; B must not receive historical events')
        self.mode,self.agents,self.accounts=mode,agents,accounts
        self.environments=environments
        self.clock=min(e.proposal.start for e in environments.values())
        self.t0=self.clock
        self.seed=seed
        self.randomness_used=False
        self.states={}
        self._events=tuple(sorted(events,key=lambda v:(v.created,v.proposal,v.voter,v.id))) if mode=='A' else ()
        self._cursor=0
        self._applied=set()
        self._batch_count=0
        self._check_events()
        for e in self.environments.values():
            e.update_lifecycle(self.clock)

    def _check_events(self):
        ids,keys=set(),set()
        for v in self._events:
            if v.id in ids or (v.proposal,v.voter) in keys:
                raise InputError('Duplicate retained event or wallet-proposal')
            if v.proposal not in self.environments or v.voter not in self.agents:
                raise InputError('Event FK not present')
            p=self.environments[v.proposal].proposal
            if type(v.created) is not int or type(v.choice) is not int or not p.start<=v.created<=p.end or not 1<=v.choice<=len(p.choices) or v.vp<0 or not v.vp.is_finite():
                raise InputError('Invalid retained event time/choice/VP')
            if len(v.components)!=len(p.strategies):
                raise InputError('Component dimension mismatch')
            from engine import close
            if any(x<0 or not x.is_finite() for x in v.components) or not close(sum(v.components,Decimal(0)),v.vp):
                raise InputError('Invalid VP components')
            ids.add(v.id)
            keys.add((v.proposal,v.voter))

    def advance_before(self,t):
        """Apply all retained events with timestamp strictly <t, atomically per second."""
        if self.mode!='A':
            raise InputError('Behavior scheduling is not implemented in 4.1.1')
        if type(t) is not int or t<self.clock:
            raise InputError('Clock must be monotone integer UTC seconds')
        while self._cursor<len(self._events) and self._events[self._cursor].created<t:
            at=self._events[self._cursor].created
            stop=self._cursor
            while stop<len(self._events) and self._events[stop].created==at:
                stop+=1
            batch=self._events[self._cursor:stop]
            # Validate entire batch before changing any state.
            for v in batch:
                if v.id in self._applied or (v.voter,v.proposal) in self.states:
                    raise InputError('Unexpected replacement/duplicate event')
            with localcontext() as ctx:
                ctx.prec=120
                for v in batch:
                    e=self.environments[v.proposal]
                    e.totals[v.choice-1]+=v.vp  # Total VP once; components are descriptive.
                    e.votes_count+=1
                    self.states[v.voter,v.proposal]=AgentProposalState(v.voter,v.proposal,v.vp,v.components,v.choice,
                                                                      v.created,'OBSERVED_RETAINED_VOTE',
                                                                      'HISTORICAL_RECORD_NOT_NEW_ACTION_CERTIFICATE')
                    self._applied.add(v.id)
            self._cursor=stop
            self._batch_count+=1
        self.clock=t
        for e in self.environments.values():
            e.update_lifecycle(t)

    def agent_view(self,wallet,sid):
        """No future catalog, participation list, rule commit, final outcome, graph or other wallets."""
        wallet=normalize_wallet(wallet)
        if wallet not in self.agents or sid not in self.environments:
            raise InputError('Agent/proposal FK missing')
        e=self.environments[sid]
        if self.clock<e.proposal.start:
            return None
        state=self.states.get((wallet,sid))
        agent=self.agents[wallet]
        return dict(wallet_id=wallet,snapshot_id=sid,clock=self.clock,
                    proposal=dict(choices=list(e.proposal.choices),start=e.proposal.start,end=e.proposal.end,
                                  metadata_release='ASSUMED_AT_START_NOT_HISTORICAL_PUBLICATION_PROOF'),
                    own_state=dict(vp=None if state is None else state.vp,
                                   components=None if state is None else state.components,
                                   choice=None if state is None else state.choice,
                                   known_since=None if state is None else state.known_since,
                                   permission_status='UNVERIFIED' if state is None else state.permission_status),
                    own_role=agent.role,own_budget=agent.account.balances,
                    preferences=agent.preferences,utility_parameters=agent.utility_parameters,
                    new_action_feasibility='UNVERIFIED',
                    public_tally=None,threshold_publication_status='UNVERIFIED_NOT_EXPOSED',
                    eligible_population=None)


def build_world(mode,proposal_inputs,events,wallets,scenario=None,seed=0):
    scenario={} if scenario is None else scenario
    if not isinstance(scenario,dict):
        raise InputError('Scenario must be a JSON object')
    allowed={'scenario_label','owner_map','budgets_by_principal','vp_assignments'}
    if set(scenario)-allowed:
        raise InputError('Unsupported scenario fields; behavioral rules are out of scope')
    if 'scenario_label' in scenario and (not isinstance(scenario['scenario_label'],str) or not scenario['scenario_label']):
        raise InputError('Scenario label must be a nonempty string')
    if not isinstance(scenario.get('vp_assignments',[]),list):
        raise InputError('vp_assignments must be a list')
    if mode=='A' and scenario:
        raise InputError('Replay mode cannot override history or budgets')
    agents,accounts=build_agents(wallets,mode,scenario)
    environments={}
    for p,rule,threshold,flags in proposal_inputs:
        if p.id in environments:
            raise InputError('Duplicate proposal')
        environments[p.id]=ProposalEnvironment(p,rule,number(threshold),dict(flags),snapshot_references(p))
    world=InitializedWorld(mode,agents,accounts,environments,events,seed)
    seen=set()
    for assignment in scenario.get('vp_assignments',[]):
        required={'wallet_id','snapshot_id','vp','components','network','snapshot_block','basis'}
        if not isinstance(assignment,dict) or set(assignment)!=required:
            raise InputError('VP assignment schema mismatch')
        wallet=normalize_wallet(assignment['wallet_id'])
        sid=assignment['snapshot_id']
        key=wallet,sid
        if key in seen or wallet not in agents or sid not in environments:
            raise InputError('Duplicate/invalid VP assignment FK')
        p=environments[sid].proposal
        if str(assignment['network'])!=p.raw['snapshot_network'] or type(assignment['snapshot_block']) is not int or assignment['snapshot_block']!=p.snapshot_block:
            raise InputError('Scenario VP has wrong network or block')
        if assignment['basis']!='SCENARIO_ASSUMPTION':
            raise InputError('Cannot certify unverified scenario VP as empirical eligibility')
        if not isinstance(assignment['components'],list):
            raise InputError('Scenario components must be a list')
        parts=tuple(number(x) for x in assignment['components'])
        vp=number(assignment['vp'])
        from engine import close
        if len(parts)!=len(p.strategies) or not close(sum(parts,Decimal(0)),vp):
            raise InputError('Scenario component mismatch')
        # Private scenario state; never a vote or a social/participation edge.
        world.states[key]=AgentProposalState(wallet,sid,vp,parts,None,p.start,'SCENARIO_ASSUMPTION','UNVERIFIED')
        seen.add(key)
    return world
