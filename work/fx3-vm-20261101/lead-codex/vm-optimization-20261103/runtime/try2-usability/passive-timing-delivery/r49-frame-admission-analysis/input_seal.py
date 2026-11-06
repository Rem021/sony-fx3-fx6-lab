#!/usr/bin/env python3
import hashlib,json,subprocess,sys
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
R48=DEL/'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'
R47=DEL/'r47-runtime-integration-candidate'
FILES=[DEL/'r48-coordinator-final-review.json',DEL/'r48-user-approval.json',DEL/'r48-dispatch-receipt.json',
 R48/'REPORT.md',R48/'RESULT.json',R48/'SHA256SUMS',R48/'FAILURE.json',R48/'ledger.json',
 R48/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/traffic.har',
 R48/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/result.json',
 R48/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/proof.json',
 R48/'CLEANUP-AUDIT.json',R48/'INPUT-HASH-COMPARE.json',
 R48/'step-01-attempt-01/click-receipt.json',R48/'step-01-attempt-01/outcome.json',R48/'step-01-attempt-01/identity.json',
 R48/'step-01-attempt-02/click-receipt.json',R48/'step-01-attempt-02/outcome.json',R48/'step-01-attempt-02/identity.json',
 R48/'initial-standby/current.png',R48/'step-01-attempt-01/recovery-review/observation.png',R48/'step-01-attempt-01/recovery-cancel/observation/observation.png',
 R48/'FIRST-FRAME-CLOCK.json',R48/'FIRST-FRAME-PASS.json',R48/'runtime.json',R48/'ACTUAL-RUNNING-ARGV.json',
 R47/'PAGE-IDENTITY.json',R47/'receipts/final-canonical-script.txt',R47/'receipts/final-served-script.txt',
 R47/'operator-helpers/planned_navigation_click.js',R47/'tests/page_runtime_test.cjs']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[]
 for p in FILES:
  if not p.is_file():raise SystemExit('missing '+str(p))
  st=p.stat(); rows.append({'path':str(p),'sha256':h(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns})
 v={'schema':'fx3-r49-input-seal-v1','phase':phase,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B',
  'task':'task_1570d1fe8f1b','dispatch':'ctx_8c5041207422','inputs':rows,'count':len(rows),
  'note':'r48/r47 and evidence are read-only; only r49 directory is written'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({'phase':phase,'count':len(rows),'out':str(Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json'))}))
if __name__=='__main__':main(sys.argv[1])
