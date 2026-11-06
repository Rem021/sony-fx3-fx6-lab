#!/usr/bin/env python3
"""Cache construction, admission, queue publication and whole-pool stop audit.

Independent bounded guest phases, including a pre-queue observation witness.
No native allocator, token API, lock, list hook, notify, worker or thread exit.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'stage20-worker-lifecycle'))
import worker_lifecycle as w

q, cr, pp, qp, APP, reg = w.q, w.q.cr, w.pp, w.qp, w.APP, w.reg
SCRATCH, MANAGER, POOL, OLD, FP = w.SCRATCH, w.MANAGER, w.POOL, w.OLD, w.FP
PARAMS, CELL = SCRATCH + 0xc000, SCRATCH + 0xc800
DISPATCH, KIND = 0x4a41278, q.KIND


def phase(r, description):
    r['scope'] = description + '; independent synthetic phase, not complete caller, admission or native synchronization.'
    return r


def dispatch_to_factory(option):
    m = q.BoundaryMicro(APP, [(0x2bd1980, 0x2bd19bc)],
                        boundaries={0x2c3e01c: 'original_table_factory_entry'})
    w.putregs(m, x20=MANAGER, x24=KIND, x25=PARAMS, x22=option)
    r = m.run(0x2bd1980)
    assert r['reason'] == 'phase boundary: original_table_factory_entry'
    actual = [m.uc.reg_read(getattr(reg, 'UC_ARM64_REG_X' + str(i))) for i in range(5)]
    assert actual == [MANAGER, KIND, PARAMS, option, 0] and not r['stores']
    r.update(raw_option=option, actual_arguments=[hex(v) for v in actual], member_adjustment=0)
    return phase(r, 'Original member-function table dispatch after assumed acquired manager mutex')


def typed_to_factory(option):
    m = q.BoundaryMicro(APP, [(0x271760c, 0x2717638), (0x2bd1798, 0x2bd17a4)],
                        boundaries={0x2c3de38: 'original_typed_factory_entry'})
    m.uc.mem_write(PARAMS + 4, pp.p32(option))
    r = m.run(0x271760c, [PARAMS])
    assert r['reason'] == 'phase boundary: original_typed_factory_entry'
    actual = [m.uc.reg_read(getattr(reg, 'UC_ARM64_REG_X' + str(i))) for i in range(4)]
    assert actual == [0x9680760, KIND, PARAMS + 0x10, option]
    r.update(raw_option=option, actual_arguments=[hex(v) for v in actual],
             global_manager_getter_executed=True, outer_callers_or_lock_ownership_known=False)
    return phase(r, 'Original typed wrapper and pure manager getter, stopped before factory body')


def factory_to_enqueue(typed):
    start, end = (0x2c3de70, 0x2c3de98) if typed else (0x2c3e068, 0x2c3e080)
    m = q.BoundaryMicro(APP, [(start, end)], boundaries={0x2c0d628: 'original_common_enqueue_entry'})
    if typed:
        w.putregs(m, x19=MANAGER, x20=OLD, x21=KIND, x22=1)
    else:
        w.putregs(m, x19=OLD, x21=MANAGER, x22=KIND, x23=1)
    r = m.run(start)
    assert r['reason'] == 'phase boundary: original_common_enqueue_entry'
    actual = [m.uc.reg_read(getattr(reg, 'UC_ARM64_REG_X' + str(i))) for i in range(5)]
    assert actual == [MANAGER, OLD, KIND, 1, int(typed)]
    r.update(factory='typed' if typed else 'table', actual_arguments=[hex(v) for v in actual],
             registry_lock_control=int(typed), allocator_or_constructor_executed=False)
    return phase(r, 'Original post-constructor marshalling; typed saved-frame and table dependency-return preconditions are synthetic')


def off_queue_witness(im, rows, wide, flag):
    captured, blob = cr.capture(im, rows, wide, cr.cache_marker(im), {'frame': 0}, flag=flag)
    assert int.from_bytes(blob[0x388:0x38c], 'little') == (2 if flag else 0)
    m = q.BoundaryMicro(APP, [(0x2c0d628, 0x2c0d86c)])
    q.seed_pool(m.uc, None, ())
    m.uc.mem_write(OLD, blob)
    m.uc.mem_write(SCRATCH + 0xf000, pp.p32(0))
    r = m.run(0x2c0d628, [MANAGER, OLD, KIND, 1, 1])
    assert r['reason'] == 'unapproved execution 2bd18ec'
    assert bytes(m.uc.mem_read(OLD, len(blob))) == blob
    assert w.read64(m.uc, POOL + 0x78) == 0 and w.read64(m.uc, POOL + 0x10) == 0
    observed = w.observe_pool(m)
    assert observed['predicate'] == 'accepted'
    r.update(capture=captured, capture_flag_fixture=flag, later_flag_fixture=0,
             outside_queue_marker=int.from_bytes(blob[0x388:0x38c], 'little'), observer=observed,
             original_token_API_executed=False, queue_or_current_published=False,
             actual_race_or_outer_lock_exclusion_proven=False)
    return phase(r, 'Bounded real getter capture and earlier guest marker, then a separate common-admission entry with empty synthetic pool. Constructor prefix, real allocation, outer ownership and scheduling are excluded')


def metadata_before_queue():
    m = q.BoundaryMicro(APP, [(0x2c0d678, 0x2c0d6a8)])
    q.seed_pool(m.uc, None, ()); w.task_fixture(m)
    token, name = w.TOKEN, w.read_file64(0x4113260 + KIND * 8)
    m.uc.mem_write(FP + 0x64, pp.p32(KIND))
    m.uc.mem_write(MANAGER + 0x2bf8, q.p64(31))
    w.putregs(m, x0=token, x19=MANAGER, x20=OLD, x21=KIND, x22=FP + 0x64, x23=name, x29=FP)
    r = m.run(0x2c0d678)
    assert r['reason'] == 'unapproved execution 2bd14d8'
    assert w.read64(m.uc, OLD + 0x10) == token and w.read64(m.uc, OLD + 0x18) == name
    assert w.read64(m.uc, OLD + 0x20) == MANAGER and cr.a.read32(m.uc, OLD + 8) == KIND
    assert cr.a.read32(m.uc, OLD + 0x388) == 2
    observed = w.observe_pool(m); assert observed['predicate'] == 'accepted'
    r.update(token_input_fixture=hex(token), metadata_written=True, observer=observed,
             original_token_generation_registry_or_queue_insertion_executed=False)
    return phase(r, 'Post-token-return precondition; original metadata writes stop before dependency-map lookup')


def registry_lock_branch(control):
    m = q.BoundaryMicro(APP, [(0x2c0d6b4, 0x2c0d6d4), (0x2c0d7c4, 0x2c0d7e8)])
    w.task_fixture(m)
    w.putregs(m, x19=MANAGER, x24=control, x29=FP)
    m.uc.mem_write(FP + 0x68, q.p64(OLD))
    r = m.run(0x2c0d6b4)
    assert r['reason'] == ('unapproved execution 16ed554' if control else 'unapproved execution 2c027c0')
    r.update(registry_lock_control=control, native_registry_or_manager_lock_executed=False,
             outer_manager_lock_ownership_verified=False)
    return phase(r, 'Original flag-dependent registry-lock branch; zero control does not prove the caller lacks the lock')


def pool_lock_destination(kind):
    m = q.BoundaryMicro(APP, [(0x2c0d714, 0x2c0d740)])
    m.uc.mem_write(FP + 0x64, pp.p32(kind))
    w.putregs(m, x19=MANAGER, x20=0x90, x29=FP)
    r = m.run(0x2c0d714)
    pool = int.from_bytes(APP.read(0x39091b0 + kind * 4, 4), 'little')
    assert r['reason'] == 'unapproved execution 16ed554'
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == MANAGER + 0x338 + pool * 0x90
    assert m.uc.reg_read(reg.UC_ARM64_REG_X21) == MANAGER + 0x320 + pool * 0x90
    r.update(kind=kind, mapped_pool=pool, mutex_pointer=hex(MANAGER + 0x338 + pool * 0x90),
             native_pool_lock_or_queue_insertion_executed=False)
    return phase(r, 'Original mapping after excluded token/dependency/registry/statistics operations')


def queue_notify_destination():
    m = q.BoundaryMicro(APP, [(0x2c0d770, 0x2c0d77c)])
    w.putregs(m, x19=MANAGER, x20=0)
    r = m.run(0x2c0d770)
    assert r['reason'].startswith('unapproved PLT ')
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == POOL + 0x48
    r.update(original_plt_symbol=APP.plt[0x1593f80], condition_variable='pool+0x48',
             manager_wait_cv_is_different=True, native_notify_executed=False)
    return phase(r, 'Post-insertion and post-unlock precondition; prepare worker wakeup destination only')


def null_task_branch():
    m = q.BoundaryMicro(APP, [(0x2bd76bc, 0x2bd76cc), (0x2bd778c, 0x2bd7794)])
    q.seed_pool(m.uc, None, ())
    w.putregs(m, x19=w.ARGS, x20=0, x22=FP + 0x70)
    r = m.run(0x2bd76bc)
    assert r['reason'] == 'unapproved execution 1724ccc'
    assert '0x2bd778c' in r['pcs'] and '0x2bd76c4' not in r['pcs'] and not r['stores']
    r.update(null_task_selects_worker_return_path=True, worker_return_or_thread_exit_executed=False)
    return phase(r, 'Selected-null-task precondition after excluded queue removal; stop before unlock and thread return')


def stop_wait_destination():
    m = q.BoundaryMicro(APP, [(0x2c0d5fc, 0x2c0d604), (0x2f71e60, 0x2f71e64)])
    handle = 0x13579bdf
    m.uc.mem_write(MANAGER + 0x1360, q.p64(handle))
    w.putregs(m, x19=MANAGER + 0x1360)
    r = m.run(0x2c0d5fc)
    assert r['reason'] == 'unapproved PLT osal_wait_thread_exit'
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == handle
    r.update(thread_handle_fixture=hex(handle), backend_symbol=APP.plt[0x15940b0],
             actual_wait_join_shutdown_or_restart_executed=False)
    return phase(r, 'One original whole-manager stop-loop iteration before native thread-exit wait')


def direct_branches(im, targets):
    rows = []
    for segment in im.elf.iter_segments():
        if segment['p_type'] != 'PT_LOAD' or not segment['p_flags'] & 1: continue
        raw, base = segment.data(), segment['p_vaddr']
        for offset in range(0, len(raw) - 3, 4):
            word = struct.unpack_from('<I', raw, offset)[0]
            if word & 0x7c000000 != 0x14000000: continue
            displacement = word & 0x3ffffff
            if displacement & (1 << 25): displacement -= 1 << 26
            target = base + offset + displacement * 4
            if target in targets:
                rows.append({'pc': hex(base + offset), 'mnemonic': 'bl' if word >> 31 else 'b', 'target': hex(target)})
    return rows


def run(out):
    sources = [APP.path, cr.MPR.path] + [Path(m.__file__) for m in (w, q, cr, cr.cp, cr.ss, pp, qp, cr.a)]
    sources.append(Path(sys.modules[pp.Image.__module__].__file__))
    sources.append(BASE / 'stage4-windows-collab/mac-verification/offline_verify.py')
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    previous = BASE / 'stage20-worker-lifecycle/final-receipt.json'
    assert all(qp.sha(ROOT / f['path']) == f['sha256'] for f in json.loads(previous.read_text())['files'])
    im = pp.Image(); rows, wide = cr.cache_rows(im)
    assert w.read_file64(0x4714100) == DISPATCH
    assert struct.unpack('<QQ', APP.read(DISPATCH + KIND * 16, 16)) == (0x2c3e01c, 0)
    assert w.read_file64(0x4029600) == 0x271760c
    targets = {0x2c3d618, 0x2c3dbd0, 0x2c3dd34, 0x2c3de38, 0x2c3de98,
               0x2c3deec, 0x2c3e01c, 0x2c0d628, 0x2c0d570, 0x271760c}
    branches = direct_branches(im, targets)
    assert {v['pc'] for v in branches if v['target'] == '0x2c3d618'} == {
        '0x2c3dc70', '0x2c3ddc4', '0x2c3de6c', '0x2c3df8c', '0x2c3e054'}
    groups = {
        'table_dispatch_cases': [dispatch_to_factory(v) for v in (0, 1)],
        'typed_wrapper_cases': [typed_to_factory(v) for v in (0, 1)],
        'post_constructor_marshalling_cases': [factory_to_enqueue(v) for v in (False, True)],
        'off_queue_capture_cases': [off_queue_witness(im, rows, wide, v) for v in (0, 1)],
        'metadata_before_queue_cases': [metadata_before_queue()],
        'registry_lock_control_cases': [registry_lock_branch(v) for v in (0, 1)],
        'pool_lock_destination_cases': [pool_lock_destination(v) for v in (0, 1, KIND)],
        'queue_notification_cases': [queue_notify_destination()],
        'null_selected_task_cases': [null_task_branch()],
        'stop_thread_wait_cases': [stop_wait_destination()],
    }
    regions = [('typed_wrapper', 0x271760c, 0x2717638),
               ('two_task_dispatch', 0x2bd1940, 0x2bd1a30),
               ('common_admission', 0x2c0d628, 0x2c0d86c),
               ('list_node_allocation', 0x2c0d544, 0x2c0d570),
               ('whole_manager_stop', 0x2c0d570, 0x2c0d628),
               ('cache_capture_exit_and_factory_family', 0x2c3dbbc, 0x2c3e098),
               ('insert_before_helper', 0x2c1671c, 0x2c16768),
               ('thread_exit_wait_wrapper', 0x2f71e60, 0x2f71e64)]
    proof = {'status': 'PASS_ADMISSION_BOUNDARY_FRAGMENTS_NOT_REAL_QUIESCENCE',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256': qp.sha(APP.path), 'previous_manifest_sha256': qp.sha(previous),
        'bindings': {'kind': KIND, 'name': 'sequence_get_media_remain', 'pool': 0,
                     'member_dispatch_entry': hex(DISPATCH + KIND * 16), 'member_factory': '0x2c3e01c',
                     'typed_table_reference': '0x4029600', 'typed_wrapper': '0x271760c',
                     'typed_factory': '0x2c3de38', 'common_admission': '0x2c0d628'},
        'constructor_family': [
            {'entry': '0x2c3dbd0', 'capture_call': '0x2c3dc70', 'role': 'Find queued target, construct new object and insert before it; manager then pool locks in body.'},
            {'entry': '0x2c3dd34', 'capture_call': '0x2c3ddc4', 'role': 'Backward pending-list replacement; internal pool lock absent, caller contract unproven.'},
            {'entry': '0x2c3de38', 'capture_call': '0x2c3de6c', 'role': 'Construct then common admission with registry lock control1.'},
            {'entry': '0x2c3deec', 'capture_call': '0x2c3df8c', 'role': 'Pool-locked backward replacement, falling back to typed normal admission after unlock.'},
            {'entry': '0x2c3e01c', 'capture_call': '0x2c3e054', 'role': 'Member-table construct, optional dependency linkage, common admission with control0; outer dispatch holds manager lock.'}],
        'all_direct_branches_to_scoped_targets': branches,
        'inventory_scope': 'All executable PT_LOAD direct B/BL references to these fixed targets, plus confirmed original data references. Not complete indirect reachability, caller ownership or all-class admission coverage.',
        **groups,
        'static_regions': [{'name': n, 'start': hex(s), 'end_exclusive': hex(e),
                            'original_bytes_sha256': hashlib.sha256(APP.read(s, e-s)).hexdigest(),
                            'instructions': im.dump(s, e)} for n, s, e in regions],
        'findings': [
            'Normal factories capture settings before common admission; an existing marked cache may be outside the queue. Original single-pool predicate can accept this synthetic state.',
            'This is an observation-scope counterexample, not proof of an actual race; outer model ownership, producer lifetime and complete callers remain unverified.',
            'The member-table path is under an outer manager lock; the typed path acquires manager lock for registration and releases it before pool insertion. Internal control0 cannot be labeled unsynchronized without its caller contract.',
            'Admission wakes the pool-specific CV with notify_one; completed work wakes the separate manager wait CV with notify_all.',
            'A whole-manager stop path enqueues null selections and calls osal_wait_thread_exit over29 handles. It is application-lifecycle code, not a verified reversible patch-unload gate or recovery mechanism.',
            'Holding the manager mutex while demanding worker completion is not a standalone freeze strategy: the original worker needs that mutex for completion; the original condition wait releases/reacquires it. An admission barrier must persist separately across the wait.',
        ],
        'earlier_guest_marker_reused_for_capture_only': True,
        'no_native_outputs_or_return_values_stubbed': True,
        'native_allocator_token_mutex_list_hook_notify_worker_or_thread_exit_executed': False,
        'complete_admission_gate_or_live_quiescence_observer_implemented': False,
        'camera_interface_auth_driver_files_module_WBI_or_write': False,
        'new_remote_attempts': False, 'goal_complete': False, 'persistent_write_release': False}
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    summary = {'status': proof['status'], 'case_counts': {k: len(v) for k,v in groups.items()},
        'bounded_phase_cases': sum(len(v) for v in groups.values()), 'copied_pool_predicates': 3,
        'direct_constructor_sites': 5, 'marked_off_queue_pool_acceptance_witness': True,
        'actual_race_proven': False, 'complete_gate_or_safe_unload_verified': False,
        'whole_manager_stop_not_executed': True, 'goal_complete': False, 'persistent_write_release': False}
    qp.write_json(out/'admission-boundary-results.json', proof); qp.write_json(out/'summary.json', summary)
    qp.write_json(out/'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'inputs': hashes,
        'results_sha256': qp.sha(out/'admission-boundary-results.json'),
        'summary_sha256': qp.sha(out/'summary.json'), 'previous_manifest_sha256': qp.sha(previous),
        'volume_uuid': qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();qp.verify_volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try: run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        qp.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
