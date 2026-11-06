"""Build a host-only bounded input-receipt candidate from pinned v15."""
from pathlib import Path
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
source=PARENT/'run_trial_v15_startup_receipt.py'
original=source.read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='b6170379b9105e7e1220572c129dbaf1c90e00460c4146f09a041a3164d62f8e'
helper='''def native_input_deadline_error(command, step, up_seen, both_native_events, now):
    """Bound missing sender AND native-consumer evidence, without resending a key."""
    if command is None or now-command['sent_monotonic'] <= 12:
        return None
    if step not in up_seen:
        return '按键 12 秒内未得到原生 key-up 回执'
    if not both_native_events:
        return '按键 12 秒内原程序按下/抬起接收证据不完整，停止本轮；不会自动重发。'
    return None


'''
assert original.count('def main():\n')==1
text=original.replace('def main():\n',helper+'def main():\n',1)
old="""                if current_command is not None and host_step not in up_seen and time.monotonic()-current_command['sent_monotonic'] > 12:
                    raise RuntimeError('按键 12 秒内未得到原生 key-up 回执')"""
new="""                missing_input_error = native_input_deadline_error(
                    current_command, host_step, up_seen, both_native_events, time.monotonic())
                if missing_input_error:
                    raise RuntimeError(missing_input_error)"""
assert text.count(old)==1
text=text.replace(old,new,1)
text=text.replace('web-startup-receipt-STATE.json','web-input-deadline-STATE.json')
text=text.replace("'try2startupinternal'","'try2inputinternal'").replace("'try2startup'","'try2input'")
target=PARENT/'run_trial_v16_input_deadline.py'
compile(text,str(target),'exec');target.write_text(text)
(HERE/'runner.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=source.name,tofile=target.name)))
(HERE/'build-receipt.json').write_text(json.dumps({'source':str(source),'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'candidate':str(target),'candidate_sha256':hashlib.sha256(text.encode()).hexdigest(),'scope':'host input observation timeout only; no guest or platform change'},indent=2)+'\n')
print(target)
