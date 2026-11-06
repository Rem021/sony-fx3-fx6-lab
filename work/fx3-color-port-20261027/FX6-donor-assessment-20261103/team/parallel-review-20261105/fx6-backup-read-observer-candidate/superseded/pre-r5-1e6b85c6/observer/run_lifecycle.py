#!/usr/bin/env python3
"""Default-disabled execution entry.

The real launch path is present for review but is NOT invoked during host
preparation.  It requires both an explicit token and a separate current-run
approval flag; the old token is not a run authorization.
"""
import argparse,json,sys,tempfile
from pathlib import Path
TOKEN='APPROVE_GRMREAL46_TWO_KEYS_0214_0218'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--approved-token');ap.add_argument('--new-run-approval',action='store_true');ap.add_argument('--run-root',type=Path)
 a=ap.parse_args()
 if a.approved_token is None:print('DISABLED: execution adapter default-disabled; no VM will be started');return 2
 if a.approved_token!=TOKEN or not a.new_run_approval:print('DENIED: explicit token and separate --new-run-approval required');return 2
 if not a.run_root:print('DENIED: fresh private --run-root required');return 2
 # This branch is intentionally not exercised in host preparation; it requires
 # an explicit token AND separate current-run approval.
 from host_runner import HostRunner,real_deps
 out=HostRunner(real_deps(a.run_root)).run()
 print(json.dumps(out,ensure_ascii=False,indent=2))
 return 0 if out.get('clean') else 1
if __name__=='__main__':sys.exit(main())
