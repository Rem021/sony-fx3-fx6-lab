"""Best-effort paused readback of an optional guest /proc diagnostic.

The fixed r3 guest has no PCDSING1 producer. Its absence is evidence of a
missing channel, never evidence that a guest task was runnable or blocked.
"""
from __future__ import annotations

import hashlib
import json
import struct
import time
from pathlib import Path

ADDRESS = 0x41df00000
SIZE = 0x10000
MAGIC = 0x31474e4953444350
SLOT_BYTES = 0x6000
SLOTS = (0xa000,)
TEXT_CAP = SLOT_BYTES - 64


def fnv(data: bytes) -> int:
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return value


def parse(raw: bytes) -> dict:
    if len(raw) != SIZE:
        return {'available': False, 'reason': 'wrong_snapshot_size'}
    magic, latest, outstanding, dropped = struct.unpack_from('<QQII', raw, 0x9000)
    if magic != MAGIC:
        return {'available': False, 'reason': 'diagnostic_not_loaded_or_no_capture',
                'magic_seen': f'0x{magic:016x}'}
    slots = []
    for offset in SLOTS:
        seq, length, step, done, begin_ns, digest = struct.unpack_from('<QIII4xQQ', raw, offset)
        trailer = struct.unpack_from('<Q', raw, offset + SLOT_BYTES - 8)[0]
        valid = bool(seq and not seq & 1 and seq == trailer and length < TEXT_CAP)
        text = raw[offset + 40:offset + 40 + length] if valid else b''
        valid = valid and fnv(text) == digest
        slots.append({'offset': offset, 'valid': valid, 'sequence': seq // 2 if valid else None,
                      'step': step if valid else None, 'done': done if valid else None,
                      'guest_monotonic_begin_ns': begin_ns if valid else None,
                      'text': text.decode('utf-8', errors='replace') if valid else None})
    matched = [s for s in slots if s['valid'] and s['sequence'] == latest]
    return {'available': bool(matched), 'reason': 'validated_latest_slot' if matched else 'missing_or_torn_latest_slot',
            'latest_sequence': latest, 'outstanding_reader_children': outstanding,
            'dropped_text_writes': dropped, 'slots': slots,
            'packet_integrity_complete': bool(matched) and dropped == 0}


def capture(qmp, run: Path, *, budget: float = 6.0, clock=time.monotonic) -> dict:
    """Do not throw on absent helper or optional QMP failure."""
    record = {'available': False, 'read_only': True, 'paused_state_required': True,
              'reason': 'not_attempted', 'errors': []}
    if not 0 < budget <= 10:
        raise ValueError('invalid optional task readback budget')
    deadline = clock() + budget
    path = run / 'procdiag-final-key93.bin'
    receipt = run / 'procdiag-final-readback.json'
    if path.exists() or receipt.exists():
        record['reason'] = 'existing_artifact_not_overwritten'
        return record
    try:
        def ask(name, arguments=None):
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError('optional task snapshot deadline')
            return qmp(name, arguments, timeout=remaining)
        state_response = ask('query-status')
        state = state_response.get('return') if isinstance(state_response, dict) else None
        if not isinstance(state, dict) or state.get('running') is not False or state.get('status') != 'paused':
            record['reason'] = 'not_provably_paused'
            return record
        response = ask('human-monitor-command', {
            'command-line': f'pmemsave {ADDRESS:#x} {SIZE:#x} "{path}"'})
        if not isinstance(response, dict) or 'error' in response or 'return' not in response:
            record['reason'] = 'pmemsave_qmp_error'
            record['errors'].append(repr(response))
            return record
        if not path.is_file() or path.stat().st_size != SIZE:
            record['reason'] = 'missing_or_short_snapshot'
            return record
        raw = path.read_bytes()
        record.update(parse(raw))
        record['bytes'] = len(raw)
        record['sha256'] = hashlib.sha256(raw).hexdigest()
        record['path'] = str(path)
        record['consistent_memory'] = True
    except Exception as exc:
        record['reason'] = 'optional_readback_exception'
        record['errors'].append(repr(exc))
    finally:
        try:
            receipt.write_text(json.dumps(record, indent=2) + '\n')
        except Exception as exc:
            record['errors'].append('receipt_write_exception:' + repr(exc))
    return record
