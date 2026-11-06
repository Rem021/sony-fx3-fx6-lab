#!/usr/bin/env python3
"""Bind the correct cache class and compare capture epochs, device-free."""
from pathlib import Path
import argparse
import json
import struct
import cached_remain as cr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cr.qp.verify_volume()
    out = Path(args.output).resolve()
    assert cr.STAGE in out.parents and not out.exists()
    out.mkdir()
    sources = [cr.APP.path, cr.MPR.path, Path(cr.__file__), Path(cr.cp.__file__), Path(cr.pp.__file__),
               Path(cr.qp.__file__), Path(cr.a.__file__), Path(cr.ss.__file__),
               cr.BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes = {str(p.relative_to(cr.ROOT)): cr.qp.sha(p) for p in sources}
    im = cr.pp.Image(); static = cr.ss.StaticImage()
    wanted = {0x47827d8: 0x46e7ff0, 0x46e8010: 0x2baf850}
    relocs = {}
    for sec in static.elf.iter_sections():
        if sec['sh_type'] == 'SHT_RELA':
            for r in sec.iter_relocations():
                if r['r_info_type'] == 1027 and r['r_offset'] in wanted:
                    relocs[r['r_offset']] = r['r_addend']
    assert relocs == wanted
    assert struct.unpack('<Q', cr.APP.read(0x46e7ff8, 8))[0] == 0x46e7fd8
    assert struct.unpack('<Q', cr.APP.read(0x46e7fe0, 8))[0] == 0x3928f50
    name = cr.APP.read(0x3928f50, 80).split(b'\0')[0].decode()
    assert name == 'N5model25sequence_get_media_remainE'
    expected = {0x2c3d63c: 'ldr x0, [x0, #0x7d8]', 0x2c3d640: 'add x0, x0, #0x10',
                0x2c3d644: 'str x0, [x19]', 0x2c3d654: 'bl #0x2aa1ea8',
                0x2c3dbbc: 'bl #0x2aa1ab4', 0x2bb03c4: 'mov x1, #0x4d8',
                0x2bafa8c: 'ldr w0, [x19, #0x388]', 0x2bafa90: 'str w0, [x29, #0xc8]',
                0x2bafd1c: 'bl #0x2dda854', 0x2e6a960: 'bl #0x1594430'}
    for pc, text in expected.items(): assert static.dump(pc, pc + 4)[0]['asm'] == text
    marker = cr.cache_marker(im); rows, wide = cr.cache_rows(im)
    qpatch, _ = cr.qp.new_patch(); live_marker = cr.cp.capture_patch(im)
    live_rows = cr.cp.model_copy_rows(im); setter_patch = cr.pp.trampolines(im)[1]
    builder_patches = cr.a.patches(im)
    joined = []
    for captured in (0, 1):
        for future in (0, 1):
            builder = cr.a.builder(im, builder_patches, frame=0, flag=captured)
            setter = cr.cp.tuple_setter(im, setter_patch, builder['builder_tuple'], future_flag=future)
            live_capture, live_blob = cr.cp.copy_packet(im, live_rows, live_marker, {'frame': 0}, flag=captured)
            live_query = cr.cp.captured_query(live_blob, qpatch, future_flag=future)
            capture, cache = cr.capture(im, rows, wide, marker, {'frame': 0}, flag=captured)
            copied, blob = cr.copy_to_call(cache, future_flag=future)
            remain = cr.prepare_remain(cache, blob, qpatch, future_flag=future)
            assert setter['output_vpc_quality_frame'] == live_query['output_vpc_quality_frame'] == remain['output_vpc_quality_frame']
            joined.append({'independent_objects_given_same_capture_flag': captured,
                           'future_flag': future, 'builder': builder, 'setter': setter,
                           'live_capture': live_capture, 'live_query': live_query,
                           'cache_capture': capture, 'cache_copy': copied, 'remain_preparation': remain,
                           'one_actual_atomic_transaction_executed': False})
    different = []
    for main_capture, cache_capture in ((0, 1), (1, 0)):
        builder = cr.a.builder(im, builder_patches, frame=0, flag=main_capture)
        setter = cr.cp.tuple_setter(im, setter_patch, builder['builder_tuple'], future_flag=0)
        captured, cache = cr.capture(im, rows, wide, marker, {'frame': 0}, flag=cache_capture)
        copied, blob = cr.copy_to_call(cache)
        remain = cr.prepare_remain(cache, blob, qpatch)
        assert setter['output_vpc_quality_frame'] != remain['output_vpc_quality_frame']
        different.append({'main_capture_flag': main_capture, 'cache_capture_flag': cache_capture,
                          'setter': setter, 'capture': captured, 'copy': copied, 'remain': remain,
                          'interpretation': 'Different captured identities; cannot claim they describe the same recording configuration without epoch/intent policy.'})
    captured, old_cache = cr.capture(im, rows, wide, marker, {'frame': 0}, flag=1)
    copied, old_blob = cr.copy_to_call(old_cache, future_flag=0)
    removed = cr.prepare_remain(old_cache, old_blob, None)
    regenerated, stock_cache = cr.capture(im, rows, wide, marker, {'frame': 0}, flag=0)
    stock_copy, stock_blob = cr.copy_to_call(stock_cache)
    stock = cr.prepare_remain(stock_cache, stock_blob, None)
    assert removed['reason'].startswith('firmware assertion entry reached')
    assert stock['reason'] == 'conversion block complete'
    assert hashes == {str(p.relative_to(cr.ROOT)): cr.qp.sha(p) for p in sources}
    proof = {'status': 'PASS_CACHE_TYPE_AND_CAPTURE_IDENTITY_BOUNDARY', 'inputs_unchanged': hashes,
        'class_binding': {'type_name': name, 'relative_relocations': {hex(k): hex(v) for k, v in relocs.items()},
            'vtable_typeinfo_pointer': '0x46e7fd8', 'typeinfo_name_pointer': '0x3928f50',
            'vtable_run_pointer': '0x2baf850', 'constructor_vptr_GOT': '0x47827d8',
            'deleting_destructor_size': '0x4d8'},
        'constructor_direct_call_references': static.calls({0x2c3d618}),
        'same_capture_fixture_joined_consumers': joined,
        'different_capture_identity_controls': different,
        'cache_consumer_removal': {'old_capture': captured, 'old_copy': copied, 'removed_consumer': removed,
            'regenerated_capture': regenerated, 'regenerated_copy': stock_copy, 'stock_consumer': stock},
        'scope': 'Class binding and independently constructed guest fixtures; not same-thread atomic publication, actual cache invalidation, real scheduling, MPR calculation or device.',
        'finding': 'Main setter, live query and cached remain preparation can share the target identity without late flag reads, but actual generation/intent policy must prevent incompatible queued snapshots when they are required to describe one recording configuration.',
        'invalidation_observer_or_queue_drain_implemented': False,
        'camera_or_actual_remaining_time_or_restore_actions': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'RTTI_vtable_constructor_run_binding_verified': True,
               'same_capture_joined_fixtures': len(joined), 'different_capture_identity_controls': len(different),
               'old_cache_stock_consumer': removed['reason'], 'regenerated_cache_stock_consumer': stock['reason'],
               'real_atomic_epoch_cache_invalidation_or_recovery_verified': False, 'goal_complete': False}
    cr.qp.write_json(out / 'cache-boundary-results.json', proof)
    cr.qp.write_json(out / 'summary.json', summary)
    cr.qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(cr.ROOT)),
        'script_sha256': cr.qp.sha(Path(__file__)), 'results_sha256': cr.qp.sha(out / 'cache-boundary-results.json'),
        'summary_sha256': cr.qp.sha(out / 'summary.json'), 'inputs': hashes, 'volume_uuid': cr.qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
