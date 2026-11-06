"""Exactly two targeted pre-timer checks; never starts browser/server/arm or guest."""
import ast,importlib.util,sys
from common import *
from dependency_gate import verify
from fixture_contract import complete_review
verify('DEPENDENCY-BEFORE.json')
assert not (HERE/'fixture.json').exists() and not (HERE/'ledger.json').exists()
for p in HERE.glob('*.py'):ast.parse(p.read_text())
spec=importlib.util.spec_from_file_location('original_r21_for_state_check',FROZEN/'trial_web_v22_navigation_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=m.TrialState('offline_state_check_only',600,8);s.update(phase='ready',ready=True,steps=1)
png=Path(CFG['historical_root'])/'trial-final.png';s.publish(png.read_bytes(),{'sequence':213,'PNG_sha256':sha(png),'width':640,'height':480,'all_zero_pixels':False})
snapshot=complete_review(s)
assert snapshot['review_required'] and snapshot['visual_state'] in ('visual_changed','no_change_observed') and not s.pending
assert 'complete_review(state)' in (HERE/'fixture_server.py').read_text()
write('PREFLIGHT-FIXTURE-STATE.json',{'passed':True,'uses_same_complete_review_function_as_actual_fixture':True,'snapshot':snapshot,'calls_to_server_browser_arm_guest':0,**stamp()})
# Injection calls run_action, which is now the actual imported and CLI guard.
# All writes/cleanup callbacks in this child are test-local stand-ins; no browser command can execute.
source='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import operate
trace=[]
def injected(action):
 trace.append({'action_called':action});raise RuntimeError('intentional pre-timer exception; no browser/arm')
def fake_cleanup():
 trace.append({'End_cleanup_callback_called':True,'browser_calls':0,'arm_calls':0,'key_calls':0,'confirm_calls':0});return {'returncode':0,'mock_only':True}
def fake_write(name,value):trace.append({'write_called':name,'value':value})
operate._run_action=injected;operate._cleanup_on_failure=fake_cleanup;operate.write=fake_write
try:operate.run_action('preflight_exception')
finally:Path(sys.argv[2]).write_text(json.dumps(trace,indent=2)+'\\n')
'''
tracepath=HERE/'PREFLIGHT-EXCEPTION-TRACE.json'
start=stamp();p=subprocess.run(['python3','-c',source,str(HERE),str(tracepath)],env=ENV,text=True,capture_output=True)
trace=json.loads(tracepath.read_text());assert p.returncode!=0 and 'intentional pre-timer exception' in p.stderr
assert len([x for x in trace if x.get('End_cleanup_callback_called')])==1
assert [x['write_called'] for x in trace if 'write_called' in x]==['FAILURE.json','FAILURE-CLEANUP-DISPATCH.json']
assert not (HERE/'FAILURE.json').exists() and not (HERE/'FAILURE-CLEANUP-DISPATCH.json').exists()
assert not (HERE/'fixture.json').exists() and not (HERE/'ledger.json').exists()
write('PREFLIGHT-EXCEPTION-PROCESS.json',{'start':start,'end':stamp(),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'expected_nonzero':True,'actual_run_action_guard_exercised':True,'cleanup_callback_replaced_with_no_browser_test_double':True})
write('PREFLIGHT-RESULT.json',{'passed':True,'checks':{'actual_fixture_final_review_state':'passed','actual_run_action_exception_cleanup_callback_and_nonzero':'passed'},'scope':'targeted only; no browser/server/arm; not semantic operator review and not an extra timed rehearsal',**stamp()})
print(json.dumps({'passed':True,'checks':2,'no_browser_server_arm':True}))
