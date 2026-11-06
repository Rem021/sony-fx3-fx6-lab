#!/usr/bin/env python3
"""Seal bounded MIPS QoS consumption/copy evidence, no hardware claim."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE))
import vcd_qos as a
im, BASE, ROOT = a.im, a.BASE, a.ROOT


def main():
    im.volume()
    s = STAGE
    assert not (s/'final-receipt.json').exists()
    prior = BASE/'stage78-native-start-flags-and-query-tail/final-receipt.json'
    assert im.sha(prior.read_bytes()) == 'abe85ad128853086e4af536afdd72050aa18d5713e3a7ce3f8c0943ee8e820b5'
    previous = json.loads(prior.read_text())['files']
    assert len(previous) == 11
    for row in previous:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    before = (s/'goal-status-before.json').read_bytes()
    canonical = BASE/'GOAL_STATUS.json'
    assert before == canonical.read_bytes() == (prior.parent/'goal-status-after.json').read_bytes()
    formal = s/'run-source-bounded-20261026'
    result_path = formal/'vcd-qos-results.json'
    j = json.loads(result_path.read_text())
    assert j['status'] == 'PASS_ORIGINAL_MIPS_QOS_TARGET_CONSUMER_WITH_BOUNDED_TIMING_STOP'
    assert j['source_receipt']['script_sha256'] == im.sha((s/'vcd_qos.py').read_bytes())
    assert (formal/'executed-source.py').read_bytes() == (s/'vcd_qos.py').read_bytes()
    src = prior.parent/'run-20261026/start-flags-results.json'
    assert j['source_receipt']['captured_stage78_result_sha256'] == im.sha(src.read_bytes())
    originals = json.loads(src.read_text())['cases']
    blob = a.v.VCD_PATH.read_bytes()
    assert j['source_receipt']['VCD_sha256'] == im.sha(blob) == im.PINS[str(a.v.VCD_PATH.relative_to(BASE))]
    assert len(j['cases']) == 12 and j['original_function_entries'] == 18
    assert j['original_returned_cases'] == 10 and j['timing_boundary_cases'] == 2
    assert j['independent_existing_handle_transfers'] == 4 and j['independent_missing_handle_boundaries'] == 2
    returned_backend = 0
    for x in j['cases']:
        source = next(z for z in originals if z['seed'] == x['seed'])
        prefix = bytes.fromhex(source['cases'][x['source_case_index']]['extra_first64_hex'])
        if not x['source_bytes_unmodified']:
            edited = bytearray(prefix)
            struct.pack_into('<I', edited, 0, 0)
            prefix = bytes(edited)
        assert x['input_prefix64_hex'] == prefix.hex()
        assert x['original_image_and_input_unchanged'] and x['whole_context_matches_only_declared_target_flag_and_pending_changes']
        assert x['scalar_return_not_used_as_hardware_success'] and not x['outer_MMIO_translation_allocator_or_hardware_application_executed']
        mask = int.from_bytes(prefix[:4], 'little')
        if mask == 0x80:
            assert x['input_offsets_read'] == [0, 1, 2, 3, 24, 25, 26, 27]
            assert x['pending_byte_after'] == 1
            assert x['decoded_context_target_after'] == a.decode(int.from_bytes(prefix[0x18:0x1c], 'little'))
            assert hex(a.IMAGE+0x18faa0) in x['pcs']
        elif mask == 0:
            assert x['input_offsets_read'] == [0, 1, 2, 3]
            assert x['pending_byte_after'] == 0 and x['decoded_context_target_after'] == 16000000
        else:
            assert mask == 0x100
            assert x['timing_boundary']['original_stack_argument8_hex'] == '80a90300481f0000'
            assert not x['timing_boundary']['callee_executed']
        if 'independent_existing_handle_transfer' in x:
            b = x['independent_existing_handle_transfer']
            assert b['reason'] == 'returned' and b['native_copy_bytes'] == 292
            raw = bytes.fromhex(b['output_guarded1024_hex'])
            assert raw[0x1c:0x140].hex() == b['original_parameter_source292_hex']
            assert raw[:0x1c] == bytes([0xb6])*0x1c and raw[0x140:] == bytes([0xb6])*(0x400-0x140)
            assert b['copied_target_decoded'] == x['decoded_context_target_after']
            assert b['backend_update_flag_after'] & 0x40 and b['pending_byte_not_cleared']
            assert b['handle_and_physical_buffer_are_declared_fixtures_not_actual_allocations']
            assert not b['allocation_GP_path_hardware_application_or_upper_completion_executed']
            assert hex(a.IMAGE+0x19bdd8) not in b['pcs']
            returned_backend += 1
        if 'independent_missing_handle_boundary' in x:
            b = x['independent_missing_handle_boundary']
            assert b['reason'] == 'boundary: original_runtime_GP_dependency_before_execution'
            assert b['native_copy_bytes'] == 0 and b['pending_byte_not_cleared']
            assert bytes.fromhex(b['output_guarded1024_hex']) == bytes([0xb6])*0x400
    assert returned_backend == 4
    for directory in ('run-20261026', 'run-backend-transfer-20261026'):
        p = s/directory
        old = json.loads((p/'vcd-qos-results.json').read_text())
        assert im.sha((p/'executed-source.py').read_bytes()) == old['source_receipt']['script_sha256']
    assert not j['Windows_UU_camera_operations'] and not j['goal_complete'] and not j['persistent_write_release']
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(ROOT))
    words = {int(x['offset'], 16): x for x in j['runtime_update_words']}
    assert words[0x19bde0]['bytes'] == '26000070' and words[0x19bde0]['asm'] is None
    boundaries = {
        'created_utc': now,
        'scope': 'STATIC_AND_BOUNDED_DECLARED_CONTEXT_NOT_PHYSICAL_APPLICATION',
        'outer_translation': {'offset': '18fd58', 'MMIO_load_offset': '18fd6c',
                              'address': 'BE000064', 'executed': False},
        'existing_handle_branch': {'entry': '19bda4', 'copy_bytes': 292,
                                   'destination_start': 'declared buffer+1c', 'destination_target_word': '+28',
                                   'valid_hardware_request_or_real_allocation_proven': False},
        'missing_handle': {'stop_before': '19bdd8', 'unknown_GP_state_not_read': True,
                           'unexecuted_undecoded_words': [x for x in j['runtime_update_words'] if x['asm'] is None]},
        'timing': {'stop_before': '1a085c', 'native_argument8_hex': '80a90300481f0000',
                   'hardware_frame_rate_or_exact30_proven': False},
        'upper_pending_completion_and_buffer_consumers_executed': False,
        'same_body_health_backup_or_independent_recovery_proven': False,
    }
    im.write_json(s/'runtime-boundaries.json', boundaries)
    review = {
        'created_utc': now, 'status': 'PASS_NATIVE_MIPS_QOS_CONSUMPTION_AND_EXISTING_HANDLE_COPY_SCOPE',
        'prior_sealed_files_verified': 11, 'input_cases': 12, 'original_function_entries': 18,
        'original_returns': 14, 'bounded_stops': 4,
        'original_prefix80_target_consumed_into_context198_and_flag280': True,
        'cleared_mask_retained20M_word_does_not_update_context': True,
        'original_existing_handle292_copy_count': 4,
        'pending_byte_retained_not_upper_completion_proof': True,
        'missing_handle_GP_boundaries': 2, 'timing_helper_entry_boundaries': 2,
        'original_runtime_allocation_physical_mapping_full_Start_hardware_recording_or_recovery_proven': False,
        'Windows_UU_camera_operations': False, 'goal_complete': False, 'persistent_write_release': False,
        'review_scope': 'Same agent source/trace/byte review, not independent reimplementation or camera acceptance.',
    }
    im.write_json(s/'completed-evidence-review.json', review)
    im.write_json(s/'summary.json', review)
    im.write_json(s/'coordinator-observations.json', {
        'recorded_utc': now, 'previous_goal_turn_classification': 'progress',
        'previous_evidence': 'stage78 sealed11 files and canonical verified; native Start flags/preparation, downstream still open.',
        'new_evidence': 'Actual captured QoS prefixes consumed by original MIPS code; optional20M updates a separate declared state and is copied by original existing-handle path into a declared guarded buffer. Missing-handle/timing boundaries retained.',
        'Windows_UU_actions_this_turn': 0, 'camera_operations': False,
        'requirements_retained': 16, 'goal_complete': False, 'persistent_write_release': False,
    })
    old = json.loads(before)
    g = json.loads(before)
    g['updated_utc'] = now
    g['latest_stage'] = s.name
    g['research_activity'] = 'Mac_only_native_MIPS_QoS_consumption_and_existing_handle_parameter_transfer'
    g['progress_audit'] = {
        'classification': 'progress', 'previous_goal_turn_classification': 'progress',
        'basis': [
            'stage78封存11件/canonical复核；原样64字节输出前缀交官方VCD原18fdb4/18faa0，不虚构全128字节传输或实际流状态。',
            '更新位80消费目标字到声明context198，置context280 bit29与待处理字节；20M字但更新位0时不读目标/保留16M。尾参数原样传到1a085c前停。',
            '四次明确已有句柄输入上，原19bda4复制292字节并保留16M/20M目标、设置后端40位，保护区保持且外层pending仍1。不是实际分配/物理映射、语义完整硬件请求或上层完成；无句柄两例在GP读取前停，不改未知指令/分配返回。',
            '12输入18原入口/14原返回4边界复核；原文件/C原型/相机授权/Mac-only和16项要求不变。完整Start/真实同步/硬件录制/成片及同机恢复仍未证。',
        ],
        'completion_not_claimed': True,
    }
    g['latest_stage_evidence']['stage79_vcd_qos_consumption'] = {
        'readme': rel+'/README.md', 'review': rel+'/completed-evidence-review.json',
        'result': rel+'/run-source-bounded-20261026/vcd-qos-results.json',
        'boundaries': rel+'/runtime-boundaries.json',
        'scope': 'Original MIPS QoS consumer and explicitly preallocated-handle copy; declared RAM/context, no real allocation, hardware acceptance, completed Start or recovery.',
        'authorization_unchanged': True, 'goal_complete': False,
    }
    for req in g['requirements']:
        if req['id'] in ('G02', 'G10', 'G11'):
            req['evidence'].extend([rel+'/run-source-bounded-20261026/vcd-qos-results.json', rel+'/runtime-boundaries.json'])
            req['stage79_scope'] = '原VCD QoS消费更新位/目标到声明状态并置pending；已有句柄原路径复制292含目标并置后端更新位，仍保留pending。无真实分配/物理映射/上层完成/完整Start/硬件接受；无句柄GP读取及尾参数helper前保留边界。12输入18入口，全部实机验收仍缺。'
    g['next_safe_offline_actions'].append(
        'stage79优先追VCD真实流状态/已有句柄的构造与所有权、190878..190900的pending/提交结果及292字节缓冲后续消费者；再接1a085c尾参数语义。现有handle/地址是声明输入，未初始化字节不当完整硬件请求；无句柄GP/未知指令/真实分配不可伪造。外层18fd58 MMIO映射和全部Start/HAL/实机与恢复验收保留。')
    for key in ('objective', 'authorization', 'completion_rule', 'current_user_operational_constraint',
                'external_dependencies', 'current_guest_adapter_prototype'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16
    assert [(x['id'], x['status']) for x in g['requirements']] == [(x['id'], x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json', g)
    after = (s/'goal-status-after.json').read_bytes()
    index = ROOT/'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3 VCD侧QoS消费与缓冲转交](<work/sony-firmware-20261024/stage79-vcd-qos-consumption/README.md>)：原目标字进入声明状态/已有句柄缓冲，pending仍保留；12输入18入口，分配/硬件应用/主录/恢复未证，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n') == 1
    ia = ib.decode().replace('## 相机与固件研究\n', '## 相机与固件研究\n\n'+entry, 1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    files = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': im.sha(p.read_bytes())}
             for p in sorted(s.rglob('*')) if p.is_file()]
    final = {
        'schema': 'fx3-stage79-vcd-qos-consumption/1', 'created_utc': now, 'volume_uuid': im.VOLUME,
        'files': files, 'previous_manifest_sha256': im.sha(prior.read_bytes()),
        'mutable_progress': {'path': str(canonical), 'before_sha256': im.sha(before), 'after_sha256': im.sha(after)},
        'readme_index_entry': entry, 'readme_index_before_sha256': im.sha(ib), 'readme_index_after_sha256': im.sha(ia),
        'operations': review, 'requirements_retained': 16, 'authorization_unchanged': True,
    }
    im.write_json(s/'final-receipt.json', final)
    assert all(im.sha((ROOT/x['path']).read_bytes()) == x['sha256'] for x in files)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({'sealed_files': len(files), 'manifest_sha256': im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage': s.name, 'hardware_recording_or_recovery_proven': False, 'goal_complete': False}))


if __name__ == '__main__':
    main()
