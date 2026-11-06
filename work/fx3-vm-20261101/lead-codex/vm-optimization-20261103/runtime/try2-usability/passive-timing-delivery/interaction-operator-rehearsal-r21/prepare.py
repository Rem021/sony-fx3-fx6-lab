import sys
from common import *
from dependency_gate import verify
verify('DEPENDENCY-PREPARATION.json')
# All action and cleanup scripts exist before service/browser/timer; freeze local source now.
write('SOURCE-FREEZE.json',{p.name:sha(p) for p in HERE.glob('*.py')})
assert not (HERE/'fixture.json').exists()
log=(HERE/'fixture-stdout.txt').open('x');err=(HERE/'fixture-stderr.txt').open('x')
p=subprocess.Popen(['python3',str(HERE/'fixture_server.py')],stdout=log,stderr=err,env=ENV,start_new_session=True)
write('fixture-process-launch.json',{'pid':p.pid,**stamp()})
end=time.monotonic()+5
while time.monotonic()<end:
 if (HERE/'fixture.json').exists():break
 if p.poll() is not None:raise RuntimeError('fixture died')
 time.sleep(.03)
else:raise RuntimeError('fixture no config')
c=identity();browser('browser-open',['open',c['url']]);browser('viewport',['set','viewport','1280','1200'])
browser('start-ready-wait',['wait','--fn','!!lastStatus&&lastStatus.browser_ready&&!startButton.disabled'])
browser('Start-original-button',['click','#start'])
ready=wait_readonly('prepared-loaded-state','lastStatus?.ready&&frameLoadedFor(lastStatus)&&!document.querySelector(\'[data-key="427"]\').disabled&&({sha:shownSHA,gen:displayedGeneration,seq:displayed,launch:lastStatus.launch_request_id})')
assert identity()['launch_id']==ready['launch']
write('prepared-state.json',ready)
write('deadline-install.json',dl('deadline-install','install'))
browser('prepared-snapshot',['snapshot']);browser('prepared-screenshot',['screenshot',str(HERE/'prepared-page.png')])
info=json.loads(browser('browser-ownership-info',['session','info','--json']));write('prepared-browser-info.json',info)
# Validate exact single session/tab/output identities before the timer.
tabs=json.loads(browser('prepared-owned-tab',['tab','--json']))['data']['tabs'];assert len(tabs)==1 and tabs[0]['url']==c['url']
assert CFG['nonce_A']!=CFG['nonce_B'];assert not (HERE/'ledger.json').exists()
write('PREPARATION.json',{'passed':True,'no_arm_yet':True,'no_key_yet':True,'historical_fixture_visual':{'initial':'standby icons','current_after_rejection':'NO CARD historical partial view','accepted_target':'complete Setup > Area/Date 45/59 with orange focus'},'session':CFG['session'],'url':c['url'],'tab':tabs[0],'action_commands':['python3 operate.py reject_capture','python3 operate.py cancel_A','python3 operate.py accept_capture','python3 operate.py confirm_B','python3 cleanup.py'],'failures':'End and cleanup then FAILED; never rerun','model_received_at':'unknown','model_review_completed_at':'unknown',**stamp()})
print(json.dumps({'status':'prepared','screenshot_path':str(HERE/'prepared-page.png'),'state':ready,'session':CFG['session']}))
