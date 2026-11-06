#!/usr/bin/env python3
"""Rebuild an isolated v19 host candidate; no guest or VM execution."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'run_trial_v17_mss_key_contrast.py'
TARGET = HERE / 'run_trial_v19_mss_key_contrast_preinput_stop.py'
original = SOURCE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '4918eaec03f512656b0170558c4491e9c3fdccc96b9ffc93b436fd9c277766c7'
helper = '''def pre_input_stop_reason(monitor, standby_observed, shutdown_count_at_ready):
    """Recheck newly appended native stop events before any guest write."""
    if monitor.failure:
        return monitor.failure
    if monitor.native_power_off_events:
        return 'native_model_power_off_observed: ' + monitor.native_power_off_events[-1]
    if standby_observed and len(monitor.native_shutdown_events) > shutdown_count_at_ready:
        return 'native_shutdown_after_ready_without_user_power_key: ' + monitor.native_shutdown_events[-1]
    return None


'''
old = '''                    log_monitor.poll()
                    if log_monitor.failure:
                        early_stop_reason = log_monitor.failure
                        trial.fail(early_stop_reason)
                        break
                    key = proposed['key']'''
new = '''                    log_monitor.poll()
                    pending_stop = pre_input_stop_reason(
                        log_monitor, phaseA_capture is not None, shutdown_count_at_ready)
                    if pending_stop:
                        early_stop_reason = pending_stop
                        trial.fail(early_stop_reason)
                        break
                    key = proposed['key']'''
assert original.count(old) == 1 and original.count('def main():\n') == 1
text = original.replace('def main():\n', helper + 'def main():\n', 1).replace(old, new, 1)
text = text.replace("parent / 'STATE.json'", "parent / 'STATE-v19.json'")
text = text.replace("parent / 'STATE.json.tmp'", "parent / 'STATE-v19.json.tmp'")
text = text.replace("'try2mssallinternal-keycontrast'", "'try2mssallinternal-keycontrast-v19'")
assert text.count("'STATE-v19.json'") == 1 and text.count("'STATE-v19.json.tmp'") == 1
compile(text, str(TARGET), 'exec')
TARGET.write_text(text)
(HERE / 'host-v19.diff').write_text(''.join(difflib.unified_diff(
    original.splitlines(True), text.splitlines(True), fromfile=SOURCE.name, tofile=TARGET.name)))
(HERE / 'host-v19-build-receipt.json').write_text(json.dumps({
    'source': str(SOURCE), 'source_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'candidate': str(TARGET), 'candidate_sha256': hashlib.sha256(text.encode()).hexdigest(),
    'coordinator_patch': str(HERE.parent / 'host-preinput-stop/runner.diff'),
    'coordinator_patch_source_sha256': '80c0e0f286a166d87f1b5de411fad83f2560d294328036450b13ae47538a8179',
    'scope': 'host pre-write native stop recheck only; no guest/VM execution',
}, indent=2) + '\n')
print(TARGET)
