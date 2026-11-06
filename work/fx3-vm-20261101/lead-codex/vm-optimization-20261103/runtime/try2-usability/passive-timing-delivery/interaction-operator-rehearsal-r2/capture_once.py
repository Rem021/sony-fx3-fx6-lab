#!/usr/bin/env python3
"""ONE arm, ONE fake-MENU click, read-only capture. Never confirm; fail nonzero."""
import datetime,json,subprocess,time
from pathlib import Path
from capture_validation import validate_capture
from dependency_gate import verify
H=Path(__file__).resolve().parent;D=H.parent
events=[]
def stamp(label):
    events.append({'stage':label,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_monotonic':time.monotonic()})
    (H/'operator-capture-timeline.json').write_text(json.dumps(events,indent=2)+'\n')
def run(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def main():
    verification=verify() # Missing coordinator release refuses BEFORE arm.
    (H/'DEPENDENCY-VERIFICATION.json').write_text(json.dumps(verification,indent=2)+'\n')
    c=json.loads((H/'fixture.json').read_text())
    evidence=H/'menu-capture-01'
    if evidence.exists() or evidence.is_symlink():raise ValueError('exclusive capture directory already exists')
    with (H/'once-only-arm-marker').open('x') as f:f.write('No rehearsal retry allowed\n')
    stamp('capture_command_enter')
    stamp('arm_CLI_enter')
    arm=json.loads(run(['python3','-B',str(D/'interaction-deadline-helper/deadline_cli.py'),'arm','--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',c['nonce']]))
    (H/'deadline-arm.json').write_text(json.dumps(arm,indent=2)+'\n')
    assert arm['deadline_ms']==20000 and arm['current']['nonce']==c['nonce'] and arm['current']['state']=='armed'
    assert arm['current']['due_ms']-arm['current']['armed_ms']==20000
    stamp('arm_CLI_return_verified')
    stamp('real_fake_MENU_click_enter')
    (H/'fake-MENU-click.txt').write_text(run(['agent-browser','--session',c['session'],'click','button[data-key="427"]']))
    stamp('real_fake_MENU_click_return')
    stamp('bounded_capture_CLI_enter')
    p=subprocess.run(['python3','-B',str(D/'interaction-bounded-capture-helper-r2/bounded_capture_cli.py'),'--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',c['nonce'],'--evidence-dir',str(evidence)],capture_output=True,text=True,timeout=20)
    stamp('bounded_capture_CLI_return')
    (H/'bounded-capture-process.json').write_text(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n')
    result=validate_capture(p.returncode,p.stdout,evidence)
    stamp('validated_tool_image_return_preparation_boundary')
    result['return_boundary']=events[-1]
    (H/'validated-image-return.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    try:r=main()
    except Exception as e:
        stamp('capture_failed_return_boundary')
        r={'status':'capture_failed','reason':str(e),'validated_new_screenshot':False}
        (H/'capture-failure.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps(r),flush=True);raise SystemExit(2)
    print(json.dumps(r),flush=True)
