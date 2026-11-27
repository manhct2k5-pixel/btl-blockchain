"""Reexecute original paired bootstrap and audit valid crossover existence separately."""
import csv,random,math
from fractions import Fraction as F
import numpy as np
from audit_common import *

def load_vectors(path=None):
    path=path or MAIN/'MC_MAIN_RESULTS.csv'
    if not path.is_file():raise FileNotFoundError(path)
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    grouped={}
    for r in rows:
        if r['group']!='MAIN' or r['eligible']!='True':continue
        key=(r['world_id'],r['family'])
        d=grouped.setdefault(key,{})
        if r['mechanism'] in d:raise ValueError('Duplicate paired world')
        if r['policy_success'] not in ('True','False'):raise ValueError('Unknown policy result cannot become false')
        d[r['mechanism']]=int(r['policy_success']=='True')
    groups={'SPLIT':[],'OTHER':[]};ids={'SPLIT':[],'OTHER':[]}
    for (world,family),d in sorted(grouped.items()):
        if set(d)!={'TW','QV','CAP'}:raise ValueError('Missing paired mechanism')
        key='SPLIT' if family=='SPLIT' else 'OTHER'
        groups[key].append([d[m] for m in ('TW','QV','CAP')]);ids[key].append(world)
    return {k:np.asarray(v,dtype=np.int64) for k,v in groups.items()},ids

def classify_crossing(split_counts,other_counts,ns,no):
    # A = r_OTHER_TW-r_OTHER_QV; B = r_SPLIT_QV-r_SPLIT_TW.
    a=(int(other_counts[0])-int(other_counts[1]))*ns
    b=(int(split_counts[1])-int(split_counts[0]))*no
    denominator=a+b
    if denominator==0:
        return dict(kind='IDENTICAL_LINES_NO_UNIQUE_ROOT' if a==0 else 'PARALLEL_NO_ROOT',
                    root=None,valid=False,a=a,b=b,denominator=0)
    p=F(a,denominator)
    return dict(kind='VALID_CLOSED_UNIT_INTERVAL' if 0<=p<=1 else 'OUTSIDE_UNIT_INTERVAL',
                root=float(p),valid=0<=p<=1,a=a,b=b,denominator=denominator)

def bootstrap(vectors,iterations=10000,seed=4302029):
    s,o=vectors['SPLIT'],vectors['OTHER'];ns,no=len(s),len(o)
    if ns==0 or no==0:raise ValueError('Both strata must be nonempty')
    rng=random.Random(seed);draws=[];legacy=[];valid_roots=[]
    for i in range(iterations):
        # Same RNG calls/order as original script, retaining all three mechanisms together.
        si=[rng.randint(0,ns-1) for _ in range(ns)]
        oi=[rng.randint(0,no-1) for _ in range(no)]
        ks=s[si].sum(axis=0);ko=o[oi].sum(axis=0)
        rates_s=ks/ns;rates_o=ko/no
        denominator=(rates_s[1]-rates_s[0])+(rates_o[0]-rates_o[1])
        legacy_root=None
        if denominator>0:
            legacy_root=float((rates_o[0]-rates_o[1])/denominator);legacy.append(legacy_root)
        classified=classify_crossing(ks,ko,ns,no)
        if classified['valid']:valid_roots.append(classified['root'])
        draws.append(dict(replicate=i,split_tw=int(ks[0]),split_qv=int(ks[1]),split_cap=int(ks[2]),
            other_tw=int(ko[0]),other_qv=int(ko[1]),other_cap=int(ko[2]),
            **classified,legacy_root=legacy_root))
    def ci(a):return np.percentile(a,[2.5,97.5]).tolist() if a else None
    counts={kind:sum(d['kind']==kind for d in draws) for kind in sorted({d['kind'] for d in draws})}
    return draws,dict(iterations=iterations,seed=seed,paired_unit='WORLD_VECTOR_TW_QV_CAP_WITHIN_STRATUM',
        split_worlds=ns,other_worlds=no,kind_counts=counts,valid_root_samples=len(valid_roots),
        valid_root_fraction=len(valid_roots)/iterations,
        legacy_positive_denominator_samples=len(legacy),
        legacy_formula_real_line_percentile95=ci(legacy),
        valid_root_conditional_percentile95=ci(valid_roots),
        conditional_interval_is_not_unconditional_95pct_confidence_set=True)

def main():
    protect();vectors,ids=load_vectors()
    counts={k:dict(zip(('TW','QV','CAP'),map(int,v.sum(axis=0)))) for k,v in vectors.items()}
    assert (len(vectors['SPLIT']),len(vectors['OTHER']))==(257,452)
    point=classify_crossing(vectors['SPLIT'].sum(axis=0),vectors['OTHER'].sum(axis=0),257,452)
    assert F(point['a'],point['denominator'])==F(257,8845)
    draws,summary=bootstrap(vectors)
    source=read(ORIGINAL/'TYPE_A_REWEIGHTING_RESULTS.json')
    previous=source['crossover_summary']['bootstrap_ci_95']
    assert np.allclose(previous,summary['legacy_formula_real_line_percentile95'],atol=1e-13,rtol=0)
    summary.update(point=point,exact_p_star='257/8845',source_counts=counts,
        previous_saved_interval=previous,original_interval_reproduced=True,
        scalar_parameter_scope='Mixture weight over eligible synthetic SPLIT opportunities, not real DAO prevalence',
        paired_world_ids_sha256=digest(ids))
    with (ROOT/'CROSSOVER_BOOTSTRAP_DRAWS.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(draws[0]));writer.writeheader();writer.writerows(draws)
    dump(ROOT/'CROSSOVER_BOOTSTRAP_RESULTS.json',summary)
    dump(ROOT/'BOOTSTRAP_PAIRED_INPUT.json',dict(world_ids=ids,vectors={k:v.tolist() for k,v in vectors.items()}))
    print(json.dumps(summary,indent=2))
    protect()
if __name__=='__main__':main()
