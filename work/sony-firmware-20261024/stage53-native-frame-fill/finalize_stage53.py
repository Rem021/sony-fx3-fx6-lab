#!/usr/bin/env python3
"""Seal the source/trace review and scope correction; no device/native replay."""
import ast
import collections
import datetime
import json
import struct
import native_frame_fill as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    prior=f.l.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((root/e['path']).read_bytes())==e['sha256']
    run=stage/'run-coupled-geometry-20261025';path=run/'native-frame-fill-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'native_frame_fill.py';ast.parse(source.read_text())
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    assert not any(isinstance(x,ast.FunctionDef) and x.name in ('store','load','code') for x in ast.walk(ast.parse(source.read_text())))
    old_receipt=json.loads((f.l.STAGE/'run-bounded-string-compare-20261025/source-receipt.json').read_text())
    for key in ('avcam_sha256','LIRO_sha256','kernel_sha256'):assert receipt[key]==old_receipt[key]
    assert p['original_fragments']==len(p['original_events'])==112
    counts=collections.Counter(e['reason'] for e in p['original_events'])
    assert counts=={'returned':105,'boundary: after_original_kernel_memcpy_before_next_diagnostic':3,
      'boundary: before_real_locked_Start_wrapper':3,'boundary: before_unexecuted_diagnostic':1}
    for e in p['original_events']:
        if e['reason']=='returned':assert e['SP_after']==hex(f.r.SP)
        assert not e.get('native_output_or_PC_return_adapter',False)
        assert not e.get('native_output_or_return_adapter',False)
    assert p['ImageSizeInfo_RTTI']=='35C_DataflowInfra_Entry_ImageSizeInfo'
    assert p['CameraInfo_RTTI']=='32C_DataflowInfra_Entry_CameraInfo'
    cases=p['cases'];assert len(cases)==4
    assert [x['native_function_return'] for x in cases]==[1]*4
    assert [x['format_byte28'] for x in cases]==[5,6,0,5]
    assert [x['encoder_input_f8_format'] for x in cases]==[5,6,8,5]
    assert [x['encoder_input_e8_ea_geometry'] for x in cases]==[[1920,1080],[1280,720],[0,0],[1920,1080]]
    for i,x in enumerate(cases):
        assert x['native_fragment']['start_pc']==hex(f.V+0x1479d8)
        assert x['native_fragment']['reason']=='returned'
        # Whole original fill restores caller LR through native tail getter.
        assert hex(f.V+0x1479d8) in x['native_fragment']['pcs']
        assert hex(f.V+0x147ad4) in x['native_fragment']['pcs']
        assert hex(f.V+0xa474c) in x['native_fragment']['pcs']
        data=bytes.fromhex(x['record_hex']);inp=bytes.fromhex(x['independent_encoder_pack_input_hex'])
        assert len(data)==f.STRIDE and len(inp)==0x170
        assert struct.unpack_from('<2H',inp,0xe8)==struct.unpack_from('<2H',data,0x3e)
        assert x['queue_before']==x['queue_after']==x['slot_index']+1
        assert x['validity_bytes']['0x0']==(0 if i==2 else 1)
        assert x['validity_bytes']['0x9c']==(0 if i==3 else 1)
        for key,value in x['validity_bytes'].items():
            if key not in ('0x0','0x9c'):assert value==1
    failed=json.loads((stage/'run-20261025/last-phase-at-failure.json').read_text())
    assert failed['reason']=='unapproved execution '+hex(f.V+0x94574)
    intermediate=json.loads((stage/'run-yc-export-range-20261025/native-frame-fill-results.json').read_text())
    assert intermediate['original_fragments']==108
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']
    assert im.dump(blob,0x24d030,0x24d034,f.V)[0]['asm']=='ldurb w0, [x26, #-0x20]'
    assert im.dump(blob,0x92070,0x92074,f.V)[0]['asm']=='strb w1, [x0, #0x40]'
    assert im.dump(blob,0x91f6c,0x91f70,f.V)[0]['asm']=='strh w1, [x0, #0x4e]'
    oldproof=f.l.STAGE/'run-bounded-string-compare-20261025/frame-lifetime-results.json'
    oldcase=json.loads(oldproof.read_text())['geometry_tag_cases'][0]
    oldprefix=bytes.fromhex(oldcase['record_prefix_hex'])
    assert oldprefix[0x28]==0 and oldprefix[0x36]==5
    assert struct.unpack_from('<2H',oldprefix,0x3e)==(1920,1080)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    correction={'created_utc':now,'old_stage52_files_and_execution_preserved':True,
      'incorrect_claim':'stage52 record_format_byte36 label and README/progress descriptions treated single byte at record+36 as input format5.',
      'correct_scope':'record+28 is input format; +29 accompanying flag. Ten u16 geometry values start+36. Original x26 points record+48 and LDURB[x26-20] reads+28.',
      'stage52_actual_bytes':{'record28':oldprefix[0x28],'record36_low_byte':oldprefix[0x36],
        'record3e_40_geometry':[1920,1080],'input_format5_proven':False},
      'unaffected_stage52_scope':'48byte tag copy, selected geometry+3e/+40 and independent queue/slot lifetime observations remain valid.',
      'new_evidence':'Original typed setters/native event serialization/full frame fill and independent encoder packing carry format5 at+28 to input+f8 and1920x1080 to input+e8/+ea.',
      'return_scope':'Whole0x1479d8 return1 comes from tail tag24 getter, not aggregate prior tag validity. Missing image/camera controls still return1.',
      'sources':[str(oldproof.relative_to(root)),ev],
      'field_instructions':[im.dump(blob,0x24d024,0x24d038,f.V),im.dump(blob,0x92070,0x92078,f.V),im.dump(blob,0x91f6c,0x91f74,f.V)]}
    im.write_json(stage/'scope-corrections.json',correction)
    summary={'created_utc':now,'status':p['status'],'original_fragments':112,'original_stop_reasons':dict(counts),
      'original_ImageSizeInfo_RTTI':p['ImageSizeInfo_RTTI'],
      'native_SSYC_ctor_and_native_typed_tag_serialization':True,
      'whole_frame_fill_returns_through_original_tail_getter':True,
      'native_image_tag_replacement_keeps9entries_and_preserves_old_filled_record':True,
      'cases':[{k:x[k] for k in ('label','format_byte28','geometry_10u16_at36','validity_bytes',
        'encoder_input_e8_ea_geometry','encoder_input_f8_format','native_function_return')} for x in cases],
      'stage52_format_offset_corrected_without_rewriting_old_receipts':True,
      'return1_not_aggregate_frame_validity':True,'whole_Start_live_MAIN_Hal_or_recovery':False,
      'proof_sha256':im.sha(path.read_bytes()),'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    im.write_json(stage/'coordinator-observations.json',{
      'created_utc':now,'reviewer':'Same agent source/native-byte/trace/hash review; no independent implementation or device replay.',
      'prior_stage14files_and_official_provider_hashes_verified':True,
      '112receipts_and105_original_stack_returns_verified':True,
      'all4_complete_fill_entry_tail_and_return_paths_checked':True,
      'native_tag_setters_serialization_and_replacement_checked':True,
      'actual_filled_record_bytes_reach_independent_encoder_packing_unchanged':True,
      'absent_image_or_camera_does_not_make_tail_return_false':True,
      'source_has_no_new_execution_memory_or_register_output_hooks':True,
      'old_format_label_error_corrected_and_failed_range_attempt_preserved':True,
      'current_MAIN_hardware_recording_restore_and_recovery_verified':False,
      'UU_Windows_camera_files_drivers_module_WBI_flash_operations':False,
      'outcome':'PASS_OFFLINE_TYPED_PRODUCTION_FULL_FILL_AND_BOUNDED_CONSUMPTION_WITH_PHYSICAL_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.l.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name
    g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
      'basis':[
        '原RTTI绑定ImageSizeInfo/CameraInfo；原SSYC构造/typed setter/序列化创建9类标签，完整1479d8帧填充正常原栈返回，实际读取并保留1920x1080、格式5。',
        '同一原容器替换图像标签不增加重复key，新槽得到1280x720/格式6，旧槽保持；实际填充记录原样进入独立编码几何片段，生成input+e8/ea及+f8，到真实锁边界前停止。',
        '缺图像或CameraInfo时完整fill仍返回1，分别valid字节0；返回来自尾部tag24，不是整帧有效。缺图像的几何消费产生0/0、格式8并到padding诊断前。',
        '更正stage52误标：格式实际record+28，+36为几何u16起点；旧输入+28仍0，不能称原格式5生成。48字节复制/选定宽高/寿命结果保留，历史封存不改。',
        '112段有界原执行通过，无原输出/返回/日志/锁/HAL替身；真实上游图像生产/MAIN、完整Start、质量FH与硬件/恢复仍待验收。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage53_native_frame_fill']={
      'readme':rel+'/README.md','proof':ev,'summary':rel+'/summary.json',
      'review':rel+'/coordinator-observations.json','corrections':rel+'/scope-corrections.json',
      'scope':'Native SSYC/typed tag production, whole frame fill and independent geometry-consumer fragment on declared RAM values/object links. No real source graph/current MAIN/whole encoder action/logs/locks/Start/Hal/device recovery.',
      'original_fragments':112,'whole_frame_fill_cases':4,'current_MAIN_or_Hal_proven':False,
      'goal_complete':False,'authorization_unchanged':True}
    g['latest_stage_evidence']['stage52_frame_lifetime_and_fill']['format_field_label_superseded_by_stage53']='record+36 is geometry, not input format. Stage52 record+28 was0; only48byte copy and selected geometry/lifetime claims retained.'
    g['corrections_to_prior_stage']['stage52_image_format_offset_and_full_fill_return']={
      'wrong_format_label':'record_format_byte36','correct_format_offset':'record+0x28',
      'geometry_start':'record+0x36 is ten u16 values',
      'stage52_positive_actually_had_format0':True,'old_files_preserved':True,
      'full_fill_return1_not_aggregate_validity':True,'evidence':[ev,rel+'/scope-corrections.json']}
    addition=' stage53原SSYC/typed标签构造、setter及序列化与完整1479d8帧填充接通，4例包含同容器替换、缺Image/CameraInfo，112段原执行通过；实际填充记录原样进入独立几何打包生成1920x1080/格式5，锁/日志/完整动作仍未执行。stage52的record+36格式名更正：实际+28为格式，旧输入+28=0，+36是几何u16起点；旧48字节复制/选定宽高及寿命证据保留。完整fill返回1来自尾tag24，缺其它tag仍可能1，需逐有效字节与实际上层流程。真实上游生产/当前MAIN/同步/完整Start/质量FH/硬件及同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-corrections.json'])
            req['remaining']=req['remaining'].replace('原48字节标签getter及调用者valid写入在声明输入上生成5/1920/1080',
              '原48字节标签getter及调用者valid写入在声明输入上复制选定1920/1080；旧+36单字节5是几何输入，不是实际+28格式')+addition
    g['next_safe_offline_actions'][0]='追实际输入动作的ImageSizeInfo上游生产/格式选择、MAIN事件来源及标签必需性/缺失处理；补完整Start元数据、真实默认查询/同步/通知/代次、VCD完整Start与硬件完成。并继续解决quality22/FH与真实MAIN16M选择缺口，不以默认标签或人工FF代替。'
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 原标签生成与完整帧填充](<work/sony-firmware-20261024/stage53-native-frame-fill/README.md>)：112段原执行接通typed标签序列化/完整fill/独立几何消费；更正格式偏移+28，返回1不等整帧有效，真实MAIN、完整启动/硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage53-native-frame-fill/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'112 bounded original fragments: SSYC/typed tag generation and serialization, complete frame fill and independent geometry packing on unchanged native-filled records. Stage52 format-offset label corrected; no actual MAIN/wholeStart/Hal/hardware/recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_guest_code_unchanged':True,'RAM_inputs_object_links_backing_storage_and_ownership_are_fixtures':True,
        'native_output_PC_return_log_lock_notification_or_HAL_adapter':False,'new_loadable_camera_module':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for e in files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':112,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
