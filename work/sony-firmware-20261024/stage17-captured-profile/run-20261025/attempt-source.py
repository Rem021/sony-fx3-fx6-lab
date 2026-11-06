#!/usr/bin/env python3
"""Guest-only captured profile identity over real model-copy instructions.

No global model write, camera loader, persistence or full transaction. Tests
post-capture toggles separately from different-capture negative controls.
"""
from pathlib import Path
import argparse
import datetime
import itertools
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'stage16-system-snapshot')]
import system_snapshot as ss
from unicorn import UC_HOOK_MEM_READ

a, pp, qp = ss.activation, ss.pp, ss.qp
APP, MPR, reg = ss.APP, ss.MPR, ss.reg
SCRATCH, STACK, FP = ss.SCRATCH, ss.STACK, ss.FP
PRODUCER_START, PRODUCER_SITE, PRODUCER_END = 0x27cb7c0, 0x27cbba8, 0x27cbbac
CAPTURE_CODE = pp.CODE + 0xc00
PACKET = FP + 0x200
LOCAL_MARKER_OFFSET = 0x1c


class ReadTrace:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flag_reads = []
        self.hooks.append(self.uc.hook_add(UC_HOOK_MEM_READ, self.read_flag))

    def read_flag(self, uc, access, address, size, value, user):
        if address < a.FLAG + 4 and a.FLAG < address + size:
            self.flag_reads.append({'pc': hex(uc.reg_read(reg.UC_ARM64_REG_PC)),
                                    'address': hex(address), 'size': size})

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        result['private_flag_reads'] = self.flag_reads
        return result


class CopyMicro(ReadTrace, a.FlagApp): pass
class QueryMicro(ReadTrace, ss.CallerMicro): pass


def capture_patch(im):
    assert im.read(PRODUCER_SITE, 4).hex() == 'e00314aa'  # mov x0,x20
    x = pp.Asm(CAPTURE_CODE)
    for w in a.SAVE: x.emit(w)
    a.load_flag(x); x.cmp(0, 1); x.branch('stock', cond=1)
    x.ldr(0, 20, 0x14); x.cmp(0, 6); x.branch('stock', cond=1)
    x.ldr(0, 20, 0x10); x.cmp(0, 16); x.branch('stock', cond=8)
    x.branch(qp.MOVIE_PREDICATE, link=True)
    x.cmp(0, 0); x.branch('stock', cond=0)
    # Keep the selected original model legal. The new identity is local only.
    x.ldr(0, 20, LOCAL_MARKER_OFFSET)
    for valid in (0, 1, 4, 5, 6):
        x.cmp(0, valid); x.branch('mark', cond=0)
    x.branch('stock')
    x.label('mark'); x.mov(0, 2); x.str(0, 20, LOCAL_MARKER_OFFSET)
    x.label('stock')
    for w in a.RESTORE: x.emit(w)
    x.emit(struct.unpack('<I', im.read(PRODUCER_SITE, 4))[0])
    x.branch(PRODUCER_SITE + 4)
    raw = x.finish()
    assert CAPTURE_CODE + len(raw) <= pp.CODE + 4096
    return (PRODUCER_SITE, CAPTURE_CODE, raw)


def model_copy_rows(im):
    ins = list(im.md.disasm(im.read(PRODUCER_START, PRODUCER_END - PRODUCER_START), PRODUCER_START))
    rows = []
    for i, op in enumerate(ins):
        if op.mnemonic != 'bl': continue
        getter = int(op.op_str.split('#')[1], 16)
        following, store = ins[i + 1:i + 3]
        assert following.mnemonic == 'ldr' and following.op_str == 'w0, [x0]'
        assert store.mnemonic == 'str' and store.op_str.startswith('w0, [x29, #')
        offset = int(store.op_str.split('#')[1].rstrip(']'), 16) - 0x200
        cell = im.leaf(getter)
        assert cell is not None and 0 <= offset < 0x150
        rows.append({'getter': getter, 'model_cell': cell, 'local_packet_offset': offset,
                     'call_pc': op.address, 'store_pc': store.address})
    assert len({r['local_packet_offset'] for r in rows}) == len(rows)
    assert next(r for r in rows if r['local_packet_offset'] == 0x138)['getter'] == 0x2935aac
    return rows


