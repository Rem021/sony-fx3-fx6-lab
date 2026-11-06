#!/usr/bin/env python3
"""Compile three isolated guest timestamp source copies; do not package or run."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
TOP = HERE.parents[4]
TRY2 = HERE.parent
HELPERS = TOP / 'menu-repair-01/runtime/helpers'
SOURCE_RECEIPT = json.loads((HERE / 'passive-timing-next/source-receipt.json').read_text())
assert SOURCE_RECEIPT['status'] == 'source_only_not_build_or_guest_validated'
CONFIG = {
    'rm': (TRY2 / 'src/guest-build.json',
           '6acb0e52e610cb0d13721f38fcf1c7c27b0e5a48e687d7a4feda5fde9f9bcd14'),
    'ap': (HELPERS / 'fx3-preset-context-v6-save102-build.json',
           'eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170'),
    'osd': (HELPERS / 'fx3-osd-headless-v7-observe102-build.json',
            '816bbf9019ff422c2e24ca5a601a41dc144fa82e7baf39a563d638a55a841dbb'),
}
OUT = HERE / 'passive-timing-next/build'
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

rows = []
for row in SOURCE_RECEIPT['rows']:
    kind = row['kind']
    recipe, original_so_sha = CONFIG[kind]
    args = json.loads(recipe.read_text())['args']
    assert sha(row['candidate_source']) == row['candidate_sha256']
    original_c = row['source']
    assert args.count(original_c) == 1
    original_so = args[-1]
    assert sha(original_so) == original_so_sha
    target = OUT / (kind + '-timing.so')
    args = [str(target) if arg == original_so else row['candidate_source'] if arg == original_c else arg
            for arg in args]
    args[args.index(row['candidate_source']):args.index(row['candidate_source'])] = ['-I', str(Path(original_c).parent)]
    result = subprocess.run(args, capture_output=True, text=True)
    log = OUT / (kind + '-compile.log')
    log.write_text(result.stdout + result.stderr)
    item = {'kind': kind, 'recipe': str(recipe), 'recipe_sha256': sha(recipe),
            'original_source_sha256': row['source_sha256'], 'original_so_sha256': original_so_sha,
            'candidate_source_sha256': row['candidate_sha256'], 'output': str(target),
            'compiler_exit': result.returncode, 'compiler_log': str(log),
            'output_sha256': sha(target) if result.returncode == 0 and target.is_file() else None}
    rows.append(item)
    if result.returncode:
        break
receipt = {'scope': 'offline shared objects only; no CPIO, DTB, QEMU, original files or seed changed',
           'rows': rows, 'all_compiled': len(rows) == 3 and all(x['compiler_exit'] == 0 for x in rows),
           'runtime_validated': False}
(HERE / 'passive-timing-next/build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert receipt['all_compiled'], rows[-1]
print(json.dumps([{'kind': x['kind'], 'output_sha256': x['output_sha256']}
                  for x in rows], indent=2))
