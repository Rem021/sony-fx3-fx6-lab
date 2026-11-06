#!/usr/bin/env python3
"""Prepare owned browser and production alarm; never arms or confirms."""
import datetime,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
c=json.loads((HERE/'fixture.json').read_text());D=HERE.parent
events=[]
def stamp(label):events.append({'stage':label,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_monotonic':time.monotonic()})
def browser(*args,code=None):
    p=subprocess.run(['agent-browser','--session',c['session'],*args],input=code,capture_output=True,text=True,timeout=15)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def js(code):return json.loads(browser('eval','--stdin',code=code))
def wait(code):
    until=time.monotonic()+8
    while time.monotonic()<until:
        r=js(code)
        if r:return r
        time.sleep(.05)
    raise RuntimeError('preparation state timed out')
stamp('prepare_enter')
browser('open',c['url']);browser('set','viewport','1280','1200')
wait('!!lastStatus?.browser_ready&&!startButton.disabled')
stamp('real_Start_click_enter');browser('click','#start');stamp('real_Start_click_return')
c['launch_id']=wait("lastStatus?.phase==='ready'&&lastStatus?.ready&&shownSHA===lastStatus.frame?.PNG_sha256?lastStatus.launch_request_id:null")
(HERE/'fixture.json').write_text(json.dumps(c,indent=2)+'\n')
stamp('deadline_install_enter')
p=subprocess.run(['python3','-B',str(D/'interaction-deadline-helper/deadline_cli.py'),'install','--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id']],capture_output=True,text=True,timeout=20)
assert p.returncode==0,p.stderr
h=json.loads(p.stdout);assert h['deadline_ms']==20000
(HERE/'deadline-install.json').write_text(p.stdout)
stamp('deadline_install_return')
(HERE/'prepared-snapshot.txt').write_text(browser('snapshot','-i'))
browser('screenshot',str(HERE/'prepared-page.png'))
identity=js('({url:location.href,launch_id:lastStatus.launch_request_id,phase:lastStatus.phase,shownSHA,displayedGeneration,displayed,frame:lastStatus.frame,render_valid:lastStatus.render_valid})')
(HERE/'prepared-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
stamp('prepare_complete')
(HERE/'prepare-timeline.json').write_text(json.dumps(events,indent=2)+'\n')
print(json.dumps({'prepared':True,**c,'identity':identity},indent=2))
