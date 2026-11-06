#!/usr/bin/env python3
"""Review and seal stage50 once; no native replay, device or remote action."""
from pathlib import Path
import ast
import datetime
import json
import struct
import start_geometry as s


def main():
    im=s.im;im.volume();stage=s.STAGE;root=s.ROOT
    prior=s.v.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())==s.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((root/row['path']).read_bytes())==row['sha256']
    provider=s.c.n.STAGE/'final-receipt.json'
    assert im.sha(provider.read_bytes())==s.c.PRIOR_SHA
    for row in json.loads(provider.read_text())['files']:
        assert im.sha((root/row['path']).read_bytes())==row['sha256']
    proofpath=stage/'run-corrected-20261025/start-geometry-results.json'
    proof=json.loads(proofpath.read_text())
    executed=proofpath.parent/'executed-source.py';script=stage/'start_geometry.py'
    receipt=json.loads((proofpath.parent/'source-receipt.json').read_text())
    assert im.sha(script.read_bytes())==im.sha(executed.read_bytes())==receipt['script_sha256']
    ast.parse(script.read_text())
    for func in ast.walk(ast.parse(script.read_text())):
        if isinstance(func,ast.FunctionDef) and func.name in ('code','geometry_read'):
            for call in ast.walk(func):
                assert not (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and call.func.attr in ('reg_write','mem_write'))
    assert proof['original_A64_fragments']==76 and proof['original_MIPS_predicates']==6
    assert len(proof['cases'])==6 and proof['encoder_source_name']=='enc/imola_enc_state.cpp'
    assert proof['rejected_same_offset_source']['source_name']=='dec/imola_dec_state.cpp'
    summaries=[]
    for case in proof['cases']:
        raw=bytes.fromhex(case['start_input_hex'])
        chosen=case['selected_record_fixture']
        reads=[r['record_index'] for e in case['original_fragments'] for r in e.get('geometry_reads',[])]
        assert reads and set(reads)=={chosen}
        assert list(struct.unpack_from('<8H',raw,0xe0))==case['produced_geometry']
        assert not case['host_post_production_geometry_edit']
        if 'VCD_baseband_predicate' in case:
            assert case['common_geometry']==[1920,1080] and case['decoded_target']==16000000
            assert case['VCD_baseband_predicate']['native_v0']=='0x0'
            assert case['VCD_config_predicate']['native_v0']=='0x0'
            assert case['VCD_baseband_predicate']['original_code_and_input_unchanged']
            assert case['VCD_config_predicate']['original_code_and_input_unchanged']
            common=bytes.fromhex(case['common_hex']);codec=bytes.fromhex(case['codec_hex'])
            assert struct.unpack_from('<2I',common,0xc)==(1920,1080)
            assert all(codec[i]==0 for i in s.c.EXPECTED_UNWRITTEN)
        summaries.append({k:case.get(k) for k in ('label','produced_geometry','produced_f4_f8_fc',
          'geometry_rows_read','producer_stop','builder_prefix_stop','common_geometry','common_format','common_pitch')})
    a,b,c=proof['cases'][:3]
    for key in ('start_input_hex','common_hex','codec_hex'):
        assert a[key]==c[key]
    assert (a['common_format'],a['common_pitch'])==(13,2400)
    assert (b['common_format'],b['common_pitch'])==(14,2880)
    assert proof['cases'][3]['produced_geometry'][4:6]==[1280,720]
    assert proof['cases'][3]['producer_stop']=='boundary: before_unexecuted_diagnostic_acquire'
    assert all(z['builder_prefix_stop']=='boundary: before_unexecuted_diagnostic_acquire' for z in proof['cases'][4:])
    failure=json.loads((stage/'run-20261025/attempt-failure.json').read_text())
    assert not failure['passing_result']
    old=(stage/'run-20261025/attempt-source.py').read_text()
    assert '(0x246138,0x246150)' in old and '(0x246138,0x246154)' in script.read_text()
    avcam=(s.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(avcam)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    ins=im.dump(avcam,0x24614c,0x246154,s.V)
    assert ins[-1]['offset']=='0x246150' and ins[-1]['asm'].strip()=='ret'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary={'created_utc':now,'status':proof['status'],'A64_original_fragments':76,
      'MIPS_original_predicates':6,'cases':summaries,
      'original_selected_record_geometry_reaches_COMMON_without_host_output_repair':True,
      'actual_live_record_producer_MAIN_registration_full_flags_defaults_locks_logs_or_complete_Start':False,
      'hardware_encoding_files_audio_sync_longrun_backup_restore_or_independent_recovery':False,
      'proof_sha256':im.sha(proofpath.read_bytes()),'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    review={'created_utc':now,'reviewer':'same agent source/original-byte/trace/hash review; no independent implementation/replay',
      'previous_stage_files_verified':16,'provider_stage_files_verified':21,
      'executed_source_copy_and_receipt_match':True,
      'metadata_pointer_index_and_d18_selection_original_chain_verified_on_declared_fixtures':True,
      'native_reads_only_selected_record_and_unselected_mutation_has_no_output_effect':True,
      'native_produced_e8_ea_and_COMMON_c_10_match1920_1080_in3_positive_cases':True,
      'no_host_post_production_geometry_edit_or_native_output_return_adapter':True,
      'separate_post_diagnostic_guest_fixtures_not_continuous_action_execution':True,
      'shorter_source_padding_stop_not_claimed_rejection_or_full_success':True,
      'width_alignment_and_unsupported_format_reach_original_diagnostics':True,
      'paired_VCD_predicates_complete_and_return0_but_do_not_establish_bitrate_hardware':True,
      'same_offset_decoder_candidate_excluded_by_original_source_name':True,
      'first_failure':{'path':'run-20261025/attempt-failure.json',
        'initial_trace_does_not_save_exact_stopping_PC':True,
        'source_review_finding':'Original second getter returns at246150; initial whitelist ended before it. Extend exclusive end to246154; no instruction or return replacement.',
        'corrected_run_saved_separately':True,'failed_source_preserved':True},
      'host_space_observation':{'shell_here_document_failed_before_Python':True,
        'observed_internal_available':'116Mi','observed_external_available':'393Gi',
        'observed_private_tmp_usage':'36G','resolution':'Run task scripts directly from verified external task directory; no unrelated temporary/history/backup deletion.'},
      'all_source_records_owners_current_MAIN_index_epochs_default_query_flags_and_actual_register_mapping_still_unbound':True,
      'no_UU_Windows_active_camera_or_driver_module_WBI_flash_operation':True,
      'review_outcome':'PASS_WITH_EXPLICIT_LIVE_METADATA_FULL_START_AND_DEVICE_GAPS'}
    im.write_json(stage/'coordinator-observations.json',review)
    statuspath=s.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert statuspath.read_bytes()==before==(s.v.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);oldg=json.loads(before);rel=str(stage.relative_to(root));ev=str(proofpath.relative_to(root))
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':oldg['progress_audit']['classification'],
      'basis':[
        '绑定enc/imola_enc_state.cpp原setter/getter、元数据数组+18、启动事件索引+14、stride d18选择和原几何打包；排除同偏移的解码器候选。实际记录来源/MAIN登记仍是缺口。',
        '原指令将选中记录+3e/+40生产到start-input+e8/+ea，再由原builder消费为COMMON+c/+10；3正向场景原VCD基带/配置谓词均返回0，没有人工修补生产结果。',
        '格式输入号5/6分别形成COMMON输入格式13/14和pitch2400/2880；改未选行不影响输出，换行进入原padding诊断前，1921宽与格式8到原builder诊断。仅为明确记录/格式/ownerfixture的受控范围。',
        '正式76段A64与6次MIPS执行通过。首轮白名单边界错误和内盘临时空间导致的shell读取失败保留说明；外置盘脚本继续工作。默认查询/标志/锁/日志/真实数组与完整Start、硬件/文件/恢复仍未完成。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage50_native_start_geometry']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json',
      'scope':'Original encoder-side selected-record producer feeds separate original builder fragments and paired VCD predicates on declared metadata/owner/index fixtures. Not actual live record creation or complete Start.',
      'A64_fragments':76,'MIPS_predicates':6,'positive_geometry1920_1080_cases':3,
      'host_geometry_output_repair':False,'actual_live_MAIN_registration_full_start_or_device_acceptance':False,
      'authorization_unchanged':True,'goal_complete':False}
    g['corrections_to_prior_stage']['native_geometry_production_vs_live_record_provenance']={
      'previous_scope':'stage49 preserved minimal COMMON native3006; only host geometry edits passed its isolated baseband predicate.',
      'new_scope':'Original encoder-side metadata setters/getters/index/record packing now produce geometry and format before original builder; paired predicates pass without host output repair. Actual record origin/current MAIN index/default query/flags/full logs/locks/action remain fixtures or unexecuted.',
      'old_minimal_input_and_error_preserved':True,'full_native_Start_or_hardware_not_claimed':True,'evidence':ev}
    addition=' stage50在声明元数据/通道图上执行原setter/getter/index*d18及打包，原生成e8/ea进入COMMON+c/10，3组1920x1080基带/配置谓词通过；无生产后人工几何修补。未选行控制不变，换行进入padding诊断前、1921宽/格式8到原诊断。真实记录生产/MAIN索引/所有权/代次、默认查询22ba98、标志246274、完整日志/共享锁/Start/HAL与恢复仍未验收；输入格式号与MAIN流类型不混用。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].append(ev);req['remaining']+=addition
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    g['next_safe_offline_actions'][0]='追24c1d4元数据设置和启动事件+14索引的真实生产/校验/MAIN绑定，核对记录数组所有权与寿命；接入22ba98默认查询、246274标志附加参数及完整原锁/日志/动作。保留quality22/FH未命中与人工FF区别，不能将原几何生产片段和VCD纯谓词通过当硬件主录或恢复证明。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==oldg[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert statuspath.read_bytes()==before;statuspath.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 原编码输入几何生成](<work/sony-firmware-20261024/stage50-native-start-geometry/README.md>)：原通道索引/打包生成HD几何并通过配套原谓词，76段A64与6次MIPS验证；真实记录来源/MAIN登记/完整启动、硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
      for p in sorted(stage.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage50-native-start-geometry/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
      'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'76original A64 fragments plus6MIPS predicates. Original encoder-side selected-record geometry production on declared graph reaches paired predicates without host output repair. Live record origin/MAIN registration/full flags/defaults/locks/logs/Start/hardware and recovery remain unproven.',
      'mutable_progress':{'path':str(statuspath),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_guest_source_code_unchanged':True,'host_post_production_geometry_repair':False,
        'native_output_PC_return_log_or_lock_adapter':False,'explicit_metadata_owner_index_and_private_preset_host_fixtures':True,
        'failed_attempt_and_source_preserved':True,'new_loadable_camera_module':False,
        'UU_Windows_camera_interfaces_auth_mode_drivers_media_module_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert statuspath.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'A64_fragments':76,'MIPS_predicates':6,'goal_complete':False}))


if __name__=='__main__':main()
