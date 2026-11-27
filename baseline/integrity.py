"""Verify offline evidence without importing or executing earlier collection scripts."""
import csv
import json
import zipfile
from pathlib import Path, PurePosixPath

from engine import InputError, rows, sha


def source_manifest(workspace: Path) -> dict:
    files = []
    for directory in ['data_enrichment', 'audit_dao', 'Decentraland']:
        files.extend(p for p in (workspace/directory).rglob('*')
                     if p.is_file() and not set(p.parts)&{'.venv', '.git', '__pycache__'})
    files.extend(p for p in workspace.glob('*') if p.is_file())
    return {p.relative_to(workspace).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(set(files))}


def verify_existing(source: Path) -> dict:
    prior = json.loads((source/'replay_verification.json').read_text(encoding='utf-8'))
    for name, expected in prior['sha256'].items():
        path = source/Path(name.replace('\\', '/'))
        if not path.is_file() or sha(path) != expected:
            raise InputError(f'Enrichment replay checksum changed: {name}')
    logs = rows(source/'source_log.csv')
    allowed = {}
    for row in logs:
        path = (source/row['raw_file']).resolve()
        if not path.is_relative_to(source.resolve()):
            raise InputError(f'Raw path escapes source directory: {row["raw_file"]}')
        if not path.is_file() or sha(path) != row['sha256']:
            raise InputError(f'Raw response checksum mismatch: {row["raw_file"]}')
        allowed[row['raw_file']] = row
    return {'normalized_checksums_verified': len(prior['sha256']),
            'raw_checksums_verified': len(logs), 'source_log': allowed}


def check_provenance(row: dict, log: dict, context: str):
    path = row.get('source_raw_file', '')
    if path not in log:
        raise InputError(f'{context}: raw source missing from source_log')
    if row.get('source_sha256') != log[path]['sha256']:
        raise InputError(f'{context}: source SHA disagrees with source_log')


def verify_zip_if_present(workspace: Path, source: Path) -> dict:
    path = workspace/'data_enrichment.zip'
    if not path.exists():
        return {'zip_present': False, 'used_extracted_directory': True}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = PurePosixPath(info.filename.replace('\\', '/'))
            if name.is_absolute() or '..' in name.parts or (name.parts and ':' in name.parts[0]):
                raise InputError(f'Unsafe ZIP member: {info.filename}')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise InputError(f'ZIP symlink not accepted: {info.filename}')
        # Directory already exists; do not extract over validated evidence.
        import hashlib
        matched = 0
        for name in ['proposal_metadata.csv', 'votes_recovered.csv', 'historical_rules.csv',
                     'proposal_reconciliation_updated.csv', 'choice_reconciliation.csv',
                     'recent/proposal_metadata.csv', 'recent/votes_recovered.csv']:
            member = 'data_enrichment/'+name
            if member not in archive.namelist():
                raise InputError(f'ZIP missing expected source member: {member}')
            with archive.open(member) as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            if digest != sha(source/name):
                raise InputError(f'ZIP/directory content differs: {member}')
            matched += 1
    return {'zip_present': True, 'zip_members_checked_safe': len(archive.infolist()),
            'zip_primary_tables_equal': matched, 'used_extracted_directory': True,
            'extracted_or_overwritten': False}


def verify_unchanged(workspace: Path, before: dict):
    changed = []
    for name, item in before.items():
        path = workspace/name
        if not path.exists() or sha(path) != item['sha256']:
            changed.append(name)
    if changed:
        raise InputError(f'Protected source files changed: {changed}')
    return {'protected_files_verified_unchanged': len(before), 'all_unchanged': True}
