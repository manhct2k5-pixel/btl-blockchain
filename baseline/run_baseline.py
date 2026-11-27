"""Standalone offline Baseline. Writes only the selected directory below baseline/."""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from abm_inputs import export_inputs, phase
from catalog import catalog_records, load_catalog
from engine import (BINDING_TYPES, InputError, Proposal, UnknownRule, close, compare_snapshot,
                    govern, integer, level_b_eligibility, number, read_json, rows, select_rule, snapshot_time_valid, tally)
from integrity import (check_provenance, source_manifest, verify_existing,
                       verify_zip_if_present, verify_unchanged)


def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def write_csv(path, records, fields=None):
    records = list(records)
    fields = fields or (list(records[0]) if records else ['snapshot_id', 'issue_code', 'category', 'details'])
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def stream_votes(paths, provenance):
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            required = {'vote_id', 'snapshot_id', 'voter', 'created', 'choice_json', 'vp', 'vp_state',
                        'vp_by_strategy_json', 'source_raw_file', 'source_sha256', 'choice_label', 'choice_index'}
            if not reader.fieldnames or required-set(reader.fieldnames):
                raise InputError(f'Vote schema missing fields: {path}')
            for i, row in enumerate(reader, 1):
                if None in row or any(v is None for v in row.values()):
                    raise InputError(f'Malformed CSV: {path}, record {i}')
                check_provenance(row, provenance, f'{path.name}:{i}')
                yield row


def unique_map(records, key, name):
    result = {}
    for row in records:
        if not row.get(key) or row[key] in result:
            raise InputError(f'{name}: empty/duplicate key: {row.get(key)!r}')
        result[row[key]] = row
    return result


def official_outcome(status):
    return {'passed': 'ACCEPTED', 'enacted': 'ACCEPTED',
            'rejected': 'REJECTED', 'finished': 'FINISHED'}.get(status, '')


