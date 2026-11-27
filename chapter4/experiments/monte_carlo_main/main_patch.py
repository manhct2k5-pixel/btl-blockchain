"""ATTACK_MODEL_MAIN_V2: Versioned simulation driver for official Level-A Monte Carlo.
Maintains exact temporal contract, verifies invariants, handles no-attack / with-attack outcomes.
"""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]
sys.path.insert(0, str(WS / 'chapter4/experiments/attack_model'))
from attack_core import simulate as simulate_v1

MODEL_VERSION = 'ATTACK_MODEL_MAIN_V2'
COMPLETION_EVENTS = {
    'SPLIT': 'PRE_SNAPSHOT_FIXED_SOURCE_PARTITION',
    'SWITCH': 'OWN_CONTROLLED_BALLOT_ACTION',
    'MOBILIZE': 'SIMULTANEOUS_RESPONSE_ATOMIC_BATCH',
    'BRIBE_E': 'VERIFY_FINAL_ACTION_PAY_AND_REFUND'
}

def simulate(config):
    result = deepcopy(simulate_v1(config))
    result['model_version'] = MODEL_VERSION
    result['evidence_label'] = 'SYNTHETIC_ASSUMPTION'
    attempted = result['attempted']
    if not attempted:
        result['success'] = None

    # Primary policy success flag
    result['policy_success'] = (result['success'] if attempted else False) if result.get('eligible') is True else None

    # Temporal breakdown
    result['time_to_decision'] = None
    result['time_to_action_completion'] = None
    result['time_to_final_evaluation'] = None
    result['action_completed_at'] = None
    result['completion_event'] = None
    result['ballot_response_completed_at'] = None

    if attempted:
        attack = config['attack']
        published = attack['published_at']
        result['time_to_decision'] = attack['decision_at'] - published
        family = attack['family']
        expected = COMPLETION_EVENTS[family]
        matches = [e for e in result['events'] if e['kind'] == expected]
        if len(matches) != 1:
            raise ValueError(f'Main V2 completion event missing or ambiguous for family {family}')
        completion = matches[0]['time']
        result['completion_event'] = expected
        result['action_completed_at'] = completion
        result['time_to_action_completion'] = completion - published
        result['time_to_final_evaluation'] = config['proposal']['end'] + 1 - published
        for e in result['events']:
            if e['kind'] in ('SIMULTANEOUS_RESPONSE_ATOMIC_BATCH', 'OWN_CONTROLLED_BALLOT_ACTION'):
                result['ballot_response_completed_at'] = e['time']
        if not 0 <= result['time_to_decision'] <= result['time_to_action_completion'] <= result['time_to_final_evaluation']:
            raise ValueError(f'Inconsistent Main V2 temporal contract in scenario {config.get("scenario_id")}')

    result['decision_time_basis'] = 'DECLARED_SCHEDULED_ACTION_OR_RECIPIENT_DECISION_CONTEXT_NOT_CPU_TIME'
    result['attacker_offer_decision_at'] = (config['attack']['published_at'] if result.get('views') else None)
    result['first_target_time'] = None
    result['first_target_time_status'] = 'NOT_INFERRED_FROM_FINAL_OUTCOME'
    return result
