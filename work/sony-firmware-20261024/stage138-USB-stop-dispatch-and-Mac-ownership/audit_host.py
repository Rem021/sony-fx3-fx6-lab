#!/usr/bin/env python3
"""Source/host-metadata audit only; never import PyUSB, libusb or a driver."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.metadata
import json
import platform
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def main():
    receipt = json.loads((HERE / 'inputs-receipt.json').read_text())
    for item in receipt['fixed_upstream_sources']:
        p = ROOT / item['path']
        assert p.stat().st_size == item['bytes'] and sha256(p.read_bytes()).hexdigest() == item['sha256']
    backend_path = HERE / 'upstream/pmca-libusb.py'
    backend = ast.parse(backend_path.read_text())
    cls = next(n for n in backend.body if isinstance(n, ast.ClassDef) and n.name == 'UsbBackend')
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    def calls(node):
        return [n.func.attr for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert 'detach_kernel_driver' in calls(methods['reset'])
    assert 'is_kernel_driver_active' in calls(methods['reset'])
    assert 'dispose_resources' in calls(methods['__del__'])
    assert not any('attach_kernel_driver' in calls(n) for n in methods.values())
    assert not any('set_auto_detach_kernel_driver' in calls(n) for n in methods.values())
    assert isinstance(methods['reset'].body[0], ast.Try)
    assert methods['reset'].body[0].handlers[0].type.id == 'NotImplementedError'
    vendor = methods['vendorRequestOut']
    assert 'ctrl_transfer' in calls(vendor)
    timeout = next(n for n in ast.walk(methods['__init__']) if isinstance(n, ast.Assign)
                   and isinstance(n.targets[0], ast.Attribute) and n.targets[0].attr == 'default_timeout')
    assert ast.literal_eval(timeout.value) == 5000
    base_path = HERE / 'upstream/pmca-usb-base.py'
    base = ast.parse(base_path.read_text())
    usb = next(n for n in base.body if isinstance(n, ast.ClassDef) and n.name == 'UsbDevice')
    ctor = next(n for n in usb.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    assert 'reset' in calls(ctor)
    msc = next(n for n in base.body if isinstance(n, ast.ClassDef) and n.name == 'MscDevice')
    msc_reset = next(n for n in msc.body if isinstance(n, ast.FunctionDef) and n.name == 'reset')
    assert 'reset' in calls(msc_reset) and 'sendCommand' in calls(msc_reset)
    all_commands = BASE / 'stage134-backup-reader-scope-and-service-extension/upstream/usb-commands.py'
    command_ast = ast.parse(all_commands.read_text())
    listing = next(n for n in command_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'listDevices')
    assert 'getDeviceInfo' in calls(listing)

    darwin_path = HERE / 'upstream/darwin_usb-v1.0.30.c'
    raw = darwin_path.read_text()
    def function(name):
        # Strip comments and strings without changing line/character offsets.
        tokens = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
        clean = tokens.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), raw)
        match = re.search(r'^static\s+(?:int|void)\s+' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', clean, re.M)
        assert match, name
        start = clean.index('{', match.start())
        depth, end = 1, start + 1
        while depth:
            assert end < len(clean)
            if clean[end] == '{':
                depth += 1
            elif clean[end] == '}':
                depth -= 1
            end += 1
        return {'name': name, 'first_line': raw.count('\n', 0, match.start()) + 1,
                'last_line': raw.count('\n', 0, end) + 1, 'text': raw[match.start():end]}
    names = ['darwin_detach_kernel_driver', 'darwin_attach_kernel_driver',
             'darwin_capture_claim_interface', 'darwin_capture_release_interface', 'darwin_close']
    functions = {n: function(n) for n in names}
    detach, attach = (functions[n]['text'] for n in names[:2])
    release, close = functions[names[3]]['text'], functions[names[4]]['text']
    assert 'UNUSED(interface)' in detach and 'darwin_reenumerate_device (dev_handle, true)' in detach
    assert 'IOServiceAuthorize' in detach and 'geteuid()' in detach and 'LIBUSB_ERROR_ACCESS' in detach
    assert 'UNUSED(interface)' in attach and 'darwin_reenumerate_device (dev_handle, false)' in attach
    assert 'auto_detach_kernel_driver' in release and 'darwin_attach_kernel_driver' in release
    assert 'ignore the error as the interface was successfully released' in release
    assert 'libusb_release_interface' in close and 'USBDeviceClose' in close
    assert 'darwin_attach_kernel_driver' not in close
    changes = (HERE / 'upstream/libusb-v1.0.30-ChangeLog.txt').read_text()
    assert '2026-05-17: v1.0.30' in changes
    libraries = []
    for p in (Path('/opt/homebrew/Cellar/libusb'), Path('/usr/local/Cellar/libusb')):
        if p.exists():
            libraries.append({'path': str(p), 'versions': sorted(x.name for x in p.iterdir() if x.is_dir())})
    packages = {}
    for package in ['pyusb', 'libusb1']:
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    result = {
        'status': 'PASS_STATIC_MAC_DRIVER_OWNERSHIP_NOT_DRIVER_RELEASE_OR_CAMERA_QUERY',
        'PMCA_fixed_commit': 'a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0',
        'PMCA_AST_facts': {'backend_reset_lines': [methods['reset'].lineno, methods['reset'].end_lineno],
            'reset_may_explicitly_detach_interface0': True,
            'detach_catches_only_NotImplementedError_here': True,
            'no_paired_attach_or_auto_detach_setup_in_reviewed_backend': True,
            'destructor_disposes_resources_not_explicitly_attaches': True,
            'default_timeout_property_ms': 5000,
            'constructor_dispatches_reset': {'lines': [ctor.lineno, ctor.end_lineno]},
            'MSC_reset_also_issues_SCSI_command': {'lines': [msc_reset.lineno, msc_reset.end_lineno]},
            'CLI_listing_calls_MSC_getDeviceInfo': {'lines': [listing.lineno, listing.end_lineno]},
            'standard_tool_list_is_not_cache_only_and_must_not_be_run_under_cache_authority': True,
            'vendor_call_lines': [vendor.lineno, vendor.end_lineno]},
        'libusb_source_reference': {'tag': 'v1.0.30', 'published_changelog_date': '2026-05-17',
            'path': darwin_path.relative_to(ROOT).as_posix(), 'sha256': sha256(darwin_path.read_bytes()).hexdigest(),
            'functions': list(functions.values()),
            'detach_captures_whole_device_and_may_reenumerate': True,
            'authorization_or_root_condition_is_source_branch_not_current_access_request': True,
            'attach_reenumerates_after_capture_count_reaches0': True,
            'auto_release_can_return_success_despite_attach_failure': True,
            'explicit_Python_detach_not_proven_paired_by_dispose': True,
            'not_loaded_or_claimed_current_installed_backend': True},
        'host_metadata_only': {'macOS': platform.mac_ver()[0], 'machine': platform.machine(),
            'known_Homebrew_libusb_cellars': libraries, 'research_venv_packages': packages,
            'scope': 'Two conventional Cellar paths and this research venv only; not a full host package inventory'},
        'future_active_trial_constraints': [
            'Select the exact permitted FX3 before any constructor/reset or query; do not reuse broad all-Sony listing as cached metadata.',
            'Driver capture, service protocol and post-attach identity/driver restoration require separate concrete evidence and matching authority.',
            'Keep enter/auth/reenumeration/stop/body-complete/host-reattach results separate; host timeout or disposal alone leaves outcome unknown.',
            'Do not change entitlements, invoke root, install drivers/libraries, detach, auto-retry or reset based on this static audit.'],
        'driver_library_import_load_or_device_open': False,
        'new_camera_USB_cache_Windows_UU_or_Fastboot_test': False,
        'live_service_plan_released': False, 'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'Mac-driver-ownership-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'libusb_C_functions_statically_reviewed': len(functions),
                      'camera_or_driver_operations': 0, 'host_metadata': result['host_metadata_only']}))


if __name__ == '__main__':
    main()
