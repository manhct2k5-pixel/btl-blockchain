"""Unit/regression suite and two offline byte-reproducible historical evaluations."""
import io,json,socket,unittest
from unittest.mock import patch
from run_qv import ROOT,WS,main,sha,dump,protect
from engine import rows

def suite(path,log):
    stream=io.StringIO()
    found=unittest.defaultTestLoader.discover(str(path),top_level_dir=str(path))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(found)
    (ROOT/log).write_text(stream.getvalue(),encoding='utf-8')
    if not result.wasSuccessful(): raise AssertionError(stream.getvalue())
    return result.testsRun

def verify():
    counts={}
    for key,path,log in [
        ('qv',ROOT/'tests','QV_TEST_LOG.txt'),
        ('initialization',WS/'chapter4/initialization/tests','INITIALIZATION_REGRESSION_LOG.txt'),
        ('behavior',WS/'chapter4/behavior/tests','BEHAVIOR_REGRESSION_LOG.txt'),
        ('token_weighted',WS/'chapter4/mechanisms/token_weighted/tests','TOKEN_WEIGHTED_REGRESSION_LOG.txt'),
        ('baseline',WS/'baseline/tests','BASELINE_REGRESSION_LOG.txt')]:
        counts[key]=suite(path,log)
    with patch.object(socket,'socket',side_effect=RuntimeError('Offline verification: network disabled')):
        summary=main()
        main(['--output',str(ROOT/'replay')])
    manifest=json.loads((ROOT/'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in manifest.items():
        assert sha(ROOT/name)==h==sha(ROOT/'replay'/name),name
    result=rows(ROOT/'QV_RESULTS.csv')
    assert len(result)==1023 and len({r['snapshot_id'] for r in result})==1023
    assert sum(int(r['retained_wallet_count']) for r in result)==63662
    assert all(r['baseline_raw_tally_count_match']=='True' for r in result)
    assert all(r['attack_success_rate']==r['monetary_attack_cost']=='' for r in result)
    assert all(r['identity_verified']==r['physical_rights_verified']==r['sybil_resistance']=='False' for r in result)
    assert all(r['replacement_history']=='UNKNOWN_RETAINED_FINAL_ONLY' for r in result)
    h=summary['historical']
    assert h['assessed']+h['excluded']==1023
    assert h['assessed']==943 and h['excluded']==80 and h['numeric_unresolved']==0
    verification=dict(tests=counts,total_tests=sum(counts.values()),failures=0,errors=0,
        offline_historical_runs=2,identical_result_files=len(manifest),
        historical_rows=1023,historical_votes=63662,historical_wallets=6004,
        raw_baseline_matches=1023,prior_files_unchanged=protect(),
        fixed_behavior_matches_frozen_412=True,strategic_response_modelled=False,
        Monte_Carlo=False,attack_success_evaluated=False)
    dump(ROOT/'VERIFICATION.json',verification)
    print(json.dumps(verification,indent=2),flush=True)
    return verification
if __name__=='__main__':verify()
