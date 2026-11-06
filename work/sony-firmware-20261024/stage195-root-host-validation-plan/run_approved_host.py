"""Run ONLY after exact newly recorded HOST_ONLY authorization.

No device command path. Do not run this script just to test imports or syntax.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time
import host_supervisor as S
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
    goal=json.loads((HERE.parent/'GOAL_STATUS.json').read_text())
    session=S.launch_root_session(goal)
    print(json.dumps({'status':'HOST_ONLY_TERMINAL_REQUESTED','job':str(session.directory),'helper_invocations_max':2}),flush=True)
    last=None
    while True:
        value=session.step();key=json.dumps(value,sort_keys=True)
        if key!=last:
            print(json.dumps({'observed_utc':datetime.now(timezone.utc).isoformat(),**value}),flush=True);last=key
        if value['status']=='HOST_TRIAL_AND_READBACK_COMPLETE':
            S.put(session.directory/'host-live-summary.json',value);session.close_observer();break
        # Keep the same session and its proof/buffers alive. A relay exit or
        # observation deadline never starts another administrator request.
        if value['status']=='UNKNOWN_HOST_TEST':
            S.put(session.directory/'host-unknown-summary.json',value)
            break # helper has no hardware; no kill/reset/retry or resource takeover
        if session.runner.poll() is not None and session.runner.returncode!=0 and not any(s.verified for s in session.stages):
            S.put(session.directory/'host-launch-unknown.json',{'status':'UNKNOWN_TERMINAL_REQUEST_FAILED','returncode':session.runner.returncode,'automatic_retry':False})
            break
        time.sleep(.05)
