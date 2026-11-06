"""Replay production wait predicates; no runtime or input operations."""
from pathlib import Path
import ast
import json
import re
import types

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
old=ast.parse((PARENT/'run_trial_v15_startup_receipt.py').read_text())
branch=next(n for n in ast.walk(old) if isinstance(n,ast.If)
            and 'host_step not in up_seen' in ast.unparse(n.test)
            and "current_command['sent_monotonic']" in ast.unparse(n.test))
old_predicate=compile(ast.Expression(branch.test),'baseline-input-deadline','eval')
new=ast.parse((PARENT/'run_trial_v16_input_deadline.py').read_text())
helper=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='native_input_deadline_error')
namespace={};exec(compile(ast.Module(body=[helper],type_ignores=[]),'candidate-input-deadline','exec'),namespace)
fn=namespace['native_input_deadline_error']
command={'sent_monotonic':100.0,'key':0x1ab};up={1:(101.0,0x1ab)}
rows=[]
for label,current,step,seen,both,now,should_fail in [
    ('idle',None,1,{},False,1000,False),
    ('before_deadline',command,1,{},False,111.9,False),
    ('missing_sender',command,1,{},True,112.1,True),
    ('missing_native_consumer',command,1,up,False,112.1,True),
    ('wrong_step_sender',command,2,up,True,112.1,True),
    ('all_input_receipts_menu_still_rendering',command,1,up,True,250,False),
]:
    result=fn(current,step,seen,both,now)
    assert bool(result)==should_fail,(label,result)
    old_fails=eval(old_predicate,{'current_command':current,'host_step':step,'up_seen':seen,'time':types.SimpleNamespace(monotonic=lambda:now)})
    if label=='missing_native_consumer':assert not old_fails and result
    rows.append({'case':label,'baseline_timeout':old_fails,'candidate_error':result,'passed':True})
# The user's historical step10 is explicitly NOT this defect's reproduction.
historical=PARENT.parent/'try2-delivery/runs/try2-70588c4c/serial.log'
serial=historical.read_bytes().decode(errors='replace')
down=bool(re.search(r'FX3_KEY_INPUT_RECV step=10 key=0x30 status=1 [^\n]*native_result=0',serial))
keyup=bool(re.search(r'FX3_KEY_INPUT_RECV step=10 key=0x30 status=0 [^\n]*native_result=0',serial))
sent=bool(re.search(r'FX3_SYNTH_KEY step=10 key=0x30 status=0 [^\n]*result=0 ',serial))
assert down and keyup and sent
(HERE/'test-receipt.json').write_text(json.dumps({'scope':'production predicate/helper extraction; no QEMU or new guest input','cases':rows,'historical_step10':{'source':str(historical),'native_down':down,'native_up':keyup,'sender_up':sent,'caused_by_this_gap':False}},ensure_ascii=False,indent=2)+'\n')
print('6 input-deadline cases passed; baseline missing-consumer stall reproduced; historical step10 excluded')
