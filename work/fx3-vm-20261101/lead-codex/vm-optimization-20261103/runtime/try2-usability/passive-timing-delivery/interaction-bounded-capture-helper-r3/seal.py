#!/usr/bin/env python3
"""Freeze this candidate's source, pinned inputs and delivery files."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
base = here.parent
run = base.parent / 'runs/v25gate-n64-r17-c33f8c46'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
sources = ['bounded_capture.js', 'capture_after.js', 'bounded_capture_cli.py',
           'offline_browser_test.py', 'seal.py']
inputs = {
    'r17_PAGE': base / 'v25-r17-tail-receipt/trial_web_v22_navigation_review.py',
    'original_deadline_JS': base / 'interaction-deadline-helper/deadline.js',
    'original_explicit_confirm_JS': base / 'interaction-explicit-confirm-helper/explicit_confirm.js',
    'intermediate_firmware_PNG': run / 'trial-step-01-key-1ab.png',
    'complete_reference_firmware_PNG': run / 'trial-final.png',
    'frozen_v1_capture_JS': base / 'interaction-bounded-capture-helper/bounded_capture.js',
    'failed_operator_rehearsal_report': base / 'interaction-operator-rehearsal/REPORT.md',
    'failed_operator_capture_receipt': base / 'interaction-operator-rehearsal/menu-capture-01/capture-result.json',
    'frozen_r2_capture_JS': base / 'interaction-bounded-capture-helper-r2/bounded_capture.js',
    'r17_runner': base / 'v25-r17-tail-receipt/run_trial_v25_diag_r3.py',
    'r17_visual_classifier': base / 'v25-r17-tail-receipt/pending_visual_v20.py',
    'actual_VM_r2_capture_receipt_at_review': base.parent / 'runs/v25gate-n64-r17-07c897a7/operator-step-01/capture/capture-result.json',
    'actual_VM_failed_run_report': base.parent / 'runs/v25gate-n64-r17-07c897a7/MENU8-RESULT.md',
}
(here / 'SOURCE-FREEZE.json').write_text(json.dumps({
    'scope':'offline bounded first-MENU capture source',
    'files':{name:sha(here / name) for name in sources}},indent=2) + '\n')
(here / 'DEPENDENCIES.json').write_text(json.dumps({name:{'path':str(path),'sha256':sha(path)}
    for name,path in inputs.items()},indent=2) + '\n')
files = sorted(p for p in here.rglob('*') if p.is_file() and '__pycache__' not in p.parts
               and p.name != 'SHA256SUMS')
(here / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(here)}\n' for p in files))
print(f'{len(sources)} sources; {len(inputs)} inputs; {len(files)} delivery files')
