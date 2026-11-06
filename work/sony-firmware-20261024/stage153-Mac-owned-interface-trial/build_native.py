#!/usr/bin/env python3
"""Compile and inspect the native candidate without loading it."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B' and volume['WritableVolume']
    sdk = Path(subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip())
    dylib = HERE / 'owner-iokit.dylib'
    assert not dylib.exists()
    argv = ['xcrun', 'clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-deprecated-declarations',
        '-fvisibility=hidden', '-dynamiclib', str(HERE / 'owner_core.c'), str(HERE / 'owner_iokit.c'),
        '-framework', 'IOKit', '-framework', 'CoreFoundation', '-framework', 'DiskArbitration', '-o', str(dylib)]
    run = subprocess.run(argv, capture_output=True, text=True, check=True)
    dependencies = subprocess.check_output(['otool', '-L', str(dylib)], text=True)
    symbols = subprocess.check_output(['nm', '-gU', str(dylib)], text=True)
    exports = [line.split()[-1] for line in symbols.splitlines() if line.split()]
    assert exports == ['_fx3_owner_run']
    source_names = ['owner_trial.h', 'owner_core.c', 'owner_iokit.c', 'owner_binding.py']
    sources = [{'path': name, 'bytes': (HERE / name).stat().st_size, 'sha256': sha256((HERE / name).read_bytes()).hexdigest()} for name in source_names]
    own = (HERE / 'owner_iokit.c').read_text()
    forbidden = ['USBDeviceRequest', 'DeviceRequestTO', 'ReadPipe', 'WritePipe', 'SetConfiguration', 'ResetDevice', 'SetSuspend', 'SetAlternateInterface']
    assert all(name not in own for name in forbidden)
    headers = []
    for relative, markers in [
        ('System/Library/Frameworks/IOKit.framework/Versions/A/Headers/usb/IOUSBLib.h',
         ['except when you are passing the kUSBReEnumerateCaptureDeviceBit', 'non-mass storage interfaces', 'run with root privileges']),
        ('System/Library/Frameworks/IOKit.framework/Versions/A/Headers/usb/USB.h',
         ['any drivers attached to a Mass Storage Class IOUSBInterface', 'kUSBReEnumerateCaptureDeviceMask', 'kUSBReEnumerateReleaseDeviceMask'])]:
        path = sdk / relative
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            text = raw.decode('latin-1')
            encoding = 'latin-1'
        assert all(marker in text for marker in markers)
        lines = text.splitlines()
        matches = [{'line': i + 1, 'text': line.strip()} for i, line in enumerate(lines) if any(marker in line for marker in markers)]
        headers.append({'path': str(path), 'sha256': sha256(raw).hexdigest(), 'inspection_encoding': encoding, 'checked_markers': markers, 'matches': matches})
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'compile_argv': argv, 'compiler_stdout': run.stdout,
        'compiler_stderr': run.stderr, 'sdk': str(sdk), 'sources': sources, 'native_dylib_sha256': sha256(dylib.read_bytes()).hexdigest(),
        'native_dylib_bytes': dylib.stat().st_size, 'dependencies': dependencies, 'exported_symbols': exports,
        'forbidden_explicit_API_names_absent': forbidden, 'SDK_header_audit': headers,
        'deprecation_warnings_disabled_for_legacy_IOKit_API': True,
        'actual_native_candidate_loaded_or_run': False, 'new_device_operations': 0,
        'MSC_driver_exclusion_is_documented_not_actual_OS_behavior_verified': True,
        'explicit_Seize_and_capture_release_masks_require_new_driver_scope': True}
    with (HERE / 'native-build-receipt.json').open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    (HERE / 'build-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'native_dylib_sha256': report['native_dylib_sha256'], 'exports': exports, 'compiled_not_loaded': True}))


if __name__ == '__main__':
    main()
