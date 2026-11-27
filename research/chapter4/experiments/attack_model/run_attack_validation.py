"""Run only the finite declared fixture list. No Monte Carlo entry point."""
import argparse,json,hashlib,platform,socket
from pathlib import Path
from unittest.mock import patch
from technical_gate import ROOT,WS,protect,sha
from qv_numeric_v2 import PATCH_ID
from attack_core import simulate
from fixtures import scenarios
from metrics import summarize,planned_independent_bernoulli_repeats
from run_behavior import jsonable
import initialize

def dump(p,x):p.write_text(json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT)
    output=parser.parse_args(argv).output.resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must be inside attack_model')
    output.mkdir(parents=True,exist_ok=True)
    prior=protect()
    gate=json.loads((ROOT/'TECHNICAL_GATE.json').read_text(encoding='utf-8'))
    if gate.get('status')!='PASSED' or gate['patch_sha256']!=sha(ROOT/'qv_numeric_v2.py'):
        raise RuntimeError('Technical gate not current; run technical_gate.py before model validation')
    configs=scenarios()
    with patch.object(socket,'socket',side_effect=RuntimeError('Fixture validation must be offline')):
        results=[simulate(c) for c in configs]
        replay=[simulate(c) for c in configs]
    assert jsonable(results)==jsonable(replay)
    dump(output/'FIXTURE_CONFIGS.json',configs)
    dump(output/'FIXTURE_RESULTS.json',results)
    metric=summarize(results)
    # Finite fixture counts are software verification, not MC rates/intervals.
    dump(output/'METRIC_ACCOUNTING.json',metric)
    csv=[]
    for c,r in zip(configs,results):
        a=r.get('resources',{}).get(c['attacker'],{})
        no=r.get('no_attack') or {};yes=r.get('with_attack') or {}
        csv.append(dict(scenario_id=c['scenario_id'],family=c['attack']['family'],mechanism=c['mechanism'],
            target_outcome=c['attack']['target_outcome'],status=r['status'],reason=r['reason'],
            eligible=r.get('eligible'),attempted=r['attempted'],success=r['success'],
            no_attack_outcome=no.get('outcome'),attack_outcome=yes.get('outcome'),
            no_attack_source_vp=no.get('source_vp'),attack_source_vp=yes.get('source_vp'),
            no_attack_effective=no.get('effective_total'),attack_effective=yes.get('effective_total'),
            no_attack_options_json=json.dumps(no.get('options')),attack_options_json=json.dumps(yes.get('options')),
            weight_unit=yes.get('unit'),paid=str(a.get('paid','')),refund=str(a.get('refund','')),
            peak_escrow=str(a.get('peak_escrow','')),cash_expense=str(r.get('net_cash_expense','')),
            opportunity_utility=str(r.get('opportunity_cost_utility','')),capital_utility=str(r.get('capital_cost_utility','')),
            currency='TEST_COIN',execution='UNKNOWN_NOT_INFERRED',
            identity='SYNTHETIC_CONTROLLERS_NOT_REAL_WALLET_IDENTIFICATION',
            information='EX_ANTE_BELIEFS_NO_FINAL_TALLY',seed=c['seed'],rng_used=False,
            empirical_attack_probability='',actual_usd_cost=''))
    initialize.write_csv(output/'VALIDATION_RESULTS.csv',csv)
    parents=[WS/'chapter4/mechanisms'/name/'COMPARISON_CONTRACT.json' for name in ('token_weighted','quadratic_voting','vote_escrow_capping')]
    contract=dict(schema='4.3-attack-comparison-v1',scope='FINITE_SYNTHETIC_SOFTWARE_FIXTURES_ONLY',
        parent_contracts={p.relative_to(WS).as_posix():sha(p) for p in parents},
        mechanism_policy='HYPOTHETICAL_COMMON_BINARY_STRICT_MAJORITY_NO_QUORUM_V1',
        target_fixed_before_decision=True,comparison='NO_ATTACK_VS_ATTACK_WITHIN_SAME_MECHANISM',
        held_constant=['initial_principal_assets','money_budgets','preferences','snapshot_reference',
            'rights_assumptions','baseline_action_plan','exogenous_belief_profiles','outsider_rho','seed'],
        endogenous_differences=['actor_actions','payments','funded_escrow','capped_or_sqrt_effective_weights_after_declared_allocation'],
        split_special_case='Same pre-allocation resources; allocation changes before snapshot only',
        qv_formula_variant='WALLET_SQRT_SINGLE_CHOICE_V1',
        qv_implementation_version=PATCH_ID,
        original_qv_helper_unchanged=True,belief_model='EXOGENOUS_ACTION_PROFILES_NOT_MECHANISM_RESPONSIVE',
        payoff_solution='ABM_STRICT_DELTA_GT_EPSILON_NOT_NASH_NOT_SPNE',
        payment_model='FULLY_COLLATERALIZED_OPT_IN_FINAL_VALID_ACTION_NOT_OUTCOME',
        settlement_verifier='PERFECT_SYNTHETIC_ASSUMPTION_NOT_DEPLOYED_CONTRACT',
        same_second_policy='PRE_SNAPSHOT_ALLOCATION; INITIAL_VOTES; FUNDING; STRICTLY_LATER_RESPONSE_BATCH; SETTLEMENT_AND_FINAL_EVALUATION',
        shared_budget_conflict='CANCEL_ALL_SPENDERS_OF_OVERBOOKED_PRINCIPAL',
        historical_attack_roles_assigned=False,blockchain_transactions=False,Monte_Carlo=False,
        source_code_hashes={p.relative_to(WS).as_posix():sha(p) for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts},
        external_method_references=['https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm',
            'https://docs.python.org/3/library/random.html'])
    dump(output/'COMPARISON_CONTRACT.json',contract)
    dump(output/'MC_READINESS.json',dict(status='NOT_READY_FOR_CALIBRATED_MONTE_CARLO',
        distributions=None,empirically_fitted=False,large_scale_execution_enabled=False,
        proposed_fixed_n_precision=dict(confidence='0.95',absolute_half_width='0.02',
            conservative_independent_bernoulli_n=planned_independent_bernoulli_repeats()),
        unresolved=['unobserved_payoff_and_belief_distributions','common_controller_structure',
            'eligible_nonvoter_rights','asset_acquisition_and_loan_constraints','mechanism_dependent_response_beliefs',
            'escrow_verifier_feasibility','lock_choice_and_opportunity_cost_calibration']))
    dump(output/'PATCH_IMPACT.json',dict(patch=PATCH_ID,formula_unchanged=True,
        validation_before_cache=True,cache_typed=True,original_files_unchanged=prior,
        fifty_numeric_oracles=True,single_process_repeated_scenarios=True,
        historical_outputs_recomputed=False,prospective_entry_point='WalletSqrtNumericV2'))
    summary=dict(fixture_scenarios=len(results),counts=metric['counts'],rng_used=False,Monte_Carlo=False,
        all_results_repeated_equal_in_one_process=True,prior_files_unchanged=protect(),
        python=platform.python_version(),current_technical_gate=gate,
        attack_probability_claimed=False,large_scale_experiment_executed=False)
    dump(output/'SUMMARY.json',summary)
    names=['FIXTURE_CONFIGS.json','FIXTURE_RESULTS.json','METRIC_ACCOUNTING.json','VALIDATION_RESULTS.csv',
        'COMPARISON_CONTRACT.json','MC_READINESS.json','PATCH_IMPACT.json','SUMMARY.json']
    dump(output/'RESULT_MANIFEST.json',{n:sha(output/n) for n in names})
    print(json.dumps(summary,indent=2),flush=True)
    return summary
if __name__=='__main__':main()
