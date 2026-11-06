#!/usr/bin/env python3
"""Guest-only cache capture -> original copy -> GetMovieRemain preparation.

Stops BEFORE the external MPR API. No actual time calculation, filesystem,
media/free-space query, mutex/thread execution, native loader or camera action.
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
sys.path[:0] = [str(BASE / 'stage17-captured-profile')]
import captured_profile as cp

pp, qp, a, ss = cp.pp, cp.qp, cp.a, cp.ss
APP, MPR, reg = cp.APP, cp.MPR, cp.reg
SCRATCH, STACK, FP = cp.SCRATCH, cp.STACK, cp.FP
CACHE = SCRATCH + 0xa000
CACHE_SIZE = 0x4d8
CAPTURE_START, CAPTURE_SITE, CAPTURE_END = 0x2c3d78c, 0x2c3dbb8, 0x2c3dbbc
CAPTURE_CODE = pp.CODE + 0xe00
COPY_START, COPY_END = 0x2bafa6c, 0x2bafd1c
COPY_PACKET = FP + 0xb0
PREP_START, PREP_CALL = 0x2e6a5e0, 0x2e6a960


def cache_marker(im):
    assert im.read(CAPTURE_SITE, 4).hex() == 'e00314aa'  # mov x0,x20
    p = pp.Asm(CAPTURE_CODE)
    for w in a.SAVE: p.emit(w)
    a.load_flag(p); p.cmp(0, 1); p.branch('stock', cond=1)
    p.ldr(0, 19, 0x380); p.cmp(0, 6); p.branch('stock', cond=1)
    p.ldr(0, 19, 0x37c); p.cmp(0, 16); p.branch('stock', cond=8)
    p.branch(qp.MOVIE_PREDICATE, link=True)
    p.cmp(0, 0); p.branch('stock', cond=0)
    p.ldr(0, 19, 0x388)
    for allowed in (0, 1, 4, 5, 6):
        p.cmp(0, allowed); p.branch('mark', cond=0)
    p.branch('stock')
    p.label('mark'); p.mov(0, 2); p.str(0, 19, 0x388)
    p.label('stock')
    for w in a.RESTORE: p.emit(w)
    p.emit(struct.unpack('<I', im.read(CAPTURE_SITE, 4))[0])
    p.branch(CAPTURE_SITE + 4)
    raw = p.finish()
    assert CAPTURE_CODE + len(raw) <= pp.CODE + 4096
    return (CAPTURE_SITE, CAPTURE_CODE, raw)


def cache_rows(im):
    ins = list(im.md.disasm(im.read(CAPTURE_START, CAPTURE_END - CAPTURE_START), CAPTURE_START))
    scalar, wide = [], []
    for i, op in enumerate(ins):
        if op.mnemonic != 'bl': continue
        getter = int(op.op_str.split('#')[1], 16)
        cell = im.leaf(getter)
        assert cell is not None
        following = ins[i + 1]
        if getter == 0x29464b8:
            assert following.mnemonic == 'ldp' and following.op_str == 'x2, x3, [x0]'
            wide.append({'getter': getter, 'model_cell': cell, 'cache_offset': 0x4b8, 'bytes': 19})
            continue
        assert following.mnemonic == 'ldr' and following.op_str == 'w0, [x0]'
        store = None
        for candidate in ins[i + 2:i + 7]:
            if candidate.mnemonic == 'str' and candidate.op_str.startswith('w0, [x19, #'):
                store = candidate
                break
            assert candidate.mnemonic not in ('bl', 'blr', 'b', 'ret')
            _, writes = candidate.regs_access()
            assert not {'w0', 'x0'} & {candidate.reg_name(r) for r in writes}
        assert store is not None
        offset = int(store.op_str.split('#')[1].rstrip(']'), 16)
        scalar.append({'getter': getter, 'model_cell': cell, 'cache_offset': offset,
                       'call_pc': op.address, 'store_pc': store.address})
    assert len(wide) == 1 and len({r['cache_offset'] for r in scalar}) == len(scalar)
    assert next(r for r in scalar if r['cache_offset'] == 0x37c)['getter'] == 0x293d90c
    assert next(r for r in scalar if r['cache_offset'] == 0x388)['getter'] == pp.FRAMEGET
    assert next(r for r in scalar if r['cache_offset'] == 0x4a4)['getter'] == 0x2935aac
    return scalar, wide


def capture(im, rows, wide, patch, case, *, flag=0, proxy=0, tagged=False):
    getters = {r['getter'] for r in rows + wide}
    ranges = [(CAPTURE_START, CAPTURE_END), (qp.MOVIE_PREDICATE, 0x2a4e6e4),
              (0x2a4e794, 0x2a4e798)] + [(g, g + 20) for g in getters]
    m = cp.CopyMicro(APP, ranges, end=CAPTURE_END, patches=[patch] if patch else [], profile_flag=flag)
    values = {0x293d90c: case.get('mode', 5), 0x2934c9c: case.get('fmt', 6),
              pp.FRAMEGET: case['frame'], pp.Q60: case.get('q60', 12),
              pp.Q24: case.get('q24', 17), pp.Q120: case.get('q120', 9), 0x2935aac: proxy}
    seeded = {r['model_cell']: 0x10000000 + r['cache_offset'] if tagged else values.get(r['getter'], 0) for r in rows}
    for address, value in seeded.items(): m.uc.mem_write(address, pp.p32(value))
    wide_bytes = bytes(range(0xb0, 0xb0 + 19)) if tagged else bytes(19)
    m.uc.mem_write(wide[0]['model_cell'], wide_bytes)
    # Excluded earlier constructor fields are a synthetic input precondition.
    initial = bytearray(b'\x5a' * CACHE_SIZE)
    struct.pack_into('<I', initial, 0x1bc, 0)
    initial[0x1c0:0x310] = bytes(0x150)
    m.uc.mem_write(CACHE, bytes(initial))
    for rr, value in [(reg.UC_ARM64_REG_X19, CACHE), (reg.UC_ARM64_REG_X20, FP + 0x38),
                      (reg.UC_ARM64_REG_X21, CACHE + 0x4b8), (reg.UC_ARM64_REG_X29, FP)]:
        m.uc.reg_write(rr, value)
    result = m.run(CAPTURE_START)
    assert result['reason'] == 'conversion block complete'
    assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK and m.uc.reg_read(reg.UC_ARM64_REG_X0) == FP + 0x38
    assert all(a.read32(m.uc, address) == value for address, value in seeded.items())
    assert bytes(m.uc.mem_read(wide[0]['model_cell'], 19)) == wide_bytes
    blob = bytes(m.uc.mem_read(CACHE, CACHE_SIZE))
    for row in rows:
        if patch and flag == 1 and row['cache_offset'] == 0x388 and not tagged: continue
        assert int.from_bytes(blob[row['cache_offset']:row['cache_offset'] + 4], 'little') == seeded[row['model_cell']]
    assert blob[0x4b8:0x4cb] == wide_bytes
    result.update(input_case=case, proxy_model_value=proxy, cache_blob_hex=blob.hex(),
                  cache_HS_frame=int.from_bytes(blob[0x388:0x38c], 'little'),
                  global_model_values_unchanged=True,
                  constructor_prefix_memcpy_model_lock_or_destructor_executed=False,
                  synthetic_preconditions='Existing0x4d8cache object, zero current-MPR metadata region and caller registers; original current getters execute')
    return result, blob


def copy_to_call(cache_blob, *, future_flag=0):
    m = cp.CopyMicro(APP, [(COPY_START, COPY_END)], end=COPY_END, profile_flag=future_flag)
    m.uc.mem_write(CACHE, cache_blob)
    m.uc.mem_write(COPY_PACKET, b'\xa5' * 0x160)
    for rr, value in [(reg.UC_ARM64_REG_X19, CACHE), (reg.UC_ARM64_REG_X25, COPY_PACKET),
                      (reg.UC_ARM64_REG_X26, FP + 0x78), (reg.UC_ARM64_REG_X27, CACHE + 0x1c0),
                      (reg.UC_ARM64_REG_X29, FP)]: m.uc.reg_write(rr, value)
    result = m.run(COPY_START)
    blob = bytes(m.uc.mem_read(COPY_PACKET, 0x160))
    assert result['reason'] == 'conversion block complete' and not result['private_flag_reads']
    assert bytes(m.uc.mem_read(CACHE, CACHE_SIZE)) == cache_blob
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == COPY_PACKET
    # Exact original copy correspondence, including all74scalar arguments.
    assert blob[0x10:0x138] == cache_blob[0x37c:0x4a4]
    assert blob[0x138:0x14c] == cache_blob[0x4a4:0x4b8]
    assert blob[0x14c:0x15f] == cache_blob[0x4b8:0x4cb]
    result.update(call_input_hex=blob.hex(), cache_unchanged=True,
                  original_copy_only=True, full_sequence_or_wrapper_executed=False)
    return result, blob


def prepare_remain(cache_blob, input_blob, query_patch, *, future_flag=0, enabled_helpers=True):
    ranges = list(qp.RANGES) + [(PREP_START, PREP_CALL + 4), (0x2e6a9d0, 0x2e6a9dc)]
    if enabled_helpers:
        ranges += [(0x2e5349c, 0x2e53520), (0x2e50bf0, 0x2e50df8)]
    m = cp.QueryMicro(APP, ranges, end=PREP_CALL, patches=[query_patch] if query_patch else [], profile_flag=future_flag)
    qp.prepare_map(m.uc)
    m.uc.mem_write(CACHE, cache_blob)
    m.uc.mem_write(ss.INPUT, input_blob)
    for rr, value in [(reg.UC_ARM64_REG_X19, ss.INPUT), (reg.UC_ARM64_REG_X29, FP),
                      (reg.UC_ARM64_REG_X24, 0x398d000), (reg.UC_ARM64_REG_X22, 0x3966000)]:
        m.uc.reg_write(rr, value)
    result = m.run(PREP_START)
    packet = bytes(m.uc.mem_read(FP + 0x60, 0x3c))
    assert bytes(m.uc.mem_read(CACHE, CACHE_SIZE)) == cache_blob
    assert bytes(m.uc.mem_read(ss.INPUT, len(input_blob))) == input_blob
    assert not result['private_flag_reads']
    result.update(actual_original_MPR_input_packet_hex=packet.hex(),
                  query_entry_snapshot=m.query_entry_snapshot,
                  output_vpc_quality_frame=[int.from_bytes(packet[o:o + 4], 'little') for o in (0xc, 0x14, 0x10)],
                  packet_audio_fields=[int.from_bytes(packet[o:o + 4], 'little') for o in (0x18, 0x1c)],
                  packet_proxy_enabled_byte=packet[0x20],
                  original_GetMovieRemain_API_called=False,
                  actual_remaining_seconds_free_space_or_media_queried=False)
    if result['reason'] == 'conversion block complete':
        assert int.from_bytes(packet[:4], 'little') == 0xc
        assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == FP + 0x60
        assert m.uc.reg_read(reg.UC_ARM64_REG_X1) == FP + 0x58
        assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    qp.verify_volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    sources = [APP.path, MPR.path, Path(cp.__file__), Path(pp.__file__), Path(qp.__file__), Path(ss.__file__),
               BASE / 'stage15-private-activation/private_activation.py',
               BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    previous = json.loads((BASE / 'stage17-captured-profile/final-receipt.json').read_text())
    assert all(qp.sha(ROOT / row['path']) == row['sha256'] for row in previous['files'])
    im = pp.Image(); marker = cache_marker(im); rows, wide = cache_rows(im)
    query_patch, _ = qp.new_patch()
    tagged, _ = capture(im, rows, wide, None, {'frame': 0}, tagged=True)
    pairs = []
    for case in pp.allowed_cases(im)['cases']:
        stock, original = capture(im, rows, wide, None, case)
        off, disabled = capture(im, rows, wide, marker, case)
        on, active = capture(im, rows, wide, marker, case, flag=1)
        assert original == disabled and active[0x388:0x38c] == pp.p32(2)
        assert original[:0x388] == active[:0x388] and original[0x38c:] == active[0x38c:]
        copied0, ib0 = copy_to_call(disabled, future_flag=1)
        copied1, ib1 = copy_to_call(active, future_flag=0)
        p0 = prepare_remain(disabled, ib0, query_patch, future_flag=1)
        p1 = prepare_remain(active, ib1, query_patch, future_flag=0)
        expected = a.query(a.patches(im), **case, flag=0)
        assert p0['reason'] == p1['reason'] == 'conversion block complete', (p0['reason'], p1['reason'])
        assert p0['output_vpc_quality_frame'] == expected['output_vpc_quality_frame']
        assert p1['output_vpc_quality_frame'] == a.ENCODING
        assert p0['packet_audio_fields'] == p1['packet_audio_fields']
        pairs.append({'factory_case': case, 'stock_capture': stock, 'disabled_capture': off, 'active_capture': on,
                      'disabled_copy_after_toggle': copied0, 'active_copy_after_toggle': copied1,
                      'disabled_preparation_after_toggle': p0, 'active_preparation_after_toggle': p1})
    controls = []
    for case, flag in [({'frame': 0, 'mode': 0}, 1), ({'frame': 0, 'mode': 10}, 1),
                       ({'frame': 0, 'fmt': 7}, 1), ({'frame': 0, 'fmt': 8}, 1),
                       ({'frame': 2}, 1), ({'frame': 0}, 2), ({'frame': 0}, 0xffffffff)]:
        left, lb = capture(im, rows, wide, None, case)
        right, rb = capture(im, rows, wide, marker, case, flag=flag)
        assert lb == rb
        controls.append({'case': case, 'flag': flag, 'stock': left, 'candidate': right,
                         'same_cache_only_not_full_mode_or_corruption_regression': True})
    proxy_cases = []
    for proxy in (0, 1):
        capt, cache = capture(im, rows, wide, marker, {'frame': 0}, flag=1, proxy=proxy)
        copied, blob = copy_to_call(cache)
        prepared = prepare_remain(cache, blob, query_patch)
        assert prepared['reason'] == 'conversion block complete'
        assert prepared['output_vpc_quality_frame'] == a.ENCODING
        assert int.from_bytes(blob[0x138:0x13c], 'little') == proxy
        proxy_cases.append({'proxy_model_value': proxy, 'capture': capt, 'copy': copied, 'prepared': prepared})
    active = pairs[0]['active_capture']; cache = bytes.fromhex(active['cache_blob_hex'])
    _, blob = copy_to_call(cache)
    no_helper = prepare_remain(cache, blob, query_patch, enabled_helpers=False)
    assert no_helper['reason'] == 'unapproved execution 2e5349c'
    removed = prepare_remain(cache, blob, None)
    assert removed['reason'].startswith('firmware assertion entry reached')
    assert APP.plt[0x1594430] == '_ZN3mpr14GetMovieRemainERKNS_21getMovieRemainInParamEPNS_22getMovieRemainOutParamE'
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    static = ss.StaticImage()
    proof = {'status': 'PASS_CAPTURED_CACHE_TO_ORIGINAL_GET_MOVIE_REMAIN_INPUT_PREPARATION',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'inputs_unchanged': hashes,
        'cache_class_binding': {'RTTI': APP.read(0x3928f50, 80).split(b'\0')[0].decode(),
            'vtable_base': '0x46e7ff0', 'vtable_run_slot': '0x46e8010', 'run': '0x2baf850',
            'constructor': '0x2c3d618', 'GOT_slot': '0x47827d8', 'bytes': CACHE_SIZE,
            'static_owner_scope': ['0x2c3d654 model_lock enter', '0x2c3dbb8 marker site', '0x2c3dbbc model_lock exit'],
            'runtime_owner_or_lifetime_executed': False},
        'copied_scalar_fields': rows, 'copied_opaque_wide_field': wide,
        'tagged_original_copy': tagged,
        'marker_guest_only': {'site': hex(marker[0]), 'synthetic_address_not_camera_cave': hex(marker[1]),
            'instructions': [{'pc': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
                             for i in APP.md.disasm(marker[2], marker[1])]},
        'factory_pairs': pairs, 'capture_only_guard_controls': controls, 'proxy_cases': proxy_cases,
        'unmodelled_audio_helper_stop': no_helper, 'consumer_removal_negative': removed,
        'static_regions': [{'name': name, 'start': hex(start), 'end': hex(end), 'instructions': static.dump(start, end)}
            for name, start, end in [('cache_constructor_prefix', 0x2c3d618, CAPTURE_START),
                ('cache_constructor_body', CAPTURE_START, 0x2c3dbd0), ('actual_cached_copy', COPY_START, COPY_END + 4),
                ('remain_preparation', PREP_START, PREP_CALL + 4)]],
        'scope': 'Original cache getter copies and cached-call copy, original query plus selected default audio/proxy conversions, stop immediately before external MPR API. No actual remaining-time or hardware.',
        'rollback_constraint': 'Cache markers outlive the local caller stack. Rebuild/discard outstanding cached sequence objects as well as marked local packets before removing consumers.',
        'real_common_capture_epoch_writer_record_idle_UI_or_persistence_implemented': False,
        'camera_USB_native_thread_media_free_space_module_WBI_or_write': False,
        'firmware_payload_or_patchfile_exported': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'actual_scalar_getter_copies': len(rows), 'opaque_field_bytes': 19,
        'factory_pairs': len(pairs), 'guard_controls_cache_only': len(controls), 'proxy_cases': len(proxy_cases),
        'target_GetMovieRemain_input_tuple': a.ENCODING, 'actual_GetMovieRemain_API_invoked': False,
        'actual_remaining_seconds_computed': False, 'cached_sequence_drain_required': True,
        'global_model_values_written': False, 'real_epoch_idle_owner_or_recovery_verified': False, 'goal_complete': False}
    qp.write_json(out / 'cached-remain-results.json', proof)
    qp.write_json(out / 'summary.json', summary)
    qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'results_sha256': qp.sha(out / 'cached-remain-results.json'),
        'summary_sha256': qp.sha(out / 'summary.json'), 'inputs': hashes, 'volume_uuid': qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
