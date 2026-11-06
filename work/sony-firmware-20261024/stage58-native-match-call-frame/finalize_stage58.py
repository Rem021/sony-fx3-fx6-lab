#!/usr/bin/env python3
"""Seal reviewed bounded call-frame receipts; no replay or camera access."""
import ast
import collections
import datetime
import json
from pathlib import Path
import match_call_frame as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-post-loader-patch-20261026';path=run/'match-call-frame-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'match_call_frame.py';cs=stage/'match_adapter.c'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    assert im.sha(cs.read_bytes())==im.sha((run/'compiled-source.c').read_bytes())==receipt['C_source_sha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store','observe_input_reads'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    obj=(run/'match_adapter.a64.o').read_bytes();code,ro,relocs=f.object_image(obj)
    assert len(code)==228 and len(ro)==136 and len(relocs)==4
    assert im.sha(obj)==p['prototype']['object_sha256'] and im.sha(code)==p['prototype']['text_sha256']
    assert relocs==p['prototype']['relocations']
    original_links=[x for x in relocs if x['symbol']=='sony_matcher']
    assert {x['type'] for x in original_links}=={282,283}
    assert all(x['target']==hex(f.ORIGINAL) for x in original_links)
    assert (stage/'expected_hd16m.inc').read_bytes()==(f.prev.STAGE/'expected_hd16m.inc').read_bytes()
    assert receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert blob[f.SITE-f.V:f.SITE-f.V+4]==f.branch(f.SITE,f.ORIGINAL,True)
    assert f.SITE+4-f.V<len(blob)<f.BRIDGE-f.V
    assert p['scope']['ONE_original_guest_BL_explicitly_redirected_not_pristine_guest_code']
    cases=p['cases'];assert len(cases)==5
    assert [x['native_matcher_row'] for x in cases]==[386,386,386,-1,431]
    assert [x['scope_alias_applied'] for x in cases]==[True,True,False,False,False]
    events=[e for c in cases for e in c['original_events']]
    assert len(events)==p['original_and_wrapper_bounded_fragments']==25
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':10,
      'boundary: before_unexecuted_diagnostic':10,'returned':5}
    for e in events:
        assert not e.get('native_output_or_PC_return_adapter',False) and not e.get('native_output_or_return_adapter',False)
        if e['reason']=='returned':assert e['SP_after']==hex(f.r.SP)
    for c in cases:
        bridge=c['wrapper_entry'];entered=c['real_matcher_entry']
        raw=bytes.fromhex(c['original_source98_hex']);argument=bytes.fromhex(c['real_matcher_argument98_hex'])
        assert len(raw)==len(argument)==152 and raw[:136]==bytes.fromhex(c['original_descriptor_hex'])
        assert c['original_call_instruction']==f.branch(f.SITE,f.ORIGINAL,True).hex()
        assert c['guest_only_replacement_BL']==f.branch(f.SITE,f.BRIDGE,True).hex()
        assert bridge['pc']==hex(f.BRIDGE) and bridge['owner']==entered['owner']==hex(f.p.COMMON)
        assert bridge['LR']==hex(f.SITE+4)
        source_ptr=int(bridge['source'],16);ptr=int(entered['input_pointer'],16)
        caller_sp=int(bridge['SP'],16);wrapper_sp=int(entered['SP'],16)
        returns=c['actual_native_return_to_original_caller']
        assert returns==[{'pc':hex(f.SITE+4),'W0':c['native_matcher_row']&0xffffffff,'SP':hex(caller_sp)}]
        assert caller_sp%16==wrapper_sp%16==0
        for w in c['wrapper_native_stores']+c['post_body_wrapper_native_stores']:
            assert f.BRIDGE<=int(w['pc'],16)<f.BRIDGE+len(code)
            assert f.r.STACK<=int(w['address'],16) and int(w['address'],16)+w['size']<=f.r.STACK+f.r.STACK_SIZE
        reads=c['read_events_during_original_matcher_body'];assert reads
        if c['scope_alias_applied']:
            assert [i for i,(a,b) in enumerate(zip(raw,argument)) if a!=b]==[0x38]
            assert raw[0x38]==4 and argument[0x38]==6
            assert ptr!=source_ptr and wrapper_sp<=ptr and ptr+152<=caller_sp
            assert f.BRIDGE<=int(entered['LR'],16)<f.BRIDGE+len(code)
            assert all(int(x['SP'],16)<ptr for x in reads)
            touched=set()
            for w in c['wrapper_native_stores']:
                at=int(w['address'],16);touched.update(range(max(0,at-ptr),min(152,at+w['size']-ptr)))
            assert touched==set(range(152))
            e=c['original_events'][-1]
            assert any(f.BRIDGE<=int(pc,16)<f.BRIDGE+len(code) for pc in e['pcs'])
        else:
            assert ptr==source_ptr and argument==raw and wrapper_sp==caller_sp
            assert entered['LR']==hex(f.SITE+4)
        assert c['diagnostics_excluded_and_post_body_is_independent_copied_state']
        assert c['global_pointer_non_escape_all_threads_and_all_consumers_proven'] is False
    failed=json.loads((stage/'run-20261026/attempt-failure.json').read_text())
    assert not failed['passing_result'] and 'native_initialization.py' in failed['traceback'] and 'in link' in failed['traceback']
    assert im.sha((stage/'run-20261026/match_adapter.a64.o').read_bytes())==im.sha(obj)
    # Retain the loader's original pristine-image check; application moved after
    # n.link, rather than editing the old source/assertion or its sealed files.
    text=source.read_text();assert text.index('load=n.link(m)')<text.index('m.uc.mem_write(SITE,m.patch)')
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'scope':'One modeled guest BL -> OUR compiled stack wrapper -> original matcher prefix, then independent copied post-log body -> real compiler epilogue/original caller.',
      'original_guest_callsite_changed_explicitly_original_firmware_file_unmodified':True,
      'guest_mapping_and_function_ABI_not_actual_camera_MMU_or_Sony_module_ABI':True,
      'caller_source_and_common_descriptor_unchanged_target_view_only_quality4to6':True,
      'host_does_not_supply_new_X19_view_or_matcher_return_in_post_body':True,
      'target_view_lifetime_observed_until_local_matcher_return_in_active_wrapper_frame':True,
      'excluded_diagnostics_neutrality_and_global_pointer_non_escape_unproven':True,
      'all_threads_code_exit_shared_sync_actual_owner_epoch_and_full_Open_unproven':True,
      'near_code_allocation_code_patch_publication_ICache_and_loader_unproven':True,
      'stage57_private16M_writer_not_integrated_by_this_wrapper':True,
      'next_scope':'Inspect original diagnostic argument passing/pointer retention and caller synchronization before coupling native post-match preparation to private16M writer; actual same-body runtime mapping/identity and recovery gates remain.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    im.write_json(stage/'summary.json',{'created_utc':now,'status':p['status'],'bounded_fragments':25,
      'original_stop_counts':dict(counts),'compiled_wrapper_bytes':228,'rodata_bytes':136,
      'single_guest_callsite':hex(f.SITE),'guest_wrapper_mapping':hex(f.BRIDGE),
      'target_and_control_rows':[x['native_matcher_row'] for x in cases],
      'actual_camera_address_module_or_full_matcher_not_proven':True,
      'proof_sha256':im.sha(path.read_bytes()),'goal_complete':False,'persistent_write_release':False})
    im.write_json(stage/'coordinator-observations.json',{'created_utc':now,
      'reviewer':'Same-agent original bytes/source/trace/object/hash review; no independent implementation or device replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'stage57_sealed23files_and_canonical_verified':True,
      'new_observer_hooks_no_guest_memory_register_or_PC_return_writes':True,
      'one_guest_BL_only_other_image_bytes_and_const_code_checked':True,
      'real_original_matcher_call_and_native_caller_return_and_SP_verified':True,
      'two_target_views_inside_compiler_active_frame_and_full152byte_store_coverage':True,
      'three_non_target_controls_use_original_pointer_and_original_rows':True,
      'excluded_logs_post_body_independent_no_full_continuity_claim':True,
      'first_loader_guard_failure_preserved_and_guard_not_weakened':True,
      'current_memory_registry_lines_shifted_safety_scope_rechecked':True,
      'UU_Windows_camera_or_protocol_operations_this_stage':False,
      'outcome':'PASS_LOCAL_CALL_FRAME_WITH_ACTUAL_MAPPING_SYNC_DIAGNOSTICS_AND_PHYSICAL_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      '核验stage57封存23件/canonical后，将原调用点21ed18的一个客体BL指向自编译包装函数，不修改原固件文件或其它客体代码/原表。',
      '包装函数C源码228字节机器码，在编译器栈中复制152字节并校验原FH目标/common/MAIN尾，目标副本只改quality4→6；其它输入传原指针。',
      '原queued Open连续进入包装函数及原匹配器前诊断；独立保存状态后正文保留真实X19临时指针，原返回经过编译尾声到21ed1c，W0/原W23=386，SP恢复原caller值。',
      '两组目标/A5C3及人工FF、proxyFH、UHD共25段验证：386/386/386/-1/431。目标参数152字节落活动176字节包装帧，正文读取在帧释放前；非目标原指针不变。',
      '首次原装载完整性断言拦住过早客体改动，失败源保留；改为先原检查后实验BL，未放宽原断言。诊断中性/指针全局无逃逸、代码发布/MMU/真实owner代次/锁、stage57写者接入及完整硬件/同机恢复仍缺。',
      '未重连UU或操作Windows；最后显式断连/离线状态保持，后续只允许虚拟屏1与UU传输，不影响用户实体屏游戏。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage58_native_match_call_frame']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'scope':'Single guest BL -> compiled local stack view -> actual original matcher and native caller return with explicitly separate post-diagnostic state. No real loader/MMU/synchronization/hardware or recovery.',
      'bounded_fragments':25,'actual_runtime_hook_and_temporary_view_global_safety_proven':False,
      'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['matcher_view_call_frame_scope']={
      'stage57_scope':'Host invokes compiled view on separate stack, then chooses X19=VIEW for independent matcher body.',
      'new_scope':'Guest original BL invokes compiled wrapper, compiler-generated stack view is real matcher argument; post body retains that actual pointer and real native return traverses compiler epilogue/original caller.',
      'not_full_matcher_or_real_patch_address_module_sync_or_global_pointer_lifetime':True,
      'original_guest_code_has_one_declared_callsite_change_not_pristine':True,
      'old_files_preserved':True,'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage58原21ed18客体BL接编译栈包装函数→真实原matcher；独立后诊断正文不再人工改X19，原返回经编译尾声到原调用者并恢复SP。A5/C3目标与3对照25段通过，目标152字节在176字节活动包装帧内，只有副本quality改6。单条客体代码改动明确声明，原文件不改；模型近地址不是实机地址。诊断中性/指针无逃逸、真实模块/MMU/代码发布缓存同步/owner代次/共同锁、私有16M写者真实接入及全部硬件与同机恢复仍未验收。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='核对原资源匹配诊断的参数/指针传递与外层调用同步，确定临时视图是否有本轮未覆盖引用；继续将原匹配后行选择/通道准备与私有16M写者接合。模型地址/ABI不代替同机实际加载映射、代码发布/缓存同步/当前owner代次与共同锁，全部实际Open/Start/Hal、成片和备份恢复要求不变。'
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();text=idxbefore.decode()
    entry='- [2026-10-26 FX3 原调用点与临时参数栈帧](<work/sony-firmware-20261024/stage58-native-match-call-frame/README.md>)：一个客体BL接编译包装函数，临时视图被原matcher读取并经真实尾声返回原caller；25段通过，诊断/实际装载/同步/硬件与恢复仍未验收。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    idxafter=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage58-native-match-call-frame/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'scope':'Single guest-callsite redirection and compiler-owned temporary stack view through original matcher/native caller return; excluded diagnostics and independent copied post-body. No actual code publication/ABI/MMU/device/recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_firmware_file_unchanged':True,'original_guest_BL_explicitly_changed':True,
        'other_original_guest_code_and_data_except_existing_import_binding_unchanged':True,
        'observer_native_output_PC_return_or_diagnostic_adapter':False,
        'Sony_loadable_module_or_firmware_exported':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'bounded_fragments':25,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
