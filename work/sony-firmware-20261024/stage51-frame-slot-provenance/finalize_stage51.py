#!/usr/bin/env python3
"""Review and seal stage51 once. No native replay or device operation."""
from pathlib import Path
import ast
import datetime
import json
import struct
import frame_slots as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    prior=f.s.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    provider=f.n.STAGE/'final-receipt.json'
    assert im.sha(provider.read_bytes())==f.c.PRIOR_SHA
    for e in json.loads(provider.read_text())['files']:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    p=stage/'run-20261025/frame-slot-results.json';proof=json.loads(p.read_text())
    source=stage/'frame_slots.py';receipt=json.loads((p.parent/'source-receipt.json').read_text())
    assert im.sha(source.read_bytes())==im.sha((p.parent/'executed-source.py').read_bytes())==receipt['script_sha256']
    ast.parse(source.read_text())
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('store','code','load'):
            for call in ast.walk(node):
                assert not (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and call.func.attr in ('reg_write','mem_write'))
    assert len(proof['original_events'])==proof['original_fragments']==62
    assert len(proof['allocations'])==41
    for i,e in enumerate(proof['allocations']):
        assert e['native_index']==(i if i<40 else 0xffffffff)
        assert e['native_record_pointer']==hex(f.POOL+i*f.STRIDE if i<40 else 0)
        assert e['original_fragment']['reason']=='returned'
        assert int(e['original_fragment']['x0_after'],16)&0xffffffff==e['native_index']
    assert proof['frame_array_bytes']==40*3352==0x20bc0
    metadata=bytes.fromhex(proof['metadata_prefix_hex'])
    assert struct.unpack_from('<Q',metadata,0x18)[0]==f.POOL
    assert struct.unpack_from('<I',metadata,0x20)[0]==40
    assert struct.unpack_from('<Q',metadata,8)[0]==f.POOL+0x20bc0
    assert struct.unpack_from('<I',metadata,0x10)[0]==0x120c
    start=bytes.fromhex(proof['Start_packet_hex'])
    assert struct.unpack_from('<3H',start,0)==(0x2103,0x102,0x90) and start[8:]==metadata
    for case in proof['picture_cases']:
        raw=bytes.fromhex(case['packet_hex'])
        assert struct.unpack_from('<3H',raw,0)==(0x2103,0x103,0x30)
        assert struct.unpack_from('<I',raw,8+0x14)[0]==case['native_allocator_index']
        assert raw[0x18]==case['final']
    assert [e['original_fragment']['reason'] for e in proof['flag_cases']]==[
      'returned','returned','boundary: before_unexecuted_diagnostic','boundary: before_unexecuted_diagnostic']
    assert [e['name'] for e in proof['typed_bindings']]==[
      'resource_video_enc_start_param_t','resource_video_enc_encode_picture_param_t']
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Correct an old enumeration's scope without rewriting sealed evidence.
    old_stage=f.BASE/'stage42-encoder-state-and-lock-boundaries'
    old_source=old_stage/'encoder_state.py';old_manifest=json.loads((old_stage/'final-receipt.json').read_text())
    rows=[e for e in old_manifest['files'] if e['path']==str(old_source.relative_to(root))]
    assert len(rows)==1 and rows[0]['sha256']==im.sha(old_source.read_bytes())
    assert 'for n in range(16):' in old_source.read_text()
    aliases=[]
    for name,table,nexttable,lo,hi in (
      ('enc_sys_v_t',0x3806d8,0x380828,0x252f54,0x252f90),
      ('enc_stop_done_t',0x380978,0x380ac8,0x2533d4,0x253410)):
        assert nexttable-table==14*24
        assert im.adrp_refs(blob,{nexttable:'next typed event table'})
        instructions=im.dump(blob,lo,hi,f.V)
        assert any(x['asm']=='cmp w20, #0xf' for x in instructions)
        assert any(x['asm']=='cmp w20, #0xe' for x in instructions)
        for state in (14,15):
            at=table+state*24
            assert at==nexttable+(state-14)*24
            aliases.append({'old_event':name,'old_claimed_state':state,'physical_row_offset':hex(at),
              'actual_scope':'adjacent event table row'+str(state-14)+'; excluded before table lookup by original event helper',
              'dispatch_migration_evidence_for_old_claimed_state':False})
    correction={'created_utc':now,'old_files_preserved':True,
      'frame_index_namespace':{'previous_stage50_name':'channel records/index was a provisional name',
        'current_evidence':'Original40-slot initializer, allocator clearing3352bytes and native picture index marshalling support frame-slot index; not fixed MAIN encoding-channel identity.'},
      'state_table_scope':{'ordinary_rows_per_table':14,'state_name_count_can_still_be16':True,
        'special_states14_15_handled_before_lookup':True,'old_stage42_enumerated_rows_per_table':16,
        'old_32_selector_rows_ordinary_valid_scope':28,'excluded_adjacent_table_aliases':aliases,
        'earlier_normal_wrapper_and_pending_tests_not_invalidated':True,
        'source':str(old_source.relative_to(root)),'source_sha256':im.sha(old_source.read_bytes()),
        'entry_scope_instructions':[im.dump(blob,0x252f54,0x252f90,f.V),im.dump(blob,0x2533d4,0x253410,f.V)]}}
    im.write_json(stage/'scope-corrections.json',correction)
    summary={'created_utc':now,'status':proof['status'],'original_fragments':62,
      'frame_slots':40,'record_bytes':3352,'native_indices':[x['native_index'] for x in proof['allocations']],
      'native_allocation_clear_and_capacity_verified':True,'metadata_and_picture_are_distinct_typed_events':True,
      'native_Start_and_picture_header_tuples':[[0x2103,0x102,0x90],[0x2103,0x103,0x30]],
      'frame_slot_index_not_MAIN_channel_ID':True,'full_Start_metadata_validity':False,
      'flag_preparer_complete_only_under_declared_conditions':True,
      'old_state_table_adjacent_alias_rows_excluded':4,
      'real_frame_fill_return_epoch_Hal_recording_or_recovery':False,
      'proof_sha256':im.sha(p.read_bytes()),'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    review={'created_utc':now,'reviewer':'same agent source/byte/trace/hash review; no independent implementation or device replay',
      'previous_stage_files_verified':12,'provider_stage_files_verified':21,
      'executed_source_copy_and_receipt_match':True,
      'native_hooks_have_no_memory_register_output_replacement':True,
      'store_count_digest_observations_do_not_modify_native_writes':True,
      'complete_native_pool_and_companion_initializers_on_declared_map_node_pool':True,
      '40sequential_native_indices_and41st_capacity_sentinel_verified':True,
      'selected_record_zeroing_and_untouched_record_A5_checks_in_run_source':True,
      'actual_getters_link_frame_pool_self_to_partial_Start_metadata':True,
      'native_message_shapes_UID_comparison_picture_index_and_final_branch_verified':True,
      'MID102_Start_andMID103_picture_types_distinct_from_VCD_command1e':True,
      'partial_metadata_seed_not_current_camera_or_real_uninitialized_bug':True,
      'native_flag_preparer_positive_and_diagnostic_controls_verified':True,
      'old_14row_table_vs16names_and4adjacent_aliases_corrected_without_history_changes':True,
      'frame_return_actual_fill_real_MAIN_owner_epoch_global_quiescence_unproven':True,
      'no_camera_UU_Windows_interfaces_drivers_modules_WBI_flash':True,
      'outcome':'PASS_WITH_LIVE_FILL_LIFETIME_FULL_START_AND_DEVICE_GAPS'}
    im.write_json(stage/'coordinator-observations.json',review)
    path=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert path.read_bytes()==before==(f.s.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);oldg=json.loads(before);rel=str(stage.relative_to(root));ev=str(p.relative_to(root))
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':oldg['progress_audit']['classification'],
      'basis':[
        '原40项帧池初始化/分配器完整正文运行，在明确map节点输入下产生0..39索引、每项原清零，41次返回FFFFFFFF/null。索引收紧为帧槽号，不是固定MAIN通道。',
        '原前端getter将帧池self地址/40写入Start元数据前段；原MID102Start和MID103逐帧包复制/接收分派核对，native借出0/39/1进入payload+14，普通/最终帧分支区分。元数据后半段/真实消息传输仍未完成。',
        '原完整标志helper在关闭覆盖的声明状态下返回1，缓存控制和两项诊断对照核对；62段原执行通过，无日志/锁/返回替身。实际填充/归还/MAIN owner/epoch/完整Start/HAL及恢复仍缺。',
        '更正stage42每表16行枚举范围：普通分派14行，状态14/15由入口处理，4条相邻表别名剔出迁移证据，历史记录不改。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage51_frame_slot_provenance']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','corrections':rel+'/scope-corrections.json',
      'scope':'Original pool initialization/allocator/getters, partial metadata/picture messages, receiver branches and bounded flag preparation on declared object/map fixtures. No real frame fill/return/controller boot or hardware.',
      'original_fragments':62,'native_slots':40,'stride':3352,
      'frame_index_is_not_fixed_encoding_channel':True,'full_valid_Start_or_device_acceptance':False,
      'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['frame_slot_and_state_table_namespaces']={
      'stage50_provisional_channel_record_name':'Frame-slot record/index established by original40slot allocator and picture API; actual MAIN encoding-channel ID unbound.',
      'stage42_selector_scope':'14ordinary rows per typed table. Old2x16 enumeration has4adjacent-table aliases, excluded from dispatch evidence; native helpers handle14/15before lookup.',
      'state_selectors_not_completed_live_transition':True,'old_files_preserved':True,
      'evidence':[ev,rel+'/scope-corrections.json']}
    addition=' stage51原40帧槽池初始化/分配生成0..39索引并逐槽清零，满后返回FFFFFFFF/null，Start元数据前段与逐帧MID103原包/接收分派绑定该索引。它不是固定编码通道；真实帧填充/归还、MAIN身份/代次/同步仍未闭合。原标志helper仅在声明覆盖状态下完整返回，完整元数据/默认查询/锁/日志/Start/HAL与恢复仍缺。stage42普通事件表14行，旧枚举末两行各读相邻表，4项不再作为迁移证据。局部帧槽计数也不能代表全局硬件/代码退出。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-corrections.json']);req['remaining']+=addition
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    g['next_safe_offline_actions'][0]='追15f8c0帧槽借用后的实际几何/格式填充及API调用者，接原归还/取消/错误与异步完成，核对MAIN请求/配置代次；补136378完整Start元数据、22ba98默认查询和真实覆盖状态/共享锁/日志。帧槽索引不当编码通道，局部used计数不当全局退出，原纯检查/片段不当硬件主录或恢复证明。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==oldg[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert path.read_bytes()==before;path.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 帧槽来源与两类事件](<work/sony-firmware-20261024/stage51-frame-slot-provenance/README.md>)：原40帧槽分配/清零及Start/逐帧包、标志准备62段验证，索引不当编码通道；更正旧表4项越界枚举，真实填充/归还/完整启动、硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage51-frame-slot-provenance/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
      'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'62original fragments:40slot initialization/allocation/clear/capacity and actual getters, partial Start/picture message framing/receiver branches and bounded complete flag helper. Frame-slot namespace and4old table aliases corrected. No actual frame fill/return/current MAIN owner/fullStart/HAL/hardware/recovery proof.',
      'mutable_progress':{'path':str(path),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_guest_code_unchanged':True,'map_node_pool_and_object_links_are_explicit_fixtures':True,
        'native_output_PC_return_log_lock_or_Hal_adapter':False,'partial_metadata_not_ready_to_submit':True,
        'new_loadable_camera_module':False,'UU_Windows_camera_interfaces_auth_modes_drivers_media_module_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for e in files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    assert path.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'native_fragments':62,'old_alias_rows_excluded':4,'goal_complete':False}))


if __name__=='__main__':main()
