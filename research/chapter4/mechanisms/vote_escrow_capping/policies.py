"""Separate rights/weights/outcomes using the frozen mechanism interfaces."""
from dataclasses import replace
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
sys.path.insert(0,str(WS/'chapter4/mechanisms/quadratic_voting'))
from qv_mechanism import (Ballot,BallotBox,WalletSqrt,StrictBinaryScoreMajority,VARIANT,
    TokenWeighted,HistoricalGovernance,InputError,Decision,exclusion,valid_vp,distribution,show)
from mechanism import WeightContext
from escrow import FrozenEscrow

CAP_ID='WALLET_ABSOLUTE_POST_AGGREGATION_NO_REDISTRIBUTION_V1'
VE_ID='MANA_ONLY_LINEAR_REMAINING_TIME_FROZEN_SNAPSHOT_V1'

def decimal_display(x,precision=120):
    x=F(x)
    with localcontext() as ctx:
        ctx.prec=max(precision,len(str(abs(x.numerator)))+len(str(x.denominator))+5)
        return Decimal(x.numerator)/Decimal(x.denominator)

class CappingWeightPolicy:
    policy_id=CAP_ID
    weight_unit='VP'
    def __init__(self,cap,unit='VP'):
        valid_vp(cap)
        if unit!='VP':raise InputError('Cap and source must both be VP')
        self.cap=cap
    def exact_weight(self,b,context=None):
        valid_vp(b.vp)
        return min(F(b.vp),F(self.cap))
    def weight(self,b,context=None):return decimal_display(self.exact_weight(b,context))

class VoteEscrowWeightPolicy:
    policy_id=VE_ID
    weight_unit='VE_MANA_POINT'
    def __init__(self,snapshot,points_per_mana=F(1),source_vp_per_mana=F(1)):
        if not isinstance(snapshot,FrozenEscrow) or snapshot.evidence!='SYNTHETIC_DECLARED_NOT_CHAIN_DATA':
            raise InputError('Explicit declared synthetic frozen lock state required')
        if snapshot.asset!='MANA' or points_per_mana!=F(1) or source_vp_per_mana!=F(1):
            raise InputError('Version 1 fixes eligible asset and explicit unit mappings')
        if type(snapshot.time) is not int or type(snapshot.max_seconds) is not int or snapshot.max_seconds<=0:
            raise InputError('Invalid frozen time domain')
        if set(snapshot.states)!=set(snapshot.controllers):
            raise InputError('Frozen controller coverage missing')
        positions=[]
        for state in snapshot.states.values():
            if state.locked<0 or state.liquid<0 or state.start>snapshot.time or state.end-snapshot.time>snapshot.max_seconds:
                raise InputError('Invalid frozen lock state')
            if state.locked:
                if not state.position_id:raise InputError('Missing locked position provenance')
                positions.append(state.position_id)
        if len(positions)!=len(set(positions)):raise InputError('One locked position counted for multiple wallets')
        self.snapshot=snapshot
        self.points_per_mana=F(points_per_mana);self.source_vp_per_mana=F(source_vp_per_mana)
    def exact_weight(self,b,context):
        s=self.snapshot
        if context is None or (context.snapshot_id,context.snapshot_network,context.snapshot_block)!=(s.snapshot_id,s.network,s.block):
            raise InputError('Wrong frozen snapshot network/block/proposal')
        if context.as_of<s.time:raise InputError('Cannot use a future lock snapshot')
        if b.wallet_id not in s.states:raise InputError('Unknown asset state is not zero lock')
        state=s.states[b.wallet_id];valid_vp(b.vp)
        # Explicit synthetic resource comparator, never infer token quantity from historical VP.
        if F(b.vp)!=(state.liquid+state.locked)*self.source_vp_per_mana:
            raise InputError('Declared MANA-only reference VP mismatch')
        if state.locked<0 or state.liquid<0 or state.start>s.time or state.end-s.time>s.max_seconds:
            raise InputError('Invalid frozen position')
        return state.locked*F(max(state.end-s.time,0),s.max_seconds)*self.points_per_mana
    def weight(self,b,context):return decimal_display(self.exact_weight(b,context))

