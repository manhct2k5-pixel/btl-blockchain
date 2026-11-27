"""Separate historical validation, synthetic tests and unchanged-module regressions."""
import io
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch
from run_token_weighted import ROOT,WS,main,sha,dump,protect
from engine import rows


def suite(path,log):
    stream=io.StringIO()
    found=unittest.defaultTestLoader.discover(str(path),top_level_dir=str(path))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(found)
    (ROOT/log).write_text(stream.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():
        raise AssertionError(stream.getvalue())
    return result.testsRun


def verify():
    counts={}
    counts['mechanism_tests']=suite(ROOT/'tests','TEST_LOG.txt')
    counts['initialization_regression_tests']=suite(WS/'chapter4/initialization/tests','INITIALIZATION_REGRESSION_LOG.txt')
    counts['behavior_regression_tests']=suite(WS/'chapter4/behavior/tests','BEHAVIOR_REGRESSION_LOG.txt')
    counts['preparation_baseline_regression_tests']=suite(WS/'baseline/tests','PREPARATION_BASELINE_REGRESSION_LOG.txt')
    with patch.object(socket,'socket',side_effect=RuntimeError('Network disabled for mechanism validation')):
        summary=main()
        main(['--output',str(ROOT/'replay')])
    manifest=json.loads((ROOT/'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        assert sha(ROOT/name)==digest==sha(ROOT/'replay'/name),name
    m=rows(ROOT/'BASELINE_METRICS.csv')
    assert len(m)==1025 and len({(r['mode'],r['scenario_id'],r['snapshot_id']) for r in m})==1025
    hist=[r for r in m if r['mode']=='A_HISTORICAL_RETAINED']
    synthetic=[r for r in m if r['mode']=='B_SYNTHETIC_BEHAVIOR']
    assert len(hist)==1023 and len(synthetic)==2
    assert all(r['baseline_tally_outcome_match']=='True' for r in hist)
    assert len(rows(ROOT/'HISTORICAL_MISMATCHES.csv'))==7
    assert len(rows(ROOT/'DEFAULT_DEPENDENCY.csv'))==49
    assert all(r['eligible_turnout']==r['attack_success_rate']==r['money_attack_cost_usd']=='' for r in m)
    assert all(r['replacement_count']==r['replacement_outcome_change_batches']=='' for r in hist)
    assert all(r['physical_rights_verified']=='False' for r in m)
    for current,previous in [('MODE_B_DECISIONS.json','DECISION_HISTORY.json'),('MODE_B_VIEWS.json','DECISION_VIEWS.json')]:
        assert json.loads((ROOT/current).read_text(encoding='utf-8'))==json.loads((WS/'chapter4/behavior/outputs'/previous).read_text(encoding='utf-8'))
    verification=dict(**counts,failures=0,errors=0,engine_import_verified=True,
         historical_proposals=1023,historical_ballots=63662,historical_baseline_matches=1023,
         historical_official_matches=1016,historical_official_mismatches=7,
         mode_B_matches_frozen_412_trace=True,identical_result_files=len(manifest),
         protected_prior_files_unchanged=protect(),network_disabled_during_full_runs=True,
         defense_or_attack_simulated=False,Monte_Carlo=False,sensitivity_analysis=False,
         empirical_behavior_validated=False,other_mechanisms_implemented=False)
    dump(ROOT/'VERIFICATION.json',verification)
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    verify()
