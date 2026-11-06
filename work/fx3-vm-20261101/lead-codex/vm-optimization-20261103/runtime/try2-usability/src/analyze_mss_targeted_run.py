#!/usr/bin/env python3
"""Extract bounded original MSS/key/power evidence without mixing clocks."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fields(line):
    return {k: v for k, v in re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^ ]+)', line)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ns = ap.parse_args()
    run = ns.run.resolve()
    serial = run / 'serial.log'
    receipt = json.loads((run / 'receipt.json').read_text())
    wanted = ('FX3_MSS_ORIGINAL_PATH ', 'FX3_MSS_OBSERVER_BOUND ',
              'FX3_SYNTH_KEY step=', 'FX3_KEY_INPUT_RECV step=',
              'FX3_KEY95_STEP_DONE step=', 'FX3_POWER_NATIVE_NOTIFY ',
              'FX3_BOOT_QUEUE_SEND tid=381 bytes=28 source=0x830128 raw=2c0003',
              'open screen: scr0132_0001 -> scr0039_shutdown')
    events = []
    for raw in serial.read_bytes().splitlines():
        line = raw.decode('utf-8', 'replace').strip()
        if line.startswith(wanted):
            events.append({'line': line, 'fields': fields(line)})
    mss = [e for e in events if e['line'].startswith('FX3_MSS_ORIGINAL_PATH ')]
    keys = [e for e in events if e['line'].startswith('FX3_SYNTH_KEY step=')]
    power = [e for e in events if e['line'].startswith('FX3_POWER_NATIVE_NOTIFY ')]
    last_mss = int(mss[-1]['fields']['ns']) if mss else None
    last_up = int([e for e in keys if e['fields']['status'] == '0'][-1]['fields']['monotonic_ns']) if keys else None
    first_power = int(power[0]['fields']['ns']) if power else None
    result = {
        'scope': 'passive original app points plus synthetic input receiver; kernel UPM consumer unknown',
        'run': str(run), 'serial_sha256': digest(serial), 'receipt_sha256': digest(run/'receipt.json'),
        'candidate_sha256': receipt['candidate_sha256'],
        'observer_source_snapshot': receipt['observer_source_snapshot'],
        'events': events,
        'counts': {'mss_points': len(mss), 'synthetic_key_edges': len(keys), 'power_native_points': len(power)},
        'same_guest_monotonic_only': {
            'last_boot_mss_point_ns': last_mss, 'last_key_up_ns': last_up,
            'first_power_notify_ns': first_power,
            'last_mss_to_power_seconds': (first_power-last_mss)/1e9 if first_power and last_mss else None,
            'last_key_up_to_power_seconds': (first_power-last_up)/1e9 if first_power and last_up else None,
        },
        'host_duration_seconds_separate_clock': receipt['duration_seconds'],
        'shutdown': {k: receipt[k] for k in ('early_stop_reason','qemu_exit','process_reaped','PID_absent',
                    'inputs_unchanged','locks','cleanup','health_pass','key_steps')},
        'limitations': ['MSS after-send raw16 was not readable; no live 16B payload claim',
                        'osal_snd_sync_msg result=0 does not prove UPM consume or timer reload',
                        'no claim that MENU is the only activity path',
                        'native power notification and original shutdown screen are observed; specific factor is original table plus passive raw12'],
    }
    ns.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(ns.output)


if __name__ == '__main__':
    main()
