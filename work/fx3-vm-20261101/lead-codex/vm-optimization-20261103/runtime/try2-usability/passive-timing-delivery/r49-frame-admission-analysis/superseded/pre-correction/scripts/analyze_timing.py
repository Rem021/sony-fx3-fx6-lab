#!/usr/bin/env python3
"""Read-only r48 command-entry / click timing boundaries; no runtime contact.

Explicitly preserves unknown boundaries: no phases.first_kinds artifact, no exact
guest-entry timestamp, no cross-domain subtraction. Later serial_bytes_before_cleanup
and final serial size are not used as interaction cutoff.
"""
import datetime
import json
from pathlib import Path

DEL = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
RUN = DEL / 'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'
OUT = DEL / 'r49-frame-admission-analysis/receipts'
OUT.mkdir(parents=True, exist_ok=True)
NATIVE = Path(json.loads((RUN / 'runtime.json').read_text())['run'])
HAR = json.loads((RUN / 'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/traffic.har').read_text())
POSTS = [e['startedDateTime'] for e in HAR['log']['entries'] if e['request']['method'] == 'POST']
REQ = {e['request']['url'].split('/api/')[-1]: e['startedDateTime'] for e in HAR['log']['entries']
       if e['request']['method'] == 'POST' and '/api/' in e['request']['url']}


def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))


def diff(a, b):
    return (dt(b) - dt(a)).total_seconds()


