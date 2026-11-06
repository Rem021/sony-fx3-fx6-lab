"""Offline differential replay against Path.read_text(errors='replace')."""
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path

from serial_snapshot import SerialSnapshot

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[3] / 'menu-repair-01/runtime/runs'
sys.path.insert(0, str(RUNS.parent))
from trial_log_v2 import FullLogMonitor
LOGS = [
    ('ap104light4save1200-2e5d177c', '546cb84e55fe55b57c820a71334d53d43548ab8001b440e99c33c737ceef9845'),
    ('try1-740a3263', '7ea21fead6e939bcbe4581a26502a14b849c4aca97fbe4bc7ff9779b28677863'),
]
PROBES = [r'unfetched', r'FX3_LIGHT104_ALLOC_RETURN[^\n]*result=-1018(?: |$)',
          r'FX3_AP89_SCREEN_OPEN_ENTER [^\n]*id2=(0x[0-9a-f]+)',
          r'FX3_SYNTH_KEY step=(\d+) key=(0x[0-9a-f]+) status=0 [^\n]*result=0 ',
          r'FX3_GUEST_UPTIME_SNAPSHOT\s*\n([0-9]+\.[0-9]+) ([0-9]+\.[0-9]+)']


def old(path):
    return path.read_text(errors='replace') if path.exists() else ''


def check(path, reader):
    expected = old(path)
    actual = reader.poll()
    assert actual == expected, (len(actual), len(expected), reader.offset)
    for expression in PROBES:
        assert re.findall(expression, actual) == re.findall(expression, expected)
    assert reader.poll() == expected


def synthetic(tmp):
    path = tmp / 'synthetic.log'
    reader = SerialSnapshot(path)
    check(path, reader)  # absent startup
    data = b'A\r\nB\rC\n' + '菜单'.encode() + b'\r\n' + bytes(range(256)) + b'last-line'
    rng = random.Random(105)
    cursor = 0
    while cursor < len(data):
        n = rng.randrange(1, 18)
        with path.open('ab') as stream:
            stream.write(data[cursor:cursor + n])
        cursor += n
        check(path, reader)
    path.write_bytes(b'new\r')  # truncate, dangling CR
    check(path, reader)
    with path.open('ab') as stream:
        stream.write(b'\nUTF8=' + '中'.encode()[:1])
    check(path, reader)
    with path.open('ab') as stream:
        stream.write('中'.encode()[1:])
    check(path, reader)
    path.write_bytes(b'X' * path.stat().st_size)  # same-size in-place rewrite
    os.utime(path, ns=(time.time_ns(), time.time_ns()))
    check(path, reader)
    path.write_bytes(b'Y' * (path.stat().st_size + 70))  # rewrite plus growth
    check(path, reader)
    other = tmp / 'replacement.log'
    other.write_bytes(b'other\n\xff')
    os.replace(other, path)  # inode replacement
    check(path, reader)
    path.unlink()
    check(path, reader)
    return {'partition_seed': 105, 'bytes': len(data), 'resets': reader.resets}


def known_counterexample(tmp):
    path = tmp/'same_anchor_rewrite.log'
    path.write_bytes(b'A'*200)
    reader = SerialSnapshot(path)
    assert reader.poll() == old(path)
    path.write_bytes(b'B'*100 + b'A'*100 + b'C'*70)
    actual = reader.poll()
    expected = old(path)
    assert actual != expected
    return {'case': 'same inode, grow after rewriting early bytes while preserving old trailing 64 bytes',
            'old_length': len(expected), 'candidate_length': len(actual),
            'equal': False, 'mitigation': 'new run path or full reread on rewrite-capable source'}


