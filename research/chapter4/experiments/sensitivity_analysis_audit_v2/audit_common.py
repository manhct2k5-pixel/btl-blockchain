"""Read-only access to all frozen sources; all audit output stays in this folder."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
ORIGINAL=WS/'chapter4/experiments/sensitivity_analysis'
MAIN=WS/'chapter4/experiments/monte_carlo_main'
for p in (ORIGINAL,WS/'chapter4/behavior',WS/'chapter4/initialization',
    WS/'chapter4/mechanisms/token_weighted',WS/'chapter4/mechanisms/quadratic_voting',
    WS/'chapter4/mechanisms/vote_escrow_capping',WS/'chapter4/experiments/attack_model',MAIN):
    sys.path.insert(0,str(p))
from run_behavior import jsonable
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def canonical(x):return json.dumps(jsonable(x),sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(x):return hashlib.sha256(canonical(x).encode('utf-8')).hexdigest()
def audit_code_manifest():
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts}
def protect():
    m=read(ROOT/'PROTECTED_INPUTS.json')
    for n,h in m.items():
        if sha(WS/n)!=h:raise AssertionError('Frozen source changed: '+n)
    return len(m)
def prepare():
    if (ROOT/'PROTECTED_INPUTS.json').exists():raise RuntimeError('Audit baseline already frozen')
    prior={};text={}
    for p in sorted(WS.rglob('*')):
        if not p.is_file() or ROOT in p.parents or any(x in p.parts for x in ('.git','.venv','__pycache__','.pytest_cache')):continue
        n=p.relative_to(WS).as_posix();prior[n]=sha(p)
        if p.suffix in ('.py','.md','.json') and p.stat().st_size<1000000:
            text[n]={'sha256':prior[n],'characters_read':len(p.read_text(encoding='utf-8-sig'))}
    dump(ROOT/'PROTECTED_INPUTS.json',prior);dump(ROOT/'READING_INDEX.json',text)
    dump(ROOT/'AUDIT_CONTRACT.json',dict(version='4.4-AUDIT-V2',scope='RECONCILE_EXISTING_56_CELLS_NO_4_5',
        numerical_source_order=['WORLD_REEXECUTION_WITH_FROZEN_CODE_AND_INPUT','SOURCE_JSON_CSV','REPORT_TEXT'],
        baseline_world_source='monte_carlo_main/WORLDS.json',regenerate_seed_from='monte_carlo_main/MC_MAIN_CONTRACT.json',
        preserve_actual_original_seed=True,bootstrap_iterations=10000,bootstrap_seed=4302029,
        bootstrap_unit='PAIRED_WORLD_VECTOR_WITHIN_SPLIT_OTHER_STRATA',
        crossover_validity='UNIQUE_FINITE_ROOT_IN_CLOSED_UNIT_INTERVAL',
        targeted_split_grant='EXOGENOUS_SYNTHETIC_PREANNOUNCEMENT_NOT_REAL_PROPOSER_IDENTIFICATION',
        generic_preallocation='NOT_IMPLEMENTED_DO_NOT_CLASSIFY_AS_IMPOSSIBLE',
        output_world_rows=True,legacy_metadata_corrections=True,actual_blockchain_transactions=False,
        unrelated_main_run=False,section_4_5=False))
    dump(ROOT/'VE_SUPPLEMENT_CONTRACT.json',dict(version='VE-SUPPLEMENT-AUDIT-V1',
        source_worlds=200,source='monte_carlo_main/WORLDS.json',cells=6,
        remaining_of_feasible_max_fractions=['0.25','0.5','1'],amount_fractions=['0.5','1'],
        source_asset='MANA_DECLARED_BALANCE',end_rule='snapshot+floor(f*(Tmax-(snapshot-create_time)))',
        amount_rule='declared_MANA_balance*amount_fraction',historical_evidence=False,
        separate_from_original_duration_only_3_cells=True,code_preserves_future_extensions=True,
        future_extension_validity='DROP_NO_OP_OR_SHORTENING_EXTENSION_AFTER_LONGER_NEW_LOCK',
        active=False,activation_requires_audit_tests=True))
    print(json.dumps({'prior_files':len(prior),'text_files_read':len(text)}))
if __name__=='__main__':prepare()
