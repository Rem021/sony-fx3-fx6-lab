#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
R49=DEL/'r49-frame-admission-analysis'; R47=DEL/'r47-runtime-integration-candidate'; RUN=R47/'run-inputs/f9c618eedbad'
P=[R49/'REPORT.md',R49/'RESULT.json',R49/'SHA256SUMS',DEL/'r49-coordinator-final-review.json',R49/'DESIGN-MINIMAL-IMPROVEMENT.md',
 R49/'receipts/frame-admission-findings.json',R49/'receipts/command-entry-timing.json',R49/'receipts/startup-observation-audit.json',
 R47/'PAGE-IDENTITY.json',R47/'receipts/final-canonical-script.txt',R47/'receipts/final-served-script.txt',R47/'operator-helpers/planned_navigation_click.js',
 RUN/'REPORT.md',RUN/'RESULT.json',RUN/'SHA256SUMS',RUN/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/traffic.har']
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(phase):
 rows=[]
 for p in P:
  if not p.is_file():raise SystemExit('missing '+str(p))
  rows.append({'path':str(p),'sha256':h(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns})
 v={'schema':'fx3-r50-input-seal-v1','phase':phase,'task':'task_0cce6dde0290','dispatch':'ctx_89f797a305ca','volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','inputs':rows,'count':len(rows),'note':'r47/r48/r49/platform read-only; only r50 written'}
 (Path(__file__).resolve().parent/'receipts'/(phase+'-input-seal.json')).write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({'phase':phase,'count':len(rows)}))
if __name__=='__main__':main(sys.argv[1])
