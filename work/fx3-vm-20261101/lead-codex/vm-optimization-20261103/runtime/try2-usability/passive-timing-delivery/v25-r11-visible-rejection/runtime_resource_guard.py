"""Host-only lifetime guard for one existing FX3 QEMU process.

It owns a short /tmp alias for both local Unix sockets. An exception while
connecting, logging, sampling, or writing a receipt cannot release run locks
before the known child is gone and waited. It never starts a second guest.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path


class ShortRunSockets:
    def __init__(self, run: Path):
        self.run = Path(run).resolve()
        self.root = Path(tempfile.mkdtemp(prefix='fx3-sock-', dir='/tmp'))
        self.alias = self.root / 'r'
        os.symlink(self.run, self.alias, target_is_directory=True)

    def path(self, name: str) -> str:
        if name not in ('q', 'g'):
            raise ValueError('only reviewed local QMP/GDB sockets')
        value = str(self.alias / name)
        if len(os.fsencode(value)) >= 100:
            raise RuntimeError('short AF_UNIX alias exceeded bound')
        return value

    def close(self):
        # Only the alias created here is removed. Never follow the symlink.
        try:
            self.alias.unlink(missing_ok=True)
            self.root.rmdir()
        except FileNotFoundError:
            pass


class RuntimeResourceGuard:
    def __init__(self, run: Path, *, socket_alias: ShortRunSockets | None = None):
        self.run = Path(run)
        self.alias = socket_alias or ShortRunSockets(run)
        self.locks = []
        self.process = None
        self.qmp = None
        self.input_gate = None
        self.closed = False
        self.cleanup_attempted = False
        self.process_reaped = False
        self.events = []

    def add_lock(self, file):
        self.locks.append(file)

    def set_process(self, process):
        if self.process is not None:
            raise RuntimeError('one resource guard cannot own two guests')
        self.process = process

    def set_qmp(self, qmp):
        self.qmp = qmp

    def set_input_gate(self, gate):
        self.input_gate = gate

    def _record(self, name, **data):
        self.events.append({'event': name, 'host_monotonic': time.monotonic(), **data})

    def _safe_write(self, name: str, data):
        try:
            (self.run / name).write_text(json.dumps(data, indent=2) + '\n')
        except Exception as exc:
            self._record('receipt_write_error', file=name, error=repr(exc))

    def _get_qmp(self):
        if self.qmp is not None:
            return self.qmp, None
        from qmp_line_transport import QmpLineTransport
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            sock.connect(self.alias.path('q'))
            transport = QmpLineTransport(sock, [], started=time.monotonic())
            greeting = transport.read_json()
            response = transport.command('qmp_capabilities')
            if 'error' in response:
                raise RuntimeError('QMP capabilities error: ' + repr(response))
            self._record('qmp_reconnected', greeting=bool(greeting))
            return transport.command, sock
        except Exception:
            sock.close()
            raise

    def _wait_or_signal(self, process, sig, timeout: float):
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            pass
        except Exception as exc:
            self._record('process_wait_error', signal=sig, error=repr(exc))
            return False
        if process.poll() is None:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass  # exited between poll and killpg; still wait/reap
            except Exception as exc:
                self._record('process_signal_error', signal=sig, error=repr(exc))
                return False
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False
        except Exception as exc:
            self._record('process_wait_error', signal=sig, error=repr(exc))
            return False

    def finalize(self, *, reason: str, diagnostics=True, capture_fn=None,
                 task_fn=None, vcpu_fn=None, restore_fn=None, reap_wait: float = 3):
        if self.closed:
            return
        if not 0 < reap_wait <= 3:
            raise ValueError('reap_wait must be bounded at at most 3 seconds')
        p = self.process
        self._record('guard_enter', reason=reason, pid=None if p is None else p.pid,
                     locks_held=sum(not f.closed for f in self.locks))
        qmp = self.qmp
        opened = None
        try:
            if not self.cleanup_attempted and p is not None and p.poll() is None:
                self.cleanup_attempted = True
                if qmp is None:
                    try:
                        qmp, opened = self._get_qmp()
                    except Exception as exc:
                        self._record('qmp_connect_error', error=repr(exc))
                if qmp is not None:
                    try:
                        from quiesced_diag_readback import capture as default_capture
                        fn = capture_fn or default_capture
                        if not (self.run / 'osd-ring-final.bin').exists():
                            result = fn(qmp, self.run)
                            self._record('core_ring_capture', consistent=result.get('consistent', False))
                        else:
                            self._record('core_ring_existing')
                    except Exception as exc:
                        self._record('core_ring_capture_error', error=repr(exc))
                    if diagnostics:
                        for label, supplied, module, symbol in (
                            ('tasks', task_fn, 'procdiag_readback', 'capture'),
                            ('vcpus', vcpu_fn, 'quiesced_diag_readback', 'capture_optional_vcpus')):
                            try:
                                fn = supplied
                                if fn is None:
                                    import importlib
                                    fn = getattr(importlib.import_module(module), symbol)
                                result = fn(qmp, self.run)
                                self._record(label + '_capture', available=result.get('available'), complete=result.get('complete'))
                            except Exception as exc:
                                self._record(label + '_capture_error', error=repr(exc))
                    try:
                        from restore_api103_v2 import restore_native_api
                        from gate_input_usability import InputGate
                        gate = self.input_gate or InputGate(self.run, delete_key=0x1f8, max_steps=4096,
                                                            socket_path=self.alias.path('g'))
                        fn = restore_fn or restore_native_api
                        if not (self.run / 'restore103-receipt.json').exists():
                            result = fn(qmp, gate, self.run, timeout=20)
                            self._record('api16_restore', passed=result.get('passed', False), reason=result.get('reason'))
                    except Exception as exc:
                        self._record('api16_restore_error', error=repr(exc))
                    try:
                        response = qmp('quit')
                        self._record('qmp_quit', response=response)
                    except Exception as exc:
                        self._record('qmp_quit_error', error=repr(exc))
            if p is not None and not self.process_reaped:
                if not self._wait_or_signal(p, signal.SIGTERM, reap_wait):
                    self._record('term_or_wait_failed')
                    if not self._wait_or_signal(p, signal.SIGKILL, reap_wait):
                        self._record('kill_or_wait_failed')
                try:
                    p.wait(timeout=0)
                    self.process_reaped = True
                    self._record('process_reaped', pid=p.pid, returncode=p.returncode)
                except Exception as exc:
                    self._record('process_reap_error', error=repr(exc))
            elif p is None:
                self.process_reaped = True
        finally:
            if opened is not None:
                try: opened.close()
                except OSError: pass
            if self.input_gate is not None and self.input_gate.sock is not None:
                try: self.input_gate.sock.close()
                except OSError: pass
            if not self.process_reaped:
                self._record('cleanup_pending_unreaped', pid=None if p is None else p.pid,
                             locks_held=sum(not f.closed for f in self.locks))
                self._safe_write('resource-guard-pending.json',
                                 {'reason': reason, 'pid': None if p is None else p.pid,
                                  'process_reaped': False, 'locks_held': sum(not f.closed for f in self.locks),
                                  'events': self.events})
            else:
                for file in self.locks:
                    if not file.closed:
                        try:
                            import fcntl
                            fcntl.flock(file, fcntl.LOCK_UN)
                        except Exception as exc:
                            self._record('unlock_error', error=repr(exc))
                        finally:
                            file.close()
                try: self.alias.close()
                except Exception as exc: self._record('socket_alias_cleanup_error', error=repr(exc))
                self.closed = True
                self._safe_write('resource-guard-receipt.json',
                                 {'reason': reason, 'events': self.events,
                                  'process_reaped': self.process_reaped,
                                  'locks_released_after_reap': self.process_reaped})
        return self.closed
