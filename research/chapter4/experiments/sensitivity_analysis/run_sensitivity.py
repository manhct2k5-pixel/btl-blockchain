"""run_sensitivity.py: Master execution script for Section 4.4 Sensitivity Analysis.
Executes all Type B re-simulation modules offline, deterministically, and saves full records.
"""
import argparse, datetime, json, os, socket, sys, time
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import numpy as np

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

from main_generator import load_contract, generate_world, decimal_text, jsonable
from sensitivity_simulator import custom_simulate, modify_alias_count, modify_budget, compute_gini_hhi

def run_all_sensitivity(main_limit=1000, ve_limit=200):
    contract = load_contract()
    c = deepcopy(contract)
    c['main_worlds'] = main_limit
    c['ve_worlds'] = ve_limit
    
    print("=" * 70)
    print("STARTING SECTION 4.4 SENSITIVITY ANALYSIS EXPERIMENTS (TYPE B)")
    print(f"Master Seed: 4302028 | Main Worlds: {main_limit} | VE Worlds: {ve_limit}")
    print("=" * 70, flush=True)
    
    # Pre-generate all worlds in memory once to ensure consistent RNG and baseline
    print("Pre-generating MAIN and VE worlds...", flush=True)
    main_worlds = [generate_world(c, 'MAIN', i) for i in range(main_limit)]
    ve_worlds = [generate_world(c, 'VE', i) for i in range(ve_limit)]
    
    split_world_indices = [i for i, w in enumerate(main_worlds) if w['config']['attack']['family'] == 'SPLIT']
    print(f"Loaded {len(main_worlds)} MAIN worlds (including {len(split_world_indices)} SPLIT worlds) and {len(ve_worlds)} VE worlds.", flush=True)
    
    all_summary_rows = []
    
    # =========================================================================
    # MODULE 1: INFORMATION CONDITION SENSITIVITY
    # =========================================================================
    print("\n--- Running Module 1: Information Condition Sensitivity ---", flush=True)
    info_conditions = ['INFORMED_PROPOSER', 'UNINFORMED_VOTER', 'BLOCKED']
    info_results = {cond: {m: {'eligible': 0, 'attempted': 0, 'success': 0} for m in ['TW', 'QV', 'CAP']} for cond in info_conditions}
    
    for cond in info_conditions:
        t0 = time.time()
        for idx in split_world_indices:
            w = main_worlds[idx]
            for m in ['TW', 'QV', 'CAP']:
                cfg = deepcopy(w['config'])
                cfg['mechanism'] = m
                cfg['information_condition'] = cond
                res = custom_simulate(cfg)
                
                if res.get('eligible'):
                    info_results[cond][m]['eligible'] += 1
                if res.get('attempted'):
                    info_results[cond][m]['attempted'] += 1
                if res.get('policy_success'):
                    info_results[cond][m]['success'] += 1
                    
        dt = time.time() - t0
        print(f"  Condition {cond:20s} completed in {dt:.1f}s: TW={info_results[cond]['TW']['success']}, QV={info_results[cond]['QV']['success']}, CAP={info_results[cond]['CAP']['success']}", flush=True)
        for m in ['TW', 'QV', 'CAP']:
            e = info_results[cond][m]['eligible']
            a = info_results[cond][m]['attempted']
            s = info_results[cond][m]['success']
            all_summary_rows.append({
                'experiment_name': 'INFORMATION_CONDITION',
                'factor_name': 'information_condition',
                'factor_value': cond,
                'mechanism': m,
                'n_worlds': len(split_world_indices),
                'n_eligible': e,
                'n_attempted': a,
                'n_success': s,
                'success_rate_eligible': s / e if e > 0 else 0.0,
                'success_rate_attempted': s / a if a > 0 else 0.0
            })
            
    (ROOT / 'INFO_CONDITION_RESULTS.json').write_text(json.dumps(info_results, indent=2), encoding='utf-8')

    # =========================================================================
    # MODULE 2: ALIAS WALLET COUNT SENSITIVITY (k in {1, 2, 4, 8})
    # =========================================================================
    print("\n--- Running Module 2: Alias Wallet Count Sensitivity ---", flush=True)
    alias_counts = [1, 2, 4, 8]
    alias_results = {k: {m: {'eligible': 0, 'attempted': 0, 'success': 0, 'eff_vp_sum': 0.0} for m in ['TW', 'QV', 'CAP']} for k in alias_counts}
    
    for k in alias_counts:
        t0 = time.time()
        for idx in split_world_indices:
            w = main_worlds[idx]
            cfg_k = modify_alias_count(w['config'], k, base_voters=c['base_voters'])
            for m in ['TW', 'QV', 'CAP']:
                cfg = deepcopy(cfg_k)
                cfg['mechanism'] = m
                res = custom_simulate(cfg)
                
                if res.get('eligible'):
                    alias_results[k][m]['eligible'] += 1
                if res.get('attempted'):
                    alias_results[k][m]['attempted'] += 1
                if res.get('policy_success'):
                    alias_results[k][m]['success'] += 1
                alias_results[k][m]['eff_vp_sum'] += float(res.get('attack_effective_total', 0.0) or 0.0)
                
        dt = time.time() - t0
        print(f"  Alias count k={k:1d} completed in {dt:.1f}s: TW={alias_results[k]['TW']['success']}, QV={alias_results[k]['QV']['success']}, CAP={alias_results[k]['CAP']['success']}", flush=True)
        for m in ['TW', 'QV', 'CAP']:
            e = alias_results[k][m]['eligible']
            a = alias_results[k][m]['attempted']
            s = alias_results[k][m]['success']
            all_summary_rows.append({
                'experiment_name': 'ALIAS_COUNT',
                'factor_name': 'alias_count_k',
                'factor_value': str(k),
                'mechanism': m,
                'n_worlds': len(split_world_indices),
                'n_eligible': e,
                'n_attempted': a,
                'n_success': s,
                'success_rate_eligible': s / e if e > 0 else 0.0,
                'success_rate_attempted': s / a if a > 0 else 0.0
            })
            
    (ROOT / 'ALIAS_COUNT_RESULTS.json').write_text(json.dumps(alias_results, indent=2), encoding='utf-8')

    # =========================================================================
    # MODULE 3: CAPPING THRESHOLD SENSITIVITY (cap_vp in {25k, 50k, 100k, 200k})
    # =========================================================================
    print("\n--- Running Module 3: Capping Threshold Sensitivity (All MAIN Worlds) ---", flush=True)
    capping_thresholds = [25000, 50000, 100000, 200000]
    cap_results = {thresh: {'eligible': 0, 'attempted': 0, 'success': 0, 'split_success': 0, 'non_split_success': 0, 'gini_sum': 0.0, 'hhi_sum': 0.0} for thresh in capping_thresholds}
    
    for thresh in capping_thresholds:
        t0 = time.time()
        for idx, w in enumerate(main_worlds):
            cfg = deepcopy(w['config'])
            cfg['mechanism'] = 'CAP'
            cfg['cap_vp'] = str(thresh)
            res = custom_simulate(cfg)
            
            is_split = (cfg['attack']['family'] == 'SPLIT')
            if res.get('eligible'):
                cap_results[thresh]['eligible'] += 1
            if res.get('attempted'):
                cap_results[thresh]['attempted'] += 1
            if res.get('policy_success'):
                cap_results[thresh]['success'] += 1
                if is_split:
                    cap_results[thresh]['split_success'] += 1
                else:
                    cap_results[thresh]['non_split_success'] += 1
            cap_results[thresh]['gini_sum'] += float(res.get('wallet_gini', 0.0) or 0.0)
            cap_results[thresh]['hhi_sum'] += float(res.get('wallet_hhi', 0.0) or 0.0)
            
        dt = time.time() - t0
        e = cap_results[thresh]['eligible']
        a = cap_results[thresh]['attempted']
        s = cap_results[thresh]['success']
        ss = cap_results[thresh]['split_success']
        nss = cap_results[thresh]['non_split_success']
        print(f"  Cap={thresh:6d} completed in {dt:.1f}s: Eligible={e}, Attempted={a}, Total Succ={s} (SPLIT={ss}, Other={nss})", flush=True)
        all_summary_rows.append({
            'experiment_name': 'CAPPING_THRESHOLD',
            'factor_name': 'cap_vp',
            'factor_value': str(thresh),
            'mechanism': 'CAP',
            'n_worlds': len(main_worlds),
            'n_eligible': e,
            'n_attempted': a,
            'n_success': s,
            'success_rate_eligible': s / e if e > 0 else 0.0,
            'success_rate_attempted': s / a if a > 0 else 0.0
        })
        
    (ROOT / 'CAPPING_THRESHOLD_RESULTS.json').write_text(json.dumps(cap_results, indent=2), encoding='utf-8')

    # =========================================================================
    # MODULE 4: ATTACK BUDGET SENSITIVITY (scale in {0.5, 1.0, 1.5, 2.0})
    # =========================================================================
    print("\n--- Running Module 4: Attack Budget Sensitivity (All MAIN Worlds) ---", flush=True)
    budget_scales = [0.5, 1.0, 1.5, 2.0]
    budget_results = {scale: {m: {'eligible': 0, 'attempted': 0, 'success': 0, 'by_family': {}} for m in ['TW', 'QV', 'CAP']} for scale in budget_scales}
    
    for scale in budget_scales:
        t0 = time.time()
        for idx, w in enumerate(main_worlds):
            cfg_scaled = modify_budget(w['config'], scale)
            fam = cfg_scaled['attack']['family']
            for m in ['TW', 'QV', 'CAP']:
                cfg = deepcopy(cfg_scaled)
                cfg['mechanism'] = m
                res = custom_simulate(cfg)
                
                if fam not in budget_results[scale][m]['by_family']:
                    budget_results[scale][m]['by_family'][fam] = {'eligible': 0, 'attempted': 0, 'success': 0}
                    
                if res.get('eligible'):
                    budget_results[scale][m]['eligible'] += 1
                    budget_results[scale][m]['by_family'][fam]['eligible'] += 1
                if res.get('attempted'):
                    budget_results[scale][m]['attempted'] += 1
                    budget_results[scale][m]['by_family'][fam]['attempted'] += 1
                if res.get('policy_success'):
                    budget_results[scale][m]['success'] += 1
                    budget_results[scale][m]['by_family'][fam]['success'] += 1
                    
        dt = time.time() - t0
        print(f"  Budget scale={scale:3.1f}x completed in {dt:.1f}s: TW succ={budget_results[scale]['TW']['success']} (elig={budget_results[scale]['TW']['eligible']}), QV succ={budget_results[scale]['QV']['success']}, CAP succ={budget_results[scale]['CAP']['success']}", flush=True)
        for m in ['TW', 'QV', 'CAP']:
            e = budget_results[scale][m]['eligible']
            a = budget_results[scale][m]['attempted']
            s = budget_results[scale][m]['success']
            all_summary_rows.append({
                'experiment_name': 'ATTACK_BUDGET',
                'factor_name': 'budget_scale',
                'factor_value': f"{scale}x",
                'mechanism': m,
                'n_worlds': len(main_worlds),
                'n_eligible': e,
                'n_attempted': a,
                'n_success': s,
                'success_rate_eligible': s / e if e > 0 else 0.0,
                'success_rate_attempted': s / a if a > 0 else 0.0
            })
            
    (ROOT / 'ATTACK_BUDGET_RESULTS.json').write_text(json.dumps(budget_results, indent=2), encoding='utf-8')

    # =========================================================================
    # MODULE 5: INTERACTION ANALYSIS (k in {1, 2, 4, 8} x cap in {25k, 50k, 100k, 200k})
    # =========================================================================
    print("\n--- Running Module 5: Interaction Analysis (Alias Count x Capping Threshold) ---", flush=True)
    interaction_matrix = {}
    for k in [1, 2, 4, 8]:
        interaction_matrix[k] = {}
        for cap in [25000, 50000, 100000, 200000]:
            interaction_matrix[k][cap] = {'eligible': 0, 'attempted': 0, 'success': 0}
            
    t0 = time.time()
    for k in [1, 2, 4, 8]:
        for cap in [25000, 50000, 100000, 200000]:
            for idx in split_world_indices:
                w = main_worlds[idx]
                cfg_k = modify_alias_count(w['config'], k, base_voters=c['base_voters'])
                cfg_k['mechanism'] = 'CAP'
                cfg_k['cap_vp'] = str(cap)
                res = custom_simulate(cfg_k)
                
                if res.get('eligible'):
                    interaction_matrix[k][cap]['eligible'] += 1
                if res.get('attempted'):
                    interaction_matrix[k][cap]['attempted'] += 1
                if res.get('policy_success'):
                    interaction_matrix[k][cap]['success'] += 1
                    
            e = interaction_matrix[k][cap]['eligible']
            a = interaction_matrix[k][cap]['attempted']
            s = interaction_matrix[k][cap]['success']
            all_summary_rows.append({
                'experiment_name': 'INTERACTION_ALIAS_CAP',
                'factor_name': f"k={k}_cap={cap}",
                'factor_value': f"{k}_{cap}",
                'mechanism': 'CAP',
                'n_worlds': len(split_world_indices),
                'n_eligible': e,
                'n_attempted': a,
                'n_success': s,
                'success_rate_eligible': s / e if e > 0 else 0.0,
                'success_rate_attempted': s / a if a > 0 else 0.0
            })
            
    dt = time.time() - t0
    print(f"  Interaction matrix 4x4 completed in {dt:.1f}s", flush=True)
    (ROOT / 'INTERACTION_RESULTS.json').write_text(json.dumps(interaction_matrix, indent=2), encoding='utf-8')

    # =========================================================================
    # MODULE 6: VOTE-ESCROW SENSITIVITY (Standalone)
    # =========================================================================
    print("\n--- Running Module 6: Standalone Vote-Escrow Sensitivity ---", flush=True)
    lock_rem_fractions = [0.25, 0.5, 1.0]
    ve_results = {frac: {'eligible': 0, 'attempted': 0, 'success': 0} for frac in lock_rem_fractions}
    
    t0 = time.time()
    for frac in lock_rem_fractions:
        for w in ve_worlds:
            cfg = deepcopy(w['config'])
            # Override lock remaining duration on events
            g = c['proposal']['epoch']
            max_sec = c['ve']['max_seconds']
            for ev in cfg.get('ve', {}).get('events', []):
                if ev['kind'] == 'CREATE':
                    rem = int(max_sec * frac)
                    ev['end'] = ev['time'] + rem
                    
            cfg['mechanism'] = 'VE'
            res = custom_simulate(cfg)
            if res.get('eligible'):
                ve_results[frac]['eligible'] += 1
            if res.get('attempted'):
                ve_results[frac]['attempted'] += 1
            if res.get('policy_success'):
                ve_results[frac]['success'] += 1
                
        e = ve_results[frac]['eligible']
        a = ve_results[frac]['attempted']
        s = ve_results[frac]['success']
        print(f"  VE Lock Remaining Fraction={frac:.2f}: eligible={e}, attempted={a}, success={s}", flush=True)
        all_summary_rows.append({
            'experiment_name': 'VOTE_ESCROW_LOCK_TIME',
            'factor_name': 'lock_remaining_fraction',
            'factor_value': str(frac),
            'mechanism': 'VE',
            'n_worlds': len(ve_worlds),
            'n_eligible': e,
            'n_attempted': a,
            'n_success': s,
            'success_rate_eligible': s / e if e > 0 else 0.0,
            'success_rate_attempted': s / a if a > 0 else 0.0
        })
        
    dt = time.time() - t0
    print(f"  VE sensitivity completed in {dt:.1f}s", flush=True)
    (ROOT / 'VOTE_ESCROW_RESULTS.json').write_text(json.dumps(ve_results, indent=2), encoding='utf-8')

    # Save SENSITIVITY_RESULTS.csv
    df_results = pd.DataFrame(all_summary_rows)
    df_results.to_csv(ROOT / 'SENSITIVITY_RESULTS.csv', index=False)
    print("\n" + "=" * 70)
    print(f"ALL TYPE B SENSITIVITY RUNS COMPLETE. Saved to {ROOT / 'SENSITIVITY_RESULTS.csv'}")
    print("=" * 70, flush=True)
    return df_results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Section 4.4 Sensitivity Experiments")
    parser.add_argument('--main-limit', type=int, default=1000, help="Number of MAIN worlds (default: 1000)")
    parser.add_argument('--ve-limit', type=int, default=200, help="Number of VE worlds (default: 200)")
    args = parser.parse_args()
    
    with patch.object(socket, 'socket', side_effect=RuntimeError('Must run strictly offline')):
        run_all_sensitivity(main_limit=args.main_limit, ve_limit=args.ve_limit)
