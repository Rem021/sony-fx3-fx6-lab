#!/usr/bin/env python3
"""Review existing prototype/native receipts and seal once; no test replay."""
import ast
import collections
import datetime
import json
import struct
from pathlib import Path
import resource_alias as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    assert not (stage/'final-receipt.json').exists()
    prior=f.BASE/'stage56-native-stop-name-flow/final-receipt.json'
    assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    run=stage/'run-bounded-stores-20261026';path=run/'resource-alias-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'resource_alias.py';csource=stage/'resource_alias.c'
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    assert im.sha(csource.read_bytes())==im.sha((run/'compiled-source.c').read_bytes())==receipt['C_source_sha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store','observe_read'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    origin=json.loads((stage/'prototype-source-origin.json').read_text())
    assert im.sha((stage/'prototype-source-origin.json').read_bytes())==receipt['source_origin_sha256']
    assert im.sha((root/origin['source']).read_bytes())==origin['source_sha256']
    for name,pin in origin['outputs'].items():assert im.sha((stage/name).read_bytes())==pin
    obj=(run/'resource_alias.a64.o').read_bytes();code,ro,functions,relocs=f.object_image(obj)
    assert im.sha(obj)==p['prototype']['object_sha256'] and im.sha(code)==p['prototype']['code_sha256']
    assert len(code)==2728 and len(ro)==392 and len(relocs)==6
    assert {k:hex(v) for k,v in functions.items()}==p['prototype']['functions']
    assert ro[:256]==(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()[0x3c5798:0x3c5898]
    descriptor=bytes.fromhex(origin['expected_descriptor_hex']);assert len(descriptor)==136
    assert ro[256:]==descriptor and struct.unpack_from('<I',descriptor,0x38)[0]==4
    assert receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    cases=p['positive_cases'];assert len(cases)==2 and [x['seed'] for x in cases]==[0xa5,0xc3]
    original=[e for x in cases for e in x['original_events']]+p['negative_controls']['original_setup_events']
    proto=[e for x in cases for e in x['prototype_events']]+[x['event'] for x in p['negative_controls']['controls']]
    assert len(original)==p['original_fragments']==25 and len(proto)==p['compiled_prototype_calls']==33
    counts=collections.Counter(e['reason'] for e in original)
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':5,
      'returned':9,'boundary: before_unexecuted_diagnostic':5,'boundary: before_original_row_diagnostic':2,
      'boundary: before_actual_buffer_and_channel_preparation':2,
      'boundary: after_original_rate_fields_before_other_inputs':2}
    for e in original:
        assert not e.get('native_output_or_PC_return_adapter',False) and not e.get('native_output_or_return_adapter',False)
        if e['reason']=='returned':assert e['SP_after']==hex(f.r.SP)
    for e in proto:
        assert e['reason']=='returned' and e['SP_after']==hex(f.r.STACK+0x2000)
        assert not e['native_output_or_PC_return_adapter']
        assert all(int(pc,16)==f.r.STOP or f.CODE<=int(pc,16)<f.CODE+len(code) for pc in e['pcs'])
        assert all(f.CODE<=int(w['pc'],16)<f.CODE+len(code) for w in e['writes'])
    for x in cases:
        raw=bytes.fromhex(x['original_input98_hex']);view=bytes.fromhex(x['compiled_match_view98_hex'])
        assert raw[:136]==descriptor==bytes.fromhex(x['original_FH_descriptor88_hex'])
        assert [i for i,(a,b) in enumerate(zip(raw,view)) if a!=b]==[0x38] and view[0x38]==6
        assert x['native_MAIN_tail']==[1,10,25,x['seed']*0x01010101]
        assert x['native_matcher_row']==386 and x['native_preset_id']=='0x19450'
        assert x['native_row_address']==hex(f.V+0x395108+386*0x90)
        assert x['native_metadata_identity_remains_FH_and_source_unchanged'] and x['entire_other_owner_and_old_packet_unchanged']
        ev=x['prototype_events'];assert [e['status'] for e in ev]==[0,0,0,10,0,0,10,0,0]
        copies=[w for w in ev[0]['writes'] if f.VIEW<=int(w['address'],16)<f.VIEW+152]
        assert [(int(w['address'],16),w['size']) for w in copies]==[(f.VIEW+i,1) for i in range(152)]+[(f.VIEW+0x38,4)]
        cp=[w for w in ev[1]['writes'] if f.COPY<=int(w['address'],16)<f.COPY+256]
        assert [(int(w['address'],16),w['size']) for w in cp]==[(f.COPY+i,1) for i in range(256)]+[(f.COPY+0xb0,4)]
        pub=[i for i,w in enumerate(ev[1]['writes']) if int(w['address'],16)==f.COMMON+0xe000]
        assert len(pub)==1 and ev[1]['writes'][pub[0]]['size']==8
        assert max(i for i,w in enumerate(ev[1]['writes']) if f.COPY<=int(w['address'],16)<f.COPY+256)<pub[0]
        rates=[e['decoded_trace_target_cpb'] for e in x['original_events'] if 'decoded_trace_target_cpb' in e]
        assert rates==[[25999360,24498176,26000000],[25999360,16000000,26000000],
          [25999360,16000000,26000000],[25999360,24498176,26000000]]
        assert x['control_after']['live']==0 and x['control_after']['gate']==0 and x['control_after']['data_restored']==1
    negatives=p['negative_controls']['controls'];assert len(negatives)==15
    for row in negatives:
        assert row['destination_and_common_unchanged'] and row['event']['status']==row['expected_status']!=0
        assert not any(f.VIEW<=int(w['address'],16)<f.VIEW+152 for w in row['event']['writes'])
    baseline=p['existing_baseline_receipt'];assert baseline['not_replayed_this_stage']
    assert im.sha((root/baseline['path']).read_bytes())==baseline['sha256']
    failure=json.loads((stage/'run-20261025/attempt-failure.json').read_text())
    oldphase=json.loads((stage/'run-20261025/last-phase-at-failure.json').read_text())
    assert not failure['passing_result'] and oldphase['reason']=='unapproved execution '+hex(f.V+0x21dd54)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'scope':'OUR compiled temporary match view + exact original FH private writer, original native matcher/row/default/partial pack on explicit offline contexts.',
      'matcher_view_is_new_compiled_code_not_a_Sony_native_feature':True,
      'original_source_and_common_descriptor_quality4_unchanged_view_only_quality6':True,
      'post_diagnostic_original_matcher_separate_guest_input_X19_is_compiled_view':True,
      'diagnostic_effect_neutrality_real_call_frame_owner_epoch_shared_locks_unproven':True,
      'row386_and_preset19450_derived_by_original_code_not_supplied_as_matcher_returns':True,
      'private16M_generation_queries_and_partial_pack_proven_not_Hal_rate':True,
      'live_source_metadata_query_cache_mux_consumer_alignment_not_complete':True,
      'completion_notifications_simulated_and_pointer_restore_not_stock_mode_restore':True,
      'no_code_reclamation_or_actual_temporary_view_lifetime_hook':True,
      'next_scope':'Bind actual resource match call storage/owner/epoch/synchronization and full channel preparation/parameter consumers while preserving query/cache/mux identity and all physical/recovery gates.',
      'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    im.write_json(stage/'summary.json',{'created_utc':now,'status':p['status'],'original_fragments':25,
      'compiled_prototype_calls':33,'original_stop_counts':dict(counts),'negative_controls':15,
      'source_quality':4,'temporary_match_quality':6,'native_row':386,'preset_id':'0x19450',
      'original_default_target':24498176,'compiled_private_target':16000000,
      'target_actual_recording_or_recovery':False,'proof_sha256':im.sha(path.read_bytes()),
      'goal_complete':False,'persistent_write_release':False})
    remote={'created_utc':now,'host':'DESKTOP-262CR7C','user_reported_online_and_desktop_observed':True,
      'existing_host_project_outputs_verified_by_UU_file_transfer_UI':'C:\\Users\\owo\\Documents\\Codex\\2026-10-16\\rea-2\\outputs',
      'handoff_local_directory_opened_in_UU':str(f.BASE/'stage12-prototype/msc-probe/windows-cache-handoff'),
      'new_handoff_transfer_success_receipt_or_native_Windows_execution':False,
      'remote_directory_create_or_file_selection_action_effect':'unverified; no success/new-transfer receipt observed',
      'latest_authoritative_UI':'与远端设备的连接已断开; after dismiss: DESKTOP-262CR7C 离线',
      'last_CUA_disconnect_observation':'Native alert then offline screenshot/AX; no inference from timeout.',
      'user_scope':'仅虚拟屏1及UU文件传输，不影响实体屏游戏；不再全局Alt+Tab。',
      'earlier_physical_screen_switch_and_alt_tab_occurred_then_user_constraint_applied':True,
      'cached_PnP_task_not_submitted_or_executed':True,'camera_interface_auth_mode_driver_file_module_WBI_or_flash':False}
    im.write_json(stage/'windows-handoff-observation.json',remote)
    im.write_json(stage/'coordinator-observations.json',{'created_utc':now,
      'reviewer':'Same-agent original-byte/source/trace/hash review, no independent implementation or actual device replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'prior_stage18files_and_canonical_snapshot_verified':True,
      'new_observer_hooks_no_guest_register_memory_or_return_writes':True,
      'compiled_PC_stores_view_copy_and_ordered_private_publish_verified':True,
      'exact_source_FH_native_row_and_preset_default_query_and_partial_pack_checked':True,
      '15negative_controls_preserve_destination_and_common':True,
      'first_unapproved_expected_boundary_and_source_retained':True,
      'Windows_connection_observed_then_explicit_disconnect_no_transfer_or_PnP_completion_claim':True,
      'whole_native_Open_Start_Hal_recording_restore_and_code_exit_unverified':True,
      'outcome':'PASS_SCOPED_COMPILED_RESOURCE_VIEW_WITH_LIVE_BINDING_AND_PHYSICAL_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(prior.parent/'goal-status-after.json').read_bytes()
    oldg=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      'stage56封存18件和canonical复核；本轮编译2函数临时匹配视图／严格原FH私有写者，不再依赖整项上层FF质量替换。',
      '原queued Open生成MAIN(1,10,25,旧值)，新编译代码只复制152字节并将副本质量4改6，原输入与common FH描述不变。',
      '独立后诊断原matcher消费编译副本返回386，原行地址／ID计算及原静态selector选19450，默认24498176。写者复制改私有目标后原查询／部分打包得16000000，trace/CPB不变。',
      '25段原执行与33原型调用通过，两种尾旧值与15负例通过；新PC完整写轨迹核对副本和私有复制／发布顺序。首轮漏登记21dd54边界及失败源保留。',
      '真实钩子／临时副本寿命／owner代次／共同同步／全消费者／完整Open/Start/Hal与全部实机和恢复仍未验收。数据指针复原不等于恢复原厂有效拍摄模式。',
      '用户恢复Windows后UU在线桌面与已有项目outputs路径已见；自动输入未可靠提交。按用户要求转仅虚拟屏/UU传输，随后原生断连提示及离线已确认。无新传输成功、缓存PnP执行或相机接口操作。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage57_native_resource_alias']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'Windows_observation':rel+'/windows-handoff-observation.json','original_fragments':25,'compiled_prototype_calls':33,
      'scope':'Compiled matcher-only temporary FF view with source FH unchanged; native row386/preset19450, exact FH private16M writer and original selected-rate query/partial pack. Independent post-log inputs, no live hook or full Open/Start.',
      'actual_resource_quality_alignment_or_hardware_proven':False,'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['scoped_match_view_vs_global_FF_identity']={
      'prior_scope':'stage37 required an artificial FF common descriptor; stage54 showed original FH failed and upper quality8/raw25000 inconsistent.',
      'new_scope':'Compiled temporary match-only quality6 view selects original MAIN386 while source/common quality4/FH is unchanged; a new exact-FH writer variant yields16M in native default query/partial pack.',
      'not_live_hook_synchronization_or_all_query_cache_mux_alignment_proof':True,
      'data_pointer_restore_is_not_supported_stock_mode_restore':True,'old_files_preserved':True,
      'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage57新编译临时匹配视图只改副本quality4→6，原源/common FH136字节保持；独立后诊断原matcher返回MAIN386，原row/ID/selector选19450。精确原FH资格的私有写者产16M，原查询和部分打包为16000000，trace/CPB保留。25段原执行/33原型调用、A5/C3及15负例通过。真实hook/临时副本寿命/owner代次/共同同步/完整构造及query/cache/mux全消费者未闭合；指针复原回24.5M而FH描述仍在，不是有效原厂模式恢复。实机Open/Start/Hal/成片及全部同机恢复要求保留。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='追真实资源match调用处的对象身份/配置代次/共享同步和临时视图存储寿命，将仅匹配转换与原通道准备/私有16M预置应用/完整参数消费者接合；保留上层VQuality6、原FH源/common描述及查询/缓存/封装一致性。全部实际Open/Start/Hal/成片/备份恢复和冷启动/独立救援不变。'
    g['next_authorized_cached_metadata_action']['current_external_dependency']='Windows briefly restored and UU desktop/file-transfer project path observed; no new handoff or task execution proven. UU explicitly disconnected then host offline. Future UI limited to virtual screen1/file transfer, never physical-screen gaming or global Alt+Tab.'
    g['external_dependencies']['Windows_cached_association_handoff'].update({
      'status':'deferred_after_observed_reconnect_then_explicit_disconnect',
      'user_response':'好了win在线了；已切到FX3 Codex，可以操作；随后要求仅另一个桌面、不影响游戏。',
      'new_remote_attempts_this_stage':True,'latest_host_state':'UU explicit disconnect alert then host offline',
      'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False,
      'UI_scope':'virtual screen1 and UU file transfer only; no physical screen/global app switch'})
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    for key in ('objective','authorization','completion_rule'):assert g[key]==oldg[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();text=idxbefore.decode()
    entry='- [2026-10-26 FX3 保持FH身份的资源匹配原型](<work/sony-firmware-20261024/stage57-native-resource-alias/README.md>)：临时视图选MAIN386，严格原FH私有写者得16M，25原片段/33原型调用通过；真实hook/共享同步/完整硬件与恢复仍缺，Windows仅虚拟屏协作待连接恢复。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    idxafter=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage57-native-resource-alias/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':f.PRIOR_SHA,
      'scope':'Compiled temporary quality match view and exact FH private16M writer with original bounded matcher/row/selector/default/partial pack. Explicit post-log and ownership inputs. No live hook or complete hardware/recovery.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_avcam_file_and_executable_code_unchanged':True,
        'new_code_only_guest_prototype_not_Sony_loadable_module':True,
        'UU_Windows_UI_observed_and_remote_handoff_attempted':True,
        'new_transfer_or_Windows_PnP_execution_proven':False,
        'camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for row in files:assert im.sha((root/row['path']).read_bytes())==row['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':25,'compiled_calls':33,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
