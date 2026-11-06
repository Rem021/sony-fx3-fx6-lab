"""Typed bridge for our marked SDK-vtable fixture only.

The real owner must call the C adapter in its own address space. This module has
no live pointer importer, root launcher, IOKit loader or cross-process pointer API.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import ctypes as C
import json
import math
import os
import threading

HERE = Path(__file__).resolve().parent
N = 516
STATUSES = ('OK', 'DENIED', 'BUSY', 'STALL', 'TIMEOUT', 'GONE', 'ERROR', 'SHORT',
            'BAD_COUNT', 'BUFFER', 'LATE', 'CLOCK', 'OWNER', 'LIMIT', 'DEADLINE',
            'SHAPE', 'TOKEN', 'CANCEL')
HARD = {1, 4, 5, 6, 8, 9, 10, 11, 12, 16}


class Rejected(ValueError):
    pass


class NativeResult(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in (
        'abi', 'status', 'operation', 'requested', 'actual_known', 'reported_count',
        'timeout_ms', 'native_returned')] + [('raw_return', C.c_int32)] + [
        (n, C.c_uint32) for n in ('buffer_ok', 'owner_ok', 'body_effect_proven')]


@dataclass(frozen=True, eq=False)
class ContextRef:
    creator_pid: int
    generation: int
    mode: str
    backend: str = field(default='SDK_IOKIT650_OWN_FIXTURE', init=False)
    _address: int = field(default=0, repr=False)


class FixtureLibrary:
    """Own every fixture allocation until its synchronous call actually returns."""
    def __init__(self):
        receipt = json.loads((HERE/'wire-build-receipt.json').read_text())
        for rec in receipt['sources']:
            if sha256((HERE/rec['path']).read_bytes()).hexdigest() != rec['sha256']:
                raise Rejected('fixture source changed since build')
        rec = receipt['fixture']
        path = HERE/'artifacts-v5/fake-iokit.dylib'
        if sha256(path.read_bytes()).hexdigest() != rec['sha256']:
            raise Rejected('fixture binary changed since build')
        self.library = C.CDLL(str(path))  # This DSO only links libSystem.
        self.pid = os.getpid()
        self._registry_guard = threading.RLock()
        self.refs = {}
        self._locks = {}
        self._tokens = {}
        ptr, u32, u64, byte = C.c_void_p, C.c_uint32, C.c_uint64, C.POINTER(C.c_ubyte)
        specs = {
            'fx3_iokit_fixture_marker': ([], u32),
            'fx3_iokit_fixture_create': ([u32, u64, C.c_int], ptr),
            'fx3_iokit_fixture_dispose': ([ptr], C.c_int),
            'fx3_iokit_fixture_fault': ([ptr, u32, u32], C.c_int),
            'fx3_iokit_fixture_reply': ([ptr, byte, u32], C.c_int),
            'fx3_iokit_fixture_sent': ([ptr, byte, u32], C.c_int),
            'fx3_iokit_fixture_stat': ([ptr, u32], u64),
            'fx3_iokit_fixture_release': ([ptr], None),
            'fx3_iokit_fixture_clock': ([ptr, u64], C.c_int),
            'fx3_iokit_fixture_owner': ([ptr, u32, u64], C.c_int),
            'fx3_io_pending': ([ptr], u32),
            'fx3_io_refresh': ([ptr, u64], C.c_int),
            'fx3_io_invalidate': ([ptr, u64], C.c_int),
            'fx3_io_control': ([ptr, u64, u64, byte, u64, u32, C.POINTER(NativeResult)], C.c_int),
            'fx3_io_out': ([ptr, u64, u64, byte, u32, u64, u32, C.POINTER(NativeResult)], C.c_int),
            'fx3_io_in': ([ptr, u64, u64, byte, u32, u64, u32, C.POINTER(NativeResult)], C.c_int),
        }
        for name, (args, restype) in specs.items():
            fn = getattr(self.library, name)
            fn.argtypes, fn.restype = args, restype
        if self.library.fx3_iokit_fixture_marker() != 0x494f4649 or C.sizeof(NativeResult) != 48:
            raise Rejected('wrong fixture marker or result ABI')

    def validate(self, ref, mode=None):
        if self.pid != os.getpid() or type(ref) is not ContextRef or ref.creator_pid != self.pid or \
           self.refs.get(id(ref)) is not ref or mode is not None and mode != ref.mode:
            raise Rejected('unregistered, foreign-process, disposed or wrong-mode IOKit context')

    @contextmanager
    def hold(self, ref):
        with self._registry_guard:
            self.validate(ref)
            lock = self._locks[id(ref)]
            if not lock.acquire(blocking=False):
                raise Rejected('fixture operation still pending; no close, retry or wait')
        try:
            self.validate(ref)
            yield ref._address
        finally:
            lock.release()

    def create(self, mode='MSC', generation=1, reverse=False):
        if self.pid != os.getpid() or mode not in ('MSC', 'SERVICE') or \
           type(generation) is not int or not 0 < generation < 2**64 or type(reverse) is not bool:
            raise Rejected('invalid fixture allocation')
        address = self.library.fx3_iokit_fixture_create(1 if mode == 'MSC' else 2, generation, reverse)
        if not address:
            raise Rejected('fixture bind failed')
        ref = ContextRef(self.pid, generation, mode, _address=address)
        self.refs[id(ref)] = ref
        self._locks[id(ref)] = threading.Lock()
        self._tokens[id(ref)] = 0
        return ref

    def _metadata(self, ref, name, *args):
        with self.hold(ref) as ptr:
            return getattr(self.library, name)(ptr, *args)

    def refresh(self, ref):
        return self._metadata(ref, 'fx3_io_refresh', ref.generation)

    def invalidate(self, ref):
        return self._metadata(ref, 'fx3_io_invalidate', ref.generation)

    def dispose(self, ref):
        with self.hold(ref) as ptr:
            with self._registry_guard:
                result = self.library.fx3_iokit_fixture_dispose(ptr)
                if result == 0:
                    del self.refs[id(ref)]
                    del self._tokens[id(ref)]
                    del self._locks[id(ref)]
                return result

    def fault(self, ref, op, fault):
        return self._metadata(ref, 'fx3_iokit_fixture_fault', op, fault)

    def owner(self, ref, active, generation):
        return self._metadata(ref, 'fx3_iokit_fixture_owner', active, generation)

    def set_clock(self, ref, seconds):
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds < 2**63/1e9:
            raise Rejected('invalid fixture clock')
        return self._metadata(ref, 'fx3_iokit_fixture_clock', int(seconds*1e9))

    def stat(self, ref, index):
        # Only atomic entered/pending can be read concurrently with our fake call.
        if index == 17:
            with self._registry_guard:
                self.validate(ref)
                return self.library.fx3_iokit_fixture_stat(ref._address, index)
        return self._metadata(ref, 'fx3_iokit_fixture_stat', index)

    def release(self, ref):
        # Explicit release of our own blocking fixture; never an IOKit cancellation.
        with self._registry_guard:
            self.validate(ref)
            self.library.fx3_iokit_fixture_release(ref._address)

    def pending(self, ref):
        with self._registry_guard:
            self.validate(ref)
            return self.library.fx3_io_pending(ref._address)

    def set_reply(self, ref, packet):
        if type(packet) is not bytes or len(packet) != N:
            raise Rejected('fixture reply must be exactly516 immutable bytes')
        buf = (C.c_ubyte*N).from_buffer_copy(packet)
        return self._metadata(ref, 'fx3_iokit_fixture_reply', buf, N)

    def sent(self, ref):
        buf = (C.c_ubyte*N)()
        if self._metadata(ref, 'fx3_iokit_fixture_sent', buf, N):
            raise Rejected('fixture snapshot rejected')
        return bytes(buf)

    def transfer(self, ref, operation, payload, deadline, timeout):
        if operation not in ('CONTROL', 'BULK_OUT', 'BULK_IN') or \
           type(payload) is not bytes or len(payload) != (8 if operation == 'CONTROL' else N) or \
           type(deadline) not in (int, float) or not math.isfinite(deadline) or not 0 < deadline < 2**63/1e9 or \
           type(timeout) is not int or not 1 <= timeout <= 1000:
            raise Rejected('invalid bounded call shape or deadline')
        with self.hold(ref) as ptr:
            token = self._tokens[id(ref)] + 1
            self._tokens[id(ref)] = token
            result = NativeResult()
            buf = (C.c_ubyte*len(payload)).from_buffer_copy(payload)
            common = [ptr, ref.generation, token, buf]
            if operation != 'CONTROL':
                common.append(N)
            common.extend([int(deadline*1e9), timeout, C.byref(result)])
            function = {'CONTROL': 'fx3_io_control', 'BULK_OUT': 'fx3_io_out', 'BULK_IN': 'fx3_io_in'}[operation]
            status = getattr(self.library, function)(*common)
            if result.abi != 1 or status != result.status or not 0 <= status < len(STATUSES):
                raise Rejected('native result ABI mismatch')
            public = {name: getattr(result, name) for name, unused in result._fields_}
            public['adapter_status'] = STATUSES[status]
            public['actual_count_known'] = bool(result.actual_known)
            public['transferred'] = result.reported_count if result.actual_known else None
            # A reported count on error is metadata, never valid received data.
            reply = bytes(buf) if operation == 'BULK_IN' and status == 0 else b''
            return public, reply
