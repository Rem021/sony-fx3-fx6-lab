"""Replay a native shutdown arriving between the loop poll and pre-write poll."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
spec = importlib.util.spec_from_file_location('real_log_monitor', PARENT / 'trial_log_v4_mss.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
history = PARENT / 'runs/try2mssinternal-a1d8f68a/serial.log'
data = history.read_bytes()
power = re.search(rb'FX3_BOOT_QUEUE_SEND[^\r\n]*source=0x830128 raw=2c000300[^\r\n]*', data)
shutdown = re.search(rb'open screen: [^\r\n]* -> scr0039_shutdown[^\r\n]*', data)
assert power and shutdown

def extract(path):
    tree = ast.parse(path.read_text())
    block = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                 and ast.unparse(n.test) == 'proposed is not None and (not trial.stop.is_set())')
    # Use the actual production statements up to key selection, including break.
    end = next(i for i, n in enumerate(block.body) if isinstance(n, ast.Assign)
               and ast.unparse(n.targets[0]) == 'key')
    body = block.body[:end]
    body += ast.parse('writes.append("would_reach_guest_write")\nbreak').body
    loop = ast.While(test=ast.Constant(True), body=body, orelse=[])
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pre_input_stop_reason']
    return compile(ast.fix_missing_locations(ast.Module(body=helpers+[loop], type_ignores=[])), str(path), 'exec')

old = extract(PARENT / 'run_trial_v16_input_deadline.py')
new = extract(PARENT / 'run_trial_v18_preinput_stop.py')
rows = []
for name, initial, appended, ready, count, expect_old, expect_new in [
    ('native_poweroff_between_polls', b'', power.group()+b'\n', {}, 0, True, False),
    ('native_shutdown_between_polls', b'', shutdown.group()+b'\n', {}, 0, True, False),
    ('known_boot_shutdown_unchanged', shutdown.group()+b'\n', b'', {}, 1, True, True),
    ('ordinary_native_activity', b'', b'FX3_KEY_INPUT_RECV step=1 key=0x3 status=0 native_result=0\n', {}, 0, True, True),
    ('existing_fatal_guard', b'', b'FX3_SYNC100_REJECT\n', {}, 0, False, False),
]:
    outcomes=[]
    for code in (old,new):
        with tempfile.TemporaryDirectory(prefix='fx3-preinput-stop-') as tmp:
            path=Path(tmp)/'serial.log';path.write_bytes(initial)
            monitor=module.FullLogMonitor(path);monitor.poll()
            assert monitor.failure is None and not monitor.native_power_off_events
            with path.open('ab') as stream:stream.write(appended)
            errors=[]
            trial=type('Trial',(),{'fail':lambda self,reason:errors.append(reason)})()
            ns={'log_monitor':monitor,'phaseA_capture':ready,'shutdown_count_at_ready':count,'trial':trial,'writes':[]}
            exec(code,ns)
            outcomes.append({'would_reach_guest_write':bool(ns['writes']),'errors':errors})
    assert outcomes[0]['would_reach_guest_write']==expect_old,(name,outcomes)
    assert outcomes[1]['would_reach_guest_write']==expect_new,(name,outcomes)
    rows.append({'case':name,'baseline':outcomes[0],'candidate':outcomes[1]})
(HERE/'test-receipt.json').write_text(json.dumps({'scope':'production AST pre-input branch plus actual incremental monitor; no QEMU and no guest key', 'historical_serial':str(history), 'historical_serial_sha256':hashlib.sha256(data).hexdigest(), 'historical_event_byte_ranges':{'poweroff':[power.start(),power.end()],'shutdown':[shutdown.start(),shutdown.end()]}, 'historical_race_occurrence_proven':False,'cases':rows},ensure_ascii=False,indent=2)+'\n')
print('5 cases passed; baseline pre-input stop gap reproduced in both native stop cases')
