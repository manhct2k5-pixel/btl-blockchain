"""main_metrics.py: Formal Level-A statistical metrics, 4 explicit estimands,
correct denominators, Wilson score intervals, financial/utility cost separation,
and cluster bootstrap paired differences.
"""
from collections import defaultdict
from fractions import Fraction as F
from math import sqrt
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]
sys.path.insert(0, str(WS / 'chapter4/experiments/attack_model'))
from metrics import wilson_interval

def ratio(k, n):
    return None if n == 0 else k / n

def interval(k, n):
    return None if n == 0 else list(wilson_interval(k, n))

def describe(values):
    a = [float(x) for x in values if x is not None]
    if not a:
        return dict(n=0, mean=None, sd=None, min=None, max=None)
    mean = sum(a) / len(a)
    return dict(
        n=len(a),
        mean=mean,
        sd=sqrt(sum((x - mean) ** 2 for x in a) / (len(a) - 1)) if len(a) > 1 else None,
        min=min(a),
        max=max(a)
    )

def summarize(rows):
    eligible = [r for r in rows if r.get('eligible') is True]
    attempted = [r for r in eligible if r['attempted']]
    declined = [r for r in eligible if not r['attempted']]
    known = [r for r in attempted if r['success'] is not None]
    unknown = len(attempted) - len(known)

    # Classification by baseline outcome
    baseline_acc_attempted = [r for r in known if (r.get('no_attack') or {}).get('outcome') == 'ACCEPTED']
    baseline_rej_attempted = [r for r in known if (r.get('no_attack') or {}).get('outcome') == 'REJECTED']

    # Flips: REJECTED baseline changed to ACCEPTED
    flips = [r for r in baseline_rej_attempted if r['success'] is True]
    successes = len(flips)
    failures = sum(r['success'] is False for r in known)

    count = dict(
        worlds=len(rows),
        eligible=len(eligible),
        infeasible=sum(r.get('eligible') is False for r in rows),
        not_ready=sum(r.get('eligible') is None for r in rows),
        declined=len(declined),
        attempted=len(attempted),
        known_attempted=len(known),
        unknown_outcome=unknown,
        baseline_accepted_attempted=len(baseline_acc_attempted),
        baseline_rejected_attempted=len(baseline_rej_attempted),
        flip_successes=successes,
        failures=failures
    )

    # ESTIMAND 1: Eligible Policy Success Rate (Denominator = eligible)
    e1_fraction = ratio(successes, len(eligible))
    e1_wilson = interval(successes, len(eligible))

    # ESTIMAND 2: Attempted Success Rate (Denominator = known_attempted)
    e2_fraction = ratio(successes, len(known))
    e2_wilson = interval(successes, len(known))

    # ESTIMAND 3: Conditional Flip Success Rate (Denominator = baseline_rejected_attempted)
    e3_fraction = ratio(successes, len(baseline_rej_attempted))
    e3_wilson = interval(successes, len(baseline_rej_attempted))

    # ESTIMAND 4: Target Already Satisfied Rate (Denominator = known_attempted)
    e4_count = len(baseline_acc_attempted)
    e4_fraction = ratio(e4_count, len(known))
    e4_wilson = interval(e4_count, len(known))

    # Financial and Utility Cost Accounting
    cost_rows = [r for r in rows if 'resources' in r]
    accounts = [r['resources']['attacker'] for r in cost_rows]

    # Partition costs by success, failure, declined
    success_rows = [r for r in known if r['success'] is True]
    failure_rows = [r for r in known if r['success'] is False]

    def cost_breakdown(subrows):
        if not subrows:
            return dict(n=0, total_cash_expense='0', mean_cash_expense='0',
                        total_paid='0', total_fees='0', total_refunded='0',
                        total_opportunity_utility='0', total_capital_utility='0')
        sub_acc = [r['resources']['attacker'] for r in subrows]
        tot_cash = sum((F(r.get('net_cash_expense', 0)) for r in subrows), F(0))
        tot_paid = sum((F(a['paid']) for a in sub_acc), F(0))
        tot_fees = sum((F(a['external_fees']) for a in sub_acc), F(0))
        tot_ref = sum((F(a['refund']) for a in sub_acc), F(0))
        tot_opp = sum((F(r.get('opportunity_cost_utility', 0)) for r in subrows), F(0))
        tot_cap = sum((F(r.get('capital_cost_utility', 0)) for r in subrows), F(0))
        return dict(
            n=len(subrows),
            total_cash_expense=str(tot_cash),
            mean_cash_expense=str(float(tot_cash / len(subrows))),
            total_paid=str(tot_paid),
            total_fees=str(tot_fees),
            total_refunded=str(tot_ref),
            total_opportunity_utility=str(tot_opp),
            total_capital_utility=str(tot_cap)
        )

    costs = dict(
        known_worlds=len(cost_rows),
        money_unit='TEST_COIN',
        total_paid=str(sum((F(a['paid']) for a in accounts), F(0))),
        total_external_fees=str(sum((F(a['external_fees']) for a in accounts), F(0))),
        maximum_peak_escrow=str(max((F(a['peak_escrow']) for a in accounts), default=F(0))),
        total_refunded=str(sum((F(a['refund']) for a in accounts), F(0))),
        total_cash_expense=str(sum((F(r.get('net_cash_expense', 0)) for r in cost_rows), F(0))),
        total_opportunity_utility=str(sum((F(r.get('opportunity_cost_utility', 0)) for r in attempted), F(0))),
        total_capital_utility=str(sum((F(r.get('capital_cost_utility', 0)) for r in attempted), F(0))),
        by_outcome=dict(
            success=cost_breakdown(success_rows),
            failure=cost_breakdown(failure_rows),
            declined=cost_breakdown(declined)
        )
    )

    times = {k: describe([r.get(k) for r in attempted]) for k in
             ('time_to_decision', 'time_to_action_completion', 'time_to_final_evaluation')}

    return dict(
        counts=count,
        estimand_1_eligible_policy_success=dict(k=successes, n=len(eligible), fraction=e1_fraction, wilson95=e1_wilson),
        estimand_2_attempted_success=dict(k=successes, n=len(known), fraction=e2_fraction, wilson95=e2_wilson),
        estimand_3_conditional_flip_success=dict(k=successes, n=len(baseline_rej_attempted), fraction=e3_fraction, wilson95=e3_wilson),
        estimand_4_target_already_satisfied=dict(k=e4_count, n=len(known), fraction=e4_fraction, wilson95=e4_wilson),
        costs=costs,
        times=times,
        effective_concentration={
            k: describe([(r.get('with_attack') or {}).get(k) or None for r in rows])
            for k in ('wallet_gini', 'wallet_hhi', 'controller_gini', 'controller_hhi')
        },
        eligible_source_vp=describe([(r.get('with_attack') or {}).get('source_vp') for r in rows]),
        uncertainty='Monte Carlo sampling variation under frozen synthetic Level-A assumptions; not empirical DAO probability'
    )