def main():
    ff_clock = json.loads((RUN / 'FIRST-FRAME-CLOCK.json').read_text())
    ff_pass = json.loads((RUN / 'FIRST-FRAME-PASS.json').read_text())
    standby = json.loads((RUN / 'initial-standby/capture-result.json').read_text())
    pre = json.loads((RUN / 'PRESTART-READY.json').read_text())
    rec = json.loads((NATIVE / 'receipt.json').read_text())
    arg = json.loads((RUN / 'ACTUAL-RUNNING-ARGV.json').read_text())
    cmd = json.loads((NATIVE / 'command.json').read_text())
    qmp = json.loads((NATIVE / 'startup-qmp-timing.json').read_text())
    trans = json.loads((OUT / 'har-transitions.json').read_text())
    first_frame_wait_from_start_monotonic = ff_pass['host_ns'] / 1e9 - ff_clock['start_monotonic']
    first_frame_clock_to_pass = diff(ff_clock['UTC'], ff_pass['UTC'])
    start_post_to_clock = diff(REQ['start'], ff_clock['UTC'])
    start_post_to_first_frame = diff(REQ['start'], ff_pass['UTC'])
    start_post_to_stop = diff(REQ['start'], REQ['stop'])
    stop_to_final_ack = diff(REQ['stop'], REQ['final-ack'])
    attempts = []
    for a in trans['attempts']:
        attempts.append({
            'case': a['case'], 'identity_utc': a['identity']['UTC'], 'arm_ms': a['outcome'].get('created_monotonic_ms'),
            'last_tick_utc': a['last_status_before']['utc'], 'click_snapshot_utc': a['click_snapshot_utc'],
            'preflight_utc': a['preflight_utc'], 'last_tick_to_click_ms': a['last_tick_to_click_ms'],
            'click_to_preflight_ms': a['click_to_preflight_ms'], 'last_tick_to_preflight_ms': a['last_tick_to_preflight_ms'],
            'frame_transition': {'clicked': a['clicked_frame'], 'preflight': a['preflight_status']['frame']},
            'outcome': a['outcome'], 'failing_frame_terms': a['failing_frame_terms']})
    value = {
        'schema': 'fx3-r49-command-entry-timing-v1',
        'source_run': str(RUN), 'native_run': str(NATIVE),
        'har_post_utc': POSTS,
        'api_start_post_utc': REQ.get('start'), 'api_stop_post_utc': REQ.get('stop'),
        'api_final_ack_post_utc': REQ.get('final-ack'),
        'prestart_ready_utc': pre.get('UTC'), 'prestart_ready_host_ns': pre.get('host_ns'),
        'first_frame_clock': {'utc': ff_clock['UTC'], 'host_ns': ff_clock['host_ns'],
                              'start_monotonic': ff_clock['start_monotonic'], 'limit_seconds': ff_clock['limit_seconds']},
        'first_frame_pass': {'utc': ff_pass['UTC'], 'host_ns': ff_pass['host_ns']},
        'initial_standby': {'utc': standby.get('UTC'), 'host_ns': standby.get('host_ns'),
                            'before_performance_ms': standby['before']['performance_ms'],
                            'after_performance_ms': standby['after']['performance_ms'],
                            'firmware': standby.get('firmware')},
        'observed_first_frame_wait': {
            'start_monotonic_to_pass_s': first_frame_wait_from_start_monotonic,
            'first_frame_clock_to_pass_s': first_frame_clock_to_pass,
            'api_start_post_to_first_frame_clock_s': start_post_to_clock,
            'api_start_post_to_first_frame_s': start_post_to_first_frame,
            'limit_seconds': 180,
            'under_limit': first_frame_wait_from_start_monotonic < 180,
        },
        'api_start_to_stop_s': start_post_to_stop, 'api_stop_to_final_ack_s': stop_to_final_ack,
        'native_receipt': {'stop_cause': rec.get('stop_cause'), 'duration_seconds': rec.get('duration_seconds'),
                           'maximum_seconds': rec.get('maximum_seconds'), 'key_steps': rec.get('key_steps'),
                           'menu_verified': rec.get('menu_verified'), 'qemu_exit': rec.get('qemu_exit'),
                           'process_reaped': rec.get('process_reaped'), 'PID_absent': rec.get('PID_absent'),
                           'API16_restored': rec.get('cleanup', {}).get('API16_restored'),
                           'quit_sent': rec.get('cleanup', {}).get('quit_sent'),
                           'serial_bytes_before_cleanup': rec.get('cleanup', {}).get('serial_bytes_before_cleanup')},
        'actual_running_argv': {'pid': arg.get('pid'), 'qemu_sha256': arg.get('qemu_sha256'),
                                'ps_command': arg.get('ps_command'), 'utc': arg.get('UTC'), 'host_ns': arg.get('host_ns')},
        'command_json': {'cwd': cmd.get('cwd'), 'candidate': cmd.get('candidate'),
                         'candidate_sha256': cmd.get('candidate_sha256'), 'args': cmd.get('args'),
                         'seconds': cmd.get('seconds'), 'smp': cmd.get('smp'), 'tcg_thread': cmd.get('tcg_thread'),
                         'icount_profile': cmd.get('icount_profile')},
        'startup_qmp_timing': qmp,
        'attempts': attempts,
        'boundaries': {
            'exact_api_start_post': 'known',
            'exact_first_frame_pass': 'known',
            'exact_guest_entry': 'unknown: no exact guest-entry marker in retained files',
            'phases_first_kinds_cleanup_serial_offset': 'unknown: no phases.first_kinds artifact retained',
            'interaction_cutoff': 'unknown: do not substitute phases-first artifact or later serial_bytes_before_cleanup/final serial size',
            'command_entry_to_guest_entry': 'unknown',
            'host_vs_guest_vs_browser_clock': 'not subtracted; guest entry -> return/adjacent same-thread gaps do not prove CPU/FIFO idle or HTTP latency',
            'serial_bytes_before_cleanup': 'present in cleanup receipt but NOT used as interaction cutoff',
            'final_serial_size': 'present on disk but NOT used as interaction cutoff',
        },
        'limitations': ['single failed run; step1 only', 'no command-entry artifact beyond the files listed',
                        'no CPU/FIFO/HTTP latency inference', 'no second VM/start'],
    }
    (OUT / 'command-entry-timing.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'first_frame_wait_s': first_frame_wait_from_start_monotonic,
                      'api_start_to_first_frame_s': start_post_to_first_frame,
                      'attempts': [{'case': a['case'], 'last_tick_to_click_ms': a['last_tick_to_click_ms'],
                                    'click_to_preflight_ms': a['click_to_preflight_ms']} for a in attempts],
                      'boundaries': value['boundaries'],
                      'receipt': str(OUT / 'command-entry-timing.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
