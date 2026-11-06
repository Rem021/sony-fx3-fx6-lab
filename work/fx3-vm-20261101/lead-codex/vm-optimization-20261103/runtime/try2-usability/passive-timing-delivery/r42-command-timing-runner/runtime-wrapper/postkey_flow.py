"""Durable per-attempt observe/pin/confirm flow; historical observations never grant input."""
from common import *
from postkey_observation import validate,STATUS
from review_snapshot_cli import evaluate,PAGE_SHA
import uuid

def persist(path,v):
 with path.open('w') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n');f.flush();os.fsync(f.fileno())
def location(a):return Path(a['path'])/'postkey-flow.json'
def initialize(a,c):
 b={**a['postkey_binding'],'url':c['url'],'launch_id':c['launch_id'],'step':a['step'],'attempt_id':a['attempt_id'],'nonce':a['nonce']}
 v={'schema':'fx3-postkey-flow-r26-v1','status':'unfixed','binding':b,'observations':[],'pin_attempted':False};p=location(a)
 with p.open('x') as f:f.write(json.dumps(v,indent=2)+'\n');f.flush();os.fsync(f.fileno())
 return v

def current(a,allowed):
 p=location(a);v=json.loads(p.read_text());b=v['binding'];c=identity()
 if v['status'] not in allowed or b['attempt_id']!=a['attempt_id'] or b['nonce']!=a['nonce'] or b['step']!=a['step'] or b['launch_id']!=c['launch_id'] or b['url']!=c['url'] or any(b.get(k)!=a['postkey_binding'][k] for k in ('document_id','document_time_origin','run_incarnation')):raise ValueError('r26_flow_terminal_or_identity')
 return v

def latest(v):
 x=v['observations'][-1]
 if x['status']!=STATUS:raise ValueError('r26_previous_observation_unknown')
 return validate(x['receipt_path'],x['receipt_sha256'],v['binding'])

def observe(a,judgement=None):
 v=current(a,('unfixed',));p=location(a)
 if v['pin_attempted'] or len(v['observations'])>=3:raise ValueError('r26_three_observations_or_already_pinned')
 if v['observations']:
  latest(v)
  if not judgement or not judgement.strip():raise ValueError('r26_explicit_prior_transition_review_required')
 n=len(v['observations'])+1;folder=Path(a['path']);reservation=folder/('observation-%d-reservation.json'%n);out=folder/('observation-%d'%n)
 x={'status':'reserved_unknown','reservation_id':str(uuid.uuid4()),'observation_number':n,'binding':v['binding'],'previous_observation_judgement':judgement,**stamp()};persist(reservation,x)
 v['observations'].append(x);v['status']='observation_reserved_unknown';persist(p,v)
 bp=folder/'postkey-binding.json'
 if not bp.exists():persist(bp,v['binding'])
 result=helper(folder.name+'-observe-%d'%n,'postkey_observation.py',['--session',CFG['session'],'--binding',str(bp),'--reservation',str(reservation),'--out',str(out)])
 if result['status']!=STATUS:raise ValueError('r26_observation_unknown')
 x.update(status=STATUS,receipt_path=str(out/'observation-result.json'),receipt_sha256=sha(out/'observation-result.json'))
 validate(x['receipt_path'],x['receipt_sha256'],v['binding']);v['status']='unfixed';persist(p,v)
 return {**result,'observation_number':n,'observations_remaining':3-n,'receipt_path':x['receipt_path'],'receipt_sha256':x['receipt_sha256']}

def before_pin(a,target):
 v=current(a,('unfixed',));latest(v)
 if not target.strip() or v['pin_attempted']:raise ValueError('r26_explicit_pin_review_required')
 # Current identity/phase check, never a current pixel comparison to a historical observation.
 result=evaluate(CFG['session'],'postkey_read.js',{**v['binding'],'page_sha':PAGE_SHA,'action':'guard'})
 if result.get('qualified') is not True:raise ValueError('r26_pin_current_identity')
 v.update(status='pin_reserved_unknown',pin_attempted=True,selection_target=target,selection_review_source='operation_agent_explicit_previous_observation_review',**stamp());persist(location(a),v)

def pinned(a,capture_path):
 v=current(a,('pin_reserved_unknown',));v.update(status='pinned',capture_path=str(capture_path),capture_sha256=sha(capture_path));persist(location(a),v)
def before_confirm(a,capture_path):
 v=current(a,('pinned',))
 if str(capture_path)!=v['capture_path'] or sha(capture_path)!=v['capture_sha256']:raise ValueError('r26_exact_pinned_capture_required')
 v['status']='confirm_reserved_unknown';persist(location(a),v)
def confirmed(a):
 v=current(a,('confirm_reserved_unknown',));v['status']='confirmed';persist(location(a),v)
def terminal():
 latch=HERE/'POSTKEY-TERMINAL.json'
 if not latch.exists():persist(latch,{'status':'terminal_End_required',**stamp()})
 try:
  a=read('current-attempt.json');p=location(a)
  if p.exists():
   v=json.loads(p.read_text());v['status']='terminal';persist(p,v)
 except BaseException:pass
