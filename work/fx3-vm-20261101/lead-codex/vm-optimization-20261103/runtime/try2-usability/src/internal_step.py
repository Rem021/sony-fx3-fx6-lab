#!/usr/bin/env python3
"""Manual one-step evidence helper. Never issues QMP or guest input itself."""
import argparse, hashlib, json, shutil
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run', type=Path)
p.add_argument('action', choices=['observe', 'request'])
p.add_argument('step', type=int)
p.add_argument('--key', type=lambda x: int(x, 0))
p.add_argument('--page')
p.add_argument('--reason')
a = p.parse_args()
run = a.run.resolve(strict=True)
if not run.name.startswith(('try2internal-', 'try2gapinternal-')):
    raise SystemExit('internal run identity mismatch')
base = run / f'internal-observe-{a.step:02d}'
record = json.loads((run/'trial-frame.json').read_text())
png = run/'trial-frame.png'
sha = hashlib.sha256(png.read_bytes()).hexdigest()
if sha != record['PNG_sha256']:
    raise SystemExit('live PNG/record changed during read; retry observation')
if a.action == 'observe':
    if base.with_suffix('.json').exists() or base.with_suffix('.png').exists():
        raise SystemExit('observation exists; do not overwrite')
    shutil.copyfile(png, base.with_suffix('.png'))
    if hashlib.sha256(base.with_suffix('.png').read_bytes()).hexdigest() != sha:
        base.with_suffix('.png').unlink()
        raise SystemExit('live PNG changed during copy; retry observation')
    base.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'PNG': str(base.with_suffix('.png')), 'step': a.step,
                      'sequence': record['sequence'], 'PNG_sha256': sha,
                      'pixel_source_sequence': record['pixel_source_sequence'],
                      'all_zero_pixels': record['all_zero_pixels']}, ensure_ascii=False))
else:
    if not all((a.key is not None, a.page, a.reason)):
        raise SystemExit('key/page/reason required')
    observed = json.loads(base.with_suffix('.json').read_text())
    observed_sha = hashlib.sha256(base.with_suffix('.png').read_bytes()).hexdigest()
    if observed_sha != observed['PNG_sha256'] or observed['sequence'] > record['sequence'] or observed_sha != sha:
        raise SystemExit('reviewed PNG is not the current committed frame; observe and view again')
    if observed.get('all_zero_pixels'):
        raise SystemExit('all-zero frame: stop business input')
    target=run/'INTERNAL_STEP.json'
    if target.exists():
        raise SystemExit('one pending request already exists')
    request={'mode':'internal-hoststep-v1','step':a.step,'key':a.key,'hold_ms':100,
             'observed_page':a.page,'reason':a.reason,
             'observed_sequence':observed['sequence'],'observed_png_sha256':sha,
             'reviewed_png':str(base.with_suffix('.png'))}
    temp=run/'INTERNAL_STEP.json.tmp'
    temp.write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
    temp.replace(target)
    print(json.dumps(request,ensure_ascii=False))
