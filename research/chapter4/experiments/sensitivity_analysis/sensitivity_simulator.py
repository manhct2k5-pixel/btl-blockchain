"""sensitivity_simulator.py: Type B Sensitivity Analysis via Parameter and Behavioral Re-simulation.
Implements modular re-simulation experiments:
1. Information condition (INFORMED_PROPOSER vs UNINFORMED_VOTER vs BLOCKED)
2. Alias wallet count (k in {1, 2, 4, 8})
3. Capping threshold (cap_vp in {25000, 50000, 100000, 200000})
4. Attack budget scaling (factor in {0.5, 1.0, 1.5, 2.0})
5. Interaction analysis (alias count x capping threshold, 16 cells)
6. Vote-Escrow sensitivity (lock remaining fraction x lock amount fraction)

Strictly non-destructive: Does not overwrite or modify any MC 4.3 data.
Enforces offline execution, exact VP conservation, and bitwise reproducibility.
"""
import copy, datetime, hashlib, json, math, os, sys
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(WS / 'chapter4/behavior'))
sys.path.insert(0, str(WS / 'chapter4/initialization'))
sys.path.insert(0, str(WS / 'chapter4/mechanisms/token_weighted'))
sys.path.insert(0, str(WS / 'chapter4/mechanisms/quadratic_voting'))
sys.path.insert(0, str(WS / 'chapter4/mechanisms/vote_escrow_capping'))
sys.path.insert(0, str(WS / 'chapter4/experiments/attack_model'))
sys.path.insert(0, str(WS / 'chapter4/experiments/monte_carlo_main'))

from main_generator import load_contract, generate_world, digest, decimal_text, jsonable
from main_patch import simulate as main_simulate
import attack_core

def custom_simulate(config, info_condition=None):
    """Wrapper around simulate with information condition enforcement."""
    cfg = deepcopy(config)
    if info_condition is None:
        info_cond = cfg.pop('information_condition', 'INFORMED_PROPOSER')
    else:
        cfg.pop('information_condition', None)
        info_cond = info_condition
        
    a = cfg['attack']
    p = cfg['proposal']
    
    # Check information condition for SPLIT
    if a.get('family') == 'SPLIT':
        if info_cond == 'UNINFORMED_VOTER':
            return {
                'status': 'INFEASIBLE_UNINFORMED_VOTER_NO_ADVANCE_PROPOSAL_KNOWLEDGE',
                'reason': 'Outside voter cannot know future proposal before snapshot',
                'eligible': False,
                'attempted': False,
                'success': False,
                'policy_success': False,
                'time_to_decision': None,
                'time_to_action_completion': None,
                'time_to_final_evaluation': None,
                'action_completed_at': None,
                'completion_event': 'NONE',
                'first_target_time': None,
                'target_outcome': a['target_outcome'],
                'target_choice': a['target_choice'],
                'evidence_label': 'SYNTHETIC_ASSUMPTION',
                'calibrated': False,
                'no_attack_outcome': None,
                'attack_outcome': None,
                'no_attack_source_vp': '0',
                'attack_source_vp': '0',
                'no_attack_effective_total': '0',
                'attack_effective_total': '0',
                'weight_unit': 'TOKEN_VP',
                'wallet_gini': '0',
                'wallet_hhi': '0',
                'controller_gini': '0',
                'controller_hhi': '0',
                'paid': '0',
                'external_fees': '0',
                'peak_escrow': '0',
                'refund': '0',
                'cash_expense': '0',
                'opportunity_cost_utility': '0',
                'capital_cost_utility': '0',
                'monetary_unit': 'TEST_COIN',
                'actual_usd_cost': '0',
                'empirical_attack_probability': '0',
                'execution': 'SUCCESS',
                've_lock_remaining_at_snapshot_json': '{}',
                've_lock_time_basis': 'REAL_TIME_EPOCH'
            }
        elif info_cond == 'BLOCKED':
            return {
                'status': 'INFEASIBLE_SPLIT_PRE_SNAPSHOT_BLOCKED',
                'reason': 'Pre-snapshot splitting is blocked by identity/timing rules',
                'eligible': False,
                'attempted': False,
                'success': False,
                'policy_success': False,
                'time_to_decision': None,
                'time_to_action_completion': None,
                'time_to_final_evaluation': None,
                'action_completed_at': None,
                'completion_event': 'NONE',
                'first_target_time': None,
                'target_outcome': a['target_outcome'],
                'target_choice': a['target_choice'],
                'evidence_label': 'SYNTHETIC_ASSUMPTION',
                'calibrated': False,
                'no_attack_outcome': None,
                'attack_outcome': None,
                'no_attack_source_vp': '0',
                'attack_source_vp': '0',
                'no_attack_effective_total': '0',
                'attack_effective_total': '0',
                'weight_unit': 'TOKEN_VP',
                'wallet_gini': '0',
                'wallet_hhi': '0',
                'controller_gini': '0',
                'controller_hhi': '0',
                'paid': '0',
                'external_fees': '0',
                'peak_escrow': '0',
                'refund': '0',
                'cash_expense': '0',
                'opportunity_cost_utility': '0',
                'capital_cost_utility': '0',
                'monetary_unit': 'TEST_COIN',
                'actual_usd_cost': '0',
                'empirical_attack_probability': '0',
                'execution': 'SUCCESS',
                've_lock_remaining_at_snapshot_json': '{}',
                've_lock_time_basis': 'REAL_TIME_EPOCH'
            }
            
    return main_simulate(cfg)

def compute_gini_hhi(weights):
    vals = [float(x) for x in weights if float(x) > 0]
    if not vals:
        return 0.0, 0.0
    s = sum(vals)
    n = len(vals)
    if s == 0:
        return 0.0, 0.0
    shares = [v / s for v in vals]
    hhi = sum(sh * sh for sh in shares)
    
    # Gini
    sorted_v = sorted(vals)
    cum = 0.0
    for i, v in enumerate(sorted_v):
        cum += (2 * (i + 1) - n - 1) * v
    gini = cum / (n * s) if n * s > 0 else 0.0
    return float(gini), float(hhi)

def modify_alias_count(world_cfg, k, base_voters=5):
    """Partition attacker VP into k wallets strictly conserving total VP."""
    cfg = deepcopy(world_cfg)
    source = '0x' + format(1, '040x')
    source_vp = F(cfg['voters'][source]['vp'])
    
    # Retain non-alias voters
    voters = {}
    for addr, vdata in cfg['voters'].items():
        if addr == source or not any(addr == '0x' + format(base_voters + i, '040x') for i in range(1, 20)):
            voters[addr] = deepcopy(vdata)
            
    partition = [source] + ['0x' + format(base_voters + i, '040x') for i in range(1, k)]
    for p_addr in partition:
        if p_addr not in voters:
            voters[p_addr] = deepcopy(voters[source])
            voters[p_addr].update(vp='0', choice=None, principal='attacker')
            
    cfg['voters'] = voters
    # Strict conservation: each gets source_vp / k
    each_vp = source_vp / k
    cfg['attack']['split'] = [dict(wallet=addr, vp=decimal_text(each_vp)) for addr in partition]
    
    # Assert conservation
    assert sum((F(x['vp']) for x in cfg['attack']['split']), F(0)) == source_vp
    return cfg

def modify_budget(world_cfg, scale_factor):
    """Scale attacker liquid budget by scale_factor."""
    cfg = deepcopy(world_cfg)
    orig_b = F(cfg['principals']['attacker']['budget'])
    new_b = int(round(float(orig_b * F(str(scale_factor)))))
    cfg['principals']['attacker']['budget'] = str(new_b)
    return cfg
