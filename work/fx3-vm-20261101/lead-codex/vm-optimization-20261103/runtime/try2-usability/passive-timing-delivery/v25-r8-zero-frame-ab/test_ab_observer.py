#!/usr/bin/env python3
"""Offline decision and local HTTP fixtures; no VM launch."""
from pathlib import Path
import sys
import os
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v25-r9-ab-host'))
from ab_observer import decide, observed, source_check, get_token, stop, check_server_pid, SerialTracker
from trial_web_v22_navigation_review import TrialState, start_server

source_check()
base = {'steps':0, 'phase':'starting', 'remaining_seconds':500,
        'ready':False, 'render_valid':False, 'frame':None}
serial = ('FX3_AP89_SCREEN_CREATE clock_id=1 ns=100000000000 tid=1 '
          'phase=presenter_factory_return screen_id=0 native_call_returned=1\n'
          'FX3_KEY96_POLL tid=2 ns=160000000000\n')
cases = [
    ('observe', dict(base), serial.replace('160000000000','159000000000'), 'observing'),
    ('no_frame', dict(base), serial, 'no_commit_or_verified_frame_after_60_guest_seconds'),
    ('commit_unverified',dict(base),serial+'FX3_OSD102_COMMIT clock_id=1 ns=150000000000 frame=1 op=0x1003\n',
     'commit_seen_visual_unverified_after_60_guest_seconds'),
    ('startup', dict(base, remaining_seconds=240), 'FX3_KEY96_POLL ns=120000000000\n', 'startup_incomplete'),
    ('frame', dict(base, ready=True, render_valid=True, frame={'sequence':1}), serial, 'first_host_verified_frame'),
    ('key', dict(base, steps=1), serial, 'protocol_fault_nonzero_key'),
    ('native_key', dict(base), serial+'FX3_KEY_INPUT_RECV step=1 key=0x1ab\n', 'protocol_fault_nonzero_key'),
    ('error', dict(base, error='guest_error'), serial, 'runner_error_or_terminal'),
    ('finished_old_frame', dict(base, phase='finished', ready=True, render_valid=True,
                                frame={'sequence':99}), serial, 'runner_error_or_terminal'),
    ('host_budget', dict(base), 'FX3_KEY96_POLL ns=120000000000\n', 'startup_incomplete'),
]
for name, status, lines, expected in cases:
    actual = decide(status, lines, host_budget_expired=name=='host_budget')['decision']
    assert actual == expected, (name, actual, expected)

runs = Path(__file__).resolve().parent.parent.parent/'runs'
for name, has_commit in [('v25diag-web-r3-91001f82', True),
                         ('v25procdiag-web-r4e-6274aabb', False),
                         ('v25procdiag-web-r6-9182e182', False)]:
    x = observed((runs/name/'serial.log').read_text(errors='replace'))
    tracker=SerialTracker(runs/name/'serial.log')
    while tracker.offset < (runs/name/'serial.log').stat().st_size:
        incremental=tracker.read()
    assert incremental==x, (name, incremental, x)
    assert x['screen0_ns'] is not None
    assert (x['first_commit_ns'] is not None) == has_commit
    print(name, x['screen0_ns'], x['first_commit_ns'], x['latest_poll_ns'])
print('PASS 10 decision branches + 3 frozen serials; no VM')

state=TrialState('offline-host-fixture',1200,4096)
server,thread=start_server(state,0)
try:
    check_server_pid(state.url,os.getpid())
    token=get_token(state.url)
    assert token==state.token
    try:
        stop(state.url,'invalid-token')
        raise AssertionError('bad token accepted')
    except urllib.error.HTTPError as exc:
        assert exc.code==403
    assert stop(state.url,token)=={'stopping':True}
    assert state.stop.is_set()
    print('PASS real frozen HTTP fixture: token rejection/valid End; no VM')
finally:
    server.shutdown();server.server_close();thread.join(timeout=3)
