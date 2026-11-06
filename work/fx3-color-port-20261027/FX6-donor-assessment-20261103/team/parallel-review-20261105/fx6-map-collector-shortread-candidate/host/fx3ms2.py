#!/usr/bin/env python3
"""Strict host-side decoder/provider for the FX3MS2 bounded sequential read.

FX3MS2 is explicitly snapshot_atomic=0: it is a complete byte stream captured
by repeated reads, not an atomic kernel map snapshot.  This module rejects
legacy FX3MS1 frames and never falls back to raw maps.
"""
import base64
import hashlib
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapping_parser as M

MAX_CAP = 262144
MIN_CAP = 4096
MAX_READS = 1024
MAX_MS = 10000
MAX_EINTR = 32
MAX_FRAMES = 16
MAX_LINES = 200000
MAX_LINE = 65536
MAX_NOISE = 20000
MAX_CHUNK_B64 = 4096
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211

BEGIN_FIELDS = ('pid', 'starttime', 'seq', 'cap', 'max_reads', 'max_ms', 'capture')
END_FIELDS = ('pid', 'starttime', 'seq', 'bytes', 'lines', 'digest',
              'read_count', 'eintr_count', 'read_attempts', 'eof_observed',
              'identity_before', 'identity_after', 'snapshot_atomic',
              'line_terminated', 'complete', 'cap_hit', 'read_limit_hit',
              'time_limit_hit')
ERROR_FIELDS = ('pid', 'starttime', 'seq', 'reason', 'read_count', 'bytes',
                'eintr_count', 'read_attempts', 'elapsed_ms')


class Reject(ValueError):
    """A complete frame is structurally or semantically invalid."""
    def __init__(self, reason):
        self.reason = str(reason)
        super().__init__(self.reason)


class Retryable(Reject):
    """A complete newline frontier has no usable frame yet; wait for more."""


class NoAppFwFrame(Retryable):
    """A valid complete frame is present but has no appFw rows yet."""


class CollectorError(Reject):
    """The guest collector explicitly reported a failure."""
    def __init__(self, reason, fields):
        self.fields = fields
        super().__init__('collector ERROR: ' + str(reason))


def _num(v, name, lo=None, hi=None):
    if len(v) > 20:
        raise Reject('%s too long' % name)
    try:
        n = int(v, 10)
    except (TypeError, ValueError):
        raise Reject('bad numeric %s=%r' % (name, v[:40]))
    if lo is not None and n < lo:
        raise Reject('%s out of range' % name)
    if hi is not None and n > hi:
        raise Reject('%s out of range' % name)
    return n


def _kv(parts, required):
    if len(parts) != len(required):
        raise Reject('field count')
    d = {}
    for p in parts:
        if '=' not in p:
            raise Reject('field without =')
        k, v = p.split('=', 1)
        if not k or not v or k in d:
            raise Reject('bad/duplicate field')
        d[k] = v
    if set(d) != set(required):
        raise Reject('unexpected fields')
    return d


def fnv1a64(b):
    h = FNV_OFFSET
    for x in b:
        h = (h ^ x) * FNV_PRIME & 0xffffffffffffffff
    return h


