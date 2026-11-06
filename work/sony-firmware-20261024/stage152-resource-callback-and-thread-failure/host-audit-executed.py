#!/usr/bin/env python3
"""Read pinned source text only; do not import third-party USB code."""
from pathlib import Path
from hashlib import sha256
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parents[1]


def main():
    receipt = json.loads((HERE / 'host-capture-source-receipt.json').read_text())
    official, public_probe = receipt['items']
    upstream = HERE / official['path']
    probe = ROOT / public_probe['path']
    for path, item in [(upstream, official), (probe, public_probe)]:
        assert path.stat().st_size == item['bytes'] and sha256(path.read_bytes()).hexdigest() == item['sha256']
    lines = upstream.read_text().splitlines()
    facts = []
    observations = [
        (2900, 2945, ['capture an entire device', 'UNUSED(interface)', 'darwin_reenumerate_device (dev_handle, true)'], 'Darwin capture is whole-device even when API takes interface 0'),
        (2140, 2244, ['kUSBReEnumerateCaptureDeviceMask', 'capture mode does not re-enumerate but it does require re-open', 'if (capture)', 'darwin_restore_state'], 'Distinguish capture/reopen branch from noncapture re-enumeration wait'),
        (2948, 2965, ['UNUSED(interface)', 'capture_count--', 'darwin_reenumerate_device (dev_handle, false)'], 'Final attach count transition takes noncapture re-enumeration route'),
        (2078, 2138, ['darwin_close (dev_handle)', 'darwin_open (dev_handle)', 'if (dpriv->active_config != active_config)', 'darwin_set_configuration', 'darwin_claim_interface'], 'Restore helper can reopen, conditionally set configuration and reclaim old interfaces'),
        (2979, 2997, ['darwin_attach_kernel_driver', 'ignore the error as the interface was successfully released', 'return LIBUSB_SUCCESS'], 'Auto-release success does not prove driver attach succeeded')]
    for first, last, expected, claim in observations:
        excerpt = '\n'.join(lines[first - 1:last])
        assert all(x in excerpt for x in expected), (first, last)
        facts.append({'source': official['url'], 'path': official['path'], 'first_line': first, 'last_line': last,
            'sha256_of_line_excerpt': sha256(excerpt.encode()).hexdigest(), 'claim': claim, 'checked_markers': expected})
    text = probe.read_text()
    assert 'self.dev.detach_kernel_driver(0)' in text and 'self.dev.attach_kernel_driver(0)' in text
    assert 'safely unmount EVERY volume' in text and '45-second total is a cooperative deadline' in text
    report = {'facts': facts,
        'public_A7CII_probe_explicit_detach_attach_interface0_and_all_volume_unmount_precondition': True,
        'public_probe_header_target': 'ILCE-7CM2 firmware 1.02; not FX3 7.02 identity evidence',
        'public_probe_actual_USB_backend_runtime_version_verified': False,
        'scope': 'Static release-tag libusb1.0.30 and pinned A7CII probe; not execution of stage142 private descriptor library',
        'new_device_Windows_USB_driver_or_privilege_operations': 0,
        'downloaded_source_compiled_imported_or_executed': False,
        'first_trial_design_requirements': [
            'Explicit whole-device capture/return scope; current permission is insufficient and remains unchanged',
            'All camera storage volumes identified and safely unmounted before capture; no media-content reads',
            'No auto-detach; exact native build and hidden restore/configuration calls audited before release',
            'Fresh ownership/identity after capture/reopen and after mode changes; stale handles cannot inherit proof',
            'Record explicit release/attach errors and fresh driver association; release success alone is insufficient',
            'Unknown in-flight I/O or missing cleanup observation remains UNKNOWN; no blind reset, capture retry or extra STOP']}
    with (HERE / 'host-capture-audit.json').open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    (HERE / 'host-audit-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'source_facts_checked': len(facts), 'whole_device_capture_scope_confirmed_in_release_source': True, 'new_device_operations': 0}))


if __name__ == '__main__':
    main()
