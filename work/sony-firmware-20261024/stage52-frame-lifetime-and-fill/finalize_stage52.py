#!/usr/bin/env python3
"""Review existing stage52 receipts and seal them once; no native/device replay."""
import ast
import collections
import datetime
import json
import struct
import frame_lifetime as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    prior=f.f.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    prior_files=json.loads(prior.read_text())['files']
    for e in prior_files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    run=stage/'run-bounded-string-compare-20261025'
    result_path=run/'frame-lifetime-results.json';p=json.loads(result_path.read_text())
    src=stage/'frame_lifetime.py';executed=run/'executed-source.py'
    receipt=json.loads((run/'source-receipt.json').read_text())
    assert im.sha(src.read_bytes())==im.sha(executed.read_bytes())==receipt['script_sha256']
    tree=ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store','load'):
            for call in ast.walk(node):
                assert not (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and call.func.attr in ('mem_write','reg_write'))
    assert not any(isinstance(x,ast.FunctionDef) and x.name in ('code','store','load') for x in ast.walk(tree))
    assert len(p['original_events'])==p['original_fragments']==193
    reasons=collections.Counter(e['reason'] for e in p['original_events'])
    assert reasons=={
      'returned':180,'boundary: after_original_kernel_memcpy_before_next_diagnostic':7,
      'boundary: after_original_tag_getter_and_record_validity_store':3,
      'boundary: before_unexecuted_diagnostic':2,'boundary: before_unbound_runtime_notification':1}
    for e in p['original_events']:
        if e['reason']=='returned':assert e['SP_after']==hex(f.r.SP)
        assert not e.get('native_output_or_return_adapter',False)
        assert not e.get('native_output_or_PC_return_adapter',False)
    states=p['lifetime_cases'][0]['states']
    assert [(s['queued_indices'],s['active_slots']) for s in states]==[(40,40),(0,40),(0,39),(1,40),(1,40),(0,39)]
    assert states[2]['selected_geometry_u16']==[1920,1080]
    assert states[3]['selected_geometry_u16']==[0,0]
    assert states[4]['flags'][0]==[1,0,1] and states[5]['flags'][0]==[0,0,0]
    other=p['lifetime_cases'][1]['states'][0]
    assert other['queued_indices']==40 and other['active_slots']==0
    assert all(v==[0,0,0] for v in other['flags'])
    notes=p['notification_cases'];assert len(notes)==2
    assert [(c['state']['queued_indices'],c['state']['flags'][0]) for c in notes]==[(1,[1,0,0]),(0,[1,1,0])]
    assert notes[0]['state']['selected_record_63c']==7
    geo=p['geometry_tag_cases'];assert len(geo)==3
    assert [x['record_valid_byte'] for x in geo]==[1,0,0]
    assert [x['record_geometry_u16'] for x in geo]==[[1920,1080],[0,0],[0,0]]
    assert geo[0]['record_format_byte36']==5
    assert bytes.fromhex(geo[0]['record_prefix_hex'])[8:]==bytes.fromhex(geo[0]['fixture_tag_payload_hex'])
    for x in geo[1:]:assert bytes.fromhex(x['record_prefix_hex'])==bytes(0x50)
    failed_dir=stage/'run-20261025'
    failed=json.loads((failed_dir/'last-phase-at-failure.json').read_text())
    assert failed['reason']=='unapproved execution '+hex(f.V+0x11e0)
    assert not json.loads((failed_dir/'attempt-failure.json').read_text())['passing_result']
    assert not (failed_dir/'frame-lifetime-results.json').exists()
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    assert im.dump(blob,0x1290,0x1294,f.V)[0]['asm'].strip()=='ret'
    assert im.dump(blob,0x1294,0x1298,f.V)[0]['asm']=='udf #0'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel=str(stage.relative_to(root));ev=str(result_path.relative_to(root))
    contract={
      'schema':'fx3-frame-lifetime-observation-contract/1','created_utc':now,
      'scope':'Design constraints only; no active probe, native gate or restore implementation.',
      'current_camera_authorization':'Windows cached PnP only; all camera handles/auth/modes/drivers/files/modules/WBI/writes remain unauthorized.',
      'local_observations':[
        {'field':'controller+0x947a8','meaning':'queued-index count','required_at_data_restore':'0 with current owner and synchronization established','sufficient_alone':False},
        {'field':'controller+0x8ade0+3*i','meaning':'active/marker1/marker2 per frame slot','required_at_data_restore':'all current active slots released; flags alone do not prove queue or hardware completion','sufficient_alone':False},
        {'field':'record+0/+8..+0x4f','meaning':'tag-validity byte and48byte source payload','required_before_submit':'successful current-frame production after native allocation clear','sufficient_alone':False},
        {'field':'record+0x630/+0x63c','meaning':'optional runtime notification branch inputs; full business semantics unbound','required_before_dequeue_completion':'real notification call and error/timeout semantics when selected','sufficient_alone':False}],
      'required_evidence_not_yet_implemented_or_verified':[
        'Actual same-body fingerprints, runtime address/owner and pool binding; MAIN and packet UID namespaces kept distinct.',
        'Admission closed under the real common synchronization; no producer can borrow, fill or publish a new frame.',
        'Current queued indices drained and all current active slots returned without inventing notification or HAL success.',
        'Original callback identities, owner lifetime and generation proven current; index-only duplicate not accepted as current completion.',
        'Producer, consumer, callback and relevant native code stacks exited; flags and queue count do not prove code exit.',
        'Hardware STOP/completion, mapping unmap and all other parameter/buffer consumers independently settled.',
        'Same-body healthy backup, scoped prior bytes and restore/readback; actual cold boot and independent recovery verified separately.'],
      'explicitly_insufficient':['queued count0','all slot flags0','composite return1','reused slot number','one successful tag copy','pure VCD predicate0','static firmware dump'],
      'late_callback_reachability_or_real_camera_ABA_bug_proven':False,
      'real_notification_Hal_stop_current_epoch_or_global_quiescence_proven':False,
      'active_probe_ready':False,'restore_ready':False,'persistent_write_release':False,'goal_complete':False,
      'evidence':ev}
    im.write_json(stage/'restore-observation-contract.json',contract)
    summary={'created_utc':now,'status':p['status'],'original_fragments':193,
      'original_stop_reasons':dict(reasons),'queue_zero_with40active_slots':True,
      'queue40with_zero_active_slots':True,'native_reborrow_clears_old_record':True,
      'index_only_control_is_not_actual_late_callback_proof':True,
      'notification_not_faked_and_queue_not_decremented_at_boundary':True,
      'original_tag_copy48bytes_and_native_validity_store':True,
      'geometry_tag_cases':[{k:x[k] for k in ('name','record_valid_byte','record_geometry_u16','record_format_byte36')} for x in geo],
      'full_event_fill_current_MAIN_hardware_or_recovery':False,
      'first_attempt_boundary_failure_preserved':True,'proof_sha256':im.sha(result_path.read_bytes()),
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    review={'created_utc':now,'reviewer':'Same agent source/native-byte/trace/hash review; no independent implementation or camera replay.',
      'prior_stage_files_verified':len(prior_files),'193_original_fragment_receipts_and180_original_stack_returns_checked':True,
      'executed_source_matches_receipt':True,'no_new_memory_register_output_hooks':True,
      'controlled_queue_vs_slot_counterexamples_verified':True,
      'old_record_retained_on_flag_clear_and_erased_by_original_allocator_verified':True,
      'index_only_order_not_asserted_reachable_in_real_Sony_scheduler':True,
      'original_notification_boundary_and_off_branch_verified':True,
      'original_tag_lookup_copy_and_native_caller_validity_store_verified':True,
      'fixture_container_not_live_camera_tag_and_full_fill_unexecuted':True,
      'first_unapproved_compare_endpoint_expanded_to_actual_original_ret_no_code_patch':True,
      'old_stage_history_and_failed_attempt_preserved':True,
      'UU_Windows_camera_driver_file_module_WBI_flash_operations':False,
      'outcome':'PASS_BOUNDED_LIFETIME_AND_SOURCE_GETTER_WITH_RUNTIME_AND_PHYSICAL_GAPS'}
    im.write_json(stage/'coordinator-observations.json',review)

    path=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert path.read_bytes()==before==(f.f.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name
    g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
      'basis':[
        '原40项队列出队到0时40槽仍active，再借失败；另一原双marker对照全flags0时队列仍40，再借也失败。收紧+947a8为queued-index count，不是active-slot count。',
        '原双marker/清flag/出队及复借执行，清flag保留记录、复借原清3352字节；索引重复控制说明低层索引不表达代次，但未证实真实迟到回调或相机ABA缺陷。',
        '原可选通知分支停在27c1a8前，队列未减；关闭条件对照原出队返回。未提供通知、日志或同步返回替身。',
        '原源端标签查找/48字节复制及调用者valid字节写入，在声明标签输入上生成record+36/+3e/+40的5/1920/1080；不同key/无root保持无效零记录。真实标签生产/完整fill/MAIN与硬件仍缺。',
        '193段有界原执行通过，保留首次原strcmp许可范围停止；恢复观察设计同时要求queue/active/owner/epoch/同步/代码退出及HAL，未降低实机或救援目标。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage52_frame_lifetime_and_fill']={
      'readme':rel+'/README.md','proof':ev,'summary':rel+'/summary.json',
      'review':rel+'/coordinator-observations.json','restore_observation_contract':rel+'/restore-observation-contract.json',
      'scope':'Original return/dequeue/reuse and bounded source tag getter/caller validity store on declared map/owner/event fixtures. No actual callback generation, notifications, full fill/Start, HAL or camera recovery.',
      'original_fragments':193,'queue_zero_not_active_zero':True,'active_zero_not_queue_zero':True,
      'actual_source_tag_or_MAIN_owner_bound':False,'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['queued_index_count_vs_active_slots']={
      'previous_stage51_wording':'使用计数 for +947a8 was provisional; frame-slot index namespace remains valid.',
      'current_scope':'Original enqueue/dequeue shows +947a8 queued-index count. Native flags can remain active with count0, or all clear with count40 on explicit ordered fixtures.',
      'global_idle_or_Hal_completion_proven':False,'old_files_preserved':True,'evidence':ev}
    addition=' stage52原归还/出队/复用与源标签片段193段验证：+947a8是索引队列计数，queue0可有40active，allflags0可有queue40；清flag不擦记录，原复借才清3352字节。可选通知27c1a8未执行，代次/同步/代码退出/HAL仍缺；索引重复受控次序不证明实机迟到回调。原48字节标签getter及调用者valid写入在声明输入上生成5/1920/1080，不同key/无root保持无效。完整fill/真实标签生产/当前MAIN绑定与硬件、同机恢复仍未闭合。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/restore-observation-contract.json']);req['remaining']+=addition
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    g['next_safe_offline_actions'][0]='追1479d8完整源端帧填充与0a3f3c标签的实际上游生产/格式/几何身份；接27c1a8原通知及真实锁/代次/回调所有权，不以queue0或flags0代替全局退出。补完整Start元数据、默认查询、日志/共享同步、VCD完整Start和硬件完成；保持FH质量缺口及全部实机/恢复验收。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert path.read_bytes()==before;path.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 帧槽归还、队列与标签来源](<work/sony-firmware-20261024/stage52-frame-lifetime-and-fill/README.md>)：193段原执行区分queue0与槽归还，复借清记录；原标签复制生成几何，通知/代次/完整填充、硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage52-frame-lifetime-and-fill/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'193 bounded original fragments: independent queue/slot lifetime, native return/dequeue/reuse, unexecuted optional notification boundary, source tag lookup/copy and native validity. No full event fill/runtime owner/epoch/Start/HAL/recording/recovery.',
      'mutable_progress':{'path':str(path),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_guest_code_unchanged':True,'map_owner_tag_and_controlled_order_are_fixtures':True,
        'native_output_PC_return_log_lock_notification_or_HAL_adapter':False,
        'real_camera_late_callback_or_ABA_bug_claimed':False,'new_loadable_camera_module':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for e in files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    assert path.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':193,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
