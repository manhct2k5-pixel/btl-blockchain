"""LEVEL_A_WORLD_GENERATOR_V2: Explicit Level-A distributions, isolated streams,
strictly pre-snapshot timing fix for SPLIT (allocation_at = snapshot - 1)
and Vote-Escrow (CREATE lock at snapshot - 10, genesis = snapshot - 86400).
"""
import hashlib, json, random, sys
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parents[2]
sys.path.insert(0, str(WS / 'chapter4/experiments/attack_model'))
from attack_core import parse_config, make_policy, feasible, ResourceLedger

STREAMS = ('vp', 'preferences', 'budgets', 'information', 'attack', 'ownership', 'locks')
GENERATOR_VERSION = 'LEVEL_A_WORLD_GENERATOR_V2'

def jsonable(val):
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, F):
        return str(val)
    if isinstance(val, D):
        return str(val)
    if isinstance(val, dict):
        return {str(k): jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [jsonable(v) for v in val]
    return str(val)

def canonical(value):
    return json.dumps(jsonable(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def seed_for(master, group, replicate, family, variable):
    return int(digest([GENERATOR_VERSION, master, group, replicate, family, variable]), 16)

def decimal_text(x):
    x = F(x)
    with localcontext() as c:
        c.prec = 100
        return format(D(x.numerator) / D(x.denominator), 'f')

def probabilities(x):
    x = F(str(x))
    return {'ACCEPTED': decimal_text(x), 'REJECTED': decimal_text(1 - x)}

def load_contract():
    c = json.loads((ROOT / 'MC_MAIN_CONTRACT.json').read_text(encoding='utf-8'))
    if c['main_worlds'] != 1000 or c['ve_worlds'] != 200 or not c['large_scale_enabled']:
        raise ValueError('Contract must be configured for 1000 MAIN worlds and 200 VE worlds')
    return c

class Draws:
    def __init__(self, c, group, replicate, family):
        self.d = c['distributions']
        self.seeds = {s: seed_for(c['master_seed'], group, replicate, family, s) for s in STREAMS}
        self.rng = {s: random.Random(seed) for s, seed in self.seeds.items()}

    def draw(self, name, stream):
        spec = self.d[name]
        params = spec['parameters']
        rng = self.rng[stream]
        if spec['kind'] == 'choice':
            return rng.choice(params['values'])
        if spec['kind'] == 'bernoulli':
            p = F(params['probability'])
            return rng.randrange(p.denominator) < p.numerator
        if spec['kind'] == 'randint':
            return rng.randint(params['low'], params['high'])
        raise ValueError('Unregistered distribution ' + name)

def generate_world(c, group, replicate):
    if group not in ('MAIN', 'VE'):
        raise ValueError('Unknown world group')
    limit = c['main_worlds'] if group == 'MAIN' else c['ve_worlds']
    if type(replicate) is not int or not 0 <= replicate < limit:
        raise ValueError('Replicate outside contract limit')

    selection_seed = seed_for(c['master_seed'], group, replicate, 'FAMILY_SELECTION', 'scenario_selection')
    family = random.Random(selection_seed).choice(
        c['distributions']['family_main' if group == 'MAIN' else 'family_ve']['parameters']['values']
    )
    d = Draws(c, group, replicate, family)
    g = c['proposal']['epoch']
    p = c['proposal']

    count = c['base_voters']
    wallets = ['0x' + format(i + 1, '040x') for i in range(count + c['split_aliases'])]
    owners = {w: ('attacker' if i == 0 else 'person' + str(i)) for i, w in enumerate(wallets[:count])}
    if d.draw('shared_controller', 'ownership'):
        owners[wallets[2]] = owners[wallets[1]]

    principals = {}
    for owner in sorted(set(owners.values())):
        is_att = (owner == 'attacker')
        principals[owner] = dict(
            budget=str(d.draw('attacker_budget' if is_att else 'other_budget', 'budgets')),
            governance_values={s: str(d.draw('governance_value', 'preferences')) for s in ('ACCEPTED', 'REJECTED')},
            success_values={'ACCEPTED': str(d.draw('attacker_benefit', 'preferences')) if is_att else '0', 'REJECTED': '0'},
            money_to_utility=c['money_to_utility'],
            epsilon=str(d.draw('epsilon', 'preferences')),
            utility_unit='CHI_' + owner,
            beliefs_keep=probabilities(d.draw('attacker_belief_keep' if is_att else 'voter_belief_keep', 'information')),
            beliefs_act=probabilities(d.draw('attacker_belief_act' if is_att else 'voter_belief_act', 'information'))
        )

    voters = {}
    asset_balances = {}
    for w in wallets[:count]:
        amount = d.draw('source_vp' if group == 'MAIN' else 'mana_balance', 'vp')
        if group == 'VE':
            asset_balances[w] = str(amount)
        rights = d.draw('rights_granted', 'ownership')
        choice = 1 if d.draw('initial_yes', 'information') else 2
        voters[w] = dict(
            principal=owners[w],
            vp=str(amount),
            choice=choice if rights else None,
            rights='GRANTED' if rights else 'DENIED',
            rights_at=g - 10,
            can_replace=d.draw('replace_allowed', 'ownership'),
            beliefs_keep=probabilities(d.draw('voter_belief_keep', 'information')),
            beliefs_act=probabilities(d.draw('voter_belief_act', 'information')),
            resource_utility=str(d.draw('resource_cost', 'preferences')),
            risk_utility=str(d.draw('risk_cost', 'preferences')),
            cash_fee=str(d.draw('action_fee', 'budgets'))
        )

    targets = [wallets[0]] if family in ('SWITCH', 'SPLIT') else [wallets[1], wallets[2]] if family == 'BRIBE_E' else [wallets[1]]
    if family == 'MOBILIZE':
        voters[wallets[1]]['choice'] = None

    delay = d.draw('decision_delay', 'information')
    published = g + p['start_offset'] + 2
    if d.draw('late_action', 'information'):
        published = g + p['end_offset'] + 1

    attack = dict(
        family=family,
        target_outcome=c['target_outcome'],
        target_choice=c['target_choice'],
        published_at=published,
        decision_at=published + int(delay),
        targets=targets,
        payments={w: str(d.draw('offer', 'attack')) if family == 'BRIBE_E' else '0' for w in targets},
        setup_fee=str(d.draw('setup_fee', 'budgets')),
        expected_paid='0',
        resource_utility=str(d.draw('resource_cost', 'preferences')),
        opportunity_utility=str(d.draw('opportunity_cost', 'preferences')),
        capital_utility=str(d.draw('capital_cost', 'preferences')),
        risk_utility=str(d.draw('risk_cost', 'preferences')),
        split=[],
        allocation_at=g - 1, # strictly prior to snapshot g
        snapshot_state_unchanged=True
    )
    liability = sum((F(x) for x in attack['payments'].values()), F(0))
    attack['expected_paid'] = decimal_text(liability * F(str(d.draw('expected_payment_fraction', 'information'))))

    # STRICT PRE-SNAPSHOT TIMING FIX FOR SPLIT
    if family == 'SPLIT':
        source = wallets[0]
        voters[source].update(rights='GRANTED', choice=c['target_choice'])
        for w in wallets[count:]:
            voters[w] = deepcopy(voters[source])
            voters[w].update(vp='0', choice=None, principal='attacker')
        partition = [source] + wallets[count:]
        attack.update(
            published_at=g - 3,
            decision_at=g - 2,
            allocation_at=g - 1, # strictly prior to snapshot g
            split=[dict(wallet=w, vp=decimal_text(F(voters[source]['vp']) / len(partition))) for w in partition]
        )

    ve = None
    if group == 'VE':
        v = c['ve']
        events = []
        # STRICT PRE-SNAPSHOT TIMING FIX FOR VOTE-ESCROW
        # Lock creation happens at g - 10 (matching voter rights_at), genesis at g - 86400
        for w in wallets[:count]:
            amount = F(asset_balances[w]) * F(str(d.draw('lock_amount_fraction', 'locks')))
            remaining = int(v['max_seconds'] * F(str(d.draw('lock_remaining_fraction', 'locks'))))
            lock_time = g - 10
            end = lock_time + remaining
            events.append(dict(
                event_id='create:' + w,
                kind='CREATE',
                time=lock_time, # strictly prior to snapshot g
                wallet=w,
                actor=owners[w],
                amount=decimal_text(amount),
                end=end,
                asset=v['asset'],
                network=v['network']
            ))
            if remaining < v['max_seconds'] and d.draw('future_lock_extension', 'locks'):
                events.append(dict(
                    event_id='future_extend:' + w,
                    kind='EXTEND',
                    time=g + 1, # strictly after snapshot g, must NOT affect snapshot VP
                    wallet=w,
                    actor=owners[w],
                    amount='0',
                    end=g + v['max_seconds'],
                    asset=v['asset'],
                    network=v['network']
                ))
        events.sort(key=lambda e: (e['time'], e['event_id']))
        ve = dict(
            asset=v['asset'],
            network=v['network'],
            balances_mana=asset_balances,
            genesis=g - 86400, # valid past genesis
            max_seconds=v['max_seconds'],
            min_seconds=v['min_seconds'],
            events=events
        )

    world_id = f'{group}_{replicate:04d}'
    config = dict(
        schema='4.3-attack-v1',
        scenario_id=world_id,
        data_label='SYNTHETIC_TEST_ONLY',
        seed=seed_for(c['master_seed'], group, replicate, family, 'model'),
        mechanism='TW' if group == 'MAIN' else 'VE',
        cap_vp=c['cap_vp'],
        proposal=dict(
            id='SYNTHETIC_' + world_id,
            choices=['Yes', 'No'],
            snapshot_time=g,
            created=g + p['created_offset'],
            start=g + p['start_offset'],
            end=g + p['end_offset'],
            network=p['network'],
            block=p['block']
        ),
        principals=principals,
        attacker='attacker',
        voters=voters,
        attack=attack,
        rho='FIXED_BASELINE_OUTSIDERS_NO_EXTRA_REACTION',
        ve=ve
    )
    parsed = parse_config(config)
    make_policy(parsed)
    status = feasible(parsed, ResourceLedger({p: s['budget'] for p, s in parsed['principals'].items()}))
    return dict(
        world_id=world_id,
        replicate_id=replicate,
        group=group,
        family=family,
        config=config,
        generator_version=GENERATOR_VERSION,
        master_seed=c['master_seed'],
        stream_seeds={'scenario_selection': selection_seed, **d.seeds},
        input_hash=digest(config),
        distribution_hash=digest(c['distributions']),
        schema_validated=True,
        structural_feasibility=status,
        evidence_label='SYNTHETIC_ASSUMPTION',
        calibrated=False
    )
