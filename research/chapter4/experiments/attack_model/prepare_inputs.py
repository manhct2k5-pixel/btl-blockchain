"""Freeze preceding artifacts and record documents read. Never overwrite an audit."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (ROOT/'PROTECTED_INPUTS.json').exists():raise RuntimeError('Already frozen')
    protected={};reading={}
    for p in sorted(WS.rglob('*')):
        if not p.is_file() or ROOT in p.parents or any(x in p.parts for x in ('.git','.venv','__pycache__')):continue
        name=p.relative_to(WS).as_posix();protected[name]=sha(p)
        if p.suffix in ('.md','.py','.json') and p.stat().st_size<1000000:
            s=p.read_text(encoding='utf-8-sig')
            reading[name]={'characters':len(s),'sha256':protected[name]}
    for n,x in [('PROTECTED_INPUTS.json',protected),('READING_INDEX.json',reading)]:
        (ROOT/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prior_files':len(protected),'text_files_read':len(reading)}))
if __name__=='__main__':main()
