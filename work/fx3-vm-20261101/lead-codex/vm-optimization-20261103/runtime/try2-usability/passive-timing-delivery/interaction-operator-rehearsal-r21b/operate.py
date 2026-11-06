"""Each subcommand is one explicit operator/tool boundary; never auto-retries."""
import argparse,sys
from common import *

def click(name,nonce,target,reviewed):
 c=identity()
 return helper(name,'operator_click.py',['--session',CFG['session'],'--url',c['url'],'--launch',c['launch_id'],'--nonce',nonce,'--key','427','--reviewed-sha',reviewed['sha'],'--reviewed-generation',str(reviewed['gen']),'--target',target,'--ledger',str(HERE/'ledger.json'),'--receipt',str(HERE/(name+'-receipt.json'))],watch=True)
def recover(name,action,folder,target=None):
 c=identity();a=[action,'--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',CFG['nonce_A'],'--binding',str(HERE/'binding-A.json'),'--out',str(HERE/folder)]
 assert not (HERE/folder).exists()
 if action=='cancel':a+=['--review',str(HERE/'recovery-review/review-result.json'),'--target',target,'--ledger',str(HERE/'ledger.json')]
 return helper(name,'recovery_tools.py',a,watch=action=='cancel')
def _run_action(action):
 event('operator_tool_'+action+'_entry')
 if action=='reject_capture':
  (HERE/'once-only-attempt-A').open('x').close()
  write('attempt-origin.json',{'host_wall_ns':time.time_ns(),**stamp()})
  # This target is the actual pre-reviewed initial screenshot, saved in preparation.
  dl('alarm-A-arm','arm',CFG['nonce_A'])
  initial=read('prepared-state.json');r=click('click-A',CFG['nonce_A'],'已亲看历史待机图，明确按一次 MENU；预期受控后台拒绝',initial)
  assert r['status']=='click_invoked'
  attempt=wait_readonly('read-attributed-attempt-A','(()=>{const a=fx3KeyAttemptOutcome();return a?.attempt_id==='+json.dumps(r['result']['attempt_id'])+'&&a.outcome==="explicit_rejected_unqueued"&&lastStatus?.ready&&frameLoadedFor(lastStatus)&&!document.querySelector(\'[data-key="427"]\').disabled?a:null})()')
  write('attempt-A.json',attempt)
  b={k:attempt[k] for k in ('attempt_id','document_time_origin','launch_request_id','key','base_step','expected_step')};b.update(PNG_sha256=attempt['frame']['PNG_sha256'],content_generation=attempt['frame']['content_generation'],sequence=attempt['frame']['sequence'],nonce=attempt['alarm_nonce']);write('binding-A.json',b)
  r=recover('recovery-capture','capture','recovery-review')
  value=validated('validated-recovery-return.json','recovery-capture',r,'recovery-review','review')
 elif action=='cancel_A':
  # This branch performs only the requested original recovery cancel and new capture.
  r=recover('recovery-cancel','cancel','recovery-cancel','亲看拒绝提示与当前 NO CARD 图；仅清除未入队旧 alarm，不批准画面或发键')
  value=validated('validated-cancel-return.json','recovery-cancel',r,'recovery-cancel','cancel')
 elif action=='accept_capture':
  (HERE/'once-only-attempt-B').open('x').close()
  dl('alarm-B-arm','arm',CFG['nonce_B'])
  current=read('current-after-cancel-visual.json')
  r=click('click-B',CFG['nonce_B'],'再次亲看取消后 NO CARD 当前图；新 nonce 下独立明确按一次 MENU',current)
  assert r['status']=='click_invoked'
  accepted=wait_readonly('read-attributed-attempt-B','(()=>{const a=fx3KeyAttemptOutcome();return a?.attempt_id==='+json.dumps(r['result']['attempt_id'])+'&&a.outcome==="accepted"?a:null})()');write('attempt-B.json',accepted)
  c=identity();folder='accepted-menu-capture';assert not (HERE/folder).exists()
  r=helper('bounded-capture','bounded_capture_cli.py',['--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',CFG['nonce_B'],'--evidence-dir',str(HERE/folder)])
  value=validated('validated-menu-return.json','bounded-capture',r,folder,'menu')
 elif action=='confirm_B':
  c=identity()
  r=helper('explicit-confirm','explicit_confirm_cli.py',['--session',CFG['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',CFG['nonce_B'],'--step','1','--png-sha','60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292','--target','亲看完整 Setup > Area/Date 45/59，Area/Date/Time Setting 橙色焦点及 Language English；仅确认该历史 fixture 图','--receipt',str(HERE/'explicit-confirm-receipt.json')])
  assert r['status']=='confirmed_and_cancelled';value={'status':r['status']}
 else:raise ValueError(action)
 event('operator_tool_'+action+'_return_prepared',**value);print(json.dumps(value));return value
def _cleanup_on_failure():
 p=subprocess.run(['python3',str(HERE/'cleanup.py')],env=ENV,text=True,capture_output=True)
 return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,**stamp()}
def run_action(action):
 # Actual imported AND CLI entry uses this guard, not just __main__.
 try:return _run_action(action)
 except BaseException as e:
  write('FAILURE.json',{'action':action,'error':repr(e),**stamp()})
  try:write('FAILURE-CLEANUP-DISPATCH.json',_cleanup_on_failure())
  except BaseException as ce:write('FAILURE-CLEANUP-ERROR.json',{'error':repr(ce),**stamp()})
  raise
if __name__=='__main__':run_action(sys.argv[1])
