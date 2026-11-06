#!/usr/bin/env python3
"""Seal pending/timing evidence and disclose observed MIPS hook limitation."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE))
import pending_timing as a
im, BASE, ROOT, IMAGE = a.im, a.BASE, a.ROOT, a.IMAGE


def main():
    im.volume()
    s = STAGE
    assert not (s/'final-receipt.json').exists()
    prior = BASE/'stage79-vcd-qos-consumption/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '3e43f278545b3d7e1bba4892a248ae8e2716883acfb741b6fe0bdcfa44aa9157'
    old_rows = json.loads(prior.read_text())['files']
    assert len(old_rows) == 15
    for row in old_rows:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    before = (s/'goal-status-before.json').read_bytes()
    canonical = BASE/'GOAL_STATUS.json'
    assert before == canonical.read_bytes() == (prior.parent/'goal-status-after.json').read_bytes()
    formal = s/'run-final-observer-20261026'
    j = json.loads((formal/'pending-timing-results.json').read_text())
    assert (formal/'executed-source.py').read_bytes() == (s/'pending_timing.py').read_bytes()
    assert j['source_receipt']['script_sha256'] == im.sha((s/'pending_timing.py').read_bytes())
    assert j['source_receipt']['prior_runner_sha256'] == im.sha((a.a.STAGE/'vcd_qos.py').read_bytes())
    assert j['source_receipt']['observer_comparison_sha256'] == im.sha((s/'observer-matrix.json').read_bytes())
    origin = BASE/'stage78-native-start-flags-and-query-tail/run-20261026/start-flags-results.json'
    assert j['source_receipt']['stage78_result_sha256'] == im.sha(origin.read_bytes())
    source = json.loads(origin.read_text())['cases']
    blob = a.a.v.VCD_PATH.read_bytes()
    assert j['source_receipt']['VCD_sha256'] == im.sha(blob) == im.PINS[str(a.a.v.VCD_PATH.relative_to(BASE))]
    assert j['status'] == 'PASS_NATIVE_PENDING_CLEAR_BACKEND_FLAGS_RETAINED_AND_TIMING_COPY'
    assert len(j['cases']) == 14 and j['bounded_phases'] == 24 and j['whole_QoS_dispatch_returns'] == 12
    rate, no_handle, timing, timing_absent, skipped = 0, 0, 0, 0, 0
    for x in j['cases']:
        src = next(z for z in source if z['seed'] == x['seed'])
        prefix = bytearray.fromhex(src['cases'][x['source_case_index']]['extra_first64_hex'])
        if x['source_mask_only_mutated']:
            struct.pack_into('<I', prefix, 0, 0)
        assert prefix.hex() == x['source_prefix64_hex']
        mask = struct.unpack_from('<I', prefix)[0]
        assert x['whole_context_and_output_match_only_declared_native_effects']
        assert not x['actual_live_flow_driver_initialization_physical_mapping_hardware_ack_or_recording_proven']
        for e in x['phases']:
            assert not e['memory_read_write_hooks_installed'] and e['memory_read_write_access_trace'] is None
            assert e['original_image_input_and_declared_handle_unchanged']
            assert e['stack_outside_declared_0x200byte_frame_window_unchanged']
            assert not e['native_output_PC_or_service_return_adapter']
            assert e['pcs'].count(hex(IMAGE+0x1a085c)) <= 1
        raw = bytes.fromhex(x['output4096_hex'])
        if mask == 0x80 and x['declared_existing_handle']:
            assert x['pending_before_upper'] == 1 and x['pending_after'] == 0
            assert x['backend_parameter_flag40'] and not x['backend_timing_flag20000000']
            e = x['phases'][1]
            assert e['reason'] == 'boundary: before_unmatched_outer_epilogue'
            assert all(hex(IMAGE+pc) in e['pcs'] for pc in (0x1908b8, 0x19bda4, 0x1908c0, 0x1908cc))
            assert e['pcs'].index(hex(IMAGE+0x19bda4)) < e['pcs'].index(hex(IMAGE+0x1908cc))
            word = struct.unpack_from('<I', raw, 0x28)[0]
            assert a.a.decode(word) == x['encoded_target_decoded']
            assert raw[:0x1c] == bytes([0xb6])*0x1c and raw[0x140:] == bytes([0xb6])*(4096-0x140)
            rate += 1
        elif mask == 0x80:
            assert x['pending_before_upper'] == x['pending_after'] == 1
            assert x['phases'][1]['reason'] == 'boundary: before_unknown_GP_parameter_allocation_state'
            assert not x['backend_parameter_flag40'] and raw == bytes([0xb6])*4096
            no_handle += 1
        elif mask == 0x100 and x['declared_existing_handle']:
            e = x['phases'][0]
            assert e['reason'] == 'returned' and len(e['native_entries']) == 1
            assert hex(IMAGE+0x1a09ec) in e['pcs']
            assert e['native_entries'][0]['native_argument8_hex'] == '80a90300481f0000'
            assert x['pending_after'] == 0 and x['backend_timing_flag20000000'] and not x['backend_parameter_flag40']
            assert raw[0x7d0:0x7d8].hex() == '80a90300481f0000'
            assert raw[:0x7d0] == bytes([0xb6])*0x7d0 and raw[0x7d8:] == bytes([0xb6])*(4096-0x7d8)
            timing += 1
        elif mask == 0x100:
            assert x['phases'][0]['reason'] == 'boundary: before_unknown_GP_timing_allocation_state'
            assert not x['backend_timing_flag20000000'] and raw == bytes([0xb6])*4096
            timing_absent += 1
        else:
            assert mask == 0 and x['pending_after'] == 0
            assert not x['phases'][1]['native_entries']
            assert raw == bytes([0xb6])*4096
            skipped += 1
    assert (rate,no_handle,timing,timing_absent,skipped) == (4,2,2,2,4)
    matrix = json.loads((s/'observer-matrix.json').read_text())
    assert matrix['script_sha256'] == im.sha((s/'probe_mips_observers.py').read_bytes())
    assert matrix['unicorn_version'] == a.u.__version__ == '2.1.4'
    bykind = {x['kind']:x for x in matrix['cases']}
    for kind in ('none','code'):
        assert bykind[kind]['error'] is None and bykind[kind]['PC'] == hex(a.STOP)
        assert bykind[kind]['SP'] == hex(a.SP) and bykind[kind]['timing8_hex'] == '80a90300481f0000'
    for kind in ('memory','both'):
        assert bykind[kind]['error'] == 'Invalid memory read (UC_ERR_READ_UNMAPPED)'
        assert bykind[kind]['SP'] != hex(a.SP)
    assert bykind['code']['target_entry_occurrences'] == 1 and bykind['both']['target_entry_occurrences'] == 2
    attempts = ['run-20261026','run-stack-observer-20261026','run-entry-read-after-stop-20261026',
                'run-rx-observer-20261026','run-no-callback-register-read-20261026','run-observer-budget-20261026']
    assert all(not json.loads((s/name/'attempt-failure.json').read_text())['passing_result'] for name in attempts)
    parser = json.loads((s/'attempt-initial-parser/parser-failure.json').read_text())
    assert parser['source_sha256'] == im.sha((s/'attempt-initial-parser/attempt-source.py').read_bytes())
    assert not parser['main_or_guest_execution_started']
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(ROOT))
    correction = {
        'created_utc':now, 'status':'LOCAL_MIPS_MEMORY_HOOK_REPLAY_CAUTION',
        'observed_engine':'Unicorn2.1.4 MIPS32_24KC on this Mac',
        'same_original_bytes_and_inputs':True,
        'no_hook_and_CODE_only_return_normally':True,
        'global_memory_hooks_reproduce_duplicate_entry_stack_shift':True,
        'exact_upstream_cause_or_all_architectures_affected_proven':False,
        'formal_observer':'CODE + invalid-access stops + whole-region postchecks; no read/write access trace.',
        'Sony_code_data_PC_results_or_runtime_returns_modified_to_pass':False,
        'historical_scope':'Retain historical MIPS traces; revalidate with corrected observation before extending new paths or relying on instruction counts/order. Current target/292-byte copy replayed here; other historical ranges not reaccepted.',
        'A64_or_static_evidence_invalidated_by_this_result':False,
        'background_primary_source':'https://github.com/unicorn-engine/unicorn/blob/master/docs/FAQ.md',
        'background_limit':'FAQ describes hook/PC sync and MIPS mappings; not evidence identifying this local failure as a specific upstream bug.',
    }
    im.write_json(s/'observer-scope-correction.json',correction)
    review = {
        'created_utc':now, 'status':'PASS_NATIVE_PENDING_DRAIN_AND_TIMING_COPY_WITH_CORRECTED_OBSERVATION',
        'prior_sealed_files_verified':15, 'cases':14, 'bounded_phases':24,
        'whole_QoS_dispatch_returns':12, 'pending_cleared_backend40_retained_cases':4,
        'timing8_copy_backend20000000_cases':2, 'unknown_GP_stop_cases':4,
        'CODE_only_whole_region_checks':True, 'global_memory_read_write_hooks_used_in_formal_run':False,
        'hardware_ack_valid_full_request_actual_initialization_Main_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False, 'goal_complete':False, 'persistent_write_release':False,
        'review_scope':'Same agent original bytes/source/PC/poststate audit; no independent emulator implementation or camera acceptance.',
    }
    im.write_json(s/'completed-evidence-review.json',review)
    im.write_json(s/'summary.json',review)
    im.write_json(s/'coordinator-observations.json',{
        'recorded_utc':now, 'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage79 sealed15 files/canonical verified; pending after independent lower copy remained1, timing entry stopped.',
        'new_evidence':'Upper original fragment genuinely calls lower updater then clears pending; backend flags/output remain. Full timing helper existing-handle copy returns. Observer matrix identifies local memory-hook-dependent stack divergence; corrected observation replay passes.',
        'Windows_UU_actions_this_turn':0, 'camera_operations':False,
        'requirements_retained':16, 'goal_complete':False, 'persistent_write_release':False,
    })
    old = json.loads(before)
    g = json.loads(before)
    g['updated_utc'] = now
    g['latest_stage'] = s.name
    g['research_activity'] = 'Mac_only_native_pending_drain_timing_transfer_and_MIPS_observer_scope_correction'
    g['progress_audit'] = {
        'classification':'progress', 'previous_goal_turn_classification':'progress',
        'basis':[
            'stage79封存15件/canonical复核。未改Sony字节/C原型/返回值；先隔离本机Unicorn MIPS全局内存钩子触发的重复入口/栈偏移。无钩子/CODE-only正常，正式改用代码白名单+全页/输出/栈窗口外核对，不声称逐次内存访问轨迹。',
            '原QoS消费后独立上层190888真实调用19bda4并返回1908c0，1908cc清pending；292字节参数及后端40位仍在，不能当硬件完成/安全回收。4例确认，关闭更新不调用，无句柄在GP前停并保留pending1。',
            '原1a085c已有声明句柄分支完整复制8008/240000原8字节到缓冲7d0并置后端20000000，外层pending仍0；另一无句柄GP前停。字段正式单位/实际29.97与精确30未证。',
            '14例24阶段通过；历史失败/源码/矩阵保留并登记观察范围更正。无真实初始化/分配/物理映射/硬件回执/全Start/成片或同机恢复，16项和Mac-only授权不变。',
        ], 'completion_not_claimed':True,
    }
    g['latest_stage_evidence']['stage80_vcd_pending_and_timing'] = {
        'readme':rel+'/README.md', 'review':rel+'/completed-evidence-review.json',
        'result':rel+'/run-final-observer-20261026/pending-timing-results.json',
        'observer_correction':rel+'/observer-scope-correction.json', 'observer_matrix':rel+'/observer-matrix.json',
        'scope':'Declared RAM/handle; complete timing copy and independent upper drain fragment before outer epilogue. Pending0 is not hardware completion. CODE-only with postchecks, no R/W traces.',
        'authorization_unchanged':True, 'goal_complete':False,
    }
    g['corrections_to_prior_stage']['MIPS_global_memory_hook_observation_scope'] = {
        'evidence':rel+'/observer-scope-correction.json',
        'correction':'本机原尾参数路径在全局内存读写钩子下出现重复入口/栈偏移，无钩子或CODE-only正常。新路径/计数顺序推论前复核历史MIPS动态记录；不认定Sony固件缺陷、不扩大到A64或所有历史结论。',
        'current_run':'CODE-only+无效访问停点+全区域前后核对；不采集逐次内存访问。真实目标/292复制在本轮重放，未重跑范围不新增通过声明。',
    }
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G16'):
            req['evidence'].extend([rel+'/run-final-observer-20261026/pending-timing-results.json',rel+'/observer-scope-correction.json'])
            req['stage80_scope'] = '修正MIPS观察后原上层清pending但后端40/参数保持；原尾参数8字节复制并置后端20000000。14例24阶段，声明句柄/状态，无真实分配/硬件回执/主录或恢复；pending0不能单独作回收/恢复门禁。'
    g['next_safe_offline_actions'].append(
        'stage80继续后端40/20000000更新位、共享缓冲真实owner/消费者及提交/回复/清除条件，不能以外层pending0回收/恢复。尾8008/240000原字节已转交，但真实字段单位/硬件时序待证。MIPS后续用已复核CODE-only+完整内存前后检查；历史全局R/W钩子结果跨新路径或计数推论前复核，保留所有静态/A64和实际实机/同机恢复要求。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16
    assert [(x['id'],x['status']) for x in g['requirements']] == [(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g)
    after = (s/'goal-status-after.json').read_bytes()
    index = ROOT/'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3 待处理标志与尾参数转交](<work/sony-firmware-20261024/stage80-vcd-pending-and-timing/README.md>)：pending清零而后端更新仍在，完整尾参数复制；修正本机MIPS观察钩子影响，14例24阶段。硬件/主录/恢复未证，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n') == 1
    ia = ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    files = [{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
             for p in sorted(s.rglob('*')) if p.is_file()]
    final = {
        'schema':'fx3-stage80-vcd-pending-timing-observer/1', 'created_utc':now,'volume_uuid':im.VOLUME,
        'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':review,'requirements_retained':16,'authorization_unchanged':True,
    }
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((ROOT/x['path']).read_bytes()) == x['sha256'] for x in files)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'hardware_recording_or_recovery_proven':False,'goal_complete':False}))


if __name__ == '__main__':
    main()
