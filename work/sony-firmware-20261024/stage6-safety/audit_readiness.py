#!/usr/bin/env python3
"""Audit this research's local evidence. No camera/network/device operations.

This is an inventory, not a flash authorization or a recovery capability test.
Only fixed task-relative inputs are read. One new JSON receipt is written using
exclusive creation; no firmware, backup or existing receipt is overwritten.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

STOCK = {
    'appFw.so': ('nflasha15/lib/appFw.so', 79015712,
        '545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'),
    'libmpr.so': ('nflasha15/lib/libmpr.so', 3517008,
        '9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'),
    'cpapp-b.bin': ('nflasha8/cpapp-b.bin', 15980568,
        'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'),
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path,
                        default=Path(__file__).resolve().parents[3])
    parser.add_argument('--out', required=True, type=Path,
                        help='new receipt path; parent must already exist')
    args = parser.parse_args()
    root = args.project_root.resolve(strict=True)
    out = args.out.resolve()
    if not out.parent.is_dir():
        parser.error('output parent must already exist; no directories created')
    if out.exists():
        parser.error('refusing to overwrite an existing file')
    task = Path('work/sony-firmware-20261024')
    stock = []
    for name, (relative, size, expected) in STOCK.items():
        relative_path = task / 'stage2/extraction/files' / relative
        path = root / relative_path
        item = {'name': name, 'path': str(relative_path),
                'source_kind': 'official_stock_reference_not_body_backup',
                'expected_bytes': size, 'expected_sha256': expected,
                'verified': False}
        if path.is_file() and not path.is_symlink():
            item.update(bytes=path.stat().st_size, sha256=digest(path))
            item['verified'] = item['bytes'] == size and item['sha256'] == expected
        stock.append(item)
    host_path = task / 'stage4-windows-collab/from-windows/host-inventory.json'
    host = {'receipt_present': False, 'live_usb_query_performed_by_this_audit': False}
    if (root / host_path).is_file():
        raw = (root / host_path).read_bytes()
        original = json.loads(raw.decode('utf-8-sig'))
        host.update(receipt_present=True, source=str(host_path),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    captured_utc=original.get('captured_utc'),
                    cached_devices=[{
                        'name': row.get('name'), 'vid': row.get('vid'),
                        'pid': row.get('pid'), 'status': row.get('status'),
                        'driver_provider': row.get('driver_provider'),
                        'driver_version': row.get('driver_version'),
                        'service': row.get('service')}
                        for row in original.get('sony_present_cached_pnp', [])],
                    access_evidence=original.get('access_evidence'))
    msc_path = task / 'stage6-safety/windows-msc-inventory/sony-pnp-inventory.json'
    msc = {'receipt_present': False, 'live_usb_query_performed_by_this_audit': False}
    msc_ok = False
    if (root / msc_path).is_file():
        raw_msc = (root / msc_path).read_bytes()
        msc_original = json.loads(raw_msc.decode('utf-8-sig'))
        nodes = msc_original.get('sony_camera_candidate_nodes', [])
        msc_ok = any(
            row.get('bus_reported_description') == 'ILME-FX3'
            and row.get('vid') == '054C'
            and row.get('present') is True
            and row.get('driver_service') == 'USBSTOR'
            and row.get('status') == 'OK'
            and row.get('config_manager_error_code') == 0
            for row in nodes)
        msc.update(receipt_present=True, source=str(msc_path),
                   sha256=hashlib.sha256(raw_msc).hexdigest(),
                   captured_utc=msc_original.get('captured_utc'),
                   cached_camera_nodes=nodes,
                   access_evidence=msc_original.get('access_evidence'))
    baseline_ok = all(item['verified'] for item in stock)
    gates = [
        {'id': 'official_reference_integrity',
         'status': 'VERIFIED' if baseline_ok else 'FAILED',
         'scope': 'Three extracted official program files only'},
        {'id': 'normal_msc_pnp_binding',
         'status': 'VERIFIED_SNAPSHOT' if msc_ok else 'NOT_PROVEN',
         'scope': 'Cached Windows bus model, USB identity and driver binding only; not device-handle or recovery access'},
        {'id': 'exact_physical_body_and_firmware', 'status': 'NOT_PROVEN',
         'needs': 'Actual FX3 identity/version/program fingerprint; latest user report is insufficient'},
        {'id': 'healthy_same_body_checkpoint', 'status': 'NOT_PROVEN',
         'needs': 'Before-change modified-scope originals/settings plus provenance and verified hashes'},
        {'id': 'normal_fx3_service_access', 'status': 'NOT_PROVEN',
         'needs': 'FX3-specific authenticated read and clean exit; no such test recorded'},
        {'id': 'recovery_entry_independent_of_modified_application', 'status': 'NOT_PROVEN',
         'needs': 'Reachability and repair under the intended application-failure condition'},
        {'id': 'fx3_restore_round_trip', 'status': 'NOT_PROVEN',
         'needs': 'Same-body complete readback, disk/RAM/cold-start/behavior verification after a real restore'},
        {'id': 'fx3_write_and_power_loss_behavior', 'status': 'NOT_PROVEN',
         'needs': 'Model-specific bounded writer and failure tests; pwrite/fsync alone is not atomic'},
        {'id': 'new_mode_actual_encoding_and_stability', 'status': 'NOT_PROVEN',
         'needs': 'Hardware acceptance, valid bitstream/audio/timestamps/long-run and cold-start results'},
    ]
    receipt = {
        'schema': 'fx3-research-safety-inventory-v1',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Only this task evidence; no search for user backups elsewhere',
        'state': 'OFFLINE_RESEARCH_ONLY' if baseline_ok else 'STOP_INVALID_REFERENCE',
        'persistent_write_release': False,
        'is_flash_authorization_or_recovery_certificate': False,
        'stock_files': stock, 'windows_snapshot': host,
        'camera_msc_snapshot': msc, 'gates': gates,
        'limits': [
            'Stock programs are not unique body calibration/NVRAM/full storage backups',
            'A cached Sony VID/PID is not authenticated service access',
            'Normal service access is not recovery after main application failure',
            'No-op restore and dry run do not prove actual restoration',
            'A CPU model or in-memory fault test does not prove power-loss recovery',
            'Hardware failure or inaccessible early boot may require qualified repair',
        ],
        'operations': {'camera_interfaces_opened': False, 'camera_commands': False,
                       'firmware_or_backup_written': False, 'network_requests': False},
    }
    with out.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(f"{receipt['state']}: reference files {sum(x['verified'] for x in stock)}/3 verified")
    print('Persistent writing remains unreleased; no camera operation performed.')
    print(str(out))
    return 0 if baseline_ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
