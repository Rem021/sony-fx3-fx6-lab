"""Bounded offline cost measurement on an immutable completed run; no VM."""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TRY = HERE.parent
ROOT = next(p for p in HERE.parents if p.name == 'Mac')
SOURCE = ROOT / 'work/fx3-vm-20261101/menu-repair-01/runtime'
sys.path.insert(0, str(SOURCE))
import osd_ring93_v4 as ring

run = TRY / 'runs/try2passivetiming-internal-v21-2383af57'
paths = [run / 'osd-ring-readback.json', run / 'trial-final.raw',
         run / 'trial-final.json', SOURCE / 'osd_ring93_v4.py',
         TRY / 'trial_ring_usability.py']
pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
data = json.loads(paths[0].read_bytes())
frames = data['frames']
raw = paths[1].read_bytes()
meta = json.loads(paths[2].read_bytes())
args = (meta['width'], meta['height'], meta['stride_pixels'], meta['native_format'])
assert ring.sha(raw) == meta['sha256']
pixels = ring.rgba(raw, *args)
assert ring.sha(ring.png(*args[:2], pixels)) == meta['PNG_sha256']
result = {
    'scope': 'offline Python CPU only; excludes QMP, disk writes, guest and browser latency',
    'input_sha256': pins,
    'frame_records': len(frames), 'poll_records': len(data['polls']),
    'readback_bytes': paths[0].stat().st_size,
    'adjacent_identical_raw_sha256': sum(a['sha256'] == b['sha256'] for a, b in zip(frames, frames[1:])),
    'unique_raw_sha256': len({f['sha256'] for f in frames}),
    'timing_ms': {},
    'interpretation': 'Potential repeated conversion cost only. SHA statistics are not permission to bypass byte equality or FNV validation. No menu speedup proven.',
}
for label, operation in [
    ('fnv', lambda: ring.fnv(raw)),
    ('rgba', lambda: ring.rgba(raw, *args)),
    ('png', lambda: ring.png(*args[:2], pixels)),
    ('full_json_serialization', lambda: json.dumps(data, indent=2)),
]:
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - start) * 1000)
    result['timing_ms'][label] = {'samples': samples, 'median': statistics.median(samples)}
assert pins == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'input_sha256'}, indent=2))
