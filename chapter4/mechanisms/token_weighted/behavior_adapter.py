"""Unchanged behavior law, with per-batch canonical ballot mechanism boundary."""
from dataclasses import asdict
from mechanism import WS,Ballot,BallotBox
import sys
sys.path.insert(0,str(WS/'chapter4/behavior'))
from behavior import BehaviorSession


class TokenWeightedBehaviorSession(BehaviorSession):
    def __init__(self,world,config):
        super().__init__(world,config)
        self.boxes={sid:BallotBox(world.environments[sid].proposal,world.environments[sid].rule,
            world.environments[sid].threshold,'SCENARIO_ASSUMED',world.environments[sid].flags,
            allow_assumed_rights=config['allow_assumed_rights']) for _,sid in self.contexts}
        self._last_signature={}
        self.mechanism_audit=[]

    def _check_invariants(self):
        # Retains all previous cash/time/VP assertions. No utility, schedule or view override.
        super()._check_invariants()
        updates={sid:[] for sid in self.boxes}
        for key,state in sorted(self.world.states.items()):
            if key not in self.contexts or state.choice is None:
                continue
            sig=(state.choice,state.vp,state.components,state.known_since)
            if self._last_signature.get(key)==sig:
                continue
            ctx=self.contexts[key]
            sid=key[1]
            updates[sid].append(Ballot(sid,key[0],state.choice,state.vp,state.components,state.known_since,
                f'{self.config["scenario_id"]}:{sid}:{key[0]}:{state.known_since}',ctx['network'],ctx['snapshot_block'],
                'SCENARIO_ASSUMED','SCENARIO_GRANTED','DECLARED_BEHAVIOR_CONFIG'))
            self._last_signature[key]=sig
        for sid,box in self.boxes.items():
            e=self.world.environments[sid]
            before=box.evaluate(self.world.clock)
            replacement_batch=any(b.wallet_id in {old.wallet_id for old in box.ballots} for b in updates[sid])
            if updates[sid]:
                box.commit(updates[sid],self.world.clock,replace=True)
            after=box.evaluate(self.world.clock)
            assert tuple(e.totals)==after.option_weights and e.votes_count==after.vote_count
            # Mechanism is canonical at the batch boundary. Token identity leaves values unchanged.
            e.totals=list(after.option_weights)
            if self.world.clock>e.proposal.end:
                assert e.voting_outcome==after.outcome
                e.voting_outcome=after.outcome
            if updates[sid]:
                self.mechanism_audit.append(dict(snapshot_id=sid,time=self.world.clock,
                    updates=len(updates[sid]),replacement_batch=replacement_batch,
                    outcome_before=before.outcome,outcome_after=after.outcome,
                    batch_outcome_changed=before.outcome!=after.outcome,
                    option_weights=after.option_weights,votes=after.vote_count,
                    information_exposure='EVALUATOR_ONLY_NOT_IN_DECISION_VIEW'))
