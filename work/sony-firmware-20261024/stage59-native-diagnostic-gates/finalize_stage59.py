#!/usr/bin/env python3
"""Review conditional original diagnostic receipts; seal once without replay."""
import ast
import collections
import datetime
import json
from pathlib import Path
import diagnostic_gates as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-real-clear-trace-20261026';path=run/'diagnostic-gates-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'diagnostic_gates.py'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    obj=root/p['wrapper_object_source'];assert im.sha(obj.read_bytes())==p['wrapper_object_sha256']==receipt['wrapper_object_sha256']
    assert receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    cases=p['cases'];assert len(cases)==8
    events=[e for c in cases for e in c['events']]
    assert len(events)==p['bounded_fragments']==31 and p['actual_contiguous_matcher_returns']==6
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':8,'returned':15,
      'boundary: after_actual_matcher_return_before_caller_diagnostic':6,
      'boundary: before_unexecuted_diagnostic_formatter':1,'boundary: before_unexecuted_logger_constructor':1}
    expected=[386,386,386,386,-1,431,None,None]
    assert [c['expected_row_if_returned'] for c in cases]==expected
    ptr_args=[]
    for i,c in enumerate(cases):
        e=c['events'][-1];bridge=c['wrapper_entry'];entered=c['real_matcher_entry']
        assert c['independent_post_diagnostic_copy_or_PC_return_adapter'] is False
        assert c['all_diagnostic_global_pointer_non_escape_or_actual_logger_state_proven'] is False
        assert c['state']['original_global_constructor_or_actual_camera_state'] is False
        for event in c['events']:
            assert not event.get('native_output_or_PC_return_adapter',False) and not event.get('native_output_or_return_adapter',False)
            if event['reason']=='returned':assert event['SP_after']==hex(f.r.SP)
        if i<6:
            assert c['one_contiguous_original_queued_to_matcher_return']
            assert c['actual_return_to_original_caller']==[{'pc':hex(f.prev.SITE+4),
              'W0':expected[i]&0xffffffff,'SP':bridge['SP']}]
            required=[f.V+0x225edc,f.V+0x27d528,f.V+0x27d564,f.V+0x225ee0,
              f.V+0x225f9c,f.V+0x27d568,f.V+0x27d5c8,f.V+0x27d624,
              f.V+0x225fa0,f.V+0x226124,f.prev.SITE+4,f.prev.SITE+8]
            # Read the ordered native trace, not just labels or status fields.
            positions=[e['pcs'].index(hex(pc)) for pc in required]
            assert positions==sorted(positions)
        else:assert not c['actual_return_to_original_caller']
        if i<7:
            assert c['native_logger_getter_returns']==[{'return_pc':hex(f.V+0x27d564),'actual_X0':hex(f.LOG)}]
            assert len(c['original_mute_setter_stores'])==1
            assert c['original_mute_setter_stores'][0]=={'pc':hex(f.V+0x27d8a0),'address':hex(f.MUTE),
              'size':1,'value':c['state']['original_setter_mute']}
            assert len(c['native_log_calls'])==1
            log=c['native_log_calls'][0];values=[int(x,16) for x in log['overflow_10words']]
            assert values[0]==f.V+0x43d0f2 and log['arguments_x0_x7'][0]==hex(f.LOG)
            assert int(entered['input_pointer'],16) not in values and int(bridge['source'],16) not in values
            assert entered['input_pointer'] not in log['arguments_x0_x7'] and bridge['source'] not in log['arguments_x0_x7']
            assert log['scalar_raw1c_width_height']==[x&0xffffffff for x in values[5:8]]
            if i in (0,1,2,3,6):
                assert log['original_literal_args']=={'1':'HEVC_MP4','2':'29_97','3':'PROGRESSIVE',
                  '4':'FF','8':'CHROMA_420','9':'BIT_DEPTH_10'}
                assert log['scalar_raw1c_width_height']==[0,1920,1080]
            ptr_args.append(log)
    assert cases[0]['native_log_calls'][0]['scalar_slot_upper32_not_scalar_value']==[0xa5a5a5a5]*3
    assert cases[1]['native_log_calls'][0]['scalar_slot_upper32_not_scalar_value']==[0xc3c3c3c3]*3
    muted=cases[0]['events'][-1]['pcs'];filtered=cases[2]['events'][-1]['pcs']
    assert hex(f.V+0x27d604) in muted and hex(f.V+0x27d628) not in muted
    assert hex(f.V+0x27d634) in filtered and hex(f.V+0x27d638) not in filtered
    enabled=cases[6]
    assert enabled['events'][-1]['stop_pc']==hex(f.V+0x27d7d0)
    assert len(enabled['native_formatter_entry_boundary'])==1
    assert hex(f.V+0x27d66c) in enabled['events'][-1]['pcs']
    assert hex(f.V+0x2f67c) in enabled['events'][-1]['pcs']
    # Executed-source assertions additionally inspect the exact original kernel
    # memset PC and256zero output bytes. Old clear observer is not in this class.
    assert "hex(m.exports['memset']['value']) in e['pcs']" in source.read_text()
    assert 'm.read(output,256)==bytes(256)' in source.read_text()
    assert cases[7]['events'][-1]['stop_pc']==hex(f.V+0x27d024)
    assert not cases[7]['native_log_calls'] and not cases[7]['original_mute_setter_stores']
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    for reg in p['original_regions']:
        for ins in reg['instructions']:
            at=int(ins['va'],16)-f.V;assert blob[at:at+4].hex()==ins['bytes']
    failed_paths=['run-20261026','run-native-gates-20261026','run-typed-varargs-20261026']
    for name in failed_paths:
        assert not json.loads((stage/name/'attempt-failure.json').read_text())['passing_result']
        assert (stage/name/'attempt-source.py').is_file()
    assert json.loads((stage/failed_paths[0]/'last-phase-at-failure.json').read_text())['reason']=='unapproved execution '+hex(f.V+0x225ee0)
    assert json.loads((stage/failed_paths[1]/'last-phase-at-failure.json').read_text())['stop_pc']==hex(f.prev.SITE+8)
    assert json.loads((stage/failed_paths[2]/'last-phase-at-failure.json').read_text())['stop_pc']==hex(f.V+0x27d7d0)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'scope':'Original diagnostic gates and complete original matcher on explicit initialized/mute/category fixtures, with the prior guest-only BL wrapper.',
      'initialized_guard_and_category_flags_host_fixtures_not_global_ctor_or_camera_observation':True,
      'mute_bit_written_by_original27d898_setter_not_host_log_return_adapter':True,
      'six_queued_to_native_caller_returns_are_contiguous_without_independent_post_log_state':True,
      'this_one_original_diagnostic_has_static_literal_and32bit_scalar_args_not_matcher_pointer':True,
      'all_diagnostics_global_pointer_escape_proven':False,
      '32bit_scalar_spill_high_halves_not_scalar_value_or_real_uninitialized_bug':True,
      'full_enabled_formatter_output_backend_and_logger_ctor_unexecuted':True,
      'current_module_MMU_shared_sync_owner_epoch_hardware_and_recovery_unproven':True,
      'next_scope':'Bind actual original formatter CAPI provider and output-path pointer lifetime before claiming enabled logger compatibility; continue actual post-match native channel preparation/private16M writer integration and every physical/recovery gate.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    im.write_json(stage/'summary.json',{'created_utc':now,'status':p['status'],'bounded_fragments':31,
      'contiguous_native_matcher_returns':6,'original_stop_counts':dict(counts),
      'conditional_return_rows':expected[:6],'formatter_and_constructor_controls_stop_as_expected':True,
      'target_native_diagnostic_literals':cases[0]['native_log_calls'][0]['original_literal_args'],
      'full_enabled_logs_or_actual_hardware_or_recovery_proven':False,
      'proof_sha256':im.sha(path.read_bytes()),'goal_complete':False,'persistent_write_release':False})
    im.write_json(stage/'coordinator-observations.json',{'created_utc':now,
      'reviewer':'Same-agent original-byte/source/trace/hash review, no independent implementation/device replay.',
      'previous_goal_turn_classification':'progress_incomplete_stage_with_verified_failed_execution',
      'this_goal_turn_classification':'progress',
      'restart_recovery_checked_stage58_18files_canonical_and_failed_stage59_receipts':True,
      'previous_failed_process_exit_confirmed_no_completed_stage_replayed_no_pending_user_request':True,
      'new_code_store_observers_have_no_guest_output_register_or_PC_writes':True,
      'original_setter_is_only_allowed_guest_logger_global_byte_write':True,
      'raw_image_compared_except_imports_one_guest_BL_and_declared4logger_bytes':True,
      'six_contiguous_returns_real_getter_literal_helpers_early_log_return_and_wrapper_epilogue':True,
      'enabled_control_has_original_kernel_memset_trace_and_zero_output_before_formatter':True,
      'old_unhooked_clear_counter_empty_not_evidence_clear_absent':True,
      'three_failed_experiments_source_and_receipts_preserved':True,
      'UU_Windows_camera_interfaces_or_protocol_operations':False,
      'outcome':'PASS_CONDITIONAL_NATIVE_DIAGNOSTICS_WITH_ENABLED_BACKEND_AND_PHYSICAL_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':[
        'Orca重启恢复先核验stage58封存18件/canonical及stage59失败回执；此前执行已失败退出，没有重复完成阶段或漏掉待答请求。',
        '声明initialized guard与类别位，原mute setter写logger+1908；原getter返回真实logger指针、原helper给字符串、原varargs/log早退分支完整执行，不补返回或独立跳过日志。',
        '31段有界执行包含6次从queued入口到原matcher及包装尾声/原caller的连续返回：目标A5/C3、类别过滤、人工FF、proxyFH、UHD为386/386/386/386/-1/431。',
        '此诊断10溢出槽及X0..7没有原/临时匹配指针，6文本是原字面量，标量按原STR W32位解码，保留高半旧值不当实机缺陷。',
        '启用控制真正经原kernel memset清256字节并停原formatter入口；guard0停原构造入口。初始化/完整启用日志/backend、全局无逃逸和实际同步/loader/MMU/owner代次、完整硬件与同机恢复仍缺。',
        '白名单中段、32位槽观察及未挂接旧clear计数器三份失败保留；当前作用域/16项要求和相机授权不变，UU不重连，只允许未来虚拟屏/传输。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage59_native_diagnostic_gates']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'scope':'Contiguous complete original matcher under explicit initialized/muted or filtered logger inputs; enabled formatter/constructor controls stop before unexecuted providers. No actual device logger state/full backend/Hal/recovery.',
      'bounded_fragments':31,'contiguous_native_returns':6,'actual_full_logger_or_hardware_proven':False,
      'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['conditional_native_diagnostics_vs_post_log_assumption']={
      'stage58_scope':'Independent copied post-diagnostic body; actual log effects unexecuted.',
      'new_scope':'Original getter/name/vararg/early-return logs execute continuously under declared initialized mute/filter states, then full matcher/compiled epilogue returns natively. This one diagnostic passes static strings/scalars, not the matcher view pointer.',
      'logger_guard_and_filters_not_actual_ctor_or_camera_state':True,
      'not_full_enabled_backend_or_global_pointer_escape_proof':True,
      'old_files_preserved':True,'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage59声明logger初始化guard/类别位并执行原静音setter后，原getter/名字helper/varargs与原早退日志连续运行，6案例原matcher/包装尾声自然返回，无独立后日志客体。该诊断参数只有原字面量与32位标量，没有直接匹配参数指针。31段通过；启用分支原kernel清256字节后停formatter，guard0停构造。真实logger状态/完整启用日志与后端、全局指针寿命/共同同步/owner代次/实际MMU装载、私有16M写者接合和全部硬件/同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='绑定原诊断formatter的CAPI provider，追启用日志的格式化/输出和潜在指针保留，不能把声明静音/过滤通过当实际相机配置；继续原调用者同步、匹配后行/通道准备与私有16M写者接合，并保留真实module/MMU/代码发布/owner代次和全部硬件/同机恢复要求。'
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-26 FX3 原诊断门控与连续匹配](<work/sony-firmware-20261024/stage59-native-diagnostic-gates/README.md>)：31段含6次原诊断早退条件下的完整matcher连续返回，参数为原字符串/标量；真实日志状态/开启后端/同步/硬件和恢复仍未验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage59-native-diagnostic-gates/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'scope':'Original initialized mute/filter diagnostic gates and full native matcher continuity on explicit data fixtures; enabled formatter/ctor boundaries. No current device logger state or hardware/recovery claim.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_firmware_file_unchanged':True,
        'guest_one_BL_and_explicit_logger_data_changes_declared':True,
        'native_log_result_PC_return_or_clear_adapter':False,
        'Sony_loadable_module_or_firmware_exported':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'bounded_fragments':31,'contiguous_returns':6,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
