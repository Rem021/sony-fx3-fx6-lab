#!/usr/bin/env python3
"""Bounded offline filesystem tests. No runner import, processes, sockets or VM."""
import ast
import contextlib
import copy
import datetime
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest

from host_exception_clock import write_host_first_exception, write_host_journal
from verify_patch import HERE, verify

EVIDENCE = []
ARTIFACT_ROOT = None
PATCHED_SOURCE = None


def original_error_leaf():
    raise ValueError('original-host-observation-error')


def original_error():
    try:
        original_error_leaf()
    except ValueError as exc:
        return exc


def extract_execute(journal, guard, sleeps):
    tree = ast.parse(PATCHED_SOURCE.read_bytes())
    execute = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                   and n.name == 'execute_runner')
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    handler = next(n for n in ast.walk(main) if isinstance(n, ast.ExceptHandler)
                   and isinstance(n.type, ast.Tuple)
                   and [v.id for v in n.type.elts if isinstance(v, ast.Name)]
                   == ['Exception', 'KeyboardInterrupt'])
    host_handler = ast.parse('def host_handler(run, journal, exc, transport, trial): pass').body[0]
    host_handler.body = copy.deepcopy(handler.body)
    module = ast.fix_missing_locations(ast.Module(body=[execute, host_handler], type_ignores=[]))
    env = {'main': lambda: 0, 'ACTIVE_GUARD': guard, 'ACTIVE_HOST_JOURNAL': journal,
           'write_host_first_exception': write_host_first_exception,
           'sys': sys, 'os': os, 'time': SimpleNamespace(sleep=sleeps.append)}
    exec(compile(module, str(PATCHED_SOURCE) + ':AST-only', 'exec'), env)
    return env


class FakeGuard:
    """No QMP, child, locks or socket alias; at most two finalize invocations."""
    def __init__(self, run, fail_first=False):
        self.run = run
        self.closed = False
        self.fail_first = fail_first
        self.calls = []
        self.receipts = []

    def _safe_write(self, name, data):
        # Match the guard's best-effort receipt boundary with real host I/O.
        try:
            (self.run / name).write_text(json.dumps(data))
        except OSError as exc:
            self.receipts.append({'name': name, 'error': repr(exc)})

    def finalize(self, **kw):
        self.calls.append(kw)
        if len(self.calls) > 2:
            # execute_runner catches AssertionError; close first to bound its loop.
            # The tests' exact call-count assertions still reject this third call.
            self.closed = True
            raise AssertionError('test guard must finish by its second call')
        if self.fail_first and len(self.calls) == 1:
            # The run does not exist: an actual FileNotFoundError, not a mocked write.
            (self.run / 'guard-first-attempt.json').write_text('{}')
        self.closed = True


