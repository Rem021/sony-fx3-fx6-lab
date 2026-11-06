#!/usr/bin/env python3
"""Default-disabled HOST_STOP_ONLY_OBSERVATION candidate; no guest control/write."""
import argparse,sys
from pathlib import Path
TOKEN='APPROVE_GRMREAL46_TWO_KEYS_STOP_ONLY'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--approved-token');ap.add_argument('--new-run-approval',action='store_true');ap.add_argument('--run-root',type=Path)
 a=ap.parse_args()
 if a.approved_token is None:print('DISABLED: HOST_STOP_ONLY_OBSERVATION default-disabled; no VM started');return 2
 if a.approved_token!=TOKEN or not a.new_run_approval or not a.run_root:print('DENIED: stop-only token + separate --new-run-approval + fresh --run-root required');return 2
 print('READY_FOR_REVIEW: stop-only mode wired; no guest restore/inherited callback; execution requires reviewed deps and separate authorization')
 return 3
if __name__=='__main__':sys.exit(main())
