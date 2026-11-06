#!/usr/bin/env python3
"""Own non-IOKit fixture parent for watchdog/recorded-observer failure injection."""
from pathlib import Path
import os
import sys
import time
import owner_supervisor as S

directory=Path(sys.argv[1])
job=S.Job.start_fixture(directory,block_phase=4)
end=time.monotonic()+4
while time.monotonic()<end:
    state=job.poll()
    if state.get('active_native_call_phase')==4:
        S.put(directory/'parent-departure.json',{'parent_pid':os.getpid(),'helper_pid':job.identity['pid'],
            'provider_phase':4,'own_fixture_only':True})
        os._exit(0)
    time.sleep(.01)
job.request_stop();job.frame.release_fixture()
raise RuntimeError('own fixture did not enter phase4')