class HostExceptionTests(unittest.TestCase):
    def setUp(self):
        self.case = ARTIFACT_ROOT / self._testMethodName
        self.case.mkdir()
        self.run = self.case / 'run'
        self.run.mkdir()
        self.journal = []
        self.extra = {}

    def tearDown(self):
        EVIDENCE.append({'test': self.id(), 'fixture': str(self.case),
                         'memory_journal': self.journal, **self.extra})

    def entry(self):
        matches = [e for e in self.journal if 'host_first_exception' in e]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_success_keeps_memory_and_both_clocks(self):
        exc = original_error()  # Save outside the active exception context.
        before_mono = time.monotonic()
        before_utc = datetime.datetime.now(datetime.timezone.utc)
        rec = write_host_first_exception(self.run, self.journal, exc)
        after_utc = datetime.datetime.now(datetime.timezone.utc)
        self.assertLessEqual(before_mono, rec['host_monotonic'])
        self.assertLessEqual(rec['host_monotonic'], time.monotonic())
        utc = datetime.datetime.fromisoformat(rec['host_utc'])
        self.assertEqual(utc.utcoffset(), datetime.timedelta(0))
        self.assertTrue(rec['host_utc'].endswith('+00:00'))
        self.assertLessEqual(before_utc, utc)
        self.assertLessEqual(utc, after_utc)
        self.assertIn('original_error_leaf', rec['traceback'])
        self.assertIn('ValueError: original-host-observation-error', rec['traceback'])
        self.assertNotIn('NoneType: None', rec['traceback'])
        self.assertIsNone(rec['qmp_send_unknown'])
        self.assertIsNone(rec['qmp_buffered_bytes'])
        self.assertIs(self.entry()['host_first_exception'], rec)
        status = self.entry()['host_first_exception_persistence']
        self.assertEqual(status['status'], 'write_completed')
        self.assertTrue(status['write_completed'])
        self.assertEqual(status['durability'], 'not_verified')
        self.assertEqual(json.loads((self.run / 'host-first-exception.json').read_text()), rec)

    def test_original_traceback_inside_unrelated_except(self):
        exc = original_error()
        try:
            raise RuntimeError('unrelated-cleanup-error')
        except RuntimeError:
            rec = write_host_first_exception(self.run, self.journal, exc)
        self.assertIn('original_error_leaf', rec['traceback'])
        self.assertNotIn('unrelated-cleanup-error', rec['traceback'])

    def test_transport_snapshot_and_continuous_exceptions(self):
        transport = SimpleNamespace(send_unknown=True, buffer=bytearray(b'part'))
        rec = write_host_first_exception(self.run, self.journal, original_error(), transport)
        frozen = copy.deepcopy(rec)
        on_disk = (self.run / 'host-first-exception.json').read_bytes()
        transport.send_unknown = False
        transport.buffer.clear()
        for exc in (OSError('cleanup-error'), KeyboardInterrupt('later-interrupt')):
            self.assertIs(write_host_first_exception(self.run, self.journal, exc), rec)
        self.assertEqual(rec, frozen)
        self.assertEqual((self.run / 'host-first-exception.json').read_bytes(), on_disk)
        self.assertIs(rec, self.entry()['host_first_exception'])
        self.assertTrue(rec['qmp_send_unknown'])
        self.assertEqual(rec['qmp_buffered_bytes'], 4)

    def test_missing_output_parent(self):
        missing = self.case / 'absent-parent' / 'run'
        rec = write_host_first_exception(missing, self.journal, original_error())
        frozen = copy.deepcopy(rec)
        status = self.entry()['host_first_exception_persistence']
        self.assertEqual(status['status'], 'failed')
        self.assertEqual(status['error_type'], 'FileNotFoundError')
        self.assertFalse(status['write_completed'])
        self.assertFalse(missing.parent.exists())
        self.assertIs(write_host_first_exception(missing, self.journal, RuntimeError('later')), rec)
        self.assertEqual(rec, frozen)

    def test_exception_file_path_is_directory(self):
        path = self.run / 'host-first-exception.json'
        path.mkdir()
        rec = write_host_first_exception(self.run, self.journal, original_error())
        self.assertEqual(rec['type'], 'ValueError')
        status = self.entry()['host_first_exception_persistence']
        self.assertEqual(status['status'], 'failed')
        self.assertEqual(status['error_type'], 'IsADirectoryError')
        self.assertFalse(status['write_completed'])
        self.assertTrue(path.is_dir())
        self.assertEqual(list(path.iterdir()), [])

    def test_qmp_write_failure_keeps_original_successful_record(self):
        rec = write_host_first_exception(self.run, self.journal, original_error())
        frozen = copy.deepcopy(rec)
        on_disk = (self.run / 'host-first-exception.json').read_bytes()
        (self.run / 'qmp.json').mkdir()
        with self.assertRaises(IsADirectoryError):
            write_host_journal(self.run, self.journal)
        self.assertEqual(rec, frozen)
        self.assertEqual((self.run / 'host-first-exception.json').read_bytes(), on_disk)
        self.assertEqual(self.journal[-1]['host_journal_persistence']['status'], 'failed')
        self.assertFalse(self.journal[-1]['host_journal_persistence']['write_completed'])
        self.assertEqual(self.entry()['host_first_exception_persistence']['status'], 'write_completed')

    def test_both_writes_fail_and_first_remains(self):
        missing = self.case / 'absent-run'
        rec = write_host_first_exception(missing, self.journal, original_error())
        frozen = copy.deepcopy(rec)
        with self.assertRaises(FileNotFoundError):
            write_host_journal(missing, self.journal)
        self.assertIs(write_host_first_exception(missing, self.journal, OSError('later')), rec)
        self.assertEqual(rec, frozen)
        self.entry()
        self.assertEqual(self.journal[-1]['host_journal_persistence']['status'], 'failed')
        self.assertFalse(missing.exists())

    def test_qmp_write_can_be_first_host_error(self):
        (self.run / 'qmp.json').mkdir()
        with self.assertRaises(IsADirectoryError):
            write_host_journal(self.run, self.journal)
        rec = self.entry()['host_first_exception']
        self.assertEqual(rec['type'], 'IsADirectoryError')
        self.assertIn('write_host_journal', rec['traceback'])
        self.assertEqual(self.entry()['host_first_exception_persistence']['status'], 'write_completed')
        self.assertEqual(self.journal[-1]['host_journal_persistence']['status'], 'failed')

    def test_qmp_success_contains_first_exception_status(self):
        rec = write_host_first_exception(self.run, self.journal, original_error())
        status = write_host_journal(self.run, self.journal)
        disk_journal = json.loads((self.run / 'qmp.json').read_text())
        self.assertEqual(disk_journal[0]['host_first_exception'], rec)
        self.assertEqual(disk_journal[0]['host_first_exception_persistence']['status'], 'write_completed')
        self.assertEqual(status['status'], 'write_completed')
        self.assertTrue(status['write_completed'])
        self.assertNotIn('host_journal_persistence', disk_journal[-1])

    def test_broken_stderr_does_not_replace_original(self):
        class BrokenStderr:
            def write(self, value):
                raise OSError('stderr-unavailable')
        with contextlib.redirect_stderr(BrokenStderr()):
            rec = write_host_first_exception(self.case / 'absent-run', self.journal, original_error())
        self.assertEqual(rec['type'], 'ValueError')
        self.assertEqual(self.entry()['host_first_exception_persistence']['error_type'], 'FileNotFoundError')

    def test_execute_main_error_missing_output_still_finalizes(self):
        missing = self.case / 'absent-parent' / 'run'
        guard, sleeps = FakeGuard(missing), []
        env = extract_execute(self.journal, guard, sleeps)
        def fake_main():
            original_error_leaf()
        self.assertEqual(env['execute_runner'](fake_main, guard_retry_seconds=.01, reap_wait=.05), 2)
        self.assertTrue(guard.closed)
        self.assertEqual(len(guard.calls), 1)
        self.assertTrue(guard.calls[0]['diagnostics'])
        self.assertEqual(sleeps, [])
        self.assertEqual(self.entry()['host_first_exception']['type'], 'ValueError')
        self.assertEqual(self.entry()['host_first_exception_persistence']['error_type'], 'FileNotFoundError')
        self.assertIs(env['ACTIVE_HOST_JOURNAL'], self.journal)
        self.assertFalse(missing.parent.exists())
        self.extra.update(guard_calls=guard.calls, sleeps=sleeps, guard_closed=guard.closed)

    def test_patched_handler_then_cleanup_and_guard_retry_keep_first(self):
        missing = self.case / 'absent-parent' / 'run'
        guard, sleeps = FakeGuard(missing, fail_first=True), []
        env = extract_execute(self.journal, guard, sleeps)
        class FailingTrial:
            def fail(self, message):
                (missing / 'trial-fail.json').write_text(message)
        frozen = {}
        def fake_main():
            try:
                original_error_leaf()
            except ValueError as exc:
                try:
                    env['host_handler'](missing, self.journal, exc, None, FailingTrial())
                finally:
                    frozen.update(copy.deepcopy(self.entry()['host_first_exception']))
        self.assertEqual(env['execute_runner'](fake_main, guard_retry_seconds=.01, reap_wait=.05), 2)
        self.assertTrue(guard.closed)
        self.assertEqual(len(guard.calls), 2)
        self.assertEqual([c['diagnostics'] for c in guard.calls], [True, False])
        self.assertEqual([c['reap_wait'] for c in guard.calls], [.05, .05])
        self.assertEqual(sleeps, [.01])
        self.assertEqual(self.entry()['host_first_exception'], frozen)
        self.assertEqual(frozen['type'], 'ValueError')
        self.assertIn('original_error_leaf', frozen['traceback'])
        self.assertFalse(missing.parent.exists())
        self.extra.update(guard_calls=guard.calls, sleeps=sleeps, guard_closed=guard.closed,
                          executed_patched_handler=True)


if __name__ == '__main__':
    PATCHED_SOURCE, patch_receipt = verify()
    fixtures = HERE / 'offline-cases'
    fixtures.mkdir(exist_ok=True)
    ARTIFACT_ROOT = Path(tempfile.mkdtemp(prefix='host-', dir=fixtures))
    output, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(stderr):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(HostExceptionTests))
    receipt = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
               'failures': len(result.failures), 'errors': len(result.errors),
               'output': output.getvalue(), 'captured_stderr': stderr.getvalue(),
               'evidence': EVIDENCE, 'fixture_root': str(ARTIFACT_ROOT),
               'patched_source_sha256': patch_receipt['applied_source_sha256'],
               'full_runner_imported': False, 'vm_started': False,
               'actual_child_reaping_or_locks_tested': False,
               'bounded_fake_guard_control_flow_tested': True,
               'integration_status': 'not_integrated'}
    (HERE / 'OFFLINE-TEST-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(output.getvalue(), end='')
    sys.exit(0 if result.wasSuccessful() else 1)
