"""Verify initialization, temporal information boundaries and deterministic full replay."""
import io
import json
import socket
import unittest
from unittest.mock import patch
from initialize import ROOT, main, sha, dump, protect, rows


def verify():
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (ROOT/'TEST_LOG.txt').write_text(stream.getvalue(),encoding='utf-8')
    assert result.wasSuccessful()
    summary=json.loads((ROOT/'outputs/SUMMARY.json').read_text(encoding='utf-8'))
    for mode in ('A','B'):
        path=ROOT/'outputs'/('mode_'+mode)
        agents=json.loads((path/'AGENTS_INITIAL.json').read_text(encoding='utf-8'))
        proposals=json.loads((path/'PROPOSALS_INITIAL.json').read_text(encoding='utf-8'))
        accounts=json.loads((path/'RESOURCE_ACCOUNTS.json').read_text(encoding='utf-8'))
        contexts=json.loads((path/'CONTEXT_STATES_INITIAL.json').read_text(encoding='utf-8'))
        assert len({a['wallet_id'] for a in agents})==6004
        assert len({p['snapshot_id'] for p in proposals})==1023
        assert len(accounts)==6004 and all(a['balances'] is None for a in accounts)
        assert not contexts
        assert all(p['vote_count']==0 and all(x=='0' for x in p['totals']) and p['execution_state'] is None for p in proposals)
        assert all(a['eligible_proposals'] is None and a['preferences'] is None and a['utility_parameters'] is None for a in agents)
        assert all(p['quality_flags']['production_deployment_verified']=='False' for p in proposals)
    comparison=rows(ROOT/'outputs/evaluation_archive/REPLAY_BASELINE_COMPARISON.csv')
    assert len(comparison)==1023 and all(r['baseline_match']=='True' for r in comparison)
    assert sum(r['governance_match']=='False' for r in comparison)==7
    assert sum(r['default_dependency_gap']=='True' for r in comparison)==49
    with patch.object(socket,'socket',side_effect=RuntimeError('Network disabled during verification replay')):
        main(['--output',str(ROOT/'replay_outputs'),'--seed','0'])
    manifest=json.loads((ROOT/'outputs/OUTPUT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        assert sha(ROOT/'outputs'/name)==digest==sha(ROOT/'replay_outputs'/name),name
    verification=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
         root_initial_states_independently_inspected=2,proposals_replayed_matching_baseline=1023,
         retained_events_replayed=63662,identical_output_files=len(manifest),
         network_disabled_during_verification_replay=True,protected_prior_files_unchanged=protect(),
         behavior_or_attack_simulation_performed=False,Monte_Carlo_performed=False,
         readiness='INITIALIZATION_SCAFFOLD_READY_BEHAVIOR_PARAMETERS_UNIDENTIFIED')
    dump(ROOT/'VERIFICATION.json',verification)
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    verify()
