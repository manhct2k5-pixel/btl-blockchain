"""Hand-specified temporal mechanism fixtures. No inferred historical locks."""
from dataclasses import asdict
from decimal import Decimal as D
from fractions import Fraction as F
from policies import *
from escrow import EscrowLedger,LockEvent
from catalog import load_catalog
from engine import Proposal

G=1700000000
DAY=86400
YEAR=31536000
A='0x'+format(1,'040x')
B='0x'+format(2,'040x')
def event(kind,wallet,time,amount='0',end=0,tag=''):
    return LockEvent(f'{kind}:{wallet}:{time}:{tag}',kind,time,wallet,'alice' if wallet==A else 'bob',D(amount),end)

def ve_specs():
    short=[event('CREATE',A,G,'100',G+YEAR//2),event('CREATE',B,G,'80',G+YEAR)]
    full=[event('CREATE',A,G,'50',G+YEAR),event('CREATE',B,G,'80',G+YEAR)]
    return [
        dict(id='NO_LOCKS',snapshot=G,events=[]),
        dict(id='LINEAR_INITIAL',snapshot=G,events=short),
        dict(id='LINEAR_QUARTER',snapshot=G+YEAR//4,events=short),
        dict(id='LINEAR_HALF',snapshot=G+YEAR//2,events=short),
        dict(id='ALL_EXPIRED',snapshot=G+YEAR,events=short),
        dict(id='EXTEND_BEFORE_SNAPSHOT',snapshot=G+YEAR//4,events=short+[event('EXTEND',A,G+DAY,end=G+YEAR)]),
        dict(id='EXTEND_AFTER_SNAPSHOT',snapshot=G+YEAR//4,events=short+[event('EXTEND',A,G+YEAR//4+1,end=G+YEAR)]),
        dict(id='INCREASE_BEFORE_SNAPSHOT',snapshot=G+YEAR//4,events=full+[event('INCREASE',A,G+DAY,'50')]),
        dict(id='INCREASE_AFTER_SNAPSHOT',snapshot=G+YEAR//4,events=full+[event('INCREASE',A,G+YEAR//4+1,'50')]),
        dict(id='CREATE_AFTER_SNAPSHOT',snapshot=G,events=[event('CREATE',B,G,'80',G+YEAR),event('CREATE',A,G+DAY,'100',G+YEAR)]),
        dict(id='WITHDRAW_EXPIRED',snapshot=G+YEAR,events=short+[event('WITHDRAW',A,G+YEAR//2)]),
        dict(id='MAX_LOCK',snapshot=G,events=[event('CREATE',A,G,'100',G+YEAR)])]

def synthetic_proposal(sid,snapshot):
    p=Proposal(sid,('Yes','No'),({'name':'SYNTHETIC_MANA_REFERENCE_NOT_CHAIN_SCORING','network':'1'},),
        snapshot+10,snapshot+20,snapshot+100,42,snapshot,{'snapshot_network':'1','snapshot_block_hash':'SYNTHETIC'})
    rule=next(r for r in load_catalog(WS/'data_enrichment') if r.family=='threshold')
    return p,rule

def build_ve_case(spec):
    ledger=EscrowLedger({A:D(100),B:D(80)},{A:'alice',B:'bob'})
    for e in spec['events']:ledger.apply(e)
    p,rule=synthetic_proposal(spec['id'],spec['snapshot'])
    frozen=ledger.freeze(p.id,p.block_timestamp,42,p.created)
    ballots=[Ballot(p.id,w,c,D(v),(D(v),),p.start+1,f'{p.id}:{w}','1',42,
        'SCENARIO_ASSUMED','SCENARIO_GRANTED','DECLARED_SYNTHETIC_ASSETS_AND_LOCK_ACTIONS')
        for w,c,v in [(A,1,100),(B,2,80)]]
    return ledger,frozen,p,rule,ballots
