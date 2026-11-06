"""Persist bounded host key-refusal evidence after native cleanup, never in HTTP lock."""
import hashlib
import json
import time
from pathlib import Path


def deliver(trial, run):
    run = Path(run)
    stamp = time.monotonic_ns()
    snapshot = None
    data = None
    try:
        snapshot = trial.key_rejection_snapshot()
        snapshot['export_host_monotonic_ns'] = stamp
        snapshot['capture_boundary'] = 'after_qemu_cleanup_before_browser_final_ack'
        data = (json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n').encode()
        path = run / 'web-key-rejections.json'
        temp = run / 'web-key-rejections.json.tmp'
        if path.exists() or temp.exists():
            raise FileExistsError('rejection evidence already exists; never overwrite')
        temp.write_bytes(data)
        temp.replace(path)
        return {'complete': True, 'path': str(path), 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest(),
                'total': snapshot['total'], 'stored': len(snapshot['records']),
                'truncated': snapshot['truncated'], 'capture_boundary': snapshot['capture_boundary']}
    except Exception as exc:
        return {'complete': False, 'error_type': type(exc).__name__, 'error': str(exc),
                'memory_bytes': len(data) if data is not None else None,
                'memory_sha256': hashlib.sha256(data).hexdigest() if data is not None else None,
                'memory_total': snapshot.get('total') if snapshot is not None else None,
                'capture_boundary': 'after_qemu_cleanup_before_browser_final_ack'}
