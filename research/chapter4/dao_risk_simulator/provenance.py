"""Read-only research sources and SHA-256 preservation boundary."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[1]
AUDIT=WS/'chapter4/experiments/sensitivity_analysis_audit_v2'
for p in [WS/'baseline',WS/'chapter4/initialization',WS/'chapter4/behavior',
    WS/'chapter4/mechanisms/token_weighted',WS/'chapter4/mechanisms/quadratic_voting',
    WS/'chapter4/mechanisms/vote_escrow_capping',WS/'chapter4/experiments/attack_model',
    WS/'chapter4/experiments/monte_carlo_main',AUDIT]:
    sys.path.insert(0,str(p))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def freeze():
    if (ROOT/'PROTECTED_INPUTS.json').exists():raise ValueError('Baseline already frozen')
    protected={};index={}
    scopes=['chapter3_final','chapter4/initialization','chapter4/behavior','chapter4/mechanisms',
        'chapter4/experiments','baseline']
    for p in sorted(WS.rglob('*')):
        if not p.is_file() or ROOT in p.parents or any(n in p.parts for n in ('__pycache__','.pytest_cache','.git','.venv')):continue
        n=p.relative_to(WS).as_posix();data=p.read_bytes();protected[n]=hashlib.sha256(data).hexdigest()
        if any(n.startswith(s+'/') for s in scopes):
            index[n]={'bytes_read':len(data),'sha256':protected[n]}
    dump(ROOT/'PROTECTED_INPUTS.json',protected);dump(ROOT/'READING_INDEX.json',index)
    return len(protected)
def protect():
    m=read(ROOT/'PROTECTED_INPUTS.json')
    for n,h in m.items():
        if sha(WS/n)!=h:raise AssertionError('Prior source changed: '+n)
    return len(m)
if __name__=='__main__':print(freeze())