def copy_packet(im, rows, patch, case, *, flag=0, proxy=0, tags=False):
    addresses = {r['getter'] for r in rows}
    ranges = [(PRODUCER_START, PRODUCER_END), (qp.MOVIE_PREDICATE, 0x2a4e6e4),
              (0x2a4e794, 0x2a4e798)] + [(addr, addr + 20) for addr in addresses]
    m = CopyMicro(APP, ranges, end=PRODUCER_END, patches=[patch] if patch else [], profile_flag=flag)
    values = {0x2934c9c: case.get('fmt', 6), pp.FRAMEGET: case['frame'],
              pp.Q60: case.get('q60', 12), pp.Q24: case.get('q24', 17),
              pp.Q120: case.get('q120', 9), 0x2935aac: proxy}
    seeded = {r['model_cell']: (0x10000000 + r['local_packet_offset'] if tags else values.get(r['getter'], 0))
              for r in rows}
    for address, value in seeded.items(): m.uc.mem_write(address, pp.p32(value))
    m.uc.mem_write(PACKET, b'\0' * 0x150)  # Original earlier memset is excluded.
    for rr, value in [(reg.UC_ARM64_REG_X29, FP), (reg.UC_ARM64_REG_X20, PACKET),
                      (reg.UC_ARM64_REG_X21, SCRATCH + 0x1000),
                      (reg.UC_ARM64_REG_X19, case.get('mode', 5))]: m.uc.reg_write(rr, value)
    result = m.run(PRODUCER_START)
    assert result['reason'] == 'conversion block complete'
    assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
    assert m.uc.reg_read(reg.UC_ARM64_REG_X0) == PACKET
    assert all(a.read32(m.uc, address) == value for address, value in seeded.items())
    blob = bytes(m.uc.mem_read(PACKET, 0x150))
    for row in rows:
        actual = struct.unpack_from('<I', blob, row['local_packet_offset'])[0]
        if row['local_packet_offset'] == LOCAL_MARKER_OFFSET and patch and flag == 1 and not tags:
            continue  # Separate semantic assertions below determine eligibility.
        assert actual == seeded[row['model_cell']]
    result.update(input_case=case, proxy_model_value=proxy, copied_model_fields=len(rows),
                  global_model_cells_unchanged=True, captured_packet_hex=blob.hex(),
                  local_HS_frame=struct.unpack_from('<I', blob, LOCAL_MARKER_OFFSET)[0],
                  producer_prefix_mode_filter_memset_and_model_lock_executed=False,
                  input_preconditions='Synthetic producer FP, mode and cleared local buffer; original getter copies execute')
    return result, blob


def captured_query(blob, patch, *, future_flag=0):
    m = QueryMicro(APP, list(qp.RANGES) + [(ss.STATUS_START, ss.STATUS_END), (0x2e6a30c, 0x2e6a314)],
                   end=ss.STATUS_END, patches=[patch] if patch else [], profile_flag=future_flag)
    qp.prepare_map(m.uc)
    m.uc.mem_write(ss.INPUT, blob)
    for rr, value in [(reg.UC_ARM64_REG_X19, ss.INPUT), (reg.UC_ARM64_REG_X29, FP),
                      (reg.UC_ARM64_REG_X24, 0x398d000), (reg.UC_ARM64_REG_X22, 0x3966000)]:
        m.uc.reg_write(rr, value)
    offsets = (0xc4, 0xc8, 0xcc)
    for offset in offsets: m.uc.mem_write(FP + offset, pp.p32(0xa5a5a5a5))
    m.uc.mem_write(FP + 0xd4, b'\x7e')
    result = m.run(ss.STATUS_START)
    assert bytes(m.uc.mem_read(ss.INPUT, len(blob))) == blob
    result.update(output_vpc_quality_frame=[a.read32(m.uc, FP + off) for off in offsets],
                  post_query_output_byte_d4=m.uc.mem_read(FP + 0xd4, 1)[0],
                  query_entry_snapshot=m.query_entry_snapshot, captured_input_unchanged=True,
                  full_status_API_or_wrapper_executed=False)
    assert not result['private_flag_reads']
    return result


