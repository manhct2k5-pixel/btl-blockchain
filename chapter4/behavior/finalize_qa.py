"""Final artifact/invariant QA; no source or initialization outputs modified."""
import json
import re
from pathlib import Path
from collections import Counter
from run_behavior import ROOT,WS,dump,sha,protected_check


def main():
    required=['BEHAVIOR_MODEL.md','DECISION_RULES.md','UTILITY_INTEGRATION.md','INFORMATION_AND_SCHEDULING.md',
              'BEHAVIOR_INPUT_CONTRACT.md','BEHAVIOR_VALIDATION.md','CH4_4_1_2_REPORT_DRAFT.md','README.md']
    docs={name:(ROOT/name).read_text(encoding='utf-8') for name in required}
    assert all(docs.values()) and not any('@@' in t or '\ufffd' in t for t in docs.values())
    v=json.loads((ROOT/'VERIFICATION.json').read_text(encoding='utf-8'))
    s=json.loads((ROOT/'outputs/SUMMARY.json').read_text(encoding='utf-8'))
    assert v['failures']==v['errors']==0
    assert str(v['behavior_tests']) in docs['BEHAVIOR_VALIDATION.md']
    assert str(v['initialization_regression_tests']) in docs['BEHAVIOR_VALIDATION.md']
    assert (s['agents_in_scope'],s['proposal_scopes'],s['context_count'],s['decision_count'])==(4,2,5,9)
    assert not s['empirically_validated'] and not s['attack_or_defense_simulated'] and not s['Monte_Carlo']
    history=json.loads((ROOT/'outputs/DECISION_HISTORY.json').read_text(encoding='utf-8'))
    views=json.loads((ROOT/'outputs/DECISION_VIEWS.json').read_text(encoding='utf-8'))
    assert Counter(r['committed_action'].split(':')[0] for r in history)=={'VOTE':3,'WAIT':3,'KEEP':2,'REPLACE':1}
    assert all(r['physical_rights']=='UNVERIFIED' for r in history)
    forbidden={'official_status','final_outcome','scores_json','future_participants','candidate_rule','retained_events','gini','hhi'}
    assert all(not forbidden.intersection(view) for view in views)
    manifest=json.loads((ROOT/'outputs/OUTPUT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        assert sha(ROOT/'outputs'/name)==digest==sha(ROOT/'replay_outputs'/name),name
    links=0
    for text in docs.values():
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
            if not target.startswith(('http://','https://','#')):
                assert (ROOT/target).resolve().exists(),target
                links+=1
    report=dict(required_documents=len(required),behavior_tests=v['behavior_tests'],
                initialization_regression_tests=v['initialization_regression_tests'],
                synthetic_only=True,real_wallets_behavior_simulated=0,identical_output_files=len(manifest),
                previous_files_unchanged=protected_check(),local_links_verified=links,
                behavior_and_attack_scope_respected=True,client_date='2026-11-19',timezone='Asia/Saigon')
    dump(ROOT/'DOCUMENT_QA.json',report)
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and
           'replay_outputs' not in p.parts and p.name!='DELIVERY_MANIFEST.json']
    dump(ROOT/'DELIVERY_MANIFEST.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
