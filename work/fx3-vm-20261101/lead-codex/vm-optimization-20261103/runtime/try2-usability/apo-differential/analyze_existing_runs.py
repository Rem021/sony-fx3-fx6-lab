#!/usr/bin/env python3
"""Read-only two-run APO comparison; guest timestamps are never mixed with host time."""
from pathlib import Path
from bisect import bisect_left, bisect_right
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'
NAMES = ('try2powerinternal-71ffcdef', 'try2mssinternal-a1d8f68a')
EXPECTED_SERIAL = ('143421ac90476b9032f5de4331df48c046d7abeab4e72c590198b4283b737e6f',
                   'cab0891be83fa46d2f16096ba2d7f354609289357d21b5e2d70fde2f4d594ada')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_run(name, expected):
    run = RUNS / name
    serial_path = run / 'serial.log'
    assert sha(serial_path) == expected, name + ': serial changed'
    b = serial_path.read_bytes()
    receipt = json.loads((run / 'receipt.json').read_text())
    events = [json.loads(s) for s in (run / 'trial-input-events.jsonl').read_text().splitlines() if s]
    frames = json.loads((run / 'trial-step-readbacks.json').read_text())
    assert len(events) == len(frames) == receipt['key_steps']
    key_re = rb'FX3_SYNTH_KEY step=(\d+) key=(0x[0-9a-f]+) status=([01])[^\r\n]*monotonic_ns=(\d+)'
    edge_matches = list(re.finditer(key_re, b))
    assert len(edge_matches) == len(events) * 2
    edges = {}
    for m in edge_matches:
        step, key, status, ns = int(m[1]), int(m[2], 16), int(m[3]), int(m[4])
        assert step in range(1, len(events)+1) and key == events[step-1]['key']
        assert status not in edges.setdefault(step, {})
        edges[step][status] = {'guest_ns': ns, 'serial_byte': m.start()}
    poll_re = rb'FX3_KEY96_POLL[^\r\n]*\bns=(\d+)'
    poll = [(m.start(), int(m[1])) for m in re.finditer(poll_re, b)]
    poll_offsets = [x[0] for x in poll]
    special_re = rb'FX3_BOOT_QUEUE_SEND[^\r\n]*bytes=20 source=0x830128 raw=(0100150001000000050000000000000000000000)[^\r\n]*caller_relative=0x16f12ec'
    specials = []
    for m in re.finditer(special_re, b):
        pos = m.start()
        before = max((step for step, pair in edges.items() if pair[0]['serial_byte'] < pos), default=None)
        after = min((step for step, pair in edges.items() if pair[1]['serial_byte'] > pos), default=None)
        i = bisect_left(poll_offsets, pos)
        specials.append({'serial_byte': pos, 'after_key_up_step': before,
                         'before_key_down_step': after,
                         'neighboring_poll_guest_ns': [poll[i-1][1], poll[i][1]] if 0 < i < len(poll) else None,
                         'body20_hex': m[1].decode(), 'source': '0x830128',
                         'destination': '0x5503e0', 'original_app_call_site': 'appFw.so+0x16f12ec'})
    callback_re = rb'FX3_BOOT_QUEUE_SEND[^\r\n]*bytes=32 source=0xa5a5a5a5 raw=([0-9a-f]{8})[0-9a-f]* caller_relative=0x16f10b4'
    callbacks = Counter(int.from_bytes(bytes.fromhex(m[1].decode()), 'little') for m in re.finditer(callback_re, b))
    power_re = rb'FX3_POWER_NATIVE_NOTIFY seq=1 ns=(\d+)[^\r\n]*raw12=([0-9a-f]+)'
    power = list(re.finditer(power_re, b))
    assert len(power) == 1 and power[0][2] == b'520000001100000002000000'
    power_ns = int(power[0][1])
    steps = []
    for index, (event, frame) in enumerate(zip(events, frames), 1):
        assert index == event['step'] == frame['step']
        key = event['key']
        png = run / f'trial-step-{index:02d}-key-{key:03x}.png'
        assert sha(png) == frame['PNG_sha256']
        recv = {}
        for status in (1, 0):
            pattern = rb'FX3_KEY_INPUT_RECV step='+str(index).encode()+rb' key='+hex(key).encode()+rb' status='+str(status).encode()+rb'[^\r\n]*native_result=0'
            recv[status] = len(re.findall(pattern, b))
            assert recv[status] == 1
        done = len(re.findall(rb'FX3_KEY95_STEP_DONE step='+str(index).encode()+rb' key='+hex(key).encode()+rb'[^\r\n]*one_down_one_up=1', b))
        assert done == 1
        steps.append({'step': index, 'key': hex(key), 'observed_page': event['observed_page'],
                      'reason': event['reason'], 'guest_down_ns': edges[index][1]['guest_ns'],
                      'guest_up_ns': edges[index][0]['guest_ns'], 'native_receive_down_up': recv,
                      'native_done_count': done, 'after_png': str(png), 'after_png_sha256': sha(png),
                      'after_frame_sequence': frame['sequence'], 'after_nonuniform': frame['nonuniform_pixels']})
    assert all(callbacks[key] == 2 * sum(e['key'] == key for e in events) for key in {e['key'] for e in events})
    shutdown = {'source': receipt['early_stop_reason'], 'stop_cause': receipt['stop_cause'],
                'native_power_off': receipt['native_model_power_off_after_ready'],
                'native_shutdown_screen': receipt['native_shutdown_after_ready'],
                'host_duration_s': receipt['duration_seconds'], 'host_limit_s': receipt['maximum_seconds'],
                'qemu_exit': receipt['qemu_exit'], 'reaped': receipt['process_reaped'],
                'pid_absent': receipt['PID_absent'], 'inputs_unchanged': receipt['inputs_unchanged'],
                'api16_restored': receipt['cleanup']['API16_restored'], 'locks': receipt['locks'],
                'health_pass': receipt['health_pass'], 'render_pass': receipt['render_pass']}
    return {'run': str(run), 'serial_sha256': expected, 'serial_bytes': len(b),
            'candidate_sha256': receipt['candidate_sha256'], 'steps': steps,
            'original_app_callback32_key_counts': {hex(k): v for k, v in sorted(callbacks.items()) if k in {e['key'] for e in events}},
            'special_app_to_boot20': specials, 'power_first_notify_guest_ns': power_ns,
            'last_key_up_to_power_guest_s': (power_ns-steps[-1]['guest_up_ns']) / 1e9,
            'shutdown': shutdown, 'mss_original_path_points': b.count(b'FX3_MSS_ORIGINAL_PATH seq='),
            'mss_ring_overflow': b'FX3_MSS_ORIGINAL_PATH_OVERFLOW' in b}


