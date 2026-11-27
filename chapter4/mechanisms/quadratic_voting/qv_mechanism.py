"""Restricted single-choice wallet square-root weighting, not full classical QV."""
from __future__ import annotations
from collections import Counter
from dataclasses import replace
from decimal import Decimal,localcontext
from fractions import Fraction as F
from functools import lru_cache
from math import isqrt
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
sys.path.insert(0,str(WS/'chapter4/mechanisms/token_weighted'))
from mechanism import Ballot,BallotBox,TokenWeighted,HistoricalGovernance,distribution,show
from engine import InputError,Decision

VARIANT='WALLET_SQRT_SINGLE_CHOICE_V1'
UNIT='SQRT_CREDIT_POINT'
ALLOWED_FAMILIES={'threshold','invalid_votes','invalid_scores'}

def exclusion(proposal,rule):
    # Determined from metadata/rule semantics, before any scores/outcome are inspected.
    reasons=[]
    if tuple(c.strip().lower() for c in proposal.choices)!=('yes','no'):
        reasons.append('NON_BINARY_YES_NO_SEMANTICS')
    if rule.family not in ALLOWED_FAMILIES:
        reasons.append('SPECIAL_OR_UNVERIFIED_HISTORICAL_RULE_FAMILY')
    return ';'.join(reasons)

def valid_vp(x):
    if not isinstance(x,Decimal) or not x.is_finite() or x<0:
        raise InputError('Source must be nonnegative finite Decimal VP')

@lru_cache(maxsize=100000)
def root_display(x):
    valid_vp(x)
    with localcontext() as ctx:
        ctx.prec=100
        return x.sqrt()

class WalletSqrt:
    policy_id=VARIANT
    weight_unit=UNIT
    def __init__(self,reference_vp=Decimal(1),source_unit='VP'):
        if reference_vp!=Decimal(1) or not isinstance(reference_vp,Decimal) or source_unit!='VP':
            raise InputError('Version 1 fixes the reference at exactly 1 VP; no implicit unit conversion')
    def weight(self,ballot,context=None):
        return root_display(ballot.vp)

def square_root_rational(x):
    a,b=isqrt(x.numerator),isqrt(x.denominator)
    return F(a,b) if a*a==x.numerator and b*b==x.denominator else None

