#!/usr/bin/env python3
"""Default-disabled HOST_STOP_ONLY_OBSERVATION entry.

No guest control/code/data writes and no inherited callback.  The real launch
is gated by token + separate --new-run-approval + fresh private run root.
Tests inject a fake deps factory; no VM is started here.
"""
import argparse,json,sys
from pathlib import Path
TOKEN='APPROVE_GRMREAL46_TWO_KEYS_STOP_ONLY'
def main(argv=None,deps_factory=None):
 ap=argparse.ArgumentParser();ap.add_argument('--approved-token');ap.add_argument('--new-run-approval',action='store_true');ap.add_argument('--run-root',type=Path)
 a=ap.parse_args(argv)
 if a.approved_token is None:print('DISABLED: HOST_STOP_ONLY_OBSERVATION default-disabled; no VM started');return 2
 if a.approved_token!=TOKEN:print('DENIED: stop-only token mismatch');return 2
 if not a.new_run_approval:print('DENIED: --new-run-approval required');return 2
 if not a.run_root:print('DENIED: fresh --run-root required');return 2
 root=a.run_root
 try:
  if deps_factory is None:
   from host_runner import real_deps as deps_factory
  deps=deps_factory(root);deps['stop_only']=True
  from host_runner import HostRunner
  out=HostRunner(deps).run()
  # HostRunner writes run_root/receipt.json; ensure the stop-only receipt is
  # serialized even if a future adapter returns before doing so.
  rec_path=root/'receipt.json'
  if not rec_path.is_file():rec_path.write_text(json.dumps(out,indent=2)+'\n')
  ok=bool(out.get('two_keys_observed')) and bool(out.get('host_cleanup_complete')) and out.get('guest_restore_status')=='unknown_not_attempted' and out.get('boot_menu_passed') is False
  print(json.dumps({'status':'STOP_ONLY_COMPLETE' if ok else 'STOP_ONLY_INCOMPLETE','two_keys_observed':out.get('two_keys_observed'),'host_cleanup_complete':out.get('host_cleanup_complete'),'guest_restore_status':out.get('guest_restore_status'),'boot_menu_passed':False,'receipt':str(rec_path)},indent=2))
  return 0 if ok else 1
 except BaseException as exc:
  try:
   root.mkdir(parents=True,exist_ok=True);(root/'receipt.json').write_text(json.dumps({'status':'STOP_ONLY_ERROR','error':repr(exc),'two_keys_observed':False,'host_cleanup_complete':False,'guest_restore_status':'unknown_not_attempted','boot_menu_passed':False},indent=2)+'\n')
  except Exception:pass
  print('STOP_ONLY_ERROR: '+repr(exc));return 1
if __name__=='__main__':sys.exit(main())
