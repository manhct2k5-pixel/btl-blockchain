"""One-time read-only inventory, schema/strategy evidence, and pre-outcome assumptions."""
import csv,hashlib,json,urllib.request
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def main():
    if (ROOT/'PROTECTED_INPUTS.json').exists(): raise RuntimeError('Preparation already frozen')
    protected={};audit={};reading={}
    scopes={'chapter3_final','chapter4','baseline','ch3_3_3_1','ch3_3_3_2','data_enrichment'}
    for p in sorted(WS.rglob('*')):
        if not p.is_file() or ROOT in p.parents or any(s in p.parts for s in ('.git','.venv','__pycache__')):continue
        name=p.relative_to(WS).as_posix();protected[name]=sha(p)
        if p.relative_to(WS).parts[0] in scopes:
            data=p.read_bytes();audit[name]={'sha256':protected[name],'bytes':len(data)}
            if p.suffix=='.md':
                content=data.decode('utf-8-sig')
                reading[name]={'headings':[line for line in content.splitlines() if line.startswith('#')],
                    'characters_read':len(content)}
    dump(ROOT/'PROTECTED_INPUTS.json',protected);dump(ROOT/'INPUT_AUDIT.json',audit)
    dump(ROOT/'READING_INDEX.json',reading)
    columns={}
    for p in sorted((WS/'data_enrichment').rglob('*.csv')):
        with p.open(encoding='utf-8-sig',newline='') as f:
            columns[p.relative_to(WS).as_posix()]=next(csv.reader(f),[])
    with (WS/'data_enrichment/proposal_metadata.csv').open(encoding='utf-8-sig',newline='') as f:
        records=list(csv.DictReader(f))
    names=Counter()
    def walk(x):
        if isinstance(x,dict):
            if isinstance(x.get('name'),str):names[x['name']]+=1
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    for row in records:walk(json.loads(row['strategies_json']))
    dump(ROOT/'LOCK_DATA_AUDIT.json',dict(scope='PROVIDED_WORKSPACE_NOT_ALL_CHAIN_HISTORY',
        csv_columns=columns,strategy_name_occurrences=dict(names),
        conclusion='NO_VERIFIED_DECENTRALAND_ESCROW_LEDGER_OR_VE_RIGHTS_MAPPING_IN_SUPPLIED_INPUT_CONTRACT',
        historical_ve_reconstructed=False,missing_fields=['lock_contract','lock_position_id','locked_amount_by_asset',
            'lock_created_at','lock_end_history','increase_extension_withdrawal_events','ve_rights_at_snapshot']))
    dump(ROOT/'CONFIG.json',dict(schema='4.2.3-v1',seed=19,
        cap=dict(variant='WALLET_ABSOLUTE_POST_AGGREGATION_NO_REDISTRIBUTION_V1',amount_vp='100000',
            source='A_FIXED_RESEARCH_ASSUMPTION_NOT_FITTED',determination='FROZEN_BEFORE_FIRST_CAPPING_OUTCOME_RUN',
            historical_preannouncement_verified=False,unit='VP'),
        ve=dict(variant='MANA_ONLY_LINEAR_REMAINING_TIME_FROZEN_SNAPSHOT_V1',asset='MANA',
            network='1',asset_contract='SYNTHETIC_NOT_DEPLOYED',max_lock_seconds=31536000,min_lock_seconds=86400,
            points_per_mana='1',weight_unit='VE_MANA_POINT',delegation='DISABLED',
            rounding='NONE_EXACT_RATIONAL',evidence='SYNTHETIC_ONLY'),
        outcome=dict(semantics='STRICT_YES_GT_NO_TIE_ZERO_REJECT',absolute_quorum='NONE_DECLARED_ASSUMPTION',
            eligibility='IDENTICAL_TO_QV_943_PRE_OUTCOME_SCREEN'),
        historical_ve='UNASSESSED_MISSING_LOCK_DATA',Monte_Carlo=False,sensitivity=False))
    sources=ROOT/'sources';sources.mkdir(exist_ok=True)
    repo='curvefi/curve-dao-contracts'
    req=urllib.request.Request(f'https://api.github.com/repos/{repo}/commits/master',headers={'User-Agent':'DAO-Research'})
    commit=json.load(urllib.request.urlopen(req))['sha']
    url=f'https://raw.githubusercontent.com/{repo}/{commit}/contracts/VotingEscrow.vy'
    (sources/'VotingEscrow.vy').write_bytes(urllib.request.urlopen(url).read())
    dump(ROOT/'SOURCE_MANIFEST.json',dict(curve_code={'commit':commit,'url':url,'sha256':sha(sources/'VotingEscrow.vy')},
        technical_references=['https://curve.readthedocs.io/dao-vecrv.html',
            'https://docs.curve.finance/user/vecrv/what-is-vecrv',
            'https://github.com/snapshot-labs/snapshot-docs/blob/1354a32a94cfa3b0613c2e8fc7e8c5725985fecf/user-guides/spaces/space-handbook/anti-whale.md']))
    print(json.dumps({'protected':len(protected),'audited':len(audit),'documents':len(reading),
        'strategy_names':sorted(names),'config_sha256':sha(ROOT/'CONFIG.json')},indent=2))
if __name__=='__main__':main()
