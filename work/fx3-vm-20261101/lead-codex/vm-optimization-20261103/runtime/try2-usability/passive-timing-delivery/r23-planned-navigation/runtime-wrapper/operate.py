"""One explicit tool call per click/capture, confirm, or recovery cancel; no retry."""
import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"operator-helpers"))
from planned_prerequisite import prerequisite,PLAN_SHA
from common import *
from capture_validation import validate_capture
from later_capture import current_guard
from untimed_image import snapshot

def savepath(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def argbase(c,nonce):return ['--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',nonce]
def failcleanup():
 p=subprocess.run(['python3','-B',str(SOURCE/'cleanup.py')],env=ENV,text=True,capture_output=True,timeout=100)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def prerequisite_record(step,cap_path,target,confirmation=None):
 c=identity();cap=json.loads(Path(cap_path).read_text())
 origin=(cap['before']['origin'] if step==0 else json.loads(Path(confirmation).read_text())['browser_result']['cancelled']['documentTimeOrigin'])
 v={'schema':'fx3-planned-prerequisite-v1','plan_sha':PLAN_SHA,'completed_step':step,'launch_id':c['launch_id'],
    'document_time_origin':origin,'observation_path':str(cap_path),'observation_sha256':sha(cap_path),
    'semantic_review':{'passed':True,'source':'operation_agent_explicit_screenshot_review','target':target,**stamp()}}
 if confirmation:v.update(confirmation_path=str(confirmation),confirmation_sha256=sha(confirmation))
 path=HERE/('step-%02d-prerequisite.json'%step);savepath(path,v)
 prerequisite(path,step+1,c['launch_id'])
 return path

def _run_action(action):
 c=identity()
 if action=='standby_review':
  target=sys.argv[2];assert target.strip()
  cap_path=HERE/'initial-standby/capture-result.json';cap=json.loads(cap_path.read_text())
  assert cap['firmware']['step']==0 and cap['status']=='qualified_current_screenshot'
  return {'status':'initial_standby_review_recorded','prerequisite_path':str(prerequisite_record(0,cap_path,target)),
          'scripted_navigation':True,'visual_review_at_click':False}
 if action=='recovery_review':
  target=sys.argv[2];assert target.strip();v=read('pending-recovery-review.json')
  cap=json.loads(Path(v['capture_result']).read_text());assert sha(cap['screenshot_path'])==cap['screenshot_sha256']
  v.update(status='explicit_recovery_image_reviewed',review_target=target,**stamp());write('pending-recovery-review.json',v)
  return {'status':v['status']}
 if action=='click':
  step=int(sys.argv[2]);target=sys.argv[3];row=CFG['steps'][step-1];assert 1<=step<=8 and target.strip()
  prior_path=HERE/('step-%02d-prerequisite.json'%(step-1));prior=prerequisite(prior_path,step,c['launch_id'])
  ledger=read('ledger.json') if (HERE/'ledger.json').exists() else {'attempts':[],'recoveries':[]}
  assert len(ledger['attempts'])<10
  if (HERE/'pending-recovery-review.json').exists():assert read('pending-recovery-review.json')['status']=='explicit_recovery_image_reviewed'
  attempt=len(ledger['attempts'])+1;folder=HERE/('step-%02d-attempt-%02d'%(step,attempt));folder.mkdir();nonce=str(__import__('uuid').uuid4());prefix=folder.name
  a={**row,'attempt_number':attempt,'nonce':nonce,'path':str(folder),'scripted_action_target':target,'scripted_navigation':True,'visual_review_at_click':False,'plan_sha':PLAN_SHA,'host_wall_ns':time.time_ns(),**stamp()};savepath(folder/'identity.json',a);write('current-attempt.json',a)
  arm=dl(prefix+'-arm','arm',nonce);assert arm['deadline_ms']==20000 and arm['current']['state']=='armed' and arm['current']['nonce']==nonce
  r=helper(prefix+'-click','planned_navigation_click.py',['--session',CFG['session'],'--url',c['url'],'--launch',c['launch_id'],'--nonce',nonce,'--plan-sha',PLAN_SHA,'--step',str(step),'--prerequisite-path',str(prior_path),'--ledger',str(HERE/'ledger.json'),'--receipt',str(folder/'click-receipt.json')],watch=True)
  assert r['status']=='click_invoked'
  aid=r['result']['attempt_id'];a['attempt_id']=aid;savepath(folder/'identity.json',a);write('current-attempt.json',a)
  outcome=wait_readonly(prefix+'-attributed-outcome','(()=>{const a=fx3KeyAttemptOutcome();if(a?.attempt_id!=='+json.dumps(aid)+')throw Error("wrong_attempt");return ["accepted","not_posted","explicit_rejected_unqueued","delivery_unknown"].includes(a.outcome)?a:null})()');savepath(folder/'outcome.json',outcome)
  if outcome['outcome'] in ('not_posted','explicit_rejected_unqueued'):
   assert len(ledger['recoveries'])<2 and not any(x['step']==step for x in ledger['recoveries'])
   b={k:outcome[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')};b.update(PNG_sha256=outcome['frame']['PNG_sha256'],content_generation=outcome['frame']['content_generation'],sequence=outcome['frame']['sequence'],nonce=nonce);savepath(folder/'binding.json',b)
   out=folder/'recovery-review';r=helper(prefix+'-recovery-capture','recovery_tools.py',['capture',*argbase(c,nonce),'--binding',str(folder/'binding.json'),'--out',str(out)])
   assert r['status']=='qualified_review_screenshot';p=Path(r['screenshot_path']);assert p==out/'review-page.png' and p.is_file() and not p.is_symlink() and sha(p)==r['screenshot_sha256'] and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
   value={'status':r['status'],'screenshot_path':str(p),'screenshot_sha256':sha(p),'step':step,'attempt':attempt};write('current-return.json',value);return value
  assert outcome['outcome']=='accepted',outcome
  out=folder/'capture';cfg={'url':c['url'],'launch_id':c['launch_id'],'nonce':nonce,'step':step,'attempt_id':aid,'prefix':prefix};savepath(folder/'capture-config.json',cfg)
  if step==1:
   r=helper(prefix+'-capture','bounded_capture_cli.py',[*argbase(c,nonce),'--evidence-dir',str(out)])
   ev(prefix+'-capture-current-attempt',current_guard(cfg))
   process=read(prefix+'-capture-process.json');valid=validate_capture(process['returncode'],process['stdout'],out)
  else:
   raw=run(prefix+'-capture',['python3','-B',str(SOURCE/'later_capture.py'),str(folder/'capture-config.json'),str(out)],timeout=18)
   process=read(prefix+'-capture-process.json');valid=validate_capture(process['returncode'],raw,out)
  assert Path(valid['screenshot_path']).stat().st_mtime_ns>=a['host_wall_ns']
  assert valid['firmware_step']==step
  valid.update(step=step,attempt_number=attempt,attempt_id=aid,nonce=nonce,**stamp());savepath(folder/'validated-image-return.json',valid);write('current-return.json',valid);return valid
 if action=='confirm':
  target=sys.argv[2];a=read('current-attempt.json');folder=Path(a['path']);cap=json.loads((folder/'validated-image-return.json').read_text());assert cap['validated_new_screenshot'] and cap['attempt_id']==a['attempt_id'] and cap['nonce']==a['nonce'] and cap['firmware_step']==a['step']==cap['step'];step=a['step']
  assert target.strip()
  savepath(folder/'visual-judgement.json',{'target':target,'semantic_passed':True,'source':'operation_agent_explicit_screenshot_review','model_received_at':'unknown','model_review_completed_at':'unknown',**stamp()})
  ev(folder.name+'-confirm-current-attempt',current_guard({**c,'step':step,'nonce':a['nonce'],'attempt_id':a['attempt_id']}))
  r=helper(folder.name+'-confirm','explicit_confirm_cli.py',[*argbase(c,a['nonce']),'--step',str(step),'--png-sha',cap['firmware_png_sha256'],'--target',target,'--receipt',str(folder/'explicit-confirm-receipt.json')]);assert r['status']=='confirmed_and_cancelled'
  expected=r['browser_result']['expected']
  assert expected['step']==step and expected['PNG_sha256']==cap['firmware_png_sha256'] and expected['content_generation']==cap['firmware_generation'] and expected['observed_sequence']>=cap['firmware_sequence']
  assert r['launch_id']==c['launch_id'] and r['alarm_nonce']==a['nonce'] and r['step']==step
  write('step-%02d-confirm.json'%step,r)
  prerequisite_record(step,folder/'validated-image-return.json',target,folder/'explicit-confirm-receipt.json')
  return {'status':r['status'],'step':step,'elapsed_ms':r['browser_result']['cancelled']['events'][-1].get('elapsed_ms')}
 if action=='recovery_cancel':
  a=read('current-attempt.json');folder=Path(a['path']);out=folder/'recovery-cancel';target=sys.argv[2]
  r=helper(folder.name+'-recovery-cancel','recovery_tools.py',['cancel',*argbase(c,a['nonce']),'--binding',str(folder/'binding.json'),'--out',str(out),'--review',str(folder/'recovery-review/review-result.json'),'--target',target,'--ledger',str(HERE/'ledger.json')],watch=True)
  assert r['status']=='cancelled_unqueued_alarm_only';p=Path(r['current_screenshot_path']);assert p==out/'current-after-cancel.png' and p.is_file() and not p.is_symlink() and sha(p)==r['current_screenshot_sha256'] and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
  # Capture result supplies a new image; next separate operator call must review it.
  fresh=snapshot(folder.name+'-cancel-pinned',folder/'cancel-pinned',a['step']-1);write('pending-recovery-review.json',{'status':'requires_separate_explicit_review','capture_result':str(folder/'cancel-pinned/capture-result.json')});value={**fresh,'status':r['status']};write('current-return.json',value);return value
 raise ValueError(action)
def run_action(action):
 try:
  event('operator_tool_'+action+'_entry');v=_run_action(action);event('operator_tool_'+action+'_return_prepared',**v);print(json.dumps(v,ensure_ascii=False));return v
 except BaseException as e:
  # Same actual guard shape as validated r21b; End before subsequent analysis.
  write('FAILURE.json',{'action':action,'error':repr(e),**stamp()})
  try:write('FAILURE-CLEANUP-DISPATCH.json',failcleanup())
  except BaseException as ce:write('FAILURE-CLEANUP-ERROR.json',{'error':repr(ce)})
  raise
if __name__=='__main__':run_action(sys.argv[1])
