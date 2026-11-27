"""Offline application service. All decisions/tallies belong to the verified model."""
from copy import deepcopy
from decimal import Decimal,localcontext
from fractions import Fraction as F
import csv,hashlib,io,json,math,time
from functools import lru_cache
import pandas as pd
import numpy as np
from provenance import ROOT,WS,AUDIT,read,sha
from main_generator import generate_world,load_contract,decimal_text,jsonable
from information_v2 import audited_simulate,declared_grant,declared_block
from attack_core import parse_config,make_policy,NotReady
from sensitivity_simulator import modify_alias_count
from ve_audit import supplement_variant

VERSION='DAO-RISK-SIMULATOR-1.0'
SCHEMA='dao-risk-request-v1'
MAIN=WS/'chapter4/experiments/monte_carlo_main'
def canonical(x):return json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def request_hash(request):return digest(request)

def module_manifest():
    scopes=['baseline','chapter4/initialization','chapter4/behavior','chapter4/mechanisms/token_weighted',
        'chapter4/mechanisms/quadratic_voting','chapter4/mechanisms/vote_escrow_capping',
        'chapter4/experiments/attack_model','chapter4/experiments/monte_carlo_main',
        'chapter4/experiments/sensitivity_analysis','chapter4/experiments/sensitivity_analysis_audit_v2']
    files={}
    for scope in scopes:
        for p in (WS/scope).glob('*.py'):files[p.relative_to(WS).as_posix()]=sha(p)
    for p in (ROOT/'service.py',ROOT/'provenance.py',ROOT/'app.py',MAIN/'MC_MAIN_CONTRACT.json'):
        if not p.is_file():continue
        files[p.relative_to(WS).as_posix()]=sha(p)
    return dict(app_version=VERSION,files=files,model_fingerprint=digest(files),
        entrypoint='information_v2.audited_simulate -> main_patch.simulate -> attack_core.simulate',
        qv='qv_numeric_v2.WalletSqrtNumericV2; interval-certified sqrt, no floor',offline=True)

def verification_status():
    p=ROOT/'VERIFICATION.json'
    current=module_manifest()['model_fingerprint']
    if not p.exists():return dict(verified=False,status='Chưa xác minh phiên bản ứng dụng này')
    try:v=read(p)
    except (OSError,ValueError):
        return dict(verified=False,status='Không đọc được hồ sơ xác minh; cần chạy lại kiểm thử')
    if not isinstance(v,dict):
        return dict(verified=False,status='Hồ sơ xác minh không hợp lệ; cần chạy lại kiểm thử')
    ok=(v.get('model_fingerprint')==current
        and all(type(v.get(k)) is int and v[k]==0 for k in ('failures','errors','skips'))
        and type(v.get('total_tests')) is int and v['total_tests']>0
        and v.get('zero_collection') is False)
    return dict(v,verified=ok,status='Đã xác minh' if ok else 'Mã đã thay đổi; cần chạy lại kiểm thử')

def number(x,name='Giá trị',positive=False,maximum=10**15):
    if isinstance(x,bool):raise ValueError(name+': không phải số hợp lệ')
    try:d=Decimal(str(x))
    except Exception as e:raise ValueError(name+': cần số thập phân hữu hạn') from e
    if not d.is_finite() or d<0 or (positive and d==0) or d>maximum:
        raise ValueError(name+': ngoài miền hữu hạn không âm'+(' và lớn hơn 0' if positive else ''))
    return F(d)
def integer(x,name,lo=0,hi=2**63-1):
    if type(x) is not int or not lo<=x<=hi:raise ValueError(name+': cần số nguyên trong miền cho phép')
    return x

def templates():
    labels={'SPLIT':'Chia nguồn VP trước snapshot','SWITCH':'Đổi phiếu trong quyền hiện có',
        'BRIBE_E':'Hối lộ công khai có điều kiện','MOBILIZE':'Huy động quyền sẵn có',
        'FLASH':'Vay chớp nhoáng, số dư snapshot không đổi','HELD_LOAN':'Khoản vay nắm giữ chưa đặc tả'}
    return [dict(id=k,label=v,group='MAIN',family=k) for k,v in labels.items()]+[
        dict(id='VE_'+k,label='Vote-Escrow · '+labels[k],group='VE',family=k) for k in ('SWITCH','BRIBE_E','MOBILIZE')]

