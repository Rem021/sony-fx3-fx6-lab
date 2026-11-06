#!/usr/bin/env python3
"""Host-only reproducible sanitizer build; all artifacts remain beside this file."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

root = Path(__file__).resolve().parent
out = root / 'build'
out.mkdir(exist_ok=True)
cmd = ['clang', '-std=c11', '-O1', '-g', '-fsanitize=address,undefined',
       '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
       str(root / 'fx3-gpe-backend.c'), str(root / 'check-gpe-backend.c'), '-o', str(out / 'check-gpe-backend')]
def run(args, **kwargs):
    p = subprocess.run(args, text=True, capture_output=True, **kwargs)
    return {'command': args, 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
def write(name, value):
    (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
meta = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'host': platform.platform(),
        'source_sha256': {f: hashlib.sha256((root / f).read_bytes()).hexdigest()
                          for f in ['fx3-gpe-backend.c', 'fx3-gpe-backend.h', 'check-gpe-backend.c', 'build_and_test.py']}}
build = run(cmd)
write('build.json', {**meta, 'compiler': run(['clang', '--version']), **build})
if build['exit_code']:
    write('test.json', {'result': 'not_run', 'reason': 'build_failed'})
    print(build['stderr'], file=sys.stderr)
    sys.exit(1)
env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
test = run([str(out / 'check-gpe-backend')], env=env)
try:
    result = json.loads(test['stdout']) if test['exit_code'] == 0 else {'result': 'failed'}
except json.JSONDecodeError:
    result = {'result': 'invalid_test_output'}
write('test.json', {**meta, **test, **result})
print(test['stdout'], end='')
if test['stderr']:
    print(test['stderr'], file=sys.stderr)
sys.exit(0 if test['exit_code'] == 0 and result['result'] == 'passed' else 1)
