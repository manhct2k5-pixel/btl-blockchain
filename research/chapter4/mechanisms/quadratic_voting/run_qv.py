"""Reproduce 4.2.2 without changing any preceding artifact."""
import argparse
from collections import Counter,defaultdict
from decimal import Decimal,localcontext
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from qv_mechanism import *
from qv_behavior_adapter import QVMechanicalBehaviorSession
sys.path.insert(0,str(WS/'chapter4/initialization'))
import initialize
from engine import rows
from behavior import BehaviorSession
from scenarios import fixture_bundle,build_fixture_world
from run_behavior import jsonable

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def protect():
    m=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for name,h in m.items():
        if sha(WS/name)!=h: raise InputError('Prior artifact changed: '+name)
    return len(m)

def metrics(box,result,baseline_outcome,old_threshold,flags,mode='HISTORICAL_B_BINDING'):
    bs=box.ballots
    raw=distribution([b.vp for b in bs])
    eff=score_distribution(bs)
    eligible=not result.outcome.startswith('UNASSESSED')
    common=common_policy_raw(box.proposal,box.rule,bs)
    with localcontext() as ctx:
        ctx.prec=120
        raw_options=[sum((b.vp for b in bs if b.choice==i+1),Decimal(0)) for i in range(len(box.proposal.choices))]
    out=dict(mode=mode,snapshot_id=box.proposal.id,choices_json=json.dumps(box.proposal.choices),
        status='ASSESSED' if eligible else result.outcome,exclusion_reason=box.exclusion_reason,
        pre_outcome_semantic_screen=exclusion(box.proposal,box.rule),
        variant=VARIANT,weight_unit=UNIT,reference_vp='1',normalization='NONE',
        credit_scope='PER_WALLET_PER_PROPOSAL_FULL_BUDGET_SINGLE_CHOICE_NO_SHARED_POOL',
        source_vp_total=show(result.total_source_vp),qv_total_score=show(result.total_effective_weight),
        raw_option_vp_json=json.dumps([show(x) for x in raw_options]),
        qv_option_scores_json=json.dumps([show(x) for x in result.option_weights]),
        retained_wallet_count=result.vote_count,positive_vp_wallet_count=raw['positive_vp_voters'],
        token_historical_outcome=baseline_outcome,qv_outcome=result.outcome,
        token_same_new_outcome_policy=common,
        outcome_changed_vs_historical=eligible and result.outcome!=baseline_outcome if eligible else '',
        outcome_changed_due_to_weighting_under_common_policy=eligible and result.outcome!=common if eligible else '',
        raw_policy_changed_vs_historical=eligible and common!=baseline_outcome if eligible else '',
        historical_threshold_vp=show(old_threshold),qv_score_gap_boundary='0',
        qv_absolute_quorum='NONE_DECLARED_ASSUMPTION',outcome_policy=StrictBinaryScoreMajority.policy_id,
        candidate_rule_family=box.rule.family,candidate_rule_commit=box.rule.commit,
        numeric_certificate_json=json.dumps(box.numeric_certificate,sort_keys=True),
        score_display_precision_significant_digits=100,display_scores_not_used_for_decision=True,
        concentration_population='CURRENT_RETAINED_BALLOTS_INCLUDING_ZERO_VP_NOT_ELIGIBLE_UNIVERSE',
        source_metrics_basis='RAW_VP_PER_WALLET',qv_metrics_basis='SQRT_VP_OVER_ONE_VP_PER_WALLET',
        concentration_precision='DESCRIPTIVE_100_DIGIT_WEIGHT_APPROXIMATION_40_DIGIT_OUTPUT',
        identity_verified=False,physical_rights_verified=False,sybil_resistance=False,
        eligible_universe_known=False,execution='UNKNOWN',attack_success_rate='',
        monetary_attack_cost='',replacement_history='UNKNOWN_RETAINED_FINAL_ONLY' if mode=='HISTORICAL_B_BINDING' else box.replacement_count)
    for prefix,d in [('raw',raw),('qv',eff)]:
        for key in ('gini','hhi','top1_share','top5_share','top10_share','vp_min','vp_q25','vp_median','vp_q75','vp_max'):
            out[prefix+'_'+key.replace('vp_','weight_')]=show(d[key])
    for key in ('default_dependency_gap','governance_match','budget_layer_unverified','production_deployment_verified','level_c_source_selected'):
        out[key]=flags.get(key,'UNVERIFIED')
    return out

