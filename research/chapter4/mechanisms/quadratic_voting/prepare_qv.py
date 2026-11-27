"""Read-only prior-input audit and pinned primary-source capture; run before coding."""
from pathlib import Path
import hashlib,json,urllib.request,datetime
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def main():
    prior={}
    audit={}
    scopes={'chapter3_final','chapter4','baseline','data_enrichment','ch3_3_3_1','ch3_3_3_2'}
    for p in sorted(WS.rglob('*')):
        if not p.is_file() or ROOT in p.parents or any(x in p.parts for x in ('.git','.venv','__pycache__')): continue
        name=p.relative_to(WS).as_posix()
        prior[name]=sha(p)
        if p.relative_to(WS).parts[0] in scopes:
            data=p.read_bytes()
            audit[name]={'sha256':prior[name],'bytes':len(data)}
    dump(ROOT/'PROTECTED_INPUTS.json',prior)
    dump(ROOT/'INPUT_AUDIT.json',audit)
    dest=ROOT/'sources';dest.mkdir(exist_ok=True)
    sources={}
    for repo,branch,filename,local in [
        ('snapshot-labs/snapshot.js','master','src/voting/quadratic.ts','snapshot_quadratic.ts'),
        ('snapshot-labs/snapshot-docs','master','user-guides/spaces/space-handbook/anti-whale.md','snapshot_anti_whale.md')]:
        api=f'https://api.github.com/repos/{repo}/commits/{branch}'
        req=urllib.request.Request(api,headers={'User-Agent':'Decentraland-Research-QV'})
        commit=json.load(urllib.request.urlopen(req))['sha']
        url=f'https://raw.githubusercontent.com/{repo}/{commit}/{filename}'
        (dest/local).write_bytes(urllib.request.urlopen(url).read())
        sources[local]={'repo':repo,'commit':commit,'url':url,'sha256':sha(dest/local)}
    sources['references']=[
        'https://www.mdpi.com/2078-2489/13/6/305',
        'https://www.aeaweb.org/articles?id=10.1257/pandp.20181002']
    dump(ROOT/'SOURCE_MANIFEST.json',sources)
    print(json.dumps({'protected':len(prior),'audited':len(audit),'sources':sources},indent=2))
if __name__=='__main__': main()
