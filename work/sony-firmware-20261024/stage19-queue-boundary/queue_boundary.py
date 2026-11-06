#!/usr/bin/env python3
"""Original queue predicates, replacement metadata and wait-set boundaries.

Synthetic read-only queue graphs; no task execution, native lock/wait/delete,
live camera, loader or recovery. Per-pool acceptance is not whole-program idle.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'stage18-cached-remain')]
import cached_remain as cr

pp, qp, APP, reg = cr.pp, cr.qp, cr.APP, cr.reg
SCRATCH, STACK = cr.SCRATCH, cr.STACK
FP = STACK + 0x200
MANAGER, POOL = SCRATCH + 0x1000, SCRATCH + 0x1320
HEAD, NODE, OLD, NEW = SCRATCH + 0x2000, SCRATCH + 0x2100, SCRATCH + 0x6000, SCRATCH + 0x8000
SET, BUCKETS, SENTINELS, SET_NODES, KEY = (SCRATCH + x for x in (0xb000, 0xb100, 0xb300, 0xb800, 0xcf00))
KIND = 113  # Bound below to the original sequence-name table, not a PTP ID.
VIRTUAL_TABLE = 0x46e8000


def p64(n): return struct.pack('<Q', n & 0xffffffffffffffff)


class BoundaryMicro(qp.QueryMicro):
    def __init__(self, *args, boundaries=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.boundaries = boundaries or {}

    def code(self, u, address, size, user):
        if address in self.boundaries:
            self.pcs.append(hex(address)); self.steps += 1
            self.abort('phase boundary: ' + self.boundaries[address])
            return
        super().code(u, address, size, user)


def make_set(uc, keys):
    uc.mem_write(SET, struct.pack('<QQ', BUCKETS, 31))
    uc.mem_write(BUCKETS, bytes(31 * 8))
    groups = {}
    for index, key in enumerate(keys): groups.setdefault(key % 31, []).append((index, key))
    for bucket, rows in groups.items():
        sentinel = SENTINELS + bucket * 16
        uc.mem_write(BUCKETS + bucket * 8, p64(sentinel))
        uc.mem_write(sentinel, p64(SET_NODES + rows[0][0] * 32))
        for n, (index, key) in enumerate(rows):
            following = SET_NODES + rows[n + 1][0] * 32 if n + 1 < len(rows) else 0
            uc.mem_write(SET_NODES + index * 32, struct.pack('<QI', following, key))


def set_lookup(keys, key):
    m = BoundaryMicro(APP, [(0x2c02470, 0x2c024d8)])
    make_set(m.uc, keys); m.uc.mem_write(KEY, pp.p32(key))
    r = m.run(0x2c02470, [SET, KEY]); result = m.uc.reg_read(reg.UC_ARM64_REG_X0)
    assert r['reason'] == 'returned' and bool(result) == (key in keys)
    if result: assert cr.a.read32(m.uc, result + 8) == key
    assert not r['stores']
    r.update(keys=list(keys), key=key, found_pointer=hex(result), lookup_adapter=False)
    return r


def object_bytes(kind, token=0, marker=2):
    raw = bytearray(0x4d8)
    struct.pack_into('<Q', raw, 0, VIRTUAL_TABLE)
    struct.pack_into('<I', raw, 8, kind)
    struct.pack_into('<Q', raw, 0x10, token)
    struct.pack_into('<I', raw, 0x388, marker)
    return bytes(raw)


def seed_pool(uc, current, queued):
    uc.mem_write(MANAGER, bytes(0x500))
    objects = []
    if current is not None:
        uc.mem_write(OLD, object_bytes(current)); objects.append(OLD)
    uc.mem_write(POOL + 0x78, p64(OLD if current is not None else 0))
    nodes = [SCRATCH + 0x4000 + i * 0x20 for i in range(len(queued))]
    uc.mem_write(POOL, struct.pack('<QQQ', nodes[0] if nodes else POOL, nodes[-1] if nodes else POOL, len(nodes)))
    for i, kind in enumerate(queued):
        obj = SCRATCH + 0x7000 + i * 0x600
        assert obj + 0x4d8 <= SET
        uc.mem_write(obj, object_bytes(kind)); objects.append(obj)
        uc.mem_write(nodes[i], struct.pack('<QQQ', nodes[i + 1] if i + 1 < len(nodes) else POOL,
                                          nodes[i - 1] if i else POOL, obj))
    return objects


def snapshot(uc, objects):
    return [bytes(uc.mem_read(MANAGER, 0x500))] + [bytes(uc.mem_read(obj, 0x4d8)) for obj in objects]


def pool_lookup(current, queued):
    boundaries = {0x2bd20bc: 'lookup_not_found_before_unlock', 0x2bd20d8: 'lookup_found_before_unlock'}
    m = BoundaryMicro(APP, [(0x2bd206c, 0x2bd20e0)], boundaries=boundaries)
    objects = seed_pool(m.uc, current, queued); before = snapshot(m.uc, objects)
    for rr, value in [(reg.UC_ARM64_REG_X21, MANAGER), (reg.UC_ARM64_REG_X20, 0),
                      (reg.UC_ARM64_REG_X19, 0), (reg.UC_ARM64_REG_X22, KIND),
                      (reg.UC_ARM64_REG_X29, FP)]: m.uc.reg_write(rr, value)
    r = m.run(0x2bd206c); found = m.uc.reg_read(reg.UC_ARM64_REG_X19)
    assert before == snapshot(m.uc, objects) and not r['stores']
    expected = current == KIND or KIND in queued
    assert bool(found) == expected and r['reason'].startswith('phase boundary: lookup_')
    if found: assert cr.a.read32(m.uc, found + 8) == KIND
    r.update(current_slot_kind=current, queued_kinds=list(queued), result_pointer=hex(found),
             graph_unchanged=True, native_lock_or_unlock_executed=False,
             scope='Inner lookup after an assumed acquired pool lock; not actual runtime idle or a frozen live snapshot')
    return r


def wait_pool(current, queued, exempt):
    boundaries = {0x2c0260c: 'pool_accepted', 0x2c02684: 'would_wait_after_unlock'}
    m = BoundaryMicro(APP, [(0x2c02550, 0x2c02748), (0x2c02470, 0x2c024d8)], boundaries=boundaries)
    objects = seed_pool(m.uc, current, queued); make_set(m.uc, exempt)
    before = snapshot(m.uc, objects)
    for rr, value in [(reg.UC_ARM64_REG_X19, POOL), (reg.UC_ARM64_REG_X20, 0x3931051),
                      (reg.UC_ARM64_REG_X21, 0), (reg.UC_ARM64_REG_X22, MANAGER),
                      (reg.UC_ARM64_REG_X23, SET), (reg.UC_ARM64_REG_X24, FP + 0x74),
                      (reg.UC_ARM64_REG_X25, FP + 0x78), (reg.UC_ARM64_REG_X26, MANAGER + 0x2bc0),
                      (reg.UC_ARM64_REG_X28, 0x186a0), (reg.UC_ARM64_REG_X29, FP)]:
        m.uc.reg_write(rr, value)
    r = m.run(0x2c02550)
    assert before == snapshot(m.uc, objects)
    if r['reason'] == 'phase boundary: pool_accepted': result = 'accepted'
    elif r['reason'] == 'phase boundary: would_wait_after_unlock': result = 'would_wait'
    elif r['reason'].startswith('firmware assertion entry reached'): result = 'assertion'
    else: raise AssertionError(r['reason'])
    r.update(current_slot_kind=current, queued_kinds=list(queued), membership_set=list(exempt),
             pool_predicate_result=result, graph_unchanged=True, original_membership_lookup=True,
             native_lock_wait_or_unlock_executed=False,
             scope='One original pool predicate in synthetic graph; accepted does not mean whole wait returned or any task stopped')
    return r


def virtual_replacement_hook(start, end):
    m = BoundaryMicro(APP, [(start, end), (0x275d3d4, 0x275d3d8)], end=end)
    raw = object_bytes(KIND, token=(KIND << 32) | 7)
    m.uc.mem_write(HEAD + 8, p64(NODE)); m.uc.mem_write(NODE + 0x10, p64(OLD)); m.uc.mem_write(OLD, raw)
    m.uc.reg_write(reg.UC_ARM64_REG_X19, HEAD)
    r = m.run(start)
    assert r['reason'] == 'conversion block complete' and hex(0x275d3d4) in r['pcs']
    assert bytes(m.uc.mem_read(OLD, len(raw))) == raw and not r['stores']
    r.update(old_marker_after=cr.a.read32(m.uc, OLD + 0x388), old_object_unchanged=True,
             actual_vtable_slot='0x20', slot_target='0x275d3d4 ret',
             task_cancel_join_or_completion_observed=False)
    return r


def token_arithmetic(kind, counter):
    m = BoundaryMicro(APP, [(0x2bd1914, 0x2bd192c)], end=0x2bd192c)
    pointer = SCRATCH + 0x1000
    m.uc.mem_write(pointer + 0x3d8, pp.p32(counter))
    m.uc.reg_write(reg.UC_ARM64_REG_X0, pointer)
    m.uc.reg_write(reg.UC_ARM64_REG_X19, kind)
    r = m.run(0x2bd1914)
    token = m.uc.reg_read(reg.UC_ARM64_REG_X19)
    assert token == (kind << 32) | counter
    assert cr.a.read32(m.uc, pointer + 0x3d8) == (counter + 1) & 0xffffffff
    r.update(synthetic_kind=kind, input_counter=counter, token_hex=hex(token),
             counter_after=cr.a.read32(m.uc, pointer + 0x3d8),
             preconditions='Start after original ADRP with a synthetic counter page; native global mutex and full token API are excluded')
    return r


def replacement_metadata(token, old_marker, new_marker):
    raw_old = object_bytes(KIND, token, old_marker); raw_new = object_bytes(KIND, 0, new_marker)
    m = BoundaryMicro(APP, [(0x2c3ddd8, 0x2c3ddec)], end=0x2c3ddec)
    m.uc.mem_write(HEAD + 8, p64(NODE)); m.uc.mem_write(NODE + 0x10, p64(OLD)); m.uc.mem_write(OLD, raw_old)
    m.uc.reg_write(reg.UC_ARM64_REG_X19, HEAD)
    before_delete = m.run(0x2c3ddd8); actual_token = m.uc.reg_read(reg.UC_ARM64_REG_X23)
    assert actual_token == token and not before_delete['stores']
    n = BoundaryMicro(APP, [(0x2c3ddf0, 0x2c3de14)], end=0x2c3de14)
    n.uc.mem_write(HEAD + 8, p64(NODE)); n.uc.mem_write(NODE + 0x10, p64(OLD)); n.uc.mem_write(NEW, raw_new)
    for rr, value in [(reg.UC_ARM64_REG_X19, HEAD), (reg.UC_ARM64_REG_X20, NEW),
                      (reg.UC_ARM64_REG_X21, KIND), (reg.UC_ARM64_REG_X22, MANAGER),
                      (reg.UC_ARM64_REG_X23, actual_token), (reg.UC_ARM64_REG_X24, KIND)]:
        n.uc.reg_write(rr, value)
    after_delete = n.run(0x2c3ddf0)
    assert int.from_bytes(n.uc.mem_read(NEW + 0x10, 8), 'little') == token
    assert int.from_bytes(n.uc.mem_read(NODE + 0x10, 8), 'little') == NEW
    assert cr.a.read32(n.uc, NEW + 0x388) == new_marker
    nameptr = int.from_bytes(n.uc.mem_read(NEW + 0x18, 8), 'little')
    assert APP.read(nameptr, 80).split(b'\0')[0] == b'sequence_get_media_remain'
    return {'old_token_hex': hex(token), 'old_marker_fixture': old_marker, 'new_marker_fixture': new_marker,
            'token_read_before_delete': before_delete, 'metadata_after_delete_precondition': after_delete,
            'new_token_hex': hex(token), 'new_marker_after': new_marker, 'new_name_pointer': hex(nameptr),
            'allocation_constructor_container_move_deletion_or_concurrency_executed': False,
            'scope': 'Separate original pre-delete token read and post-delete metadata slice; excludes unknown intervening operations, not a complete replacement execution'}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    args = parser.parse_args(); qp.verify_volume()
    out = Path(args.output).resolve(); assert STAGE in out.parents and not out.exists(); out.mkdir()
    sources = [APP.path, cr.MPR.path, Path(cr.__file__), Path(cr.cp.__file__), Path(pp.__file__), Path(qp.__file__),
               Path(cr.ss.__file__), BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    previous = json.loads((BASE / 'stage18-cached-remain/final-receipt.json').read_text())
    assert all(qp.sha(ROOT / f['path']) == f['sha256'] for f in previous['files'])
    im = cr.ss.StaticImage()
    assert struct.unpack('<Q', APP.read(VIRTUAL_TABLE + 0x20, 8))[0] == 0x275d3d4
    assert APP.read(0x275d3d4, 4).hex() == 'c0035fd6'
    nameptr = struct.unpack('<Q', APP.read(0x4113260 + KIND * 8, 8))[0]
    assert APP.read(nameptr, 80).split(b'\0')[0] == b'sequence_get_media_remain'
    assert struct.unpack('<I', APP.read(0x39091b0 + KIND * 4, 4))[0] == 0
    lookups = [set_lookup(keys, key) for keys in ((), (KIND,), (KIND, KIND + 31), (KIND + 31,))
               for key in (KIND, KIND + 31, KIND + 62)]
    queries = [pool_lookup(current, queued) for current, queued in
               ((None, ()), (KIND, ()), (KIND + 1, ()), (None, (KIND,)),
                (KIND + 1, (KIND + 2, KIND)), (KIND, (KIND,)))]
    specs = [(None, (), (), 'accepted'), (KIND, (), (), 'would_wait'),
             (KIND, (), (KIND,), 'accepted'), (KIND, (KIND + 1,), (KIND,), 'assertion'),
             (None, (KIND,), (KIND,), 'accepted'), (None, (KIND,), (), 'would_wait'),
             (None, (KIND, KIND + 1), (KIND,), 'assertion'),
             (None, (KIND + 1,), (KIND,), 'would_wait'),
             (KIND + 1, (), (KIND,), 'would_wait')]
    predicates = []
    for current, queued, exempt, expected in specs:
        row = wait_pool(current, queued, exempt); assert row['pool_predicate_result'] == expected
        predicates.append(row)
    virtuals = [virtual_replacement_hook(start, end) for start, end in
                ((0x2c3dda0, 0x2c3ddb4), (0x2c3df68, 0x2c3df7c))]
    tokens = [token_arithmetic(kind, counter) for kind in (0, KIND)
              for counter in (0, 1, 0xfffffffe, 0xffffffff)]
    replacements = [replacement_metadata((KIND << 32) | 7, old, new) for old, new in ((2, 0), (0, 2), (2, 2))]
    strict = BoundaryMicro(APP, [(0x2c024d8, 0x2c02748)])
    full_wait_stop = strict.run(0x2c024d8, [MANAGER, SET])
    assert full_wait_stop['reason'] == 'unapproved execution 2aa1c0c'
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    regions = [('refresh_without_pool_lock_in_function', 0x2c3dd34, 0x2c3de38),
               ('refresh_with_pool_lock', 0x2c3deec, 0x2c3e01c),
               ('metadata_container_move_not_executed', 0x2bd2dd4, 0x2bd2e60),
               ('token_generation', 0x2bd18ec, 0x2bd1940),
               ('lookup', 0x2bd202c, 0x2bd20e0), ('wait_membership_lookup', 0x2c02470, 0x2c024d8),
               ('wait_body', 0x2c024d8, 0x2c02748), ('cache_deleting_destructor', 0x2bb0390, 0x2bb03cc),
               ('base_destructor', 0x28443a0, 0x2844420),
               ('ownership_handoff_before_wait', 0x2aa1c0c, 0x2aa1d4c),
               ('ownership_reacquire_after_wait', 0x2aa2818, 0x2aa29f0)]
    proof = {'status': 'PASS_QUEUE_REPLACEMENT_AND_WAIT_MEMBERSHIP_BOUNDARIES',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'inputs_unchanged': hashes,
        'internal_kind_binding': {'kind': KIND, 'name_table': '0x4113260', 'name': 'sequence_get_media_remain',
            'pool_mapping_table': '0x39091b0', 'pool': 0, 'not_remote_format113_or_PTP_ID': True},
        'membership_lookup_cases': lookups, 'pool_lookup_cases': queries, 'wait_pool_predicates': predicates,
        'replacement_virtual_slot_cases': virtuals, 'token_arithmetic_cases': tokens,
        'replacement_metadata_cases': replacements, 'full_wait_unmodelled_owner_entry_stop': full_wait_stop,
        'static_regions': [{'name': name, 'start': hex(start), 'end': hex(end), 'instructions': im.dump(start, end)}
                           for name, start, end in regions],
        'findings': ['For this exact class the refresh virtual slot0x20 is RET; it does not itself change the marked object or acknowledge task termination.',
                     'Refresh preserves the old64bit request token while replacing the freshly captured cache. That token is not a configuration epoch.',
                     'The inner lookup checks a separate object slot and then the queued list; list emptiness alone does not prove this lookup is absent.',
                     'The original per-pool wait predicate accepts a current object when its kind is in the input set and the queue is empty. Do not interpret that set as tasks to wait for.',
                     'Full wait calls logical model-ownership handoff/reacquire helpers and a condition-variable wait. Actual admission freeze, worker state and post-wait epoch must be verified separately.'],
        'scope': 'Bounded original instruction fragments on synthetic graphs and counter pages. No native thread, whole replacement, complete wait, task run, destructor, free or device operation.',
        'real_quiescence_observer_admission_gate_loader_or_recovery_implemented': False,
        'camera_USB_driver_files_module_WBI_or_firmware_write': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'internal_media_remain_kind': KIND, 'pool_index': 0,
        'original_membership_lookup_cases': len(lookups), 'pool_lookup_cases': len(queries),
        'per_pool_wait_cases': len(predicates), 'empty_virtual_slot_calls': len(virtuals),
        'token_arithmetic_cases': len(tokens), 'replacement_metadata_cases': len(replacements),
        'wait_set_contains_running_kind_can_accept_pool': True,
        'replacement_preserves_token_across_different_markers': True,
        'full_native_wait_or_safe_unload_verified': False, 'goal_complete': False}
    qp.write_json(out / 'queue-boundary-results.json', proof); qp.write_json(out / 'summary.json', summary)
    qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'results_sha256': qp.sha(out / 'queue-boundary-results.json'),
        'summary_sha256': qp.sha(out / 'summary.json'), 'inputs': hashes, 'volume_uuid': qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
