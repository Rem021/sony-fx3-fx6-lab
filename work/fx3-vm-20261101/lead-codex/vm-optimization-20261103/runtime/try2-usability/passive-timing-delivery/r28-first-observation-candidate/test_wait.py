"""Targeted host/browser checks, not a model-review rehearsal; all native/image effects MOCK."""
from fixture_driver import *
RESULT={'scope':__doc__,'cases':{}}
def snapshot_meta(v):return v['sampling_browser_interval']['first_observation_wait']
def stop():
 try:js('if(!ending&&!finished)endButton.click();true')
 except Exception:pass
try:
 run=setup('target-positive');start=time.monotonic();value=operate(run,'click','1','MOCK predetermined menu target');wall=time.monotonic()-start
 m=snapshot_meta(value);assert value['status']=='qualified_unpinned_postkey_observation' and m['applied'] and m['completed_ms']>=m['arm_ms']+5000 and value['before']['displayed_frame']['PNG_sha256']==hashlib.sha256((ROOT.parent/'r26-tool-return-preparation/samples/fixed.png').read_bytes()).hexdigest()
 second=operate(run,'observe','MOCK host oracle: same accepted step, explicit second observation');assert snapshot_meta(second)['first_observation'] is False and second['before']['performance_ms']-value['after']['performance_ms']<2000
 metrics=api('fixture/metrics');assert metrics['counts']['keyPOST']==1 and metrics['counts']['pinPOST']==metrics['counts']['confirmPOST']==0
 RESULT['cases']['first5000_and_later_observe']={'passed':True,'wall_seconds':wall,'first_wait':m,'browser_interval':value['sampling_browser_interval'],'second_browser_interval':second['sampling_browser_interval'],'counts':metrics['counts']};stop()
 # Already late path: real browser clock is allowed to advance; no synthetic clock/retime.
 run=setup('target-already-late');nonce=uid();js('window.__fx3InteractionDeadlineV1?.status?.()') if False else None
 js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')');js('keys.find(x=>Number(x.dataset.key)===427).click();true');wait(lambda:js('currentKeyAttempt?.outcome==="accepted"'))
 js('(async()=>{const target=window.__fx3InteractionDeadlineV1.status().current.armed_ms+5250;while(performance.now()<target)await new Promise(r=>setTimeout(r,25));return true})()')
 start=time.monotonic();v=direct_capture(run,'late-first',1);elapsed=time.monotonic()-start;m=snapshot_meta(v);assert v['status']=='qualified_unpinned_postkey_observation' and not m['applied'] and elapsed<2
 RESULT['cases']['already_past5000_no_extra5s']={'passed':True,'capture_seconds':elapsed,'wait':m};stop()
 # Normal unqueued recovery is a separate unchanged helper path and must return before5s.
 run=setup('target-unqueued')
 js("let once=true;const originalFetch=window.fetch.bind(window);window.fetch=async(...args)=>{if(once&&busy&&currentKeyAttempt?.outcome==='preflight'&&String(args[0]).includes('/api/status')){once=false;await originalFetch('/fixture/preflight-change');await new Promise(r=>setTimeout(r,550));}return originalFetch(...args)};true")
 start=time.monotonic();v=operate(run,'click','1','MOCK legal unqueued preflight rejection');elapsed=time.monotonic()-start
 assert v['status']=='qualified_recovery_observation' and elapsed<5 and api('fixture/metrics')['counts']['keyPOST']==0
 RESULT['cases']['unqueued_recovery_no_first_wait']={'passed':True,'seconds':elapsed,'status':v['status'],'counts':api('fixture/metrics')['counts']};stop()
 for name,code in [('End','endButton.click()'),('launch',"fetch('/fixture/change-launch')"),('document','location.reload()'),('nonce','currentKeyAttempt.alarm_nonce=crypto.randomUUID()'),('attempt','currentKeyAttempt.attempt_id=crypto.randomUUID()'),('unknown','deliveryUnknown=true')]:
  run=setup('target-'+name)
  js('setTimeout(()=>{'+code+'},1500);true')
  operate(run,'click','1','MOCK identity injection during wait',ok=False)
  assert (run/'POSTKEY-TERMINAL.json').exists();a=json.loads((run/'current-attempt.json').read_text());folder=Path(a['path']);rec=json.loads((folder/'observation-1/observation-result.json').read_text())
  assert rec['status']=='unknown' and not (folder/'observation-1/observation.png').exists()
  counts=api('fixture/metrics')['counts'];assert counts['keyPOST']==1 and counts['pinPOST']==counts['confirmPOST']==0
  RESULT['cases']['during_wait_'+name]={'passed':True,'status':rec['status'],'reason':rec.get('reason'),'counts':counts};stop()
 # At19.2s the arm+5 gate is already passed, but native-review readiness still waits.
 # Natural original20s expiry must terminate that shared waiting/identity path.
 run=setup('target-expired','no-native');nonce=uid();js('window.__fx3InteractionDeadlineV1.arm('+json.dumps(nonce)+')');js('keys.find(x=>Number(x.dataset.key)===427).click();true');wait(lambda:js('currentKeyAttempt?.outcome==="accepted"'))
 js('(async()=>{const target=window.__fx3InteractionDeadlineV1.status().current.armed_ms+19200;while(performance.now()<target)await new Promise(r=>setTimeout(r,25));return true})()')
 v=direct_capture(run,'expired-first',1);assert v['status']=='unknown';alarm=js('window.__fx3InteractionDeadlineV1.status()');assert alarm['current']['state']=='expired' and alarm['deadline_ms']==20000
 RESULT['cases']['natural20s_expiry_while_waiting_for_native_phase']={'passed':True,'alarm':alarm,'status':v['status'],'no_native_MOCK':True};stop()
 RESULT['passed']=True
finally:
 save(ROOT/'evidence/WAIT-TEST-RESULT.json',RESULT)
print(json.dumps({'passed':RESULT.get('passed'),'cases':len(RESULT['cases'])}))
