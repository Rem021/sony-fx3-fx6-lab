#!/usr/bin/env python3
"""MANUAL invocation only AFTER agent sees complete screenshot, once, no retries."""
import datetime,json,subprocess,time
from pathlib import Path
H=Path(__file__).resolve().parent;D=H.parent
c=json.loads((H/'fixture.json').read_text())
capture=json.loads((H/'validated-image-return.json').read_text())
assert capture['status']=='qualified_screenshot_for_operator_review' and capture['validated_new_screenshot'] is True
assert not (H/'capture-failure.json').exists()
record={'UTC_enter':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host_monotonic_enter':time.monotonic(),
        'operator_approval':'Agent has just personally viewed the qualified returned image: Setup > Area/Date, orange Area/Date/Time Setting focus, Language English; simulated historical PNG only',
        'model_image_received_UTC':None,'model_semantic_review_finished_UTC':None,'unknown_reason':'No measurable model image reception/review clock exists'}
with (H/'manual-confirm-invocation.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
argv=['python3','-B',str(D/'interaction-explicit-confirm-helper/explicit_confirm_cli.py'),'--session',c['session'],'--url',c['url'],'--launch-id',c['launch_id'],'--nonce',c['nonce'],'--step','1','--png-sha','60e9acccbc4609ac93c2694ae05fe659cd9734f257c1f55c1f763cf28d7e1292','--target','亲看模拟历史完整菜单：Setup > Area/Date；橙色Area/Date/Time Setting焦点；Language English可读','--receipt',str(H/'explicit-confirm-receipt.json')]
record['argv']=argv
p=subprocess.run(argv,capture_output=True,text=True,timeout=20)
record.update(UTC_return=datetime.datetime.now(datetime.timezone.utc).isoformat(),host_monotonic_return=time.monotonic(),exit_code=p.returncode,stderr=p.stderr)
(H/'manual-confirm-invocation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(p.stdout)
raise SystemExit(p.returncode)
