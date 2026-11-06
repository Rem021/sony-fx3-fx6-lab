"""Host evidence links for one explicit unqueued recovery; never authorizes a key."""
from common import *
from recovery_observation import validate

def pinned(path,expected):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or sha(p)!=expected:raise ValueError('recovery_link_hash')
 return json.loads(p.read_text())
def pending(require_review):
 v=read('pending-recovery-review.json');a=read('current-attempt.json');folder=Path(a['path'])
 if v.get('status')!=('explicit_recovery_image_reviewed' if require_review else 'requires_separate_explicit_review'):raise ValueError('recovery_review_state_or_replay')
 if any(v.get(k)!=a.get(k) for k in ('step','attempt_number','attempt_id','nonce')):raise ValueError('recovery_attempt_changed')
 b=pinned(folder/'binding.json',v['binding_sha256'])
 cr=pinned(v['cancel_path'],v['cancel_sha256']);br=cr.get('browser_result',{});alarm=br.get('alarm_cancel_receipt',{})
 if cr.get('status')!='cancelled_unqueued_alarm_only' or cr.get('binding')!=b or br.get('nonce')!=a['nonce'] or alarm.get('current',{}).get('nonce')!=a['nonce'] or alarm.get('current',{}).get('state')!='cancelled':raise ValueError('recovery_cancel_binding')
 cap=validate(v['capture_result'],b,'cancelled',v['capture_sha256'])
 if cr['observation_path']!=v['capture_result'] or cr['observation_sha256']!=v['capture_sha256'] or cap['source']['url']!=identity()['url'] or cap['source']['session']!=CFG['session']:raise ValueError('recovery_source_link')
 records=read('ledger.json')['recoveries'];matches=[r for r in records if r['attempt_id']==a['attempt_id'] and r['nonce']==a['nonce'] and r['step']==a['step']]
 if len(matches)!=1 or matches[0].get('status')!='cancelled_unqueued_alarm_only' or matches[0].get('current_screenshot_status')!='delivered_requires_separate_operator_review':raise ValueError('recovery_ledger_link')
 if require_review and (not v.get('review_target','').strip() or v.get('reviewed_png_sha256')!=cap['screenshot_sha256'] or v.get('reviewed_receipt_sha256')!=v['capture_sha256']):raise ValueError('recovery_explicit_review_link')
 # Same live lifecycle and same cancelled nonce, but no historical SHA/gen equality.
 code=(CANDIDATE_OPS/'recovery_readonly.js').read_text()+'('+json.dumps({'url':identity()['url'],'launch_id':identity()['launch_id'],'nonce':a['nonce'],'binding':b,'mode':'cancelled','cancel_receipt':alarm,'cancel_identity_json':br['alarm_cancel_identity_json']})+')'
 live=ev(folder.name+'-recovery-current-lifecycle',code)
 if not live.get('qualified') or live.get('document_id')!=cap['before']['document_id'] or live.get('document_time_origin')!=cap['before']['document_time_origin']:raise ValueError('recovery_live_lifecycle')
 return v,cap

def click_guard(step,ledger):
 if len(ledger['attempts'])>=10 or len(ledger['recoveries'])>2:raise ValueError('navigation_budget')
 if not (HERE/'current-attempt.json').exists():return None
 a=read('current-attempt.json')
 if a['step']!=step:return None
 # A same-step repeat always requires its exact distinct reviewed recovery observation.
 return pending(True)[0]

def durable_pending(v):
 p=HERE/'pending-recovery-review.json'
 with p.open('w') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n');f.flush();os.fsync(f.fileno())
