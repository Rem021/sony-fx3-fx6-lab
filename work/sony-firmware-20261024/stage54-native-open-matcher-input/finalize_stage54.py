#!/usr/bin/env python3
"""Review and seal existing native Open/quality evidence. No device replay."""
import ast
import collections
import datetime
import json
import struct
import open_matcher_input as f


def main():
    im=f.im;im.volume();stage=f.STAGE;root=f.ROOT
    prior=f.p.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((root/e['path']).read_bytes())==e['sha256']
    foundations={
      'stage32-resource-open-descriptor':'0ae57711bc1a8d5756c224de9c1666140700359789ae7a66ec9bcbc29f5807f2',
      'stage33-imola-format-matcher':'f1f5393b412f4f3fe26f0b399df5f010c9947b9641002d9fddf9637dbc30623b'}
    for name,pin in foundations.items():
        file=f.BASE/name/'final-receipt.json';assert im.sha(file.read_bytes())==pin
        for e in json.loads(file.read_text())['files']:
            assert im.sha((root/e['path']).read_bytes())==e['sha256']
    run=stage/'run-native-quality-and-tail-20261025';path=run/'open-matcher-input-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    source=stage/'open_matcher_input.py';tree=ast.parse(source.read_text())
    assert im.sha(source.read_bytes())==im.sha((run/'executed-source.py').read_bytes())==receipt['script_sha256']
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','observe_read','store','load'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    assert receipt['MPR_sha256']=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    provider=json.loads((f.p.STAGE/'run-coupled-geometry-20261025/source-receipt.json').read_text())
    for key in ('avcam_sha256','LIRO_sha256','kernel_sha256'):assert receipt[key]==provider[key]
    assert p['original_fragments']==24 and len(p['cases'])==4
    events=[e for x in p['cases'] for e in x['original_events']]
    counts=collections.Counter(e['reason'] for e in events)
    assert counts=={'returned':4,'boundary: after_original_kernel_memcpy_before_next_diagnostic':8,
      'boundary: before_unexecuted_diagnostic':8}
    for e in events:
        if e['reason']=='returned':assert e['SP_after']==hex(f.r.SP)
        assert not e.get('native_output_or_PC_return_adapter',False)
        assert not e.get('native_output_or_return_adapter',False)
    expected_roles=[1,1,2,1];expected_rows=[-1,386,-1,431]
    for i,x in enumerate(p['cases']):
        assert x['native_tail_words88_8c_90_94']==[expected_roles[i],10,25,0xc3c3c3c3]
        assert x['independent_native_matcher_row']==expected_rows[i]
        a,b=x['native_common_entry'],x['native_matcher_entry']
        assert a['owner']==b['owner']==hex(f.COMMON)
        assert a['input98_hex']==b['input98_hex']
        assert bytes.fromhex(a['input98_hex'])[:0x88]==bytes.fromhex(x['descriptor88_hex'])
        assert x['native_new_handler_id']==0 and x['source_UID_fixture']==0x2a
        assert x['native_new_handler_registered_in_map'] and x['pending_Open_queue_count_after_native_dequeue']==0
        native=x['original_events'][2];post=x['original_events'][4]
        for pc in (0x22f34c,0x229808,0x227cdc,0x228e40,0x227e0c,0x229014,0x21e26c,0x21ecf4,0x225eb8):
            assert hex(f.V+pc) in native['pcs'],hex(pc)
        assert native['pcs'][-2]==hex(f.V+0x225edc)
        assert native['SP_after']!=hex(f.r.SP)
        assert hex(f.V+0x226124) in post['pcs'] and hex(f.V+0x21ed1c) in post['pcs']
        assert post['pcs'][-2]==hex(f.V+0x21ed20)
        assert {(z['offset'],z['size']) for z in x['independent_matcher_tail_reads']}=={('0x88',4),('0x8c',4)}
    qualities=p['MPR_quality_comparison'];assert len(qualities)==2
    assert [(q['DefStruct_VQuality'],q['original_API_quality'],q['GetVideoBitrate_raw']) for q in qualities]==[(6,22,16000),(8,24,25000)]
    for q in qualities:
        assert q['original_quality_fragment']['reason']=='conversion block complete'
        assert q['original_bitrate_function']['reason']=='returned'
        for e in (q['original_quality_fragment'],q['original_bitrate_function']):
            assert not e['logging_return_nonconsumption_proofs']
            assert not any('stub' in z or 'logging_adapter' in z for z in e['calls'])
    failed=json.loads((stage/'run-20261025/last-phase-at-failure.json').read_text())
    assert failed['reason']=='unapproved execution '+hex(f.V+0x227ecc)
    early=json.loads((stage/'run-id-return-range-20261025/open-matcher-input-results.json').read_text())
    assert early['original_fragments']==20
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']
    roles=[]
    for i in range(14):
        at=struct.unpack_from('<Q',blob,0x32e5d0+i*8)[0]-f.V
        roles.append({'value':i,'original_name':im.cstring(blob,at),'string_offset':hex(at)})
    assert roles[1]['original_name']=='ENC_MAIN' and roles[2]['original_name']=='ENC_PROXY'
    assert im.dump(blob,0x227ecc,0x227ed0,f.V)[0]['asm'].strip()=='ret'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(stage.relative_to(root));ev=str(path.relative_to(root))
    refinement={'created_utc':now,'older_sealed_files_preserved':True,
      'stage33_appended_fixture_scope':'Old MAIN(2,10) and proxy(2,1) remain conditional fixtures; not claimed real field production.',
      'new_native_production':'Original queued Open writes88/8c/90. Classifier produces1 ENC_MAIN for HEVC MAIN and2 ENC_PROXY for proxy; this declared new-handler path keeps8c10. Current controls produce native(1,10)/(2,10).',
      '88_role_not_pixel_format_or_bit_depth':True,'original_role_names':roles,
      'original_role_name_getter':im.dump(blob,0x2297e4,0x229808,f.V),
      '94_prior_stack_seed_not_device_uninitialized_bug_or_globally_unused':True,
      'FF386_matches_under_new_native_MAIN_role_but_quality_still_artificial':True,
      'target_FH_does_not_match_original_table':True,
      'proxy_old2_1_row607_not_new_native2_10_result':True,
      'query_quality_alignment':'Original VQuality6 produces API22/raw16000; VQuality8 produces API24/raw25000. Changing to FF upstream is not a16M identity-preserving change.',
      'new_queued_Open_count0_is_not_code_exit_or_global_idle':True,
      'independent_post_diagnostic_matcher_not_whole_Open':True,
      'actual_queue_factory_epoch_source_graph_Hal_and_camera_recovery_unbound':True,'evidence':ev}
    im.write_json(stage/'scope-refinement.json',refinement)
    summary={'created_utc':now,'status':p['status'],'original_fragments':24,
      'native_Open_chain_case_events':dict(counts),'whole_common_ctor_cases':4,
      'native_roles_and_rows':[{k:x[k] for k in ('label','native_tail_words88_8c_90_94','independent_native_matcher_row')} for x in p['cases']],
      'original_quality_comparison':[{k:q[k] for k in ('DefStruct_VQuality','original_API_quality','GetVideoBitrate_raw')} for q in qualities],
      'native_queue_allocation_ID_map_common_to_matcher_call_chain_verified':True,
      'pending_queue0_but_native_stack_still_live':True,
      'native_tail_replaces_arbitrary_MAIN_role2_assumption_with_role1':True,
      'target_FH_quality_gap_resolved':False,'upstream_FF_selection_or16M_consistency_proven':False,
      'hardware_recording_or_recovery_proven':False,'proof_sha256':im.sha(path.read_bytes()),
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(stage/'summary.json',summary)
    im.write_json(stage/'coordinator-observations.json',{
      'created_utc':now,'reviewer':'Same agent source/native-byte/trace/hash review; no independent implementation or device replay.',
      'previous_stage17files_and_stage32_33_manifests_checked':True,
      '24original_fragment_receipts_and4common_constructor_stack_returns_checked':True,
      'native_contiguous_Open_consumer_classifier_alloc_ID_map_common_matcher_entry_PCs_checked':True,
      'source_descriptor_unchanged_and_tail_generated_by_original_code':True,
      'original_named_roles1_MAIN_2_PROXY_not_pixel_enums':True,
      'post_diagnostic_native_return_and_original_W23_capture_checked':True,
      'only88_8c_read_by_executed_matcher_tail_scope':True,
      'FH_missing_row_preserved_FF386_still_an_artificial_quality_control':True,
      'original_MPR_quality_and_rate_scalars_with_no_logging_stubs_checked':True,
      'current_source_observer_hooks_do_not_write_guest_memory_or_registers':True,
      'failed_range_attempt_and20fragment_intermediate_preserved':True,
      'UU_Windows_camera_files_drivers_modules_WBI_flash_operations':False,
      'full_Start_hardware_recording_backup_restore_or_independent_rescue_verified':False,
      'outcome':'PASS_NATIVE_OPEN_MATCHER_INPUT_WITH_QUALITY_AND_RUNTIME_DEVICE_GAPS'})
    canonical=f.BASE/'GOAL_STATUS.json';before=(stage/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.p.STAGE/'goal-status-after.json').read_bytes()
    g=json.loads(before);old=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=stage.name;g['research_activity']='engineering_progress_within_offline_authorization'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':old['progress_audit']['classification'],
      'basis':[
        '原22f34c队列消费到229808分类/handler分配/ID/map登记，再到21e26c原复制/清零/分派、21ecf4和225eb8入口，真实原调用链到首诊断前；4组完整common构造和调用链通过，工厂空闲队列/node等仍是声明输入。',
        '原MAIN尾88=1/ENC_MAIN、8c10、9025，proxy88=2/ENC_PROXY；94保持C3栈输入，原匹配只读88/8c。此前MAIN人工2实际是proxy角色，仍保留为条件对照而非实机来源。',
        '独立后诊断客体消费前段实际生成98字节，原matcher返回到原调用者W23：FH-1，人工FF386，proxy2/10为-1，UHD431。新来源闭合不等完整Open或原诊断执行，FH质量缺口仍未解决。',
        '原MPR VQuality6→API22/raw16000，而VQuality8→API24/raw25000，直接上层换FF不能保持16M查询身份；24段有界原执行无原输出/日志/锁/HAL替身。',
        'Open待处理队列已0时原栈仍在matcher中且handler已登记，队列0不作全局退出或恢复条件；实际MAIN/同步/质量对齐/硬件与同机恢复验收仍缺。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage54_native_open_matcher_input']={
      'readme':rel+'/README.md','proof':ev,'summary':rel+'/summary.json',
      'review':rel+'/coordinator-observations.json','refinement':rel+'/scope-refinement.json',
      'scope':'Original queued Open allocation/ID/map/common-to-matcher entry on declared queues and descriptors; post-diagnostic matcher is a separate guest. MPR quality/rate scalar comparison; no actual MAIN/fullOpen/Start/Hal or device recovery.',
      'original_fragments':24,'native_MAIN_role':1,'native_proxy_role':2,
      'FH_quality_alignment_resolved':False,'goal_complete':False,'authorization_unchanged':True}
    g['corrections_to_prior_stage']['native_Open_matcher_tail_role_provenance']={
      'prior_stage33_MAIN_extra2_10':'Conditional artificial fixture;2 is ENC_PROXY role, not observed MAIN input pixel format.',
      'new_scope':'Original new-handler queued Open produces(1 ENC_MAIN,10) for MAIN, (2 ENC_PROXY,10) for proxy; old proxy(2,1)607match not promoted to this route.',
      'native_FF386_match_does_not_solve_upstream_quality_or16M_identity':True,
      'old_files_preserved':True,'evidence':[ev,rel+'/scope-refinement.json']}
    addition=' stage54原Open队列消费/分配/ID/map登记/common构建器到matcher首诊断的调用桥执行，生成MAIN尾(1 ENC_MAIN,10,25)；旧MAIN人工2对应ENC_PROXY。独立后诊断原matcher用实际生成输入返回到原调用者：FH-1、人工FF386、proxy(2,10)-1、UHD431，24段验证通过。原VQuality8→API24/raw25000，不能直接替换现VQuality6→API22/raw16000而称16M一致。完整诊断/状态/同步/实际MAIN/上层质量选择与query/cache/mux、Start/HAL和同机恢复仍缺；队列0时原栈仍在途。'
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/scope-refinement.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='确定16M候选在上层VQuality/API质量、资源FF预置选择和mux/查询/缓存中的一致身份与受限转换位置；原FH不匹配仍未解决，不把VQuality8/raw25000或人工FF命中当作16M已实现。继续原队列提交/状态与已有handler分支、完整诊断/同步/Start和硬件完成，保持实际备份/恢复/冷启动全部要求。'
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(stage/'goal-status-after.json',g);after=(stage/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before;canonical.write_bytes(after)
    index=root/'README.md';idxbefore=index.read_bytes();txt=idxbefore.decode()
    entry='- [2026-10-25 FX3 原Open队列与匹配输入来源](<work/sony-firmware-20261024/stage54-native-open-matcher-input/README.md>)：24段原执行接通分配/登记/common到matcher入口，MAIN尾角色1已绑定；FH仍不匹配，改上层FF会改变码率查询，完整启动/硬件与恢复仍待验收。'
    assert entry not in txt and txt.count('## 相机与固件研究\n')==1
    idxafter=txt.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert index.read_bytes()==idxbefore;index.write_bytes(idxafter)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(stage.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage54-native-open-matcher-input/1','created_utc':now,'volume_uuid':im.VOLUME,
      'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
      'scope':'24 bounded original fragments: queued Open classifier/handler allocation/ID/map/common-to-matcher entry; native tail1MAIN/2proxy and independent matcher return; original MPR quality/rate comparison. No full Open/diagnostics/Start/Hal/hardware/recovery; FH alignment still missing.',
      'mutable_progress':{'path':str(canonical),'before_snapshot':rel+'/goal-status-before.json','after_snapshot':rel+'/goal-status-after.json',
        'before_sha256':im.sha(before),'after_sha256':im.sha(after),'policy':'Canonical mutable; stage snapshots immutable.'},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(idxbefore),'readme_index_after_sha256':im.sha(idxafter),
      'operations':{'original_guest_code_unchanged':True,'queues_free_slots_ID_nodes_descriptors_and_UID_are_fixtures':True,
        'independent_post_diagnostic_copy_is_not_executed_log':True,
        'native_output_PC_return_log_lock_or_HAL_adapter':False,'new_loadable_camera_module':False,
        'UU_Windows_camera_interfaces_auth_modes_drivers_files_modules_WBI_flash':False,
        'real_hardware_recording_backup_restore_or_independent_recovery':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(stage/'final-receipt.json',final)
    for e in files:assert im.sha((root/e['path']).read_bytes())==e['sha256']
    assert canonical.read_bytes()==after and index.read_bytes()==idxafter
    print(json.dumps({'sealed_files':len(files),'final_manifest_sha256':im.sha((stage/'final-receipt.json').read_bytes()),
      'latest_stage':g['latest_stage'],'original_fragments':24,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
