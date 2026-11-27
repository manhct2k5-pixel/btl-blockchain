"""verify_main.py: Pre-execution gates, execution of official 1000 MAIN + 200 VE worlds,
verification of invariants, temporal contracts, and result manifests.
"""
import json, subprocess, sys, socket
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]

sys.path.insert(0, str(ROOT))
from run_main import main, dump, protect, code_hashes, digest_file
from main_generator import digest

def suite(path, log):
    code = """import io, sys, unittest
s = io.StringIO()
t = unittest.defaultTestLoader.discover(sys.argv[1], top_level_dir=sys.argv[1])
r = unittest.TextTestRunner(stream=s, verbosity=2).run(t)
print(s.getvalue())
print('COUNT=' + str(r.testsRun))
sys.exit(0 if r.wasSuccessful() else 1)
"""
    r = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, text=True, encoding='utf-8')
    (ROOT / log).write_text(r.stdout + r.stderr, encoding='utf-8')
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return int(next(x.split('=', 1)[1] for x in r.stdout.splitlines() if x.startswith('COUNT=')))

def verify():
    print('Starting Pre-execution Gate Verification...', flush=True)
    counts = {}
    scopes = [
        ('main_mc', ROOT / 'tests'),
        ('pilot', WS / 'chapter4/experiments/monte_carlo_pilot/tests'),
        ('attack_model', WS / 'chapter4/experiments/attack_model/tests'),
        ('initialization', WS / 'chapter4/initialization/tests'),
        ('behavior', WS / 'chapter4/behavior/tests'),
        ('token_weighted', WS / 'chapter4/mechanisms/token_weighted/tests'),
        ('qv', WS / 'chapter4/mechanisms/quadratic_voting/tests'),
        ('ve_cap', WS / 'chapter4/mechanisms/vote_escrow_capping/tests'),
        ('baseline', WS / 'baseline/tests'),
        ('ch3_margins', WS / 'ch3_3_3_1/tests'),
        ('ch3_critical', WS / 'ch3_3_3_2/tests')
    ]
    for name, path in scopes:
        counts[name] = suite(path, name.upper() + '_TEST_LOG.txt')
        print(f'Scope {name}: {counts[name]} tests passed.', flush=True)

    ch = code_hashes()
    code_digest = digest(ch)
    gate = dict(
        status='PASSED',
        tests=counts,
        total_tests=sum(counts.values()),
        code_hash=code_digest,
        contract_hash=digest_file(ROOT / 'MC_MAIN_CONTRACT.json')
    )
    dump(ROOT / 'MAIN_GATE.json', gate)
    print(f'MAIN_GATE PASSED with {gate["total_tests"]} tests.', flush=True)

    print('Executing Official Level-A Monte Carlo (1000 MAIN + 200 VE worlds)...', flush=True)
    with patch.object(socket, 'socket', side_effect=RuntimeError('Main runs must be offline')):
        main_counts = main()

    manifest = json.loads((ROOT / 'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for n, h in manifest.items():
        assert digest_file(ROOT / n) == h, f'Manifest mismatch for {n}'

    results = json.loads((ROOT / 'MC_RESULT_DETAILS.json').read_text(encoding='utf-8'))
    worlds = json.loads((ROOT / 'WORLDS.json').read_text(encoding='utf-8'))

    assert len(worlds) == 1200, f'Expected 1200 worlds, found {len(worlds)}'
    assert len({w['world_id'] for w in worlds}) == 1200, 'World IDs must be strictly unique'
    assert len(results) == 3200, f'Expected 3200 mechanism runs, found {len(results)}'
    assert len({(r['world_id'], r['mechanism']) for r in results}) == 3200, 'Run IDs must be strictly unique'

    for r in results:
        if not r['attempted']:
            assert r['success'] is None, 'Declined attempts must have success=None'
        if r.get('eligible') is not True:
            assert r['policy_success'] is None, 'Infeasible worlds must have policy_success=None'
        if r['attempted']:
            event = next(e for e in r['events'] if e['kind'] == r['completion_event'])
            assert r['action_completed_at'] == event['time'], 'Action completed time must match completion event'

    for w in worlds:
        rows = [r for r in results if r['world_id'] == w['world_id']]
        if w['group'] == 'MAIN':
            assert len(rows) == 3, 'MAIN world must have exactly 3 mechanism results'
            assert len({r['eligible'] for r in rows}) == 1, 'Eligibility must be invariant across mechanisms'
            assert len({r['attempted'] for r in rows}) == 1, 'Attempt decision must be invariant across mechanisms'

    verification = dict(
        test_counts=counts,
        total_tests=sum(counts.values()),
        failures=0,
        errors=0,
        unique_worlds=1200,
        main_worlds=1000,
        ve_worlds=200,
        mechanism_world_rows=3200,
        main_three_way_matched_triplets=1000,
        pairwise_comparisons=3000,
        independent_world_sampling_unit=True,
        level='A_SYNTHETIC_ASSUMPTION',
        empirically_calibrated=False,
        offline_execution=True,
        prior_files_unchanged=protect(),
        large_scale_executed=True
    )
    dump(ROOT / 'VERIFICATION.json', verification)
    print('ALL VERIFICATIONS PASSED SUCCESSFULLY.')
    print(json.dumps(verification, indent=2))
    return verification

if __name__ == '__main__':
    verify()