def sybil_fixture():
    # Hand specified property case, not attack optimization or a historical identity inference.
    return dict(label='SYNTHETIC_FIXED_VP_PROPERTY_TEST',one_wallet_vp=[100],split_wallet_vp=[25,25,25,25],
        opposition_vp=[144],subject_vp_before=100,subject_vp_after=100,total_source_before=244,total_source_after=244,
        subject_score_before=10,subject_score_after=20,opposition_score=12,
        outcome_before='REJECTED',outcome_after='ACCEPTED',
        physical_redistribution_feasibility='NOT_ASSERTED',controller='ASSUMED_SYNTHETIC_NOT_IDENTIFIED')

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT)
    out=p.parse_args(argv).output.resolve()
    if not out.is_relative_to(ROOT): raise InputError('Output must remain in QV task folder')
    out.mkdir(exist_ok=True,parents=True)
    protected=protect()
    import engine
    assert Path(engine.__file__).resolve()==(WS/'baseline/engine.py').resolve()
    print('Verified actual baseline/engine.py; checking full historical inputs...',flush=True)
    inputs,events,wallets,validation,integrity,counts=initialize.load_sources()
    assert (len(inputs),len(events),len(wallets))==(1023,63662,6004)
    grouped=defaultdict(list)
    for v in events: grouped[v.proposal].append(v)
    previous={r['snapshot_id']:r for r in rows(WS/'chapter4/mechanisms/token_weighted/BASELINE_METRICS.csv')
              if r['mode']=='A_HISTORICAL_RETAINED'}
    result_rows=[]
    for proposal,rule,threshold,flags in inputs:
        box=QVBox(proposal,rule,'HISTORICAL_RETAINED',flags)
        bs=[Ballot(proposal.id,v.voter,v.choice,v.vp,v.components,v.created,v.id,
            proposal.raw['snapshot_network'],proposal.snapshot_block,'HISTORICAL_RETAINED',
            'OBSERVED_RETAINED_RECORD',v.source_file,v.state) for v in grouped[proposal.id]]
        box.commit(bs,proposal.end)
        result=box.evaluate(proposal.end+1)
        old=previous[proposal.id]
        row=metrics(box,result,old['computed_outcome'],threshold,flags)
        assert F(row['source_vp_total'])==F(old['total_vp'])
        assert result.vote_count==int(old['voters'])
        assert [F(x) for x in json.loads(row['raw_option_vp_json'])]==[F(x) for x in json.loads(old['option_vp_json'])]
        row['baseline_raw_tally_count_match']=True
        result_rows.append(row)
    print('Completed all 1,023 historical rows; checking fixed-behavior sidecar...',flush=True)
    bundle=fixture_bundle()
    control=BehaviorSession(build_fixture_world(bundle),bundle['behavior'])
    control_summary=control.run()
    session=QVMechanicalBehaviorSession(build_fixture_world(bundle),bundle['behavior'])
    sidecar_summary=session.run()
    assert jsonable(control_summary)==jsonable(sidecar_summary)
    assert jsonable(control.log)==jsonable(session.log) and jsonable(control.views)==jsonable(session.views)
    for filename,value in [('DECISION_HISTORY.json',session.log),('DECISION_VIEWS.json',session.views)]:
        assert json.loads((WS/'chapter4/behavior/outputs'/filename).read_text(encoding='utf-8'))==jsonable(value)
    synthetic=[]
    for sid,box in sorted(session.qv_boxes.items()):
        baseline=session.boxes[sid].evaluate(session.world.clock)
        synthetic.append(metrics(box,box.evaluate(session.world.clock),baseline.outcome,
                                 session.boxes[sid].threshold,box.flags,'SYNTHETIC_FIXED_BEHAVIOR'))
    initialize.write_csv(out/'QV_RESULTS.csv',result_rows)
    initialize.write_csv(out/'QV_SYNTHETIC_RESULTS.csv',synthetic)
    dump(out/'BEHAVIOR_CONFIG.json',bundle)
    dump(out/'BEHAVIOR_DECISIONS.json',session.log)
    dump(out/'BEHAVIOR_VIEWS.json',session.views)
    dump(out/'BEHAVIOR_QV_AUDIT.json',session.qv_audit)
    dump(out/'SYBIL_FIXTURE.json',sybil_fixture())
    assessed=[r for r in result_rows if r['status']=='ASSESSED']
    summary=dict(variant=VARIANT,engine_file=str(Path(engine.__file__).resolve()),
        historical=dict(proposals=1023,votes=63662,wallets=6004,assessed=len(assessed),
            excluded=1023-len(assessed),
            exclusion_reason_combinations=dict(Counter(r['exclusion_reason'] for r in result_rows if r['status']!='ASSESSED')),
            exclusion_individual_reasons=dict(Counter(reason for r in result_rows if r['status']!='ASSESSED' for reason in r['exclusion_reason'].split(';'))),
            qv_outcomes=dict(Counter(r['qv_outcome'] for r in assessed)),
            token_historical_outcomes_on_assessed=dict(Counter(r['token_historical_outcome'] for r in assessed)),
            transition_vs_historical=dict(Counter(r['token_historical_outcome']+' -> '+r['qv_outcome'] for r in assessed)),
            changed_vs_historical=sum(r['outcome_changed_vs_historical'] for r in assessed),
            changed_due_to_weighting_under_common_policy=sum(r['outcome_changed_due_to_weighting_under_common_policy'] for r in assessed),
            changed_raw_policy_vs_historical=sum(r['raw_policy_changed_vs_historical'] for r in assessed),
            numeric_unresolved=sum(r['status']=='UNASSESSED_NUMERIC' for r in result_rows),
            baseline_raw_tally_count_matches=1023,
            official_labels_used_in_qv_calibration=False,
            gini_reduced=sum(F(r['qv_gini'])<F(r['raw_gini']) for r in assessed if r['qv_gini']!='')),
        synthetic=dict(proposals=len(synthetic),decisions=len(session.log),behavior_fixed_and_frozen_views_match=True,
            replacements=sum(b.replacement_count for b in session.qv_boxes.values()),strategic_response_modelled=False),
        source_integrity=integrity,source_counts=counts,protected_prior_files_unchanged=protected,
        Monte_Carlo=False,attack_or_defense_success_evaluated=False,sensitivity_analysis=False,
        data_label='HYPOTHETICAL_MECHANICAL_COUNTERFACTUAL_NOT_REAL_DAO_QV')
    dump(out/'SUMMARY.json',summary)
    parent=WS/'chapter4/mechanisms/token_weighted/COMPARISON_CONTRACT.json'
    contract=json.loads(parent.read_text(encoding='utf-8'))
    contract.update(status='QV_RESTRICTED_MECHANICAL_COUNTERFACTUAL_ONLY',parent_contract=str(parent.relative_to(WS)),
        parent_contract_sha256=sha(parent),variant=VARIANT,
        weight_policy=VARIANT,weight_unit=UNIT,formula='score_i=sqrt(VP_i / 1 VP); S_k=sum(score_i where choice_i=k)',
        normalization='NONE_NO_BACK_SCALING_TO_RAW_VP',reference_vp='1 VP',
        outcome_policy=StrictBinaryScoreMajority.policy_id,
        outcome_assumptions='Binary Yes>No, tie/zero reject, no quorum; special families excluded before scoring',
        threshold='Zero difference in score points, not historical winning VP floor',
        credit_scope='Independent wallet/proposal full-budget single choice; no currency, no across-proposal depletion',
        identity_policy='Wallet-level; no verified controllers or anti-Sybil gate',
        fixed_behavior_only=True,mechanism_dependent_beliefs_implemented=False,
        common_policy_control='Raw VP majority under identical new policy isolates weighting conditional on fixed ballots',
        differences_from_historical=['weight transformation','explicit new outcome/no-quorum policy','predeclared eligibility screen'],
        source_code_hashes={**contract['source_code_hashes'],**{
            str(p.relative_to(WS)).replace('\\','/'):sha(p) for p in sorted(ROOT.glob('*.py'))}})
    dump(out/'COMPARISON_CONTRACT.json',contract)
    names=['QV_RESULTS.csv','QV_SYNTHETIC_RESULTS.csv','BEHAVIOR_CONFIG.json','BEHAVIOR_DECISIONS.json',
        'BEHAVIOR_VIEWS.json','BEHAVIOR_QV_AUDIT.json','SYBIL_FIXTURE.json','SUMMARY.json','COMPARISON_CONTRACT.json']
    dump(out/'RESULT_MANIFEST.json',{name:sha(out/name) for name in names})
    assert protect()==protected
    print(json.dumps(summary['historical'],indent=2),flush=True)
    return summary

if __name__=='__main__': main()
