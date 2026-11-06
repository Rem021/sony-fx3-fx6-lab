#!/usr/bin/env python3
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'host'))
import run_candidate_v2 as E

GOOD = {'two_keys_observed': True, 'host_cleanup_complete': True, 'input_unchanged_after': True,
        'postflight_error': None, 'verification_failed': False,
        'guest_restore_status': 'unknown_not_attempted', 'boot_menu_passed': False}
checks = []

def check(name, fn):
    fn()
    checks.append(name)
    print('PASS', name)

class R:
    def __init__(self, out): self.out = out
    def run(self): return self.out

def test_gates():
    calls = []
    def rf(root):
        calls.append(root)
        return R(GOOD)
    rf.__offline_fake__ = True
    def real_like(root):
        calls.append(root)
        return R(GOOD)
    base = ['--approved-token', E.TOKEN, '--new-run-approval', '--run-root', '/tmp/x']
    assert E.main([], rf) == 2 and not calls
    assert E.main(['--approved-token', 'WRONG', '--new-run-approval', '--run-root', '/tmp/x'], rf) == 2 and not calls
    assert E.main(['--approved-token', E.TOKEN, '--run-root', '/tmp/x'], rf) == 2 and not calls
    # valid token + flag but no explicit offline fake: hard technical block
    assert E.main(base) == 3 and not calls
    assert E.main(base, rf) == 3 and not calls
    assert E.main(base, real_like, allow_offline_fake=True) == 3 and not calls
    # explicit, marked offline fake injection is the only executable path
    assert E.main(base, rf, allow_offline_fake=True) == 0 and len(calls) == 1
check('entry_default_disabled_and_hard_admission_block', test_gates)

def test_failure_gate():
    bad = dict(GOOD); bad['two_keys_observed'] = False; bad['verification_failed'] = True
    calls = []
    def rf(root):
        calls.append(root)
        return R(bad)
    rf.__offline_fake__ = True
    base = ['--approved-token', E.TOKEN, '--new-run-approval', '--run-root', '/tmp/x']
    assert E.main(base, rf, allow_offline_fake=True) == 1 and len(calls) == 1
check('entry_nonzero_on_failed_result', test_failure_gate)

out = {'schema': 'fx6-map-collector-shortread-entry-gates-v1', 'status': 'PASS',
       'tests': len(checks), 'cases': checks}
(HERE / 'receipts/entry-gates.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
