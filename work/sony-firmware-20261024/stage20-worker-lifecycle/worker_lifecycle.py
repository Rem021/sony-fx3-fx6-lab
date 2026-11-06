#!/usr/bin/env python3
"""Original sequence-worker publication and retirement boundary fragments.

Synthetic guest memory only. Independent phase preconditions are explicit;
no thread, lock, unlink/free, task, future-delivery, destructor or notify backend.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'stage19-queue-boundary'))
import queue_boundary as q

APP, pp, qp, reg = q.APP, q.pp, q.qp, q.reg
SCRATCH, MANAGER, POOL, OLD, FP = q.SCRATCH, q.MANAGER, q.POOL, q.OLD, q.FP
ARGS = MANAGER + 0x310
CALLBACK = 0x2bd77b8
TOKEN = (q.KIND << 32) | 7


def read64(uc, address): return int.from_bytes(uc.mem_read(address, 8), 'little')


def putregs(m, **values):
    for name, value in values.items():
        m.uc.reg_write(getattr(reg, 'UC_ARM64_REG_' + name.upper()), value)


def task_fixture(m, marker=2):
    m.uc.mem_write(OLD, q.object_bytes(q.KIND, TOKEN, marker))


def observe_pool(source, exempt=()):
    """Copy a fragment's scratch bytes; run the original predicate read-only.

    This is a separate guest with an assumed-held pool lock, not a concurrent
    observer, live lock acquisition, full wait or admission freeze.
    """
    m = q.BoundaryMicro(APP, [(0x2c02550, 0x2c02748), (0x2c02470, 0x2c024d8)],
                        boundaries={0x2c0260c: 'pool_accepted', 0x2c02684: 'would_wait_after_unlock'})
    raw = bytes(source.uc.mem_read(SCRATCH, 0x10000))
    m.uc.mem_write(SCRATCH, raw)
    q.make_set(m.uc, exempt)
    putregs(m, x19=POOL, x20=0x3931051, x21=0, x22=MANAGER, x23=q.SET,
            x24=FP + 0x74, x25=FP + 0x78, x26=MANAGER + 0x2bc0,
            x28=0x186a0, x29=FP)
    before = bytes(m.uc.mem_read(SCRATCH, 0x10000))
    result = m.run(0x2c02550)
    assert bytes(m.uc.mem_read(SCRATCH, 0x10000)) == before
    reason = result['reason']
    assert reason in ('phase boundary: pool_accepted', 'phase boundary: would_wait_after_unlock')
    result.update(predicate='accepted' if reason.endswith('pool_accepted') else 'would_wait',
                  membership_exemptions=list(exempt), scratch_unchanged=True,
                  current_pointer=hex(read64(source.uc, POOL + 0x78)),
                  queue_count=read64(source.uc, POOL + 0x10),
                  scope='Separate copied synthetic phase; assumed-held pool lock. Not a live observation or whole wait.')
    return result


def startup_arguments(pool_index):
    m = q.BoundaryMicro(APP, [(0x2bd17d8, 0x2bd17f8)], end=0x2bd17f8)
    cell = ARGS + pool_index * 0x90
    m.uc.mem_write(cell + 0x88, q.p64(OLD))
    putregs(m, x19=cell, x20=pool_index, x21=CALLBACK, x22=MANAGER)
    r = m.run(0x2bd17d8)
    assert r['reason'] == 'conversion block complete'
    assert read64(m.uc, cell) == MANAGER
    assert q.cr.a.read32(m.uc, cell + 8) == pool_index
    assert read64(m.uc, cell + 0x88) == 0
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == CALLBACK
    assert m.uc.reg_read(reg.UC_ARM64_REG_X1) == cell
    assert m.uc.reg_read(reg.UC_ARM64_REG_X2) == pool_index + 4
    r.update(pool_index=pool_index, argument_cell=hex(cell),
             current_slot=hex(cell + 0x88), pool_relative_current_slot='0x78',
             callback=hex(CALLBACK), thread_id_enum=pool_index + 4,
             native_create_thread_invoked=False)
    return r


def callback_arguments(pool_index):
    m = q.BoundaryMicro(APP, [(CALLBACK, CALLBACK + 12)],
                        boundaries={0x2bd7604: 'worker_entry_before_prologue'})
    cell = ARGS + pool_index * 0x90
    m.uc.mem_write(cell, q.p64(MANAGER))
    r = m.run(CALLBACK, [cell])
    assert r['reason'] == 'phase boundary: worker_entry_before_prologue'
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == MANAGER
    assert m.uc.reg_read(reg.UC_ARM64_REG_X1) == cell
    assert not r['stores']
    r.update(pool_index=pool_index, native_thread_created_or_running=False)
    return r


def dequeue_selection(count):
    m = q.BoundaryMicro(APP, [(0x2bd7688, 0x2bd76a0)], end=0x2bd76a0)
    q.seed_pool(m.uc, None, (q.KIND,) + tuple(q.KIND + i + 1 for i in range(count - 1)))
    head = read64(m.uc, POOL)
    obj = read64(m.uc, head + 0x10)
    putregs(m, x19=ARGS)
    r = m.run(0x2bd7688)
    assert r['reason'] == 'conversion block complete'
    assert read64(m.uc, POOL + 0x10) == count - 1
    assert m.uc.reg_read(reg.UC_ARM64_REG_X20) == obj
    assert read64(m.uc, POOL) == head and read64(m.uc, POOL + 0x78) == 0
    r.update(queue_count_before=count, queue_count_after=count - 1,
             selected_object=hex(obj), list_unlink_or_node_free_executed=False,
             current_not_yet_published=True,
             scope='Selection/count update while pool lock is assumed held; stops before original list unlink. Intermediate graph is not a wait input.')
    return r


def publish(marker):
    m = q.BoundaryMicro(APP, [(0x2bd76bc, 0x2bd76cc)])
    q.seed_pool(m.uc, None, ()); task_fixture(m, marker)
    putregs(m, x19=ARGS, x20=OLD, x22=FP + 0x70)
    r = m.run(0x2bd76bc)
    assert r['reason'] == 'unapproved execution 1724ccc'
    assert read64(m.uc, POOL + 0x78) == OLD
    assert q.cr.a.read32(m.uc, OLD + 0x388) == marker
    observations = [observe_pool(m, exempt) for exempt in ((), (q.KIND,))]
    assert [v['predicate'] for v in observations] == ['would_wait', 'accepted']
    r.update(marker_fixture=marker, current_pointer_after=hex(OLD),
             observer_cases=observations, original_pool_unlock_executed=False,
             precondition='Fresh independent fixture assumes successful dequeue, original node unlink/free, retained object X20 and held pool lock. Those earlier operations are not executed here.')
    return r


def dispatch(marker, deleting=False):
    start, end, target = ((0x2bd7758, 0x2bd7768, 0x2bb03a4) if deleting
                          else (0x2bd76ec, 0x2bd76fc, 0x2baf850))
    m = q.BoundaryMicro(APP, [(start, end)],
                        boundaries={target: 'original_deleting_destructor_entry' if deleting else 'original_media_remain_run_entry'})
    q.seed_pool(m.uc, q.KIND, ()); task_fixture(m, marker)
    raw = bytes(m.uc.mem_read(OLD, 0x4d8))
    putregs(m, x19=ARGS, x20=OLD)
    r = m.run(start)
    assert r['reason'].startswith('phase boundary: original_')
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == OLD
    assert m.uc.reg_read(reg.UC_ARM64_REG_LR) == end
    assert bytes(m.uc.mem_read(OLD, 0x4d8)) == raw and not r['stores']
    assert read64(m.uc, POOL + 0x78) == OLD
    r.update(marker_fixture=marker, original_virtual_target=hex(target),
             vtable_offset='0x8' if deleting else '0x10',
             current_still_published=True, task_or_destructor_body_executed=False,
             observer=observe_pool(m),
             precondition='Independent phase fixture, not execution of intervening native helpers or the complete worker.')
    assert r['observer']['predicate'] == 'would_wait'
    return r


def result_cleanup(registry):
    m = q.BoundaryMicro(APP, [(0x2bd7728, 0x2bd7758), (0x2bd77b0, 0x2bd77b8)])
    q.seed_pool(m.uc, q.KIND, ()); task_fixture(m)
    sentinel, node = MANAGER + 0x2c60, SCRATCH + 0x9800
    m.uc.mem_write(sentinel, struct.pack('<QQQ', sentinel, sentinel, 0))
    if registry != 'empty':
        m.uc.mem_write(sentinel, struct.pack('<QQQ', node, node, 1))
        m.uc.mem_write(node, struct.pack('<QQQQ', sentinel, sentinel, 0,
                                        TOKEN if registry == 'matching_token' else TOKEN + 1))
    putregs(m, x19=ARGS, x20=OLD, x21=MANAGER)
    r = m.run(0x2bd7728)
    expected = 'unapproved execution ' + ('2bd75c4' if registry == 'matching_token' else '2bd1ecc')
    assert r['reason'] == expected and read64(m.uc, POOL + 0x78) == OLD
    assert not r['stores']
    r.update(registry_fixture=registry, current_still_published=True,
             result_delivery_registry_removal_or_deletion_executed=False,
             observer=observe_pool(m),
             precondition='Assume task body and timing hooks returned and both manager/pool locks acquired; none of those operations are executed.')
    assert r['observer']['predicate'] == 'would_wait'
    return r


def clear_after_delete(queued):
    m = q.BoundaryMicro(APP, [(0x2bd7768, 0x2bd7770)], end=0x2bd7770)
    q.seed_pool(m.uc, q.KIND, tuple(q.KIND + 1 + i for i in range(queued)))
    # The old object's lifetime has ended in this explicit precondition. Poison
    # its still-mapped guest bytes; the original slice must not dereference it.
    m.uc.mem_write(OLD, bytes([0xa5]) * 0x4d8)
    putregs(m, x19=ARGS, x20=OLD, x22=FP + 0x70)
    r = m.run(0x2bd7768)
    assert r['reason'] == 'conversion block complete'
    assert read64(m.uc, POOL + 0x78) == 0
    assert bytes(m.uc.mem_read(OLD, 0x4d8)) == bytes([0xa5]) * 0x4d8
    assert len(r['stores']) == 1 and r['stores'][0]['address'] == hex(POOL + 0x78)
    r.update(queued_count_fixture=queued, current_pointer_after='0x0',
             old_bytes_poisoned_and_untouched=True, observer=observe_pool(m),
             native_unlock_notify_or_actual_delete_executed=False,
             precondition='Independent post-return slice assumes successful result delivery and deleting destructor returned under both locks. No such success is manufactured by a stub; the earlier bodies are excluded.')
    assert r['observer']['predicate'] == ('accepted' if queued == 0 else 'would_wait')
    return r


def notify_destination():
    m = q.BoundaryMicro(APP, [(0x2bd777c, 0x2bd7788)])
    putregs(m, x21=MANAGER)
    r = m.run(0x2bd777c)
    assert r['reason'].startswith('unapproved PLT ')
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == MANAGER + 0x2bc0
    assert not r['stores']
    r.update(condition_variable_address=hex(MANAGER + 0x2bc0),
             original_plt_symbol=APP.plt[0x1592120], native_notify_executed=False,
             precondition='Independent argument slice assumes both original unlock helpers returned; their bodies are excluded.')
    return r


def run(out):
    sources = [APP.path, q.cr.MPR.path, Path(q.__file__), Path(q.cr.__file__),
               Path(pp.__file__), Path(qp.__file__), Path(q.cr.ss.__file__),
               BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    prior_path = BASE / 'stage19-queue-boundary/final-receipt.json'
    prior = json.loads(prior_path.read_text())
    assert all(qp.sha(ROOT / f['path']) == f['sha256'] for f in prior['files'])
    im = q.cr.ss.StaticImage()
    assert read_file64(0x47a9c38) == CALLBACK
    assert read_file64(q.VIRTUAL_TABLE + 0x10) == 0x2baf850
    assert read_file64(q.VIRTUAL_TABLE + 8) == 0x2bb03a4
    assert APP.read(0x3d08bb8, 120).split(b'\0')[0] == b'void* lib::create_thread(lib::entry_function_t, void*, lib::thread_id_t)'
    groups = {
        'startup_argument_cases': [startup_arguments(n) for n in (0, 1, 28)],
        'callback_argument_cases': [callback_arguments(n) for n in (0, 28)],
        'dequeue_selection_cases': [dequeue_selection(n) for n in (1, 2, 7)],
        'publication_cases': [publish(n) for n in (0, 2)],
        'run_dispatch_cases': [dispatch(n) for n in (0, 2)],
        'result_cleanup_cases': [result_cleanup(v) for v in ('empty', 'other_token', 'matching_token')],
        'destructor_dispatch_cases': [dispatch(n, deleting=True) for n in (0, 2)],
        'current_clear_cases': [clear_after_delete(n) for n in (0, 1, 3)],
        'notify_argument_cases': [notify_destination()],
    }
    full = q.BoundaryMicro(APP, [(0x2bd7604, 0x2bd77c4)])
    full.uc.mem_write(ARGS, q.p64(MANAGER))
    full_stop = full.run(CALLBACK, [ARGS])
    assert full_stop['reason'] == 'unapproved execution 16ed554'
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    regions = [
        ('static_manager_initializer', 0x168f6dc, 0x168f71c),
        ('manager_constructor_pool_loop', 0x2d03fa0, 0x2d0402c),
        ('manager_thread_startup', 0x2bd17a4, 0x2bd181c),
        ('original_sequence_worker', 0x2bd7604, 0x2bd77c4),
        ('original_result_delivery_not_executed', 0x2bd1ecc, 0x2bd202c),
        ('original_registry_removal_not_executed', 0x2bd75c4, 0x2bd7604),
        ('optional_pre_run_dependencies_not_executed', 0x2b49430, 0x2b49528),
        ('original_pool_unlock_not_executed', 0x1724ccc, 0x1724cf0),
        ('original_guard_unlock_not_executed', 0x273879c, 0x27387b4),
        ('original_create_thread_not_executed', 0x2f71d6c, 0x2f71e60),
        ('media_remain_destructor_not_executed', 0x2bb0390, 0x2bb03cc),
    ]
    proof = {
        'status': 'PASS_ORIGINAL_WORKER_PHASE_FRAGMENTS_ONLY',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256': qp.sha(APP.path), 'prior_manifest_sha256': qp.sha(prior_path),
        'bindings': {'internal_task_kind': q.KIND, 'internal_task_name': 'sequence_get_media_remain',
            'pool_index': 0, 'global_manager': '0x9680760', 'pool_stride': '0x90',
            'pool_base_from_manager': '0x320', 'worker_argument_from_manager': '0x310 + pool*0x90',
            'pool_current_pointer': 'pool+0x78 == worker_argument+0x88',
            'callback_got': '0x47a9c38', 'callback': hex(CALLBACK), 'worker': '0x2bd7604',
            'run_vtable_target': '0x2baf850', 'deleting_destructor_target': '0x2bb03a4',
            'notify_all_destination': 'manager+0x2bc0'},
        **groups, 'full_worker_native_mutex_stop': full_stop,
        'static_regions': [{'name': name, 'start': hex(start), 'end_exclusive': hex(end),
                            'original_bytes_sha256': __import__('hashlib').sha256(APP.read(start, end-start)).hexdigest(),
                            'instructions': im.dump(start, end)} for name, start, end in regions],
        'findings': [
            'The previously independent slot is statically bound to the real sequence worker: publication precedes task run; deleting destructor and result delivery precede clearing.',
            'The worker decrements queue count before publishing the selected object while it still holds the pool lock. A raw unlocked queue/current sample can observe an intermediate state.',
            'Returning from the task body is not retirement. Matching-token registry cleanup, future-related result delivery and deleting destructor lie before the current slot is cleared.',
            'Original notify_all is after slot clearing and both unlock helper calls, then the worker loops. It neither terminates the thread nor freezes new admission.',
            'The copied-phase original wait predicate still accepts a published task when its kind is exempted; empty exemption waits. Current cleared with pending queue still waits.',
        ],
        'scope': 'Original instruction fragments on independent synthetic phase fixtures. Not a continuous worker execution, real lock, native task, future delivery, destructor, notify, safe unload, loader, recovery or device acceptance.',
        'phase_gaps_have_no_output_stubs': True,
        'native_task_thread_mutex_wait_free_destructor_or_notify_executed': False,
        'actual_live_quiescence_observer_or_admission_gate_implemented': False,
        'camera_USB_driver_files_module_WBI_or_firmware_write': False,
        'firmware_payload_or_patchfile_exported': False,
        'goal_complete': False, 'persistent_write_release': False,
    }
    summary = {
        'status': proof['status'], 'case_counts': {k: len(v) for k, v in groups.items()},
        'original_phase_cases': sum(len(v) for v in groups.values()),
        'copied_phase_predicate_cases': 14,
        'full_worker_negative_cases': 1,
        'current_slot_bound_to_original_worker': True,
        'task_return_or_notification_equals_thread_join': False,
        'full_native_wait_or_safe_unload_verified': False,
        'goal_complete': False, 'persistent_write_release': False,
    }
    assert sum(len(v.get('observer_cases', [])) + int('observer' in v)
               for values in groups.values() for v in values) == summary['copied_phase_predicate_cases']
    qp.write_json(out / 'worker-lifecycle-results.json', proof)
    qp.write_json(out / 'summary.json', summary)
    qp.write_json(out / 'source-receipt.json', {
        'script': str(Path(__file__).relative_to(ROOT)), 'script_sha256': qp.sha(Path(__file__)),
        'results_sha256': qp.sha(out / 'worker-lifecycle-results.json'),
        'summary_sha256': qp.sha(out / 'summary.json'), 'inputs': hashes,
        'previous_manifest': str(prior_path.relative_to(ROOT)), 'previous_manifest_sha256': qp.sha(prior_path),
        'volume_uuid': qp.EXPECTED_VOLUME,
    })
    print(json.dumps(summary, ensure_ascii=False))


def read_file64(address): return int.from_bytes(APP.read(address, 8), 'little')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    qp.verify_volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    try:
        run(out)
    except Exception:
        with (out / 'attempt-source.py').open('xb') as f: f.write(Path(__file__).read_bytes())
        qp.write_json(out / 'attempt-failure.json', {'traceback': traceback.format_exc(),
                      'scope': 'Failed offline phase attempt preserved; not a passing result.'})
        raise


if __name__ == '__main__': main()
