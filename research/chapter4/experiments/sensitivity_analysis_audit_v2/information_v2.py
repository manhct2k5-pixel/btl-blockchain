"""Explicit external information grants and scoped no-action result semantics."""
from copy import deepcopy
from audit_common import *
from main_patch import simulate as main_simulate
from attack_core import parse_config,make_policy,tally,ResourceLedger

def planned_content(c):
    p=c['proposal'];a=c['attack']
    return dict(planned_proposal_id=p['id'],planned_choices=p['choices'],target_choice=a['target_choice'],
        target_outcome=a['target_outcome'],planned_snapshot=p['snapshot_time'],
        planned_release=p['created'],planned_vote_start=p['start'])
def declared_grant(c):
    """Caller supplies this declared exogenous premise, never a real-person identification."""
    att=c['attacker']
    return dict(grant_id='SYNTHETIC_PLAN_GRANT:'+c['scenario_id'],principal=att,
        role_bindings={att:['SYNTHETIC_PLAN_HOLDER']},role='SYNTHETIC_PLAN_HOLDER',
        issuer='EXOGENOUS_SCENARIO_DESIGNER',source='SYNTHETIC_PREANNOUNCEMENT',
        scope='TARGETED_PRE_SNAPSHOT_SPLIT',known_at=c['attack']['published_at']-1,
        content=planned_content(c),content_hash=digest(planned_content(c)),
        evidence='SYNTHETIC_ASSUMPTION_NOT_OBSERVED',identity_verified=False)
def declared_block(c):
    return dict(rule_id='SYNTHETIC_TARGETED_SPLIT_PROHIBITION',enabled=True,
        principal=c['attacker'],effective_at=c['attack']['published_at']-1,
        scope='TARGETED_PRE_SNAPSHOT_SPLIT',evidence='SYNTHETIC_ASSUMPTION_NOT_PRODUCTION_RULE')

def validate_grant(c,g):
    if g is None:return 'NOT_READY_MISSING_EXOGENOUS_GRANT'
    required={'grant_id','principal','role_bindings','role','issuer','source','scope','known_at',
              'content','content_hash','evidence','identity_verified'}
    if set(g)!=required:return 'NOT_READY_INCOMPLETE_GRANT_SCHEMA'
    if g['principal']!=c['attacker'] or g['role'] not in g['role_bindings'].get(c['attacker'],[]):
        return 'INFEASIBLE_ACTOR_ROLE_OR_PRINCIPAL_MISMATCH'
    if g['role']!='SYNTHETIC_PLAN_HOLDER' or g['source']!='SYNTHETIC_PREANNOUNCEMENT' or g['issuer']!='EXOGENOUS_SCENARIO_DESIGNER':
        return 'INFEASIBLE_UNAUTHORIZED_INFORMATION_SOURCE'
    if g['scope']!='TARGETED_PRE_SNAPSHOT_SPLIT' or g['evidence']!='SYNTHETIC_ASSUMPTION_NOT_OBSERVED' or g['identity_verified'] is not False:
        return 'NOT_READY_WRONG_GRANT_EVIDENCE_OR_SCOPE'
    if g['content']!=planned_content(c) or g['content_hash']!=digest(g['content']):
        return 'INFEASIBLE_INFORMATION_CONTENT_NOT_BOUND_TO_PLAN'
    a,p=c['attack'],c['proposal']
    if type(g['known_at']) is not int or not g['known_at']<=a['published_at']<a['decision_at']<=a['allocation_at']<p['snapshot_time']<p['created']<p['start']:
        return 'INFEASIBLE_INFORMATION_OR_ALLOCATION_TIMELINE'
    return 'VALID_EXOGENOUS_SYNTHETIC_GRANT'

def no_action(c,reason):
    cfg=parse_config(c);policy=make_policy(cfg);baseline=tally(cfg,cfg['voters'],policy)
    resources=ResourceLedger({p:s['budget'] for p,s in cfg['principals'].items()}).report()
    return dict(scenario_id=cfg['scenario_id'],mechanism=cfg['mechanism'],family=cfg['attack']['family'],
        status=reason,eligible=None if reason.startswith('NOT_READY') else False,attempted=False,
        success=None,policy_success=None,no_attack=baseline,with_attack=deepcopy(baseline),
        resources=resources,events=[],views=[],responses=[],nominal_money_cost=F(0),net_cash_expense=F(0),
        opportunity_cost_utility=F(0),capital_cost_utility=F(0),time_to_decision=None,
        time_to_action_completion=None,time_to_final_evaluation=None,completion_event=None,
        action_completed_at=None,first_target_time=None,
        execution='NOT_EXECUTED',governance_execution='UNKNOWN_NOT_INFERRED',
        actual_usd_cost=None,empirical_attack_probability=None)

def audited_simulate(c,condition='INFORMED_PROPOSER',grant=None,block_rule=None,allocation_strategy='TARGETED_PROPOSAL'):
    cfg=deepcopy(c);cfg.pop('information_condition',None)
    reason='NOT_APPLICABLE_NON_SPLIT'
    if cfg['attack']['family']=='SPLIT':
        if allocation_strategy=='GENERAL_PREALLOCATION':
            result=no_action(cfg,'NOT_READY_GENERIC_PREALLOCATION_NOT_IMPLEMENTED')
        elif condition=='INFORMED_PROPOSER':
            reason=validate_grant(cfg,grant)
            result=main_simulate(cfg) if reason=='VALID_EXOGENOUS_SYNTHETIC_GRANT' else no_action(cfg,reason)
        elif condition=='UNINFORMED_VOTER':
            reason='INFEASIBLE_NO_ADVANCE_TARGETED_PLAN' if grant is None else 'NOT_READY_CONDITION_GRANT_CONFLICT'
            result=no_action(cfg,reason)
        elif condition=='BLOCKED':
            r=block_rule or {}
            valid=(r.get('enabled') is True and r.get('principal')==cfg['attacker'] and
                   r.get('scope')=='TARGETED_PRE_SNAPSHOT_SPLIT' and
                   type(r.get('effective_at')) is int and r['effective_at']<=cfg['attack']['allocation_at'] and
                   r.get('evidence')=='SYNTHETIC_ASSUMPTION_NOT_PRODUCTION_RULE')
            reason='INFEASIBLE_DECLARED_TARGETED_SPLIT_PROHIBITION' if valid else 'NOT_READY_BLOCK_RULE_NOT_SPECIFIED'
            result=no_action(cfg,reason)
        else:raise ValueError('Unknown information condition')
    else:result=main_simulate(cfg)
    result['model_version']='SENSITIVITY_INFORMATION_AUDIT_V2'
    result['information_condition']=condition
    result['information_authorization']=reason
    result['information_grant_hash']=digest(grant) if grant is not None else None
    result['allocation_strategy']=allocation_strategy
    if result.get('attempted') is False:
        result['success']=None
        result['execution']='NOT_EXECUTED'
    else:result['execution']='SIMULATED_ACTION_COMPLETED'
    result['governance_execution']='UNKNOWN_NOT_INFERRED'
    result['actual_usd_cost']=None;result['empirical_attack_probability']=None
    if result.get('eligible') is not True:result['policy_success']=None
    if reason=='VALID_EXOGENOUS_SYNTHETIC_GRANT':
        for v in result.get('views',[]):
            if v.get('role')=='ATTACKER':
                v['view']['authorized_external_plan_grant']=dict(grant_id=grant['grant_id'],
                    known_at=grant['known_at'],content=grant['content'],evidence=grant['evidence'])
    return result
