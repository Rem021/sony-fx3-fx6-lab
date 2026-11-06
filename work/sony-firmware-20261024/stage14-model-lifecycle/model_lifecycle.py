#!/usr/bin/env python3
"""Bounded original model-update and synthetic profile-lifecycle checks.

This does not update any camera, run listeners, persist settings or expose a
device interface. Synthetic context selects an original no-record branch of the
change-record handler; the ordinary record branch is separately shown to stop.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import plistlib
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'stage13-query-profile'), str(BASE / 'stage12-prototype/profile'),
               str(BASE / 'stage4-windows-collab/mac-verification')]
import query_profile as qp
import profile_prototype as pp
from offline_verify import APP, MPR, SCRATCH, STACK, STOP, read32
import unicorn.arm64_const as reg

UPDATE = 0x1e49a38
REGISTRY = 0x4174920
HANDLERS = 0x46f3ed0
RECORD_DISPATCH = 0x2f6e7ac
RECORD_HANDLER = 0x2f6d454
RECORD_CONTEXT_HELPER = 0x2f6cfc4
FILTER_MAP = 0x9ad5f48
CURRENT, MIRROR, WRAPPER, CONTEXT = SCRATCH + 0x2000, SCRATCH + 0x2010, SCRATCH + 0x1000, SCRATCH + 0x4000


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify_volume():
    x = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert x['VolumeUUID'] == qp.EXPECTED_VOLUME and x['MountPoint'] == '/Volumes/KAFU2T'


def dump(a, z):
    return [{'pc': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
            for i in APP.md.disasm(APP.read(a, z - a), a)]


def registry_row(key):
    address = REGISTRY + key * 24
    raw = APP.read(address, 24)
    handler_index, stored_key, length = struct.unpack_from('<iII', raw)
    name_ptr = struct.unpack_from('<Q', raw, 16)[0]
    assert stored_key == key and 0 < length < 256 and 0 <= handler_index < 32
    name = APP.read(name_ptr, length + 1).split(b'\0')[0].decode('ascii')
    pointer_slot = HANDLERS + handler_index * 8
    handler = struct.unpack('<Q', APP.read(pointer_slot, 8))[0]
    return {'internal_key': hex(key), 'record_address': hex(address), 'record_bytes': raw.hex(),
            'name': name, 'handler_index': handler_index, 'handler_pointer_slot': hex(pointer_slot),
            'handler': hex(handler), 'not_a_persistent_or_PTP_address': True}


class UpdateMicro(pp.StrictMicro):
    def code(self, u, a, n, user):
        if a == RECORD_CONTEXT_HELPER:
            self.pcs.append(hex(a))
            self.steps += 1
            self.abort('unmodelled change-record context/thread helper; no adapter')
            return
        super().code(u, a, n, user)


def update_case(value, *, initial=0, bank=2):
    ranges = [(UPDATE, 0x1e49a8c), (RECORD_DISPATCH, 0x2f6e834),
              (RECORD_HANDLER, 0x2f6d5a4), (0x2b02cc8, 0x2b02d00), (0x2ab2ddc, 0x2ab2e30)]
    m = UpdateMicro(APP, ranges)
    # Two model-value slots, not an allowed-values collection or backup address.
    m.uc.mem_write(CURRENT, pp.p32(initial))
    m.uc.mem_write(MIRROR, pp.p32(initial))
    m.uc.mem_write(WRAPPER, struct.pack('<QQIIQ', CURRENT, MIRROR, 0x39c, 0, CONTEXT))
    # The original change-record filter lookup sees an empty synthetic bucket.
    m.uc.mem_write(FILTER_MAP, struct.pack('<QQ', SCRATCH + 0x3000, 1))
    m.uc.mem_write(SCRATCH + 0x3000, struct.pack('<Q', 0))
    # Bank >1 takes the real handler's early no-record branch. This is synthetic
    # state, not evidence that normal production recording/notification is safe.
    m.uc.mem_write(CONTEXT + 0x1efa, bytes([bank]))
    result = m.run(UPDATE, [WRAPPER, value])
    result.update(input_value=value, initial_value=initial, synthetic_record_bank=bank,
                  current_value=read32(m.uc, CURRENT), paired_value=read32(m.uc, MIRROR),
                  changed_flag=m.uc.mem_read(WRAPPER + 0x14, 1)[0],
                  model_stores=[w for w in result['stores'] if int(w['address'], 16) in
                                (CURRENT, MIRROR, WRAPPER + 0x14)])
    if result['reason'] == 'returned':
        assert result['current_value'] == result['paired_value'] == value
        assert result['changed_flag'] == 1
        assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
    return result


def lifecycle_row(im, patches, qpatch, mode):
    base_builder = pp.builder(im, patches, frame=0, exposure=mode)
    stored_builder = pp.builder(im, patches, frame=2, exposure=mode)
    base_query = qp.query(qpatch, frame=0, mode=mode)
    stored_query = qp.query(qpatch, frame=2, mode=mode)
    b_ok, q_ok = base_builder['reason'] == 'returned', base_query['reason'] == 'returned'
    p_b_ok, p_q_ok = stored_builder['reason'] == 'returned', stored_query['reason'] == 'returned'
    if b_ok and q_ok and p_b_ok and p_q_ok:
        classification = 'target_parameters_returned_in_ordinary_movie_fixture'
        assert stored_builder['builder_tuple'] == [15, 6, 2, 0]
        assert stored_query['output_vpc_quality_frame'] == [6, 6, 3]
    elif b_ok and q_ok and not p_b_ok and not p_q_ok:
        classification = 'valid_baseline_fixture_but_stored_profile_hits_original_error_paths'
    else:
        classification = 'fixture_or_additional_mode_dependencies_unclosed'
    return {'mode_value': mode, 'classification': classification,
            'baseline_typed_HS_frame': 0, 'stored_profile_typed_HS_frame': 2,
            'model_key_persisted_or_mode_transition_executed': False,
            'baseline_builder': base_builder, 'profile_builder': stored_builder,
            'baseline_query': base_query, 'profile_query': stored_query}


def newjson(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    verify_volume()
    destination = Path(args.output).resolve()
    assert STAGE in destination.parents and not destination.exists()
    destination.mkdir()
    originals = {str(n.path.relative_to(ROOT)): sha(n.path) for n in (APP, MPR)}
    dependencies = [BASE / 'stage13-query-profile/query_profile.py',
                    BASE / 'stage12-prototype/profile/profile_prototype.py',
                    BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    before = {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    rows = [registry_row(k) for k in (0x399, 0x39c, 0x3a4, 0x3a5, 0x3a6, 0x7a7, 0x12ca)]
    assert all(r['handler'] == hex(RECORD_HANDLER) for r in rows[:5])
    writes = []
    for value in (0, 1, 2, 3, 7, 8, 9, 0xffffffff):
        result = update_case(value)
        assert result['reason'] == 'returned'
        assert any(int(w['pc'], 16) == 0x1e49a6c for w in result['model_stores'])
        assert any(int(w['pc'], 16) == 0x1e49a74 for w in result['model_stores'])
        writes.append(result)
    strict = update_case(2, bank=0)
    assert strict['reason'].startswith('unmodelled change-record context')
    assert strict['current_value'] == strict['paired_value'] == 0 and strict['changed_flag'] == 0
    unchanged = update_case(2, initial=2, bank=0)
    assert unchanged['reason'] == 'returned'
    im = pp.Image()
    patches = pp.trampolines(im)
    qpatch, _ = qp.new_patch()
    lifecycle = [lifecycle_row(im, patches, qpatch, mode) for mode in range(17)]
    groups = {}
    for row in lifecycle:
        groups.setdefault(row['classification'], []).append(row['mode_value'])
    assert groups['target_parameters_returned_in_ordinary_movie_fixture'] == [5, 6, 7, 8, 9, 15]
    assert groups['valid_baseline_fixture_but_stored_profile_hits_original_error_paths'] == [0, 1, 2, 3, 4]
    assert originals == {str(n.path.relative_to(ROOT)): sha(n.path) for n in (APP, MPR)}
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in dependencies}
    proof = {
        'status': 'PASS_BOUNDED_LIFECYCLE_AND_MODEL_SLOT_AUDIT',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'Synthetic local model-update context and independently constructed mode fixtures; not a real transition, listener execution, persistence or camera test',
        'source_originals': originals, 'dependencies_unchanged': before,
        'registry': rows,
        'getter_pair': {'current': {'function': '0x2934d14', 'global': hex(im.leaf(0x2934d14))},
                        'paired': {'function': '0x2934d28', 'global': hex(im.leaf(0x2934d28))},
                        'both_receive_same_32bit_value_in_local_update': True,
                        'paired_slot_is_not_proven_allowed_values_or_persistent_backup': True},
        'static_regions': [
            {'start': hex(a), 'end': hex(z), 'instructions': dump(a, z)} for a, z in
            [(0x2934d14, 0x2934d3c), (0x27c79c4, 0x27c7ac8), (UPDATE, 0x1e49a8c),
             (RECORD_DISPATCH, 0x2f6e834), (RECORD_HANDLER, 0x2f6d5a4),
             (0x1e49074, 0x1e49088), (0x2759ee4, 0x2759eec)]],
        'conditional_local_update_cases': writes,
        'normal_change_record_branch_stopped_without_adapter': strict,
        'unchanged_value_case': unchanged,
        'local_update_stubs': [],
        'model_listeners_or_save_executed': False,
        'synthetic_mode_matrix': lifecycle, 'matrix_groups': groups,
        'policy_not_selected': ['automatic normalization before leaving ordinary movie',
                                'interpreting a stored movie preset in other modes'],
        'policy_note': 'Do not choose either lifecycle policy without caller/UI/persistence evidence; these are unresolved design options, not executable camera steps.',
        'camera_USB_UI_or_native_actions': False, 'camera_state_or_files_written': False,
        'persisted_key_or_backup_address_discovered': False,
        'goal_complete': False,
    }
    newjson(destination / 'model-lifecycle-results.json', proof)
    summary = {'status': proof['status'], 'conditional_model_slot_writes': len(writes),
               'negative_change_record_dependency_cases': 1, 'unchanged_value_case': 1,
               'mode_fixture_pairs': len(lifecycle), 'groups': groups,
               'real_mode_transitions_or_persistence_tested': False,
               'source_unchanged': True, 'goal_complete': False}
    newjson(destination / 'summary.json', summary)
    newjson(destination / 'source-receipt.json', {
        'script': str(Path(__file__).relative_to(ROOT)), 'script_sha256': sha(__file__),
        'results_sha256': sha(destination / 'model-lifecycle-results.json'),
        'summary_sha256': sha(destination / 'summary.json'), 'originals': originals,
        'dependencies': before, 'volume_uuid': qp.EXPECTED_VOLUME,
        'bounded_guest_function_emulation': True, 'camera_native_execution': False})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
