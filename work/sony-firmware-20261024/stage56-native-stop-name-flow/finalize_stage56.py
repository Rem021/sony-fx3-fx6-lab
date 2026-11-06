#!/usr/bin/env python3
"""Check existing original-code receipts and seal once, without rerunning them."""
import ast
import collections
import datetime
import json
from pathlib import Path
import stop_name_flow as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-cross-library-link-20261025';path=run/'stop-name-flow-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    assert p['status']=='PASS_ORIGINAL_EMPTY_NAME_STOP_AND_CLIP_SUFFIX_WITH_EXPLICIT_BOUNDARIES'
    source=stage/'stop_name_flow.py'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    tree=ast.parse(source.read_text())
    for fn in ast.walk(tree):
        if not isinstance(fn,ast.FunctionDef) or fn.name!='code':continue
        writes=[x for x in ast.walk(fn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
          and x.func.attr in ('reg_write','mem_write')]
        assert len(writes)==1 and writes[0].func.attr=='reg_write'
        assert isinstance(writes[0].args[0],ast.Attribute) and writes[0].args[0].attr=='UC_ARM64_REG_PC'
        assert isinstance(writes[0].args[1],ast.Name) and writes[0].args[1].id=='target'
    assert 'self.ret(' not in source.read_text() and 'logging_adapter=True' not in source.read_text()
    extraction=json.loads((stage/'official-extraction-receipt.json').read_text())
    assert im.sha((stage/'official-extraction-receipt.json').read_bytes())==receipt['extraction_receipt_sha256']
    for row in extraction['files']:
        assert im.sha((root/row['output']).read_bytes())==row['sha256']
        assert row['file_entry']['type']==0x8000 and row['symlink_entry']['type']==0xa000
    assert receipt['MPR_sha256']=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    assert receipt['prior_manifest_sha256']==f.PRIOR_SHA
    for lib in (f.LIBC,f.CPP):
        assert lib.receipt() in receipt['runtime_libraries']
        assert all(x['type']=='STT_FUNC' for x in lib.receipt()['approved_original_functions'].values())
    events=p['original_default_map_key_events']+[e for c in p['cases'] for e in c['events']]+p['callback_binding']['events']+[p['allocation_denial_control']]
    assert len(events)==p['original_fragments']==50
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'returned':28,'boundary: after_selected_StopCmp_copy_before_completion_logic':8,
      'boundary: after_65byte_clip_name_copy':4,'boundary: before_unrecognized_writer_diagnostic':4,
      'boundary: before_original_diagnostic':2,'boundary: before_factory_allocation':1,
      'boundary: before_full_registration':1,'boundary: after_registration_before_allocation':1,
      'unapproved PLT '+f.PREFIX+'9_M_createERmm':1}
    native_links=[]
    for e in events:
        assert not e['native_output_printf_allocator_PC_return_adapter']
        assert not any('stub' in call or 'logging_adapter' in call for call in e['calls'])
        if e['reason']=='returned':assert e['SP_after']==hex(f.pp.STACK)
        for call in e['calls']:
            if 'original_library_target' not in call:continue
            native_links.append(call)
            assert call['partial_link_only_no_synthesized_return']
            lib=next(x for x in (f.LIBC,f.CPP) if im.sha(x.blob)==call['library_sha256'])
            name=call['symbol'];assert name in lib.allowed_names
            assert call['original_library_target']==hex(lib.symbols[name]['va'])
    cases=p['cases'];assert len(cases)==4
    assert [c['native_name_ascii'] for c in cases]==['','','CONTROL','']
    assert cases[0]['metadata_fields']==cases[1]['metadata_fields']
    for c in cases:
        fields=c['metadata_fields']
        assert fields['width_height_3c_3e']==[1920,1080] and fields['bitrate_raw40']==16000
        assert fields['rate_2c_30']==fields['rate_34_38']==[30000,1001]
        assert fields['valid_byte0']==1 and fields['record_format_enum4']==5 and fields['alternate_classifier_byte46']==0
        name=c['native_name_ascii'].encode();seed=c['prior_seed']
        assert bytes.fromhex(c['native_name_output_128_hex'])==name+bytes(128-len(name))
        formatter=c['events'][4]
        assert formatter['entry']=='0x117b20' and formatter['return_u64']==0
        assert {'return_instruction':'0x24d7d0','return_x0':'0x97'} in formatter['calls']
        assert {'return_instruction':'0x117ba4','return_x0':'0x0'} in formatter['calls']
        assert any(call.get('symbol')=='strncpy' for call in formatter['calls'])
        main,proxy,wrong=c['owner_copy_controls']
        assert (main['uid'],proxy['uid'],wrong['uid'])==(1,5,2)
        for owner in (main,proxy):
            copied=bytes.fromhex(owner['copied_name_128_hex'])
            assert copied==name+bytes(127-len(name))+bytes([seed])
            assert owner['other_name_field_unchanged'] and owner['native_completion_flag_set']
        clip=main['clip_info_suffix'];assert bytes.fromhex(clip['65byte_name_hex'])==name+bytes(65-len(name))
        assert clip['separate_codec_scalar_6a8_unchanged'] and clip['codec_scalar_producer_not_executed']
        assert wrong['record_unchanged'] and wrong['copied'] is False
    assert any(call['symbol']=='memcpy' and call['PLT']=='0x160897b0' for call in native_links)
    binding=p['callback_binding']
    assert binding['callback_va']=='0xda760' and binding['event']=='0x40000001'
    assert binding['native_named_receiver']=='_ZN3mpr20RecvWriterEvtStopCmpEmjiPvjS0_'
    assert binding['events'][3]['native_named_entries'][0]['entry']=='0xda760'
    assert binding['events'][4]['native_named_entries'][0]['entry']=='0xda3b4'
    for reg in p['original_regions']:
        for ins in reg['instructions']:
            assert f.MPR.read(int(ins['va'],16),len(bytes.fromhex(ins['bytes']))).hex()==ins['bytes']
    init={ins['va']:ins['asm'] for ins in p['original_regions'][0]['instructions']}
    assert init['0x8ef38']=='mov w0, #0x97' and init['0x8ef40']=='adrp x1, #0x2cf000'
    assert init['0x8ef44']=='add x1, x1, #0xb4f' and init['0x8ef54']=='bl #0x2428a4'
    assert f.MPR.read(0x2cfb4f,1)==b'\0'
    failure=json.loads((stage/'run-20261025/attempt-failure.json').read_text())
    failed_phase=json.loads((stage/'run-20261025/last-phase-at-failure.json').read_text())
    assert failure['passing_result'] is False and failed_phase['reason']=='unapproved execution 160897b0'
    assert failed_phase['label']=='original std::string constructor from artificial short-name control'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'observed_formatter_callsite_scope':'MPR120784 optional Stop completion record, not proof about all exported callers/consumers.',
      'official_default_enum97_empty_literal':{'literal_va':'0x2cfb4f','constructor_call':'0x8ef54'},
      'original_default_map_and_single_entry_name_vector_are_declared_fixtures':True,
      'global_construction_heap_allocation_actual_camera_state_unexecuted':True,
      'actual_factory_callback_load_registration_and_indirect_entry_fragments':True,
      'factory_allocation_and_constructor_not_executed_owner_pointer_fixture':True,
      'post_lock_dispatch_is_independent_input_not_actual_lock_success_or_resume':True,
      'record_owner_UIDs_are_post_lookup_fixtures_not_real_recorder_binding':True,
      'empty_name_MAIN_PROXYSuffix65_clip_name_flow_proven_in_scope':True,
      'strncpy127_leaves_byte127_outside_copy_not_real_uninitialized_bug_claim':True,
      'MAIN_clip_codec_scalar_source_and_complete_ClipInfo_function_not_executed':True,
      'no_full_Stop_or_MP4_close_commit_XML_catalog_player_file_validation':True,
      'empty_name_globally_harmless_or_cannot_affect_recording':False,
      'next_scope':'Prioritize upper16M/FH-to-resourceFF consistency without relabeling HD as UHD; retain downstream file/readback and every physical/recovery requirement.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    im.write_json(stage/'summary.json',{'created_utc':now,'status':p['status'],'original_fragments':50,
      'original_stop_reasons':dict(counts),'native_runtime_link_calls':len(native_links),
      'target_metadata_fields':cases[0]['metadata_fields'],'names':[c['native_name_ascii'] for c in cases],
      'observed_stop_callback':binding['native_named_receiver'],'event':binding['event'],
      'first_cross_library_linker_denial_preserved':True,
      'empty_name_globally_harmless_proven':False,'full_writer_or_real_recording_or_recovery':False,
      'proof_sha256':im.sha(path.read_bytes()),'goal_complete':False,'persistent_write_release':False})
    im.write_json(stage/'coordinator-observations.json',{'created_utc':now,
      'reviewer':'Same-agent source/original-byte/trace/hash review, no independent implementation or device replay.',
      'previous_goal_turn_classification':'no_progress_status_only',
      'previous_no_progress_revalidated_by_unchanged_stage55_canonical_and_sealed11files':True,
      'this_goal_turn_classification':'progress',
      'source_executed_copy_library_hashes_static_literal_native_returns_and_controls_reviewed':True,
      'new_code_hook_only_PC_to_original_allowlisted_symbol_no_outputs_or_PC_to_LR':True,
      '50fragments_28returns_21boundaries_1expected_allocator_denial_verified':True,
      'first_cross_library_link_failure_and_source_preserved':True,
      'runtime_provider_functions_are_original_STT_FUNC_not_IFUNC_or_host_adapters':True,
      'official_code_PF_X_bytes_compared_after_guest_runs':True,
      'full_state_owner_sync_MP4_actual_hardware_and_restore_unverified':True,
      'UU_Windows_camera_or_protocol_operations':False,
      'outcome':'PASS_LOCAL_NATIVE_NAME_STOP_FLOW_WITH_PHYSICAL_AND_CONSUMER_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    oldg=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name
    g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'no_progress',
      'basis':[
        '上轮仅状态汇报；核验stage55清单11件及canonical一致后推进原执行，未把状态复述当进展。',
        '同版官方ext2提取libc/libstdc++，原STT_FUNC字符串/内存函数部分链接，原可执行段逐段保持；无输出/日志/锁/分配器/返回替身。',
        '原完整名称函数对HD29.97/raw16000和声明默认map/名称向量返回0及空名称；A5/C3一致，短CONTROL及错key对照排除恒空替身。',
        '原工厂指针/登记片段绑定da760；原事件40000001间接调用进入它，独立后锁分派进入RecvWriterEvtStopCmp，均停首诊断，不是完整Stop。',
        '后查找声明归属上MAIN1/PROXY5复制127字节，错UID2不写；MAIN媒体资料独立后缀复制65字节。空名后续文件提交/目录/XML/播放效果仍未知。',
        '50段原执行、28原返回、21显式边界及1预期分配拒绝；首版跨库链接失败保留，修实验链接器后通过。资源FH与上层16M身份桥接及全部实机/恢复要求仍缺。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage56_native_stop_name_flow']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json',
      'refinement':rel+'/scope-refinement.json','official_extraction':rel+'/official-extraction-receipt.json',
      'scope':'Original complete formatter with original runtimes; independent callback registration/dispatch and post-lookup StopCmp/clip-name suffixes on explicit fixtures. No full Stop, file commit, actual Open/Start/Hal or recovery.',
      'original_fragments':50,'observed_callback_receiver':'RecvWriterEvtStopCmp',
      'empty_name_global_effect_known':False,'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['default97_name_and_completion_scope']={
      'previous_stage55_open_question':'Default97 actual descriptive/admission/container effect unresolved.',
      'new_scope':'Observed formatter caller feeds optional Stop completion metadata; original formatter returns0 and empty name flows to MAIN/proxy records and MAIN clip name suffix under explicit fixtures. Not an Open admission predicate.',
      'not_global_harmless_or_real_file_recording_proof':True,
      'global_ctor_log_lock_real_owner_lookup_and_full_Stop_unexecuted':True,
      'old_files_preserved':True,'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage56同版原libc/libstdc++部分链接完成完整名称函数：声明默认map/单项名称向量上HD29.97/raw16000分类97、空名称、返回0；CONTROL/错key及A5/C3对照通过。原登记/间接回调和独立后锁分派绑定40000001→RecvWriterEvtStopCmp；后查找MAIN/proxy复制127字节，错UID不写，MAIN资料后缀复制65字节。不是Open准入；完整Stop/锁/真实查找/MP4关闭提交/XML目录播放效果仍未知。50段原执行不构成实际成片或恢复；FH→FF受限资源身份桥接、完整Start/Hal与全部实机/同机恢复要求保留。'
    for req in g['requirements']:
        if req['id'] in ('G02','G03','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='优先研究保持上层VQuality6/raw16000的受限资源FH→FF桥接及私有预置应用，核对真实MAIN选择、owner/epoch/同步与query/cache/mux一致性；已追名称调用属于Stop资料，保留完整文件关闭/目录/XML/播放下游验证，不给HD强套UHD名称；全部备份恢复/实机Open/Start/Hal与成片验收不变。'
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==oldg[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 空名称与结束资料原路径](<work/sony-firmware-20261024/stage56-native-stop-name-flow/README.md>)：同版原运行库支撑50段有界执行，空名进入StopCmp及MAIN资料；不据此判Open失败或全局无害，资源16M桥接、完整成片与同机恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage56-native-stop-name-flow/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'scope':'50 bounded native fragments with original same-version libc/libstdc++. Full formatter and independent StopCmp/clip suffixes, explicit input fixtures and denied log/lock/allocation. No actual file/hardware/recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_MPR_and_runtime_executable_code_unchanged':True,
        'map_vector_owner_and_independent_fragment_inputs_are_fixtures':True,
        'native_output_log_lock_allocator_or_PC_return_adapter':False,
        'new_loadable_camera_module':False,'empty_name_proven_globally_harmless':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':50,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
