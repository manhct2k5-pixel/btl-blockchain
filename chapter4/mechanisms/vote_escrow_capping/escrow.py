"""Synthetic lock-action ledger. Assets stay separate from voting points and utility."""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction as F
from types import MappingProxyType
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
WS=ROOT.parents[2]
sys.path.insert(0,str(WS/'chapter4/mechanisms/quadratic_voting'))
from qv_mechanism import InputError,valid_vp

def time_int(t):
    if type(t) is not int or t<0:raise InputError('Time/block must be nonnegative integer')

@dataclass(frozen=True)
class LockEvent:
    event_id:str
    kind:str
    time:int
    wallet:str
    actor:str
    amount:Decimal=Decimal(0)
    end:int=0
    asset:str='MANA'
    network:str='1'

@dataclass(frozen=True)
class LockState:
    liquid:F
    locked:F=F(0)
    start:int=0
    end:int=0
    position_id:str=''

@dataclass(frozen=True)
class FrozenEscrow:
    snapshot_id:str
    time:int
    network:str
    block:int
    states:object
    controllers:object
    max_seconds:int
    asset:str='MANA'
    evidence:str='SYNTHETIC_DECLARED_NOT_CHAIN_DATA'

class EscrowLedger:
    """One lock per wallet; CREATE/INCREASE/EXTEND/WITHDRAW are explicit actions.

    No autonomous lock choice, transfers, delegation, income or fees are inferred.
    Temporal order is the input event order, including same-second events.
    """
    def __init__(self,balances,controllers,genesis=1700000000,max_seconds=31536000,min_seconds=86400):
        time_int(genesis);time_int(max_seconds);time_int(min_seconds)
        if not 0<min_seconds<=max_seconds:raise InputError('Invalid lock limits')
        if set(balances)!=set(controllers) or not balances:raise InputError('Controller coverage required')
        from model import normalize_wallet
        for w,x in balances.items():
            if normalize_wallet(w)!=w or not isinstance(controllers[w],str) or not controllers[w]:
                raise InputError('Explicit canonical wallet/controller required')
            valid_vp(x)
        self.genesis,self.max_seconds,self.min_seconds=genesis,max_seconds,min_seconds
        self.controllers=MappingProxyType(dict(controllers))
        self.initial=MappingProxyType({w:F(x) for w,x in balances.items()})
        self._states={w:LockState(F(x)) for w,x in balances.items()}
        self._history={w:[(genesis,self._states[w])] for w in balances}
        self._events=[];self._ids=set();self._clock=genesis

    @property
    def events(self):return tuple(self._events)

    def apply(self,e):
        if not isinstance(e,LockEvent):raise InputError('LockEvent required')
        time_int(e.time);time_int(e.end);valid_vp(e.amount)
        if e.asset!='MANA' or e.network!='1':raise InputError('Only declared synthetic MANA on network 1')
        if e.wallet not in self._states or self.controllers[e.wallet]!=e.actor:
            raise InputError('Undeclared wallet or asset controller')
        if e.time<self._clock or not e.event_id or e.event_id in self._ids:
            raise InputError('Event time/id invalid')
        old=self._states[e.wallet];amount=F(e.amount)
        if e.kind=='CREATE':
            if old.locked or amount<=0 or amount>old.liquid:
                raise InputError('New positive funded lock requires no outstanding position')
            if not self.min_seconds<=e.end-e.time<=self.max_seconds:
                raise InputError('Lock duration outside declared bounds')
            new=LockState(old.liquid-amount,amount,e.time,e.end,e.event_id)
        elif e.kind=='INCREASE':
            if not old.locked or e.time>=old.end or amount<=0 or amount>old.liquid or e.end!=0:
                raise InputError('Increase requires live funded position; does not extend time')
            new=LockState(old.liquid-amount,old.locked+amount,old.start,old.end,old.position_id)
        elif e.kind=='EXTEND':
            if not old.locked or e.time>=old.end or amount!=0 or not old.end<e.end<=e.time+self.max_seconds:
                raise InputError('Extension must strictly increase a live lock end within maximum')
            new=LockState(old.liquid,old.locked,old.start,e.end,old.position_id)
        elif e.kind=='WITHDRAW':
            if not old.locked or e.time<old.end or amount!=0 or e.end!=0:
                raise InputError('Withdrawal requires expired lock and no custom amount/end')
            new=LockState(old.liquid+old.locked)
        else:raise InputError('Unsupported action; locked voting delegation/transfer disabled')
        if new.liquid<0 or new.locked<0 or new.liquid+new.locked!=self.initial[e.wallet]:
            raise InputError('Escrow asset conservation failed')
        self._states[e.wallet]=new
        self._history[e.wallet].append((e.time,new))
        self._events.append(e);self._ids.add(e.event_id);self._clock=e.time
        return new

    def state_at(self,wallet,t):
        time_int(t)
        if t<self.genesis or wallet not in self._history:raise InputError('Unknown historical asset state')
        return next(s for time,s in reversed(self._history[wallet]) if time<=t)

    def freeze(self,snapshot_id,t,block,known_at):
        time_int(t);time_int(block);time_int(known_at)
        if known_at<t or block<=0 or not snapshot_id:raise InputError('Future snapshot or invalid identifier')
        states={w:self.state_at(w,t) for w in self.initial}
        return FrozenEscrow(snapshot_id,t,'1',block,MappingProxyType(states),
                            self.controllers,self.max_seconds)

def opportunity_cost_utility(amount,remaining_seconds,rate_utility_per_mana_second):
    """Optional declared simple opportunity cost in individual utility, not a cash debit.

    Rate must be supplied; principal is recoverable, not fully expensed as loss.
    No historical economic calibration is claimed.
    """
    valid_vp(amount);time_int(remaining_seconds)
    if rate_utility_per_mana_second is None:raise InputError('Unknown opportunity cost rate')
    rate=F(rate_utility_per_mana_second)
    if rate<0:raise InputError('Negative opportunity cost rate')
    return F(amount)*remaining_seconds*rate
