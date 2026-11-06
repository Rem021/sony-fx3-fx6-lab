#!/usr/bin/env python3
"""Seal verified native manager/factory evidence without replay."""
import ast
import collections
import datetime
import json
import manager_factory as f


def main():
    im=f.im;im.volume();s=f.STAGE;root=f.ROOT
    assert not (s/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((root/x['path']).read_bytes())==x['sha256']
    run=s/'run-object-isolation-20261026';path=run/'manager-factory-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    assert im.sha((s/'manager_factory.py').read_bytes())==receipt['script_sha256']==im.sha((run/'executed-source.py').read_bytes())
    for node in ast.walk(ast.parse((s/'manager_factory.py').read_text())):
        if isinstance(node,ast.FunctionDef) and node.name=='code':
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for file,key in ((f.n.STAGE/'official-files/nflasha15/kmod/liro.ko','LIRO_sha256'),
      (f.n.STAGE/'official-files/nflasha3/vmlinux.bin','kernel_sha256'),
      (f.prev.prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o','wrapper_object_sha256'),
      (f.prev.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o','writer_object_mapped_not_executed_sha256')):
        assert im.sha(file.read_bytes())==receipt[key]
    cases=p['cases'];assert len(cases)==3
    assert [c['expected_native_row'] for c in cases]==[386,386,431]
    assert [c['seed'] for c in cases]==[0xa5,0xc3,0xc3]
    events=[e for c in cases for e in c['events']];counts=collections.Counter(e['reason'] for e in events)
    assert len(events)==p['bounded_fragments']==21
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':3,'returned':12,
      'boundary: before_original_buffer_channel_preparation':3,
      'boundary: before_original_unexecuted_resource_provider':3}
    for c in cases:
        assert c['native_manager']==hex(f.MANAGER) and c['native_common']==hex(f.COMMON)
        assert c['original_common_constructors']==[hex(f.COMMON+i*0xe518) for i in range(6)]
        assert c['original_proxy_constructors']==[hex(f.FACTORY+0x56080+i*0x269b0) for i in range(2)]
        assert len(c['manager_constructor_real_memset_calls'])==25
        assert collections.Counter(x['size'] for x in c['manager_constructor_real_memset_calls'])=={
          0x2a90:8,0x90:1,0x650:8,0x1010:8}
        assert all(x['fill']==0 for x in c['manager_constructor_real_memset_calls'])
        for e in c['events'][2:5]:
            assert e['full_guest_arena_outside_constructed_object_unchanged']
            assert e['SP_before']==e['SP_after']==hex(f.r.SP)
        assert c['events'][2]['constructed_object_range']==[hex(f.MANAGER),hex(f.MANAGER+f.MANAGER_SIZE)]
        for e in c['events'][3:5]:
            assert e['constructed_object_range']==[hex(f.FACTORY),hex(f.FACTORY+f.FACTORY_SIZE)]
        bindings=c['native_manager_bindings'];assert len(bindings)==8
        assert all(x['manager']==hex(f.MANAGER) for x in bindings)
        assert [x['caller'] for x in bindings]==[hex(f.V+0x226e88)]*6+[hex(f.V+0x226ebc)]*2
        assert c['native_free_queues_initialized']=={'free_ids':8,'free_main_slots':6,'free_proxy_slots':2,'free_main_map_nodes':6}
        assert c['queue_counts_after_request']=={'ids':7,'main_slots':5,'main_map_nodes':5}
        assert c['actual_matcher_returns'][0]['W0']==c['expected_native_row']
        prefix,cont=c['events'][5:7]
        assert prefix['stop_pc']==cont['start_pc']==hex(f.V+0x21dd54)
        assert prefix['SP_after']==cont['SP_before']=='0x10007ac0'
        assert not cont['independent_entry_fixture'] and cont['stop_pc']==hex(f.V+0x27bdb4)
        assert len(c['channel_entries'])==len(c['provider_entries'])==1
        ch=c['channel_entries'][0];assert ch['body_executed'] and ch['x0_x4'][0]==hex(f.MANAGER)
        pro=c['provider_entries'][0]
        assert not pro['body_executed'] and not pro['provider_return_adapter']
        assert pro['x0_x5']==['0x61003c','0x10007968','0x470','0x11','0x0','0x806800f3']
        assert pro['LR']==hex(f.V+0x22d3fc) and pro['SP']=='0x10007950'
        for at in (0x22d394,0x22de54,0x22de94,0x22de98,0x22d3c4,0x22d3f8,0x27bdb4):
            assert hex(f.V+at) in cont['pcs']
        assert len(c['original_diagnostics'])==4
        assert not c['real_OS_singleton_task_threads_locks_provider_Hal_recording_or_recovery']
        assert not c['independent_private16M_writer_or_actual_writer_hook_executed_here']
        assert all(not (f.prev.old.CODE<=int(pc,16)<f.prev.old.CODE+0x10000)
          for e in c['events'] for pc in e['pcs'])
    initial=s/'run-20261026';oldproof=json.loads((initial/'manager-factory-results.json').read_text())
    oldrec=json.loads((initial/'source-receipt.json').read_text())
    assert oldproof['status']==p['status'] and oldproof['bounded_fragments']==21
    assert im.sha((initial/'executed-source.py').read_bytes())==oldrec['script_sha256']
    audit=json.loads((s/'provider-source-audit.json').read_text())
    assert audit['avcam_sha256']==im.sha(blob) and audit['LIRO_sha256']==receipt['LIRO_sha256']
    assert audit['table_base_from_original_header']==hex(f.V+0x1a4)
    assert not audit['executed_actual_provider_OSAL_threads_memory_allocator_sync_message_or_Hal']
    assert im.sha((root/audit['provider_module']).read_bytes())==audit['provider_module_sha256']
    expected={'osal_valloc_msg_wait':'0x398','osal_snd_sync_msg':'0x368','osal_free_msg':'0x3a0','osal_set_msg_src':'0x3c8'}
    assert {x['symbol']:x['LIRO_init_data_relocation_offset'] for x in audit['imports']}==expected
    assert {x['symbol'] for x in audit['provider_definitions']}==set(expected)
    for region in [*p['original_regions'],*audit['regions'],*audit['imports']]:
        for ins in region['instructions']:
            at=int(ins['va'],16)-f.V;assert blob[at:at+4].hex()==ins['bytes']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(root));ev=str(path.relative_to(root))
    summary={'created_utc':now,'status':p['status'],'bounded_fragments':21,'stop_counts':dict(counts),
      'per_case_native_manager_clear_calls':25,'per_case_common_proxy_ctors':[6,2],
      'per_case_native_bindings':8,'per_case_native_queues_initial':[8,6,2,6],
      'per_case_after_MAIN_ids_slots_nodes':[7,5,5],'outside_object_arena_checks':9,
      'OSAL_imports_and_provider_definitions_static':4,'provider_executed':False,
      'goal_complete':False,'persistent_write_release':False,'proof_sha256':im.sha(path.read_bytes())}
    review={'created_utc':now,'reviewer':'Same-agent original-byte/source/trace/hash review; no independent or physical replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'previous15files_and_canonical_verified':True,'original_manager_constructor_25native_clear_calls':True,
      'original_factory_6plus2_ctors_binding_and_native_free_queue_reset_completed':True,
      'full_arena_outside_each_object_unchanged_in_nine_checks':True,
      'external_request_dispatcher_header_and_muted_logger_inputs_still_declared':True,
      'channel_body_now_really_executed_observer_correctly_updated':True,
      'no_artificial_allocator_reply_thread_or_current_task_state':True,
      'header_base_vs_LIRO_copy_offset_used_in_symbol_mapping':True,
      'provider_module_original_symbols_found_but_not_loaded_or_executed':True,
      'UU_Windows_or_camera_operations':False,'outcome':'PASS_NATIVE_CONSTRUCTION_AND_QUEUES_WITH_PROVIDER_AND_PHYSICAL_GAPS'}
    canonical=f.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      'stage61封存15件及canonical复核，继续追其真实manager缺口。',
      '原manager22cc8c完成25次原memset；原factory226d2c构造6MAIN+2其它编码对象并8次原setter绑定；原2270d4初始化ID8/MAIN6/其它2/map-node6。',
      '三组目标A5/C3和原UHD各21段中的7段通过；每组三个原构造/重置前后全arena对象外保持，合计9次隔离检查；没有宿主补写ID/handler/node队列。',
      '原queued请求自然取得第一个原构造handler，计数为7/5/5；同状态继续原22d394及缓存miss，抵达27bdb4提供者入口，未执行其体/补分配或回复。',
      '静态由原header表基址1a4与LIRO复制起点1ec对应4个OSAL消息符号，已有原osal_uipc.ko定义均找到；未加载或执行该模块、真实线程或单例启动。',
      '旧通过结果保留，增加对象隔离检查另存正式结果；全部16要求/相机授权/硬件成片与同机恢复未变，未操作UU或Windows。'],
      'completion_not_claimed':True}
    # Keep the wording of the global count precise: three cases, 7 fragments each.
    g['progress_audit']['basis'][2]='三组目标A5/C3和原UHD各7段，共21段通过；每组三个原构造/重置前后全arena对象外保持，合计9次隔离检查；没有宿主补写ID/handler/node队列。'
    g['latest_stage_evidence']['stage62_native_manager_factory']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','provider_audit':rel+'/provider-source-audit.json',
      'bounded_fragments':21,'scope':'Original manager/factory6plus2/setter/free queue initialization; same native request reaches unexecuted resource provider. Partial dispatcher/logger/external storage inputs remain; no real OS or hardware.',
      'goal_complete':False,'authorization_unchanged':True}
    addition=' stage62原manager/factory6+2/8次setter/空闲队列初始化完成，目标A5/C3及UHD共21段、9次对象外全arena隔离通过。原请求使ID/MAIN/map-node从8/6/6到7/5/5，不再手填这些队列；通道body及cache miss执行到未执行的27bdb4提供者入口。静态定位4个OSAL消息导入及osal_uipc定义，未加载/执行提供者/线程，实际单例/锁/owner代次/硬件及同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/provider-source-audit.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='核对原osal_uipc.ko四个消息提供者符号及其重定位、初始化/内核依赖，推进27bdb4→27bec8→99004原消息路径直到实际未绑定服务边界；不伪造线程/current-task/分配/物理缓冲区或同步回复。继续真实writer接合、共享锁/owner代次/完成通知、日志时间/输出寿命与全部硬件/同机恢复要求。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    index=root/'README.md';ib=index.read_bytes();text=ib.decode()
    entry='- [2026-10-26 FX3 原管理对象与factory队列](<work/sony-firmware-20261024/stage62-native-manager-factory/README.md>)：原manager、6+2构造/绑定及空闲队列21段通过，9次对象外隔离；请求进到未执行资源提供者，真实OSAL/硬件/主录与恢复未验收。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    ia=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    im.write_json(s/'summary.json',summary);im.write_json(s/'coordinator-observations.json',review)
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(s.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage62-native-manager-factory/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
      'previous_manifest_sha256':f.PRIOR_SHA,
      'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
      'operations':{'original_firmware_unchanged':True,'Sony_loadable_payload_exported':False,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'actual_provider_threads_Hal_recording_backup_restore_or_independent_rescue':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((root/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
      'latest_stage':s.name,'bounded_fragments':21,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
