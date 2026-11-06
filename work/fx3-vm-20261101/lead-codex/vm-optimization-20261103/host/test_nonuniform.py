"""Offline equivalence and timing; never contacts QEMU or a running trial."""
import hashlib
import json
import random
import statistics
import time
from pathlib import Path

from nonuniform_candidate import nonuniform_rgba


def original(pixels):
    return any(pixels[i:i + 4] != pixels[:4] for i in range(4, len(pixels), 4))


def measure(fn, payload, rounds=9):
    values = []
    for _ in range(rounds):
        start = time.perf_counter_ns()
        result = fn(payload)
        values.append((time.perf_counter_ns() - start) / 1e6)
        assert result == original(payload)
    return round(statistics.median(values), 4)


def main():
    randomizer = random.Random(0x105)
    checked = 0
    for size in range(33):
        for _ in range(100):
            payload = randomizer.randbytes(size)
            assert nonuniform_rgba(payload) == original(payload)
            checked += 1
    pixel = bytes.fromhex('102030ff')
    uniform = pixel * (640 * 480)
    late = uniform[:-4] + bytes.fromhex('102031ff')
    early = uniform[:4] + bytes.fromhex('102031ff') + uniform[8:]
    cases = {'uniform': uniform, 'late_change': late, 'early_change': early}
    rows = []
    for name, payload in cases.items():
        before = hashlib.sha256(payload).hexdigest()
        old = measure(original, payload)
        new = measure(nonuniform_rgba, payload)
        assert hashlib.sha256(payload).hexdigest() == before
        rows.append({'case': name, 'bytes': len(payload), 'result': original(payload),
                     'old_median_ms': old, 'candidate_median_ms': new,
                     'speedup': round(old / new, 2) if new else None,
                     'input_sha256_unchanged': True})
    result = {'scope': 'host-only synthetic RGBA; no guest/UI/save/exit acceptance',
              'small_random_cases': checked, 'cases': rows,
              'counterexample_checked': 'trailing 1-3 bytes make the old scan true when length exceeds 4',
              'source_bytes_written': False}
    target = Path(__file__).with_name('measurement.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