class CommonBinaryOutcomePolicy:
    policy_id='HYPOTHETICAL_COMMON_BINARY_STRICT_MAJORITY_NO_QUORUM_V1'
    units={'TOKEN_WEIGHTED_VP_IDENTITY':'VP',VARIANT:'SQRT_CREDIT_POINT',CAP_ID:'VP',VE_ID:'VE_MANA_POINT'}
    def evaluate(self,proposal,totals,count,threshold,rule,weight_policy):
        if not isinstance(threshold,Decimal) or threshold!=0:
            raise InputError('Only zero within-mechanism difference boundary, no historical floor')
        if self.units.get(weight_policy.policy_id)!=weight_policy.weight_unit:
            raise InputError('Unregistered weight/unit mapping')
        if len(totals)!=len(proposal.choices) or any(not isinstance(v,Decimal) or not v.is_finite() or v<0 for v in totals):
            raise InputError('Invalid display totals')
        reason=exclusion(proposal,rule)
        return Decision('UNASSESSED_SEMANTICS' if reason else 'UNASSESSED_REQUIRES_EXACT_CERTIFICATE',
                        '',Decimal(0),Decimal(0),reason or 'EXACT_BALLOT_CERTIFICATE_REQUIRED',False)
    def certify(self,proposal,rule,ballots,weight_policy,context):
        reason=exclusion(proposal,rule)
        if reason:return 'UNASSESSED_SEMANTICS',reason,{'method':'PRE_OUTCOME_METADATA_SCREEN'}
        if weight_policy.policy_id==VARIANT:
            return StrictBinaryScoreMajority().certify(proposal,rule,ballots)
        def w(b):
            return F(b.vp) if weight_policy.policy_id=='TOKEN_WEIGHTED_VP_IDENTITY' else weight_policy.exact_weight(b,context)
        gap=sum((w(b) if b.choice==1 else -w(b) for b in ballots),F(0))
        return ('ACCEPTED' if gap>0 else 'REJECTED'),'',{'method':'EXACT_RATIONAL_SIGN','gap':str(gap)}

class CommonBox(BallotBox):
    def __init__(self,proposal,rule,origin,policy,flags=None,allow_assumed_rights=False):
        super().__init__(proposal,rule,Decimal(0),origin,flags,allow_assumed_rights,policy,CommonBinaryOutcomePolicy())
        if policy.policy_id==VE_ID:
            if origin!='SCENARIO_ASSUMED' or policy.snapshot.time!=proposal.block_timestamp:
                raise InputError('VE requires matching declared asset snapshot, not historical total VP')
        self.certificate=None;self.exclusion_reason=None
    def _validate(self,b,as_of):
        if self.origin!='SCENARIO_ASSUMED':return super()._validate(b,as_of)
        valid_vp(b.vp)
        if not isinstance(b.components,tuple):raise InputError('Components must be tuple')
        for x in b.components:valid_vp(x)
        if sum((F(x) for x in b.components),F(0))!=F(b.vp):raise InputError('Component mismatch')
        super()._validate(replace(b,vp=Decimal(0),components=tuple(Decimal(0) for _ in b.components)),as_of)
    def context(self,as_of):
        return WeightContext(self.proposal.id,as_of,self.proposal.raw['snapshot_network'],self.proposal.snapshot_block,dict(self.flags))
    def exact_weights(self,as_of):
        if self.weight_policy.policy_id==VARIANT:raise InputError('QV uses radical certificate, not rational weights')
        return [F(b.vp) if self.weight_policy.policy_id=='TOKEN_WEIGHTED_VP_IDENTITY'
            else self.weight_policy.exact_weight(b,self.context(as_of)) for b in self.ballots]
    def evaluate(self,as_of):
        result=super().evaluate(as_of)  # preserves timing validation and provenance checks
        outcome,reason,certificate=self.outcome_policy.certify(self.proposal,self.rule,self.ballots,self.weight_policy,self.context(as_of))
        self.certificate,self.exclusion_reason=certificate,reason
        totals=result.option_weights;total=result.total_effective_weight
        if self.weight_policy.policy_id!=VARIANT:
            weights=self.exact_weights(as_of)
            totals=tuple(decimal_display(sum((w for b,w in zip(self.ballots,weights) if b.choice==i+1),F(0)))
                         for i in range(len(self.proposal.choices)))
            total=decimal_display(sum(weights,F(0)))
        source=decimal_display(sum((F(b.vp) for b in self.ballots),F(0)))
        winner='' if outcome.startswith('UNASSESSED') else self.proposal.choices[0 if outcome=='ACCEPTED' else 1]
        return replace(result,option_weights=totals,total_source_vp=source,total_effective_weight=total,
            outcome=outcome,winner_label=winner,winner_weight=Decimal(0) if not winner else totals[0 if outcome=='ACCEPTED' else 1],
            data_status='DECLARED_MECHANICAL_COUNTERFACTUAL_NOT_PRODUCTION',
            flags={**result.flags,'exclusion_reason':reason,'numeric_certificate':certificate,
                'identity_verified':False,'strategic_response_modelled':False})

def aggregate_delegated_sources(sources,assignments):
    """Synthetic source-ID routing: each original source assigned once, recipient cap after sum.

    Not an implementation of Decentraland delegation. No chains/recursive reassignment.
    """
    if set(sources)!=set(assignments):raise InputError('Every source assigned exactly once')
    from model import normalize_wallet
    out={}
    for source,vp in sources.items():
        valid_vp(vp);recipient=assignments[source]
        if normalize_wallet(recipient)!=recipient:raise InputError('Canonical recipient required')
        out[recipient]=out.get(recipient,F(0))+F(vp)
    assert sum(out.values(),F(0))==sum((F(x) for x in sources.values()),F(0))
    return out
