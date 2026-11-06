"""Read-only review of the first FX6 AP run; never starts a guest."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
DONOR = Path(__file__).resolve().parent.parent
RUN = DONOR / 'hybrid-ap-candidate/runs/fx6ap-bb7588e5'
BASE = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def main():
    baseline = json.loads(BASE.read_text())
    command = json.loads((RUN / 'command.json').read_text())
    receipt = json.loads((RUN / 'receipt.json').read_text())
    fault = json.loads((RUN / 'fault-context.json').read_text())
    assert sha(BASE) == '854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'
    original, actual = baseline['fx3_vm_command'], command['args']
    assert len(original) == len(actual) == 34
    changed = [i for i, (a, b) in enumerate(zip(original, actual)) if a != b]
    assert changed == [20, 31], changed
    assert actual[20] == 'file:' + str(RUN / 'serial.log')
    candidate = DONOR / 'hybrid-ap-candidate/guest-three-entry.cpio'
    assert actual[31] == 'loader,file=' + str(candidate) + ',addr=0x440000000,force-raw=on'
    assert command['model_env'] == baseline['model_env']
    hashes = {}
    for name, item in baseline['sha256'].items():
        hashes[name] = sha(item['path'])
        assert hashes[name] == item['sha256'], name
        assert Path(item['path']).stat().st_size == item['bytes'], name
    hashes['candidate'] = sha(candidate)
    assert hashes['candidate'] == 'bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02'
    serial = (RUN / 'serial.log').read_bytes()
    hashes['serial'] = hashlib.sha256(serial).hexdigest()
    assert hashes['serial'] == receipt['serial']['sha256'] == fault['serial_sha256']
    for name, item in fault['ranges'].items():
        start, end = item['byte_range']
        assert serial[start:end].decode().rstrip('\n') == item['raw_line'], name
    assert receipt['serial_health_failure']['text'] == 'assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075'
    assert receipt['stop_cause'] == 'first_health_fault'
    assert receipt['key_steps'] == receipt['synthetic_events'] == 0
    assert receipt['qemu_exit'] == 0 and receipt['process_reaped']
    assert receipt['host_error'] is None
    restore = receipt['cleanup']['restore']
    assert restore['passed'] and receipt['cleanup']['API16_restored']
    last = restore['attempts'][-1]
    assert last['restore_seen'] == 1
    assert sha(last['header']) == last['header_SHA256']
    expected = '000b00b4fd7bbba9fd030091f35301a9'
    assert Path(last['api16']).read_bytes().hex() == expected
    assert (RUN / 'pcidma-original16-restored.bin').read_bytes().hex() == expected
    print(json.dumps({
        'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'PASS_FIXED_PLATFORM_FIRST_ASSERT_EVIDENCE',
        'run': str(RUN), 'argv_changed_indices': changed,
        'hashes': hashes, 'raw_ranges_verified': len(fault['ranges']),
        'duration_seconds': receipt['duration_seconds'],
        'observed_assert': receipt['serial_health_failure'],
        'cleanup_receipt_and_saved_original_bytes_verified': True,
        'live_process_or_lock_rechecked': False,
        'FX6_menu_or_complete_AP_ABI_proven': False,
        'request_reply_causality_proven': False,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
