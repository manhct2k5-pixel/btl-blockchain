"""Independent aggregation of the exported world table against all original 56 cells/JSON."""
import csv,re
from collections import Counter,defaultdict
from audit_common import *
def json_counts(cell):
    exp,val,m=cell['experiment_name'],cell['factor_value'],cell['mechanism']
    if exp=='INFORMATION_CONDITION':return read(ORIGINAL/'INFO_CONDITION_RESULTS.json')[val][m]
    if exp=='ALIAS_COUNT':return read(ORIGINAL/'ALIAS_COUNT_RESULTS.json')[val][m]
    if exp=='CAPPING_THRESHOLD':return read(ORIGINAL/'CAPPING_THRESHOLD_RESULTS.json')[val]
    if exp=='ATTACK_BUDGET':return read(ORIGINAL/'ATTACK_BUDGET_RESULTS.json')[str(float(val.rstrip('x')))][m]
    if exp=='INTERACTION_ALIAS_CAP':
        k,cap=val.split('_');return read(ORIGINAL/'INTERACTION_RESULTS.json')[k][cap]
    if exp=='VOTE_ESCROW_LOCK_TIME':return read(ORIGINAL/'VOTE_ESCROW_RESULTS.json')[val]
    raise ValueError(exp)
def main():
    path=ROOT/'TYPE_B_WORLD_LEVEL_RESULTS.csv'
    if not path.is_file():raise FileNotFoundError(path)
    agg=defaultdict(Counter);seen=set()
    with path.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            key=tuple(r[k] for k in ('experiment_name','factor_name','factor_value','mechanism'))
            identity=key+(r['world_id'],)
            if identity in seen:raise ValueError('Duplicate cell/world')
            seen.add(identity);d=agg[key];d['worlds']+=1
            d['eligible']+=r['eligible']=='True';d['attempted']+=r['attempted']=='True';d['success']+=r['policy_success']=='True'
            d['unknown']+=r['unknown_state']=='True'
            if r['attempted']=='False' and r['success']!='':raise AssertionError('Nonattempt result not null')
    with (ORIGINAL/'SENSITIVITY_RESULTS.csv').open(encoding='utf-8-sig',newline='') as f:cells=list(csv.DictReader(f))
    rows=[]
    for c in cells:
        key=tuple(c[k] for k in ('experiment_name','factor_name','factor_value','mechanism'))
        got=agg[key];j=json_counts(c)
        counts_match=(got['worlds']==int(c['n_worlds']) and all(got[k]==int(c['n_'+k])==int(j[k]) for k in ('eligible','attempted','success')))
        rows.append(dict(**{k:c[k] for k in ('experiment_name','factor_name','factor_value','mechanism')},
            report_text_note='745 eligible is wrong in old report' if c['experiment_name']=='ATTACK_BUDGET' and c['factor_value']=='2.0x'
                else 'Old text not treated as numerical source; see separate claim reconciliation',
            original_csv_worlds=c['n_worlds'],recomputed_worlds=got['worlds'],
            original_csv_eligible=c['n_eligible'],json_eligible=j['eligible'],recomputed_eligible=got['eligible'],
            original_csv_attempted=c['n_attempted'],json_attempted=j['attempted'],recomputed_attempted=got['attempted'],
            original_csv_success=c['n_success'],json_success=j['success'],recomputed_success=got['success'],
            original_csv_rate_eligible=c['success_rate_eligible'],
            correct_rate_eligible=got['success']/got['eligible'] if got['eligible'] else None,
            correct_rate_attempted=got['success']/got['attempted'] if got['attempted'] else None,
            numeric_count_match=counts_match,unknown_worlds=got['unknown'],
            reason='COUNTS_REPRODUCED; ZERO_DENOMINATOR_RATE_IS_NULL' if got['eligible']==0 else 'CSV_JSON_AND_WORLD_REEXECUTION_MATCH'))
    if len(agg)!=56 or len(rows)!=56 or not all(r['numeric_count_match'] for r in rows):
        raise AssertionError('56-cell numerical mismatch')
    import initialize
    initialize.write_csv(ROOT/'NUMERICAL_RECONCILIATION.csv',rows)
    claims=[]
    for p in sorted(ORIGINAL.glob('*.md')):
        for line,text in enumerate(p.read_text(encoding='utf-8-sig').splitlines(),1):
            if re.search(r'745|733|1[,\.]8\s*%.*4[,\.]5|12[,\.]1|15[,\.]3|7/128|6/128|2[,\.]91|ми|miễn nhiễm|tương đương|bất lực|tuyệt đối',text,re.I):
                claims.append(dict(file=p.name,line=line,text=text))
    initialize.write_csv(ROOT/'TEXT_CLAIM_EXTRACTS.csv',claims)
    result=dict(cells=56,world_rows=len(seen),all_count_matches=True,claim_extracts=len(claims),
        undefined_rates_corrected_to_null=sum(r['recomputed_eligible']==0 for r in rows),
        no_original_file_overwritten=True,prior_files_unchanged=protect())
    dump(ROOT/'NUMERICAL_RECONCILIATION_SUMMARY.json',result)
    return result
if __name__=='__main__':print(main())
