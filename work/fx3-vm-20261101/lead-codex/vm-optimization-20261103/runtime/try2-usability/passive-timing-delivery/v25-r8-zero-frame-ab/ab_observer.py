#!/usr/bin/env python3
"""Zero-key A/B observer for an already launched, frozen r9 web runner.

No QMP or guest access. Does not start a VM. --send-stop is explicit and only
uses the existing HTTP End endpoint after a terminal observation decision.
"""
import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

HOST = Path(__file__).resolve().parent.parent / 'v25-r9-ab-host'
PINS = {
    'run_trial_v25_diag_r3.py': '902869ee48c1c80dbe770316d0515ac429a5679beb1af73971dfabf7be041126',
    'startup_qmp_v1.py': 'efba2c336e063e18208f21df6e3bf9ae462abb1fef5ed0ec618f009004b67c74',
    'host_exception_clock.py': '5f133dd0c8f6d17b19cab87616b1efe725445829d75447ac0de71ceb99a083dc',
    'SOURCE-FREEZE.json': '48b0b0abfd2f6ac633c6ac74f5c6ff912ece0290e938206b09c42163a77a5c36',
}
ARMS = {
    'A': {'candidate': 'a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518',
          'cpio': '31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83',
          'procdiag': 'not_available_by_candidate'},
    'B': {'candidate': 'ced1644fbcecc542c3d90f16be2a461876e7f3af92ff639c793742f090136d22',
          'cpio': '439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db',
          'procdiag': 'optional_if_pending_key_only'},
}
SCREEN0 = re.compile(r'FX3_AP89_SCREEN_CREATE clock_id=1 ns=(\d+)[^\r\n]*phase=presenter_factory_return screen_id=0(?:\s|\r|$)')
COMMIT = re.compile(r'FX3_OSD102_COMMIT clock_id=1 ns=(\d+)[^\r\n]*frame=(\d+) op=0x1003(?:\s|\r|$)')
POLL = re.compile(r'FX3_KEY96_POLL[^\r\n]*?(?<![A-Za-z_])ns=(\d+)')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def source_check():
    bad = [name for name, expected in PINS.items() if sha(HOST/name) != expected]
    freeze = json.loads((HOST/'SOURCE-FREEZE.json').read_text())['files_sha256']
    bad += [name for name, expected in freeze.items() if not (HOST/name).is_file() or sha(HOST/name) != expected]
    if bad:
        raise RuntimeError('frozen r9 host mismatch: ' + ', '.join(sorted(set(bad))))


def observed(serial):
    screen = SCREEN0.search(serial)
    commit = COMMIT.search(serial)
    polls = POLL.findall(serial)
    return {'screen0_ns': int(screen[1]) if screen else None,
            'first_commit_ns': int(commit[1]) if commit else None,
            'first_commit_frame': int(commit[2]) if commit else None,
            'latest_poll_ns': int(polls[-1]) if polls else None,
            'native_key_seen': bool(re.search(r'FX3_KEY_INPUT_RECV step=[1-9]', serial))}


class SerialTracker:
    """Read only appended serial bytes; preserve a short partial-line tail."""
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.backlog_bytes = 0
        self.tail = ''
        self.value = {'screen0_ns':None, 'first_commit_ns':None,
                      'first_commit_frame':None, 'latest_poll_ns':None,
                      'native_key_seen':False}

    def read(self):
        with self.path.open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            if size < self.offset:
                raise RuntimeError('serial log truncated during observation')
            stream.seek(self.offset)
            data = stream.read(8 * 1024 * 1024)
            self.offset = stream.tell()
            self.backlog_bytes = size - self.offset
        if not data:
            return dict(self.value)
        joined = self.tail + data.decode('utf8', errors='replace')
        lines = joined.split('\n')
        self.tail = lines.pop()[-4096:]
        for line in lines:
            if self.value['screen0_ns'] is None:
                m = SCREEN0.search(line)
                if m: self.value['screen0_ns'] = int(m[1])
            if self.value['first_commit_ns'] is None:
                m = COMMIT.search(line)
                if m:
                    self.value['first_commit_ns'] = int(m[1])
                    self.value['first_commit_frame'] = int(m[2])
            m = POLL.search(line)
            if m: self.value['latest_poll_ns'] = int(m[1])
            if re.search(r'FX3_KEY_INPUT_RECV step=[1-9]', line):
                self.value['native_key_seen'] = True
        return dict(self.value)


