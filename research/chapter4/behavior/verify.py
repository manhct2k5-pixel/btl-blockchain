"""Software validation only: behavior tests, unchanged-init regression, deterministic fixture."""
import io
import json
import socket
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from behavior import ROOT,WS,BehaviorSession
from scenarios import fixture_bundle,build_fixture_world
from run_behavior import main,dump,sha,protected_check


def run_suite(path,name):
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(path),top_level_dir=str(path))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (ROOT/name).write_text(stream.getvalue(),encoding='utf-8')
    assert result.wasSuccessful(),stream.getvalue()
    return result.testsRun


def verify():
    behavior_tests=run_suite(ROOT/'tests','TEST_LOG.txt')
    init_tests=run_suite(WS/'chapter4/initialization/tests','INITIALIZATION_REGRESSION_LOG.txt')
    with patch.object(socket,'socket',side_effect=RuntimeError('Network disabled for synthetic fixture')):
        summary=main()
        second=main(['--output',str(ROOT/'replay_outputs')])
    manifest=json.loads((ROOT/'outputs/OUTPUT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        assert sha(ROOT/'outputs'/name)==digest==sha(ROOT/'replay_outputs'/name),name
    decisions=json.loads((ROOT/'outputs/DECISION_HISTORY.json').read_text(encoding='utf-8'))
    kinds=Counter(r['committed_action'].split(':')[0] for r in decisions)
    assert kinds=={'VOTE':3,'WAIT':3,'KEEP':2,'REPLACE':1},kinds
    by={r['snapshot_id']:r for r in summary['results']}
    assert list(by['SYNTHETIC_BINARY']['option_vp'])==[10,3] and by['SYNTHETIC_BINARY']['votes']==2
    assert list(by['SYNTHETIC_MULTI']['option_vp'])==[6,0,0] and by['SYNTHETIC_MULTI']['votes']==1
    assert all(r['computed_outcome']=='ACCEPTED' and r['execution_state'] is None for r in summary['results'])
    assert all(r['physical_rights']=='UNVERIFIED' for r in decisions)
    verification=dict(behavior_tests=behavior_tests,initialization_regression_tests=init_tests,
        failures=0,errors=0,synthetic_agents=summary['agents_in_scope'],synthetic_proposals=summary['proposal_scopes'],
        synthetic_contexts=summary['context_count'],synthetic_decisions=summary['decision_count'],
        committed_action_counts=dict(kinds),identical_output_files=len(manifest),
        protected_prior_files_unchanged=protected_check(),network_disabled_during_runs=True,
        real_wallets_behavior_simulated=0,historical_predictions_evaluated=0,attack_or_defense_simulated=False,
        Monte_Carlo=False,empirical_behavior_validation=False,initialization_api_modified=False)
    dump(ROOT/'VERIFICATION.json',verification)
    print(json.dumps(verification,ensure_ascii=False,indent=2))


if __name__=='__main__':
    verify()
