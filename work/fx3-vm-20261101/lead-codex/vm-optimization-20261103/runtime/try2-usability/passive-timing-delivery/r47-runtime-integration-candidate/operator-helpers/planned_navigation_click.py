#!/usr/bin/env python3
"""Explicit planned single-step navigation; historical review is not click-time visual permission."""
import argparse,fcntl,hashlib,json,os,subprocess,time,uuid
from pathlib import Path
from recovery_tools import call,SESSION,UUID
from urllib.parse import urlsplit
from planned_prerequisite import PLAN_SHA,plan,prerequisite
HERE=Path(__file__).resolve().parent
PAGE_SHA='f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf'
KEYS=(3,48,21,431,428,427,504)
IDENTITY_CHECKS=set('document_unchanged time_origin_unchanged exact_url top_level one_inline_script script_unchanged_during_digest page_fingerprint launch_identity prerequisite_document'.split())
PREFLIGHT_CHECKS=set('status_present phase_ready server_ready server_no_error server_not_busy server_no_review steps_under_eight page_not_busy page_not_ending page_not_finished delivery_known review_known review_not_awaiting no_awaiting_step no_render_fault frame_loaded plan_matches plan_step_matches server_step_matches previous_confirm_matches alarm_document_matches alarm_nonce_matches alarm_armed alarm_due_in_future key_exists key_enabled'.split())
def bound_result(value,config):
 """A typed, request-bound reply is required; malformed/foreign replies stay unknown."""
 if type(value) is not dict or value.get('schema')!='fx3-planned-navigation-v1':return False
 s=value.get('snapshot'); checks=value.get('checks'); failed=value.get('failed_checks')
 if type(s) is not dict or type(checks) is not dict or type(failed) is not list:return False
 page=s.get('page');alarm=s.get('alarm')
 if not all(type(x) is dict for x in (page,alarm)):return False
 return (s.get('identity_trusted') is True and set(page)==IDENTITY_CHECKS and
         set(checks)==PREFLIGHT_CHECKS and all(v is True for v in page.values()) and
         s.get('key')==config['key'] and s.get('launch')==config['launch'] and
         s.get('expected_launch')==config['launch'] and s.get('canonical_sha256')==config['page_sha'] and
         s.get('expected_page_sha256')==config['page_sha'] and
         s.get('document_time_origin')==s.get('digest_document_time_origin') and
         type(s.get('document_time_origin')) in (int,float) and
         alarm.get('expected_nonce')==config['nonce'] and
         value.get('scripted_navigation') is True and value.get('visual_review_at_click') is False and
         value.get('plan_sha')==config['plan_sha'] and value.get('plan_step')==config['step'] and
         s.get('plan_sha')==config['plan_sha'] and s.get('plan_step')==config['step'] and
         s.get('prerequisite_sha256')==config['prerequisite']['prerequisite_sha256'] and
         s.get('previous_confirm')==config['prerequisite']['previous_confirm'] and
         all(type(v) is bool for v in checks.values()) and checks and
         all(type(k) is str for k in failed) and len(failed)==len(set(failed)) and
         set(failed)=={k for k,v in checks.items() if not v})
def click(session,url,launch,nonce,plan_sha,step,prerequisite_path,ledger,receipt):
 nav=plan(plan_sha)
 if type(step) is not int or not 1<=step<=8:raise ValueError('plan_step_out_of_range')
 key=nav['steps'][step-1]['key'];target=nav['steps'][step-1]['target']
 previous=prerequisite(prerequisite_path,step,launch)
 u=urlsplit(url)
 if (not SESSION.fullmatch(session) or not UUID.fullmatch(launch) or not UUID.fullmatch(nonce) or
     u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.path!='/' or u.query or u.fragment or
     url!=f'http://127.0.0.1:{u.port}/'):raise ValueError('owned_tab_URL_launch_nonce')
 tabs=json.loads(call(session,['tab','--json']))['data']['tabs']
 if len(tabs)!=1 or tabs[0]['url']!=url:raise ValueError('one_owned_tab_exact_URL')
 tab=tabs[0].get('id')
 ledger=Path(ledger);receipt=Path(receipt)
 if not ledger.parent.is_dir() or not receipt.parent.is_dir():raise ValueError('existing receipt parents')
 with ledger.open('a+') as f:
  fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);raw=f.read();state=json.loads(raw) if raw else {'attempts':[],'recoveries':[]}
  if len(state['attempts'])>=10:raise ValueError('10 explicit attempts reached')
  if any(x.get('status')!='click_invoked' for x in state['attempts']):raise ValueError('previous click outcome unknown; End required')
  if any(x.get('status')!='cancelled_unqueued_alarm_only' or x.get('current_screenshot_status')!='delivered_requires_separate_operator_review' for x in state['recoveries']):raise ValueError('recovery outcome or new screenshot unknown; End required')
  script=(HERE/'planned_navigation_click.js').read_text()
  config={'url':url,'launch':launch,'nonce':nonce,'key':key,'plan_sha':plan_sha,'step':step,'prerequisite':previous,'page_sha':PAGE_SHA}
  record={'status':'unknown','scripted_navigation':True,'visual_review_at_click':False,'plan_sha':plan_sha,'plan_step':step,'nonce':nonce,'launch':launch,'document_time_origin':previous['document_time_origin'],'click_time_frame':None,'previous_confirm':previous['previous_confirm'],'session':session,'tab':tab,'target':target,'key':key,'host_start_ns':time.monotonic_ns(),'eval_may_have_started':True,'guest_keys_sent_directly_by_cli':0}
  receipt.open('x').write(json.dumps(record,indent=2)+'\n')
  reservation={'status':'reserved_unknown','reservation_id':str(uuid.uuid4()),'key':key,'plan_sha':plan_sha,'plan_step':step,'host_ns':time.monotonic_ns()}
  state['attempts'].append(reservation)
  f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();os.fsync(f.fileno())
  try:
   value=json.loads(call(session,['eval','--stdin'],source=script+'('+json.dumps(config)+')',timeout=12))
   record['result']=value
   if bound_result(value,config):record['click_time_frame']=value['snapshot']['click_time_frame']
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
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('session','url','launch','nonce','plan-sha','step','prerequisite-path','ledger','receipt'):
  p.add_argument('--'+k,required=True,type=int if k=='step' else str)
 a=p.parse_args()
 try:r=click(a.session,a.url,a.launch,a.nonce,a.plan_sha,a.step,a.prerequisite_path,a.ledger,a.receipt)
 except (ValueError,KeyError,TypeError,FileNotFoundError) as e:
  print(json.dumps({'status':'host_preflight_refused','reason':str(e),'scripted_navigation':True,'visual_review_at_click':False}));raise SystemExit(2)
 print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='click_invoked' else 2)
