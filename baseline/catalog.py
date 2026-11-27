"""Manual source-to-rule family mapping, fixed independently of observed outcomes."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from engine import InputError, Rule, rows, sha

FAMILIES = {
    'bca40873': 'early_index_bug_empty', '173cee84': 'early_index_bug_empty',
    '5e6b0182': 'early_index_bug', 'b1c65056': 'early_two',
    '8b1e29b5': 'early_three', '51c4835c': 'early_three', '8932e972': 'early_three',
    '8daa5752': 'threshold',
    '83ffa82f': 'invalid_votes', '9dca8654': 'invalid_votes',
    '0731a47e': 'invalid_votes', '4bc07bef': 'invalid_votes',
    'f445561e': 'invalid_scores', 'e05af5e6': 'invalid_scores',
    'd5542bf4': 'invalid_scores', '206fed2a': 'invalid_scores', '922f3edb': 'invalid_scores',
    '7846e827': 'abstain_default', '5e28acc6': 'abstain_legacy', '0476346c': 'abstain_legacy',
}


def load_catalog(source: Path) -> list[Rule]:
    result = []
    for row in rows(source/'rule_source_versions.csv'):
        commit = row['commit']
        family = FAMILIES.get(commit[:8])
        if family is None:
            raise InputError(f'Unknown code version, requires source review: {commit}')
        paths = list((source/'raw_downloads').glob('historical_rule_'+commit+'_*'))
        if len(paths) != 1:
            raise InputError(f'Ambiguous source file: {commit}')
        helper = ''
        if family.startswith('abstain'):
            hp = list((source/'raw_downloads').glob('outcome_utils_'+commit+'_*'))
            if len(hp) != 1:
                raise InputError(f'Missing winner/helper source: {commit}')
            helper = hp[0].relative_to(source).as_posix()
        result.append(Rule(commit, int(datetime.fromisoformat(row['commit_date_utc'].replace('Z', '+00:00')).timestamp()),
                           family, paths[0].relative_to(source).as_posix(), sha(paths[0]),
                           row['source_url'], helper, False))
    return sorted(result, key=lambda r: r.commit_timestamp)


def catalog_records(rules: list[Rule], source: Path):
    for rule in rules:
        d = asdict(rule)
        d['helper_sha256'] = sha(source/rule.helper_path) if rule.helper_path else ''
        d['default_candidate'] = ['yes', 'no', 'abstain'] if rule.uses_default else None
        d['default_constant_basis'] = 'prior enrichment candidate; definition absent from offline archive' if rule.uses_default else 'not used'
        d['production_deployment_verified'] = False
        d['projection_basis'] = ('numeric index keys, but Boolean comparison reads label keys (source bug)'
                                 if rule.family.startswith('early_index_bug') else
                                 'getVotingResults uses choices.indexOf' if rule.family in {'invalid_scores', 'abstain_default', 'abstain_legacy'}
                                 else 'vote loop adds vp by label')
        yield d