def decode(text):
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        raise Reject('too many input lines')
    cur = None
    latest = None
    frame_count = 0
    noise = 0
    first_id = None
    last_seq = None
    for raw in lines:
        if len(raw) > MAX_LINE:
            raise Reject('line too long')
        if raw.startswith('FX3MS1'):
            raise Reject('legacy FX3MS1 frame not accepted')
        if not raw.startswith('FX3MS2 '):
            noise += 1
            if noise > MAX_NOISE:
                raise Reject('too much console noise')
            continue
        parts = raw.split()
        if len(parts) < 2:
            raise Reject('bad FX3MS2 line')
        typ = parts[1]
        if typ == 'BEGIN':
            if cur is not None:
                raise Reject('BEGIN before prior END')
            d = _kv(parts[2:], BEGIN_FIELDS)
            pid = _num(d['pid'], 'pid', 1, 2147483647)
            st = _num(d['starttime'], 'starttime', 0)
            seq = _num(d['seq'], 'seq', 0)
            cap = _num(d['cap'], 'cap', MIN_CAP, MAX_CAP)
            mr = _num(d['max_reads'], 'max_reads', 1, MAX_READS)
            mm = _num(d['max_ms'], 'max_ms', 1, MAX_MS)
            if d['capture'] != 'bounded_sequential_read':
                raise Reject('bad capture')
            if first_id is not None and (pid, st) != first_id:
                raise Reject('mixed PID/starttime frames')
            if last_seq is not None and seq <= last_seq:
                raise Reject('duplicate/out-of-order sequence')
            first_id = (pid, st)
            last_seq = seq
            cur = {'pid': pid, 'starttime': st, 'seq': seq, 'cap': cap,
                   'max_reads': mr, 'max_ms': mm, 'blob': bytearray(), 'next': 0}
        elif typ == 'DATA':
            if cur is None:
                raise Reject('DATA without BEGIN')
            if len(parts) != 7:
                raise Reject('DATA token count')
            i = _num(parts[2], 'DATA index', 0, 1000000)
            dpid = _num(parts[3], 'DATA pid', 1, 2147483647)
            dst = _num(parts[4], 'DATA starttime', 0)
            dseq = _num(parts[5], 'DATA seq', 0)
            if (dpid, dst, dseq) != (cur['pid'], cur['starttime'], cur['seq']):
                raise Reject('DATA identity mismatch')
            if i != cur['next']:
                raise Reject('DATA out of order/duplicate')
            enc = parts[6]
            if not enc or len(enc) % 4 or len(enc) > MAX_CHUNK_B64:
                raise Reject('DATA base64 size')
            try:
                rawb = base64.b64decode(enc, validate=True)
            except Exception:
                raise Reject('DATA base64')
            if not rawb:
                raise Reject('empty DATA chunk')
            if len(cur['blob']) + len(rawb) >= cur['cap']:
                raise Reject('data reaches/exceeds cap')
            cur['blob'].extend(rawb)
            cur['next'] += 1
        elif typ == 'END':
            if cur is None:
                raise Reject('END without BEGIN')
            d = _kv(parts[2:], END_FIELDS)
            if (d['pid'], d['starttime'], d['seq']) != (str(cur['pid']), str(cur['starttime']), str(cur['seq'])):
                raise Reject('identity change')
            if d['eof_observed'] != '1':
                raise Reject('EOF not observed')
            expect_id = '%d:%d' % (cur['pid'], cur['starttime'])
            if d['identity_before'] != expect_id or d['identity_after'] != expect_id:
                raise Reject('identity_before/after mismatch')
            if d['snapshot_atomic'] != '0':
                raise Reject('atomic snapshot claim unsupported')
            if d['line_terminated'] != '1':
                raise Reject('unterminated flag')
            if d['complete'] != '1':
                raise Reject('incomplete flag')
            for flag in ('cap_hit', 'read_limit_hit', 'time_limit_hit'):
                if d[flag] != '0':
                    raise Reject(flag + ' set')
            read_count = _num(d['read_count'], 'read_count', 1, cur['max_reads'])
            eintr = _num(d['eintr_count'], 'eintr_count', 0, MAX_EINTR)
            attempts = _num(d['read_attempts'], 'read_attempts', 1, 1000000)
            if attempts != read_count + eintr + 1:
                raise Reject('read attempt accounting')
            blob = bytes(cur['blob'])
            if not blob:
                raise Reject('empty payload')
            if len(blob) != _num(d['bytes'], 'bytes'):
                raise Reject('length mismatch')
            if len(blob) >= cur['cap']:
                raise Reject('payload reaches/exceeds cap')
            if blob[-1:] != b'\n':
                raise Reject('payload final byte not newline')
            if blob.count(b'\n') != _num(d['lines'], 'lines'):
                raise Reject('line count mismatch')
            if d['digest'] != 'fnv1a64:%016x' % fnv1a64(blob):
                raise Reject('digest mismatch')
            if frame_count >= MAX_FRAMES:
                raise Reject('too many frames')
            frame_count += 1
            latest = (cur, d, read_count, eintr, attempts, blob)
            cur = None
        elif typ == 'ERROR':
            d = _kv(parts[2:], ERROR_FIELDS)
            raise CollectorError(d['reason'], d)
        else:
            raise Reject('unknown frame ' + typ)
    if cur is not None:
        raise Retryable('missing END')
    if latest is None:
        raise Retryable('no complete frame')
    f, end, read_count, eintr, attempts, blob = latest
    return {
        'pid': f['pid'],
        'starttime': f['starttime'],
        'seq': f['seq'],
        'cap': f['cap'],
        'max_reads': f['max_reads'],
        'max_ms': f['max_ms'],
        'bytes': len(blob),
        'lines': blob.count(b'\n'),
        'digest': 'fnv1a64:%016x' % fnv1a64(blob),
        'maps_sha256': hashlib.sha256(blob).hexdigest(),
        'maps_text': blob.decode('utf-8', 'replace'),
        'frame_count': frame_count,
        'selected_seq': f['seq'],
        'read_count': read_count,
        'eintr_count': eintr,
        'read_attempts': attempts,
        'eof_observed': True,
        'snapshot_atomic': False,
        'line_terminated': True,
        'console_noise_lines': noise,
        'note': 'complete bounded sequential read; not an atomic kernel snapshot and not boot/menu proof',
    }


