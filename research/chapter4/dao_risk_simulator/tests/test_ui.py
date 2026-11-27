import sys,json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import service as s
APP=Path(__file__).resolve().parents[1]/'app.py'
def start():return AppTest.from_file(str(APP),default_timeout=40).run()
def nav(at,i):return at.radio(key='page').set_value(at.radio(key='page').options[i]).run()
def good(at):assert not at.exception and not at.error
def configured():
    at=nav(start(),2);at.checkbox[0].check().run();good(at);return at
def button(at,text):return next(x for x in at.button if x.label==text)

@pytest.mark.parametrize('i',range(6))
def test_pages_import_and_render_without_errors(i):good(nav(start(),i))

def test_run_single_and_parameter_invalidation():
    at=configured();at.button(key='run_single').click().run();good(at)
    b=at.session_state['last_bundle'];assert b['results'][0]['mechanism']=='TW'
    h=b['input_hash']
    at.text_input(key='cap_SPLIT').set_value('50000').run();good(at)
    assert at.session_state['current_hash']!=h
    assert 'last_bundle' not in at.session_state
    at.button(key='run_single').click().run();good(at)
    assert at.session_state['last_bundle']['input_hash']!=h

def test_grant_not_default_and_uninformed_not_failed():
    at=nav(start(),2);at.button(key='run_single').click().run();good(at)
    assert at.session_state['last_bundle']['results'][0]['state']=='NOT_READY'
    selector=next(x for x in at.selectbox if x.label=='Điều kiện thông tin')
    selector.set_value('UNINFORMED_VOTER').run();at.button(key='run_single').click().run();good(at)
    r=at.session_state['last_bundle']['results'][0]
    assert r['state']=='INFEASIBLE' and r['success'] is None

def test_invalid_input_error_has_no_fake_result():
    at=configured();at.text_input(key='cap_SPLIT').set_value('-1').run()
    assert at.error and not at.exception
    assert 'last_bundle' not in at.session_state

def test_ui_calls_three_compatible_models():
    at=nav(configured(),3);button(at,'Chạy đối chứng').click().run();good(at)
    rs=at.session_state['comparison_bundle']['results']
    assert [r['mechanism'] for r in rs]==['TW','QV','CAP']
    assert len({r['world_id'] for r in rs})==1

def test_explicit_small_batch_progress_and_counts():
    at=nav(configured(),3)
    mode=next(x for x in at.radio if x.label=='Phạm vi thực thi');mode.set_value(mode.options[1]).run()
    next(x for x in at.number_input if x.label=='Số world tổng hợp').set_value(2).run()
    button(at,'Chạy đối chứng').click().run();good(at)
    b=at.session_state['comparison_bundle']
    assert len(b['results'])==6 and all(r['worlds']==2 for r in b['summary'])

def test_ve_stays_separate_and_lock_controls_used():
    at=nav(start(),2);next(x for x in at.selectbox if x.label=='Mẫu kịch bản').set_value('VE_MOBILIZE').run();good(at)
    assert not any(x.key=='cap_VE_MOBILIZE' for x in at.text_input)
    at.button(key='run_single').click().run();good(at)
    assert at.session_state['last_bundle']['results'][0]['mechanism']=='VE'
    at=nav(at,3);button(at,'Chạy đối chứng').click().run();good(at)
    assert [r['mechanism'] for r in at.session_state['comparison_bundle']['results']]==['VE']

def test_type_a_and_actual_type_b_grid():
    at=nav(configured(),4);good(at)
    method=next(x for x in at.radio if x.label=='Phương pháp');method.set_value(method.options[1]).run()
    button(at,'Chạy lưới Type B').click().run();good(at)
    b=at.session_state['sensitivity_bundle']
    assert len(b['results'])==12 and b['evidence']=='TYPE_B_NEW_MODEL_EXECUTION'

def test_import_json_and_execute_without_default_overwrite():
    q=s.build_scenario('SPLIT',replicate=9,overrides={'grant_enabled':True,'budget':'321'})
    at=nav(start(),5);at.text_area[0].set_value(json.dumps(q)).run()
    button(at,'Kiểm tra & nạp cấu hình').click().run();good(at)
    assert at.session_state['current_request']==q
    button(at,'Thực thi cấu hình đang nạp').click().run();good(at)
    assert at.session_state['last_bundle']['request']==q
    assert len(at.get('download_button'))>=6

def test_history_filters_and_no_attack_label():
    at=nav(start(),1);good(at)
    assert any('1.023' in str(m.value) or '1023' in str(m.value) for m in at.metric)
    assert len(at.dataframe)>0

def test_model_version_change_discards_old_ui_result(monkeypatch):
    at=configured();at.button(key='run_single').click().run();good(at)
    old=at.session_state['last_bundle']['model_fingerprint']
    original=s.module_manifest
    def changed():
        m=original();m['model_fingerprint']='new-version';return m
    monkeypatch.setattr(s,'module_manifest',changed)
    at.run();good(at)
    assert old!='new-version' and 'last_bundle' not in at.session_state
