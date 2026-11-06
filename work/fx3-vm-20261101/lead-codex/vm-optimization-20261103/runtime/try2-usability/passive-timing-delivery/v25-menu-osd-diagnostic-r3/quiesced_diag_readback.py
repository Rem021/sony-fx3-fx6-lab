"""QMP-paused, checked full-ring snapshot; no live-memory consistency claim."""
from __future__ import annotations

import hashlib
import json
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
    path = run / 'osd-ring-final.bin'
    if path.exists():
        raise FileExistsError(path)
    result = qmp('human-monitor-command', {
        'command-line': f'pmemsave {ADDRESS:#x} {SIZE:#x} "{path}"'})
    if 'error' in result or 'return' not in result:
        raise RuntimeError('QMP pmemsave failed: ' + repr(result))
    if not path.is_file() or path.stat().st_size != SIZE:
        raise RuntimeError('full OSD ring readback missing or wrong size')
    raw = path.read_bytes()
    parsed = parse(raw, quiesced=True)
    digest = hashlib.sha256(raw).hexdigest()
    (run / 'osd-ring-final-diag.json').write_text(json.dumps(parsed, indent=2) + '\n')
    receipt = {'consistent': True, 'method': 'QMP stop acknowledged; query-status running=false,status=paused; full pmemsave while paused',
               'query_status': state, 'bytes': len(raw), 'sha256': digest,
               'path': str(path), 'parse_path': str(run / 'osd-ring-final-diag.json'),
               'dropped_busy_writer_events': parsed['dropped_busy_writer_events'],
               'invalid_or_torn_slots': parsed['invalid_or_torn_slots']}
    (run / 'osd-ring-final-readback-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt
