#!/usr/bin/env python3
"""Offline r22 candidate: attributed pre-click refusal; original PAGE click only, no recovery."""
import argparse,fcntl,hashlib,json,os,subprocess,time,uuid
from pathlib import Path
from recovery_tools import check,call
HERE=Path(__file__).resolve().parent
PAGE_SHA='f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab'
KEYS=(3,48,21,431,428,427,504)
IDENTITY_CHECKS=set('document_unchanged time_origin_unchanged exact_url top_level one_inline_script script_unchanged_during_digest page_fingerprint launch_identity'.split())
PREFLIGHT_CHECKS=set('status_present phase_ready server_ready server_no_error server_not_busy server_no_review steps_under_eight page_not_busy page_not_ending page_not_finished delivery_known review_known review_not_awaiting no_awaiting_step no_render_fault frame_loaded reviewed_sha_matches reviewed_generation_matches alarm_nonce_matches alarm_armed alarm_due_in_future key_exists key_enabled'.split())
def bound_result(value,config):
 """A typed, request-bound reply is required; malformed/foreign replies stay unknown."""
 if type(value) is not dict or value.get('schema')!='fx3-operator-preclick-v1':return False
 s=value.get('snapshot'); checks=value.get('checks'); failed=value.get('failed_checks')
 if type(s) is not dict or type(checks) is not dict or type(failed) is not list:return False
 page=s.get('page');alarm=s.get('alarm');reviewed=s.get('reviewed')
 if not all(type(x) is dict for x in (page,alarm,reviewed)):return False
 return (s.get('identity_trusted') is True and set(page)==IDENTITY_CHECKS and
         set(checks)==PREFLIGHT_CHECKS and all(v is True for v in page.values()) and
         s.get('key')==config['key'] and s.get('launch')==config['launch'] and
         s.get('expected_launch')==config['launch'] and s.get('canonical_sha256')==config['page_sha'] and
         s.get('expected_page_sha256')==config['page_sha'] and
         s.get('document_time_origin')==s.get('digest_document_time_origin') and
         type(s.get('document_time_origin')) in (int,float) and
         alarm.get('expected_nonce')==config['nonce'] and
         reviewed=={'sha256':config['sha'],'generation':config['gen']} and
         all(type(v) is bool for v in checks.values()) and checks and
         all(type(k) is str for k in failed) and len(failed)==len(set(failed)) and
         set(failed)=={k for k,v in checks.items() if not v})
def click(session,url,launch,nonce,key,reviewed_sha,reviewed_generation,target,ledger,receipt):
 if key not in KEYS or not target.strip() or len(target)>500 or len(reviewed_sha)!=64 or reviewed_generation<1:raise ValueError('operator explicit inputs')
 binding={'launch_request_id':launch,'nonce':nonce,'attempt_id':'00000000-0000-4000-8000-000000000000','base_step':0,'expected_step':1,'key':key,'PNG_sha256':reviewed_sha,'content_generation':reviewed_generation,'sequence':1}
 tab=check(session,url,launch,nonce,binding)
 ledger=Path(ledger);receipt=Path(receipt)
 if not ledger.parent.is_dir() or not receipt.parent.is_dir():raise ValueError('existing receipt parents')
 with ledger.open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);raw=f.read();state=json.loads(raw) if raw else {'attempts':[],'recoveries':[]}
  if len(state['attempts'])>=10:raise ValueError('10 explicit attempts reached')
  if any(x.get('status')!='click_invoked' for x in state['attempts']):raise ValueError('previous click outcome unknown; End required')
  if any(x.get('status')!='cancelled_unqueued_alarm_only' or x.get('current_screenshot_status')!='delivered_requires_separate_operator_review' for x in state['recoveries']):raise ValueError('recovery outcome or new screenshot unknown; End required')
  script=(HERE/'operator_preflight.js').read_text()
  config={'url':url,'launch':launch,'nonce':nonce,'key':key,'sha':reviewed_sha,'gen':reviewed_generation,'page_sha':PAGE_SHA}
  record={'status':'unknown','session':session,'tab':tab,'target':target,'key':key,'host_start_ns':time.monotonic_ns(),'eval_may_have_started':True,'guest_keys_sent_directly_by_cli':0}
  receipt.open('x').write(json.dumps(record,indent=2)+'\n')
  reservation={'status':'reserved_unknown','reservation_id':str(uuid.uuid4()),'key':key,'host_ns':time.monotonic_ns()}
  state['attempts'].append(reservation)
  f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();os.fsync(f.fileno())
  try:
   value=json.loads(call(session,['eval','--stdin'],source=script+'('+json.dumps(config)+')',timeout=12))
   record['result']=value
   if (bound_result(value,config) and
       value.get('status')=='preflight_not_clicked' and value.get('click_called') is False and
       value.get('decision')=='refuse_before_click' and value.get('failed_checks') and
       value.get('snapshot',{}).get('identity_trusted') is True):
    record['status']='preflight_not_clicked'
   elif (bound_result(value,config) and
         value.get('status')=='click_invoked' and value.get('click_called') is True and
         value.get('decision')=='invoke_original_button_once' and not value['failed_checks'] and value.get('attempt_id')):
    record['status']='click_invoked'
  except BaseException as e:record['error']={'kind':type(e).__name__,'detail':'eval result unavailable; delivery remains unknown'}
  result=record.get('result') if type(record.get('result')) is dict else {}
  reservation.update(status=record['status'],attempt_id=result.get('attempt_id'),step=result.get('step'))
  f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();os.fsync(f.fileno());record['host_end_ns']=time.monotonic_ns();receipt.write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('session','url','launch','nonce','key','reviewed-sha','reviewed-generation','target','ledger','receipt'):
  p.add_argument('--'+k,required=True,type=int if k in ('key','reviewed-generation') else str)
 a=p.parse_args();x=click(a.session,a.url,a.launch,a.nonce,a.key,a.reviewed_sha,a.reviewed_generation,a.target,a.ledger,a.receipt);print(json.dumps(x,indent=2));raise SystemExit(0 if x['status']=='click_invoked' else 2)
