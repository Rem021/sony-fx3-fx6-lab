#!/usr/bin/env python3
"""Entry for the FX3MS2 candidate.

The real runtime path is hard-blocked at code level until technical admission is
explicitly accepted by a separate review.  A valid token/new-run-approval is
not sufficient.  Only an explicitly injected offline fake runner is executable,
which keeps host tests hermetic and prevents an accidental real_deps/QEMU path.
"""
import argparse
import json
import sys
from pathlib import Path

TOKEN = 'APPROVE_FX6_MAP_COLLECTOR_SHORTREAD_20261106'
TECHNICAL_ADMISSION_ACCEPTED = False
BLOCK_REASON = ('technical admission is not accepted: non-atomic FX3MS2 map cannot establish '
                'current executable mapping/PTE permissions at pause; a token cannot replace this gate')


def main(argv=None, runner_factory=None, allow_offline_fake=False):
    ap = argparse.ArgumentParser()
    ap.add_argument('--approved-token')
    ap.add_argument('--new-run-approval', action='store_true')
    ap.add_argument('--run-root', type=Path)
    a = ap.parse_args(argv)
    if a.approved_token is None:
        print('DISABLED: FX3MS2 collector candidate default-disabled; no VM started')
        return 2
    if a.approved_token != TOKEN:
        print('DENIED: wrong FX3MS2 token')
        return 2
    if not a.new_run_approval:
        print('DENIED: --new-run-approval required')
        return 2
    if not a.run_root:
        print('DENIED: fresh --run-root required')
        return 2
    if not (allow_offline_fake and runner_factory is not None and
            getattr(runner_factory, '__offline_fake__', False) is True):
        print('BLOCKED: ' + BLOCK_REASON)
        print('BLOCKED: real runner path disabled; only a marked offline fake runner may be injected')
        return 3
    try:
        runner = runner_factory(a.run_root)
        res = runner.run()
        ok = (res.get('two_keys_observed') is True and res.get('host_cleanup_complete') is True and
              res.get('input_unchanged_after') is True and res.get('postflight_error') is None and
              res.get('verification_failed') is False and
              res.get('guest_restore_status') == 'unknown_not_attempted' and
              res.get('boot_menu_passed') is False)
        print(json.dumps({'status': 'SUCCESS' if ok else 'FAILED',
                          'two_keys_observed': res.get('two_keys_observed'),
                          'host_cleanup_complete': res.get('host_cleanup_complete'),
                          'input_unchanged_after': res.get('input_unchanged_after'),
                          'postflight_error': res.get('postflight_error'),
                          'verification_failed': res.get('verification_failed'),
                          'guest_restore_status': res.get('guest_restore_status'),
                          'boot_menu_passed': False,
                          'first_stop_identity': str(a.run_root / 'first-stop-identity.json'),
                          'receipt': res.get('receipt') or str(a.run_root / 'receipt.json')}, indent=2))
        return 0 if ok else 1
    except Exception as e:
        print('FX3MS2_ENTRY_ERROR', repr(e))
        return 1


if __name__ == '__main__':
    sys.exit(main())
