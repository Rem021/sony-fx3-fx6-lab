#!/usr/bin/env python3
"""Host-only state and 31/32 contract test; no guest or browser acceptance."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trial_web_v3_usability import TrialState
from gate_input_usability import valid_command

state = TrialState(Path(__file__).resolve().parent, 3600, 4096)
state.update(phase='ready', ready=True)
state.publish(b'nonblack', {'sequence': 1, 'pixel_source_sequence': 1,
                            'PNG_sha256': 'a', 'all_zero_pixels': False})
for step in range(1, 33):
    assert valid_command(step, 3, 100, step-1, 0x1f8, 4096)
    code, result = state.submit({'key': 3, 'observed_sequence': 1})
    assert code == 202, (step, result)
    assert len(state.pending) == 1
    assert state.submit({'key': 3, 'observed_sequence': 1})[0] == 409
    state.take()
    state.update(steps=step, busy=False)
assert state.snapshot()['ready'] and state.snapshot()['steps'] == 32
state.publish(b'black', {'sequence': 2, 'pixel_source_sequence': 2,
                         'PNG_sha256': 'b', 'all_zero_pixels': True})
assert not state.snapshot()['ready'] and len(state.black_after_ready) == 1
assert state.submit({'key': 3, 'observed_sequence': 2})[0] == 409
print('WEB_HOST_PASS 31_32/one_pending/black_suspends_keys/max_4096')
