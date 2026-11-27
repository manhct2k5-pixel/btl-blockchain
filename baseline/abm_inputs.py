"""Replay inputs and descriptive training-only estimates; no behavioral model."""
import bisect
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from engine import ZERO


def phase(end: int, cohort: str) -> str:
    if cohort != 'historical':
        return 'recent_tally_only'
    if end < 1640995200:
        return 'development'
    if end < 1672531200:
        return 'validation'
    return 'final_historical'


def strict_history(votes):
    by_wallet = defaultdict(list)
    for v in votes:
        by_wallet[v.voter].append(v.created)
    for times in by_wallet.values():
        times.sort()
    return {v.id: bisect.bisect_left(by_wallet[v.voter], v.created) for v in votes}


def distribution(vps):
    values = sorted(float(x) for x in vps)
    total, count = math.fsum(values), len(values)
    if count == 0 or total == 0:
        return {'gini_participants': None, 'hhi_participants': None, 'top1_share': None, 'top5_share': None}
    return {'gini_participants': 2*math.fsum((i+1)*x for i, x in enumerate(values))/(count*total)-(count+1)/count,
            'hhi_participants': math.fsum((x/total)**2 for x in values),
            'top1_share': values[-1]/total, 'top5_share': math.fsum(values[-5:])/total}


def quantile(values, q):
    values = sorted(values)
    if not values:
        return None
    i = (len(values)-1)*q
    lo, hi = math.floor(i), math.ceil(i)
    return values[lo]*(hi-i)+values[hi]*(i-lo) if hi != lo else values[lo]


def training_vote_sample(tallies, validation_by_id):
    ids = {sid for sid, r in validation_by_id.items()
           if r['level_b_eligible_pre_outcome'] and r['phase'] == 'development'}
    return ids, [v for sid in ids for v in tallies[sid].votes]


def export_inputs(output: Path, proposals, tallies, validation, write_csv):
    folder = output/'abm_inputs'
    folder.mkdir(exist_ok=True)
    vr = {r['snapshot_id']: r for r in validation}
    c_ids = {sid for sid, r in vr.items() if r['level_c_source_selected']}
    # History uses all retained historical votes before each instant, not future C membership.
    historical_votes = [v for sid, t in tallies.items()
                        if proposals[sid].raw['cohort'] == 'historical' for v in t.votes]
    history = strict_history(historical_votes)
    agents = {}
    events, components, features, rule_rows = [], [], [], []
    for sid in sorted(c_ids):
        p, t, check = proposals[sid], tallies[sid], vr[sid]
        ph = phase(p.end, p.raw['cohort'])
        rule_rows.append({'snapshot_id': sid, 'proposal_type': p.raw['governance_type'],
                          'choices_json': json.dumps(p.choices, ensure_ascii=False),
                          'snapshot_block': p.snapshot_block, 'start': p.start, 'end': p.end,
                          'candidate_rule_commit': check['candidate_rule_commit'],
                          'candidate_rule_family': check['candidate_rule_family'],
                          'threshold': check['threshold_effective'],
                          'has_unverified_default_constant': check['default_dependency_gap'],
                          'deployment_verified': False, 'phase': ph,
                          'selection_uses_official_outcome': True,
                          'source_raw_file': p.raw['source_raw_file']})
        for v in sorted(t.votes, key=lambda x: (x.created, x.id)):
            agents.setdefault(v.voter, {'agent_id': v.voter, 'identity_unit': 'wallet_not_person',
                                       'universe': 'participants_in_outcome_selected_C',
                                       'eligible_nonvoters_known': False})
            delegated = ZERO
            for index, (strategy, amount) in enumerate(zip(p.strategies, v.components)):
                if strategy.get('name') == 'delegation':
                    delegated += amount
                components.append({'vote_id': v.id, 'snapshot_id': sid, 'agent_id': v.voter,
                                   'strategy_index': index, 'strategy_name': strategy.get('name', ''),
                                   'strategy_symbol': strategy.get('params', {}).get('symbol', ''),
                                   'network': strategy.get('network', p.raw['snapshot_network']),
                                   'vp_component': amount, 'component_is_additional_to_total': False,
                                   'source_raw_file': v.source_file})
            events.append({'vote_id': v.id, 'snapshot_id': sid, 'agent_id': v.voter,
                           'vp': v.vp, 'delegated_vp_component': delegated,
                           'choice_index': v.choice, 'choice_label': p.choices[v.choice-1],
                           'created': v.created, 'elapsed_seconds': v.created-p.start,
                           'normalized_delay': (v.created-p.start)/(p.end-p.start),
                           'prior_retained_votes_strictly_before': history[v.id],
                           'proposal_type': p.raw['governance_type'], 'phase': ph,
                           'observation_role': 'retained_vote_replay_not_ex_ante_decision',
                           'source_raw_file': v.source_file})
        features.append({'snapshot_id': sid, 'phase': ph, 'observed_voters': len(t.votes),
                         'observed_used_vp': t.total, **distribution(v.vp for v in t.votes),
                         'eligible_wallet_count': '', 'eligible_vp': '', 'population_turnout': '',
                         'feature_available_at': 'after_voting_end',
                         'use_for_decision_at_start': False})
    write_csv(folder/'agents.csv', [agents[k] for k in sorted(agents)])
    write_csv(folder/'agent_proposal_votes.csv', events)
    write_csv(folder/'vp_components.csv', components)
    write_csv(folder/'proposals.csv', rule_rows)
    write_csv(folder/'proposal_features_after_close.csv', features)
    # Fit once using the development period of pre-outcome level B, not the outcome-selected C.
    train_ids, train = training_vote_sample(tallies, vr)
    delays = [(v.created-proposals[v.proposal].start)/(proposals[v.proposal].end-proposals[v.proposal].start)
              for v in train]
    vps = [float(v.vp) for v in train]
    estimates = []
    for variable, values in [('retained_vote_delay', delays), ('participant_vp', vps)]:
        for label, q in [('q25', .25), ('median', .5), ('q75', .75)]:
            estimates.append({'parameter': variable+'_'+label, 'value': quantile(values, q),
                              'parameter_group': 'estimated_from_development_only',
                              'sample_votes': len(train), 'sample_proposals': len(train_ids),
                              'fit_phase': 'development', 'latest_permitted_end_exclusive': 1640995200,
                              'population': 'observed participants in B, not all eligible wallets',
                              'use_limit': 'descriptive empirical marginal, not causal behavior or turnout'})
    write_csv(folder/'empirical_parameters.csv', estimates)
    return {'c_proposals': len(c_ids), 'c_votes': len(events), 'c_wallets': len(agents),
            'vp_component_records': len(components), 'development_fit_proposals': len(train_ids),
            'development_fit_votes': len(train)}
