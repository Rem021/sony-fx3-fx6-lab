#!/usr/bin/env python3
"""Review original authentication publication and history effects without executing them."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
PREVIOUS = BASE / 'stage134-backup-reader-scope-and-service-extension'


def main():
    source = PREVIOUS / 'audit_readers.py'
    receipt = json.loads((PREVIOUS / 'final-receipt.json').read_text())
    pin = next(x for x in receipt['files'] if x['path'] == source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('prior_static_reader', source)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    core = prior.Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    names = ['NinThread', '_ZN19WorkerThreadManager20start_authenticationEPFvvE',
             '_ZN19WorkerThreadManager12registHaspIdEi', '_ZN19WorkerThreadManager10onCompleteEi',
             'Regist_HaspId', 'Read_Hasp', '_Z15tlog_file_existv', '_Z14tlog_read_fileP9StraceLog',
             '_Z16tlog_update_fileiP10StraceData', '_Z15tlog_write_fileP9StraceLog',
             '_ZN3Usb24onCompleteAuthenticationEv', '_ZN10CoreModule9nin_startER13NinCooperator']
    functions = [core.function(n) for n in names]
    relocations = list(core.elf.get_section_by_name('.rela.dyn').iter_relocations())
    vtable = core.symbols['_ZTV19WorkerThreadManager']
    address_point = vtable['st_value'] + 16
    slots = []
    for rel in relocations:
        if address_point <= rel['r_offset'] < vtable['st_value'] + vtable['st_size']:
            symbol = core.dynsym.get_symbol(rel['r_info_sym'])
            assert rel['r_info_type'] == 257
            slots.append({'offset': rel['r_offset'] - address_point, 'symbol': symbol.name,
                          'target': hex(symbol['st_value'] + rel['r_addend'])})
    assert next(x['symbol'] for x in slots if x['offset'] == 0x20) == '_ZN19WorkerThreadManager12registHaspIdEi'
    assert next(x['symbol'] for x in slots if x['offset'] == 0x28) == '_ZN19WorkerThreadManager10onCompleteEi'
    instructions = {int(i['pc'], 16): i for f in functions for i in f['instructions']}
    assert instructions[0xbe9c]['asm'] == 'ldr x2, [x0, #0x20]'
    assert instructions[0xbea4]['asm'] == 'blr x2'
    assert instructions[0xbf24]['asm'] == 'ldr x2, [x0, #0x28]'
    assert instructions[0xbf2c]['asm'] == 'blr x2'
    checked = []
    for address, name in [(0xbe6c, '_Z9SerializePFiPhmEPvm'), (0xc194, 'Regist_HaspId'),
                          (0xbf30, '_Z15tlog_file_existv'), (0xbf4c, '_Z16tlog_update_fileiP10StraceData'),
                          (0x137b0, '_Z14tlog_read_fileP9StraceLog'), (0x138dc, '_Z15tlog_write_fileP9StraceLog'),
                          (0x1360c, 'fopen'), (0x1362c, 'fread'), (0x13684, 'fopen'),
                          (0x136a0, 'fwrite'), (0x136b0, 'fclose'), (0xc044, '_ZNK8DeviceIo5writeEPKvm')]:
        checked.append(core.expect_call(address, name))
    assert instructions[0x13624]['asm'] == 'mov x1, #0x1000'
    assert instructions[0x1369c]['asm'] == 'mov x1, #0x1000'
    assert instructions[0xc040]['asm'] == 'mov x2, #3'
    paths = {hex(a): core.string(a) for a in (0x55121, 0x54e8c, 0x54e89, 0x54e9d, 0x16a74, 0x16a80)}
    assert list(paths.values()) == ['/setting/.hasp', '/setting/.etools', 'rb', 'wb', '/ramdsk/dev', '/ramdsk/dev/mode']
    globals = []
    for rel in relocations:
        if rel['r_offset'] in (0x6aec0, 0x6aee0, 0x6aeb0, 0x6ae40, 0x6ae58, 0x6aea0):
            symbol = core.dynsym.get_symbol(rel['r_info_sym'])
            globals.append({'GOT': hex(rel['r_offset']), 'symbol': symbol.name, 'target': hex(symbol['st_value'])})
    assert len(globals) == 6
    runtime = json.loads((BASE / 'stage7-entry/firmware/runtime-static.json').read_text())
    fstab = runtime['scripts']['/sbin/initrc/fstab']
    active_lines = [line for line in fstab['text'].splitlines() if line and not line.startswith('#')]
    assert any(line.startswith('/dev/nflasha2\t/setting ') and '\trw,' in line for line in active_lines)
    assert any(line.startswith('/dev/nflasha10\t/tmp\t') and '\trw,' in line for line in active_lines)
    assert any(line.startswith('/dev/nflasha15\t/usr\t') and '\tro,' in line for line in active_lines)
    result = {
        'status': 'PASS_STATIC_AUTH_CALLBACK_PUBLICATION_AND_HISTORY_ORDER_NOT_DEVICE_AUTHENTICATION',
        'core_SHA256': sha256(core.raw).hexdigest(), 'functions': functions, 'checked_PLT_calls': checked,
        'WorkerThreadManager_vtable_address_point': hex(address_point), 'worker_vtable_slots': slots,
        'global_bindings': globals, 'strings': paths,
        'conditional_original_order': [
            {'pc': '0xbe6c', 'event': 'serialize final auth reply'},
            {'pc': '0xbea4', 'event': 'virtual registHaspId; standard worker slot -> Regist_HaspId'},
            {'pc': '0xbf2c', 'event': 'virtual onComplete; standard worker slot -> table publication and callback'},
            {'pc': '0xbf4c', 'event': 'if tlog file exists, request log update'},
            {'pc': '0xc044', 'event': 'level3 path prepares 3-byte /ramdsk/dev/mode write before thread return'}],
        'onComplete_table_mapping': {'1': 'pFunc_level_C', '2': 'pFunc_level_B', '3': 'pFunc_level_A', 'other': None},
        'terminal_change_function_is_disabled': 'level != 3; do not mistake this variable for an encoding/thread lock',
        'callback_invoked_for_other_null_table_levels_in_this_function': True,
        'history_effects': {'hasp': 'conditional88B history update, as stage134; no target file presence assumed',
                           'etools': 'existing/readable4096B log -> decoder/update/encoder -> wb fwrite4096B; actual existence/mount/output not tested',
                           'mode': 'level3 creates/writes3B path; other branch removes/rmdir; backing of /ramdsk not established here'},
        'official_startup_fstab': {'recorded_source_sha256': fstab['sha256'], 'text': fstab['text'],
                                  'actual_body_mounts_not_measured': True},
        'temporary_path_name_not_RAM_guarantee': '/tmp is configured on nflasha10; do not assume desktop tmpfs semantics',
        'limits': ['Static vtable/branch sequence only, not a successful cryptographic handshake or live object construction.',
                   'Auth reply and callback are not proof all subsequent writers/workers ended.',
                   'Three shipped tables remain the reviewed scope; no independent recovery or dynamic-plugin closure proved.',
                   'No service entry/stop, real camera history read/write, active query or native Sony execution.'],
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'authentication-publication-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'whole_original_functions': len(functions),
                      'worker_slots_verified': len(slots), 'PLT_targets_checked': len(checked),
                      'device_authentication_executed': False}))


if __name__ == '__main__':
    main()
