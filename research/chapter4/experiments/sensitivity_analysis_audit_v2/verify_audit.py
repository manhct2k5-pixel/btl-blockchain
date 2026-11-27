"""Execute the exact 13 legacy scopes, >0 tests each, plus new behavioral audit tests."""
import os,re,subprocess,sys,json,argparse
from audit_common import ROOT,WS,ORIGINAL,read,dump,protect,sha,digest,audit_code_manifest

SCOPES=[
 ('sensitivity',ORIGINAL/'tests'),
 ('main_audit_v2',WS/'chapter4/experiments/monte_carlo_main_audit_v2/tests'),
 ('main_mc',WS/'chapter4/experiments/monte_carlo_main/tests'),
 ('pilot',WS/'chapter4/experiments/monte_carlo_pilot/tests'),
 ('attack_model',WS/'chapter4/experiments/attack_model/tests'),
 ('initialization',WS/'chapter4/initialization/tests'),('behavior',WS/'chapter4/behavior/tests'),
 ('token_weighted',WS/'chapter4/mechanisms/token_weighted/tests'),
 ('qv',WS/'chapter4/mechanisms/quadratic_voting/tests'),
 ('ve_cap',WS/'chapter4/mechanisms/vote_escrow_capping/tests'),
 ('baseline',WS/'baseline/tests'),('ch3_margins',WS/'ch3_3_3_1/tests'),('ch3_critical',WS/'ch3_3_3_2/tests')]
def scope(name,path):
    if not path.exists():raise AssertionError('Missing test scope '+str(path))
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    r=subprocess.run([sys.executable,'-m','pytest',str(path),'-q','-p','no:cacheprovider'],
        capture_output=True,text=True,encoding='utf-8',env=env)
    (ROOT/(name.upper()+'_TEST_LOG.txt')).write_text(r.stdout+r.stderr,encoding='utf-8')
    m=re.search(r'(\d+)\s+passed',r.stdout)
    if r.returncode or not m or int(m.group(1))<=0:raise AssertionError(f'{name}: {r.stdout}\n{r.stderr}')
    if re.search(r'\d+\s+(failed|skipped|xfailed|error)',r.stdout):raise AssertionError('Incomplete scope '+name)
    return int(m.group(1))
def verify(legacy_only=False,phase='final'):
    protected=protect()
    required=[ORIGINAL/'SENSITIVITY_RESULTS.csv',ORIGINAL/'TYPE_A_REWEIGHTING_RESULTS.json',
        WS/'chapter4/experiments/monte_carlo_main/MC_MAIN_RESULTS.csv',
        WS/'chapter4/experiments/monte_carlo_main/WORLDS.json']
    for p in required:
        if not p.is_file():raise AssertionError('Fail closed: required result missing '+str(p))
    counts={}
    log=[]
    for name,path in SCOPES:
        count=scope(name,path);counts[name]=count
        line=f'{name}: {count} passed; nonzero discovery; sources SHA256 unchanged'
        print(line,flush=True);log.append(line)
        assert protect()==protected
    new_count=0
    if not legacy_only:
        new_count=scope('audit_new',ROOT/'tests/test_unit_audit.py' if phase=='pre' else ROOT/'tests')
        log.append(f'audit_new: {new_count} passed')
    result=dict(legacy_scope_counts=counts,legacy_scopes=len(counts),legacy_total=sum(counts.values()),
        new_audit_tests=new_count,total_tests=sum(counts.values())+new_count,failures=0,errors=0,
        prior_files_unchanged=protect(),legacy_only=legacy_only,phase=phase,
        code_manifest_sha256=digest(audit_code_manifest()),audit_contract_sha256=sha(ROOT/'AUDIT_CONTRACT.json'),
        no_zero_collection=True,required_results_fail_closed=True,existence_not_used_as_immutability_proof=True)
    dump(ROOT/('LEGACY_VERIFICATION.json' if legacy_only else 'VERIFICATION.json'),result)
    (ROOT/'TEST_EXECUTION_LOG.txt').write_text('\n'.join(log)+'\n'+json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--legacy-only',action='store_true');p.add_argument('--phase',choices=['pre','final'],default='final')
    args=p.parse_args();print(json.dumps(verify(args.legacy_only,args.phase),indent=2))
