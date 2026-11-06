#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trial_health_v2 import evaluate

base=dict(lifecycle=True, observer_error=None, serial_failure=None,
          markers_complete=True, standby_observed=True, render_valid=True,
          black_after_ready=[], early_stop=None)
assert evaluate(**base)==(True,True,True)
for changed, expected in [
 ({'lifecycle':False},(True,True,False)),
 ({'observer_error':'error'},(False,True,False)),
 ({'serial_failure':'REJECT'},(False,True,False)),
 ({'markers_complete':False},(False,True,False)),
 ({'standby_observed':False},(True,False,False)),
 ({'render_valid':False},(True,False,False)),
 ({'black_after_ready':[{'sequence':5}]},(True,False,False)),
 ({'black_after_ready':[{'sequence':5}],'render_valid':True},(True,False,False)),
 ({'early_stop':'render unknown'},(True,True,False)),
]:
 assert evaluate(**(base|changed))==expected, changed
print('health gates: lifecycle, protocol, render, ever-black and recovered-black negatives PASS')
