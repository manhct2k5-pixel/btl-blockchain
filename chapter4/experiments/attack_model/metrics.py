"""Counts first; no fixture success fraction is an empirical probability."""
from fractions import Fraction as F
from math import ceil,log,sqrt
def summarize(results):
    eligible=[r for r in results if r.get('eligible') is True]
    attempted=[r for r in eligible if r['attempted']]
    known=[r for r in attempted if r['success'] is not None]
    counts=dict(total=len(results),infeasible=sum(r.get('eligible') is False for r in results),
        not_ready=sum(r.get('eligible') is None for r in results),eligible=len(eligible),
        eligible_declined=sum(not r['attempted'] for r in eligible),attempted=len(attempted),
        outcome_known_attempted=len(known),outcome_unknown_attempted=len(attempted)-len(known),
        success=sum(r['success'] is True for r in known),failure=sum(r['success'] is False for r in known))
    return dict(counts=counts,conditional_success_fraction=F(counts['success'],len(known)) if known else None,
        eligible_policy_yield_fraction=F(counts['success'],len(eligible)) if eligible else None,
        unknown_outcome_success_bounds=(F(counts['success'],len(attempted)),F(counts['success']+counts['outcome_unknown_attempted'],len(attempted))) if attempted else None,
        label='SOFTWARE_FIXTURE_ACCOUNTING_NOT_EMPIRICAL_PROBABILITY',confidence_interval=None)
def planned_independent_bernoulli_repeats(half_width='0.02',alpha='0.05'):
    h,a=float(half_width),float(alpha)
    if not 0<h<1 or not 0<a<1:raise ValueError('Bad planned precision')
    # Hoeffding fixed-n bound; design calculation only, no simulation launched.
    return ceil(log(2/a)/(2*h*h))
def wilson_interval(success,n,z=1.959963984540054):
    if n<=0 or not 0<=success<=n:raise ValueError('Need known denominator')
    p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,center-half),min(1,center+half)