def paired_bootstrap_ci(diffs, iterations=10000, seed=4302027):
    if not diffs:
        return None
    if all(d == 0 for d in diffs):
        return [0.0, 0.0]
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(iterations):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low = means[int(0.025 * iterations)]
    high = means[int(0.975 * iterations)]
    return [low, high]

def paired(rows, first, second, family=None):
    selected = [r for r in rows if r['group'] == 'MAIN' and (family is None or r['family'] == family)]
    indexed = defaultdict(dict)
    for r in selected:
        indexed[r['world_id']][r['mechanism']] = r
    pairs = [(d[first], d[second]) for d in indexed.values() if first in d and second in d]

    eligible = [(a, b) for a, b in pairs if a.get('eligible') is True and b.get('eligible') is True
                and a['policy_success'] is not None and b['policy_success'] is not None]
    attempted = [(a, b) for a, b in eligible if a['attempted'] and b['attempted']]

    def differences(ps, bootstrap_seed_offset=0):
        if not ps:
            return dict(n=0, mean=None, second_only=0, first_only=0, both_success=0, neither_success=0,
                        contingency_table={'11': 0, '10': 0, '01': 0, '00': 0}, bootstrap_95ci=None)
        diffs = [int(b['policy_success']) - int(a['policy_success']) for a, b in ps]
        n = len(ps)
        mean_diff = sum(diffs) / n
        second_only = sum(x == 1 for x in diffs)   # b succeeded, a failed
        first_only = sum(x == -1 for x in diffs)  # a succeeded, b failed
        both = sum(a['policy_success'] and b['policy_success'] for a, b in ps)
        neither = sum(not a['policy_success'] and not b['policy_success'] for a, b in ps)
        ci = paired_bootstrap_ci(diffs, iterations=10000, seed=4302027 + bootstrap_seed_offset)
        return dict(
            n=n,
            mean=mean_diff,
            second_only=second_only,
            first_only=first_only,
            both_success=both,
            neither_success=neither,
            contingency_table={
                '11_both_succeeded': both,
                '10_first_only': first_only,
                '01_second_only': second_only,
                '00_neither_succeeded': neither
            },
            bootstrap_95ci=ci
        )

    return dict(
        first=first,
        second=second,
        family=family or 'ALL',
        generated_pairs=len(pairs),
        direction='SECOND_MINUS_FIRST',
        primary_eligible_policy_difference=differences(eligible, 100),
        common_attempted_difference=differences(attempted, 200),
        independent_sample_ci_used=False,
        paired_method='World-level cluster bootstrap (10,000 iterations); discordant pair accounting'
    )
