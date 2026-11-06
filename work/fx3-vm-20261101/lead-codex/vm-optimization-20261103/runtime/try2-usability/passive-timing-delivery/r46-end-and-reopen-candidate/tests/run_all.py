#!/usr/bin/env python3
"""Run the complete offline r46 suite and capture raw receipts.

No VM/browser/server/QMP/guest/deployment. Every temp artifact stays under
receipts/raw and is removed after the suite; only raw stdout/stderr and JSON
receipts survive.
"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
RAW = HERE / 'receipts/raw'
RAW.mkdir(parents=True, exist_ok=True)
CASES = [
    ('cleanup-evidence', ['python3', 'tests/cleanup_evidence_test.py']),
    ('page-source', ['python3', 'tests/page_source_check.py']),
    ('page-replay', ['node', 'tests/page_replay_test.cjs']),
    ('input-seal-after', ['python3', 'tests/input_seal.py', 'after']),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    failed = False
    for name, argv in CASES:
        t0 = time.monotonic()
        p = subprocess.run(argv, cwd=HERE, text=True, capture_output=True,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        elapsed = time.monotonic() - t0
        (RAW / (name + '.stdout.txt')).write_text(p.stdout)
        (RAW / (name + '.stderr.txt')).write_text(p.stderr)
        rows.append({'case': name, 'argv': argv, 'returncode': p.returncode,
                     'elapsed_seconds': elapsed, 'stdout': p.stdout[-2000:], 'stderr': p.stderr[-2000:]})
        if p.returncode != 0:
            failed = True
            print('FAIL', name, 'rc', p.returncode)
            print(p.stdout[-2000:])
            print(p.stderr[-2000:])
        else:
            print('PASS', name)
    # Compare the two input seals field by field (path -> sha256).
    before = json.loads((HERE / 'receipts/input-seal-before.json').read_text())
    after = json.loads((HERE / 'receipts/input-seal-after.json').read_text())
    b = {x['path']: x['sha256'] for x in before['inputs']}
    a = {x['path']: x['sha256'] for x in after['inputs']}
    changed = sorted(k for k in set(b) | set(a) if b.get(k) != a.get(k))
    input_unchanged = (not changed and before['input_count'] == after['input_count'] and
                       before['manifest_554']['ok'] == 554 and after['manifest_554']['ok'] == 554 and
                       before['manifest_150_native']['ok'] == 150 and after['manifest_150_native']['ok'] == 150)
    compare = {'schema': 'fx3-r46-input-seal-compare-v1', 'before': 'receipts/input-seal-before.json',
               'after': 'receipts/input-seal-after.json', 'input_count': len(b),
               'changed': changed, 'unchanged': input_unchanged,
               'manifest_554_ok_before': before['manifest_554']['ok'],
               'manifest_554_ok_after': after['manifest_554']['ok'],
               'manifest_150_ok_before': before['manifest_150_native']['ok'],
               'manifest_150_ok_after': after['manifest_150_native']['ok']}
    (HERE / 'receipts/input-seal-compare.json').write_text(json.dumps(compare, ensure_ascii=False, indent=2) + '\n')
    if not input_unchanged:
        failed = True
        print('FAIL input seal changed', changed)
    # Remove only ephemeral test directories; keep raw stdout/stderr.
    for p in RAW.iterdir():
        if p.is_dir() and p.name.startswith(('r46-cleanup-', 'r46-replay-', 'call-', 'r45-', 'r45-orig-', 'r45-first-')):
            shutil.rmtree(p, ignore_errors=True)
    for p in sorted(HERE.rglob('__pycache__'), reverse=True):
        shutil.rmtree(p, ignore_errors=True)
    receipts = {}
    for p in sorted((HERE / 'receipts').glob('*.json')):
        receipts[p.name] = {'sha256': sha(p), 'bytes': p.stat().st_size}
    run = {'schema': 'fx3-r46-test-run-v1', 'offline': True, 'browser': False, 'server': False,
           'network': False, 'VM': False, 'QMP': False, 'guest': False,
           'started_utc': started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'cases': rows, 'cases_failed': sum(1 for r in rows if r['returncode'] != 0),
           'input_seal': compare, 'receipts': receipts, 'passed': not failed}
    out = HERE / 'receipts/test-run.json'
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': not failed, 'cases': len(rows), 'failed': run['cases_failed'],
                      'input_unchanged': input_unchanged, 'receipt': str(out)}))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
