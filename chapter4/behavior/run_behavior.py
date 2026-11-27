"""Run only the explicitly marked small synthetic baseline fixture, or check readiness."""
import argparse
from dataclasses import asdict,is_dataclass
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from behavior import ROOT,WS,BehaviorSession,NotReady,InputError
from scenarios import fixture_bundle,build_fixture_world


def jsonable(value):
    if isinstance(value,Decimal):
        return format(value,'f')
    if isinstance(value,Fraction):
        return str(value.numerator) if value.denominator==1 else f'{value.numerator}/{value.denominator}'
    if isinstance(value,dict):
        return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [jsonable(v) for v in value]
    if is_dataclass(value):
        return jsonable(asdict(value))
    return value


def dump(path,value):
    path.write_text(json.dumps(jsonable(value),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def protected_check():
    manifest=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for name,digest in manifest.items():
        if sha(WS/name)!=digest:
            raise ValueError('Protected earlier file changed: '+name)
    return len(manifest)


def source_audit():
    paths=[]
    for name in ('chapter3_final','chapter4/initialization','baseline','data_enrichment'):
        paths += [p for p in (WS/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return {str(p.relative_to(WS)):dict(bytes=len(p.read_bytes()),sha256=sha(p)) for p in sorted(paths)}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('Output must remain in chapter4/behavior')
    output.mkdir(parents=True,exist_ok=True)
    protected_check()
    # Remove only known derived results in this task output folder, preventing stale
    # successful results from surviving a subsequent blocked/check-only configuration.
    for name in ('SUMMARY.json','DECISION_HISTORY.json','DECISION_VIEWS.json','EVIDENCE_LAYER.json',
                 'FINAL_BALLOTS.json','OUTPUT_MANIFEST.json'):
        (output/name).unlink(missing_ok=True)
    bundle=json.loads(args.config.read_text(encoding='utf-8'),parse_float=Decimal) if args.config else fixture_bundle()
    dump(output/'CONFIG.json',bundle)
    dump(output/'INPUT_AUDIT.json',source_audit())
    try:
        world=build_fixture_world(bundle)
        session=BehaviorSession(world,bundle['behavior'])
    except (InputError,KeyError,TypeError,ValueError) as exc:
        issues=exc.issues if isinstance(exc,NotReady) else [str(exc)]
        dump(output/'READINESS.json',dict(ready=False,issues=issues,run_performed=False))
        print('NOT_READY:', '; '.join(issues))
        return dict(ready=False,run_performed=False)
    dump(output/'READINESS.json',session.readiness)
    if args.check_only:
        return dict(ready=True,run_performed=False)
    summary=session.run()
    summary['protected_prior_files_unchanged']=protected_check()
    dump(output/'SUMMARY.json',summary)
    dump(output/'DECISION_HISTORY.json',session.log)
    dump(output/'DECISION_VIEWS.json',session.views)
    dump(output/'EVIDENCE_LAYER.json',[dict(wallet_id=w,snapshot_id=s,**v) for (w,s),v in sorted(session.evidence.items())])
    dump(output/'FINAL_BALLOTS.json',[asdict(s) for _,s in sorted(world.states.items())])
    dump(output/'OUTPUT_MANIFEST.json',{p.name:sha(p) for p in sorted(output.glob('*.json')) if p.name!='OUTPUT_MANIFEST.json'})
    print(json.dumps(jsonable(summary),ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    main()
