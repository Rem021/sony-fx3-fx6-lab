#!/usr/bin/env python3
"""prepare_run.py offline: create self-bound config only; never start browser/runner/QEMU."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
RUN = HERE / 'run-inputs/r47prepare'
shutil.rmtree(RUN, ignore_errors=True)
p = subprocess.run(['python3', '-B', str(HERE / 'prepare_run.py'), '--run-dir', str(RUN),
                    '--task-id', 'task_r47prepare', '--dispatch-id', 'ctx_r47prepare',
                    '--session', 'fx3-deadline-r47prepare'], text=True, capture_output=True)
assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
cfg = json.loads((RUN / 'config.json').read_text())
local = json.loads((RUN / 'LOCAL-SOURCE-FREEZE.json').read_text())
source = json.loads((HERE / 'SOURCE-FREEZE.json').read_text())
assert cfg['candidate_source_root'] == str(HERE)
assert cfg['runner_profile'] == 'r47-runtime-integration-60s'
assert cfg['frozen_root'] == str(HERE.parent / 'v25-r21-recovery-integration')
assert cfg['plan_sha'] == __import__('hashlib').sha256((HERE / 'NAVIGATION-PLAN.json').read_bytes()).hexdigest()
assert len(local) == len(source) == 44
assert local == {str(HERE / rel): h for rel, h in source.items()}
assert (RUN / 'CLI-TEMPLATES.json').is_file() and (RUN / 'ledger.json').is_file()
assert not (RUN / 'runtime.json').exists()
value = {'schema': 'fx3-r47-prepare-only-v1', 'offline': True, 'browser': False, 'server': False,
         'VM': False, 'QMP': False, 'guest': False, 'runner_started': False,
         'run_dir': str(RUN), 'config': cfg, 'local_source_members': len(local),
         'stdout': p.stdout, 'stderr': p.stderr}
(HERE / 'receipts/prepare-only.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'passed': True, 'profile': cfg['runner_profile'], 'members': len(local),
                  'receipt': str(HERE / 'receipts/prepare-only.json')}))
