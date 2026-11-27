"""run_main.py: Execute the official Level-A Monte Carlo experiment (Section 4.3).
1000 matched main worlds (TW, QV, CAP) + 200 separate Vote-Escrow worlds.
Enforces offline execution, invariant conservation, frozen seeds, and full audit logging.
"""
import argparse, datetime, hashlib, json, platform, socket, sys
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(WS / 'chapter4/behavior'))
sys.path.insert(0, str(WS / 'chapter4/initialization'))
sys.path.insert(0, str(WS / 'chapter4/experiments/attack_model'))

from main_generator import ROOT as GEN_ROOT, WS as GEN_WS, load_contract, generate_world, digest, digest_file, jsonable
from main_patch import simulate, MODEL_VERSION
from main_metrics import summarize, paired
import initialize

def dump(p, x):
    p.write_text(json.dumps(jsonable(x), ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')

def protect():
    m = json.loads((ROOT / 'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for n, h in m.items():
        if digest_file(WS / n) != h:
            raise ValueError('Protected input file changed: ' + n)
    return len(m)

def code_hashes():
    paths = [p for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts]
    paths += [WS / 'chapter4/experiments/attack_model' / n for n in ('attack_core.py', 'qv_numeric_v2.py', 'metrics.py')]
    paths += [WS / 'chapter4/mechanisms' / n for n in (
        'token_weighted/mechanism.py', 'quadratic_voting/qv_mechanism.py',
        'vote_escrow_capping/policies.py', 'vote_escrow_capping/escrow.py'
    )]
    paths += [WS / n for n in (
        'baseline/engine.py', 'baseline/catalog.py', 'chapter4/initialization/model.py',
        'chapter4/behavior/behavior.py'
    )]
    return {p.relative_to(WS).as_posix(): digest_file(p) for p in paths}

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=ROOT)
    p.add_argument('--reverse-mechanisms', action='store_true')
    args = p.parse_args(argv)
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('Output restricted to monte_carlo_main folder')
    output.mkdir(parents=True, exist_ok=True)
    prior = protect()
    contract = load_contract()
    ch = code_hashes()
    code_digest = digest(ch)

    world_rows = []
    results = []
    seed_rows = []
    journal = {
        'wall_started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reverse_mechanisms': args.reverse_mechanisms,
        'events': []
    }

    with patch.object(socket, 'socket', side_effect=RuntimeError('Official Monte Carlo must run strictly offline')):
        for group in ('MAIN', 'VE'):
            n = contract['main_worlds'] if group == 'MAIN' else contract['ve_worlds']
            mechanisms = contract['mechanisms_main'] if group == 'MAIN' else contract['mechanisms_ve']
            if args.reverse_mechanisms:
                mechanisms = list(reversed(mechanisms))

            for i in range(n):
                world = generate_world(contract, group, i)
                original_digest = digest(world)
                world_rows.append(world)
                seed_rows.append({
                    k: world[k] for k in ('world_id', 'group', 'replicate_id', 'master_seed',
                                         'stream_seeds', 'input_hash', 'distribution_hash')
                })

                for mechanism in mechanisms:
                    config = deepcopy(world['config'])
                    config['mechanism'] = mechanism
                    result = simulate(config)
                    result.update(
                        world_id=world['world_id'],
                        replicate_id=i,
                        group=group,
                        input_hash=digest(config),
                        shared_world_hash=world['input_hash'],
                        code_hash=code_digest,
                        contract_hash=digest_file(ROOT / 'MC_MAIN_CONTRACT.json'),
                        distribution_hash=world['distribution_hash'],
                        master_seed=contract['master_seed'],
                        generator_version=world['generator_version'],
                        calibrated=False,
                        Monte_Carlo=True,
                        rng_used=True,
                        random_world_generation=True,
                        decision_rng_used=False,
                        experiment_level='A_SYNTHETIC_ASSUMPTION',
                        registry_source_vp=str(sum((F(v['vp']) for v in config['voters'].values()), F(0))),
                        initial_total_money=str(sum((F(pr['budget']) for pr in config['principals'].values()), F(0)))
                    )
                    results.append(result)

                assert digest(world) == original_digest, 'Mechanism mutated shared world/RNG config'
                if (i + 1) % 100 == 0 or (group == 'VE' and (i + 1) % 50 == 0):
                    print(f'Progress: Completed {i + 1}/{n} worlds for group {group}', flush=True)

    world_rows.sort(key=lambda x: x['world_id'])
    seed_rows.sort(key=lambda x: x['world_id'])
    results.sort(key=lambda x: (x['world_id'], x['mechanism']))

    summary = {}
    for group, mechanisms in [('MAIN', contract['mechanisms_main']), ('VE', contract['mechanisms_ve'])]:
        for mechanism in mechanisms:
            rows = [r for r in results if r['group'] == group and r['mechanism'] == mechanism]
            summary[group + '_' + mechanism] = summarize(rows)
            for family in sorted({r['family'] for r in rows}):
                summary[group + '_' + mechanism + '_' + family] = summarize([r for r in rows if r['family'] == family])

    pairs = [paired(results, a, b) for a, b in [('TW', 'QV'), ('TW', 'CAP'), ('QV', 'CAP')]]
    pairs += [
        paired(results, a, b, fam)
        for fam in ('SWITCH', 'BRIBE_E', 'MOBILIZE', 'SPLIT')
        for a, b in [('TW', 'QV'), ('TW', 'CAP'), ('QV', 'CAP')]
    ]

    csv_rows = []
    for r in results:
        no = r.get('no_attack') or {}
        yes = r.get('with_attack') or {}
        cash = r.get('resources', {}).get('attacker', {})
        record = {
            k: r.get(k) for k in (
                'world_id', 'replicate_id', 'group', 'family', 'mechanism', 'seed', 'master_seed',
                'model_version', 'generator_version', 'numeric_patch', 'input_hash', 'shared_world_hash',
                'code_hash', 'contract_hash', 'distribution_hash', 'status', 'reason', 'eligible',
                'attempted', 'success', 'policy_success', 'time_to_decision', 'time_to_action_completion',
                'time_to_final_evaluation', 'action_completed_at', 'completion_event', 'first_target_time',
                'target_outcome', 'target_choice', 'evidence_label', 'calibrated', 'registry_source_vp',
                'initial_total_money', 'Monte_Carlo', 'rng_used', 'random_world_generation',
                'decision_rng_used', 'experiment_level'
            )
        }
        record.update(
            no_attack_outcome=no.get('outcome'),
            attack_outcome=yes.get('outcome'),
            no_attack_source_vp=no.get('source_vp'),
            attack_source_vp=yes.get('source_vp'),
            no_attack_effective_total=no.get('effective_total'),
            attack_effective_total=yes.get('effective_total'),
            weight_unit=yes.get('unit'),
            no_attack_options_json=json.dumps(no.get('options')),
            attack_options_json=json.dumps(yes.get('options')),
            wallet_gini=yes.get('wallet_gini'),
            wallet_hhi=yes.get('wallet_hhi'),
            controller_gini=yes.get('controller_gini'),
            controller_hhi=yes.get('controller_hhi'),
            paid=str(cash.get('paid', '')),
            external_fees=str(cash.get('external_fees', '')),
            peak_escrow=str(cash.get('peak_escrow', '')),
            refund=str(cash.get('refund', '')),
            cash_expense=str(r.get('net_cash_expense', '')),
            opportunity_cost_utility=str(r.get('opportunity_cost_utility', '')),
            capital_cost_utility=str(r.get('capital_cost_utility', '')),
            monetary_unit='TEST_COIN',
            actual_usd_cost='',
            empirical_attack_probability='',
            execution='UNKNOWN'
        )
        if r['group'] == 'VE':
            w = next(w for w in world_rows if w['world_id'] == r['world_id'])
            events = w['config']['ve']['events']
            snapshot = w['config']['proposal']['snapshot_time']
            record['ve_lock_remaining_at_snapshot_json'] = json.dumps([e['end'] - snapshot for e in events if e['kind'] == 'CREATE'])
            record['ve_lock_time_basis'] = 'DECLARED_SECONDS_AT_SNAPSHOT_NOT_OBSERVED_HISTORY'
        csv_rows.append(record)

    initialize.write_csv(output / 'MC_MAIN_RESULTS.csv', csv_rows)
    dump(output / 'WORLDS.json', world_rows)
    dump(output / 'MC_RESULT_DETAILS.json', results)
    dump(output / 'SEEDS.json', seed_rows)
    dump(output / 'MC_MAIN_SUMMARY.json', summary)
    dump(output / 'PAIRED_COMPARISONS.json', pairs)
    dump(output / 'CODE_MANIFEST.json', ch)

    main_counts = {k: summary[k]['counts'] for k in ('MAIN_TW', 'MAIN_QV', 'MAIN_CAP', 'VE_VE')}
    dump(output / 'RUN_METADATA.json', dict(
        unique_worlds=len(world_rows),
        main_worlds=contract['main_worlds'],
        ve_worlds=contract['ve_worlds'],
        mechanism_world_rows=len(results),
        no_attack_branches=len(results),
        attack_policy_branches=len(results),
        main_three_way_matched_worlds=contract['main_worlds'],
        pairwise_mechanism_world_comparisons=3 * contract['main_worlds'],
        counts=main_counts,
        master_seed=contract['master_seed'],
        python=platform.python_version(),
        level='A_SYNTHETIC_ASSUMPTION',
        Monte_Carlo=True,
        calibrated=False,
        large_scale_experiment=True,
        contract_hash=digest_file(ROOT / 'MC_MAIN_CONTRACT.json'),
        code_hash=code_digest,
        prior_files_unchanged=prior,
        network_disabled=True
    ))

    names = [
        'MC_MAIN_RESULTS.csv', 'WORLDS.json', 'MC_RESULT_DETAILS.json', 'SEEDS.json',
        'MC_MAIN_SUMMARY.json', 'PAIRED_COMPARISONS.json', 'CODE_MANIFEST.json', 'RUN_METADATA.json'
    ]
    dump(output / 'RESULT_MANIFEST.json', {n: digest_file(output / n) for n in names})

    journal['wall_finished_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    journal['unique_worlds_completed'] = len(world_rows)
    journal['mechanism_world_rows'] = len(results)
    journal['wall_times_not_simulated_action_times'] = True
    dump(output / 'EXECUTION_LOG.json', journal)

    print('Execution complete. Summary of counts:')
    print(json.dumps(main_counts, indent=2))
    return main_counts

if __name__ == '__main__':
    main()
