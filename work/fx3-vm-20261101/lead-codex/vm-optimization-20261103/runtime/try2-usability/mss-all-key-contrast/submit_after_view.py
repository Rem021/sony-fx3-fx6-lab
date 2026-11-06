#!/usr/bin/env python3
"""One explicit key request after a human viewed one immutable PNG; no navigation plan."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('run',type=Path)
p.add_argument('--step',type=int,required=True)
p.add_argument('--key',type=lambda s:int(s,0),required=True)
p.add_argument('--viewed-png',type=Path,required=True)
p.add_argument('--page',required=True)
p.add_argument('--reason',required=True)
a=p.parse_args()
r=a.run.resolve()
if not r.is_dir() or not r.name.startswith('try2mssallinternal-keycontrast-') or a.step<1 or a.step>12:raise SystemExit('run/step invalid')
if (a.viewed_png.resolve().parent!=r or not a.viewed_png.is_file() or
        not a.viewed_png.name.startswith(f'view-step-{a.step:02d}-seq-')):
 raise SystemExit('viewed PNG must be a frozen per-step artifact')
if (r/'receipt.json').exists() or (r/'INTERNAL_STEP.json').exists():raise SystemExit('finished or pending')
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
current=json.loads((r/'trial-frame.json').read_text())
viewed=sha(a.viewed_png)
frozen=json.loads(a.viewed_png.with_suffix('.json').read_text())
if (frozen['PNG_sha256']!=viewed or
        sha(r/'trial-frame.png')!=current['PNG_sha256'] or viewed!=current['PNG_sha256']):
 print(json.dumps({'status':'STALE_NO_REQUEST','viewed_png':str(a.viewed_png),'viewed_sha256':viewed,'current_sha256':current['PNG_sha256']}));raise SystemExit(3)
for ext in ('png','json'):shutil.copy2(r/f'trial-frame.{ext}',r/f'internal-observe-{a.step:02d}.{ext}')
observed=json.loads((r/f'internal-observe-{a.step:02d}.json').read_text())
if (observed['PNG_sha256']!=viewed or
        sha(r/f'internal-observe-{a.step:02d}.png')!=viewed):raise SystemExit('snapshot raced; no request')
(r/f'internal-observe-{a.step:02d}-decision.md').write_text('Viewed '+str(a.viewed_png)+' using image tool; frozen_sequence='+str(frozen['sequence'])+' current_sequence='+str(observed['sequence'])+' exact_PNG_SHA256='+viewed+'. '+a.page+' Next: '+a.reason+'\n')
q={'mode':'internal-hoststep-v1','run_id':r.name,'step':a.step,'key':a.key,'hold_ms':100,'observed_sequence':observed['sequence'],'observed_png_sha256':viewed,'observed_page':a.page,'reason':a.reason}
t=r/'INTERNAL_STEP.json.tmp';t.write_text(json.dumps(q,ensure_ascii=False)+'\n');t.replace(r/'INTERNAL_STEP.json')
print(json.dumps({'status':'ONE_REQUEST_SUBMITTED','step':a.step,'key':hex(a.key),'observed_sequence':observed['sequence'],'sha256':viewed}))
