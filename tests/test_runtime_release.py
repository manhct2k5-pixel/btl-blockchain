"""Verification fixtures only: reexecute existing demos, no new experiments."""
import json,sys,csv
from pathlib import Path
from fractions import Fraction as F
import pytest
PROJECT=Path(__file__).resolve().parents[1]
BASE=PROJECT / "research"
sys.path.insert(0,str(BASE/'chapter4/dao_risk_simulator'))
import service as s

def test_imports_resolve_inside_extracted_release():
    import information_v2,attack_core,behavior,engine,main_generator
    assert s.WS==BASE
    for mod in (s,information_v2,attack_core,behavior,engine,main_generator):assert Path(mod.__file__).resolve().is_relative_to(BASE)

def test_file_manifest_matches_bytes():
    import hashlib
    m=json.loads((PROJECT/'RELEASE_FILE_MANIFEST.json').read_text(encoding='utf-8'))
    for name,h in m.items():assert hashlib.sha256((PROJECT/name).read_bytes()).hexdigest()==h,name

def test_runtime_binding_slice_retains_scope():
    df=s.historical_data();assert len(df)==1023 and sum(df['qv_status']=='ASSESSED')==943
    wallets=set();count=0
    for rel in ('data_enrichment/votes_recovered.csv','data_enrichment/recent/votes_recovered.csv'):
        with (BASE/rel).open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):count+=1;wallets.add(r['voter_normalized'])
    assert count==63662 and len(wallets)==6004

def test_saved_tw_demo_reexecutes_same_outcome():
    q=s.import_scenario((BASE/'chapter4/dao_risk_simulator/demos/demo1_tw/scenario.json').read_text(encoding='utf-8'))
    expected=json.loads((BASE/'chapter4/dao_risk_simulator/demos/demo1_tw/actual.json').read_text(encoding='utf-8'))['results'][0]
    actual=s.run_scenario(q)['results'][0]
    assert actual['with_attack']==expected['with_attack'] and actual['policy_success']==expected['policy_success']

def test_three_mechanisms_and_type_b_saved_grid():
    q=s.import_scenario((BASE/'chapter4/dao_risk_simulator/demos/demo2_qv_split/scenario.json').read_text(encoding='utf-8'))
    b=s.run_scenario(q,['TW','QV','CAP']);assert len(b['results'])==3
    grid=s.run_sensitivity(q,'alias_count',[1,4]);rs=[r for r in grid['results'] if r['mechanism']=='QV']
    assert rs[0]['with_attack']['options']!=rs[1]['with_attack']['options']
    assert rs[0]['policy_success'] is False and rs[1]['policy_success'] is True

def test_saved_ve_demo_and_roundtrip():
    q=s.import_scenario((BASE/'chapter4/dao_risk_simulator/demos/demo4_ve/scenario.json').read_text(encoding='utf-8'))
    a=s.run_scenario(q,['VE']);loaded=s.import_scenario(s.export_bundle(a)['scenario.json'].decode())
    assert s.run_scenario(loaded,['VE'])['results']==a['results']
    with pytest.raises(ValueError):s.run_scenario(q,['VE','TW'])

def test_not_ready_and_infeasible_remain_distinct():
    q=s.build_scenario('SPLIT',replicate=9)
    assert s.run_scenario(q)['results'][0]['state']=='NOT_READY'
    q['information_condition']='UNINFORMED_VOTER'
    r=s.run_scenario(q)['results'][0];assert r['state']=='INFEASIBLE' and r['success'] is None

def test_type_a_keeps_saved_bootstrap_uncertainty():
    assert s.crossover_info()['valid_root_fraction']==.7565
    assert s.type_a(1)[1]['rate']==pytest.approx(19/257)
