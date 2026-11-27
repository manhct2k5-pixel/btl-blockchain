"""Evaluator-only QV sidecar. Does not expose new outcomes or claim strategic response."""
from qv_mechanism import QVBox
from behavior_adapter import TokenWeightedBehaviorSession

class QVMechanicalBehaviorSession(TokenWeightedBehaviorSession):
    def __init__(self,world,config):
        super().__init__(world,config)
        self.qv_boxes={sid:QVBox(b.proposal,b.rule,b.origin,b.flags,b.allow_assumed_rights)
                       for sid,b in self.boxes.items()}
        self.qv_audit=[]
    def _check_invariants(self):
        super()._check_invariants()
        for sid,source in sorted(self.boxes.items()):
            target=self.qv_boxes[sid]
            existing={b.wallet_id:b for b in target.ballots}
            updates=[b for b in source.ballots if existing.get(b.wallet_id)!=b]
            if updates:
                target.commit(updates,self.world.clock,replace=True)
                result=target.evaluate(self.world.clock)
                assert result.total_source_vp==source.evaluate(self.world.clock).total_source_vp
                self.qv_audit.append(dict(snapshot_id=sid,time=self.world.clock,updates=len(updates),
                    qv_outcome=result.outcome,option_scores=result.option_weights,
                    replacement_count=target.replacement_count,exclusion_reason=target.exclusion_reason,
                    exposure='EVALUATOR_ONLY_NEVER_IN_AGENT_VIEW',
                    strategic_response_modelled=False))
