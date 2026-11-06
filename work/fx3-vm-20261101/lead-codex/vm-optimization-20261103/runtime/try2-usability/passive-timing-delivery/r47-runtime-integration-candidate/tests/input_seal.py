#!/usr/bin/env python3
"""r47 read-only input seal before/after final validation.

All listed inputs are old r44/r45/r46/r42 evidence or frozen source; none is written.
Usage: python3 tests/input_seal.py before|after
"""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
DEL = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery'
R44 = DEL / 'r44-review-budget-candidate'
R46 = DEL / 'r46-end-and-reopen-candidate'
R42 = DEL / 'r42-command-timing-package'
FROZEN = DEL / 'v25-r21-recovery-integration'
EVID = R44 / 'run-inputs/r45-vm-r45vm0323'
RUN45 = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/v44review-n64-r44-6583e25e'
HERE = Path(__file__).resolve().parents[1]
CALL1 = EVID / 'cleanup-calls/4302ff41-653d-4ae5-9b79-f713120ab9e2'
CALL2 = EVID / 'cleanup-calls/0687a34f-8dcd-4d62-b4a0-b1c0037830b1'
STEP8 = EVID / 'step-08-attempt-08'

INPUTS = [
    DEL / 'r46-coordinator-final-review.json',
    R44 / 'SOURCE-FREEZE.json', R44 / 'CORE-SOURCE-FREEZE.json', R44 / 'PAGE-IDENTITY.json',
    R44 / 'runtime-wrapper/cleanup.py', R44 / 'runtime-wrapper/cleanup_evidence.py',
    R44 / 'runtime-wrapper/common.py',
    R44 / 'trial_web_r24_review_snapshot.py', R44 / 'run_trial_r24_review_snapshot.py',
    R44 / 'r35_package_selection.py', R44 / 'prepare_run.py',
    R44 / 'operator-helpers/deadline.js', R44 / 'operator-helpers/recovery_readonly.js',
    R44 / 'operator-helpers/recovery_cancel.js', R44 / 'operator-helpers/planned_navigation_click.py',
    FROZEN / 'trial_web_v22_navigation_review.py',
    R46 / 'SHA256SUMS', R46 / 'runtime-wrapper/cleanup.py', R46 / 'runtime-wrapper/cleanup_evidence.py',
    R46 / 'page/PAGE-script-r46.txt', R46 / 'page/PAGE-IDENTITY-r46.json',
    R46 / 'DIFF-cleanup.patch', R46 / 'DIFF-page.patch', R46 / 'REPORT.md',
    R42 / 'candidate.json', R42 / 'guest.cpio',
    EVID / 'SHA256SUMS', EVID / 'NATIVE-SHA256SUMS', EVID / 'RESULT.json',
    EVID / 'RESOURCE-AUDIT.json', EVID / 'APPROVAL.json', EVID / 'CLEANUP.json',
    CALL1 / 'body-result.json', CALL1 / 'ENDED-STATE.json', CALL1 / 'ALARM-DISPOSITION.json',
    CALL1 / 'dispose-not-invoked.json', CALL1 / 'result.json', CALL1 / 'MANIFEST.json',
    CALL2 / 'result.json',
    STEP8 / 'click-receipt.json', STEP8 / 'outcome.json', STEP8 / 'binding.json',
    STEP8 / 'recovery-review/observation-result.json',
    EVID / 'step-08-attempt-08-click-process.json',
    EVID / 'step-08-attempt-08-attributed-outcome-process.json',
    EVID / 'step-08-attempt-08-recovery-capture-process.json',
    RUN45 / 'trial-session.json', RUN45 / 'receipt.json', RUN45 / 'trial-web-final-receipt.json',
    RUN45 / 'resource-guard-receipt.json', RUN45 / 'command.json',
]


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest(manifest_path, cwd):
    p = subprocess.run(['shasum', '-a', '256', '-c', str(manifest_path)], cwd=cwd,
                       text=True, capture_output=True)
    lines = p.stdout.splitlines()
    return {'manifest': str(manifest_path), 'cwd': str(cwd), 'returncode': p.returncode,
            'ok': sum(1 for x in lines if x.endswith(': OK')),
            'failed': sum(1 for x in lines if ': FAILED' in x), 'tail': lines[-3:]}


