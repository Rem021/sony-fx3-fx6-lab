#!/usr/bin/env python3
"""Review native metadata/classification receipts and seal once; no replay."""
import ast
import collections
import datetime
import json
import re
import struct
import mux_identity as f


def initializer_literals():
    # Bounded static constant propagation of the empty-map initialization arm.
    # This is source analysis, not native execution or a map-insert return stub.
    regs={};memory={};calls=[]
    for ins in f.instructions(0x24b658,0x24b7f4):
        asm=ins['asm'];pc=int(ins['va'],16)
        m=re.fullmatch(r'mov ([wx])(\d+), #(-?(?:0x[0-9a-f]+|\d+))',asm)
        if m:regs[int(m[2])]=int(m[3],0)&((1<<(32 if m[1]=='w' else 64))-1)
        m=re.fullmatch(r'str(h?) w(\d+), \[x29, #(0x[0-9a-f]+)\]',asm)
        if m and int(m[3],0) in (0x40,0x42,0x44):
            size=2 if m[1] else 4;value=regs[int(m[2])]
            for i,b in enumerate(value.to_bytes(size,'little')):memory[int(m[3],0)+i]=b
        if asm=='ldr x0, [x29, #0x40]':
            regs[0]=int.from_bytes(bytes(memory[0x40+i] for i in range(8)),'little')
        if asm=='bl #0x242b84':
            packed=regs[0];calls.append((pc,packed&0xffff,(packed>>16)&0xffff,packed>>32,regs[1]))
            regs.pop(0,None)
        if asm=='bl #0x24b580':
            for i in range(19):regs.pop(i,None)
    assert calls==[row[:5] for row in f.MAP_SOURCES]
    return [{'callsite':hex(pc),'width':w,'height':h,'profile_enum':p,'level_enum':l}
      for pc,w,h,p,l in calls]


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((root/e['path']).read_bytes())==e['sha256']
    run=stage/'run-20261025';path=run/'mux-identity-results.json';p=json.loads(path.read_text())
    receipt=json.loads((run/'source-receipt.json').read_text());source=stage/'mux_identity.py'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','observe_read','write','store','load'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    assert receipt['MPR_sha256']=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    assert receipt['APP_sha256']=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    setter=f.BASE/'stage12-prototype/profile/profile-results.json'
    assert im.sha(setter.read_bytes())==receipt['setter_result_sha256']
    old=json.loads(setter.read_text());assert old['experimental_target_setter']['output_vpc_quality_frame']==[6,6,3]
    assert p['original_fragments']==36 and len(p['cases'])==6
    events=p['original_key_events']+[e for x in p['cases'] for e in x['original_events']]
    assert len(events)==36
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'returned':34,'unapproved PLT printf':1,'boundary: before_alternate_record_format_classifier':1}
    for e in events:
        if e['reason']=='returned':assert e['SP_after']==hex(f.pp.STACK)
        assert not e['native_output_printf_allocator_PC_return_adapter']
        assert not any('stub' in x or 'logging_adapter' in x for x in e['calls'])
    calls=initializer_literals()
    pairs=p['original_default_map_pairs'];assert len(pairs)==len(calls)==8
    for pair,event,call in zip(pairs,p['original_key_events'],calls):
        assert [pair[k] for k in ('width','height','profile_enum','level_enum')]==[
          call[k] for k in ('width','height','profile_enum','level_enum')]
        packed=pair['width']|(pair['height']<<16)|(pair['profile_enum']<<32)
        stores={int(x['pc'],16):x for x in event['stores']}
        assert stores[0x242b88]['value']==packed and stores[0x242b94]['value']==pair['level_enum']
        assert event['return_u64']==pair['native_key']!=(1<<64)-1
    assert [x['map_value'] for x in pairs]==list(range(0x8b,0x93))
    cases=p['cases'];a,b,ff,hd9,uhd,alternate=cases
    assert a['observed_fields']==b['observed_fields']
    assert a['observed_fields']['width_height_3c_3e']==[1920,1080]
    assert a['observed_fields']['rate_2c_30']==a['observed_fields']['rate_34_38']==[30000,1001]
    assert a['observed_fields']['bitrate_raw40']==16000
    assert [x['native_record_format_classification_enum'] for x in cases]==[151,151,None,151,142,None]
    assert [x['native_MPF_profile_level_enum'] for x in cases]==[45,45,None,43,50,45]
    raw_a=bytes.fromhex(a['video_metadata_hex']);raw_b=bytes.fromhex(b['video_metadata_hex'])
    unchanged_by_code=a['bytes_not_written_by_initializers_or_converter']
    assert unchanged_by_code==b['bytes_not_written_by_initializers_or_converter']==[1,2,3,0x1d,0x1e,0x1f,0x47]
    assert [i for i,(x,y) in enumerate(zip(raw_a,raw_b)) if x!=y]==unchanged_by_code
    for x in cases:
        ev=x['original_events'];assert ev[0]['entry']=='0x115e18' and ev[1]['entry']=='0x115e54'
        assert ev[2]['entry']=='0x115fec'
        if x is not ff:
            assert ev[2]['reason']=='returned' and ev[2]['return_u64']==0
            assert '0x116768' in ev[2]['pcs'] and x['observed_fields']['valid_byte0']==1
            assert x['map_fixture']['native_map_ctor_allocator_or_balancing_executed'] is False
            if x is not alternate:
                assert '0x242b84' in ev[-1]['pcs'] and '0x247b14' in ev[-1]['pcs']
        else:
            assert ev[2]['reason']=='unapproved PLT printf' and ev[2]['stop_pc']=='0x83670'
            assert ev[2]['printf_arguments']==['0x2cd8ce','0x2ce408']
            assert x['observed_fields']['valid_byte0']==0 and x['observed_fields']['bitrate_raw40']==25000
    assert '0x24d394' in uhd['original_events'][-1]['pcs']
    assert all('0x24d394' not in x['original_events'][-1]['pcs'] for x in (a,b,hd9))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'scope':'Original metadata helpers and format classifier on declared writer-state and original-default-pair lookup fixtures.',
      'actual_setter_tuple_to_writer_state_handoff_not_executed':True,
      'original_video_audio_initializers_bound_to_actual_caller':True,
      'initializer_constants_checked_by_static_propagation_not_map_constructor_execution':calls,
      'original_map_global_header_node_storage_allocator_and_balancing_are_fixtures':True,
      'HD_key_minus1_and_classifier_default97_not_actual_mux_failure_proof':True,
      'actual_runtime_map_initialization_or_later_modifications_unobserved':True,
      'level5_profile1_MPF45_are_internal_enums_not_literal_HEVC_standard_levels':True,
      'seven_unwritten_bytes_not_globally_unused_or_safe_to_overwrite':unchanged_by_code,
      'FF8_Conv_ERROR_log_not_executed_and_not_fatal_recording_proof':True,
      'original_caller_overwrites_scalar_return_after_level_helper':f.instructions(0x1161e0,0x116204),
      'original_video_copy_span_and_name_conversion_caller':f.instructions(0x120760,0x120788),
      'name_conversion_classifier_chain':f.instructions(0x117b20,0x117b68),
      'actual_admission_header_file_XML_or_descriptive_name_effect_unresolved':True,
      'next_scope':'Trace fallback97 through record-format/name consumers before deciding whether a scoped map extension is required. Continue upper16M/resourceFF identity bridge and all physical/recovery gates.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    summary={'created_utc':now,'status':p['status'],'original_fragments':36,'original_stop_reasons':dict(counts),
      'target_native_metadata':a['observed_fields'],'target_MPF_internal_enum':45,
      'target_record_format_classifier_default':151,'stock_UHD_classifier_value':142,
      'FF_quality8_stopped_before_printf_and_metadata_not_complete':True,
      'default_map_entries':8,'default_map_global_construction_executed':False,
      'target_actual_mux_open_or_recording_failure_established':False,
      'complete_target_recording_or_recovery':False,'proof_sha256':im.sha(path.read_bytes()),
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    im.write_json(stage/'coordinator-observations.json',{
      'created_utc':now,'reviewer':'Same agent source/native-byte/trace/hash review; no independent implementation or device replay.',
      'previous_stage17files_and_APP_MPR_pins_verified':True,
      '36receipts_34original_stack_returns_and2explicit_boundaries_verified':True,
      'original_initializers_full_metadata_converter_and_original_helpers_executed':True,
      'target16M_geometry_rate_fields_and_prior_content_invariance_checked':True,
      'native_init_default_map_literals_checked_against_original_instruction_constants':True,
      'original_lookup_on_declared_tree_has_positive_UHD_and_negative_HD_controls':True,
      'map_constructor_allocator_actual_global_map_and_whole_writer_unexecuted':True,
      'new_observer_hooks_have_no_guest_memory_or_register_output_writes':True,
      'no_printf_log_return_or_allocator_adapter':True,
      'fallback_not_promoted_to_actual_mux_failure':True,
      'UU_Windows_camera_files_drivers_modules_WBI_flash_operations':False,
      'hardware_recording_backup_restore_or_independent_recovery_verified':False,
      'outcome':'PASS_NATIVE_METADATA_WITH_DOWNSTREAM_CLASSIFICATION_AND_PHYSICAL_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);oldg=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':oldg['progress_audit']['classification'],
      'basis':[
        '原video/audio初始化和完整115fec元数据转换运行，原setter候选[6,6,3]作声明输入后生成1920x1080、30000/1001、raw16000，正常返回0/valid1。A5/C3命名字段一致，7字节未写不判全局无用。',
        '原MPF profile/level转换候选得到内部枚举45；人工上层FF质量8在level helper原Conv ERROR printf前停止，raw25000/valid0，不把日志或未执行后段当实机失败。',
        '原格式key只接受3840/7680宽度和指定level/profile；候选HD返回-1。原默认初始化8组常量经静态传播核对，原key生成8键，声明map节点供原分类/查找：HD默认97，原UHD正常8e。真实map构造/后续修改及fallback实际影响仍缺。',
        '36段原执行通过，无printf/分配器/结果/返回替身；已定位分类至名称转换调用者，下一步确认它对描述/准入/容器的用途，再决定是否需改映射，不给HD套UHD标识。',
        'FH资源质量缺口与16M受限桥接仍未实现；完整应用到writer绑定、Open/Start/HAL、实际成片/音画长录和同机恢复/冷启动/独立救援全部保留。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage55_native_mux_identity']={
      'readme':rel+'/README.md','proof':ev,'summary':rel+'/summary.json',
      'review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'scope':'Original metadata initialization/full conversion, profile-level and record-format classification on declared state and original-default-pair tree fixtures. No full writer/mux/file output/current MAIN or recovery.',
      'original_fragments':36,'target_metadata_raw_rate':16000,'HD_classifier_default':151,
      'fallback_actual_recording_effect_known':False,'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['upper_quality_identity_and_mux_scope']={
      'new_scope':'UpperVQuality6 has native16M metadata path. VQuality8 enters original level diagnostic; changing it wholesale is not demonstrated safe. Native metadata fields do not establish supported record-format classification or actual MP4 writing.',
      'HD_classifier_default97_is_not_fatal_mux_failure_proof':True,
      'original_default_map_lookup_node_storage_is_fixture_not_actual_global_ctor':True,
      'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage55原初始化/完整writer元数据转换把声明候选[6,6,3]生成HD30000/1001/raw16000并正常返回；内部MPF45。上层FF8到原Conv ERROR日志前，raw25000/valid0。原格式key拒绝1920宽度/目标level5，以原默认8项构造的声明查找树中HD返回默认97、UHD8e；实际global map构造/后续修改、名称回退是否影响描述/准入或MP4写入仍待追，不判定实机不可录。36段原执行通过；真实应用到writer/当前MAIN、FH质量桥接/完整Start/HAL、成片/音画/长录及同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='追record-format默认97经ConvertVideoCodecTypeName的实际用途和消费者，区分描述性回退与writer/容器准入，再决定受限映射是否需要；保持上层VQuality6/raw16000身份，研究资源FH→FF私有预置桥接及query/cache/mux一致性，继续真实绑定/同步/完整Start/HAL和全部备份恢复/实机要求。'
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==oldg[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 原封装元数据与HD分类](<work/sony-firmware-20261024/stage55-native-mux-identity/README.md>)：36段原执行生成HD29.97/raw16000元数据；原分类默认97、UHD对照命中，实际用途仍待追，质量桥接/完整启动/硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage55-native-mux-identity/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'36 bounded original fragments: original video/audio initialization/full metadata conversion, profile-level conversion and format classification with original-default-pair tree fixtures. Native16M metadata; HD fallback97 actual effect unresolved. No full writer/MP4/Start/Hal/hardware/recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_MPR_code_unchanged':True,'writer_state_map_header_and_nodes_are_fixtures':True,
        'native_output_printf_allocator_PC_return_adapter':False,'new_loadable_camera_module':False,
        'HD_fallback_is_actual_mux_failure_claimed':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for e in files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':36,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
