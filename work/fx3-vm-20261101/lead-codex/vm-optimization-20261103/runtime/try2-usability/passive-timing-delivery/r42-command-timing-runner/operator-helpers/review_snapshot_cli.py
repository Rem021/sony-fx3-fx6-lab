#!/usr/bin/env python3
"""Explicit pin/capture or confirm of one immutable post-key snapshot; never a guest key or retry."""
import argparse,base64,hashlib,json,subprocess,time
from pathlib import Path
from urllib.parse import urlsplit
HERE=Path(__file__).resolve().parent
PAGE_SHA=json.loads((HERE.parent/'PAGE-IDENTITY.json').read_text())['canonical_script_sha256']
IDENTITY=('snapshot_id','run_incarnation','launch_id','document_id','step','attempt_id','pin_request_id','observed_sequence','content_generation','PNG_sha256')
MENU_SHA='60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def call(session,args,source=None,timeout=15):
 p=subprocess.run(['agent-browser','--session',session,*args],input=source,text=True,capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError('owned browser operation failed')
 return p.stdout.strip()
def check(session,url):
 import re
 u=urlsplit(url)
 if not re.fullmatch('fx3-deadline-[A-Za-z0-9_-]+',session) or u.scheme!='http' or u.hostname!='127.0.0.1' or not u.port or url!=f'http://127.0.0.1:{u.port}/':raise ValueError('owned exact loopback session')
 tabs=json.loads(call(session,['tab','--json']))['data']['tabs']
 if len(tabs)!=1 or tabs[0]['url']!=url:raise ValueError('one owned tab')
def evaluate(session,file,c):return json.loads(call(session,['eval','--stdin'],(HERE/file).read_text()+'('+json.dumps(c)+')'))
def validate_capture(path,step,attempt,nonce,launch):
 p=Path(path);r=json.loads(p.read_text());s=r['snapshot'];image=Path(r['screenshot_path'])
 if (r.get('capture_schema')!='fx3-r24-snapshot-capture-v1' or r.get('status')!='qualified_review_snapshot' or r.get('nonce')!=nonce or
     s.get('schema')!='fx3-review-snapshot-v1' or s.get('step')!=step or s.get('attempt_id')!=attempt or s.get('launch_id')!=launch or
     not image.is_absolute() or image.is_symlink() or not image.is_file() or image.parent!=(p.parent if p.name=='capture-result.json' else p.parent/'capture') or
     not image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') or sha(image)!=s.get('PNG_sha256') or sha(image)!=r.get('screenshot_sha256') or
     image.stat().st_size!=s.get('byte_length') or s['observed_sequence']<=s['native_receive_floor_sequence']):raise ValueError('exact_snapshot_capture_binding')
 return r

def capture(session,url,launch,nonce,step,attempt,out,reference_sha=None):
 check(session,url);out=Path(out);out.mkdir();record={'status':'unknown','capture_schema':'fx3-r24-snapshot-capture-v1','nonce':nonce,'step':step,'attempt_id':attempt,'guest_keys_sent':0,'host_start_ns':time.monotonic_ns()}
 config={'url':url,'launch':launch,'nonce':nonce,'step':step,'attempt_id':attempt,'page_sha':PAGE_SHA,'reference_sha':reference_sha}
 try:
  evaluate(session,'snapshot_read.js',{**config,'action':'ready'})
  record['pin_result']=evaluate(session,'snapshot_read.js',{**config,'action':'pin'})
  result=evaluate(session,'snapshot_read.js',{**config,'action':'export','include_bytes':True})
  data=base64.b64decode(result.pop('png_base64'),validate=True);s=result['snapshot']
  if len(data)!=s['byte_length'] or hashlib.sha256(data).hexdigest()!=s['PNG_sha256']:raise ValueError('snapshot_png_bytes')
  image=out/'review-snapshot.png';image.write_bytes(data)
  again=evaluate(session,'snapshot_read.js',{**config,'action':'export','include_bytes':False})
  if any(again['snapshot'][k]!=s[k] for k in IDENTITY) or again['document_time_origin']!=result['document_time_origin']:raise ValueError('snapshot_export_changed')
  record.update(result,screenshot_path=str(image),screenshot_sha256=sha(image),actual_visual_semantic_review='pending separate operation-agent image viewing')
 except BaseException as e:record['error_kind']=type(e).__name__
 record['host_end_ns']=time.monotonic_ns();(out/'capture-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 return record

def confirm(session,url,launch,nonce,step,attempt,capture_path,target,receipt):
 check(session,url);r=validate_capture(capture_path,step,attempt,nonce,launch)
 if not target.strip() or len(target)>500:raise ValueError('explicit actual screenshot semantic judgement required')
 receipt=Path(receipt);record={'status':'unknown','receipt_schema':'fx3-r24-snapshot-confirm-v1','launch_id':launch,'alarm_nonce':nonce,'step':step,'attempt_id':attempt,'reviewed_png_sha256':r['snapshot']['PNG_sha256'],'target':target,'retries':0,'guest_keys_sent_by_helper':0,'eval_may_have_started':False}
 with receipt.open('x') as f:f.write(json.dumps(record,indent=2)+'\n')
 try:
  c={'url':url,'launch':launch,'nonce':nonce,'step':step,'attempt_id':attempt,'snapshot':r['snapshot'],'page_sha':PAGE_SHA}
  record['eval_may_have_started']=True;receipt.write_text(json.dumps(record,indent=2)+'\n')
  v=evaluate(session,'snapshot_confirm.js',c);record['browser_result']=v
  if type(v) is dict and v.get('receipt_schema')==record['receipt_schema']:
   if v.get('status') in ('refused','unknown'):record['status']=v['status']
   elif (v.get('status')=='confirmed_and_cancelled' and v.get('click_invoked') is True and
         type(v.get('expected')) is dict and all(v['expected'].get(k)==r['snapshot'][k] for k in IDENTITY) and
         v.get('cancelled',{}).get('current',{}).get('nonce')==nonce and
         v['cancelled']['current'].get('state')=='cancelled'):
    record['status']='confirmed_and_cancelled'
 except BaseException as e:record['error_kind']=type(e).__name__
 receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');return record
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['capture','confirm'])
 for k in ('session','url','launch','nonce','step','attempt'):p.add_argument('--'+k,required=True,type=int if k=='step' else str)
 for k in ('out','capture-path','target','receipt','reference-sha'):p.add_argument('--'+k)
 a=p.parse_args()
 r=capture(a.session,a.url,a.launch,a.nonce,a.step,a.attempt,a.out,a.reference_sha) if a.action=='capture' else confirm(a.session,a.url,a.launch,a.nonce,a.step,a.attempt,a.capture_path,a.target or '',a.receipt)
 print(json.dumps(r,ensure_ascii=False));raise SystemExit(0 if r['status'] in ('qualified_review_snapshot','confirmed_and_cancelled') else 2)
