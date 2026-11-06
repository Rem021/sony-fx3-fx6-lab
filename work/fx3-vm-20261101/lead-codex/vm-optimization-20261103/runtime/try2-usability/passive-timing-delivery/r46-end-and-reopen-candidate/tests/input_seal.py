#!/usr/bin/env python3
"""Read-only input seal for r46. No input file is opened for writing.

Usage: python3 tests/input_seal.py before|after
Writes receipts/input-seal-<phase>.json and prints a compact summary.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
DEL = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery'
TRY = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability'
RUN = TRY / 'runs/v44review-n64-r44-6583e25e'
EVID = DEL / 'r44-review-budget-candidate/run-inputs/r45-vm-r45vm0323'
HERE = Path(__file__).resolve().parents[1]
CALL = EVID / 'cleanup-calls/4302ff41-653d-4ae5-9b79-f713120ab9e2'
STEP8 = EVID / 'step-08-attempt-08'

INPUTS = [
    DEL / 'r45-coordinator-final-review.json',
    DEL / 'r46-deepseek-end-and-reopen-task.txt',
    DEL / 'r44-review-budget-candidate/SOURCE-FREEZE.json',
    DEL / 'r44-review-budget-candidate/CORE-SOURCE-FREEZE.json',
    DEL / 'r44-review-budget-candidate/PAGE-IDENTITY.json',
    DEL / 'r44-review-budget-candidate/runtime-wrapper/cleanup.py',
    DEL / 'r44-review-budget-candidate/runtime-wrapper/cleanup_evidence.py',
    DEL / 'r44-review-budget-candidate/runtime-wrapper/common.py',
    DEL / 'r44-review-budget-candidate/operator-helpers/deadline.js',
    DEL / 'r44-review-budget-candidate/operator-helpers/recovery_readonly.js',
    DEL / 'r44-review-budget-candidate/operator-helpers/planned_navigation_click.js',
    DEL / 'r44-review-budget-candidate/operator-helpers/planned_navigation_click.py',
    DEL / 'r44-review-budget-candidate/tests/fixtures/PAGE-script.txt',
    DEL / 'v25-r21-recovery-integration/trial_web_v22_navigation_review.py',
    EVID / 'SHA256SUMS',
    EVID / 'NATIVE-SHA256SUMS',
    EVID / 'APPROVAL.json',
    EVID / 'RESULT.json',
    EVID / 'RESOURCE-AUDIT.json',
    EVID / 'FAILURE.json',
    EVID / 'CLEANUP.json',
    EVID / 'CLEANUP-FIRST.json',
    EVID / 'current-attempt.json',
    CALL / 'body-result.json',
    CALL / 'ENDED-STATE.json',
    CALL / 'ALARM-DISPOSITION.json',
    CALL / 'dispose-not-invoked.json',
    CALL / 'deadline-after-End.json',
    CALL / 'result.json',
    CALL / 'MANIFEST.json',
    CALL / 'traffic.har',
    CALL / 'browser-before-close-process.json',
    CALL / 'browser-after-close-process.json',
    CALL / 'End-original-button-process.json',
    CALL / 'ended-state-process.json',
    CALL / 'ended-page-process.json',
    CALL / 'HAR-stop-process.json',
    CALL / 'browser-close-process.json',
    STEP8 / 'click-receipt.json',
    STEP8 / 'outcome.json',
    STEP8 / 'identity.json',
    STEP8 / 'binding.json',
    STEP8 / 'recovery-review/observation-result.json',
    EVID / 'step-08-attempt-08-click-process.json',
    EVID / 'step-08-attempt-08-attributed-outcome-process.json',
    EVID / 'step-08-attempt-08-recovery-capture-process.json',
    RUN / 'trial-session.json',
    RUN / 'receipt.json',
    RUN / 'trial-web-final-receipt.json',
    RUN / 'resource-guard-receipt.json',
    RUN / 'command.json',
]


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest_check(manifest, cwd):
    p = subprocess.run(['shasum', '-a', '256', '-c', str(manifest)], cwd=cwd,
                       text=True, capture_output=True)
    lines = p.stdout.splitlines()
    ok = sum(1 for x in lines if x.endswith(': OK'))
    failed = sum(1 for x in lines if ': FAILED' in x)
    missing = sum(1 for x in lines if 'FAILED open or read' in x)
    return {'manifest': str(manifest), 'cwd': str(cwd), 'returncode': p.returncode,
            'ok': ok, 'failed': failed, 'missing': missing,
            'tail': lines[-3:] if lines else [], 'stderr_tail': p.stderr.splitlines()[-3:]}


def main(phase):
    assert phase in ('before', 'after')
    rows = []
    missing = []
    for p in INPUTS:
        if not p.exists():
            missing.append(str(p))
            continue
        st = p.stat()
        rows.append({'path': str(p), 'sha256': sha(p), 'bytes': st.st_size,
                     'mtime_ns': st.st_mtime_ns})
    task_manifest = manifest_check(EVID / 'SHA256SUMS', EVID)
    native_manifest = manifest_check(EVID / 'NATIVE-SHA256SUMS', RUN)
    value = {
        'schema': 'fx3-r46-input-seal-v1',
        'phase': phase,
        'volume_uuid': 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B',
        'root': str(ROOT),
        'non_git_root': True,
        'scope': 'r45 review/task, r44 source+cleanup+page+operators, r45 554/150 manifests, '
                 'r45 cleanup/step8/resource evidence, 150-native run receipts',
        'inputs': rows,
        'input_count': len(rows),
        'missing': missing,
        'manifest_554': task_manifest,
        'manifest_150_native': native_manifest,
        'manifest_self_sha256': {
            'SHA256SUMS': sha(EVID / 'SHA256SUMS'),
            'NATIVE-SHA256SUMS': sha(EVID / 'NATIVE-SHA256SUMS'),
        },
    }
    out = HERE / 'receipts' / ('input-seal-' + phase + '.json')
    out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'phase': phase, 'inputs': len(rows), 'missing': missing,
                      'manifest_554_ok': task_manifest['ok'],
                      'manifest_150_ok': native_manifest['ok'],
                      'out': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
