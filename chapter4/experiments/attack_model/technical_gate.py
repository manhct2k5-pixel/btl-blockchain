"""Must pass before the prospective attack engine is enabled."""
import io,json,hashlib,sys,unittest
from pathlib import Path
from qv_numeric_v2 import ROOT,WS,PATCH_ID
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def protect():
    m=json.loads((ROOT/'PROTECTED_INPUTS.json').read_text(encoding='utf-8'))
    for n,h in m.items():
        if sha(WS/n)!=h:raise RuntimeError('Prior artifact changed: '+n)
    return len(m)
def main():
    stream=io.StringIO()
    tests=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_numeric_patch.py',top_level_dir=str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    (ROOT/'TECHNICAL_GATE_LOG.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():raise AssertionError(stream.getvalue())
    gate={'status':'PASSED','tests':result.testsRun,'prior_files_unchanged':protect(),
        'numeric_patch':PATCH_ID,'same_process_repeat_checks':True,
        'old_qv_not_modified':True,'missing_values_not_zero':True,
        'event_order':'PRE_SNAPSHOT_ALLOCATION; FUNDING; STRICTLY_LATER_SIMULTANEOUS_RESPONSE; FINAL_TALLY; SETTLEMENT',
        'patch_sha256':sha(ROOT/'qv_numeric_v2.py')}
    (ROOT/'TECHNICAL_GATE.json').write_text(json.dumps(gate,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(gate,indent=2))
if __name__=='__main__':main()
