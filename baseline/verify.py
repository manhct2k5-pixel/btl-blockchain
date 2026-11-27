"""Run automated tests, differential source checks and a socket-disabled replay."""
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT))
from engine import sha
from integrity import verify_unchanged


def run(command):
    result = subprocess.run(command, cwd=WORKSPACE, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (ROOT/'TEST_LOG.txt').write_text(stream.getvalue(), encoding='utf-8')
    test_summary = {'unit_tests': result.testsRun, 'failures': len(result.failures),
                    'errors': len(result.errors), 'skipped': len(result.skipped)}
    (ROOT/'TEST_RESULTS.json').write_text(json.dumps(test_summary, indent=2), encoding='utf-8')
    if not result.wasSuccessful():
        raise RuntimeError(stream.getvalue())
    print('Unit tests:', result.testsRun, 'passed', flush=True)
    run([sys.executable, str(ROOT/'make_synthetic_cases.py')])
    for name, output in [('ORACLE_CASES.json', 'SOURCE_PARITY.json'), ('SYNTHETIC_CASES.json', 'SYNTHETIC_PARITY.json')]:
        out = run(['node', str(ROOT/'source_oracle.mjs'), '--source', str(WORKSPACE/'data_enrichment'),
                   '--cases', str(ROOT/name), '--catalog', str(ROOT/'RULE_CATALOG.json'),
                   '--output', str(ROOT/output)])
        print(out.strip(), flush=True)
    expected = json.loads((ROOT/'OUTPUT_MANIFEST.json').read_text(encoding='utf-8'))
    guard = (
        'import runpy,socket,sys;'
        'sys.path.insert(0,'+repr(str(ROOT))+');'
        'socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("Network prohibited in Baseline replay"));'
        'socket.create_connection=socket.socket;'
        'sys.argv='+repr([str(ROOT/'run_baseline.py'), '--output', str(ROOT/'replay')])+';'
        'runpy.run_path('+repr(str(ROOT/'run_baseline.py'))+',run_name="__main__")'
    )
    print('Run full offline replay with sockets disabled...', flush=True)
    run([sys.executable, '-c', guard])
    comparisons = {}
    for name, record in expected.items():
        target = ROOT/'replay'/name
        if not target.exists() or sha(target) != record['sha256']:
            raise RuntimeError('Replay output differs: '+name)
        comparisons[name] = record['sha256']
    source_checks = verify_unchanged(WORKSPACE, json.loads((ROOT/'INPUT_MANIFEST.json').read_text(encoding='utf-8')))
    record = {'csv_outputs_byte_identical': len(comparisons), 'sha256': comparisons,
              'python_network_sockets_disabled': True, 'input_preservation': source_checks,
              'unit_tests': test_summary,
              'source_parity': json.loads((ROOT/'SOURCE_PARITY.json').read_text(encoding='utf-8'))['matched'],
              'synthetic_source_parity': json.loads((ROOT/'SYNTHETIC_PARITY.json').read_text(encoding='utf-8'))['matched']}
    (ROOT/'REPLAY_VERIFICATION.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print('Verified byte-identical CSV outputs:', len(comparisons), flush=True)


if __name__ == '__main__':
    main()