def summarize(records):
    b = [r for r in records if r['level_b_eligible_pre_outcome']]
    compared = [r for r in b if r['governance_comparison_available']]
    strict = [r for r in compared if not r['default_dependency_gap']]
    return {
        'proposals': len(records),
        'votes': sum(r['computed_votes'] for r in records),
        'snapshot_total_matches': sum(r['snapshot_total_match'] for r in records),
        'snapshot_all_options_matches': sum(r['snapshot_option_match'] for r in records),
        'snapshot_all_checks_match': sum(r['snapshot_total_match'] and r['snapshot_option_match'] and r['snapshot_count_match'] for r in records),
        'level_a_final': sum(r['level_a_final'] for r in records),
        'level_b_eligible_pre_outcome': len(b),
        'level_b_comparable': len(compared),
        'level_b_matches': sum(r['governance_match'] for r in compared),
        'level_b_mismatches': sum(not r['governance_match'] for r in compared),
        'level_b_match_rate': sum(r['governance_match'] for r in compared)/len(b) if b else None,
        'level_b_match_rate_among_comparable': sum(r['governance_match'] for r in compared)/len(compared) if compared else None,
        'level_b_reference_coverage': len(compared)/len(b) if b else None,
        'b_without_default_definition_gap': len(strict),
        'b_without_default_definition_gap_matches': sum(r['governance_match'] for r in strict),
        'level_c_selected': sum(r['level_c_source_selected'] for r in records),
        'level_c_matches': sum(r['governance_match'] for r in records if r['level_c_source_selected']),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent/'data_enrichment')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    source, output = args.source.resolve(), args.output.resolve()
    if not output.is_relative_to(root):
        raise InputError('Output directory must remain inside baseline/ to protect existing evidence')
    output.mkdir(parents=True, exist_ok=True)
    workspace = root.parent
    print('Verify read-only inputs and cached evidence...', flush=True)
    before = source_manifest(workspace)
    dump_json(output/'INPUT_MANIFEST.json', before)
    integrity = verify_existing(source)
    provenance = integrity.pop('source_log')
    zipcheck = verify_zip_if_present(workspace, source)
    rules = load_catalog(source)
    dump_json(output/'RULE_CATALOG.json', list(catalog_records(rules, source)))
    metadata = rows(source/'proposal_metadata.csv') + rows(source/'recent/proposal_metadata.csv')
    for row in metadata:
        check_provenance(row, provenance, row['snapshot_id'])
    proposals = {sid: Proposal.parse(r) for sid, r in unique_map(metadata, 'snapshot_id', 'proposals').items()}
    supplied_rules = unique_map(rows(source/'historical_rules.csv'), 'snapshot_id', 'historical_rules')
    historical_ids = {sid for sid, p in proposals.items() if p.raw['cohort'] == 'historical'}
    if set(supplied_rules) != historical_ids:
        raise InputError('historical_rules FK population does not match historical metadata')
    archive_path = next((source/'raw_downloads').glob('transparency_archive_proposals_json_*'))
    archive = unique_map(json.loads(archive_path.read_text(encoding='utf-8')), 'snapshot_id', 'archived Governance')
    current_source = json.loads((source/'governance_collected.json').read_text(encoding='utf-8'))
    current = {r['snapshot_id']: {k: r.get(k) for k in ['status', 'passed_by', 'rejected_by',
               'passed_description', 'rejected_description', 'updated_at']} for r in current_source}
    del current_source
    prior = unique_map(rows(source/'proposal_reconciliation_updated.csv'), 'snapshot_id', 'prior reconciliation')
    if set(prior) != set(proposals):
        raise InputError('Prior reconciliation FK population differs from input proposals')
    c_ids = {sid for sid, row in prior.items()
             if row['eligible_historical_outcome_conditional_on_code_version'] == 'True' and row['type'] in BINDING_TYPES}
    prior_choices = {}
    for row in rows(source/'choice_reconciliation.csv'):
        key = (row['snapshot_id'], integer(row['choice_index']))
        if key in prior_choices or key[0] not in proposals:
            raise InputError(f'Duplicate/orphan prior choice reference: {key}')
        prior_choices[key] = row
    expected_options = {(sid, i+1) for sid, p in proposals.items() for i in range(len(p.choices))}
    if set(prior_choices) != expected_options:
        raise InputError('Prior choice reference coverage differs from metadata')
    prior_summary = json.loads((source/'validation.json').read_text(encoding='utf-8'))
    if len(proposals) != prior_summary['proposals_total'] or len(c_ids) != 1006:
        raise InputError('Input population differs from declared validation or C=1006')
    print('Independent tally from individual votes...', flush=True)
    tallies = tally(proposals, stream_votes([source/'votes_recovered.csv', source/'recent/votes_recovered.csv'], provenance))
    count = sum(len(t.votes) for t in tallies.values())
    if count != prior_summary['votes_total']:
        raise InputError(f'Vote row count differs from validated population: {count}')
    validation, option_checks, issues, oracle_cases = [], [], [], []
    archived_cutoff = 1682850399  # Gh-pages commit UTC; closure cutoff, not an atomic vote capture time.

    def issue(sid, code, category, details, source_file=''):
        issues.append({'snapshot_id': sid, 'issue_code': code, 'category': category,
                       'details': details, 'source_raw_file': source_file})

    for sid in sorted(proposals):
        p, total = proposals[sid], tallies[sid]
        candidate = select_rule(rules, p.end, p.raw['cohort'])
        if sid in supplied_rules:
            sr = supplied_rules[sid]
            if sr['choices_json'] != p.raw['choices_json'] or sr['rule_code_candidate'] != (candidate.commit if candidate else ''):
                raise InputError(f'Historical rule assignment/choices differ from independently selected version: {sid}')
            if integer(sr['snapshot_block']) != p.snapshot_block or sr['network'] != p.raw['snapshot_network']:
                raise InputError(f'Historical rule snapshot/network differs: {sid}')
            if read_json(sr['strategies_json']) != list(p.strategies):
                raise InputError(f'Historical rule strategies differ: {sid}')
        g = archive.get(sid)
        threshold = number(g['required_to_pass'], sid) if g and g.get('required_to_pass') is not None else None
        decision, rule_error = None, ''
        if candidate and g:
            try:
                decision = govern(p.choices, total.totals, len(total.votes), threshold, candidate)
            except UnknownRule as exc:
                rule_error = str(exc)
        # Only after independent totals/decision do we read published score vectors.
        ref = compare_snapshot(p, total)
        pending = sum(v.state != 'final' for v in total.votes)
        a_ready = (ref['count_match'] and ref['option_match'] and ref['total_match'] and not pending
                   and p.raw['snapshot_state'] == 'closed' and p.raw['scores_state'] == 'final')
        snapshot_valid = snapshot_time_valid(p)
        b_ready, exclusion = level_b_eligibility(p, a_ready, candidate, g, archived_cutoff, snapshot_valid)
        if b_ready and decision is None:
            b_ready, exclusion = False, 'RULE_EVALUATION_UNSUPPORTED'
        # Official label is comparison only. It cannot select or alter the rule.
        status = g['status'] if g else p.raw.get('governance_status_current', '')
        expected = official_outcome(status)
        comparison = bool(b_ready and expected and decision)
        matched = bool(comparison and decision.outcome == expected)
        manual = current.get(sid, {})
        has_manual = bool(manual.get('passed_by') or manual.get('rejected_by'))
        budget = bool(candidate and candidate.budget_layer and p.raw['governance_type'] == 'grant'
                      and p.start >= 1672531200 and decision and decision.outcome == 'ACCEPTED')
        default_gap = bool(candidate and candidate.uses_default and not candidate.default_definition_verified)
        record = {
            'snapshot_id': sid, 'governance_proposal_id': p.raw['governance_proposal_id'],
            'cohort': p.raw['cohort'], 'phase': phase(p.end, p.raw['cohort']),
            'proposal_type': p.raw['governance_type'], 'created': p.created, 'voting_end': p.end,
            'computed_votes': len(total.votes), 'computed_total_vp': str(total.total),
            'computed_option_vp_json': json.dumps([str(x) for x in total.totals]),
            'snapshot_count_match': ref['count_match'], 'snapshot_total_match': ref['total_match'],
            'snapshot_option_match': ref['option_match'],
            'snapshot_max_option_abs_error': str(ref['max_option_abs_error']),
            'snapshot_total_abs_error': str(ref['total_abs_error']), 'pending_votes': pending,
            'snapshot_block_timestamp_valid': snapshot_valid, 'level_a_final': a_ready,
            'candidate_rule_commit': candidate.commit if candidate else '',
            'candidate_rule_family': candidate.family if candidate else '',
            'candidate_source_path': candidate.source_path if candidate else '',
            'candidate_source_sha256': candidate.source_sha256 if candidate else '',
            'rule_error': rule_error, 'default_dependency_gap': default_gap,
            'production_deployment_verified': False,
            'threshold_effective': str(decision.threshold) if decision else '',
            'label_projection': decision.projection if decision else '',
            'winner_label': decision.winner if decision else '',
            'computed_governance_outcome': decision.outcome if decision else '',
            'official_status_observed': status, 'official_status_as_voting_outcome': expected,
            'official_status_basis': 'archived_2023' if g else 'current_api_not_historical_reference',
            'level_b_eligible_pre_outcome': b_ready, 'level_b_exclusion_reason': exclusion,
            'governance_comparison_available': comparison, 'governance_match': matched if comparison else '',
            'level_c_source_selected': sid in c_ids, 'c_selection_uses_outcome': sid in c_ids,
            'manual_adjustment_fields_present_current': has_manual,
            'manual_fields_updated_at_current': manual.get('updated_at') or '',
            'budget_layer_unverified': budget, 'duplicate_choice_labels': len(set(c.lower() for c in p.choices)) != len(p.choices),
            'source_raw_file': p.raw['source_raw_file']}
        validation.append(record)
        references = json.loads(p.raw['scores_json'])
        for i, choice in enumerate(p.choices):
            old_choice = prior_choices[(sid, i+1)]
            if old_choice['choice_label'] != choice:
                raise InputError(f'Prior choice label differs: {sid}/{i+1}')
            option_checks.append({'snapshot_id': sid, 'choice_index': i+1, 'choice_label': choice,
                                  'computed_vp': str(total.totals[i]), 'reference_vp': references[i],
                                  'prior_enrichment_tally_match': close(total.totals[i], number(old_choice['recovered_vp'])),
                                  'source_raw_file': p.raw['source_raw_file']})
        if not (ref['count_match'] and ref['total_match'] and ref['option_match']):
            issue(sid, 'SNAPSHOT_TALLY_DIFF', 'DATA_OR_TALLY_ERROR', 'Independent tally differs from reference', p.raw['source_raw_file'])
        if pending:
            issue(sid, 'PENDING_VP', 'DATA_NOT_FINAL', f'{pending} source votes not final', p.raw['source_raw_file'])
        if not snapshot_valid:
            issue(sid, 'SNAPSHOT_TIME_NOT_VALIDATED', 'INSUFFICIENT_EVIDENCE', 'Keep timestamp/block as supplied; do not repair', p.raw['source_raw_file'])
        if not b_ready:
            issue(sid, exclusion, 'RULE_OR_REFERENCE_COVERAGE_GAP', rule_error or exclusion, p.raw['source_raw_file'])
        if default_gap:
            issue(sid, 'DEFAULT_CONSTANT_DEFINITION_NOT_ARCHIVED', 'MISSING_RULE_EVIDENCE',
                  'Candidate [yes,no,abstain] retained from prior documented model; declaration absent', candidate.source_path)
        if record['duplicate_choice_labels']:
            issue(sid, 'HISTORICAL_LABEL_COLLISION', 'SOURCE_DATA_SEMANTICS',
                  'A indexes remain separate; B follows original source label projection', p.raw['source_raw_file'])
        if budget:
            issue(sid, 'BUDGET_STATE_NOT_RECONSTRUCTED', 'GOVERNANCE_LAYER_UNVERIFIED',
                  'Vote acceptance does not determine allocation/funding; kept in B denominator', p.raw['governance_source_raw_file'])
        if comparison and not matched:
            category = 'GOVERNANCE_ADJUSTMENT_EVIDENCE' if has_manual else 'CAUSE_UNRESOLVED'
            issue(sid, 'GOVERNANCE_OUTCOME_DIFF', category,
                  json.dumps({'calculated': decision.outcome, 'observed_status': status,
                              'manual_fields_present_current': has_manual,
                              'current_passed_by': manual.get('passed_by'), 'current_rejected_by': manual.get('rejected_by'),
                              'current_updated_at': manual.get('updated_at'),
                              'causality_or_historical_override_time_proven': False}, ensure_ascii=False),
                  p.raw.get('governance_source_raw_file', ''))
        if b_ready:
            oracle_cases.append({'id': sid, 'commit': candidate.commit, 'choices': list(p.choices),
                                 'totals': [float(x) for x in total.totals],
                                 'threshold': float(threshold) if threshold is not None else None,
                                 'votes': [{'voter': v.voter, 'choice': v.choice, 'vp': float(v.vp)} for v in total.votes],
                                 'python_outcome': decision.outcome})
    write_csv(output/'BASELINE_VALIDATION.csv', validation)
    write_csv(output/'BASELINE_CHOICE_VALIDATION.csv', option_checks)
    write_csv(output/'BASELINE_MISMATCHES.csv', issues)
    dump_json(output/'ORACLE_CASES.json', oracle_cases)
    metric_rows = []
    for group in ['phase', 'proposal_type', 'candidate_rule_family']:
        for value in sorted({r[group] for r in validation}):
            metric_rows.append({'group': group, 'value': value, **summarize([r for r in validation if r[group] == value])})
    write_csv(output/'METRICS_BY_GROUP.csv', metric_rows)
    confusion = Counter((r['official_status_as_voting_outcome'], r['computed_governance_outcome'])
                        for r in validation if r['governance_comparison_available'])
    write_csv(output/'GOVERNANCE_CONFUSION.csv',
              [{'observed': k[0], 'calculated': k[1], 'proposals': v} for k, v in sorted(confusion.items())])
    abm = export_inputs(output, proposals, tallies, validation, write_csv)
    summary = summarize(validation)
    summary.update({
        'historical': summarize([r for r in validation if r['cohort'] == 'historical']),
        'recent': summarize([r for r in validation if r['cohort'] != 'historical']),
        'abm_inputs': abm, 'issues_by_category': dict(Counter(r['category'] for r in issues)),
        'governance_diffs_with_manual_fields': sum(r['level_b_eligible_pre_outcome'] and r['governance_comparison_available']
                                                  and not r['governance_match'] and r['manual_adjustment_fields_present_current']
                                                  for r in validation),
        'governance_diffs_unresolved': sum(r['level_b_eligible_pre_outcome'] and r['governance_comparison_available']
                                         and not r['governance_match'] and not r['manual_adjustment_fields_present_current']
                                         for r in validation),
        'governance_reference_coverage_unavailable': sum(r['level_b_eligible_pre_outcome'] and not r['governance_comparison_available']
                                                       for r in validation),
        'source_integrity': integrity, 'zip_check': zipcheck,
        'input_preservation': verify_unchanged(workspace, before),
        'network_access_used': False, 'model_type': 'deterministic_observed_vote_replay',
        'production_replay_certified': False, 'behavioral_model_fitted': False})
    dump_json(output/'BASELINE_SUMMARY.json', summary)
    dump_json(output/'OUTPUT_MANIFEST.json',
              {p.relative_to(output).as_posix(): {'sha256': __import__('engine').sha(p), 'bytes': p.stat().st_size}
               for p in sorted(output.rglob('*.csv'))
               if 'tests' not in p.relative_to(output).parts and 'replay' not in p.relative_to(output).parts})
    print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)
    return summary


if __name__ == '__main__':
    try:
        main()
    except (InputError, OSError, KeyError, ValueError) as exc:
        print(f'BASELINE ERROR: {exc}', file=sys.stderr)
        sys.exit(2)
