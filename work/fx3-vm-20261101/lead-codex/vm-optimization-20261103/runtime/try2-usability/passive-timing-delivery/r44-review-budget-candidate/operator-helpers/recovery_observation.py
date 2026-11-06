"""Immutable interval browser observation; no firmware-frame identity or input permit."""
import hashlib,json,math,os,uuid
from pathlib import Path
SCHEMA='fx3-recovery-observation-r25-v1'
IDENTITY=('mode','attempt_id','nonce','launch_id','document_time_origin','document_id','step','attempt_binding','attempt_outcome','mutation_called','alarm_state','alarm_due_ms','alarm_armed_ms','alarm_cancelled_ms')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regular(p):
 p=Path(p)
 if not p.is_absolute() or p.is_symlink() or not p.is_file():raise ValueError('regular_absolute_observation_file')
 return p

def valid_states(before,after,binding,mode):
 for s in (before,after):
  if (s.get('qualified') is not True or s.get('mode')!=mode or s.get('attempt_binding')!=binding or s.get('attempt_id')!=binding['attempt_id'] or s.get('nonce')!=binding['nonce'] or s.get('launch_id')!=binding['launch_request_id'] or s.get('document_time_origin')!=binding['document_time_origin'] or not s.get('document_id') or s.get('step')!=binding['base_step'] or s.get('alarm_state')!=mode or s.get('phase')!='ready' or s.get('ready') is not True or any(s.get(k) for k in ('busy','review_required','error','delivery_unknown','review_unknown','protocol_unknown','ending','finished')) or s.get('attempt_outcome') not in ('not_posted','explicit_rejected_unqueued')):raise ValueError('recovery_observation_lifecycle')
  if s['attempt_outcome']=='not_posted' and s.get('mutation_called') is not False:raise ValueError('not_posted_mutation')
  if s.get('alarm_budget_ms')!=60000 or s.get('alarm_due_exact_in_browser') is not True:raise ValueError('alarm_60s_browser_identity')
  fresh=s.get('fresh_server_lifecycle',{})
  if fresh.get('phase')!='ready' or fresh.get('ready') is not True or fresh.get('steps')!=binding['base_step'] or fresh.get('launch_id')!=binding['launch_request_id'] or any(fresh.get(k) for k in ('busy','review_required','error','protocol_unknown')) or fresh.get('render_valid') is not True:raise ValueError('fresh_server_lifecycle')
  if mode=='armed' and s['performance_ms']>=s['alarm_due_ms']:raise ValueError('expired_alarm')
  if mode=='cancelled' and (not isinstance(s['alarm_cancelled_ms'],(int,float)) or not s['alarm_armed_ms']<=s['alarm_cancelled_ms']<s['alarm_due_ms']):raise ValueError('cancelled_alarm_identity')
 if any(before.get(k)!=after.get(k) for k in IDENTITY) or after['performance_ms']<before['performance_ms'] or after['sequence']<before['sequence']:raise ValueError('recovery_observation_identity_changed')

def observe(session,url,launch,nonce,binding,out,mode,call,evaluate,cancel_receipt=None,cancel_identity_json=None):
 import time
 out=Path(out);out.mkdir() # new directory makes acquisition source exclusive
 c={'url':url,'launch_id':launch,'nonce':nonce,'binding':binding,'mode':mode,'cancel_receipt':cancel_receipt,'cancel_identity_json':cancel_identity_json}
 receipt={'schema':SCHEMA,'status':'unknown','observation_id':str(uuid.uuid4()),'binding':binding,'mode':mode,'source':{'method':'agent-browser screenshot','session':session,'url':url},'host_start_ns':time.monotonic_ns(),'input_permission':False,'postkey_confirmation':False,'firmware_generation':None,'causality':'not asserted; browser capture occurred between two lifecycle observations'}
 try:
  before=evaluate(session,'recovery_readonly.js',c);receipt['before']=before
  if not before.get('qualified'):receipt.update(status='refused',reason=before.get('reason'));return receipt
  image=out/'observation.png';call(session,['screenshot',str(image)],timeout=12)
  image=regular(image);data=image.read_bytes()
  if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>16*1024*1024:raise ValueError('observation_png')
  receipt.update(screenshot_path=str(image),screenshot_sha256=sha(image),screenshot_byte_length=len(data))
  after=evaluate(session,'recovery_readonly.js',c);receipt['after']=after;valid_states(before,after,binding,mode)
  receipt.update(status='qualified_recovery_observation',frame_changed=any(before[k]!=after[k] for k in ('PNG_sha256','content_generation','sequence')))
  return receipt
 except BaseException as e:receipt.update(status='unknown',error=repr(e));return receipt
 finally:
  receipt['host_end_ns']=time.monotonic_ns();(out/'observation-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')

def validate(path,binding,mode,expected_sha):
 path=regular(path)
 if not expected_sha or sha(path)!=expected_sha:raise ValueError('observation_receipt_hash')
 v=json.loads(path.read_text())
 if v.get('schema')!=SCHEMA or v.get('status')!='qualified_recovery_observation' or v.get('binding')!=binding or v.get('mode')!=mode or v.get('input_permission') is not False or v.get('postkey_confirmation') is not False or v.get('firmware_generation') is not None or v.get('source',{}).get('method')!='agent-browser screenshot':raise ValueError('observation_receipt_contract')
 valid_states(v['before'],v['after'],binding,mode)
 p=regular(v['screenshot_path'])
 if p!=path.parent/'observation.png' or not p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') or sha(p)!=v['screenshot_sha256'] or p.stat().st_size!=v['screenshot_byte_length']:raise ValueError('observation_image_hash')
 return v
