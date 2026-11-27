"""Artifact checks against verified results, no changes to earlier work."""
import json
import re
from decimal import Decimal
from collections import Counter
from run_token_weighted import ROOT,WS,sha,dump,protect
from engine import rows


def main():
    required=['TOKEN_WEIGHTED_MODEL.md','MECHANISM_DESIGN.md','HISTORICAL_VALIDATION.md','BEHAVIOR_INTEGRATION.md',
              'BASELINE_METRICS.csv','MECHANISM_TEST_RESULTS.md','CH4_4_2_1_REPORT_DRAFT.md','README.md']
    assert all((ROOT/name).is_file() and (ROOT/name).stat().st_size>0 for name in required)
    docs={name:(ROOT/name).read_text(encoding='utf-8') for name in required if name.endswith('.md')}
    assert all('@@' not in text and '\ufffd' not in text for text in docs.values())
    s=json.loads((ROOT/'SUMMARY.json').read_text(encoding='utf-8'))
    v=json.loads((ROOT/'VERIFICATION.json').read_text(encoding='utf-8'))
    assert v['failures']==v['errors']==0
    m=rows(ROOT/'BASELINE_METRICS.csv')
    a=[r for r in m if r['mode']=='A_HISTORICAL_RETAINED']
    b=[r for r in m if r['mode']=='B_SYNTHETIC_BEHAVIOR']
    assert (len(m),len(a),len(b))==(1025,1023,2)
    assert Counter(r['computed_outcome'] for r in a)=={'ACCEPTED':412,'REJECTED':606,'FINISHED':5}
    assert sum(r['default_dependency_gap']=='True' for r in a)==49
    assert sum(r['original_governance_match']=='False' for r in a)==7
    assert sum(r['budget_layer_unverified']=='True' for r in a)==10
    assert sum(r['concentration_status']=='ZERO_TOTAL_UNDEFINED' for r in a)==1
    assert sum(int(r['replacement_count']) for r in b)==1
    assert all(r['replacement_count']=='' for r in a)
    assert all(Decimal(r['total_vp'])==Decimal(r['total_effective_weight']) for r in m)
    manifest=json.loads((ROOT/'RESULT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in manifest.items():
        assert sha(ROOT/name)==h==sha(ROOT/'replay'/name)
    contract=json.loads((ROOT/'COMPARISON_CONTRACT.json').read_text(encoding='utf-8'))
    assert contract['baseline_config_sha256']==sha(ROOT/'BEHAVIOR_BASELINE_CONFIG.json')
    assert all(sha(WS/name)==h for name,h in contract['source_code_hashes'].items())
    assert contract['behavioral_requires_declared_mechanism_dependent_belief_rule']
    checked_links=0
    for text in docs.values():
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
            if not target.startswith(('http://','https://','#')):
                assert (ROOT/target).resolve().exists(),target
                checked_links+=1
    report=dict(required_deliverables=len(required),historical_rows=len(a),synthetic_rows=len(b),
        tests_passed=sum(v[k] for k in ('mechanism_tests','initialization_regression_tests','behavior_regression_tests',
                                       'preparation_baseline_regression_tests')),
        previous_files_unchanged=protect(),identical_result_files=len(manifest),
        local_links_verified=checked_links,comparison_configuration_frozen=True,
        only_token_weighted_implemented=True,attack_defense_Monte_Carlo_or_sensitivity_performed=False,
        client_date='2026-11-19',timezone='Asia/Saigon')
    dump(ROOT/'DOCUMENT_QA.json',report)
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'replay' not in p.parts and p.name!='DELIVERY_MANIFEST.json']
    dump(ROOT/'DELIVERY_MANIFEST.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
