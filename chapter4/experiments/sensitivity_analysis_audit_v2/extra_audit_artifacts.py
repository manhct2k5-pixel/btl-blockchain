"""Reproduce auxiliary stream evidence, effective metadata, paired tables and figure."""
import csv
from audit_common import *
from main_generator import generate_world
from crossover_audit import load_vectors

def main():
    c=read(MAIN/'MC_MAIN_CONTRACT.json');rows=[]
    for w in read(MAIN/'WORLDS.json'):
        g=generate_world(c,w['group'],w['replicate_id'])
        if g['stream_seeds']!=w['stream_seeds']:raise AssertionError('Stream mismatch')
        rows.append(dict(world_id=w['world_id'],stream_seeds=w['stream_seeds'],matches=True))
    dump(ROOT/'RNG_STREAM_AUDIT.json',dict(worlds=len(rows),all_stream_seeds_match=True,records=rows))
    c=read(ORIGINAL/'SENSITIVITY_EXPERIMENT_CONTRACT.json')
    c.update(schema='SENSITIVITY_EFFECTIVE_CONTRACT_AUDIT_V2',master_seed=4302027,registered_master_seed=4302028,
        generator_version='LEVEL_A_WORLD_GENERATOR_V2',model_version='SENSITIVITY_INFORMATION_AUDIT_V2',
        world_source='REUSED_MONTE_CARLO_MAIN_43_WORLD_CONFIGS',independent_new_sensitivity_sample=False,
        original_contract_sha256=sha(ORIGINAL/'SENSITIVITY_EXPERIMENT_CONTRACT.json'))
    c['type_b_resimulation']['information_conditions']=[
        dict(id='INFORMED_PROPOSER',requirement='STRUCTURED_EXOGENOUS_GRANT_NOT_OBSERVED_IDENTITY',
            split_feasible='CONDITIONAL_ON_VALID_GRANT_AND_ORIGINAL_FEASIBILITY'),
        dict(id='UNINFORMED_VOTER',scope='TARGETED_PLAN_REQUIRING_ADVANCE_PROPOSAL_INFORMATION',
            split_feasible=False,general_preallocation='NOT_IMPLEMENTED'),
        dict(id='BLOCKED',requirement='EXPLICIT_SYNTHETIC_BLOCK_RULE',production_identity_or_snapshot_defense_verified=False)]
    c['type_b_resimulation']['vote_escrow_factors']=dict(original_executed_duration_from_create_fractions=[.25,.5,1],
        original_executed_amount_fractions=None,original_amounts_preserved=True,actual_remaining_seconds='duration_from_create - 10',
        separate_two_factor_supplement='VE_SUPPLEMENT_CONTRACT.json')
    c['original_results_immutable']=True
    c['original_56_counts_replay_scope']='SAME_NUMERICAL_RULES;EXPLICIT_INFORMATION_PREMISES;CORRECTED_NULL_AND_EXECUTION_METADATA'
    dump(ROOT/'EFFECTIVE_SENSITIVITY_CONTRACT.json',c)
    v,ids=load_vectors();out={}
    for name,x in v.items():
        out[name]={}
        for j,m in ((1,'QV'),(2,'CAP')):
            out[name][m+'_vs_TW']=dict(both_success=int(((x[:,j]==1)&(x[:,0]==1)).sum()),
                mechanism_only=int(((x[:,j]==1)&(x[:,0]==0)).sum()),tw_only=int(((x[:,j]==0)&(x[:,0]==1)).sum()),
                both_non_success=int(((x[:,j]==0)&(x[:,0]==0)).sum()))
    dump(ROOT/'PAIRED_DISCORDANCE_COUNTS.json',out)
    render();protect()

def render():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with (ROOT/'DIFFERENCE_POINTWISE_BANDS.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    fig,axs=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,m,color in zip(axs,['QV','CAP'],['#235b8e','#ad5722']):
        a=[r for r in rows if r['mechanism_minus_tw']==m];p=[100*float(r['p']) for r in a]
        ax.fill_between(p,[100*float(r['lower95']) for r in a],[100*float(r['upper95']) for r in a],
            color=color,alpha=.18,label='Pointwise 95% percentile interval')
        ax.plot(p,[100*float(r['point']) for r in a],color=color,lw=2,label='Paired mixture estimate')
        ax.axhline(0,color='#666666',lw=.8)
        if m=='QV':ax.axvline(100*257/8845,color=color,lw=1,ls=':',label='Point root: 2.906%')
        ax.set_title(m+' minus TW');ax.set_xlabel('SPLIT share among eligible opportunities (%)');ax.grid(alpha=.15)
    axs[0].set_ylabel('Policy-success rate difference (percentage points)')
    axs[0].legend(fontsize=8,loc='upper left')
    fig.suptitle('Synthetic Level-A sensitivity: paired bootstrap, 10,000 draws',fontsize=12);fig.tight_layout()
    fig.savefig(ROOT/'DIFFERENCE_POINTWISE_BANDS.png',dpi=180);fig.savefig(ROOT/'DIFFERENCE_POINTWISE_BANDS.svg');plt.close(fig)

if __name__=='__main__':main()
