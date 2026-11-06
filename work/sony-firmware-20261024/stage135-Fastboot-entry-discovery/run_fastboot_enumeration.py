#!/usr/bin/env python3
"""Run official host fastboot version/devices only, with per-process network denial."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    binary = HERE / 'host-tools/platform-tools/fastboot'
    selected = json.loads((HERE / 'selected-public-material-receipt.json').read_text())
    pin = next(r for r in selected['records'] if r['path'] == binary.relative_to(HERE).as_posix())
    assert sha256(binary.read_bytes()).hexdigest() == pin['sha256']
    sandbox = Path('/usr/bin/sandbox-exec')
    assert sandbox.is_file(), 'No network-isolated enumeration path; do not run unisolated'
    prefix = [str(sandbox), '-p', '(version 1)(allow default)(deny network*)']
    version = subprocess.run(prefix + [str(binary), '--version'], capture_output=True, timeout=10)
    assert version.returncode == 0
    version_lines = version.stdout.decode(errors='replace').splitlines()
    assert any('37.0.1' in line for line in version_lines)
    started = datetime.now(timezone.utc).isoformat()
    enumeration = subprocess.run(prefix + [str(binary), 'devices', '-l'], capture_output=True, timeout=10)
    # Serial identifiers remain in RAM and are never written to the receipt.
    device_lines = [line for line in enumeration.stdout.decode(errors='replace').splitlines() if line.strip()]
    stderr = enumeration.stderr.decode(errors='replace')
    assert enumeration.returncode == 0, 'Fastboot enumeration failed; no mode commands attempted'
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'started_utc': started,
        'official_host_binary_sha256': pin['sha256'], 'host_tool_version_line': version_lines[0],
        'commands': ['fastboot --version', 'fastboot devices -l'],
        'enumeration_exit_code': enumeration.returncode, 'listed_device_line_count': len(device_lines),
        'enumeration_stderr_bytes': len(enumeration.stderr),
        'enumeration_empty_stdout': not device_lines, 'enumeration_stderr_empty': not stderr,
        'raw_serial_output_saved': False,
        'per_process_network_denied': True, 'HOME_or_system_settings_modified': False,
        'system_install_driver_changes_or_ADB_server': False,
        'mode_entry_getvar_boot_download_flash_erase_OEM_or_unlock_commands_requested': False,
        'Sony_code_or_A7IV_payload_loaded_or_executed': False,
        'scope': 'Actual official host enumeration only; no claim that entry was tried or is impossible',
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'actual-fastboot-enumeration.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    # Check current cached interface state once after the explicit enumeration.
    spec = importlib.util.spec_from_file_location('cache_check', HERE / 'check_cached_fastboot_interfaces.py')
    cache_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_check)
    cache_check.HERE = HERE / 'post-enumeration'
    cache_check.HERE.mkdir()
    cache_check.main()
    print(json.dumps({'host_version': version_lines[0], 'listed_fastboot_devices': len(device_lines),
                      'mode_entry_commands': 0, 'partition_or_payload_commands': 0,
                      'network_denied': True}))


if __name__ == '__main__':
    main()
