#!/usr/bin/env python3
"""Recheck exact v21 browser fixture receipts and their captured PNGs."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
module_sha = hashlib.sha256((HERE / 'trial_web_v21_final_timing.py').read_bytes()).hexdigest()
rows = []
for name, expected_keys, screenshot in (
    ('normal', 1, 'after-key.png'),
    ('frame-delay', 0, 'recovered.png'),
    ('key-ack-drop', 1, 'unknown-ack.png'),
):
    folder = HERE / ('browser-v21-' + name)
    data = json.loads((folder / 'server-receipt.json').read_text())
    assert data['module_sha256'] == module_sha
    assert data['no_qemu_or_guest_input'] is True
    assert data['server_threads_reaped'] is True
    assert data['phase'] == 'finished'
    assert data['final_delivery']['acknowledged'] is True
    requests = data['requests']
    keys = [r for r in requests if r['path'] == '/api/key']
    frames = [r for r in requests if r['path'] == '/frame.png']
    acks = [r for r in requests if r['path'] == '/api/final-ack']
    assert len(keys) == expected_keys and len(acks) == 1
    assert (folder / screenshot).is_file()
    row = {'scenario': name, 'module_sha256': module_sha,
           'browser_png_sha256': hashlib.sha256((folder / screenshot).read_bytes()).hexdigest(),
           'key_requests': len(keys), 'frame_requests': len(frames),
           'final_ack_requests': len(acks), 'server_threads_reaped': True,
           'browser_final_acknowledged': True}
    if name == 'frame-delay':
        assert frames[0]['fault'] == 'frame-body-delay-9-seconds' and len(frames) == 2
        delta = frames[1]['monotonic'] - frames[0]['monotonic']
        assert 8 <= delta < 9
        row['frame_retry_after_seconds'] = delta
    if name == 'key-ack-drop':
        assert keys[0]['fault'] == 'drop-accepted-key-ack' and keys[0]['backend_status'] == 202
        assert data['steps'] == 1
    rows.append(row)
receipt = {'scope': 'actual Orca browser against historical PNG proxy; no QEMU, no guest input',
           'status': 'pass', 'rows': rows}
(HERE / 'v21-browser-verified.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(receipt, ensure_ascii=False, indent=2))
