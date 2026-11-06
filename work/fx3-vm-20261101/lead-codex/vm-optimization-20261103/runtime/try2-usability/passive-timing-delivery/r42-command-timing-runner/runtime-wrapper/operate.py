"""One explicit tool call per click/capture, confirm, or recovery cancel; no retry."""
import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"operator-helpers"))
from planned_prerequisite import prerequisite,PLAN_SHA
from common import *
from review_snapshot_cli import validate_capture
from later_capture import current_guard
from recovery_guard import pending,click_guard,durable_pending
import postkey_flow as flow

def savepath(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def argbase(c,nonce):return ['--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',nonce]
def failcleanup():
 return evidence.dispatch_cleanup(SOURCE,HERE,ENV)
def prerequisite_record(step,cap_path,target,confirmation=None):
 c=identity();cap=json.loads(Path(cap_path).read_text())
 origin=(cap['before']['origin'] if step==0 else json.loads(Path(confirmation).read_text())['browser_result']['cancelled']['documentTimeOrigin'])
 v={'schema':'fx3-planned-prerequisite-r24-v1','plan_sha':PLAN_SHA,'completed_step':step,'launch_id':c['launch_id'],
    'document_time_origin':origin,'observation_path':str(cap_path),'observation_sha256':sha(cap_path),
    'semantic_review':{'passed':True,'source':'operation_agent_explicit_screenshot_review','target':target,**stamp()}}
 if confirmation:v.update(confirmation_path=str(confirmation),confirmation_sha256=sha(confirmation))
 path=HERE/('step-%02d-prerequisite.json'%step);savepath(path,v)
 prerequisite(path,step+1,c['launch_id'])
 return path

def _run_action(action):
 c=identity()
 if (HERE/'POSTKEY-TERMINAL.json').exists():raise ValueError('r26_run_terminal_no_further_action')
 if action=='reject':raise ValueError('operator_explicit_semantic_rejection: '+sys.argv[2])
 if action=='standby_review':
  target=sys.argv[2];assert target.strip()
  cap_path=HERE/'initial-standby/capture-result.json';cap=json.loads(cap_path.read_text())
  assert cap['firmware']['step']==0 and cap['status']=='qualified_current_screenshot'
  return {'status':'initial_standby_review_recorded','prerequisite_path':str(prerequisite_record(0,cap_path,target)),
          'scripted_navigation':True,'visual_review_at_click':False}
 if action=='recovery_review':
  target=sys.argv[2];assert target.strip();v,cap=pending(False)
  v.update(status='explicit_recovery_image_reviewed',review_target=target,reviewed_png_sha256=cap['screenshot_sha256'],reviewed_receipt_sha256=v['capture_sha256'],**stamp());durable_pending(v)
  return {'status':v['status'],'observation_id':cap['observation_id'],'input_permission':False}
 if action=='click':
  step=int(sys.argv[2]);target=sys.argv[3];row=CFG['steps'][step-1];assert 1<=step<=8 and target.strip()
  prior_path=HERE/('step-%02d-prerequisite.json'%(step-1));prior=prerequisite(prior_path,step,c['launch_id'])
  ledger=read('ledger.json') if (HERE/'ledger.json').exists() else {'attempts':[],'recoveries':[]}
  assert len(ledger['attempts'])<10
  recovery=click_guard(step,ledger)
  attempt=len(ledger['attempts'])+1;folder=HERE/('step-%02d-attempt-%02d'%(step,attempt));folder.mkdir();nonce=str(__import__('uuid').uuid4());prefix=folder.name
  a={**row,'attempt_number':attempt,'nonce':nonce,'path':str(folder),'scripted_action_target':target,'scripted_navigation':True,'visual_review_at_click':False,'plan_sha':PLAN_SHA,'host_wall_ns':time.time_ns(),**stamp()};savepath(folder/'identity.json',a);write('current-attempt.json',a)
  if recovery:
   recovery.update(status='consumed_by_explicit_new_click',next_nonce=nonce,next_attempt_number=attempt,**stamp());durable_pending(recovery)
  arm=dl(prefix+'-arm','arm',nonce);assert arm['deadline_ms']==20000 and arm['current']['state']=='armed' and arm['current']['nonce']==nonce
  # Bind the actual document/run before the single original key invocation.
  binding=ev(prefix+'-postkey-document-binding','(()=>{if(location.href!=='+json.dumps(c['url'])+'||lastStatus.launch_request_id!=='+json.dumps(c['launch_id'])+'||performance.timeOrigin!=='+json.dumps(prior['document_time_origin'])+'||!lastStatus.run_incarnation)throw Error("postkey_binding");return {document_id:reviewDocumentId,document_time_origin:performance.timeOrigin,run_incarnation:lastStatus.run_incarnation}})()')
  a['postkey_binding']=binding;savepath(folder/'identity.json',a);write('current-attempt.json',a)
  r=helper(prefix+'-click','planned_navigation_click.py',['--session',CFG['session'],'--url',c['url'],'--launch',c['launch_id'],'--nonce',nonce,'--plan-sha',PLAN_SHA,'--step',str(step),'--prerequisite-path',str(prior_path),'--ledger',str(HERE/'ledger.json'),'--receipt',str(folder/'click-receipt.json')],watch=True)
  assert r['status']=='click_invoked'
  aid=r['result']['attempt_id'];a['attempt_id']=aid;savepath(folder/'identity.json',a);write('current-attempt.json',a)
  outcome=wait_readonly(prefix+'-attributed-outcome','(()=>{const a=fx3KeyAttemptOutcome();if(a?.attempt_id!=='+json.dumps(aid)+')throw Error("wrong_attempt");return ["accepted","not_posted","explicit_rejected_unqueued","delivery_unknown"].includes(a.outcome)?a:null})()');savepath(folder/'outcome.json',outcome)
  if outcome['outcome'] in ('not_posted','explicit_rejected_unqueued'):
   assert len(ledger['recoveries'])<2 and not any(x['step']==step for x in ledger['recoveries'])
   b={k:outcome[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')};b.update(PNG_sha256=outcome['frame']['PNG_sha256'],content_generation=outcome['frame']['content_generation'],sequence=outcome['frame']['sequence'],nonce=nonce);savepath(folder/'binding.json',b)
   out=folder/'recovery-review';r=helper(prefix+'-recovery-capture','recovery_tools.py',['capture',*argbase(c,nonce),'--binding',str(folder/'binding.json'),'--out',str(out)])
   assert r['status']=='qualified_recovery_observation';p=Path(r['screenshot_path']);assert p==out/'observation.png' and p.is_file() and not p.is_symlink() and sha(p)==r['screenshot_sha256'] and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
   a['recovery_capture_sha256']=sha(out/'observation-result.json');savepath(folder/'identity.json',a);write('current-attempt.json',a)
   value={'observation_path':str(out/'observation-result.json'),'observation_sha256':a['recovery_capture_sha256'],'input_permission':False,'status':r['status'],'screenshot_path':str(p),'screenshot_sha256':sha(p),'step':step,'attempt':attempt};write('current-return.json',value);return value
  assert outcome['outcome']=='accepted',outcome
  flow.initialize(a,c);value=flow.observe(a);write('current-return.json',value);return value
 if action=='observe':
  a=read('current-attempt.json');value=flow.observe(a,sys.argv[2]);write('current-return.json',value);return value
 if action=='pin':
  target=sys.argv[2];a=read('current-attempt.json');folder=Path(a['path']);step=a['step'];nonce=a['nonce'];aid=a['attempt_id'];prefix=folder.name
  flow.before_pin(a,target)
  out=folder/'capture';cfg={'url':c['url'],'launch_id':c['launch_id'],'nonce':nonce,'step':step,'attempt_id':aid,'prefix':prefix};savepath(folder/'capture-config.json',cfg)
  args=['capture','--session',CFG['session'],'--url',c['url'],'--launch',c['launch_id'],'--nonce',nonce,'--step',str(step),'--attempt',aid,'--out',str(out)]
  if step==1:args+=['--reference-sha','60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292']
  result=helper(prefix+'-snapshot-capture','review_snapshot_cli.py',args)
  assert result['status']=='qualified_review_snapshot'
  valid=validate_capture(out/'capture-result.json',step,aid,nonce,c['launch_id'])
  assert Path(valid['screenshot_path']).stat().st_mtime_ns>=a['host_wall_ns']
  valid.update(attempt_number=a['attempt_number'],**stamp());savepath(folder/'validated-image-return.json',valid);flow.pinned(a,folder/'validated-image-return.json');write('current-return.json',valid);return valid
 if action=='confirm':
  target=sys.argv[2];a=read('current-attempt.json');folder=Path(a['path']);cap=json.loads((folder/'validated-image-return.json').read_text());assert cap['status']=='qualified_review_snapshot' and cap['attempt_id']==a['attempt_id'] and cap['nonce']==a['nonce'] and cap['snapshot']['step']==a['step']==cap['step'];step=a['step']
  assert target.strip();flow.before_confirm(a,folder/'validated-image-return.json')
  savepath(folder/'visual-judgement.json',{'target':target,'semantic_passed':True,'source':'operation_agent_explicit_screenshot_review','model_received_at':'unknown','model_review_completed_at':'unknown',**stamp()})
  ev(folder.name+'-confirm-current-attempt',current_guard({**c,'step':step,'nonce':a['nonce'],'attempt_id':a['attempt_id']}))
  r=helper(folder.name+'-confirm','review_snapshot_cli.py',['confirm','--session',CFG['session'],'--url',c['url'],'--launch',c['launch_id'],'--nonce',a['nonce'],'--step',str(step),'--attempt',a['attempt_id'],'--capture-path',str(folder/'validated-image-return.json'),'--target',target,'--receipt',str(folder/'explicit-confirm-receipt.json')]);assert r['status']=='confirmed_and_cancelled'
  expected=r['browser_result']['expected'];snap=cap['snapshot']
  for key in ('snapshot_id','run_incarnation','launch_id','document_id','step','attempt_id','pin_request_id','observed_sequence','content_generation','PNG_sha256'):assert expected[key]==snap[key]
  assert r['launch_id']==c['launch_id'] and r['alarm_nonce']==a['nonce'] and r['step']==step
  write('step-%02d-confirm.json'%step,r)
  prerequisite_record(step,folder/'validated-image-return.json',target,folder/'explicit-confirm-receipt.json');flow.confirmed(a)
  return {'status':r['status'],'step':step,'elapsed_ms':r['browser_result']['cancelled']['events'][-1].get('elapsed_ms')}
 if action=='recovery_cancel':
  a=read('current-attempt.json');folder=Path(a['path']);out=folder/'recovery-cancel';target=sys.argv[2]
  r=helper(folder.name+'-recovery-cancel','recovery_tools.py',['cancel',*argbase(c,a['nonce']),'--binding',str(folder/'binding.json'),'--out',str(out),'--review',str(folder/'recovery-review/observation-result.json'),'--review-sha',a['recovery_capture_sha256'],'--target',target,'--ledger',str(HERE/'ledger.json')],watch=True)
  assert r['status']=='cancelled_unqueued_alarm_only';p=Path(r['current_screenshot_path']);assert p==out/'observation/observation.png' and p.is_file() and not p.is_symlink() and sha(p)==r['current_screenshot_sha256'] and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
  # The cancel helper already captured a distinct immutable observation after cancellation.
  v={'status':'requires_separate_explicit_review','step':a['step'],'attempt_number':a['attempt_number'],'attempt_id':a['attempt_id'],'nonce':a['nonce'],'binding_sha256':sha(folder/'binding.json'),'capture_result':r['observation_path'],'capture_sha256':r['observation_sha256'],'cancel_path':str(out/'cancel-result.json'),'cancel_sha256':sha(out/'cancel-result.json')}
  durable_pending(v)
  value={'status':r['status'],'observation_status':'qualified_recovery_observation','observation_path':v['capture_result'],'screenshot_path':str(p),'screenshot_sha256':sha(p),'input_permission':False};write('current-return.json',value);return value
 raise ValueError(action)
def run_action(action):
 try:
  event('operator_tool_'+action+'_entry');v=_run_action(action);event('operator_tool_'+action+'_return_prepared',**v);print(json.dumps(v,ensure_ascii=False));return v
 except BaseException as e:
  # Same actual guard shape as validated r21b; End before subsequent analysis.
  flow.terminal()
  write('FAILURE.json',{'action':action,'error':repr(e),**stamp()})
  try:failcleanup()
  except BaseException as ce:write('FAILURE-CLEANUP-ERROR.json',{'error':repr(ce)})
  raise
if __name__=='__main__':run_action(sys.argv[1])