def _finite_tree(x,depth=0):
    if depth>25:raise ValueError('JSON quá sâu')
    if isinstance(x,float) and not math.isfinite(x):raise ValueError('Không chấp nhận NaN/Infinity')
    if isinstance(x,dict):
        if len(x)>500:raise ValueError('Đối tượng quá lớn')
        for v in x.values():_finite_tree(v,depth+1)
    elif isinstance(x,list):
        if len(x)>1000:raise ValueError('Danh sách quá lớn')
        for v in x:_finite_tree(v,depth+1)

def _partition(c,total,distribution):
    keys=[w for w,v in c['voters'].items() if F(v['vp'])>0]
    if not keys:raise ValueError('Không có nguồn VP để phân bổ')
    if distribution=='preserve':weights=[F(c['voters'][w]['vp']) for w in keys]
    elif distribution=='equal':weights=[F(1)]*len(keys)
    elif distribution=='concentrated':weights=[F(7)]+[F(1)]*(len(keys)-1)
    else:raise ValueError('Phân bố VP chưa được hỗ trợ')
    values=[]
    with localcontext() as ctx:
        ctx.prec=80
        for w in weights[:-1]:
            a=total*w/sum(weights);values.append(F(Decimal(a.numerator)/Decimal(a.denominator)))
    values.append(total-sum(values))
    if any(v<=0 for v in values):raise ValueError('Phân bố tạo nguồn không dương')
    for w,v in zip(keys,values):c['voters'][w]['vp']=decimal_text(v)
    assert sum(F(v['vp']) for v in c['voters'].values())==total

OVERRIDES={'total_vp','distribution','alias_count','budget','cap_vp','snapshot_time','published_at','decision_at',
    'allocation_at','resource_utility','risk_utility','opportunity_utility','capital_utility','mana_scale',
    'lock_amount_fraction','lock_remaining_fraction','information_condition','grant_enabled','block_enabled','allocation_strategy'}

