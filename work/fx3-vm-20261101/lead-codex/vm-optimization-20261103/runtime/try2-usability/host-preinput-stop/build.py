"""Build an isolated host candidate; preserve all guest and platform artifacts."""
from pathlib import Path
import hashlib
import difflib
import json

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
source = PARENT / 'run_trial_v16_input_deadline.py'
original = source.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '80c0e0f286a166d87f1b5de411fad83f2560d294328036450b13ae47538a8179'
helper = '''def pre_input_stop_reason(monitor, standby_observed, shutdown_count_at_ready):
    """Recheck newly appended native stop events before the next guest write."""
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
assert original.count(old) == 1
text = original.replace('def main():\n', helper + 'def main():\n', 1).replace(old, new, 1)
text = text.replace('web-input-deadline-STATE.json', 'web-preinput-stop-STATE.json')
text = text.replace("'try2inputinternal'", "'try2prestopinternal'").replace("'try2input'", "'try2prestop'")
target = PARENT / 'run_trial_v18_preinput_stop.py'
compile(text, str(target), 'exec')
target.write_text(text)
(HERE / 'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile=source.name, tofile=target.name)))
(HERE / 'build-receipt.json').write_text(json.dumps({'source_sha256': hashlib.sha256(original.encode()).hexdigest(), 'candidate_sha256': hashlib.sha256(text.encode()).hexdigest(), 'scope': 'pre-input host stop check only; no guest or platform changes'}, indent=2) + '\n')
print(target)
