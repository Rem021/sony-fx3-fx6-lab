"""Build a separate host candidate; never launch a guest or replace an entrypoint."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
source = PARENT / 'run_trial_v14_final_receipt.py'
original = source.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '4404ef83cebe00b5f3598faadb020cc06798048a58c3c4c35fb1b6b153a7ad58'
text = original

def replace(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new, 1)

replace('    p = None\n    seq = 0', '''    p = None
    # Receipt defaults must exist before HTTP bind, process spawn, and QMP setup.
    phaseA_capture = None
    phase_exit_hit = False
    shutdown_count_at_ready = 0
    power_off_count_at_ready = 0
    seq = 0''')
replace("'date99_raw_serial_evidence': log_monitor.date99_raw_receipt(),", """'date99_raw_serial_evidence': (log_monitor.date99_raw_receipt()
                   if (run/'serial.log').is_file() else
                   {'available': False, 'reason': 'serial_log_not_created',
                    'literal_present': False, 'semantic_evidence': None}),""")
replace("    trial.update(phase='finished', busy=False, result=", """    if p is None:
        final_message = '启动未完成，模拟器未启动；请查看终端中的原始错误和回执。'
    else:
        final_message = ('试用已结束，模拟器已退出，资源已回收。' if lifecycle_pass else
                         '试用已结束，收尾检查未全部通过，请查看启动终端。')
    trial.update(phase='finished', busy=False, result=""")
replace("message='试用已结束，模拟器已退出，资源已回收。' if lifecycle_pass else '试用已结束，收尾检查未全部通过，请查看启动终端。',", 'message=final_message,')
text = text.replace('web-final-receipt-STATE.json', 'web-startup-receipt-STATE.json')
text = text.replace("'try2finalinternal'", "'try2startupinternal'").replace("'try2final'", "'try2startup'")
target = PARENT / 'run_trial_v15_startup_receipt.py'
compile(text, str(target), 'exec')
target.write_text(text)
(HERE/'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile=source.name, tofile=target.name)))
(HERE/'build-receipt.json').write_text(json.dumps({'source':str(source),'source_sha256':hashlib.sha256(original.encode()).hexdigest(), 'candidate':str(target),'candidate_sha256':hashlib.sha256(text.encode()).hexdigest(), 'scope':'host startup error receipt only; no guest, platform, default entry or web-module changes'}, indent=2)+'\n')
print(target)
