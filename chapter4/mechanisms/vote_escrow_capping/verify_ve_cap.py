"""All existing workspace unittest suites plus 4.2.3, offline full runs and manifests."""
import io,json,socket,unittest,subprocess,sys
from unittest.mock import patch
from run_ve_cap import ROOT,WS,main,protect,sha,dump
from engine import rows

def suite(path,log):
    # A fresh interpreter per suite preserves its import/cache boundary. Existing
    # QV's untyped sqrt cache can alias Decimal(1) with float(1) after another suite.
    # No old code/test is edited; integration with our public entry points is tested.
    code="""import io,json,sys,unittest
stream=io.StringIO()
found=unittest.defaultTestLoader.discover(sys.argv[1],top_level_dir=sys.argv[1])
r=unittest.TextTestRunner(stream=stream,verbosity=2).run(found)
print(stream.getvalue())
print('COUNT_JSON='+json.dumps({'tests':r.testsRun}))
sys.exit(0 if r.wasSuccessful() else 1)
"""
    run=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,text=True,encoding='utf-8')
    (ROOT/log).write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:raise AssertionError(run.stdout+run.stderr)
    return json.loads(next(s.split('=',1)[1] for s in run.stdout.splitlines() if s.startswith('COUNT_JSON=')))['tests']

def verify():
    counts={}
    suites=[('ve_cap',ROOT/'tests'),('initialization',WS/'chapter4/initialization/tests'),
        ('behavior',WS/'chapter4/behavior/tests'),('token_weighted',WS/'chapter4/mechanisms/token_weighted/tests'),
        ('qv',WS/'chapter4/mechanisms/quadratic_voting/tests'),('baseline',WS/'baseline/tests'),
        ('ch3_margins',WS/'ch3_3_3_1/tests'),('ch3_critical',WS/'ch3_3_3_2/tests')]
    for name,path in suites:counts[name]=suite(path,name.upper()+'_TEST_LOG.txt')
    assert counts['ve_cap']>=51
    with patch.object(socket,'socket',side_effect=RuntimeError('Full mechanism runs must be offline')):
        summary=main()
        main(['--output',str(ROOT/'replay')])
    manifest=json.loads((ROOT/'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in manifest.items():assert sha(ROOT/name)==h==sha(ROOT/'replay'/name),name
    hist=rows(ROOT/'CAPPING_RESULTS.csv');ve=rows(ROOT/'VE_SCENARIO_RESULTS.csv')
    assert len(hist)==1023 and len({r['snapshot_id'] for r in hist})==1023
    assert sum(int(r['wallets']) for r in hist)==63662
    assert sum(r['status']=='ASSESSED' for r in hist)==943
    assert sum(r['changed_cap_vs_tw_common']=='True' for r in hist)==40
    assert all(r['ve_outcome']=='UNASSESSED_MISSING_LOCK_DATA' for r in hist)
    assert all(r['attack_success_rate']==r['attack_cost_usd']=='' for r in hist+ve)
    assert len(ve)==12 and len({r['scenario_id'] for r in ve})==12
    by={r['scenario_id']:r for r in ve}
    assert by['LINEAR_QUARTER']['ve_exact_weights_json']=='["25", "60"]'
    assert by['EXTEND_AFTER_SNAPSHOT']['ve_exact_weights_json']==by['LINEAR_QUARTER']['ve_exact_weights_json']
    assert by['EXTEND_BEFORE_SNAPSHOT']['ve_exact_weights_json']=='["75", "60"]'
    for name,value in [('DECISION_HISTORY.json','CAPPING_BEHAVIOR_DECISIONS.json'),
                       ('DECISION_VIEWS.json','CAPPING_BEHAVIOR_VIEWS.json')]:
        assert json.loads((ROOT/value).read_text(encoding='utf-8'))==json.loads((WS/'chapter4/behavior/outputs'/name).read_text(encoding='utf-8'))
    verification=dict(test_counts=counts,total_tests=sum(counts.values()),failures=0,errors=0,
        all_existing_test_files_executed=True,offline_full_runs=2,byte_identical_result_files=len(manifest),
        prior_files_unchanged=protect(),historical_rows=1023,assessed=943,excluded=80,
        historical_ve_assessed=0,ve_synthetic_scenarios=12,
        frozen_behavior_trace_matches=True,strategic_response_modelled=False,
        Monte_Carlo=False,sensitivity_analysis=False,attack_success_evaluated=False)
    dump(ROOT/'VERIFICATION.json',verification)
    print(json.dumps(verification,indent=2),flush=True)
    return verification
if __name__=='__main__':verify()