def verify_freeze(freeze, base):
    d = json.loads(Path(freeze).read_text())
    bad = [rel for rel, h in d.items() if sha(Path(base) / rel) != h]
    return {'freeze': str(freeze), 'members': len(d), 'mismatches': bad}


def main(phase):
    assert phase in ('before', 'after')
    rows = []
    missing = []
    for p in INPUTS:
        if not p.is_file():
            missing.append(str(p))
            continue
        st = p.stat()
        rows.append({'path': str(p), 'sha256': sha(p), 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns})
    checks = {
        'r44_source43': verify_freeze(R44 / 'SOURCE-FREEZE.json', R44),
        'r44_core38': verify_freeze(R44 / 'CORE-SOURCE-FREEZE.json', R44),
        'r46_manifest_32': manifest(R46 / 'SHA256SUMS', R46),
        'r45_manifest_554': manifest(EVID / 'SHA256SUMS', EVID),
        'r45_manifest_150': manifest(EVID / 'NATIVE-SHA256SUMS', RUN45),
        'r42_candidate': sha(R42 / 'candidate.json'),
        'r42_cpio': sha(R42 / 'guest.cpio'),
        'r46_manifest_self': sha(R46 / 'SHA256SUMS'),
        'r46_cleanup': sha(R46 / 'runtime-wrapper/cleanup.py'),
        'r46_evidence': sha(R46 / 'runtime-wrapper/cleanup_evidence.py'),
        'r46_page_canonical': sha(R46 / 'page/PAGE-script-r46.txt'),
        'r44_source_sha': sha(R44 / 'SOURCE-FREEZE.json'),
        'r44_core_sha': sha(R44 / 'CORE-SOURCE-FREEZE.json'),
    }
    assert not missing, missing
    assert checks['r44_source43']['members'] == 43 and not checks['r44_source43']['mismatches']
    assert checks['r44_core38']['members'] == 38 and not checks['r44_core38']['mismatches']
    assert checks['r46_manifest_32']['ok'] == 32 and checks['r46_manifest_32']['returncode'] == 0
    assert checks['r46_manifest_self'] == '46fec31b6c727803e05937f38a23050dee70cae6bf01934e5545ec9201b8fa96'
    assert checks['r46_cleanup'] == 'ed3edbb402529acfa84a6fb18ce96720b48cb7b7c1edc1cbc622da9c92b7a1cb'
    assert checks['r46_evidence'] == 'b9c511e2c4ecf1ff24a0446a6a462dce86776b58ac983c73db12f811261a00dc'
    assert checks['r46_page_canonical'] == 'f9a4287834015ab1f82dc0e9719437b755d7643b5f96f4cc9548199f06725caf'
    assert checks['r44_source_sha'] == '3ab27924f456209af961412b876cefa9d23b7f0230b10bc160103a8ef58d995c'
    assert checks['r44_core_sha'] == 'b9d92bc251fb6da2577af7d7f50c2b646db9797000913b747327636c2e3999f1'
    assert checks['r42_candidate'] == '857c2b7aed207ca2351029a5089741989b8fbfd4aa6feeed424ab0a4e4a11806'
    assert checks['r42_cpio'] == '59c5850a4a367ddf469aa2c9f774e0808e3fd6632b9c566323e1a07592a03c63'
    value = {
        'schema': 'fx3-r47-input-seal-v1', 'phase': phase,
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'volume_uuid': 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B',
        'non_git_root': True,
        'coverage_note': 'Old r44/r45/r46/r42 inputs are read-only. Authoritative r44 SOURCE/CORE, r46 32-item '
                         'manifest and r46 code/page hashes were verified at first read before candidate writes; '
                         'this before/after seal covers the final validation window and records no content change.',
        'input_count': len(rows), 'inputs': rows, 'missing': missing, 'manifest_checks': checks,
    }
    out = HERE / 'receipts' / ('input-seal-' + phase + '.json')
    out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'phase': phase, 'inputs': len(rows), 'missing': missing,
                      'r46_32_ok': checks['r46_manifest_32']['ok'],
                      'r45_554_ok': checks['r45_manifest_554']['ok'],
                      'r45_150_ok': checks['r45_manifest_150']['ok'], 'out': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
