"""Offline deterministic tally and historical candidate rules; evaluator has no official labels."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import Iterable

getcontext().prec = 60
ZERO = Decimal(0)
ATOL, RTOL = Decimal('0.000001'), Decimal('0.000000001')
INVALID = 'invalid question/options'
DEFAULT_CANDIDATE = ('yes', 'no', 'abstain')
BINDING_TYPES = frozenset({'grant', 'poi', 'ban_name', 'linked_wearables', 'governance', 'catalyst'})


class InputError(ValueError):
    """Input cannot safely be tallied without changing the source data."""


class UnknownRule(ValueError):
    pass


def number(value, context='number') -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InputError(f'{context}: invalid numeric value {value!r}') from exc
    if not x.is_finite() or x < 0:
        raise InputError(f'{context}: VP/threshold must be finite and nonnegative: {value!r}')
    return x


def integer(value, context='integer') -> int:
    n = number(value, context)
    if n != n.to_integral_value():
        raise InputError(f'{context}: expected integer, got {value!r}')
    return int(n)


def close(actual: Decimal, reference: Decimal) -> bool:
    return abs(actual-reference) <= ATOL + RTOL*abs(reference)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise InputError(f'Missing input file: {path}')
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise InputError(f'Empty or duplicate CSV header: {path}')
        result = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in result):
        raise InputError(f'Malformed CSV row: {path}')
    return result


def read_json(text: str, context='JSON'):
    try:
        return json.loads(text, parse_float=Decimal)
    except (ValueError, TypeError) as exc:
        raise InputError(f'{context}: malformed JSON') from exc


@dataclass(slots=True)
class Proposal:
    id: str
    choices: tuple[str, ...]
    strategies: tuple[dict, ...]
    created: int
    start: int
    end: int
    snapshot_block: int
    block_timestamp: int | None
    raw: dict[str, str]

    @classmethod
    def parse(cls, r: dict[str, str]) -> 'Proposal':
        required = {'snapshot_id', 'choices_json', 'strategies_json', 'created', 'start', 'end', 'snapshot_block'}
        if required-set(r):
            raise InputError(f'Proposal schema missing: {sorted(required-set(r))}')
        choices = read_json(r['choices_json'], r['snapshot_id'])
        strategies = read_json(r['strategies_json'], r['snapshot_id'])
        if not r['snapshot_id'] or not isinstance(choices, list) or not choices or not all(isinstance(x, str) and x for x in choices):
            raise InputError(f'Invalid proposal id/choices: {r["snapshot_id"]}')
        if not isinstance(strategies, list) or not strategies:
            raise InputError(f'Missing strategies: {r["snapshot_id"]}')
        start, end = integer(r['start']), integer(r['end'])
        if start >= end:
            raise InputError(f'Nonpositive voting window: {r["snapshot_id"]}')
        bt = r.get('snapshot_block_timestamp', '')
        return cls(r['snapshot_id'], tuple(choices), tuple(strategies), integer(r['created']), start, end,
                   integer(r['snapshot_block']), integer(bt) if bt else None, r)


@dataclass(frozen=True, slots=True)
class Vote:
    id: str
    proposal: str
    voter: str
    created: int
    choice: int
    vp: Decimal
    components: tuple[Decimal, ...]
    state: str
    source_file: str

    @classmethod
    def parse(cls, r: dict[str, str], p: Proposal) -> 'Vote':
        ident, wallet = r.get('vote_id', ''), r.get('voter', '').lower()
        if not ident or r.get('snapshot_id') != p.id:
            raise InputError('Vote id missing or proposal FK mismatch')
        if not re.fullmatch(r'0x[0-9a-f]{40}', wallet):
            raise InputError(f'Invalid wallet in vote {ident}')
        c = read_json(r['choice_json'], ident)
        if type(c) is not int or not 1 <= c <= len(p.choices):
            raise InputError(f'Choice index out of bounds in vote {ident}: {c!r}')
        if integer(r['choice_index'], ident) != c or r['choice_label'] != p.choices[c-1]:
            raise InputError(f'Choice index/label disagreement in vote {ident}')
        components = read_json(r['vp_by_strategy_json'], ident)
        if not isinstance(components, list) or len(components) != len(p.strategies):
            raise InputError(f'Strategy length mismatch in vote {ident}')
        parts = tuple(number(x, ident) for x in components)
        vp = number(r['vp'], ident)
        if not close(sum(parts, ZERO), vp):
            raise InputError(f'VP component sum differs from total in vote {ident}')
        created = integer(r['created'], ident)
        if not p.start <= created <= p.end:
            raise InputError(f'Vote outside voting window: {ident}')
        if r['vp_state'] not in {'final', 'pending'}:
            raise InputError(f'Unknown vp_state in vote {ident}: {r["vp_state"]}')
        return cls(ident, p.id, wallet, created, c, vp, parts, r['vp_state'], r['source_raw_file'])


@dataclass(slots=True)
class Tally:
    totals: list[Decimal]
    votes: list[Vote] = field(default_factory=list)

    @property
    def total(self):
        return sum(self.totals, ZERO)


def tally(proposals: dict[str, Proposal], records: Iterable[dict[str, str]]) -> dict[str, Tally]:
    result = {pid: Tally([ZERO for _ in p.choices]) for pid, p in proposals.items()}
    ids, keys = set(), set()
    for r in records:
        sid = r.get('snapshot_id')
        if sid not in proposals:
            raise InputError(f'Unknown proposal referenced by vote: {sid}')
        v = Vote.parse(r, proposals[sid])
        if v.id in ids:
            raise InputError(f'Duplicate vote id: {v.id}')
        if (v.proposal, v.voter) in keys:
            raise InputError(f'Duplicate voter-proposal; no automatic replacement: {v.proposal}/{v.voter}')
        ids.add(v.id); keys.add((v.proposal, v.voter))
        result[sid].totals[v.choice-1] += v.vp  # Never add delegated VP a second time.
        result[sid].votes.append(v)
    return result


def js_keys(d: dict[str, Decimal]) -> list[str]:
    numeric = [k for k in d if re.fullmatch(r'0|[1-9][0-9]*', k) and int(k) < 2**32-1]
    return sorted(numeric, key=int) + [k for k in d if k not in numeric]


@dataclass(frozen=True, slots=True)
class Rule:
    commit: str
    commit_timestamp: int
    family: str
    source_path: str
    source_sha256: str
    source_url: str
    helper_path: str = ''
    default_definition_verified: bool = False

    @property
    def uses_default(self):
        return self.family in {'abstain_default', 'abstain_legacy'}

    @property
    def budget_layer(self):
        return self.commit_timestamp >= 1677524162


def select_rule(rules: list[Rule], end: int, cohort: str) -> Rule | None:
    if cohort != 'historical':
        return None
    eligible = [r for r in rules if r.commit_timestamp <= end]
    return max(eligible, key=lambda r: r.commit_timestamp) if eligible else None


@dataclass(frozen=True, slots=True)
class Decision:
    outcome: str
    winner: str
    winner_vp: Decimal
    threshold: Decimal
    projection: str
    default_dependency_gap: bool


def govern(choices: tuple[str, ...], totals: list[Decimal], vote_count: int,
           threshold: Decimal | None, rule: Rule | None) -> Decision:
    """Pure function: independent tallies in; no scores or official outcome accepted."""
    if rule is None:
        raise UnknownRule('No historical candidate version for this proposal')
    if rule.family not in {'early_empty', 'early_index_bug_empty', 'early_index_bug', 'early_two', 'early_three', 'threshold', 'invalid_votes',
                           'invalid_scores', 'abstain_default', 'abstain_legacy'}:
        raise UnknownRule(f'Unreviewed rule family: {rule.family}')
    if len(choices) != len(totals) or any(x < 0 or not x.is_finite() for x in totals):
        raise InputError('Invalid independent option totals')
    early = rule.family in {'early_empty', 'early_index_bug_empty', 'early_index_bug', 'early_two', 'early_three'}
    lowered = [c.lower() for c in choices]
    if any(c in {'__proto__', 'constructor', 'prototype'} for c in lowered):
        raise UnknownRule('Unsupported JavaScript object property name')
    index_bug = rule.family.startswith('early_index_bug')
    labels = list(choices) if rule.family in {'early_empty', 'early_two'} or index_bug else lowered
    projection = 'first_index_per_label' if rule.family in {'invalid_scores', 'abstain_default', 'abstain_legacy'} else 'sum_indices_per_label'
    if index_bug:
        projection = 'numeric_index_source_bug'
        labels = [str(i) for i in range(len(choices))]
    mapped: dict[str, Decimal] = {}
    for label, value in zip(labels, totals):
        if projection == 'first_index_per_label':
            mapped.setdefault(label, value)
        else:
            mapped[label] = mapped.get(label, ZERO)+value
    new = rule.uses_default
    order = [c for c in js_keys(mapped) if not (new and c == 'abstain')]
    if not order:
        raise UnknownRule('Historical winner reducer has no remaining option')
    winner = order[0]
    for key in order[1:]:
        if mapped[key] > mapped[winner] or (new and mapped[key] == mapped[winner]):
            winner = key
    floor = threshold if threshold is not None else ZERO
    if not early and threshold is None:
        raise UnknownRule('Historical threshold missing; no source null/default provenance')
    pair_sets = [('yes', 'no')]
    if rule.family not in {'early_empty', 'early_two', 'early_index_bug_empty', 'early_index_bug'}:
        pair_sets.append(('for', 'against'))
    pair_sets.append(('accept', 'reject'))
    recognized = None
    for yes, no in pair_sets:
        if rule.family in {'invalid_votes', 'invalid_scores', 'abstain_default', 'abstain_legacy'} and yes != 'yes':
            expected = [yes, no, INVALID]
        else:
            expected = [yes, no]
        if sorted(lowered) == sorted(expected):
            if rule.family == 'abstain_default' and yes == 'yes':
                continue
            recognized = (yes, no)
    if new and sorted(lowered) == sorted(DEFAULT_CANDIDATE):
        recognized = ('yes', 'no')
    gap = new and not rule.default_definition_verified
    if early:
        if recognized is None or (rule.family in {'early_empty', 'early_index_bug_empty'} and vote_count == 0):
            outcome = 'FINISHED'
        else:
            yes, no = recognized
            outcome = 'ACCEPTED' if yes in mapped and no in mapped and mapped[yes] > mapped[no] else 'REJECTED'
    elif mapped[winner] == 0 or mapped[winner] < floor:
        outcome = 'REJECTED'
    elif rule.family != 'threshold' and winner == INVALID:
        outcome = 'REJECTED'
    elif recognized:
        yes, no = recognized
        outcome = 'ACCEPTED' if mapped[yes] > mapped[no] else 'REJECTED'
    else:
        outcome = 'FINISHED'
    return Decision(outcome, winner, mapped[winner], floor, projection, gap)


def compare_snapshot(p: Proposal, result: Tally) -> dict:
    """Reference scores are consulted only here, after independent tallying."""
    reference = read_json(p.raw['scores_json'], p.id)
    if not isinstance(reference, list) or len(reference) != len(p.choices):
        raise InputError(f'Snapshot score vector length mismatch: {p.id}')
    ref = [number(x, p.id) for x in reference]
    total = number(p.raw['scores_total'], p.id)
    count = integer(p.raw['snapshot_votes'], p.id)
    return {'count_match': len(result.votes) == count,
            'option_match': all(close(a, b) for a, b in zip(result.totals, ref)),
            'total_match': close(result.total, total),
            'max_option_abs_error': max(abs(a-b) for a, b in zip(result.totals, ref)),
            'total_abs_error': abs(result.total-total)}


def snapshot_time_valid(p: Proposal) -> bool:
    return p.snapshot_block > 0 and p.block_timestamp is not None and p.block_timestamp <= p.created


def level_b_eligibility(p: Proposal, a_ready: bool, rule: Rule | None,
                        governance: dict | None, archived_cutoff: int, snapshot_valid: bool) -> tuple[bool, str]:
    """Pre-outcome gate. Cannot examine the value of an official result label."""
    if not a_ready:
        return False, 'A_NOT_FINAL_OR_INCOMPLETE'
    if p.raw.get('cohort') != 'historical' or rule is None:
        return False, 'NO_HISTORICAL_RULE'
    if rule.commit_timestamp > p.end:
        return False, 'FUTURE_RULE_VERSION'
    if not governance or p.raw.get('governance_metadata_basis') != 'archive_2023_04_30':
        return False, 'NO_ARCHIVED_GOVERNANCE'
    if p.end > archived_cutoff:
        return False, 'NOT_CLOSED_BY_ARCHIVED_CAPTURE'
    if not snapshot_valid:
        return False, 'SNAPSHOT_TIME_UNVERIFIED'
    if governance.get('required_to_pass') is None:
        return False, 'THRESHOLD_UNVERIFIED'
    if governance.get('configuration', {}).get('choices') != list(p.choices):
        return False, 'GOVERNANCE_CHOICES_DIFFER'
    return True, ''
