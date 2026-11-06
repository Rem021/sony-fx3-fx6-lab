#!/usr/bin/env python3
"""Freeze one current committed PNG before a human reviews a host-step key."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('--step', type=int, required=True)
args = parser.parse_args()
run = args.run.resolve()
if not run.is_dir() or not run.name.startswith('try2mssallinternal-') or not 1 <= args.step <= 12:
    raise SystemExit('run/step invalid')
if (run / 'receipt.json').exists() or (run / 'INTERNAL_STEP.json').exists():
    raise SystemExit('finished or pending')
before = json.loads((run / 'trial-frame.json').read_text())
png = (run / 'trial-frame.png').read_bytes()
after = json.loads((run / 'trial-frame.json').read_text())
png_sha = hashlib.sha256(png).hexdigest()
if before != after or png_sha != before['PNG_sha256']:
    raise SystemExit('frame changed during freeze; inspect a fresh frame')
stem = f"view-step-{args.step:02d}-seq-{before['sequence']}-{png_sha[:12]}"
png_path, json_path = run / (stem + '.png'), run / (stem + '.json')
with png_path.open('xb') as f:
    f.write(png)
with json_path.open('x') as f:
    json.dump(before, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'frozen_png': str(png_path), 'frame_sequence': before['sequence'],
                  'PNG_sha256': png_sha, 'must_view_this_immutable_file': True}))
