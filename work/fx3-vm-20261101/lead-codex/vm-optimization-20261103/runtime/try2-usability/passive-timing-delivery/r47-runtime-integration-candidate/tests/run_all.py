#!/usr/bin/env python3
"""Run the complete r47 offline integration suite.

No VM/browser/server/QMP/guest/deployment. All temp artifacts stay under
run-inputs/receipts and are removed after final verification.
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
    ('input-seal-before', ['python3', 'tests/input_seal.py', 'before']),
    ('cleanup-closed-loop', ['python3', 'tests/cleanup_closed_loop_test.py']),
    ('prepare-only', ['python3', 'tests/prepare_only_test.py']),
    ('preflight', ['python3', '-B', 'runtime-wrapper/preflight.py']),
    ('import-only', ['python3', 'tests/import_only_test.py']),
    ('binding-inventory', ['python3', 'tests/binding_inventory_test.py']),
    ('package-pin', ['python3', 'tests/package_pin_test.py']),
    ('page-runtime', ['node', 'tests/page_runtime_test.cjs']),
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
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
        if name == 'preflight':
            env['FX3_NAV_RUN_DIR'] = str(HERE / 'run-inputs/r47-offline-closed-loop')
        p = subprocess.run(argv, cwd=HERE, text=True, capture_output=True, env=env)
        elapsed = time.monotonic() - t0
        (RAW / (name + '.stdout.txt')).write_text(p.stdout)
        (RAW / (name + '.stderr.txt')).write_text(p.stderr)
        rows.append({'case': name, 'argv': argv, 'returncode': p.returncode,
                     'elapsed_seconds': elapsed, 'stdout_tail': p.stdout[-2000:],
                     'stderr_tail': p.stderr[-2000:]})
        if p.returncode != 0:
            failed = True
            print('FAIL', name, 'rc', p.returncode)
            print(p.stdout[-2000:])
            print(p.stderr[-2000:])
        else:
            print('PASS', name)
    before = json.loads((HERE / 'receipts/input-seal-before.json').read_text())
    after = json.loads((HERE / 'receipts/input-seal-after.json').read_text())
    b = {x['path']: x['sha256'] for x in before['inputs']}
    a = {x['path']: x['sha256'] for x in after['inputs']}
    changed = sorted(k for k in set(b) | set(a) if b.get(k) != a.get(k))
    checks = {'r46_32_before': before['manifest_checks']['r46_manifest_32']['ok'],
              'r46_32_after': after['manifest_checks']['r46_manifest_32']['ok'],
              'r45_554_before': before['manifest_checks']['r45_manifest_554']['ok'],
              'r45_554_after': after['manifest_checks']['r45_manifest_554']['ok'],
              'r45_150_before': before['manifest_checks']['r45_manifest_150']['ok'],
              'r45_150_after': after['manifest_checks']['r45_manifest_150']['ok']}
    input_unchanged = (not changed and before['input_count'] == after['input_count'] == 51 and
                       checks['r46_32_before'] == checks['r46_32_after'] == 32 and
                       checks['r45_554_before'] == checks['r45_554_after'] == 554 and
                       checks['r45_150_before'] == checks['r45_150_after'] == 150)
    compare = {'schema': 'fx3-r47-input-seal-compare-v1',
               'before': 'receipts/input-seal-before.json', 'after': 'receipts/input-seal-after.json',
               'input_count': len(b), 'changed': changed, 'unchanged': input_unchanged,
               'manifest_checks': checks,
               'coverage_note': 'old inputs are read-only; hashes are identical across the final validation window'}
    (HERE / 'receipts/input-seal-compare.json').write_text(json.dumps(compare, ensure_ascii=False, indent=2) + '\n')
    if not input_unchanged:
        failed = True
        print('FAIL input seal changed', changed)
    # Remove only ephemeral fake run dirs and bytecode; keep source/receipts/raw logs.
    for rel in ('run-inputs/r47-offline-closed-loop', 'run-inputs/r47prepare'):
        shutil.rmtree(HERE / rel, ignore_errors=True)
    for p in sorted(HERE.rglob('__pycache__'), reverse=True):
        shutil.rmtree(p, ignore_errors=True)
    receipts = {}
    for p in sorted((HERE / 'receipts').glob('*.json')):
        receipts[p.name] = {'sha256': sha(p), 'bytes': p.stat().st_size}
    run = {'schema': 'fx3-r47-test-run-v1', 'offline': True, 'browser': False, 'server': False,
           'network': False, 'VM': False, 'QMP': False, 'guest': False, 'deployment': False,
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
