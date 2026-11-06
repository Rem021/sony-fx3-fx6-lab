#!/usr/bin/env python3
"""Explicit operator-only FX3 recovery review or alarm cleanup; never a guest key."""
import argparse,fcntl,hashlib,json,re,subprocess,time
from pathlib import Path
from urllib.parse import urlsplit
HERE=Path(__file__).resolve().parent
UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
SESSION=re.compile(r'fx3-deadline-[A-Za-z0-9_-]+')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(session,args,source=None,timeout=15):
 p=subprocess.run(['agent-browser','--session',session,*args],input=source,text=True,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(f'agent-browser {args[0]} failed: {p.stdout} {p.stderr}')
 return p.stdout.strip()
def check(session,url,launch,nonce,binding):
 u=urlsplit(url)
 if not SESSION.fullmatch(session) or u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or u.path!='/' or u.query or u.fragment or url!=f'http://127.0.0.1:{u.port}/':raise ValueError('owned single tab exact loopback URL')
 if not UUID.fullmatch(launch) or not UUID.fullmatch(nonce):raise ValueError('launch/nonce')
 if (binding.get('launch_request_id')!=launch or binding.get('nonce')!=nonce or
     not UUID.fullmatch(binding.get('attempt_id','')) or type(binding.get('base_step')) is not int or
     not 0<=binding['base_step']<=4096 or binding.get('expected_step')!=binding['base_step']+1 or
     binding.get('key') not in (3,48,21,431,428,427,504) or
     not re.fullmatch(r'[0-9a-f]{64}',binding.get('PNG_sha256','')) or
     type(binding.get('content_generation')) is not int or binding['content_generation']<=0 or
     type(binding.get('sequence')) is not int or binding['sequence']<=0):raise ValueError('attempt binding')
 tabs=json.loads(call(session,['tab','--json']))['data']['tabs']
 if len(tabs)!=1 or tabs[0]['url']!=url:raise ValueError('one owned tab at exact URL')
 return tabs[0].get('id')
def evaluate(session,name,config):
 source=(HERE/name).read_text()+'('+json.dumps(config,ensure_ascii=False)+')'
 return json.loads(call(session,['eval','--stdin'],source,timeout=15))
def capture(session,url,launch,nonce,binding,out):
 tab=check(session,url,launch,nonce,binding);out=Path(out);out.mkdir() # exclusive
 c={'url':url,'launch_id':launch,'nonce':nonce,'binding':binding}
 receipt={'status':'unknown','scope':'read_only_unqueued_review','session':session,'tab':tab,'binding':binding,'host_start_ns':time.monotonic_ns(),'guest_keys_sent':0,'confirm_calls':0,'alarm_mutations':0}
 try:
  first=evaluate(session,'recovery_readonly.js',c);receipt['before']=first
  if not first.get('qualified'):receipt.update(status='refused',reason=first.get('reason'));return receipt
  image=out/'review-page.png';call(session,['screenshot',str(image)],timeout=12)
  receipt['screenshot_sha256']=sha(image);receipt['screenshot_path']=str(image)
  second=evaluate(session,'recovery_readonly.js',c);receipt['after']=second
  fields=('attempt_id','nonce','launch_id','document_time_origin','alarm_due_ms','PNG_sha256','content_generation')
  if not second.get('qualified') or any(first.get(k)!=second.get(k) for k in fields):receipt.update(status='refused',reason='post_screenshot_identity_changed');return receipt
  receipt.update(status='qualified_review_screenshot',attempt_id=first['attempt_id'],nonce=nonce,launch_id=launch,PNG_sha256=first['PNG_sha256'],content_generation=first['content_generation'],sequence=first['sequence'],server_atomic_permission=False)
  return receipt
 except BaseException as e:receipt.update(status='unknown',error=repr(e));return receipt
 finally:
  receipt['host_end_ns']=time.monotonic_ns();(out/'review-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
def _cancel_unbudgeted(session,url,launch,nonce,binding,review,target,out):
 tab=check(session,url,launch,nonce,binding);out=Path(out);out.mkdir()
 receipt={'status':'unknown','scope':'explicit_unqueued_alarm_cleanup_only','session':session,'tab':tab,'binding':binding,'review':str(review),'target':target,'host_start_ns':time.monotonic_ns(),'guest_keys_sent':0,'confirm_calls':0,'new_alarm_calls':0}
 try:
  reviewed=json.loads(Path(review).read_text())
  if not target.strip() or len(target)>500 or reviewed.get('status')!='qualified_review_screenshot' or reviewed.get('binding')!=binding or reviewed.get('nonce')!=nonce or reviewed.get('launch_id')!=launch:
   receipt.update(status='refused',reason='operator_review_binding');return receipt
  c={'url':url,'launch_id':launch,'nonce':nonce,'binding':binding,'review':reviewed,'target':target}
  receipt['eval_may_have_started']=True
  (out/'cancel-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
  result=evaluate(session,'recovery_cancel.js',c);receipt['browser_result']=result;receipt['status']=result.get('status','unknown')
  receipt['alarm_cleanup_status']='confirmed_cancelled' if receipt['status']=='cancelled_unqueued_alarm_only' else 'unknown_or_refused'
  if receipt['status']=='cancelled_unqueued_alarm_only':
   image=out/'current-after-cancel.png';call(session,['screenshot',str(image)],timeout=12)
   receipt['current_screenshot_path']=str(image);receipt['current_screenshot_sha256']=sha(image)
   receipt['current_screenshot_status']='delivered_requires_separate_operator_review'
  return receipt
 except BaseException as e:
  receipt.update(status='cancelled_screenshot_unknown' if receipt.get('alarm_cleanup_status')=='confirmed_cancelled' else ('unknown' if receipt.get('eval_may_have_started') else 'refused'),error=repr(e))
  return receipt
 finally:receipt['host_end_ns']=time.monotonic_ns();(out/'cancel-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
def cancel(session,url,launch,nonce,binding,review,target,out,ledger=None):
    """Production calls require a locked ledger; None is offline fixture only."""
    if ledger is None:return _cancel_unbudgeted(session,url,launch,nonce,binding,review,target,out)
    path=Path(ledger)
    if not path.parent.is_dir():raise ValueError('existing ledger parent')
    with path.open('a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);f.seek(0);raw=f.read()
        state=json.loads(raw) if raw else {'attempts':[],'recoveries':[]}
        step=binding['expected_step'];aid=binding['attempt_id']
        if (len(state.get('attempts',[]))>10 or len(state.get('recoveries',[]))>=2 or
            any(x.get('step')==step for x in state.get('recoveries',[])) or
            not any(x.get('attempt_id')==aid and x.get('step')==step for x in state.get('attempts',[]))):
            return {'status':'refused','reason':'supervised_budget_or_attempt_ledger','cancel_invoked':False}
        # Reserve and persist before any possible browser-side alarm mutation.
        reservation={'step':step,'attempt_id':aid,'nonce':nonce,'status':'reserved_unknown','host_ns':time.monotonic_ns()}
        state['recoveries'].append(reservation)
        f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();__import__('os').fsync(f.fileno())
        result=_cancel_unbudgeted(session,url,launch,nonce,binding,review,target,out)
        reservation['status']=result['status']
        reservation['alarm_cleanup_status']=result.get('alarm_cleanup_status','unknown')
        reservation['current_screenshot_status']=result.get('current_screenshot_status','unknown')
        f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();__import__('os').fsync(f.fileno())
        return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('capture','cancel'))
 for k in ('session','url','launch-id','nonce','binding','out'):p.add_argument('--'+k,required=True)
 p.add_argument('--review');p.add_argument('--target');p.add_argument('--ledger');a=p.parse_args()
 if a.action=='cancel' and not a.ledger:p.error('--ledger required for cancel')
 binding=json.loads(Path(a.binding).read_text());c=(a.session,a.url,a.launch_id,a.nonce,binding)
 result=capture(*c,a.out) if a.action=='capture' else cancel(*c,a.review,a.target or '',a.out,a.ledger)
 print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status'] in ('qualified_review_screenshot','cancelled_unqueued_alarm_only') else 2)
