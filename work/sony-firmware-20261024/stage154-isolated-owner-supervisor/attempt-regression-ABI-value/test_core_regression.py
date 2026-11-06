#!/usr/bin/env python3
"""Build the actual C flow against an own provider fixture; never load IOKit DSO."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / 'run-core-regression'
    out.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('reviewed_owner_binding', HERE / 'owner_binding.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    argv = ['xcrun', 'clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fvisibility=hidden', '-dynamiclib',
        str(HERE / 'owner_core.c'), str(HERE / 'owner_fixture.c'), '-o', str(out / 'owner-fixture.dylib')]
    subprocess.run(argv, check=True, capture_output=True, text=True)
    library = C.CDLL(str(out / 'owner-fixture.dylib'))
    assert library.fx3_owner_fixture_marker() == 0x46495834
    run = b.from_fixture(library)
    library.fx3_owner_fixture_reset.argtypes = [C.c_uint32] * 3
    library.fx3_owner_fixture_reset.restype = None
    library.fx3_owner_fixture_calls.argtypes = [C.c_uint32]
    library.fx3_owner_fixture_calls.restype = C.c_uint32
    library.fx3_owner_fixture_size.argtypes = [C.c_uint32]
    library.fx3_owner_fixture_size.restype = C.c_uint32
    for index, cls in enumerate([b.Config, b.Result, b.Snapshot, b.Profile, b.Event]):
        assert C.sizeof(cls) == library.fx3_owner_fixture_size(index)
    cases = []

    def case(name, fail=0, option=0, late=0, change=None, stop=False, control_abi=2):
        library.fx3_owner_fixture_reset(fail, option, late)
        config = b.Config(abi=2, arm=0x4f574e33, location=0x02100000, capture_permitted=1, vid=0x054c, pid=0x0da1,
            work_deadline_ns=21000000000, final_deadline_ns=31000000000)
        config.privacy_key[:] = bytes([0x55]) * 32
        if change:
            for k, v in change.items():
                setattr(config, k, v)
        result = b.Result()
        control = b.Control(abi=control_abi, stop_requested=1 if stop else 0)
        rc = run(C.byref(config), C.byref(result), C.byref(control))
        assert rc == result.status
        calls = {str(p): library.fx3_owner_fixture_calls(p) for p in range(1, 13)}
        assert all(calls[str(p)] <= 1 for p in (2, 4, 5, 7, 9, 10, 11))
        assert result.active_call_pending == 0 and result.persistent_camera_or_vendor_commands == 0
        cases.append({'name': name, 'raw_status': rc, 'calls': calls, 'result': b.public_result(result)})
        return rc, calls, result

    rc, calls, r = case('normal_capture_reopen_claim_release_return')
    assert rc == 0 and r.capture_attempted and r.claim_attempted and r.interface_claimed
    assert r.before.registry_id == 100 and r.after.registry_id == 101
    assert bytes(r.before.body_tag) == bytes(r.after.body_tag)
    for phase in (1, 2, 3, 4, 5, 6, 7):
        rc, calls, r = case('native_work_boundary_failure_' + str(phase), fail=phase)
        assert rc == (2 if phase == 1 else 1)
        if phase >= 4:
            assert calls['10'] == 1
        if phase >= 7:
            assert calls['9'] == 1
    for phase in (9, 10, 11):
        rc, calls, r = case('cleanup_failure_' + str(phase), fail=phase)
        assert rc == 2 and r.cleanup_error and calls['12'] >= 1
    rc, calls, r = case('post_observation_never_available', fail=12)
    assert rc == 2 and calls['12'] == 40
    rc, calls, r = case('mounted_before_prepare', option=1)
    assert rc == 1 and calls['2'] == calls['4'] == calls['7'] == 0
    rc, calls, r = case('missing_cached_serial_tag', option=2)
    assert rc == 2 and calls['2'] == calls['4'] == calls['7'] == 0
    rc, calls, r = case('wrong_endpoint_profile', option=4)
    assert rc == 1 and calls['9'] == calls['10'] == calls['11'] == 1
    rc, calls, r = case('different_body_after_return', option=8)
    assert rc == 2 and calls['12'] == 40
    rc, calls, r = case('volume_mount_race_before_capture', option=16)
    assert rc == 1 and calls['4'] == 0 and calls['11'] == 1
    rc, calls, r = case('registry_incarnation_race_before_capture', option=32)
    assert rc == 1 and calls['4'] == 0
    rc, calls, r = case('MSC_driver_remains_after_capture', option=64)
    assert rc == 1 and calls['7'] == 0 and calls['10'] == 1
    rc, calls, r = case('driver_already_absent_no_capture', option=128, change={'capture_permitted': 0})
    assert rc == 0 and calls['4'] == calls['10'] == 0 and calls['7'] == 1
    rc, calls, r = case('capture_not_permitted_driver_present', change={'capture_permitted': 0})
    assert rc == 1 and calls['2'] == calls['4'] == calls['7'] == 0
    rc, calls, r = case('clock_backwards_after_capture', option=256)
    assert rc == 2 and r.clock_invalid and calls['10'] == calls['11'] == 1
    rc, calls, r = case('late_capture_return_cleanup_still_runs', late=4)
    assert rc == 1 and calls['5'] == calls['7'] == 0 and calls['10'] == calls['11'] == 1
    for key, value in [('abi', 2), ('arm', 0), ('vid', 0x1234), ('pid', 0x0336), ('location', 0),
            ('capture_permitted', 2), ('reserved', 1), ('work_deadline_ns', 32000000000)]:
        rc, calls, r = case('invalid_config_' + key, change={key: value})
        assert rc == 3 and sum(calls.values()) == 0
    rc,calls,r=case('stop_before_any_provider_call',stop=True)
    assert rc==2 and sum(calls.values())==0
    rc,calls,r=case('invalid_control_ABI',control_abi=1)
    assert rc==3 and sum(calls.values())==0
    class Poison:
        def __getattribute__(self, name):
            raise AssertionError('native symbol lookup must not occur: ' + name)
    current = json.loads((HERE.parent / 'GOAL_STATUS.json').read_text())
    for label, goal in [('current', current), ('future_flags_without_supervisor', json.loads(json.dumps(current)))]:
        if label.startswith('future'):
            goal['authorization'].update(Mac_owner_trial_authorized=True, driver_change=True,
                Mac_owner_trial_target={'locationID': 0x02100000, 'VID': 0x054c, 'PID': 0x0da1, 'model': 'ILME-FX3', 'firmware': '7.02'})
            goal['prepared_first_device_trial']['Mac_owner_trial_released'] = True
        try:
            b.from_live(Poison(), goal)
        except b.Rejected as error:
            cases.append({'name': 'live_gate_' + label, 'rejected_before_native_symbol_lookup': True, 'reason': str(error)})
        else:
            raise AssertionError('live gate accepted an unreleased candidate')
    for name in ['owner_trial.h', 'owner_core.c', 'owner_fixture.c', 'owner_binding.py', 'test_core_regression.py']:
        (out / name).write_bytes((HERE / name).read_bytes())
    dependencies = subprocess.check_output(['otool', '-L', str(out / 'owner-fixture.dylib')], text=True)
    assert 'IOKit' not in dependencies and 'libusb' not in dependencies
    report = {'status': 'PASS_NATIVE_CORE_FIXTURES_NOT_IOKIT_OR_CAMERA_ACCEPTANCE', 'case_count': len(cases), 'cases': cases,
        'compile_argv': argv, 'fixture_dso_sha256': sha256((out / 'owner-fixture.dylib').read_bytes()).hexdigest(),
        'fixture_dependencies': dependencies, 'actual_IOKit_candidate_loaded': False, 'actual_USB_or_device_operations': 0,
        'real_process_supervision_one_shot_entry_or_driver_return_proven': False}
    with (out / 'results.json').open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': report['status'], 'cases': len(cases), 'actual_device_operations': 0}))


if __name__ == '__main__':
    main()
