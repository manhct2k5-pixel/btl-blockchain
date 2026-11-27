"""Regression suites remain isolated; the new patch/model also run repeated in one process."""
import io,json,subprocess,sys
from pathlib import Path
from run_attack_validation import ROOT,WS,main,dump,sha,protect

def suite(path,log):
    code="""import io,json,sys,unittest
s=io.StringIO();f=unittest.defaultTestLoader.discover(sys.argv[1],top_level_dir=sys.argv[1])
r=unittest.TextTestRunner(stream=s,verbosity=2).run(f)
print(s.getvalue());print('COUNT='+str(r.testsRun));sys.exit(0 if r.wasSuccessful() else 1)
"""
    r=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,text=True,encoding='utf-8')
    (ROOT/log).write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise AssertionError(r.stdout+r.stderr)
    return int(next(x.split('=',1)[1] for x in r.stdout.splitlines() if x.startswith('COUNT=')))
def verify():
    counts={}
    scopes=[('attack_model',ROOT/'tests'),('initialization',WS/'chapter4/initialization/tests'),
        ('behavior',WS/'chapter4/behavior/tests'),('token_weighted',WS/'chapter4/mechanisms/token_weighted/tests'),
        ('qv',WS/'chapter4/mechanisms/quadratic_voting/tests'),('ve_cap',WS/'chapter4/mechanisms/vote_escrow_capping/tests'),
        ('baseline',WS/'baseline/tests'),('ch3_margins',WS/'ch3_3_3_1/tests'),('ch3_critical',WS/'ch3_3_3_2/tests')]
    for name,p in scopes:counts[name]=suite(p,name.upper()+'_TEST_LOG.txt')
    summary=main();main(['--output',str(ROOT/'replay')])
    manifest=json.loads((ROOT/'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for n,h in manifest.items():assert sha(ROOT/n)==h==sha(ROOT/'replay'/n),n
    from fixtures import scenarios
    from attack_core import simulate
    # Numerical patch and public model are checked after interleaved multiple scenarios.
    from qv_numeric_v2 import safe_root,InputError
    from decimal import Decimal as D
    configs=scenarios()
    a=[simulate(c) for c in configs]
    for _ in range(3):
        for c in reversed(configs):simulate(c)
        safe_root(D(1))
        try:safe_root(1.0)
        except InputError:pass
        else:raise AssertionError('Warm cache admitted wrong type')
    assert a==[simulate(c) for c in configs]
    v=dict(test_counts=counts,total_tests=sum(counts.values()),failures=0,errors=0,
        fixture_scenarios=summary['fixture_scenarios'],byte_identical_outputs=len(manifest),
        repeated_interleaved_scenarios_in_one_process=True,prior_files_unchanged=protect(),
        blockchain_transactions=False,Monte_Carlo=False,empirical_attack_probability_estimated=False)
    dump(ROOT/'VERIFICATION.json',v);print(json.dumps(v,indent=2),flush=True)
    return v
if __name__=='__main__':verify()