def build_scenario(template_id='SPLIT',seed=4302027,replicate=0,overrides=None):
    o=deepcopy(overrides or {})
    if set(o)-OVERRIDES:raise ValueError('Tham số không được mô hình hỗ trợ: '+str(sorted(set(o)-OVERRIDES)))
    t=next((t for t in templates() if t['id']==template_id),None)
    if t is None:raise ValueError('Mẫu kịch bản không tồn tại')
    integer(seed,'Seed',0,2**63-1);integer(replicate,'Replicate',0,1000000)
    gc=deepcopy(load_contract());gc['master_seed']=seed
    gc['distributions']['family_main' if t['group']=='MAIN' else 'family_ve']['parameters']['values']=[t['family']]
    w=generate_world(gc,t['group'],replicate);c=w['config']
    if t['group']=='VE' and ('total_vp' in o or 'distribution' in o):raise ValueError('VE dùng MANA, không cấp thêm VP độc lập')
    if t['group']=='MAIN' and any(k in o for k in ('mana_scale','lock_amount_fraction','lock_remaining_fraction')):
        raise ValueError('Tham số khóa chỉ dùng cho VE')
    if 'total_vp' in o or 'distribution' in o:
        total=number(o.get('total_vp',sum(F(v['vp']) for v in c['voters'].values())),'Tổng VP',True)
        _partition(c,total,o.get('distribution','preserve'))
    if c['attack']['family']=='SPLIT':
        k=o.get('alias_count',4)
        if type(k) is not int or k not in (1,2,4,8):raise ValueError('Số ví hỗ trợ: 1, 2, 4, 8')
        c=modify_alias_count(c,k,gc['base_voters'])
    elif 'alias_count' in o:raise ValueError('Số ví chia chỉ áp dụng cho SPLIT')
    if 'budget' in o:c['principals'][c['attacker']]['budget']=decimal_text(number(o['budget'],'Ngân sách'))
    if 'cap_vp' in o:c['cap_vp']=decimal_text(number(o['cap_vp'],'Trần Capping',True))
    for k in ('resource_utility','risk_utility','opportunity_utility','capital_utility'):
        if k in o:c['attack'][k]=decimal_text(number(o[k],k))
    if 'snapshot_time' in o:
        new=integer(o['snapshot_time'],'Snapshot',86401);delta=new-c['proposal']['snapshot_time']
        for k in ('snapshot_time','created','start','end'):c['proposal'][k]+=delta
        for k in ('published_at','decision_at','allocation_at'):c['attack'][k]+=delta
        for v in c['voters'].values():v['rights_at']+=delta
        if c['ve']:
            c['ve']['genesis']+=delta
            for e in c['ve']['events']:e['time']+=delta;e['end']+=delta
    for k in ('published_at','decision_at','allocation_at'):
        if k in o:c['attack'][k]=integer(o[k],k)
    if t['group']=='VE':
        if 'mana_scale' in o:
            scale=number(o['mana_scale'],'Hệ số MANA',True,1000000)
            for wallet in c['ve']['balances_mana']:
                c['ve']['balances_mana'][wallet]=decimal_text(F(c['ve']['balances_mana'][wallet])*scale)
                c['voters'][wallet]['vp']=c['ve']['balances_mana'][wallet]
            for e in c['ve']['events']:e['amount']=decimal_text(F(e['amount'])*scale)
        if 'lock_amount_fraction' in o or 'lock_remaining_fraction' in o:
            # A two-factor transformation is explicit; unspecified dimension has a declared default 1.
            amount=number(o.get('lock_amount_fraction','1'),'Tỷ lệ amount',True,1)
            rem=number(o.get('lock_remaining_fraction','1'),'Tỷ lệ remaining',True,1)
            c=supplement_variant(c,decimal_text(rem),decimal_text(amount))
    req=dict(schema=SCHEMA,config=c,information_condition=o.get('information_condition','INFORMED_PROPOSER'),
        grant=None,block_rule=None,allocation_strategy=o.get('allocation_strategy','TARGETED_PROPOSAL'),
        source=dict(template_id=template_id,master_seed=seed,replicate=replicate,group=t['group'],
            generator_version=w['generator_version'],generator_contract=gc,overrides=jsonable(o),
            evidence='SYNTHETIC_ASSUMPTION_NOT_OBSERVED',calibrated=False))
    if o.get('grant_enabled') is True:req['grant']=declared_grant(c)
    if o.get('block_enabled') is True:req['block_rule']=declared_block(c)
    validate_request(req);return req

def validate_request(req):
    if not isinstance(req,dict) or set(req)!={'schema','config','information_condition','grant','block_rule','allocation_strategy','source'}:
        raise ValueError('Sai schema request; cần cấu hình đầy đủ được xuất từ ứng dụng')
    if req['schema']!=SCHEMA:raise ValueError('Phiên bản schema không hỗ trợ')
    _finite_tree(req)
    if req['information_condition'] not in ('INFORMED_PROPOSER','UNINFORMED_VOTER','BLOCKED'):raise ValueError('Điều kiện thông tin không hợp lệ')
    if req['allocation_strategy'] not in ('TARGETED_PROPOSAL','GENERAL_PREALLOCATION'):raise ValueError('Chiến lược phân bổ không hợp lệ')
    c=req['config']
    if not isinstance(c,dict) or not isinstance(req['source'],dict):raise ValueError('Config và source phải là đối tượng JSON')
    for field in ('voters','principals','proposal','attack'):
        if not isinstance(c.get(field),dict):raise ValueError(field+': cần đối tượng JSON')
    for field in ('voters','principals'):
        if any(not isinstance(v,dict) for v in c[field].values()):
            raise ValueError(field+': mỗi phần tử cần đối tượng JSON')
    if len(c.get('voters',{}))>100 or len(c.get('principals',{}))>100:raise ValueError('Vượt giới hạn 100 ví/chủ thể')
    number(c.get('cap_vp'),'Trần Capping',True)
    integer(c.get('seed'),'Model seed',0,2**256-1)
    for v in c.get('voters',{}).values():number(v.get('vp'),'VP')
    for p in c.get('principals',{}).values():number(p.get('budget'),'Ngân sách')
    if req['grant'] is not None:
        g=req['grant']
        if not isinstance(g,dict) or not isinstance(g.get('role_bindings'),dict):raise ValueError('Grant cần role_bindings có cấu trúc')
        if any(not isinstance(v,list) for v in g['role_bindings'].values()):raise ValueError('Role binding cần danh sách vai trò')
    if req['block_rule'] is not None and not isinstance(req['block_rule'],dict):raise ValueError('Block rule cần đối tượng')
    try:parse_config(c);make_policy(c)
    except NotReady:pass
    except Exception as e:raise ValueError('Cấu hình mô hình không hợp lệ: '+str(e)) from e
    return req