class FramedProviderV2:
    def __init__(self, elf_path=M.APP_ELF, cpio_path=None, cpio_sha=None):
        self.elf_path = elf_path
        self.cpio_path = cpio_path
        self.cpio_sha = cpio_sha
        self.last = None

    def select(self, text):
        d = decode(text)
        rows = []
        for line in d['maps_text'].splitlines():
            m = M.MAP.match(line.encode())
            if m:
                rows.append({'start': int(m.group(1), 16), 'end': int(m.group(2), 16),
                             'perms': m.group(3).decode(), 'offset': int(m.group(4), 16),
                             'inode': int(m.group(5)), 'path': m.group(6).decode()})
        app = [r for r in rows if r['path'] == M.AP_PATH.decode()]
        if not app:
            raise NoAppFwFrame('framed payload has no appFw rows')
        try:
            ap = M.map_bias(rows, M.AP_PATH.decode(), M.elf_loads(self.elf_path))
        except M.MapParserError as e:
            raise Reject('map_bias: %s: %s' % (e.code, e.message))
        except Exception as e:
            raise Reject('map_bias: ' + repr(e))
        b = Path(self.elf_path).read_bytes()
        if hashlib.sha256(b).hexdigest() != M.APPFW_SHA256:
            raise Reject('APP_ELF hash mismatch')
        phoff = int.from_bytes(b[32:40], 'little')
        es = int.from_bytes(b[54:56], 'little')
        n = int.from_bytes(b[56:58], 'little')
        checks = [('header', 0, 64, False), ('phdr', phoff, es * n, False)]
        checks += [('code', k['thunk_va'], 4, True) for k in M.KEYS]
        checks += [('code', k['return_va'], 4, True) for k in M.KEYS]
        for name, va, size, needx in checks:
            addr = ap['bias'] + va
            hits = [r for r in app if r['start'] <= addr and addr + size <= r['end']]
            if not hits:
                raise Reject('unmapped ' + name)
            if 'r' not in hits[0]['perms']:
                raise Reject('unreadable ' + name)
            if needx and 'x' not in hits[0]['perms']:
                raise Reject('nonexec ' + name)
        try:
            for k in M.KEYS:
                for va, w in ((k['thunk_va'], k['thunk_word']), (k['return_va'], k['return_word'])):
                    if M.word_at(self.elf_path, va).hex() != w:
                        raise Reject('static word mismatch')
        except M.MapParserError as e:
            raise Reject('static word: %s: %s' % (e.code, e.message))
        self.last = {'pid': d['pid'], 'seq': d['selected_seq'], 'bias': ap['bias'],
                     'frames': d['frame_count'], 'read_count': d['read_count'],
                     'eintr_count': d['eintr_count'], 'snapshot_atomic': False}
        return {'pid': d['pid'], 'starttime': d['starttime'], 'epoch': None,
                'ap': ap, 'appfw_tids': [], 'block_byte_range': [0, 0],
                'framed': True, 'frame_seq': d['selected_seq'],
                'frame_count': d['frame_count'], 'read_count': d['read_count'],
                'eintr_count': d['eintr_count'], 'read_attempts': d['read_attempts'],
                'snapshot_atomic': False, 'cpio_sha256': self.cpio_sha,
                'maps_sha256': d['maps_sha256']}


def _remaining(deadline):
    if deadline is None:
        return 150.0
    for name in ('remaining_observation', 'remaining_total'):
        try:
            return max(0.0, float(getattr(deadline, name)()))
        except Exception:
            pass
    return 0.0


def wait_mapping(provider, serial, deadline=None):
    """Wait for a complete newline frontier, then select the latest valid frame.

    A non-empty unterminated tail is held; a valid older frame is never
    returned while a tail is present.  Complete malformed frames/collector
    errors are rejected immediately; a complete frame with no appFw rows is
    retryable (the guest may not have loaded appFw yet).
    """
    last = 'none'
    serial = Path(serial)
    while True:
        raw = serial.read_bytes()
        lines = raw.split(b'\n')
        complete = b'\n'.join(lines[:-1]) + (b'\n' if len(lines) > 1 else b'')
        tail = lines[-1]
        if tail:
            last = 'incomplete tail'
        elif complete:
            text = complete.decode('utf-8', 'replace')
            try:
                return provider.select(text)
            except Retryable as e:
                last = str(e)
        else:
            last = 'no complete frame'
        rem = _remaining(deadline)
        if rem <= 0:
            raise TimeoutError('no complete framed map before deadline: ' + last)
        time.sleep(min(0.05, rem))
