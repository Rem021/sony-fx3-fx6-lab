#!/usr/bin/env python3
"""Static named model_lock scope and a fail-closed mutex dependency probe."""
from pathlib import Path
import argparse
import json
import struct
import captured_profile as cp


def dependency_stop(entry, end):
    # Synthetic runtime pointer makes the original weak thread-support test
    # take its pthread path. No pthread call is implemented or forwarded.
    m = cp.pp.StrictMicro(cp.APP, [(entry, end), (0x1724c98, 0x1724ccc), (0x16ed554, 0x16ed580)])
    m.uc.mem_write(0x4797428, struct.pack('<Q', 1))
    result = m.run(entry)
    assert result['reason'] == 'unapproved PLT pthread_mutex_lock'
    result.update(synthetic_runtime_thread_pointer=1,
                  pthread_mutex_or_thread_ID_executed_or_stubbed=False,
                  real_model_ownership_acquired=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cp.qp.verify_volume()
    out = Path(args.output).resolve()
    assert cp.STAGE in out.parents and not out.exists()
    out.mkdir()
    inputs = [cp.APP.path, Path(cp.__file__), Path(cp.ss.__file__), Path(cp.pp.__file__), Path(cp.qp.__file__),
              cp.BASE / 'stage14-model-lifecycle/model_lifecycle.py',
              cp.BASE / 'stage10-mainpath/main/audit_main_path.py']
    before = {str(p.relative_to(cp.ROOT)): cp.qp.sha(p) for p in inputs}
    im = cp.ss.StaticImage()
    name = lambda va: cp.APP.read(va, 200).split(b'\0')[0].decode('ascii')
    assert name(0x3801ea0) == 'model_mutex.cpp'
    assert name(0x3801eb0) == 'model::model_lock::model_lock()'
    assert name(0x3801ed0) == 'model::model_lock::~model_lock()'
    assert cp.APP.plt[0x1592d30] == '_ZNSt18condition_variable4waitERSt11unique_lockISt5mutexE'
    assert cp.APP.plt[0x1593f80] == '_ZNSt18condition_variable10notify_oneEv'
    assert cp.APP.plt[0x1594550] == 'pthread_self'
    field = cp.ss.lifecycle.registry_row(0x3f3)
    assert field['name'] == 'setting_sq_proxy_recording'
    assert cp.pp.Image().leaf(0x2935aac) == 0x831a87c
    assertions = {0x27cb6ec: 'bl #0x2aa1ea8', 0x27cbbac: 'bl #0x2dda7d4',
        0x27cbcd8: 'b #0x27cb760', 0x27cb764: 'bl #0x2aa1ab4',
        0x2c5b5c4: 'bl #0x2aa1ea8', 0x2c5b5d0: 'bl #0x2beea04', 0x2c5b5d8: 'bl #0x2aa1ab4',
        0x2beecb0: 'b #0x2beae8c',
        0x27cbb40: 'bl #0x2935aac', 0x27cbb48: 'str w0, [x29, #0x338]',
        0x27ccab8: 'bl #0x2935aac', 0x27ccad8: 'mov w1, #0x3f3', 0x27ccae0: 'bl #0x2f6e7ac',
        0x2aa2178: 'str x0, [x21, #0xce8]', 0x2aa1fe4: 'str w0, [x20, #0x30]',
        0x2aa1b08: 'str w0, [x25, #0x30]', 0x2aa1c04: 'str xzr, [x20, #0xce8]'}
    for pc, text in assertions.items(): assert im.dump(pc, pc + 4)[0]['asm'] == text
    regions = [('model_lock_constructor', 0x2aa1ea8, 0x2aa2180),
               ('model_lock_destructor', 0x2aa1ab4, 0x2aa1c0c),
               ('thread_identity', 0x2aa1620, 0x2aa1648),
               ('unique_lock_constructor_destructor', 0x1724c98, 0x1724cf0),
               ('live_status_producer', 0x27cb6c8, 0x27cbcfc),
               ('main_builder_constructor_model_scope', 0x2c5b590, 0x2c5b5e0),
               ('builder_tail', 0x2beec98, 0x2beecb4),
               ('local_input138_proxy_binding', 0x27ccab8, 0x27ccb0c),
               ('cached_remain_copy_not_patched', 0x2bafa6c, 0x2bafd20)]
    dependencies = [dependency_stop(0x2aa1ea8, 0x2aa2180), dependency_stop(0x2aa1ab4, 0x2aa1c0c)]
    assert before == {str(p.relative_to(cp.ROOT)): cp.qp.sha(p) for p in inputs}
    proof = {'status': 'PASS_NAMED_MODEL_OWNER_SCOPE_WITH_NATIVE_MUTEX_DEPENDENCY_STOPS',
        'scope': 'Static normal-path ownership logic and guarded synthetic entry stops, not actual threads or full scope execution',
        'inputs_unchanged': before,
        'names': {'0x3801ea0': name(0x3801ea0), '0x3801eb0': name(0x3801eb0), '0x3801ed0': name(0x3801ed0)},
        'owner_state': {'owner_thread_global': '0x8e29ce8', 'per_thread_nesting_offset': '0x30',
            'bookkeeping_mutex': '0x8e29cf0', 'native_thread_support_pointer': '0x4797428',
            'constructor': 'Free owner requires count0, records current thread and increments nesting. Same owner requires positive count and increments. Other owner queues and waits.',
            'destructor': 'Decrements nesting, verifies owner; at outermost release transfers owner and notifies waiter or clears owner.',
            'physical_mutex_vs_logical_owner': 'The short native mutex is released before the helper returns, while logical ownership persists until matching model_lock destruction.'},
        'caller_scope': {'live_status': 'Constructor0x27cb6ec precedes79getter copies and query wrapper0x27cbbac; normal result handling branches0x27cbcd8 to destructor0x27cb764.',
            'main_builder': '0x2c5b5c4 enter,0x2c5b5d0 construct/tail to original builder,0x2c5b5d8 exit.',
            'runtime_writer_and_all_consumers_participating': False},
        'input138_binding': {'packet_base': 'producerFP+0x200', 'store': 'producerFP+0x338',
            'getter': '0x2935aac', 'global_cell': '0x831a87c', 'key': field,
            'meaning': 'setting_sq_proxy_recording', 'not_NTSC_or_progressive_field': True},
        'static_regions': [{'name': name, 'start': hex(start), 'end': hex(end), 'instructions': im.dump(start, end)}
                           for name, start, end in regions],
        'actual_wrapper_call_references': im.calls({0x2dda7d4, 0x2dda854, 0x2beea04}),
        'native_mutex_dependency_stops': dependencies,
        'open_consumers': ['Captured local marker is implemented only at the live status producer. The actual cached remain producer and its cache-generation identity are not yet integrated.',
                           'Main setter uses self-contained target tuple, but full loading, calling ABI and lifecycle remain unverified.',
                           'Profile writer must participate in real model ownership; independent capture epochs and recording-idle admission still need enforcement.',
                           'Name binding of NTSC/PAL numeric values, UI, persistence/WBI and scoped restoration remain unclosed.'],
        'camera_or_native_mutex_actions': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'named_model_lock_located': True,
        'live_status_and_main_builder_model_scope_static_only': True,
        'input138_name': field['name'], 'native_mutex_dependency_stops': len(dependencies),
        'cached_remain_profile_propagation_implemented': False,
        'real_threads_owner_or_record_idle_gate_verified': False, 'goal_complete': False}
    cp.qp.write_json(out / 'model-owner-results.json', proof)
    cp.qp.write_json(out / 'summary.json', summary)
    cp.qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(cp.ROOT)),
        'script_sha256': cp.qp.sha(Path(__file__)), 'results_sha256': cp.qp.sha(out / 'model-owner-results.json'),
        'summary_sha256': cp.qp.sha(out / 'summary.json'), 'inputs': before, 'volume_uuid': cp.qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
