#!/usr/bin/env python3
"""Default-disabled isolated framed-map observer entry.

The actual HostRunner is the frozen r6 one; this adapter only binds the new
CPIO/hash and the framed provider.  No QEMU/guest is started here.
"""
import argparse,json,sys
from pathlib import Path
TOKEN='APPROVE_FX6_FRAMED_MAP_OBSERVER_20261106'
NEW_CPIO_SHA='9d4f255b0a3995b0e056e210ae4d27c8129e2c853b35904a688b6ffe149529ae'
def main(argv=None,runner_factory=None,deps_factory=None):
 ap=argparse.ArgumentParser();ap.add_argument('--approved-token');ap.add_argument('--new-run-approval',action='store_true');ap.add_argument('--run-root',type=Path);a=ap.parse_args(argv)
 if a.approved_token is None:print('DISABLED: framed observer default-disabled; no VM started');return 2
 if a.approved_token!=TOKEN:print('DENIED: wrong framed token');return 2
 if not a.new_run_approval:print('DENIED: --new-run-approval required');return 2
 if not a.run_root:print('DENIED: fresh --run-root required');return 2
 if runner_factory is None:
  from live_runner import build_runner as runner_factory
 try:
  runner=runner_factory(a.run_root);res=runner.run()
  ok=(res.get('two_keys_observed') is True and res.get('host_cleanup_complete') is True and res.get('input_unchanged_after') is True and res.get('postflight_error') is None and res.get('verification_failed') is False and res.get('guest_restore_status')=='unknown_not_attempted' and res.get('boot_menu_passed') is False)
  print(json.dumps({'status':'SUCCESS' if ok else 'FAILED','two_keys_observed':res.get('two_keys_observed'),'host_cleanup_complete':res.get('host_cleanup_complete'),'input_unchanged_after':res.get('input_unchanged_after'),'postflight_error':res.get('postflight_error'),'verification_failed':res.get('verification_failed'),'guest_restore_status':res.get('guest_restore_status'),'boot_menu_passed':False,'receipt':res.get('receipt') or res.get('receipt_path') or str(a.run_root/'receipt.json')},indent=2))
  return 0 if ok else 1
 except Exception as e:print('FRAMED_ENTRY_ERROR',repr(e));return 1

if __name__=='__main__':sys.exit(main())
