"""Historical visual evidence and original confirmation, never a current-frame permit."""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN_SHA='4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plan(sha256):
 p=HERE.parent/'NAVIGATION-PLAN.json'
 if sha256!=PLAN_SHA or sha(p)!=PLAN_SHA:raise ValueError('plan_sha_mismatch')
 return json.loads(p.read_text())
def file(p):
 p=Path(p)
 if not p.is_absolute() or p.is_symlink() or not p.is_file():raise ValueError('evidence_regular_absolute_file')
 return p

def prerequisite(path,step,launch):
 p=file(path);v=json.loads(p.read_text())
 if (v.get('schema')!='fx3-planned-prerequisite-r24-v1' or v.get('plan_sha')!=PLAN_SHA or
     type(v.get('completed_step')) is not int or v['completed_step']!=step-1 or v.get('launch_id')!=launch or
     v.get('semantic_review',{}).get('passed') is not True or
     v['semantic_review'].get('source')!='operation_agent_explicit_screenshot_review' or
     not v['semantic_review'].get('target','').strip() or
     type(v.get('document_time_origin')) not in (int,float) or not math.isfinite(v['document_time_origin'])):
  raise ValueError('previous_visual_review_or_step_missing')
 obs=file(v['observation_path']);cap=json.loads(obs.read_text())
 if sha(obs)!=v['observation_sha256']:raise ValueError('observation_receipt_hash')
 shot=file(cap['screenshot_path'])
 if not shot.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('observation_not_png')
 image_sha=cap.get('screenshot_file_sha256',cap.get('screenshot_sha256'))
 if sha(shot)!=image_sha:raise ValueError('observation_image_hash')
 if step==1:
  if cap.get('status')!='qualified_current_screenshot' or cap['firmware']['step']!=0 or cap['before']['origin']!=v['document_time_origin']:raise ValueError('initial_standby_observation')
  previous=None
 else:
  if (cap.get('capture_schema')!='fx3-r24-snapshot-capture-v1' or cap.get('status')!='qualified_review_snapshot' or
      cap.get('step')!=step-1 or not cap.get('attempt_id') or not cap.get('nonce')):raise ValueError('r24_previous_capture_binding')
  snap=cap['snapshot']
  if (image_sha!=snap.get('PNG_sha256') or shot.stat().st_size!=snap.get('byte_length') or
      snap.get('launch_id')!=launch or cap.get('document_time_origin')!=v['document_time_origin'] or
      cap.get('pin_result',{}).get('document_id')!=snap.get('document_id')):raise ValueError('r24_snapshot_image_document_binding')
  cp=file(v['confirmation_path']);cr=json.loads(cp.read_text())
  if sha(cp)!=v['confirmation_sha256']:raise ValueError('previous_confirm_hash')
  br=cr.get('browser_result',{});ex=br.get('expected',{});cancel=br.get('cancelled',{});current=cancel.get('current',{})
  keys=('snapshot_id','run_incarnation','launch_id','document_id','step','attempt_id','pin_request_id','observed_sequence','content_generation','PNG_sha256')
  if (cr.get('receipt_schema')!='fx3-r24-snapshot-confirm-v1' or cr.get('status')!='confirmed_and_cancelled' or
      cr.get('step')!=step-1 or cr.get('launch_id')!=launch or cr.get('alarm_nonce')!=cap['nonce'] or
      cr.get('reviewed_png_sha256')!=snap['PNG_sha256'] or snap['step']!=step-1 or snap['attempt_id']!=cap['attempt_id'] or
      ex.get('schema')!='fx3-review-snapshot-v1' or any(ex.get(k)!=snap[k] for k in keys) or not ex.get('request_id') or
      current.get('state')!='cancelled' or current.get('nonce')!=cap['nonce'] or
      cancel.get('documentTimeOrigin')!=v['document_time_origin']):raise ValueError('r24_previous_exact_snapshot_confirm_binding')
  previous={'expected':ex,'receipt_sha256':sha(cp),'attempt_id':cap['attempt_id'],'nonce':cap['nonce']}
 return {'completed_step':step-1,'document_time_origin':v['document_time_origin'],
         'launch_id':launch,'prerequisite_sha256':sha(p),'previous_confirm':previous,
         'historical_observation_sha256':sha(obs),'historical_image_sha256':image_sha}
