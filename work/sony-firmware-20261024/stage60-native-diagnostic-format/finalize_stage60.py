#!/usr/bin/env python3
"""Review existing native text/timer receipts and seal once, without replay."""
import ast
import collections
import datetime
import json
import struct
from pathlib import Path
import diagnostic_format as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-native-string-stream-20261026';path=run/'diagnostic-format-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'diagnostic_format.py'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    obj=f.prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    assert im.sha(obj.read_bytes())==receipt['wrapper_object_sha256']
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    context=struct.unpack_from('<Q',blob,0x126e0)[0]
    assert context==f.V+0xbf8478 and 0<=context-f.V<len(blob)-64
    first=struct.unpack_from('<Q',blob,context-f.V)[0];assert first==f.V+0x38f4f8
    cases=p['cases'];assert len(cases)==4
    assert [(c['seed'],c['independent_output_limit']) for c in cases]==[(0xa5,236),(0xc3,236),(0xc3,32),(0xc3,0)]
    events=[e for c in cases for e in c['events']]
    assert len(events)==p['bounded_fragments']==20
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':4,
      'returned':12,'boundary: before_original_unmapped_timer_MMIO_read':4}
    # The string stream helper also has general external-I/O branches. Confirm
    # these actual string-format cases never execute its indirect call sites.
    md=f.r.capstone.Cs(f.r.capstone.CS_ARCH_ARM64,f.r.capstone.CS_MODE_ARM);md.skipdata=True
    indirect={hex(i.address) for i in md.disasm(blob[0x11e68:0x12268],f.V+0x11e68) if i.mnemonic=='blr'}
    assert indirect
    text0=None
    for c in cases:
        assert len(c['events'])==5 and c['events'][3]['stop_pc']==hex(f.V+0x29f6d4)
        timer=c['timer_boundary']
        assert timer=={'pc':hex(f.V+0x29f6d4),'base_X9':'0xfffffffff3400000','offset_X8':'0x2108',
          'effective_address':'0xfffffffff3402108','load_instruction_executed':False,
          'register_or_MMIO_return_adapter':False}
        prefix=c['events'][3]['pcs']
        ordered=[f.V+0x27d7d0,f.V+0x27d808,f.V+0x27d32c,f.V+0x27d34c,
          f.V+0x2a4588,f.V+0x2a459c,f.V+0x29f6c8,f.V+0x29f6d4]
        positions=[prefix.index(hex(pc)) for pc in ordered];assert positions==sorted(positions)
        crt=c['events'][4];assert crt['reason']=='returned' and crt['SP_after']==hex(f.r.STACK+0x3000)
        assert int(crt['x0_after'],16)==c['native_CRT_return_length']==146
        assert {hex(f.V+x) for x in (0x126a8,0x125c0,0x17040,0x1d3f8,0x17028,0x11e68)}<=set(crt['pcs'])
        assert not set(crt['pcs'])&indirect
        assert c['source_view_va_list_and_spill_slots_unchanged']
        assert c['independent_formatter_not_continuous_resume_after_MMIO_or_clock_result_adapter']
        assert c['hardware_timer_or_complete_logger_header_output_backend'] is False
        assert c['original_context_pointer_from_literal']==hex(context)
        va=c['native_va_list'];raw=bytes.fromhex(va['raw32_hex'])
        fields=struct.unpack('<3Q2i',raw);assert fields[-2:]==(0,-128)
        assert [hex(x) for x in fields[:3]]==[va['stack'],va['gr_top_unconsumed_with_gr_offs0'],va['vr_top']]
        assert int(va['pointer'],16)>f.r.STACK+0x3000
        text=f.expected_text(c['native_log']);assert len(text)==146
        assert c['reference_text_for_comparison_only']==text.decode()
        if text0 is None:text0=text
        assert text==text0
        output=bytes.fromhex(c['native_output256_hex']);assert len(output)==256
        limit=c['independent_output_limit']
        if limit:
            keep=min(146,limit-1)
            assert output[:keep+1]==text[:keep]+b'\0'
            assert output[keep+1:]==bytes([0x5a])*(255-keep)
        else:assert output==bytes([0x5a])*256
    for e in events:
        assert not e.get('native_output_or_PC_return_adapter',False) and not e.get('native_output_or_return_adapter',False)
    for reg in p['original_regions']:
        for ins in reg['instructions']:
            at=int(ins['va'],16)-f.V;assert blob[at:at+4].hex()==ins['bytes']
    failure=json.loads((stage/'run-20261026/attempt-failure.json').read_text())
    failed=json.loads((stage/'run-20261026/last-phase-at-failure.json').read_text())
    assert not failure['passing_result'] and failed['reason']=='unapproved execution '+hex(f.V+0x17028)
    assert (stage/'run-20261026/attempt-source.py').is_file()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'scope':'Original enabled-log prefix to first unexecuted timer load; separate native built-in formatter call on actual original va_list/format and file-backed CRT context.',
      'direct_formatter_chain_is_internal126a8_125c0_17040_not_new_kernel_printf_provider':True,
      'no_assertion_all_firmware_formatting_or_CAPI_is_internal':True,
      'timer_effective_model_address':'0xfffffffff3402108','timer_read_or_actual_MMU_physical_mapping_observed':False,
      'original_file_context_pointer':hex(context),'file_context_first_pointer':hex(first),
      'CRT_context_and_locale_not_host_constructed_or_version_identified':True,
      'text_formatter_is_independent_entry_on_lower_stack_not_resume_of_full_logger':True,
      '146byte_output_normal_truncated_zero_capacity_and_A5C3_controls_proven':True,
      'string_stream_external_indirect_IO_call_sites_not_executed':sorted(indirect),
      'complete_log_header_output_async_lifetime_and_global_pointer_escape_unproven':True,
      'next_scope':'Audit original log-output copying/registration and lifetime independently of unread hardware time; continue post-match channel/private16M integration, actual runtime mapping/sync and all physical/recovery requirements.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    im.write_json(stage/'summary.json',{'created_utc':now,'status':p['status'],'bounded_fragments':20,
      'original_stop_counts':dict(counts),'native_text_length':146,'limits':[236,236,32,0],
      'timer_load_executed':False,'full_enabled_log_or_hardware_or_recovery':False,
      'proof_sha256':im.sha(path.read_bytes()),'goal_complete':False,'persistent_write_release':False})
    im.write_json(stage/'coordinator-observations.json',{'created_utc':now,
      'reviewer':'Same-agent source/original-byte/trace/hash review, no independent implementation or device replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'prior_stage20sealedfiles_and_canonical_verified':True,
      'new_code_observer_has_no_guest_memory_register_PC_or_MMIO_result_writes':True,
      'actual_timer_address_computed_and_instruction_stopped_before_read':True,
      'internal_native_formatter_uses_original_file_context_and_native_generated_va_list':True,
      'host_reference_is_only_comparison_never_guest_output':True,
      'full_truncated_zero_limit_outputs_and_untouched_input_slots_checked':True,
      'no_external_string_stream_virtual_IO_site_executed':True,
      'original_image_normalized_only_known_import_BL_logger_fixture_bytes_compared':True,
      'initial_missing_helper_execution_range_failure_and_source_preserved':True,
      'no_whole_enabled_logger_or_hardware_or_recovery_claim':True,
      'UU_Windows_camera_or_protocol_operations':False,
      'outcome':'PASS_ORIGINAL_TEXT_COMPONENT_WITH_HARDWARE_TIME_AND_COMPLETE_LOG_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      'stage59封存20件和canonical复核后，核对格式化直接调用为映像内126a8→125c0→17040，原文件上下文bf8478及只读首指针有效，不另外链接内核printf替身。',
      '启用诊断原路径进入27d7d0/时间头，到原29f6d4前真实算出模型有效地址fffffffff3402108；该读未执行、未映射假寄存器或编造时钟值。',
      '保留原格式串/实际va_list及槽，独立低栈运行原内部格式化：A5/C3容量236、容量32截断和容量0均返回146，输出边界及原source/view/va_list/spills保持。',
      '20段原执行，内部字符串流未进入外部I/O间接调用。Python只作参考比较，不写客体输出。首次未批准17028 helper失败保留，审原分支后补范围。',
      '文本组件独立调用不是越过MMIO继续完整日志；实际时间/MMU映射、日志头与输出后端/全局指针寿命、共享同步/owner代次/实际loader、私有16M真实接合和全部硬件/同机恢复仍缺。',
      '不重连UU/Windows，保持最后显式断连/离线与仅虚拟屏1/传输限制；全部16要求和相机授权不变。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage60_native_diagnostic_format']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'scope':'Enabled native logger prefix reaches unexecuted timer load; independent native internal formatter produces146bytes on real native varargs and original context with truncation/zero capacity controls. No full enabled logger/Hal/device/recovery.',
      'bounded_fragments':20,'native_text_length':146,'hardware_time_and_complete_log_proven':False,
      'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['diagnostic_formatter_provider_and_time_scope']={
      'stage59_next_hypothesis':'Find actual formatter CAPI provider.',
      'new_evidence':'Examined text chain is direct internal126a8/125c0/17040 with original file-backed context; header time separately reads an unmapped modeled register address. Native text can run independently without a new kernel formatter provider.',
      'not_full_enabled_logger_or_actual_time_mapping':True,'old_files_preserved':True,
      'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage60启用原诊断到首个时间LDR前计算fffffffff3402108模型地址，未读/未模拟MMIO。原内部126a8→125c0→17040使用原文件上下文和实际原va_list独立生成146字节，A5/C3、32截断、0容量对照通过，输入源/视图/槽不变。20段执行不含完整时间头或日志输出；实际时间/MMU/异步寿命/同步/owner代次、私有16M后选择真实接合与所有硬件/同机恢复仍待验收。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='核对原日志输出后端的复制/登记与数据寿命，独立于未读取的硬件时间验证；继续原匹配后行选择/通道准备和私有16M预置真实调用接合。保持实际时钟/MMU/loader/代码发布同步/owner代次及全部主录/音画长录/同机备份恢复和独立救援要求，不以独立文本输出代替完整启用日志。'
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();text=idxbefore.decode()
    entry='- [2026-10-26 FX3 原内部诊断文本与时间边界](<work/sony-firmware-20261024/stage60-native-diagnostic-format/README.md>)：原实际va_list经内部格式化产146字节，20段含截断/零容量通过；完整日志停未读时间寄存器，硬件/同步/成片与恢复仍未验收。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    idxafter=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage60-native-diagnostic-format/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'scope':'Original native enabled-log prefix stopped before timer LDR plus independent internal native text formatting. No fake clock/kernel printf, complete log/backend/device or recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_firmware_file_unchanged':True,'prior_guest_BL_and_logger_fixture_changes_declared':True,
        'native_formatter_clear_log_return_PC_or_MMIO_result_adapter':False,
        'Sony_loadable_module_or_firmware_exported':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'bounded_fragments':20,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
