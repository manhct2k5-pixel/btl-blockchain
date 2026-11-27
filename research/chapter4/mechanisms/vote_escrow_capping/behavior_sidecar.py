"""Cap evaluator after unchanged behavior commits, never supplied to agent views."""
from policies import CommonBox,CappingWeightPolicy
from behavior_adapter import TokenWeightedBehaviorSession

class CappingMechanicalBehaviorSession(TokenWeightedBehaviorSession):
    def __init__(self,world,config,cap):
        super().__init__(world,config)
        self.cap_boxes={sid:CommonBox(b.proposal,b.rule,b.origin,CappingWeightPolicy(cap),b.flags,b.allow_assumed_rights)
            for sid,b in self.boxes.items()}
        self.cap_audit=[]
    def _check_invariants(self):
        super()._check_invariants()
        for sid,source in sorted(self.boxes.items()):
            target=self.cap_boxes[sid]
            old={b.wallet_id:b for b in target.ballots}
            updates=[b for b in source.ballots if old.get(b.wallet_id)!=b]
            if updates:
                target.commit(updates,self.world.clock,replace=True)
                result=target.evaluate(self.world.clock)
                assert result.total_source_vp==source.evaluate(self.world.clock).total_source_vp
                self.cap_audit.append(dict(snapshot_id=sid,time=self.world.clock,updates=len(updates),
                    outcome=result.outcome,replacements=target.replacement_count,
                    exposure='EVALUATOR_ONLY_NOT_STRATEGIC_RESPONSE'))
