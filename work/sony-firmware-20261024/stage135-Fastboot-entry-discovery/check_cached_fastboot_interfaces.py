#!/usr/bin/env python3
"""Inspect kernel-maintained USB properties, never open a device or send commands."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SANITIZER = BASE / 'stage129-AP-DMM-config-and-device-trial-plan/mac_cached_usb_inventory.py'
SANITIZER_SHA = 'ed7094e03e1fbad280080ac852a15e8aa571a8011d2033a397648ff6f5374647'
SIGNATURE = (0xff, 0x42, 0x03)
FIELDS = ('bInterfaceClass', 'bInterfaceSubClass', 'bInterfaceProtocol')


def main():
    assert sha256(SANITIZER.read_bytes()).hexdigest() == SANITIZER_SHA
    spec = importlib.util.spec_from_file_location('sealed_cache_sanitizer', SANITIZER)
    sanitizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sanitizer)
    sanitizer.volume()
    result = subprocess.run(['/usr/sbin/ioreg', '-a', '-p', 'IOService', '-r', '-c',
                             'IOUSBHostDevice', '-l', '-w', '0'],
                            capture_output=True, check=True, timeout=15)
    assert len(result.stdout) <= sanitizer.MAX_BYTES
    roots = plistlib.loads(result.stdout)
    if isinstance(roots, dict):
        roots = [roots]
    sanitized = sanitizer.sanitize(result.stdout)
    matches = []
    visited = 0

    def walk(nodes, path=(), owner=None, depth=0):
        nonlocal visited
        assert depth <= 64 and isinstance(nodes, list)
        for number, node in enumerate(nodes):
            visited += 1
            assert visited <= 10000 and isinstance(node, dict)
            here = path + (number,)
            current = owner
            if type(node.get('idVendor')) is int and type(node.get('idProduct')) is int:
                if current is None or node.get('IOObjectClass') == 'IOUSBHostDevice':
                    current = (node['idVendor'], node['idProduct'])
            if tuple(node.get(k) for k in FIELDS) == SIGNATURE:
                matches.append({'tree_index_path': list(here),
                                'Sony_vendor_cached': current is not None and current[0] == 0x054c})
            walk(node.get('IORegistryEntryChildren', []), here, current, depth + 1)

    walk(roots)
    target = []
    for candidate in sanitized['sony_registry_candidates']:
        device = candidate['device']
        if device.get('idProduct') == 0x0da1 or device.get('USB Product Name') == 'ILME-FX3':
            target.append(candidate)
    paths = [c['device']['tree_index_path'] for c in target]
    unique_roots = [c for c in target if not any(len(p) < len(c['device']['tree_index_path']) and
                    c['device']['tree_index_path'][:len(p)] == p for p in paths)]
    tool_paths = [Path('/opt/homebrew/bin/fastboot'), Path('/usr/local/bin/fastboot'),
                  Path.home() / 'Library/Android/sdk/platform-tools/fastboot',
                  Path.home() / 'Android/Sdk/platform-tools/fastboot']
    tool_inventory = [{'candidate': str(p), 'exists': p.exists()} for p in tool_paths]
    receipt = {'created_utc': datetime.now(timezone.utc).isoformat(),
        'query': 'IORegistry IOService IOUSBHostDevice cached properties only',
        'standard_fastboot_interface_signature': {'class': 255, 'subclass': 66, 'protocol': 3},
        'signature_source': 'https://android.googlesource.com/platform/system/core/+/refs/heads/main/fastboot/fastboot.cpp',
        'FX3_cached_records': target, 'FX3_unique_cached_roots': len(unique_roots),
        'standard_fastboot_signature_node_count_all_vendors': len(matches),
        'standard_fastboot_signature_node_count_Sony_vendor': sum(m['Sony_vendor_cached'] for m in matches),
        'unrelated_device_names_serials_or_raw_tree_saved': False,
        'known_fastboot_host_paths': tool_inventory,
        'host_binary_execution_or_install': False,
        'actual_fastboot_protocol_probe_or_mode_entry_executed': False,
        'USB_open_claim_reset_auth_reboot_download_boot_flash_erase_OEM_or_media_read': False,
        'scope': 'Current cached interface presence only; no proof of entry impossibility or every possible custom interface',
        'goal_complete': False, 'persistent_write_release': False}
    sanitizer.volume()
    with (HERE / 'current-fastboot-cache-check.json').open('x') as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'FX3_cached_roots': len(unique_roots),
                      'standard_fastboot_signature_nodes': len(matches),
                      'Sony_standard_fastboot_signature_nodes': receipt['standard_fastboot_signature_node_count_Sony_vendor'],
                      'any_known_host_fastboot_exists': any(p['exists'] for p in tool_inventory),
                      'mode_entry_executed': False}))


if __name__ == '__main__':
    main()
