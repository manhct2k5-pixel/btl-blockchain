"""Final-ballot mechanism. Identity VP weighting and archived Governance are separate."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
from typing import Protocol
import sys

ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
sys.path.insert(0,str(WS/'baseline'))
from engine import InputError,UnknownRule,Proposal,Rule,govern,close
sys.path.insert(0,str(WS/'chapter4/initialization'))
from model import normalize_wallet


class WeightPolicy(Protocol):
    policy_id: str
    weight_unit: str
    def weight(self,ballot:'Ballot',context:'WeightContext') -> Decimal: ...


@dataclass(frozen=True)
class WeightContext:
    snapshot_id: str
    as_of: int
    snapshot_network: str
    snapshot_block: int
    evidence_flags: dict


class OutcomePolicy(Protocol):
    policy_id: str
    def evaluate(self,proposal,totals,count,threshold,rule,weight_policy): ...


class TokenWeighted:
    policy_id='TOKEN_WEIGHTED_VP_IDENTITY'
    weight_unit='VP'
    def weight(self,ballot,context=None):
        return ballot.vp


class HistoricalGovernance:
    policy_id='ARCHIVED_CANDIDATE_GOVERNANCE'
    def evaluate(self,proposal,totals,count,threshold,rule,weight_policy):
        if (weight_policy.policy_id,weight_policy.weight_unit)!=('TOKEN_WEIGHTED_VP_IDENTITY','VP'):
            raise InputError('Outcome/threshold compatibility for another weight policy is not verified')
        with localcontext() as ctx:
            ctx.prec=120
            return govern(proposal.choices,list(totals),count,threshold,rule)


@dataclass(frozen=True)
class Ballot:
    snapshot_id: str
    wallet_id: str
    choice: int
    vp: Decimal
    components: tuple[Decimal,...]
    created: int
    vote_id: str
    network: str
    snapshot_block: int
    origin: str
    permission_basis: str
    source_ref: str
    vp_state: str = 'final'
    physical_rights_verified: bool = False


@dataclass(frozen=True)
class MechanismResult:
    snapshot_id: str
    option_weights: tuple[Decimal,...]
    vote_count: int
    total_source_vp: Decimal
    total_effective_weight: Decimal
    outcome: str
    winner_label: str
    winner_weight: Decimal
    threshold: Decimal
    weight_policy_id: str
    weight_unit: str
    outcome_policy_id: str
    data_status: str
    as_of: int
    flags: dict
    execution_status: str = 'UNKNOWN_NOT_INFERRED_FROM_OUTCOME'


class BallotBox:
    """One current ballot per wallet/proposal. Invalid batches fail atomically."""
    def __init__(self,proposal:Proposal,rule:Rule,threshold:Decimal,origin:str,
                 flags=None,allow_assumed_rights=False,weight_policy=None,outcome_policy=None):
        if origin not in ('HISTORICAL_RETAINED','SCENARIO_ASSUMED'):
            raise InputError('Ballot origin must be explicit')
        if not isinstance(threshold,Decimal) or not threshold.is_finite() or threshold<0:
            raise InputError('Invalid threshold')
        if not proposal.choices or not proposal.raw.get('snapshot_network','').isdigit() or proposal.snapshot_block<=0:
            raise InputError('Proposal choice/network/block invalid')
        if proposal.block_timestamp is None or proposal.block_timestamp>proposal.created:
            raise InputError('Primary snapshot timing not verified for this scope')
        if rule is None or rule.commit_timestamp>proposal.end:
            raise InputError('Missing/future rule')
        self.proposal,self.rule,self.threshold,self.origin=proposal,rule,threshold,origin
        if type(allow_assumed_rights) is not bool:
            raise InputError('Assumed-right policy must be boolean')
        self.flags=dict(flags or {})
        self.allow_assumed_rights=allow_assumed_rights
        self.weight_policy=weight_policy or TokenWeighted()
        self.outcome_policy=outcome_policy or HistoricalGovernance()
        self._ballots={}
        self._seen_ids=set()
        self._last_commit=None
        self.replacement_count=0
        # No result is published to an agent. This is an administrative compatibility check.
        self.outcome_policy.evaluate(proposal,[Decimal(0)]*len(proposal.choices),0,threshold,rule,self.weight_policy)

    @property
    def ballots(self):
        return tuple(self._ballots[w] for w in sorted(self._ballots))

    def _validate(self,b,as_of):
        p=self.proposal
        if b.snapshot_id!=p.id or normalize_wallet(b.wallet_id)!=b.wallet_id:
            raise InputError('Ballot proposal/wallet mismatch')
        if type(b.choice) is not int or not 1<=b.choice<=len(p.choices):
            raise InputError('Choice outside metadata')
        if type(b.created) is not int or not p.start<=b.created<=p.end or b.created>as_of:
            raise InputError('Ballot outside voting time or from future')
        if b.network!=p.raw['snapshot_network'] or type(b.snapshot_block) is not int or b.snapshot_block!=p.snapshot_block:
            raise InputError('Ballot network/block mismatch')
        if not b.vote_id or not b.source_ref or b.vp_state!='final':
            raise InputError('Missing source/final ballot evidence')
        if b.origin!=self.origin or b.physical_rights_verified:
            raise InputError('Mixed origins or unsupported physical-right certification')
        if not isinstance(b.components,tuple):
            raise InputError('Components must be a tuple')
        values=(b.vp,*b.components)
        if len(b.components)!=len(p.strategies) or any(
                not isinstance(x,Decimal) or not x.is_finite() or x<0 for x in values):
            raise InputError('Invalid nonnegative finite VP/components')
        with localcontext() as ctx:
            ctx.prec=120
            if self.origin=='HISTORICAL_RETAINED':
                if b.permission_basis!='OBSERVED_RETAINED_RECORD' or not close(sum(b.components,Decimal(0)),b.vp):
                    raise InputError('Historical provenance/component mismatch')
            else:
                if not self.allow_assumed_rights or b.permission_basis!='SCENARIO_GRANTED' or sum(b.components,Decimal(0))!=b.vp:
                    raise InputError('Scenario rights not granted/enabled or component mismatch')

    def commit(self,ballots,as_of,replace=False):
        if type(as_of) is not int or self._last_commit is not None and as_of<self._last_commit:
            raise InputError('Commit clock moved backwards')
        incoming=list(ballots)
        staged=dict(self._ballots)
        seen=set(self._seen_ids)
        batch_wallets=set()
        replacement_count=0
        for b in incoming:
            self._validate(b,as_of)
            if b.wallet_id in batch_wallets or b.vote_id in seen:
                raise InputError('Duplicate wallet in batch or repeated ballot version')
            old=staged.get(b.wallet_id)
            if old is not None:
                if not replace or self.origin=='HISTORICAL_RETAINED' or b.created<=old.created or b.vp!=old.vp or b.components!=old.components:
                    raise InputError('Replacement not allowed/newer or snapshot VP changed')
                replacement_count+=1
            batch_wallets.add(b.wallet_id)
            seen.add(b.vote_id)
            staged[b.wallet_id]=b
        self._ballots,self._seen_ids=staged,seen
        self._last_commit=as_of
        self.replacement_count+=replacement_count

    def evaluate(self,as_of):
        if type(as_of) is not int or any(b.created>as_of for b in self._ballots.values()):
            raise InputError('Requested tally would use future ballots')
        with localcontext() as ctx:
            ctx.prec=120
            totals=[Decimal(0)]*len(self.proposal.choices)
            total_source=Decimal(0)
            context=WeightContext(self.proposal.id,as_of,self.proposal.raw['snapshot_network'],
                                  self.proposal.snapshot_block,dict(self.flags))
            for b in self.ballots:
                weight=self.weight_policy.weight(b,context)
                if not isinstance(weight,Decimal) or not weight.is_finite() or weight<0:
                    raise InputError('Invalid effective weight')
                if self.weight_policy.policy_id=='TOKEN_WEIGHTED_VP_IDENTITY' and weight!=b.vp:
                    raise InputError('Token identity policy cannot alter source VP')
                totals[b.choice-1]+=weight
                total_source+=b.vp
            decision=self.outcome_policy.evaluate(self.proposal,totals,len(self._ballots),self.threshold,self.rule,self.weight_policy)
            return MechanismResult(self.proposal.id,tuple(totals),len(self._ballots),total_source,sum(totals,Decimal(0)),
                decision.outcome,decision.winner,decision.winner_vp,self.threshold,self.weight_policy.policy_id,
                self.weight_policy.weight_unit,self.outcome_policy.policy_id,
                'CLOSED_COMPUTED_CANDIDATE' if as_of>self.proposal.end else 'OPEN_ADMINISTRATIVE_COUNTERFACTUAL_NOT_AGENT_SIGNAL',
                as_of,dict(self.flags))


def distribution(weights):
    """Source VP per participating wallet; not eligible population or attack probability."""
    a=sorted(F(w) for w in weights)
    n,total=len(a),sum(a,F(0))
    def quantile(p):
        if not a: return None
        x=(n-1)*p
        i=x.numerator//x.denominator
        return a[i] if i==n-1 else a[i]+(a[i+1]-a[i])*(x-i)
    result=dict(voters=n,positive_vp_voters=sum(w>0 for w in a),total_vp=total,
        vp_min=min(a) if a else None,vp_q25=quantile(F(1,4)),vp_median=quantile(F(1,2)),vp_q75=quantile(F(3,4)),
        vp_max=max(a) if a else None,gini=None,hhi=None,top1_share=None,top5_share=None,top10_share=None)
    if total>0:
        result.update(gini=2*sum((i+1)*w for i,w in enumerate(a))/(n*total)-F(n+1,n),
            hhi=sum((w/total)**2 for w in a),top1_share=a[-1]/total,
            top5_share=sum(a[-5:])/total,top10_share=sum(a[-10:])/total)
    return result


def show(value):
    if value is None: return ''
    if isinstance(value,F):
        with localcontext() as ctx:
            ctx.prec=40
            return format(Decimal(value.numerator)/Decimal(value.denominator),'f')
    return format(value,'f') if isinstance(value,Decimal) else value