def import_scenario(text):
    if not isinstance(text,str):raise ValueError('Cấu hình cần văn bản JSON')
    if len(text.encode('utf-8'))>1000000:raise ValueError('Cấu hình vượt 1 MB')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('Khóa JSON lặp: '+k)
            d[k]=v
        return d
    try:
        req=json.loads(text,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Không hữu hạn: '+x)))
    except RecursionError as exc:raise ValueError('JSON quá sâu') from exc
    return validate_request(req)

def state_of(r):
    if r.get('eligible') is None:return 'NOT_READY'
    if not r['eligible']:return 'INFEASIBLE'
    if not r.get('attempted'):return 'DECLINED'
    if r.get('success') is None:return 'OUTCOME_UNKNOWN'
    return 'ATTEMPTED_SUCCESS' if r['success'] else 'ATTEMPTED_FAILURE'

def _summary(results):
    out=[]
    for m in dict.fromkeys(r['mechanism'] for r in results):
        rs=[r for r in results if r['mechanism']==m];e=sum(r['eligible'] is True for r in rs)
        a=sum(r['attempted'] is True for r in rs);s=sum(r['policy_success'] is True for r in rs)
        # Unknown attempted results stay outside the known-outcome denominator, explicitly disclosed.
        unknown=sum(r['attempted'] is True and r['success'] is None for r in rs)
        out.append(dict(mechanism=m,worlds=len(rs),eligible=e,attempted=a,success=s,unknown_attempted=unknown,
            rate_eligible=None if not e or unknown else s/e,rate_attempted=None if not a or unknown else s/a))
    return out

def _pairwise(results):
    grouped={}
    for r in results:grouped.setdefault(r['world_id'],{})[r['mechanism']]=r
    out=[];ms=list(dict.fromkeys(r['mechanism'] for r in results))
    for i,m in enumerate(ms):
        for n in ms[i+1:]:
            pairs=[(d[m],d[n]) for d in grouped.values() if m in d and n in d and d[m]['eligible'] is True and d[n]['eligible'] is True
                and d[m]['policy_success'] is not None and d[n]['policy_success'] is not None]
            vals=[int(b['policy_success'])-int(a['policy_success']) for a,b in pairs]
            out.append(dict(reference=m,comparison=n,paired_worlds=len(vals),
                difference_rate=sum(vals)/len(vals) if vals else None,
                comparison_only=sum(x==1 for x in vals),reference_only=sum(x==-1 for x in vals)))
    return out

def run_scenario(request,mechanisms=None):
    validate_request(request);req=deepcopy(request);c=req['config']
    ms=[c['mechanism']] if mechanisms is None else mechanisms
    if (not isinstance(ms,(list,tuple)) or not ms
        or any(not isinstance(m,str) for m in ms) or len(ms)!=len(set(ms))):
        raise ValueError('Danh sách cơ chế không hợp lệ')
    if any(m not in ('TW','QV','CAP','VE') for m in ms):raise ValueError('Cơ chế không được hỗ trợ')
    if c.get('ve') is not None:
        if list(ms)!=['VE']:raise ValueError('VE dùng nhóm MANA riêng, không so sánh trực tiếp TW/QV/CAP')
    elif 'VE' in ms:raise ValueError('Thiếu nguồn MANA và lịch sử khóa cho VE')
    results=[];start=time.perf_counter();manifest=module_manifest()
    for m in ms:
        cfg=deepcopy(c);cfg['mechanism']=m
        try:r=audited_simulate(cfg,req['information_condition'],deepcopy(req['grant']),deepcopy(req['block_rule']),req['allocation_strategy'])
        except NotReady as e:r=dict(eligible=None,attempted=False,success=None,policy_success=None,status=str(e),no_attack=None,with_attack=None,resources={},responses=[],views=[])
        r=jsonable(r);r.update(world_id=c['scenario_id'],mechanism=m,family=c['attack']['family'],state=state_of(r),
            reason=r.get('reason') or r.get('status') or 'Xem quyết định và phản ứng',input_hash=digest(cfg),
            validation_state='ELIGIBLE' if r.get('eligible') is True else state_of(r),
            model_seed=c['seed'],source=req['source'])
        for k in ('no_attack','with_attack'):
            if r.get(k):r[k]['total_effective']=r[k].get('effective_total')
        # Check full per-principal budgets, source conservation and exact cash identities.
        for p,a in (r.get('resources') or {}).items():
            assert F(a['initial'])==F(c['principals'][p]['budget'])
            assert F(a['liquid'])+F(a['escrow'])==F(a['initial'])-F(a['external_fees'])-F(a['paid'])+F(a['received'])
        if r.get('no_attack') and r.get('with_attack'):
            registry=sum(F(v['vp']) for v in c['voters'].values())
            assert F(r['with_attack']['source_vp'])<=registry
            if c['attack']['family']!='MOBILIZE':assert F(r['no_attack']['source_vp'])==F(r['with_attack']['source_vp'])
        results.append(r)
    return dict(request=req,input_hash=request_hash(req),model_fingerprint=manifest['model_fingerprint'],manifest=manifest,
        results=results,summary=_summary(results),paired_comparisons=_pairwise(results),elapsed_seconds=time.perf_counter()-start,
        evidence='SYNTHETIC_ASSUMPTION_NOT_REAL_ATTACK_PROBABILITY',cache_used=False)

def run_batch(template_id,seed,count,overrides=None,mechanisms=None,progress=None):
    integer(count,'Số world',1,30);out=[];requests=[];start=time.perf_counter()
    for i in range(count):
        q=build_scenario(template_id,seed,i,overrides);b=run_scenario(q,mechanisms);out.extend(b['results']);requests.append(q)
        if progress:progress(i+1,count)
    return dict(request=requests[0],batch_requests=requests,input_hash=digest(requests),model_fingerprint=b['model_fingerprint'],
        manifest=b['manifest'],results=out,summary=_summary(out),paired_comparisons=_pairwise(out),
        elapsed_seconds=time.perf_counter()-start,evidence='NEW_FAMILY_CONDITIONED_SYNTHETIC_WORLDS',cache_used=False,
        assumptions='Original declared distributions conditional on selected family; common world across compatible mechanisms')

def run_sensitivity(request,parameter,values):
    validate_request(request)
    if parameter not in ('alias_count','cap_vp','budget','information_condition','lock_remaining_fraction','lock_amount_fraction'):
        raise ValueError('Tham số độ nhạy không hỗ trợ')
    if not 2<=len(values)<=8:raise ValueError('Chọn 2 đến 8 giá trị')
    if len({canonical(v) for v in values})!=len(values):raise ValueError('Giá trị khảo sát phải khác nhau')
    out=[];requests=[];start=time.perf_counter()
    for val in values:
        q=deepcopy(request);c=q['config']
        if parameter=='alias_count':
            if c['attack']['family']!='SPLIT' or type(val) is not int or val not in (1,2,4,8):raise ValueError('Alias chỉ cho SPLIT: 1/2/4/8')
            q['config']=modify_alias_count(c,val,load_contract()['base_voters'])
        elif parameter in ('cap_vp','budget'):
            x=decimal_text(number(val,parameter,parameter=='cap_vp'))
            if parameter=='cap_vp':c['cap_vp']=x
            else:c['principals'][c['attacker']]['budget']=x
        elif parameter=='information_condition':
            q['information_condition']=val
            if val!='INFORMED_PROPOSER':q['grant']=None
            if val!='BLOCKED':q['block_rule']=None
        else:
            if c['ve'] is None:raise ValueError('Tham số khóa chỉ cho VE')
            f=number(val,parameter,True,1);s=c['proposal']['snapshot_time'];v=c['ve']
            if parameter=='lock_amount_fraction':
                for e in v['events']:
                    if e['kind']=='CREATE':e['amount']=decimal_text(F(v['balances_mana'][e['wallet']])*f)
            else:
                for e in v['events']:
                    if e['kind']=='CREATE':e['end']=s+int(f*(v['max_seconds']-(s-e['time'])))
                ends={e['wallet']:e['end'] for e in v['events'] if e['kind']=='CREATE'}
                v['events']=[e for e in v['events'] if e['kind']!='EXTEND' or e['end']>ends[e['wallet']]]
        b=run_scenario(q,['VE'] if c['ve'] else ['TW','QV','CAP'])
        for r in b['results']:r['factor_name']=parameter;r['factor_value']=val
        out.extend(b['results']);requests.append(q)
    # Sensitivity cells are not pooled into one Monte Carlo probability.
    summary=[]
    for val in values:
        for r in _summary([r for r in out if r['factor_value']==val]):r.update(factor_name=parameter,factor_value=val);summary.append(r)
    return dict(request=deepcopy(request),sensitivity_requests=requests,input_hash=digest([request,parameter,values]),
        model_fingerprint=b['model_fingerprint'],manifest=b['manifest'],results=out,summary=summary,
        paired_comparisons=[],elapsed_seconds=time.perf_counter()-start,evidence='TYPE_B_NEW_MODEL_EXECUTION',cache_used=False)

def crossover_info():return read(AUDIT/'CROSSOVER_BOOTSTRAP_RESULTS.json')
def type_a(p):
    p=float(p)
    if not math.isfinite(p) or not 0<=p<=1:raise ValueError('p phải trong [0,1]')
    source=read(AUDIT/'BOOTSTRAP_PAIRED_INPUT.json');s=np.array(source['vectors']['SPLIT']);o=np.array(source['vectors']['OTHER'])
    draws=pd.read_csv(AUDIT/'CROSSOVER_BOOTSTRAP_DRAWS.csv');out=[]
    for j,m in enumerate(('TW','QV','CAP')):
        delta=p*(draws['split_'+m.lower()]-draws['split_tw'])/len(s)+(1-p)*(draws['other_'+m.lower()]-draws['other_tw'])/len(o)
        lo,hi=np.percentile(delta,[2.5,97.5])
        out.append(dict(mechanism=m,rate=float(p*s[:,j].mean()+(1-p)*o[:,j].mean()),
            lower_delta95=float(lo),upper_delta95=float(hi),p=p,evidence='TYPE_A_REWEIGHTING_NO_NEW_WORLD'))
    return out

def history_summary():
    c=read(WS/'chapter4/initialization/outputs/SUMMARY.json')['counts']
    q=read(WS/'chapter4/mechanisms/quadratic_voting/SUMMARY.json')['historical']
    return dict(proposals=c['B_binding'],votes=c['B_binding_votes'],wallets=c['B_binding_wallets'],comparable=q['assessed'])

def historical_data():
    q=pd.read_csv(WS/'chapter4/mechanisms/quadratic_voting/QV_RESULTS.csv',dtype=str,keep_default_na=False)
    q=q[q['mode']=='HISTORICAL_B_BINDING']
    b=pd.read_csv(WS/'baseline/BASELINE_VALIDATION.csv',dtype=str,keep_default_na=False)
    cap=pd.read_csv(WS/'chapter4/mechanisms/vote_escrow_capping/CAPPING_RESULTS.csv',dtype=str,keep_default_na=False)
    meta=pd.read_csv(WS/'data_enrichment/proposal_metadata.csv',dtype=str,keep_default_na=False)
    meta2=pd.read_csv(WS/'data_enrichment/recent/proposal_metadata.csv',dtype=str,keep_default_na=False)
    meta=pd.concat([meta,meta2],ignore_index=True)
    def prefix(df,p):return df.rename(columns={c:p+c for c in df if c!='snapshot_id'})
    out=q[['snapshot_id']].merge(prefix(b,'baseline_'),on='snapshot_id',validate='one_to_one')
    out=out.merge(prefix(q,'qv_'),on='snapshot_id',validate='one_to_one').merge(prefix(cap,'cap_'),on='snapshot_id',validate='one_to_one')
    out=out.merge(meta[['snapshot_id','title','choices_json','created_utc']],on='snapshot_id',validate='one_to_one')
    if len(out)!=1023 or sum(out['qv_status']=='ASSESSED')!=943:raise ValueError('Phạm vi lịch sử không khớp hợp đồng')
    return out

def historical_detail(snapshot_id):
    df=historical_data();r=df[df['snapshot_id']==snapshot_id]
    if len(r)!=1:raise ValueError('Đề xuất không nằm trong tập binding')
    row=r.iloc[0].to_dict();votes=[]
    for p in (WS/'data_enrichment/votes_recovered.csv',WS/'data_enrichment/recent/votes_recovered.csv'):
        with p.open(encoding='utf-8-sig',newline='') as f:
            votes.extend(v for v in csv.DictReader(f) if v['snapshot_id']==snapshot_id)
    return dict(proposal=row,baseline={k:v for k,v in row.items() if k.startswith('baseline_')},votes=pd.DataFrame(votes))

def fmt_rate(v):return 'Không xác định' if v is None or (isinstance(v,float) and math.isnan(v)) else f'{v*100:.4f}%'
def _csv(rows):
    rows=jsonable(rows);flat=[]
    for r in rows:flat.append({k:canonical(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    if not flat:return b''
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in flat for k in r)));w.writeheader();w.writerows(flat)
    return f.getvalue().encode('utf-8-sig')

def export_bundle(bundle):
    report=f'# Kết quả DAO Risk Simulator\n\nPhiên bản {VERSION}.\n\nĐây là mô phỏng Cấp A theo giả định, không phải xác suất tấn công thực tế. VE tách nhóm. QV căn bậc hai theo ví, Capping theo ví. Không xác minh người/ví lịch sử.\n\nHash: {bundle["input_hash"]}\n\n'
    for r in bundle['summary']:report+=f'- {r["mechanism"]}: {r["success"]}/{r["eligible"]} eligible; tỷ lệ {fmt_rate(r["rate_eligible"])}; attempted {r["attempted"]}.\n'
    report+='\nChi phí tiền dùng TEST_COIN; utility là đơn vị cá nhân; thời gian hành động theo giây sự kiện, elapsed_seconds là thời gian thực thi đồng hồ đo bằng perf_counter. Unknown được giữ null. Grant SPLIT là giả định ngoại sinh.\n'
    manifest=dict(bundle['manifest'],input_hash=bundle['input_hash'],model_seed=bundle['request']['config']['seed'],
        source=bundle['request']['source'],elapsed_seconds=bundle['elapsed_seconds'],evidence=bundle['evidence'],
        batch_requests=bundle.get('batch_requests'),sensitivity_requests=bundle.get('sensitivity_requests'))
    from xml.sax.saxutils import escape
    rs=bundle['summary'];bars=[]
    for i,r in enumerate(rs):
        label=escape(r['mechanism']+' '+str(r.get('factor_value','')))
        bars.append(f'<text x="10" y="{35+i*35}">{label}</text><rect x="130" y="{20+i*35}" width="{0 if r["rate_eligible"] is None else 400*r["rate_eligible"]}" height="18" fill="#147d73"/><text x="540" y="{35+i*35}">{escape(fmt_rate(r["rate_eligible"]))}</text>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{70+35*len(rs)}"><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="13">'+''.join(bars)+f'<text x="10" y="{60+35*len(rs)}">Policy success / eligible · mô phỏng Cấp A (%)</text></g></svg>'
    return {'scenario.json':json.dumps(bundle['request'],ensure_ascii=False,indent=2).encode(),
        'world_results.csv':_csv(bundle['results']),'summary.csv':_csv(rs),
        'manifest.json':json.dumps(jsonable(manifest),ensure_ascii=False,indent=2).encode(),
        'report.md':report.encode(),'chart.svg':svg.encode()}
