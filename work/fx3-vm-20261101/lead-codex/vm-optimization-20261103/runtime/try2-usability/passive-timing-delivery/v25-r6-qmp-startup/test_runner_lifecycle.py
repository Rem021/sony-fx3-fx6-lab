import fcntl
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import run_trial_v25_diag_r3 as runner
from runtime_resource_guard import RuntimeResourceGuard


def wait_exception_case():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        guard = RuntimeResourceGuard(root)
        lock = (root / 'lock').open('a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard.add_lock(lock)
        class BrokenWait:
            pid = 99999998
            returncode = None
            recovered = False
            def poll(self): return 0 if self.recovered else None
            def wait(self, timeout=0):
                if not self.recovered:
                    raise OSError('injected wait failure')
                self.returncode = 0
                return 0
        fake = BrokenWait()
        guard.set_process(fake)
        assert not guard.finalize(reason='wait_exception', reap_wait=.01)
        assert not guard.closed and not lock.closed
        events = json.loads((root / 'resource-guard-pending.json').read_text())['events']
        assert any(e['event'] == 'process_wait_error' for e in events)
        fake.recovered = True
        assert guard.finalize(reason='recovered', diagnostics=False, reap_wait=.01)
        assert guard.closed and lock.closed


def outer_error_case(kind):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run = root / 'run'
        run.mkdir()
        held = {}
        def fail_after_registration():
            guard = RuntimeResourceGuard(run)
            runner.ACTIVE_GUARD = guard
            lock = (root / 'lock').open('a+b')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            guard.add_lock(lock)
            child = subprocess.Popen(['/bin/sleep', '30'], start_new_session=True)
            guard.set_process(child)
            held.update(guard=guard, lock=lock, child=child)
            if kind == 'receipt_write':
                (run / 'runner-uncaught-error.json').mkdir()
                raise OSError('fixture enters actual receipt writer')
            if kind == 'connect':
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.connect(guard.alias.path('q'))
            if kind == 'log_write':
                (run / 'serial.log').mkdir()
                (run / 'serial.log').write_text('unwritable target')
            raise AssertionError('fixture must fail before this line')
        try:
            code = runner.execute_runner(fail_after_registration, guard_retry_seconds=.01, reap_wait=.05)
            assert code == 2
            assert held['child'].poll() is not None
            assert held['guard'].closed and held['lock'].closed
            if kind == 'receipt_write':
                events = json.loads((run / 'resource-guard-receipt.json').read_text())['events']
                assert any(e['event'] == 'receipt_write_error' and
                           e['file'] == 'runner-uncaught-error.json' and
                           'IsADirectoryError' in e['error'] for e in events)
            other = (root / 'lock').open('a+b')
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            other.close()
        finally:
            runner.ACTIVE_GUARD = None


def process_level_pending_case():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture = root / 'fixture.py'
        fixture.write_text('''import fcntl, os, subprocess, sys
from pathlib import Path
import runtime_resource_guard as rg
import run_trial_v25_diag_r3 as runner
root = Path(sys.argv[1]); run = root / 'run'; run.mkdir()
release = root / 'release'
class Refused:
    pid = 99999999
    returncode = None
    def poll(self): return 0 if release.exists() else None
    def wait(self, timeout=0):
        if release.exists():
            self.returncode = 0
            return 0
        raise subprocess.TimeoutExpired('fixture', timeout)
rg.os.killpg = lambda pid, sig: (_ for _ in ()).throw(PermissionError('fixture refusal'))
def main():
    guard = rg.RuntimeResourceGuard(run)
    runner.ACTIVE_GUARD = guard
    lock = (root / 'lock').open('a+b')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    guard.add_lock(lock)
    guard.set_process(Refused())
    raise RuntimeError('outer exception')
sys.exit(runner.execute_runner(main, guard_retry_seconds=.05, reap_wait=.01))
''')
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).parent))
        child = subprocess.Popen([sys.executable, str(fixture), str(root)], env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            pending = root / 'run' / 'resource-guard-pending.json'
            while not pending.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            assert pending.exists(), 'no pending receipt'
            assert child.poll() is None, 'runner exited before fake process reap'
            other = (root / 'lock').open('a+b')
            try:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    raise AssertionError('lock freed by outer runner exit')
            finally:
                other.close()
            events = json.loads(pending.read_text())['events']
            assert any(e['event'] == 'process_signal_error' for e in events)
            (root / 'release').write_text('reap confirmed')
            assert child.wait(timeout=5) == 2
            other = (root / 'lock').open('a+b')
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            other.close()
            receipt = json.loads((root / 'run' / 'resource-guard-receipt.json').read_text())
            assert receipt['process_reaped'] and receipt['locks_released_after_reap']
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)

if __name__ == '__main__':
    wait_exception_case()
    for kind in ('connect', 'log_write', 'receipt_write'):
        outer_error_case(kind)
    process_level_pending_case()
    print('outer connect/log/receipt exceptions and process-level unreaped lock retention PASS')
