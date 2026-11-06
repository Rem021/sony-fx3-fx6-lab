#!/usr/bin/env python3
"""Original caller marshalling and system-value boundaries, entirely offline.

Runs bounded instruction slices with synthetic caller frames. No full status or
remain API, locks, backup backend, persistence, encoder or camera is executed.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'stage15-private-activation'),
               str(BASE / 'stage14-model-lifecycle'), str(BASE / 'stage10-mainpath/main')]
import private_activation as activation
import model_lifecycle as lifecycle
from audit_main_path import Image as StaticImage

pp, qp = activation.pp, activation.qp
APP, MPR, reg = activation.APP, activation.MPR, activation.reg
SCRATCH, STACK, STOP = activation.SCRATCH, activation.STACK, pp.STOP
INPUT = SCRATCH + 0x8000
FP = STACK + 0x230
SYSTEM_GETTER, SYSTEM_PAIRED = 0x293dfec, 0x293e000
STATUS_START, STATUS_CALL, STATUS_END = 0x2e69fac, 0x2e6a1f0, 0x2e6a208
REMAIN_START, REMAIN_CALL, REMAIN_END = 0x2e6a6a8, 0x2e6a8f8, 0x2e6a8fc
BACKUP_CONVERT, BACKUP_CONVERT_END = 0x2ebfa14, 0x2ebfabc


class CallerMicro(activation.FlagQuery):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_entry_snapshot = None

    def code(self, u, address, size, user):
        if address == qp.QUERY_ENTRY:
            assert self.query_entry_snapshot is None
            sp = u.reg_read(reg.UC_ARM64_REG_SP)
            self.query_entry_snapshot = {
                'register_args_x0_x7': [u.reg_read(getattr(reg, f'UC_ARM64_REG_X{i}')) for i in range(8)],
                'stack_scalar_args_66': [int.from_bytes(u.mem_read(sp + i * 8, 8), 'little') for i in range(66)],
                'output_pointers': [int.from_bytes(u.mem_read(sp + i, 8), 'little') for i in (0x210, 0x218, 0x220)],
                'lr': hex(u.reg_read(reg.UC_ARM64_REG_LR)),
                'callee_saved_caller_input_pointer': hex(u.reg_read(reg.UC_ARM64_REG_X19)),
            }
        super().code(u, address, size, user)


def marshal(im, ps, case, *, caller='status', flag=0, system=0, capture_only=False):
    status = caller == 'status'
    start, call, end = ((STATUS_START, STATUS_CALL, STATUS_END) if status else
                        (REMAIN_START, REMAIN_CALL, REMAIN_END))
    ranges = list(qp.RANGES) + [(start, call + 4)]
    if status:
        ranges += [(call + 4, STATUS_END), (0x2e6a30c, 0x2e6a314)]
    m = CallerMicro(APP, ranges, end=qp.QUERY_ENTRY if capture_only else end,
                    patches=ps[2:], profile_flag=flag)
    qp.prepare_map(m.uc)
    data = bytearray(0x180)
    if capture_only:
        values = {offset: 0x10000000 + offset for offset in range(0x10, 0x138, 4)}
    else:
        values = {0x10: case.get('mode', 5), 0x14: case.get('fmt', 6),
                  0x1c: case['frame'], 0x3c: case.get('q60', 12),
                  0x40: case.get('q24', 17), 0x44: case.get('q120', 9)}
    for offset, value in values.items(): struct.pack_into('<I', data, offset, value)
    struct.pack_into('<I', data, 0x138, system)
    m.uc.mem_write(INPUT, bytes(data))
    m.uc.reg_write(reg.UC_ARM64_REG_X19, INPUT)
    m.uc.reg_write(reg.UC_ARM64_REG_X29, FP)
    m.uc.reg_write(reg.UC_ARM64_REG_X24, 0x398d000)
    m.uc.reg_write(reg.UC_ARM64_REG_X22, 0x3966000)
    out_offsets = (0xc4, 0xc8, 0xcc) if status else (0x6c, 0x74, 0x70)
    for offset in out_offsets: m.uc.mem_write(FP + offset, pp.p32(0xa5a5a5a5))
    m.uc.mem_write(FP + 0xd4, b'\x7e')
    result = m.run(start)
    snapshot = m.query_entry_snapshot
    assert snapshot is not None
    expected_regs = [struct.unpack_from('<I', data, 0x10 + i * 4)[0] for i in range(8)]
    expected_stack = [struct.unpack_from('<I', data, 0x30 + i * 4)[0] for i in range(66)]
    assert snapshot['register_args_x0_x7'] == expected_regs
    assert snapshot['stack_scalar_args_66'] == expected_stack
    assert snapshot['output_pointers'] == [FP + out_offsets[0], FP + out_offsets[2], FP + out_offsets[1]]
    assert snapshot['lr'] == hex(call + 4)
    assert bytes(m.uc.mem_read(INPUT, len(data))) == bytes(data)
    if result['reason'] == 'conversion block complete':
        assert m.uc.reg_read(reg.UC_ARM64_REG_SP) == STACK
        assert m.uc.reg_read(reg.UC_ARM64_REG_X19) == INPUT
        assert m.uc.reg_read(reg.UC_ARM64_REG_X29) == FP
    result.update(caller=caller, input_case=case, system_model_value=system,
                  actual_original_marshalling=True, query_entry_snapshot=snapshot,
                  output_vpc_quality_frame=[activation.read32(m.uc, FP + offset) for offset in out_offsets],
                  status_system_byte=m.uc.mem_read(FP + 0xd4, 1)[0] if status else None,
                  input_object_unchanged=True,
                  preconditions='Synthetic caller FP/SP/input pointer; entry excludes earlier enable/context/logging/init paths',
                  full_status_or_remain_API_executed=False)
    return result


def raw_backup_conversion(value):
    # Start AFTER the original backend read. Never calls the backend or supplies
    # a stub for it. Stop before epilogue; this is a post-read conversion slice.
    m = qp.QueryMicro(APP, [(BACKUP_CONVERT, 0x2ebfad4)], end=BACKUP_CONVERT_END)
    m.uc.reg_write(reg.UC_ARM64_REG_X29, FP)
    m.uc.reg_write(reg.UC_ARM64_REG_X19, SCRATCH + 0xb000)
    m.uc.mem_write(FP + 0x3f, bytes([value]))
    m.uc.mem_write(SCRATCH + 0xb000, pp.p32(0xfeedf00d))
    r = m.run(BACKUP_CONVERT)
    r.update(synthetic_raw_backup_byte=value,
             output_model_value=activation.read32(m.uc, SCRATCH + 0xb000),
             backend_executed_or_stubbed=False, getter_prologue_or_epilogue_executed=False)
    if value in (0, 1):
        assert r['reason'] == 'conversion block complete' and r['output_model_value'] == 1 - value
    else:
        assert r['reason'].startswith('firmware assertion entry reached')
        assert r['output_model_value'] == 0xfeedf00d
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    qp.verify_volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    sources = [APP.path, MPR.path, Path(activation.__file__), Path(qp.__file__), Path(pp.__file__),
               Path(lifecycle.__file__), BASE / 'stage4-windows-collab/mac-verification/offline_verify.py',
               BASE / 'stage10-mainpath/main/audit_main_path.py']
    hashes = {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    old = json.loads((BASE / 'stage15-private-activation/final-receipt.json').read_text())
    assert all(qp.sha(ROOT / f['path']) == f['sha256'] for f in old['files'])
    im = pp.Image(); static = StaticImage(); ps = activation.patches(im)
    registry = lifecycle.registry_row(0x7a7)
    assert registry['name'] == 'setting_ntsc_pal_selector'
    current, paired = im.leaf(SYSTEM_GETTER), im.leaf(SYSTEM_PAIRED)
    assert (current, paired) == (0x831eca8, 0x831ecac)
    captures = [marshal(im, ps, {'frame': 0}, caller=c, capture_only=True) for c in ('status', 'remain')]
    runs = []
    for case in pp.allowed_cases(im)['cases']:
        for caller in ('status', 'remain'):
            for flag in (0, 1):
                result = marshal(im, ps, case, caller=caller, flag=flag)
                expected = activation.query(ps, **case, flag=flag)
                assert result['reason'] == 'conversion block complete'
                assert result['output_vpc_quality_frame'] == expected['output_vpc_quality_frame']
                if caller == 'status': assert result['status_system_byte'] == 1
                runs.append(result)
    systems = [marshal(im, ps, {'frame': 0}, flag=flag, system=system)
               for system in (0, 1, 2, 0xffffffff) for flag in (0, 1)]
    for r in systems:
        system, flag = r['system_model_value'], r['synthetic_private_flag']
        if system in (0, 1):
            assert r['reason'] == 'conversion block complete' and r['status_system_byte'] == 1 - system
        else:
            assert r['reason'] == 'unapproved execution 2e6a314' and r['status_system_byte'] == 0x7e
        if flag == 1: assert r['output_vpc_quality_frame'] == activation.ENCODING
    backups = [raw_backup_conversion(v) for v in (0, 1, 2, 0xff, 0x80)]
    # Two original packet preparations link the system flag to fractional/integer
    # frame families; they do not read the setting model or establish its name.
    packet_cases = []
    for frame, ratio, expected_flag in ((3, [30000, 1001], 1), (2, [25, 1], 0)):
        downstream = pp.downstream([6, 6, frame], logging_adapter=True)
        assert downstream['rational']['reason'] == downstream['open_parameter_preparation']['reason'] == 'returned'
        assert [downstream['rational'][k] for k in ('numerator', 'denominator')] == ratio
        assert downstream['open_parameter_preparation']['fields']['ntsc_flag'] == expected_flag
        packet_cases.append(downstream)
    assert hashes == {str(p.relative_to(ROOT)): qp.sha(p) for p in sources}
    regions = [('system_update_key_and_getters', 0x2823420, 0x2823468),
               ('system_getters', SYSTEM_GETTER, 0x293e014),
               ('backup_read_and_conversion', 0x2ebf9e8, 0x2ebfad4),
               ('backup_write_conversion_not_executed', 0x2ebfad4, 0x2ebfbc8),
               ('status_marshaller', STATUS_START, STATUS_END),
               ('status_system_zero_branch', 0x2e6a30c, 0x2e6a314),
               ('remain_marshaller', REMAIN_START, REMAIN_END),
               ('producer_system_field_candidate', 0x22e0eac, 0x22e0ed0)]
    proof = {'status': 'PASS_ORIGINAL_MARSHALLING_AND_SYSTEM_NAMESPACE_AUDIT',
             'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'source_hashes_unchanged': hashes, 'prior_stage_files_verified': len(old['files']),
             'system_registry': registry, 'system_getters': {'current': hex(SYSTEM_GETTER), 'current_cell': hex(current),
                'paired': hex(SYSTEM_PAIRED), 'paired_cell': hex(paired), 'not_persistent_backup_addresses': True},
             'namespaces': {'internal_setting_key': '0x7a7', 'backend_item_seen_in_original_code': '0x010704fd',
                'backup_byte_to_model': {'0': 1, '1': 0},
                'raw_backend_addressing_size_lifetime_and_recovery_not_established': True,
                'named_NTSC_model0_PAL_model1_mapping': 'inferred from original status byte and fractional/integer packet flags; name strings exist but exact label binding is not independently proven'},
             'static_regions': [{'name': name, 'start': hex(start), 'end': hex(end), 'instructions': static.dump(start, end)}
                                for name, start, end in regions],
             'direct_call_references': static.calls({0x2e69ef0, 0x2e6a59c, qp.QUERY_ENTRY}),
             'distinct_tag_marshalling_captures': captures,
             'factory_legal_marshalled_query_runs': runs, 'system_model_cases': systems,
             'post_backend_raw_conversion_cases': backups, 'fractional_integer_MPR_packet_controls': packet_cases,
             'finding': 'The current private-flag query candidate returns frame3 even with system model1; the original status path then writes system byte0. A valid query tuple alone does not establish coherent system configuration.',
             'scope': 'Original marshalling slices and synthetic caller frames, not full APIs, caller construction, locking, actual mode transitions, backend or camera',
             'no_query_or_backup_output_stubs': True,
             'mpr_adapter': 'Existing single-address logging PC<-LR adapter only; no field or return-value writes',
             'full_system_guard_or_config_ownership_implemented': False,
             'camera_USB_backup_backend_module_WBI_or_write_executed': False,
             'firmware_payload_or_patchfile_exported': False, 'goal_complete': False}
    summary = {'status': proof['status'], 'distinct_tag_callers': len(captures),
               'actual_scalar_arguments_per_caller': 74, 'actual_output_pointers_per_caller': 3,
               'factory_legal_marshalled_query_runs': len(runs), 'system_model_cases': len(systems),
               'post_backend_raw_conversion_cases': len(backups),
               'fractional_integer_packet_controls': len(packet_cases),
               'raw_backup_byte_equals_model_value': False,
               'system_model1_with_active_candidate': {'query_tuple': [6, 6, 3], 'status_system_byte': 0},
               'full_API_camera_system_guard_or_restore_verified': False, 'goal_complete': False}
    qp.write_json(out / 'system-snapshot-results.json', proof)
    qp.write_json(out / 'summary.json', summary)
    qp.write_json(out / 'source-receipt.json', {'script': str(Path(__file__).relative_to(ROOT)),
        'script_sha256': qp.sha(Path(__file__)), 'results_sha256': qp.sha(out / 'system-snapshot-results.json'),
        'summary_sha256': qp.sha(out / 'summary.json'), 'inputs': hashes, 'volume_uuid': qp.EXPECTED_VOLUME})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__': main()
