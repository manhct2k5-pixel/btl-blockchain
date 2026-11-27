"""Check document/output agreement and delivery integrity."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from initialize import ROOT, dump, protect, sha, rows


def main():
    required=['ODD_FRAMEWORK.md','AGENT_NETWORK_MODEL.md','INITIALIZATION_DESIGN.md','STATE_VARIABLES.md',
              'INPUT_DATA_CONTRACT.md','INITIALIZATION_VALIDATION.md','CH4_4_1_1_REPORT_DRAFT.md','README.md']
    documents={name:(ROOT/name).read_text(encoding='utf-8') for name in required}
    assert all(documents.values())
    assert all('\ufffd' not in t for t in documents.values())
    headings=re.findall(r'^## ([1-7])\. ',documents['ODD_FRAMEWORK.md'],re.M)
    assert headings==list('1234567')
    verification=json.loads((ROOT/'VERIFICATION.json').read_text(encoding='utf-8'))
    summary=json.loads((ROOT/'outputs/SUMMARY.json').read_text(encoding='utf-8'))
    assert verification['tests']==33 and verification['failures']==verification['errors']==0
    assert str(verification['tests']) in documents['INITIALIZATION_VALIDATION.md']
    assert str(verification['tests']) in documents['CH4_4_1_1_REPORT_DRAFT.md']
    assert (summary['counts']['B_binding_wallets'],summary['counts']['B_binding'],summary['counts']['B_binding_votes'])==(6004,1023,63662)
    for mode in ('A','B'):
        state=summary['mode_'+mode+'_initial']
        assert (state['agents'],state['proposals'],state['initial_votes'],state['known_budget_accounts'])==(6004,1023,0,0)
    assert len(rows(ROOT/'outputs/evaluation_archive/OBSERVED_INCIDENCE.csv'))==63662
    assert len(rows(ROOT/'outputs/evaluation_archive/REPLAY_BASELINE_COMPARISON.csv'))==1023
    manifest=json.loads((ROOT/'outputs/OUTPUT_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        assert sha(ROOT/'outputs'/name)==digest==sha(ROOT/'replay_outputs'/name)
    dump(ROOT/'DOCUMENT_QA.json',dict(required_documents=len(required),ODD_elements=7,
         tests=verification['tests'],outputs_identical=len(manifest),protected_prior_files_unchanged=protect(),
         client_date='2026-11-19',timezone='Asia/Saigon',
         t0_utc=datetime.fromtimestamp(summary['replay_validation']['initial_time'],timezone.utc).isoformat(),
         readiness='4.1.1 completed; behavior and eligibility parameters remain unverified'))
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and
           'replay_outputs' not in p.parts and p.name!='DELIVERY_MANIFEST.json']
    dump(ROOT/'DELIVERY_MANIFEST.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
    print('Required documents: 8; ODD elements: 7; tests: 33; identical output files: 17; prior files unchanged:',protect())


if __name__=='__main__':
    main()
