#!/usr/bin/env python3
"""One arm -> one real fake-MENU button -> frozen bounded capture; NO confirm."""
import datetime,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;D=HERE.parent
c=json.loads((HERE/'fixture.json').read_text());events=[]
def stamp(label):
    events.append({'stage':label,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_monotonic':time.monotonic()})
    (HERE/'operator-capture-timeline.json').write_text(json.dumps(events,indent=2)+'\n')
def run(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
with (HERE/'once-only-arm-marker').open('x') as f:f.write('No rehearsal retry allowed\n')
stamp('capture_tool_command_enter')
stamp('arm_CLI_enter')
arm=json.loads(run(['python3','-B',str(D/'interaction-deadline-helper/deadline_cli.py'),'arm','--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',c['nonce']]))
(HERE/'deadline-arm.json').write_text(json.dumps(arm,indent=2)+'\n')
assert arm['deadline_ms']==20000 and arm['current']['nonce']==c['nonce'] and arm['current']['state']=='armed'
assert arm['current']['due_ms']-arm['current']['armed_ms']==20000
stamp('arm_CLI_return_verified')
stamp('real_fake_MENU_click_enter')
(HERE/'fake-MENU-click.txt').write_text(run(['agent-browser','--session',c['session'],'click','button[data-key="427"]']))
stamp('real_fake_MENU_click_return')
stamp('bounded_capture_CLI_enter')
p=subprocess.run(['python3','-B',str(D/'interaction-bounded-capture-helper/bounded_capture_cli.py'),'--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',c['nonce'],'--evidence-dir',str(HERE/'menu-capture-01')],capture_output=True,text=True,timeout=20)
(HERE/'bounded-capture-stdout.json').write_text(p.stdout)
stamp('bounded_capture_CLI_return')
r=json.loads(p.stdout)
stamp('tool_image_return_preparation_boundary')
print(json.dumps({'capture_status':r['status'],'screenshot_path':r.get('screenshot_path'),'screenshot_file_sha256':r.get('screenshot_file_sha256'),'firmware_png_sha256':r.get('before_eval',{}).get('before',{}).get('png_sha256'),'capture_elapsed_ms':r.get('host_elapsed_ms'),'return_boundary':events[-1]}))
