"""Typed ABI for an unreleased Mac owner trial; no native library is loaded here."""
from pathlib import Path
import ctypes as C
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


class Rejected(ValueError):
    pass


class Config(C.Structure):
    _fields_ = [('abi', C.c_uint32), ('arm', C.c_uint32), ('location', C.c_uint32), ('capture_permitted', C.c_uint32),
        ('vid', C.c_uint16), ('pid', C.c_uint16), ('reserved', C.c_uint32), ('work_deadline_ns', C.c_uint64),
        ('final_deadline_ns', C.c_uint64), ('privacy_key', C.c_uint8 * 32)]


class Snapshot(C.Structure):
    _fields_ = [('registry_id', C.c_uint64), ('media_count', C.c_uint32), ('mounted_count', C.c_uint32),
        ('media_unknown', C.c_uint32), ('storage_driver_count', C.c_uint32), ('vid', C.c_uint16), ('pid', C.c_uint16),
        ('location', C.c_uint32), ('body_tag', C.c_uint8 * 32)]


class Profile(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ('interface_number', 'alternate', 'in_address', 'out_address', 'max_packet', 'endpoints')]


class Event(C.Structure):
    _fields_ = [('phase', C.c_uint32), ('raw_return', C.c_int32)]


class Result(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ('abi', 'status', 'event_count', 'capture_attempted', 'claim_attempted',
        'interface_claimed', 'clock_invalid', 'cleanup_error', 'active_call_pending', 'persistent_camera_or_vendor_commands')]
    _fields_ += [('before', Snapshot), ('after', Snapshot), ('profile', Profile), ('events', Event * 64)]


def live_authority(goal):
    a, p = goal['authorization'], goal['prepared_first_device_trial']
    if a.get('Mac_owner_trial_authorized') is not True or a.get('driver_change') is not True or \
            p.get('Mac_owner_trial_released') is not True:
        raise Rejected('Mac owner trial lacks separately reviewed authorization and release')
    expected = {'locationID': 0x02100000, 'VID': 0x054c, 'PID': 0x0da1, 'model': 'ILME-FX3', 'firmware': '7.02'}
    if a.get('Mac_owner_trial_target') != expected:
        raise Rejected('owner trial target differs from the reviewed body/port')
    # No live process launcher exists in this stage. Passing a future authority
    # alone must not make an unfinished timeout/lifetime supervisor executable.
    raise Rejected('native candidate is not released: process supervision and one-shot entry are still required')


def from_live(library, goal=None):
    if goal is None:
        goal = json.loads((BASE / 'GOAL_STATUS.json').read_text())
    live_authority(goal)  # Before looking up a native symbol.
    raise AssertionError('unreachable while candidate is unreleased')


def from_fixture(library):
    marker = library.fx3_owner_fixture_marker
    marker.argtypes = []
    marker.restype = C.c_uint32
    if marker() != 0x46495834:
        raise Rejected('own marked fixture required')
    function = library.fx3_owner_run
    function.argtypes = [C.POINTER(Config), C.POINTER(Result), C.POINTER(Control)]
    function.restype = C.c_int
    return function


def public_result(result):
    if result.abi != 2 or result.event_count > 64:
        raise Rejected('invalid native result ABI/event count')
    return {'status_code': result.status, 'capture_attempted': bool(result.capture_attempted),
        'claim_attempted': bool(result.claim_attempted), 'interface_claimed_in_this_trial': bool(result.interface_claimed),
        'cleanup_error': bool(result.cleanup_error), 'clock_invalid': bool(result.clock_invalid),
        'active_native_call_phase': result.active_call_pending,
        'events': [{'phase': e.phase, 'raw_return': e.raw_return} for e in result.events[:result.event_count]],
        'same_camera_firmware_or_HEVC_recording_proven': False,
        'native_driver_return_independently_proven': False}


class Control(C.Structure):
    _fields_ = [("abi",C.c_uint32),("stop_requested",C.c_uint32),("reserved0",C.c_uint32),("reserved1",C.c_uint32)]

class FixtureGate(C.Structure):
    _fields_ = [("released",C.c_uint32),("entered",C.c_uint32)]
