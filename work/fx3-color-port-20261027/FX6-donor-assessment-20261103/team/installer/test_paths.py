#!/usr/bin/env python3
"""Self-created local fixtures for preflight path boundary; no device input."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import preflight

HERE = Path(__file__).resolve().parent
BASE = json.loads((HERE / 'baseline.json').read_text())['result']
ARGS = {'model':'ILME-FX3', **{c['check'].removesuffix('_sha256'): c['detail']['path']
       for c in BASE['checks'] if c['check'].endswith('_sha256')}}

def run_case(name, candidate, expected_kind):
    args = [sys.executable, str(HERE / 'preflight.py')]
    opts = dict(ARGS, ap=str(candidate))
    for k, v in opts.items(): args += ['--' + k, str(v)]
    process = subprocess.run(args, capture_output=True, text=True)
    d = json.loads(process.stdout)
    ap = next(c for c in d['checks'] if c['check'].startswith('ap_'))
    kind = 'regular_file_hash_mismatch' if ap['check'] == 'ap_sha256' else ap['detail']
    ok = process.returncode == 2 and expected_kind in kind
    return {'case':name,'command':args,'exit_code':process.returncode,
            'ap_check':ap,'expected_kind':expected_kind,'pass':ok}

with tempfile.TemporaryDirectory(prefix='path-fixture-', dir=HERE) as tmp:
    base = Path(tmp)
    regular = base / 'regular.txt'; regular.write_bytes(b'local fixture only\n')
    symlink = base / 'link.txt'; symlink.symlink_to(regular)
    outside = preflight.ROOT / '..' / 'outside-nonexistent-fixture.txt'
    rows = [run_case('legal_project_regular_file', regular, 'regular_file_hash_mismatch'),
            run_case('parent_traversal_outside_root', outside, 'path outside project'),
            run_case('symlink', symlink, 'symlink path is not accepted'),
            run_case('non_regular_directory', base, 'not a regular file')]
print(json.dumps({'schema':'fx3-local-path-regressions-v1', 'invocation':
                  'python3 test_paths.py > path-regressions.json',
                  'fixture':'temporary self-created under installer; removed after test',
                  'cases':rows,'pass':all(x['pass'] for x in rows)},ensure_ascii=False,indent=2))
sys.exit(0 if all(x['pass'] for x in rows) else 1)
