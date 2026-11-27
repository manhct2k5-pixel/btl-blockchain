"""sensitivity_reweighting.py: Type A Sensitivity Analysis via Conditional Reweighting.
Analyzes the impact of scenario mixture proportions (p = proportion of SPLIT opportunities)
on mechanism performance using empirical data from Monte Carlo Section 4.3.
Strictly read-only with respect to MC 4.3 data.
"""
import json, math, random, sys
from pathlib import Path
from fractions import Fraction as F
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]
MAIN_RESULTS_CSV = WS / 'chapter4/experiments/monte_carlo_main/MC_MAIN_RESULTS.csv'

def load_data():
    if not MAIN_RESULTS_CSV.exists():
        raise FileNotFoundError(f"Missing source dataset: {MAIN_RESULTS_CSV}")
    df = pd.read_csv(MAIN_RESULTS_CSV)
    main_df = df[(df['group'] == 'MAIN') & (df['eligible'] == True)].copy()
    return main_df

def run_reweighting_analysis(bootstrap_iter=10000, seed=4302029):
    df = load_data()
    
    # Verify counts
    split_df = df[df['family'] == 'SPLIT']
    other_df = df[df['family'] != 'SPLIT']
    
    n_split = len(split_df[split_df['mechanism'] == 'TW'])
    n_other = len(other_df[other_df['mechanism'] == 'TW'])
    n_total = n_split + n_other
    
    assert n_split == 257, f"Expected 257 SPLIT eligible, got {n_split}"
    assert n_other == 452, f"Expected 452 OTHER eligible, got {n_other}"
    assert n_total == 709, f"Expected 709 total eligible, got {n_total}"
    
    # Conditional success counts
    succ_counts = {}
    for group_name, gdf in [('SPLIT', split_df), ('OTHER', other_df), ('TOTAL', df)]:
        succ_counts[group_name] = {}
        for m in ['TW', 'QV', 'CAP']:
            sub = gdf[gdf['mechanism'] == m]
            k = int(sub['policy_success'].sum())
            n = len(sub)
            succ_counts[group_name][m] = {'k': k, 'n': n, 'rate': k / n if n > 0 else 0.0}
            
    # Verify 4.3 exact counts
    assert succ_counts['SPLIT']['TW']['k'] == 0
    assert succ_counts['SPLIT']['QV']['k'] == 19
    assert succ_counts['SPLIT']['CAP']['k'] == 19
    assert succ_counts['OTHER']['TW']['k'] == 17
    assert succ_counts['OTHER']['QV']['k'] == 16
    assert succ_counts['OTHER']['CAP']['k'] == 17
    
    # Analytical crossover point where TW = QV:
    # R_TW(p) = (1-p)*17/452
    # R_QV(p) = p*19/257 + (1-p)*16/452
    # (1-p)*(17/452 - 16/452) = p*(19/257)
    # (1-p)/452 = p*19/257 => p* = (1/452) / (19/257 + 1/452)
    p_crossover_qv_tw = (1.0 / 452.0) / ((19.0 / 257.0) + (1.0 / 452.0))
    
    # Benchmark grid of p values
    p_baseline = 257.0 / 709.0
    benchmark_p = [0.0, 0.02905, 0.1, 0.2, 0.25, p_baseline, 0.5, 0.75, 1.0]
    benchmark_p.sort()
    
    # Pairwise world-level results for bootstrap
    # Pivot to get (world_id, family) -> TW, QV, CAP success flags
    piv = df.pivot(index=['world_id', 'family'], columns='mechanism', values='policy_success').reset_index()
    split_piv = piv[piv['family'] == 'SPLIT'].to_dict(orient='records')
    other_piv = piv[piv['family'] != 'SPLIT'].to_dict(orient='records')
    
    # Run paired bootstrap
    rng = random.Random(seed)
    
    bootstrap_results = {p: {'TW': [], 'QV': [], 'CAP': [], 'QV_TW': [], 'CAP_TW': [], 'CAP_QV': []} for p in benchmark_p}
    crossover_boots = []
    
    n_s = len(split_piv)
    n_o = len(other_piv)
    
    for _ in range(bootstrap_iter):
        boot_s = [split_piv[rng.randint(0, n_s - 1)] for _ in range(n_s)]
        boot_o = [other_piv[rng.randint(0, n_o - 1)] for _ in range(n_o)]
        
        # calculate conditional rates in bootstrap sample
        k_s_tw = sum(1 for w in boot_s if w['TW']) / n_s
        k_s_qv = sum(1 for w in boot_s if w['QV']) / n_s
        k_s_cap = sum(1 for w in boot_s if w['CAP']) / n_s
        
        k_o_tw = sum(1 for w in boot_o if w['TW']) / n_o
        k_o_qv = sum(1 for w in boot_o if w['QV']) / n_o
        k_o_cap = sum(1 for w in boot_o if w['CAP']) / n_o
        
        # crossover for this boot sample
        denom = (k_s_qv - k_s_tw) + (k_o_tw - k_o_qv)
        if denom > 0:
            p_star = (k_o_tw - k_o_qv) / denom
            crossover_boots.append(p_star)
            
        for p in benchmark_p:
            r_tw = p * k_s_tw + (1.0 - p) * k_o_tw
            r_qv = p * k_s_qv + (1.0 - p) * k_o_qv
            r_cap = p * k_s_cap + (1.0 - p) * k_o_cap
            
            bootstrap_results[p]['TW'].append(r_tw)
            bootstrap_results[p]['QV'].append(r_qv)
            bootstrap_results[p]['CAP'].append(r_cap)
            bootstrap_results[p]['QV_TW'].append(r_qv - r_tw)
            bootstrap_results[p]['CAP_TW'].append(r_cap - r_tw)
            bootstrap_results[p]['CAP_QV'].append(r_cap - r_qv)
            
    # Summary of benchmark table with CIs
    benchmark_table = []
    for p in benchmark_p:
        r_tw = p * succ_counts['SPLIT']['TW']['rate'] + (1.0 - p) * succ_counts['OTHER']['TW']['rate']
        r_qv = p * succ_counts['SPLIT']['QV']['rate'] + (1.0 - p) * succ_counts['OTHER']['QV']['rate']
        r_cap = p * succ_counts['SPLIT']['CAP']['rate'] + (1.0 - p) * succ_counts['OTHER']['CAP']['rate']
        
        diff_qv_tw = r_qv - r_tw
        diff_cap_tw = r_cap - r_tw
        diff_cap_qv = r_cap - r_qv
        
        tw_ci = (np.percentile(bootstrap_results[p]['TW'], 2.5), np.percentile(bootstrap_results[p]['TW'], 97.5))
        qv_ci = (np.percentile(bootstrap_results[p]['QV'], 2.5), np.percentile(bootstrap_results[p]['QV'], 97.5))
        cap_ci = (np.percentile(bootstrap_results[p]['CAP'], 2.5), np.percentile(bootstrap_results[p]['CAP'], 97.5))
        
        qv_tw_ci = (np.percentile(bootstrap_results[p]['QV_TW'], 2.5), np.percentile(bootstrap_results[p]['QV_TW'], 97.5))
        cap_tw_ci = (np.percentile(bootstrap_results[p]['CAP_TW'], 2.5), np.percentile(bootstrap_results[p]['CAP_TW'], 97.5))
        cap_qv_ci = (np.percentile(bootstrap_results[p]['CAP_QV'], 2.5), np.percentile(bootstrap_results[p]['CAP_QV'], 97.5))
        
        benchmark_table.append({
            'p': round(p, 5),
            'p_label': f"{p*100:.1f}%",
            'R_TW': r_tw,
            'TW_ci_low': tw_ci[0],
            'TW_ci_high': tw_ci[1],
            'R_QV': r_qv,
            'QV_ci_low': qv_ci[0],
            'QV_ci_high': qv_ci[1],
            'R_CAP': r_cap,
            'CAP_ci_low': cap_ci[0],
            'CAP_ci_high': cap_ci[1],
            'Diff_QV_TW': diff_qv_tw,
            'Diff_QV_TW_ci_low': qv_tw_ci[0],
            'Diff_QV_TW_ci_high': qv_tw_ci[1],
            'Diff_CAP_TW': diff_cap_tw,
            'Diff_CAP_TW_ci_low': cap_tw_ci[0],
            'Diff_CAP_TW_ci_high': cap_tw_ci[1],
            'Diff_CAP_QV': diff_cap_qv,
            'Diff_CAP_QV_ci_low': cap_qv_ci[0],
            'Diff_CAP_QV_ci_high': cap_qv_ci[1],
        })
        
    crossover_summary = {
        'p_crossover_analytical': p_crossover_qv_tw,
        'p_crossover_analytical_pct': p_crossover_qv_tw * 100.0,
        'bootstrap_mean': float(np.mean(crossover_boots)) if crossover_boots else None,
        'bootstrap_ci_95': (float(np.percentile(crossover_boots, 2.5)), float(np.percentile(crossover_boots, 97.5))) if crossover_boots else None
    }
    
    # Continuous grid for curves (0.0 to 1.0, 101 points)
    curve_points = []
    for step in range(101):
        p_val = step / 100.0
        r_tw = p_val * succ_counts['SPLIT']['TW']['rate'] + (1.0 - p_val) * succ_counts['OTHER']['TW']['rate']
        r_qv = p_val * succ_counts['SPLIT']['QV']['rate'] + (1.0 - p_val) * succ_counts['OTHER']['QV']['rate']
        r_cap = p_val * succ_counts['SPLIT']['CAP']['rate'] + (1.0 - p_val) * succ_counts['OTHER']['CAP']['rate']
        curve_points.append({
            'p': round(p_val, 4),
            'R_TW': r_tw,
            'R_QV': r_qv,
            'R_CAP': r_cap,
            'Diff_QV_TW': r_qv - r_tw,
            'Diff_CAP_TW': r_cap - r_tw
        })
        
    output_data = {
        'empirical_conditional_counts': succ_counts,
        'crossover_summary': crossover_summary,
        'benchmark_table': benchmark_table,
        'continuous_curve': curve_points
    }
    
    out_json = ROOT / 'TYPE_A_REWEIGHTING_RESULTS.json'
    out_json.write_text(json.dumps(output_data, indent=2), encoding='utf-8')
    
    # Save CSV
    pd.DataFrame(benchmark_table).to_csv(ROOT / 'REWEIGHTING_BENCHMARKS.csv', index=False)
    pd.DataFrame(curve_points).to_csv(ROOT / 'REWEIGHTING_CURVE.csv', index=False)
    print(f"Reweighting analysis complete. Results saved to {out_json.name}")
    return output_data

if __name__ == '__main__':
    run_reweighting_analysis()