@lru_cache(maxsize=200000)
def root_interval(x,digits):
    """Exact rational enclosure on an absolute 10^-digits grid; no binary floats."""
    if x<0: raise InputError('Negative radicand')
    scale=10**digits
    n=isqrt((x.numerator*scale*scale)//x.denominator)
    lo=F(n,scale)
    exact=n*n*x.denominator==x.numerator*scale*scale
    return lo,lo if exact else F(n+1,scale)

def radical_sign(terms,max_digits=320):
    """Sign of sum coefficient*sqrt(rational), with certified intervals/exact cancellation.

    Returns (sign or None, certificate). Never interprets a tolerance as equality.
    The expensive proportional-radical grouping is used only if bounds overlap.
    """
    c=Counter()
    for coeff,x in terms:
        x=F(x)
        if x<0: raise InputError('Negative radicand')
        if x: c[x]+=F(coeff)
    c={x:v for x,v in c.items() if v}
    if not c: return 0,{'method':'EXACT_IDENTICAL_TERM_CANCELLATION','digits':0}
    for digits in (40,80,160,320):
        if digits>max_digits: break
        lo=hi=F(0)
        for x,v in c.items():
            a,b=root_interval(x,digits)
            lo+=v*(a if v>0 else b)
            hi+=v*(b if v>0 else a)
        if lo>0: return 1,{'method':'RATIONAL_INTERVAL','digits':digits}
        if hi<0: return -1,{'method':'RATIONAL_INTERVAL','digits':digits}
        if lo==hi==0: return 0,{'method':'EXACT_RATIONAL_ROOTS','digits':digits}
    groups={}
    for x,v in sorted(c.items()):
        for representative in groups:
            ratio=square_root_rational(x/representative)
            if ratio is not None:
                groups[representative]+=v*ratio
                break
        else: groups[x]=v
    if all(v==0 for v in groups.values()):
        return 0,{'method':'EXACT_PROPORTIONAL_RADICAL_CANCELLATION','digits':0}
    return None,{'method':'UNRESOLVED_AT_DECLARED_PRECISION_LIMIT','digits':max_digits}

class StrictBinaryScoreMajority:
    """Declared experiment: Yes strictly exceeds No; no quorum, no absolute floor.

    threshold is the zero difference boundary in score points, never the old VP floor.
    Rounded totals alone are deliberately insufficient for a certified QV decision.
    """
    policy_id='HYPOTHETICAL_BINARY_STRICT_SCORE_MAJORITY_NO_QUORUM_V1'
    def evaluate(self,proposal,totals,count,threshold,rule,weight_policy):
        if threshold!=Decimal(0):
            raise InputError('New policy requires explicit zero score-difference threshold')
        if (weight_policy.policy_id,weight_policy.weight_unit)!=(VARIANT,UNIT):
            raise InputError('Unsupported weighting/unit for QV outcome policy')
        reason=exclusion(proposal,rule)
        return Decision('UNASSESSED_SEMANTICS' if reason else 'UNASSESSED_REQUIRES_RADICAL_CERTIFICATE',
                        '',Decimal(0),Decimal(0),reason or 'NO_DECISION_FROM_ROUNDED_TOTALS',False)
    def certify(self,proposal,rule,ballots):
        reason=exclusion(proposal,rule)
        if reason: return 'UNASSESSED_SEMANTICS',reason,{'method':'PRE_OUTCOME_EXCLUSION'}
        terms=[(1 if b.choice==1 else -1,F(b.vp)) for b in ballots]
        sign,cert=radical_sign(terms)
        if sign is None: return 'UNASSESSED_NUMERIC','NUMERIC_CERTIFICATION_UNRESOLVED',cert
        # Empty/all-zero/tied ballots reject under this explicit experimental rule.
        return ('ACCEPTED' if sign>0 else 'REJECTED'),'',cert

class QVBox(BallotBox):
    def __init__(self,proposal,rule,origin,flags=None,allow_assumed_rights=False):
        super().__init__(proposal,rule,Decimal(0),origin,flags,allow_assumed_rights,
                         WalletSqrt(),StrictBinaryScoreMajority())
        self.numeric_certificate=None
        self.exclusion_reason=None
    def _validate(self,b,as_of):
        if self.origin!='SCENARIO_ASSUMED':
            return super()._validate(b,as_of)
        # Parent's metadata/permission checks are reused. Its fixed 120-digit
        # component sum cannot represent arbitrary finite scenario decimals.
        # Check original numerical fields exactly first, then validate all other
        # fields with a zero-valued copy. The stored ballot remains the original.
        valid_vp(b.vp)
        if not isinstance(b.components,tuple): raise InputError('Components must be tuple')
        for x in b.components: valid_vp(x)
        if sum((F(x) for x in b.components),F(0))!=F(b.vp):
            raise InputError('Exact scenario component mismatch')
        super()._validate(replace(b,vp=Decimal(0),components=tuple(Decimal(0) for _ in b.components)),as_of)
    def evaluate(self,as_of):
        result=super().evaluate(as_of)
        outcome,reason,cert=self.outcome_policy.certify(self.proposal,self.rule,self.ballots)
        self.numeric_certificate=cert
        self.exclusion_reason=reason
        winner='' if outcome.startswith('UNASSESSED') else self.proposal.choices[0 if outcome=='ACCEPTED' else 1]
        weight=Decimal(0) if not winner else result.option_weights[0 if outcome=='ACCEPTED' else 1]
        raw=sum((F(b.vp) for b in self.ballots),F(0))
        with localcontext() as ctx:
            ctx.prec=max(120,len(str(abs(raw.numerator)))+len(str(raw.denominator))+5)
            raw_decimal=Decimal(raw.numerator)/Decimal(raw.denominator)
        return replace(result,outcome=outcome,winner_label=winner,winner_weight=weight,total_source_vp=raw_decimal,
                       data_status='HYPOTHETICAL_MECHANICAL_COUNTERFACTUAL_NOT_REAL_DAO_QV',
                       flags={**result.flags,'qv_exclusion_reason':reason,'numeric_certificate':cert,
                              'identity_verified':False,'sybil_resistance_assumed':False})

def common_policy_raw(proposal,rule,ballots):
    if exclusion(proposal,rule): return 'UNASSESSED_SEMANTICS'
    gap=sum((F(b.vp) if b.choice==1 else -F(b.vp) for b in ballots),F(0))
    return 'ACCEPTED' if gap>0 else 'REJECTED'

def score_distribution(ballots):
    """100 significant digit descriptive approximations on retained wallets, including zeros."""
    return distribution([root_display(b.vp) for b in ballots])