def main():
    a, b = [parse_run(n, h) for n, h in zip(NAMES, EXPECTED_SERIAL)]
    assert len(a['steps']) == 27 and len(b['steps']) == 2
    assert [e['after_key_up_step'] for e in a['special_app_to_boot20']] == [2, 13]
    assert not b['special_app_to_boot20']
    assert all(e['key'] == '0x30' for e in a['steps'][13:])
    result = {'schema': 'fx3-apo-existing-runs-differential-v1', 'clock': 'guest CLOCK_MONOTONIC only for step and power ns; serial-order neighboring polls are an approximation, not strict event timestamps',
              'runs': {'continuous27': a, 'twoMENU': b},
              'candidate_guest_intervals': {
                  'continuous27_step13_left_up_to_power_s': (a['power_first_notify_guest_ns']-a['steps'][12]['guest_up_ns'])/1e9,
                  'continuous27_step27_down_up_to_power_s': a['last_key_up_to_power_guest_s'],
                  'twoMENU_step2_menu_up_to_power_s': b['last_key_up_to_power_guest_s'],
              },
              'interpretation_guard': 'special 20B message is a correlated app-to-boot event, not proven UPM consume or timer reset; no synthetic 0x00920204 instruction follows'}
    out = Path(__file__).resolve().parent / 'existing-runs-differential.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(out)
    print(json.dumps(result['candidate_guest_intervals'], indent=2))


if __name__ == '__main__':
    main()