def decide(status, serial, *, reserve=240, host_budget_expired=False):
    o = serial if isinstance(serial, dict) else observed(serial)
    base = {'observation': o, 'steps': status.get('steps'),
            'remaining_seconds': status.get('remaining_seconds'),
            'frame': status.get('frame'), 'render_valid': status.get('render_valid')}
    if status.get('steps') != 0 or o['native_key_seen']:
        return dict(base, decision='protocol_fault_nonzero_key', terminal=True)
    if status.get('error') or status.get('phase') in ('stopping', 'finished'):
        return dict(base, decision='runner_error_or_terminal', terminal=True)
    if status.get('ready') and status.get('render_valid') and status.get('frame'):
        return dict(base, decision='first_host_verified_frame', terminal=True)
    if (o['screen0_ns'] is not None and o['latest_poll_ns'] is not None
            and o['latest_poll_ns'] >= o['screen0_ns'] + 60_000_000_000):
        return dict(base, decision=('commit_seen_visual_unverified_after_60_guest_seconds'
                                    if o['first_commit_ns'] is not None else
                                    'no_commit_or_verified_frame_after_60_guest_seconds'), terminal=True)
    remaining = status.get('remaining_seconds')
    if host_budget_expired or (remaining is not None and remaining <= reserve):
        return dict(base, decision=('startup_incomplete' if o['screen0_ns'] is None
                                    else 'observation_budget_exhausted'), terminal=True)
    return dict(base, decision='observing', terminal=False)


def get_json(url):
    with urllib.request.urlopen(url + '/api/status', timeout=3) as f:
        return json.load(f)


def get_token(url):
    with urllib.request.urlopen(url+'/', timeout=3) as f:
        html=f.read(200000).decode('utf8')
    m=re.search(r'const token=("[^"\\]*(?:\\.[^"\\]*)*");',html)
    if not m: raise RuntimeError('page token unavailable')
    return json.loads(m[1])


def check_server_pid(url, expected):
    port=url.rsplit(':',1)[1]
    output=subprocess.check_output(['lsof','-nP','-t','-iTCP:'+port,'-sTCP:LISTEN'],text=True)
    pids={int(x) for x in output.split()}
    if pids != {int(expected)}:
        raise RuntimeError('loopback port does not belong to trial observer')


def stop(url, token):
    request = urllib.request.Request(url + '/api/stop', data=b'{}',
                                     headers={'Content-Type': 'application/json',
                                              'X-Trial-Token':token}, method='POST')
    with urllib.request.urlopen(request, timeout=3) as f:
        return json.load(f)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--arm', choices=ARMS, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--send-stop', action='store_true', help='explicitly call existing End endpoint at decision')
    args = p.parse_args()
    source_check()
    session = json.loads((args.run/'trial-session.json').read_text())
    url = session['url']
    if not re.fullmatch(r'http://127\.0\.0\.1:\d+', url):
        raise RuntimeError('not a loopback r9 session')
    command = json.loads((args.run/'command.json').read_text())
    candidate = Path(command['candidate'])
    if sha(candidate) != ARMS[args.arm]['candidate']:
        raise RuntimeError('wrong candidate arm')
    manifest = json.loads(candidate.read_text())
    if sha(manifest['initrd']['path']) != ARMS[args.arm]['cpio']:
        raise RuntimeError('wrong CPIO arm')
    if session['max_seconds'] != 1200 or session['max_steps'] != 4096:
        raise RuntimeError('A/B budget mismatch: require 20min, 4096 host limit')
    check_server_pid(url, session['observer_pid'])
    token=get_token(url)  # secret stays in memory; never print or persist
    initial=get_json(url)
    launch_id=initial.get('launch_request_id')
    if not launch_id or initial.get('phase') in ('finished','stopping'):
        raise RuntimeError('browser Start not accepted for this live session')
    out = args.run/'ab-zero-key-observation.json'
    if out.exists():
        raise FileExistsError(out)
    host_deadline=time.monotonic()+960  # independent 16min observation bound; 4min reserved
    serial_tracker=SerialTracker(args.run/'serial.log')
    while True:
        try:
            check_server_pid(url, session['observer_pid'])
            status = get_json(url)
            if status.get('launch_request_id') != launch_id:
                raise RuntimeError('launch identity changed')
            serial = serial_tracker.read()
            deadline=time.monotonic()>=host_deadline
            if deadline and serial_tracker.backlog_bytes:
                raise RuntimeError('serial backlog remains at host observation deadline')
            result = decide(status, serial, host_budget_expired=deadline)
        except Exception as exc:
            result = {'decision':'storage_or_status_unavailable', 'terminal':True,
                      'error':repr(exc), 'classification':'inconclusive'}
        if result['terminal']:
            result.update({'arm': args.arm, 'procdiag_expectation': ARMS[args.arm]['procdiag'],
                           'host_monotonic':time.monotonic(), 'stop_requested':args.send_stop,
                           'launch_request_id':launch_id, 'run':str(args.run.resolve()),
                           'candidate_sha256':ARMS[args.arm]['candidate'],
                           'cpio_sha256':ARMS[args.arm]['cpio']})
            if args.send_stop:
                try:
                    check_server_pid(url, session['observer_pid'])
                    if get_json(url).get('launch_request_id') != launch_id:
                        raise RuntimeError('launch identity changed before stop')
                    result['stop_response'] = stop(url, token)
                except Exception as exc: result['stop_error'] = repr(exc)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(result, ensure_ascii=False)); return
        time.sleep(1)


if __name__ == '__main__':
    main()
