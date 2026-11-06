"""Exercise production recovery_tools cancellation integration with controlled transport faults."""
import importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'operator-helpers/recovery_tools.py'
spec=importlib.util.spec_from_file_location('recovery_tools_fault',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
AID='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';NONCE='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';LAUNCH='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
B={'attempt_id':AID,'launch_request_id':LAUNCH,'nonce':NONCE,'base_step':0,'expected_step':1,'key':427,'PNG_sha256':'1'*64,'content_generation':1,'sequence':1,'document_time_origin':1}
CASES={}
def prep(root):
 ledger=root/'ledger.json';ledger.write_text(json.dumps({'attempts':[{'status':'click_invoked','attempt_id':AID,'step':1}],'recoveries':[]})+'\n')
 review=root/'review.json';review.write_text(json.dumps({'status':'qualified_review_screenshot','binding':B,'nonce':NONCE,'launch_id':LAUNCH,'PNG_sha256':'2'*64,'content_generation':2,'screenshot_sha256':'3'*64})+'\n')
 return ledger,review
def run(label,eval_result=None,eval_error=None,screenshot_error=False):
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);ledger,review=prep(root);seen={}
  m.check=lambda *a: 'fixture-tab'
  def eval_fake(*a):
   seen['eval']=True
   if eval_error:raise RuntimeError(eval_error)
   return eval_result
  def call_fake(*a,**kw):
   if screenshot_error:raise RuntimeError('screenshot failed after real cancel')
   Path(a[1][1]).write_bytes(b'PNG')
  m.evaluate=eval_fake;m.call=call_fake
  result=m.cancel('fx3-deadline-test','http://127.0.0.1:1234/',LAUNCH,NONCE,B,review,'fixture explicit',root/'out',ledger)
  state=json.loads(ledger.read_text());row=state['recoveries'][0]
  assert seen['eval'] and len(state['recoveries'])==1 and row['attempt_id']==AID
  # A second cancellation for the same guest step never invokes the browser.
  seen.clear();second=m.cancel('fx3-deadline-test','http://127.0.0.1:1234/',LAUNCH,NONCE,B,review,'fixture explicit',root/'out2',ledger)
  assert second['status']=='refused' and not seen
  CASES[label]={'status':result['status'],'alarm_cleanup_status':result.get('alarm_cleanup_status'),'ledger_status':row['status'],'second_status':second['status']}
  return result,row
ok={'status':'cancelled_unqueued_alarm_only','alarm_cancel_receipt':{'current':{'state':'cancelled','nonce':NONCE}}}
x,row=run('cancel_success_screenshot_failure_budget_spent',ok,screenshot_error=True)
assert x['status']=='cancelled_screenshot_unknown' and x['alarm_cleanup_status']=='confirmed_cancelled' and row['status']=='cancelled_screenshot_unknown'
x,row=run('eval_side_effect_reply_lost_budget_spent',eval_error='reply lost after side effect')
assert x['status']=='unknown' and row['status']=='unknown'
# The reservation must be persisted before the potentially mutating browser eval.
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);ledger,review=prep(root);m.check=lambda *a:'fixture-tab'
 def before(*a):
  rows=json.loads(ledger.read_text())['recoveries'];assert len(rows)==1 and rows[0]['status']=='reserved_unknown'
  raise RuntimeError('pre-mutation transport error')
 m.evaluate=before
 x=m.cancel('fx3-deadline-test','http://127.0.0.1:1234/',LAUNCH,NONCE,B,review,'fixture',root/'out',ledger)
 assert x['status']=='unknown';CASES['reservation_persisted_before_eval']={'status':x['status'],'ledger':json.loads(ledger.read_text())['recoveries'][0]['status']}
(ROOT/'evidence/recovery-faults.json').write_text(json.dumps({'passed':True,'cases':CASES},indent=2)+'\n');print('PASS',len(CASES))
# Supervised click budget blocks ten prior attempts or unresolved recovery without browser eval.
import sys;sys.path.insert(0,str(ROOT/'operator-helpers'))
spec=importlib.util.spec_from_file_location('operator_click_fault',ROOT/'operator-helpers/operator_click.py');k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
k.check=lambda *a:'fixture-tab';k.call=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('unexpected browser eval'))
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);ledger=root/'ledger.json'
 ledger.write_text(json.dumps({'attempts':[{'status':'click_invoked'}]*10,'recoveries':[]})+'\n')
 try:k.click('fx3-deadline-test','http://127.0.0.1:1234/',LAUNCH,NONCE,427,'1'*64,1,'fixture',ledger,root/'receipt')
 except ValueError as e:assert '10 explicit attempts' in str(e)
 else:raise AssertionError('attempt budget bypass')
 ledger.write_text(json.dumps({'attempts':[],'recoveries':[{'status':'reserved_unknown'}]})+'\n')
 try:k.click('fx3-deadline-test','http://127.0.0.1:1234/',LAUNCH,NONCE,427,'1'*64,1,'fixture',ledger,root/'receipt')
 except ValueError as e:assert 'recovery outcome' in str(e)
 else:raise AssertionError('pending recovery bypass')
 CASES['click_budget_ten_and_pending_recovery']={'attempt_budget_refused':True,'unknown_recovery_refused':True,'browser_eval_calls':0}
 (ROOT/'evidence/recovery-faults.json').write_text(json.dumps({'passed':True,'cases':CASES},indent=2)+'\n')
 print('PASS click budget 2')
