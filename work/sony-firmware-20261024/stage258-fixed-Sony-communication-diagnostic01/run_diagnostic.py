"""Keep the original observer alive; never restart/kill/reset a helper."""
from pathlib import Path
from datetime import datetime,timezone
import json,time
import native_factory as N
import supervisor as S
H=Path(__file__).resolve().parent
if __name__=='__main__':
    goal=json.loads((H.parent/'GOAL_STATUS.json').read_text())
    job=N.launch_native_session(goal)
    print(json.dumps(dict(status='SONY_DIAGNOSTIC_TERMINAL_REQUESTED',job=str(job.directory))),flush=True)
    last=None;unresolved_saved=False
    while True:
        result=job.step();key=json.dumps(result,sort_keys=True)
        if key!=last:
            print(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(),**result)),flush=True);last=key
        if result.get('helper_terminal_observed') or result.get('observer_may_finish'):
            S.put(job.directory/'live-final-summary.json',result);job.close_observer();break
        if result.get('status') in ('OWNER_RETAINED','UNKNOWN_OBSERVER_ERROR','UNKNOWN_PROCESS_OBSERVATION','UNKNOWN_PROCESS_IDENTITY_CHANGE') and not unresolved_saved:
            S.put(job.directory/'unresolved-summary.json',result);unresolved_saved=True
        time.sleep(.02)
