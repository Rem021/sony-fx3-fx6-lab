"""QMP-paused, checked full-ring snapshot; no live-memory consistency claim."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from parse_v25_diag_r3 import parse

ADDRESS = 0x41e000000
SIZE = 0x1000000


def capture(qmp, run: Path) -> dict:
    stop = qmp('stop')
    if 'error' in stop or 'return' not in stop:
        raise RuntimeError('QMP stop failed: ' + repr(stop))
    status = qmp('query-status')
    state = status.get('return') if isinstance(status, dict) else None
    if not isinstance(state, dict) or state.get('running') is not False or state.get('status') != 'paused':
        raise RuntimeError('QMP not provably paused: ' + repr(status))
    # The core ring read is deliberately before every optional diagnostic.
    # A failed QMP register request must never suppress this readback.
    path = run / 'osd-ring-final.bin'
    if path.exists():
        raise FileExistsError(path)
    result = qmp('human-monitor-command', {
        'command-line': f'pmemsave {ADDRESS:#x} {SIZE:#x} "{path}"'})
    if 'error' in result or 'return' not in result:
        raise RuntimeError('QMP pmemsave failed: ' + repr(result))
    if not path.is_file():
        raise RuntimeError('full OSD ring readback missing')
    raw = path.read_bytes()
    receipt = {'consistent': False, 'paused_proven': True, 'readback_complete': len(raw) == SIZE,
               'parse_valid': False,
               'method': 'QMP stop acknowledged; query-status running=false,status=paused; full pmemsave while paused',
               'query_status': state, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
               'path': str(path), 'parse_path': None}
    if len(raw) != SIZE:
        receipt['readback_error'] = 'wrong_length_after_read'
    else:
        try:
            parsed = parse(raw, quiesced=True)
        except Exception as exc:
            receipt['parse_error'] = repr(exc)
        else:
            receipt.update(parse_valid=True,
                           dropped_busy_writer_events=parsed['dropped_busy_writer_events'],
                           invalid_or_torn_slots=parsed['invalid_or_torn_slots'])
            try:
                diag_path = run / 'osd-ring-final-diag.json'
                diag_path.write_text(json.dumps(parsed, indent=2) + '\n')
                receipt['parse_path'] = str(diag_path)
                receipt['consistent'] = True
            except Exception as exc:
                receipt['parsed_artifact_write_error'] = repr(exc)
    try:
        (run / 'osd-ring-final-readback-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    except Exception as exc:
        receipt['receipt_write_error'] = repr(exc)
        receipt['consistent'] = False
    return receipt


def capture_optional_vcpus(qmp, run: Path, *, budget: float = 6.0,
                           clock=time.monotonic) -> dict:
    """Best-effort, absolute-budget read on an already-paused VM.

    This never raises and does not label an HMP error string as registers.
    It is invoked after the core ring and immutable frame are saved, before
    the guest restoration request or any other cleanup control write.
    """
    record = {'complete': False, 'guest_tid_mapping': 'unknown',
              'read_only': True, 'paused_state_required': True,
              'query_cpus_fast': None, 'hmp_info_registers_all': None,
              'errors': []}
    if not 0 < budget <= 10:
        raise ValueError('optional vCPU budget must be 0..10 seconds')
    deadline = clock() + budget
    def ask(name, arguments=None):
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError('optional vCPU total deadline expired')
        return qmp(name, arguments, timeout=remaining)
    try:
        status = ask('query-status')
        state = status.get('return') if isinstance(status, dict) else None
        record['query_status'] = status
        if not isinstance(state, dict) or state.get('running') is not False or state.get('status') != 'paused':
            record['errors'].append('not_provably_paused')
            return record
        try:
            cpus = ask('query-cpus-fast')
            record['query_cpus_fast'] = cpus
        except Exception as exc:
            record['errors'].append('query_cpus_exception:' + repr(exc))
            return record
        rows = cpus.get('return') if isinstance(cpus, dict) and 'error' not in cpus else None
        if not isinstance(rows, list) or len(rows) != 4 or {r.get('cpu-index') for r in rows if isinstance(r, dict)} != {0, 1, 2, 3}:
            record['errors'].append('invalid_or_incomplete_cpu_rows')
            return record
        try:
            registers = ask('human-monitor-command', {'command-line': 'info registers -a'})
            record['hmp_info_registers_all'] = registers
        except Exception as exc:
            record['errors'].append('hmp_register_exception:' + repr(exc))
            return record
        body = registers.get('return') if isinstance(registers, dict) and 'error' not in registers else None
        if not isinstance(body, str) or len(body.encode()) > 1048576:
            record['errors'].append('invalid_or_oversize_hmp_response')
            return record
        pcs = re.findall(r'(?im)\bPC\s*=\s*(?:0x)?[0-9a-f]{6,16}\b', body)
        if len(pcs) < 4 or re.search(r'(?im)^\s*(?:error|unknown command|invalid command|unrecognized command)\b', body):
            record['errors'].append('hmp_text_not_four_register_sets')
            return record
        record['complete'] = True
        record['vcpus'] = 4
    except Exception as exc:
        record['errors'].append('optional_capture_exception:' + repr(exc))
    finally:
        try:
            path = run / 'fault-vcpu-paused.json'
            if path.exists():
                record['errors'].append('existing_receipt_not_overwritten')
                record['complete'] = False
            else:
                path.write_text(json.dumps(record, indent=2) + '\n')
        except Exception as exc:
            record['errors'].append('receipt_write_exception:' + repr(exc))
            record['complete'] = False
    return record
