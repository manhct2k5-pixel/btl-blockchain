"""Regression cases for malformed imports and explicit execution intent."""
import json
import sys
from copy import deepcopy
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parents[1]
RESEARCH = PROJECT / 'research' if (PROJECT / 'research').is_dir() else PROJECT
sys.path.insert(0, str(RESEARCH / 'chapter4/dao_risk_simulator'))
import service

@pytest.fixture
def request_data():
    return service.build_scenario()

@pytest.mark.parametrize('field,value', [
    ('voters', []), ('voters', None), ('principals', []),
    ('voters', {'wallet': []}), ('principals', {'attacker': None}),
    ('attack', None), ('proposal', []),
])
def test_malformed_nested_import_is_a_validation_error(request_data, field, value):
    request_data['config'][field] = value
    with pytest.raises(ValueError):
        service.import_scenario(json.dumps(request_data))

def test_empty_mechanism_selection_does_not_execute_default(request_data):
    with pytest.raises(ValueError):
        service.run_scenario(request_data, [])

def test_deep_json_is_a_validation_error():
    with pytest.raises(ValueError):
        service.import_scenario('[' * 1500 + '0' + ']' * 1500)

def test_import_limit_counts_utf8_bytes(request_data):
    request_data['source']['note'] = 'ệ' * 340000
    raw = json.dumps(request_data, ensure_ascii=False)
    assert len(raw) < 1000000 < len(raw.encode('utf-8'))
    with pytest.raises(ValueError, match='1 MB'):
        service.import_scenario(raw)

def test_verification_rejects_errors_and_skips(monkeypatch):
    current = service.module_manifest()['model_fingerprint']
    for issue in ('errors', 'skips'):
        certificate = dict(model_fingerprint=current, failures=0, errors=0, skips=0,
                           total_tests=10, zero_collection=False)
        certificate[issue] = 1
        monkeypatch.setattr(service, 'read', lambda path, data=deepcopy(certificate): data)
        assert service.verification_status()['verified'] is False

def test_complete_matching_certificate_is_verified(monkeypatch):
    certificate = dict(model_fingerprint=service.module_manifest()['model_fingerprint'],
                       failures=0, errors=0, skips=0, total_tests=10, zero_collection=False)
    monkeypatch.setattr(service, 'read', lambda path: certificate)
    assert service.verification_status()['verified'] is True

@pytest.mark.parametrize('certificate', [[], None, {'failures': 0}])
def test_malformed_verification_is_not_a_crash(monkeypatch, certificate):
    monkeypatch.setattr(service, 'read', lambda path: certificate)
    assert service.verification_status()['verified'] is False

def test_unreadable_verification_is_not_a_crash(monkeypatch):
    def broken(path):
        raise ValueError('bad JSON')
    monkeypatch.setattr(service, 'read', broken)
    assert service.verification_status()['verified'] is False

def test_import_error_is_friendly_and_can_recover(request_data):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(PROJECT / 'app.py'), default_timeout=30).run()
    at.radio(key='page').set_value('Tái lập & xuất').run()
    malformed = deepcopy(request_data)
    malformed['config']['voters'] = []
    at.text_area[0].set_value(json.dumps(malformed)).run()
    next(b for b in at.button if b.label == 'Kiểm tra & nạp cấu hình').click().run()
    assert not at.exception and at.error
    assert 'voters' in str(at.error[0].value)
    at.text_area[0].set_value(json.dumps(request_data)).run()
    next(b for b in at.button if b.label == 'Kiểm tra & nạp cấu hình').click().run()
    assert not at.exception and not at.error
    assert at.session_state['current_request'] == request_data