def tuple_setter(im, patch, values, *, future_flag):
    m = CopyMicro(APP, [(pp.SETTER_ENTRY, pp.SETTER_END), (0x2e6f45c, 0x2e6f494)],
                  end=pp.SETTER_END, patches=[patch], profile_flag=future_flag)
    base = pp.STACK_BASE + 0x10000
    m.uc.mem_write(SCRATCH + 0x10, struct.pack('<4I', *values))
    for rr, value in [(reg.UC_ARM64_REG_X24, SCRATCH), (reg.UC_ARM64_REG_X29, base),
                      (reg.UC_ARM64_REG_X19, base + 0x310)]: m.uc.reg_write(rr, value)
    result = m.run(pp.SETTER_ENTRY)
    result['output_vpc_quality_frame'] = list(struct.unpack('<3I', bytes(m.uc.mem_read(base + 0x480, 12))))
    assert result['reason'] == 'conversion block complete' and not result['private_flag_reads']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    qp.verify_volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    dependencies = [APP.path, MPR.path, Path(ss.__file__), Path(a.__file__), Path(pp.__file__), Path(qp.__file__),
                    BASE / 'stage4-windows-collab/mac-verification/offline_verify.py']
    before = {str(p.relative_to(ROOT)): qp.sha(p) for p in dependencies}
    previous = json.loads((BASE / 'stage16-system-snapshot/final-receipt.json').read_text())
    assert all(qp.sha(ROOT / r['path']) == r['sha256'] for r in previous['files'])
    im = pp.Image(); marker = capture_patch(im); rows = model_copy_rows(im)
    query_patch, _ = qp.new_patch()  # Captured frame2 identity, no live flag read.
    setter_patch = pp.trampolines(im)[1]  # Exact tuple identity, no live flag read.
    builder_patches = a.patches(im)
    tagged, _ = copy_packet(im, rows, None, {'frame': 0}, tags=True)
    comparisons = []
    for case in pp.allowed_cases(im)['cases']:
        stock, plain_blob = copy_packet(im, rows, None, case)
        disabled, disabled_blob = copy_packet(im, rows, marker, case)
        active, marked_blob = copy_packet(im, rows, marker, case, flag=1)
        assert plain_blob == disabled_blob
        assert active['local_HS_frame'] == 2
        assert plain_blob[:0x1c] == marked_blob[:0x1c] and plain_blob[0x20:] == marked_blob[0x20:]
        base_query = captured_query(plain_blob, None)
        inactive_query = captured_query(disabled_blob, query_patch, future_flag=1)
        active_query = captured_query(marked_blob, query_patch, future_flag=0)
        assert base_query['reason'] == inactive_query['reason'] == active_query['reason'] == 'conversion block complete'
        assert base_query['output_vpc_quality_frame'] == inactive_query['output_vpc_quality_frame']
        assert active_query['output_vpc_quality_frame'] == a.ENCODING
        comparisons.append({'factory_legal_case': case, 'stock_copy': stock, 'disabled_copy': disabled,
                            'active_copy': active, 'stock_query': base_query, 'disabled_query_after_toggle': inactive_query,
                            'active_query_after_toggle': active_query})
    post_toggles = []
    for capture_flag, setter_flag, query_flag in itertools.product((0, 1), repeat=3):
        b = a.builder(im, builder_patches, frame=0, flag=capture_flag)
        copied, blob = copy_packet(im, rows, marker, {'frame': 0}, flag=capture_flag)
        s = tuple_setter(im, setter_patch, b['builder_tuple'], future_flag=setter_flag)
        q = captured_query(blob, query_patch, future_flag=query_flag)
        assert q['reason'] == 'conversion block complete'
        assert s['output_vpc_quality_frame'] == q['output_vpc_quality_frame']
        post_toggles.append({'snapshot_capture_flag': capture_flag, 'future_setter_flag': setter_flag,
                             'future_query_flag': query_flag, 'builder': b, 'copy': copied, 'setter': s, 'query': q})
    # Different capture epochs remain a real unresolved constraint.
    different_captures = []
    for builder_flag, query_capture_flag in ((0, 1), (1, 0)):
        b = a.builder(im, builder_patches, frame=0, flag=builder_flag)
        copied, blob = copy_packet(im, rows, marker, {'frame': 0}, flag=query_capture_flag)
        s = tuple_setter(im, setter_patch, b['builder_tuple'], future_flag=0)
        q = captured_query(blob, query_patch, future_flag=0)
        assert s['output_vpc_quality_frame'] != q['output_vpc_quality_frame']
        different_captures.append({'builder_capture_flag': builder_flag, 'query_capture_flag': query_capture_flag,
                                   'setter': s, 'query': q, 'copy': copied, 'same_epoch_not_enforced': True})
    controls = []
    for case, flag in [({'frame': 0, 'mode': 0}, 1), ({'frame': 0, 'mode': 4}, 1),
                       ({'frame': 0, 'mode': 10}, 1), ({'frame': 0, 'fmt': 7}, 1),
                       ({'frame': 0, 'fmt': 8}, 1), ({'frame': 2}, 1),
                       ({'frame': 0}, 2), ({'frame': 0}, 0xffffffff)]:
        left, lb = copy_packet(im, rows, None, case)
        right, rb = copy_packet(im, rows, marker, case, flag=flag)
        assert lb == rb
        controls.append({'case': case, 'flag': flag, 'stock': left, 'candidate': right,
                         'same_packet_only_not_full_mode_regression': True})
    proxies = []
    for proxy in (0, 1):
        copied, blob = copy_packet(im, rows, marker, {'frame': 0}, flag=1, proxy=proxy)
        q = captured_query(blob, query_patch)
        assert q['output_vpc_quality_frame'] == a.ENCODING and q['post_query_output_byte_d4'] == 1 - proxy
        assert struct.unpack_from('<I', blob, 0x138)[0] == proxy
        proxies.append({'proxy_model_value': proxy, 'copy': copied, 'query': q,
                        'actual_proxy_encoding_or_settings_modified': False})
    assert before == {str(p.relative_to(ROOT)): qp.sha(p) for p in dependencies}
    proof = {'status': 'PASS_CAPTURED_LOCAL_PROFILE_WITH_DISTINCT_CAPTURE_NEGATIVES',
             'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'inputs_unchanged': before,
             'scope': 'Original model-copy and marshalling/query slices plus own guest marker and tuple conversion. Independent snapshots, not full transaction or runtime synchronization.',
             'model_copy_fields': [{k: hex(v) if k != 'local_packet_offset' else hex(v) for k, v in row.items()} for row in rows],
             'distinct_tag_original_copy': tagged,
             'capture_patch_guest_only': {'site': hex(marker[0]), 'synthetic_code': hex(marker[1]),
                  'instructions': [{'pc': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic + ' ' + i.op_str}
                                   for i in APP.md.disasm(marker[2], marker[1])]},
             'consumers': {'builder': 'stage15 activation read during model capture',
                 'setter': 'stage12 exact target tuple, no live flag read',
                 'query': 'stage13 exact captured frame2 identity, no live flag read',
                 'global_frame2_storage': False, 'marker_only_in_stack_local_input_copy': True},
             'factory_legal_capture_comparisons': comparisons, 'all_post_capture_binary_toggles': post_toggles,
             'different_capture_epoch_negatives': different_captures, 'copy_only_guard_controls': controls,
             'proxy_input_preservation_cases': proxies,
             'real_model_lock_threading_record_idle_or_epoch_enforcement_executed': False,
             'system_NTSC_PAL_guard_implemented': False,
             'rollback_constraint': 'Drain or discard in-flight marked local packets and active tuples before removing their consumers; preserved global settings alone do not prove unload/rollback safe.',
             'camera_USB_driver_files_module_WBI_settings_or_firmware_actions': False,
             'firmware_payload_or_patchfile_exported': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'actual_original_getter_copies': len(rows),
               'factory_legal_capture_comparisons': len(comparisons),
               'post_capture_binary_toggles': len(post_toggles), 'post_capture_tuple_mismatches': 0,
               'different_capture_epoch_negatives': len(different_captures),
               'copy_only_guard_controls': len(controls), 'proxy_input_preservation_cases': len(proxies),
               'global_model_values_written': False, 'real_epoch_or_idle_gate_implemented': False,
               'camera_hardware_or_restore_verified': False, 'goal_complete': False}
    qp.write_json(out / 'captured-results.json', proof)
    qp.write_json(out / 'summary.json', summary)
    qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'results_sha256': qp.sha(out / 'captured-results.json'),
        'summary_sha256': qp.sha(out / 'summary.json'), 'inputs': before, 'volume_uuid': qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
