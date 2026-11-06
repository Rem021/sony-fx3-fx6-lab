import fcntl
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from runtime_resource_guard import RuntimeResourceGuard, ShortRunSockets
import run_trial_v25_diag_r3 as runner


def read_events(run):
    return json.loads((run / 'resource-guard-receipt.json').read_text())['events']


def case_connect_fail_and_child_reap(*, remove_cwd=False):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        run = root / 'run'; run.mkdir()
        vanished = root / 'oldcwd'; vanished.mkdir()
        if remove_cwd:
            os.chdir(vanished)
            vanished.rmdir()
            assert not vanished.exists()
        guard = RuntimeResourceGuard(run)
        assert len(guard.alias.path('q').encode()) < 100
        assert len(guard.alias.path('g').encode()) < 100
        lock = (root / 'lock').open('a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard.add_lock(lock)
        p = subprocess.Popen(['/bin/sleep', '30'], start_new_session=True)
        guard.set_process(p)
        guard.finalize(reason='fixture_connect_failure', reap_wait=.05)
        assert p.poll() is not None and lock.closed and guard.closed
        second = (root / 'lock').open('a+b')
        fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(second, fcntl.LOCK_UN); second.close()
        events = read_events(run)
        assert events[0]['locks_held'] == 1
        assert any(x['event'] == 'qmp_connect_error' for x in events)
        assert any(x['event'] == 'process_reaped' for x in events)
        if remove_cwd:
            os.chdir('/')


def case_optional_failures():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); run = root / 'run'; run.mkdir()
        guard = RuntimeResourceGuard(run)
        lock = (root / 'lock').open('a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); guard.add_lock(lock)
        p = subprocess.Popen(['/bin/sleep', '30'], start_new_session=True)
        guard.set_process(p)
        def qmp(name, args=None, *, timeout=None):
            return {'return': {}}
        def bad(*args, **kwargs):
            raise RuntimeError('injected diagnostic failure')
        guard.set_qmp(qmp)
        guard.finalize(reason='fixture_diagnostic_failure', capture_fn=bad,
                       task_fn=bad, vcpu_fn=bad, restore_fn=bad, reap_wait=.05)
        assert p.poll() is not None and lock.closed
        events = [x['event'] for x in read_events(run)]
        for name in ('core_ring_capture_error', 'tasks_capture_error',
                     'vcpus_capture_error', 'api16_restore_error',
                     'qmp_quit', 'process_reaped'):
            assert name in events, (name, events)


def case_process_already_exited():
    with tempfile.TemporaryDirectory() as temp:
        run = Path(temp)
        guard = RuntimeResourceGuard(run)
        p = subprocess.Popen(['/usr/bin/true'], start_new_session=True)
        p.wait(); guard.set_process(p)
        guard.finalize(reason='already_exited', reap_wait=.05)
        assert guard.closed
        assert not any(x['event'] == 'qmp_connect_error' for x in read_events(run))


def case_both_short_sockets():
    with tempfile.TemporaryDirectory() as temp:
        run = Path(temp)
        alias = ShortRunSockets(run)
        try:
            for name in ('q', 'g'):
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(str(run / name)); server.listen(1)
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                before = os.getcwd()
                client.connect(alias.path(name))
                conn, _ = server.accept()
                assert os.getcwd() == before
                conn.close(); client.close(); server.close()
        finally:
            alias.close()


def case_actual_final_receipt_write_error():
    with tempfile.TemporaryDirectory() as temp:
        run = Path(temp)
        (run / 'resource-guard-receipt.json').mkdir()
        guard = RuntimeResourceGuard(run)
        lock = (run / 'lock').open('a+b')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard.add_lock(lock)
        p = subprocess.Popen(['/bin/sleep', '30'], start_new_session=True)
        guard.set_process(p)
        assert guard.finalize(reason='final_receipt_is_directory', reap_wait=.05)
        assert p.poll() is not None and guard.closed and lock.closed
        assert any(e['event'] == 'receipt_write_error' and
                   e['file'] == 'resource-guard-receipt.json' and
                   'IsADirectoryError' in e['error'] for e in guard.events)


if __name__ == '__main__':
    if '--cwd-gone' in sys.argv:
        case_connect_fail_and_child_reap(remove_cwd=True)
        print('removed original cwd: child reaped, lock released after process exit PASS')
    else:
        case_both_short_sockets()
        case_connect_fail_and_child_reap()
        case_optional_failures()
        case_process_already_exited()
        case_actual_final_receipt_write_error()
        result = subprocess.run([sys.executable, __file__, '--cwd-gone'],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stdout + result.stderr
        print('short QMP/GDB aliases; connect/diagnostic/restore faults; exited child; removed cwd PASS')