def real(tmp):
    rows = []
    for label, expected_sha in LOGS:
        source = RUNS / label / 'serial.log'
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected_sha
        path = tmp / 'serial.log'
        path.write_bytes(b'')
        reader = SerialSnapshot(path)
        size = 0
        checks = 0
        for n in [1, 2, 3, 17, 4093, 65537, 1013903]:
            with path.open('ab') as stream:
                stream.write(data[size:size+n])
            size += min(n, len(data)-size)
            check(path, reader)
            checks += 1
        step = max(1, (len(data)-size)//12)
        while size < len(data):
            end = min(len(data), size+step)
            with path.open('ab') as stream:
                stream.write(data[size:end])
            size = end
            check(path, reader)
            checks += 1
        assert reader.offset == len(data)
        assert reader.bytes_read == len(data)
        monitor = FullLogMonitor(path)
        selected_text = monitor.poll()
        rows.append({'label': label, 'sha256': expected_sha, 'bytes': len(data), 'partitions': checks,
                     'contains_unfetched': 'unfetched' in reader.poll(), 'reader_bytes': reader.bytes_read,
                     'trial_selected_lines': len(monitor.selected),
                     'trial_selected_text_chars': len(selected_text),
                     'trial_selected_heap_bytes': sys.getsizeof(monitor.selected) + sum(sys.getsizeof(line) for line in monitor.selected)})
        path.unlink()
    return rows


def benchmark(tmp, source):
    data = source.read_bytes()
    path = tmp / 'benchmark.log'
    path.write_bytes(data)
    reader = SerialSnapshot(path)
    assert reader.poll() == old(path)
    repeats = 30
    start = time.process_time_ns()
    for _ in range(repeats):
        old(path)
    old_ms = (time.process_time_ns()-start)/1e6
    start = time.process_time_ns()
    for _ in range(repeats):
        reader.poll()
    new_ms = (time.process_time_ns()-start)/1e6
    assert reader.bytes_read == len(data)
    return {'bytes': len(data), 'repeat_polls': repeats, 'old_cpu_ms': round(old_ms, 3),
            'new_cpu_ms': round(new_ms, 3), 'old_disk_bytes': len(data)*repeats,
            'new_disk_bytes_after_first_poll': 0, 'new_anchor_probe_bytes': 64*repeats,
            'retained_text_chars': len(reader.poll())}


def benchmark_growth(tmp, source):
    data = source.read_bytes()
    rows = []
    for size in (1024*1024, 4*1024*1024, 8*1024*1024, 16*1024*1024, len(data)):
        path = tmp/'growth.log'
        path.write_bytes(data[:size])
        reader = SerialSnapshot(path)
        assert reader.poll() == old(path)
        repeats = 5
        start = time.process_time_ns()
        for _ in range(repeats):
            baseline = old(path)
        old_ms = (time.process_time_ns()-start)/1e6
        start = time.process_time_ns()
        for _ in range(repeats):
            observed = reader.poll()
        new_ms = (time.process_time_ns()-start)/1e6
        assert observed == baseline
        rows.append({'file_bytes': size, 'old_repeat_cpu_ms': round(old_ms,3),
                     'new_repeat_cpu_ms': round(new_ms,3),
                     'old_snapshot_heap_bytes': sys.getsizeof(baseline),
                     'new_retained_text_heap_bytes': sys.getsizeof(reader.text),
                     'new_snapshot_heap_bytes': sys.getsizeof(reader._snapshot),
                     'new_text_snapshot_same_object': reader.text is reader._snapshot})
    return rows


def main():
    with tempfile.TemporaryDirectory(dir=HERE) as folder:
        tmp = Path(folder)
        result = {'synthetic': synthetic(tmp), 'known_counterexample': known_counterexample(tmp),
                  'real_logs': real(tmp),
                  'benchmark': benchmark(tmp, RUNS/LOGS[0][0]/'serial.log'),
                  'growth': benchmark_growth(tmp, RUNS/LOGS[0][0]/'serial.log'),
                  'scope': 'host read_text snapshot equality only; regex still scans complete history; no guest/UI/save/exit validation'}
    (HERE/'measurement.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
