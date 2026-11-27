"""Pointwise paired-bootstrap uncertainty of QV/CAP minus TW, over mixture p."""
import csv
import numpy as np
from audit_common import *

def main():
    with (ROOT/'CROSSOVER_BOOTSTRAP_DRAWS.csv').open(newline='',encoding='utf-8') as f: draws=list(csv.DictReader(f))
    rows=[]
    for mechanism in ('qv','cap'):
        ds=np.array([(int(r['split_'+mechanism])-int(r['split_tw']))/257 for r in draws])
        do=np.array([(int(r['other_'+mechanism])-int(r['other_tw']))/452 for r in draws])
        for p in sorted(set([i/100 for i in range(101)]+[257/8845])):
            values=p*ds+(1-p)*do
            lo,hi=np.percentile(values,[2.5,97.5])
            point=p*(19/257)+(1-p)*((-1/452) if mechanism=='qv' else 0)
            rows.append(dict(mechanism_minus_tw=mechanism.upper(),p=p,point=point,lower95=float(lo),upper95=float(hi),
                interval_type='POINTWISE_PERCENTILE_NOT_SIMULTANEOUS',iterations=len(draws)))
    with (ROOT/'DIFFERENCE_POINTWISE_BANDS.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    dump(ROOT/'DIFFERENCE_BAND_SUMMARY.json',dict(rows=len(rows),selected=[r for r in rows if r['p'] in (0,257/8845,0.1,1)],
        interpretation='Positive means greater simulated policy success risk than TW; intervals are pointwise, not simultaneous or a root CI.',sources_unchanged=protect()))
if __name__=='__main__':main()
