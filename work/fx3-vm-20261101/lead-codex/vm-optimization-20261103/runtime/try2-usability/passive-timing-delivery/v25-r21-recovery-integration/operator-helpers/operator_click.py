#!/usr/bin/env python3
"""Explicit operator click through original PAGE button; test budget only, no direct POST."""
import argparse,fcntl,hashlib,json,os,subprocess,time,uuid
from pathlib import Path
from recovery_tools import check,call
HERE=Path(__file__).resolve().parent
PAGE_SHA='f1eb5a54e36b8395a419fee107b87a22fae86dc7eb3c32debfbf6e783e930eab'
KEYS=(3,48,21,431,428,427,504)
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
  script="""(async c=>{const digest=async s=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)))].map(x=>x.toString(16).padStart(2,'0')).join('');
   const scripts=[...document.scripts],h=window.__fx3InteractionDeadlineV1?.status?.();
   if(location.href!==c.url||window.top!==window||scripts.length!==1||scripts[0].src||
      await digest(scripts[0].textContent.replace(/^const token=[^\\r\\n]*;$/m,'const token=__TOKEN__;'))!==c.page_sha||
      !lastStatus||lastStatus.launch_request_id!==c.launch||lastStatus.phase!=='ready'||!lastStatus.ready||lastStatus.error||lastStatus.busy||lastStatus.review_required||
      lastStatus.steps>=8||busy||ending||finished||deliveryUnknown||reviewUnknown||reviewAwaiting||awaitingStep!==null||renderFault||
      !frameLoadedFor(lastStatus)||shownSHA!==c.sha||displayedGeneration!==c.gen||
      h?.current?.nonce!==c.nonce||h.current.state!=='armed'||performance.now()>=h.current.due_ms)throw Error('operator_click_preflight');
   const b=[...document.querySelectorAll('.key')].find(x=>Number(x.dataset.key)===c.key);
   if(!b||b.disabled)throw Error('key_not_available');b.click();
   const a=fx3KeyAttemptOutcome();if(!a||a.key!==c.key||a.alarm_nonce!==c.nonce)throw Error('attempt_not_created');
   return {attempt_id:a.attempt_id,step:a.expected_step,base_step:a.base_step,clicked_sha:a.frame.PNG_sha256,clicked_generation:a.frame.content_generation,server_atomic_permission:false};
  })"""
  config={'url':url,'launch':launch,'nonce':nonce,'key':key,'sha':reviewed_sha,'gen':reviewed_generation,'page_sha':PAGE_SHA}
  record={'status':'unknown','session':session,'tab':tab,'target':target,'key':key,'host_start_ns':time.monotonic_ns(),'eval_may_have_started':True,'guest_keys_sent_directly_by_cli':0}
  receipt.open('x').write(json.dumps(record,indent=2)+'\n')
  reservation={'status':'reserved_unknown','reservation_id':str(uuid.uuid4()),'key':key,'host_ns':time.monotonic_ns()}
  state['attempts'].append(reservation)
  f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();os.fsync(f.fileno())
  try:
   value=json.loads(call(session,['eval','--stdin'],source=script+'('+json.dumps(config)+')',timeout=12));record.update(status='click_invoked',result=value)
  except BaseException as e:record['error']=repr(e)
  reservation.update(status=record['status'],attempt_id=record.get('result',{}).get('attempt_id'),step=record.get('result',{}).get('step'))
  f.seek(0);f.truncate();f.write(json.dumps(state,indent=2)+'\n');f.flush();os.fsync(f.fileno());record['host_end_ns']=time.monotonic_ns();receipt.write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('session','url','launch','nonce','key','reviewed-sha','reviewed-generation','target','ledger','receipt'):
  p.add_argument('--'+k,required=True,type=int if k in ('key','reviewed-generation') else str)
 a=p.parse_args();x=click(a.session,a.url,a.launch,a.nonce,a.key,a.reviewed_sha,a.reviewed_generation,a.target,a.ledger,a.receipt);print(json.dumps(x,indent=2));raise SystemExit(0 if x['status']=='click_invoked' else 2)
