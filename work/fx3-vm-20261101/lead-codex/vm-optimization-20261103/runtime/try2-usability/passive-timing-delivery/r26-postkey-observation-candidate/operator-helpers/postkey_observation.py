"""One reserved read-only unpinned postkey PNG export; no pin/confirm/key/timer mutation."""
import argparse,base64,hashlib,json,os,time,subprocess
from pathlib import Path
from review_snapshot_cli import PAGE_SHA,check
STATUS='qualified_unpinned_postkey_observation'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 with Path(p).open('w') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n');f.flush();os.fsync(f.fileno())
def validate(path,expected_sha,binding):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or sha(p)!=expected_sha:raise ValueError('r26_observation_receipt_hash')
 v=json.loads(p.read_text());image=Path(v['screenshot_path'])
 if (v.get('schema')!='fx3-postkey-observation-r26-v1' or v.get('status')!=STATUS or v.get('binding')!=binding or v.get('snapshot_pinned') is not False or v.get('postkey_confirmation') is not False or v.get('input_permission') is not False or v.get('firmware_generation') is not None or image!=p.parent/'observation.png' or image.is_symlink() or not image.is_file() or not image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') or v.get('source',{}).get('method')!='agent-browser screenshot' or sha(image)!=v['screenshot_sha256'] or image.stat().st_size!=v['byte_length']):raise ValueError('r26_observation_not_fixed_capture_or_image_mismatch')
 return v

def capture(session,binding,reservation,out):
 reservation=Path(reservation);res=json.loads(reservation.read_text())
 if res.get('status')!='reserved_unknown' or res.get('binding')!=binding or not 1<=res.get('observation_number',0)<=3:raise ValueError('r26_one_reserved_observation')
 res.update(status='eval_started_unknown',host_ns=time.monotonic_ns());save(reservation,res)
 out=Path(out);out.mkdir();record={'schema':'fx3-postkey-observation-r26-v1','status':'unknown','host_start_ns':time.monotonic_ns(),'binding':binding,'reservation_id':res['reservation_id'],'guest_keys_sent':0,'pin_calls':0,'confirm_calls':0,'alarm_mutations':0,'snapshot_pinned':False,'postkey_confirmation':False,'input_permission':False,'firmware_generation':None}
 def browser(name,args,source=None):
  p=subprocess.run(['agent-browser','--session',session,*args],input=source,text=True,capture_output=True,timeout=15)
  save(out/(name+'.process.json'),{'returncode':p.returncode,'stdout':p.stdout[:16000],'stderr':p.stderr[:2000]})
  if p.returncode:raise RuntimeError('r26 '+name+' unknown: '+p.stderr[:500])
  return p.stdout
 def tabs(name):
  rows=json.loads(browser(name,['tab','--json']))['data']['tabs']
  if len(rows)!=1 or rows[0]['url']!=binding['url']:raise ValueError('r26_unique_owned_tab_URL')
  return rows
 def read(name,action):
  code=Path(__file__).with_name('postkey_read.js').read_text()+'('+json.dumps({**binding,'page_sha':PAGE_SHA,'action':action})+')'
  return json.loads(browser(name,['eval','--stdin'],code))
 try:
  check(session,binding['url'])
  record['tabs_before']=tabs('tabs-before');before=read('before','observe');record['before']=before
  image=out/'observation.png';browser('actual-screenshot',['screenshot',str(image)])
  record['tabs_after_screenshot']=tabs('tabs-after-screenshot');after=read('after','after');record['after']=after
  record['tabs_after']=tabs('tabs-after')
  for key in ('document_id','origin','run_incarnation'):
   if before[key]!=after[key]:raise ValueError('r26_screenshot_identity_changed')
  if before['qualified'] is not True or after['qualified'] is not True or before['alarm_identity_json']!=after['alarm_identity_json'] or after['performance_ms']<before['performance_ms']:raise ValueError('r26_screenshot_alarm_or_lifecycle_changed')
  if image.is_symlink() or not image.is_file() or not image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') or image.stat().st_size>16*1024*1024:raise ValueError('r26_real_screenshot_png')
  record.update(status=STATUS,screenshot_path=str(image),screenshot_sha256=sha(image),byte_length=image.stat().st_size,source={'method':'agent-browser screenshot','session':session,'url':binding['url'],'scope':'historical browser capture between two lifecycle observations; no single firmware generation or pixel causality'},actual_semantic_review='pending separate operator call')
 except BaseException as e:record.update(status='unknown',error_kind=type(e).__name__,reason=str(e)[:700])
 record['host_end_ns']=time.monotonic_ns();save(out/'observation-result.json',record)
 res.update(status=record['status'],receipt_path=str(out/'observation-result.json'),receipt_sha256=sha(out/'observation-result.json'));save(reservation,res)
 return record
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('session','binding','reservation','out'):p.add_argument('--'+k,required=True)
 a=p.parse_args();r=capture(a.session,json.loads(Path(a.binding).read_text()),a.reservation,a.out);print(json.dumps(r,ensure_ascii=False));raise SystemExit(0 if r['status']==STATUS else 2)
