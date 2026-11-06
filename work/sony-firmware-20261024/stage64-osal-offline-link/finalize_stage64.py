#!/usr/bin/env python3
"""Review original relocation/native boundary evidence, seal without replay."""
import ast
import collections
import datetime
import json
import struct
import link_modules as f


def main():
    im=f.im;im.volume();s=f.STAGE;root=f.ROOT
    assert not (s/'final-receipt.json').exists()
    prior=f.prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((root/x['path']).read_bytes())==x['sha256']
    linkrun=s/'link-run-20261026';lpath=linkrun/'module-relocation-results.json'
    linked=json.loads(lpath.read_text());lrec=json.loads((linkrun/'source-receipt.json').read_text())
    assert im.sha((s/'link_modules.py').read_bytes())==lrec['script_sha256']==im.sha((linkrun/'executed-source.py').read_bytes())
    modules,providers,kernel=f.build()
    comparable=[m.facts() for m in modules.values()]
    for row in comparable:row['relocation_counts']={str(k):v for k,v in row['relocation_counts'].items()}
    assert comparable==linked['modules']
    assert linked['total_relocations']==973 and linked['unique_external_provider_names']==54
    assert linked['combined_relocation_counts']=={'257':453,'283':460,'261':60}
    assert [len(m.relocations) for m in modules.values()]==[70,91,812]
    # Decode each saved field and check its claimed original target, rather
    # than treating the linker status text as proof of correct application.
    for module in modules.values():
        for rel in module.relocations:
            value=int.from_bytes(bytes.fromhex(rel['relocated_hex']),'little');place=int(rel['P'],16)
            target=int(rel['S_plus_A'],16)
            if rel['type']==257:assert value==target
            elif rel['type']==261:
                if value&(1<<31):value-=1<<32
                assert place+value==target
            else:
                assert value&0xfc000000==0x94000000
                delta=value&0x3ffffff
                if delta&(1<<25):delta-=1<<26
                assert place+delta*4==target
    run=s/'native-run-pointer-array-20261026';npath=run/'native-osal-results.json'
    p=json.loads(npath.read_text());rec=json.loads((run/'source-receipt.json').read_text())
    assert rec['linker_source_sha256']==lrec['script_sha256'] and rec['link_proof_sha256']==im.sha(lpath.read_bytes())
    assert im.sha((s/'native_osal.py').read_bytes())==rec['script_sha256']==im.sha((run/'executed-source.py').read_bytes())
    for node in ast.walk(ast.parse((s/'native_osal.py').read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    assert rec['kernel_sha256']==im.sha(kernel)
    assert rec['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    assert rec['LIRO_sha256']==im.sha((f.n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes())
    assert rec['wrapper_sha256']==im.sha((f.prev.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    requests=p['requests'];setters=p['independent_source_setters'];inits=p['independent_init_entries']
    assert len(requests)==3 and len(setters)==len(inits)==2
    groups=requests+setters+inits;events=[e for c in groups for e in c['events']]
    counts=collections.Counter(e['reason'] for e in events)
    assert len(events)==p['bounded_fragments']==33
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':7,'returned':18,
      'boundary: before_original_buffer_channel_preparation':3,
      'boundary: before_original_unexecuted_kernel_service':5}
    uipc=modules['osal_uipc.ko'];text=uipc.section('.text')['base'];bss=uipc.section('.bss')['base']
    assert [(c['seed'],c['native_row']) for c in requests]==[(0xa5,386),(0xc3,386),(0xc3,431)]
    slots={'osal_valloc_msg_wait':0x398,'osal_snd_sync_msg':0x368,'osal_free_msg':0x3a0,'osal_set_msg_src':0x3c8}
    for c in requests:
        assert len(c['import_bindings'])==4
        for bind in c['import_bindings']:
            name=bind['name'];assert bind['LIRO_init_data_offset']==hex(slots[name])
            assert bind['actual_avcam_slot']==hex(f.V+0x1ec+slots[name])
            assert bind['original_module_target']==hex(uipc.exports[name]['address'])
        branch=c['allocation_branch'];assert branch['indirect_branch_executed'] and not branch['buffer_or_OSAL_return_adapter']
        assert branch['branch_X4']==hex(uipc.exports['osal_valloc_msg_wait']['address'])
        assert c['native_OSAL_entry']['pc']==branch['branch_X4']
        assert c['native_OSAL_entry']['x0_x3']==['0x61003c','0x10007548','0xd8','0x1']
        assert c['native_OSAL_entry']['LR']==hex(f.V+0x9911c)
        cache=c['empty_client_cache'];assert cache['client_id']==60 and cache['loaded_X21']=='0x0'
        assert cache['slot_address']==hex(bss+0x2640+0x10+60*8) and cache['slot_bytes']==bytes(8).hex()
        lock=c['native_OSAL_lock_entry'];assert lock['pc']==hex(text+0x1b8)
        assert lock['object']==hex(bss+0x2640) and lock['initial_object16_hex']==bytes(16).hex()
        dep=c['kernel_service_boundary'];assert dep['names']==['_raw_spin_lock_irqsave']
        assert dep['pc']==hex(providers['_raw_spin_lock_irqsave']['address']) and dep['LR']==hex(text+0x1cc)
        assert dep['x0_x5'][0]==lock['object'] and not dep['kernel_body_executed']
        assert not dep['kernel_return_IRQ_lock_thread_or_allocation_adapter']
        assert c['source_and_common_descriptor_unchanged'] and c['module_sections_remain_relocated_initial_bytes']
        e=c['events'][-1];assert not e['independent_entry_fixture']
        assert c['events'][-2]['stop_pc']==e['start_pc']==hex(f.V+0x21dd54)
        seq=[f.V+0x2f038,text+0x44c0,text+0x3248,text+0x3290,text+0x2ee8,text+0x1b8,int(dep['pc'],16)]
        positions=[e['pcs'].index(hex(pc)) for pc in seq];assert positions==sorted(positions)
        assert not c['module_driver_init_kernel_lock_allocator_reply_or_hardware_complete']
    for c,value in zip(setters,(0x806800f3,0x12345678)):
        expected=bytearray([0x5a]*128);struct.pack_into('<I',expected,20,value)
        assert c['value']==hex(value) and c['output128_hex']==expected.hex()
        assert c['only_payload_minus12_four_bytes_changed'] and c['independent_storage_not_a_real_OSAL_allocation_or_full_message_send']
        assert c['events'][-1]['start_pc']==hex(uipc.exports['osal_set_msg_src']['address'])
        assert c['events'][-1]['reason']=='returned' and c['events'][-1]['SP_after']==hex(f.r.SP)
    for c,name in zip(inits,('osal_uipc.ko','osal_utm.ko')):
        module=modules[name];dep=c['registration_boundary'];array=c['original_driver_pointer_array']
        assert c['module']==name and dep['names']==['udif_driver_register'] and not dep['kernel_body_executed']
        assert array['address']==dep['x0_x5'][0]=='0x10007ff8' and array['count']==1
        assert dep['x0_x5'][1]=='0x1' and array['driver_pointer']==dep['x0_x5'][2]
        data=module.section('.data');assert data['base']<=int(array['driver_pointer'],16)<data['base']+data['size']
        assert c['events'][-1]['start_pc']==hex(module.address('init_module'))
        assert not c['registration_callbacks_or_runtime_driver_initialization_executed']
    boundary=json.loads((s/'kernel-boundary-audit.json').read_text())
    assert boundary['kernel_sha256']==im.sha(kernel) and not boundary['native_kernel_or_callback_execution_here']
    for b in boundary['boundaries']:
        assert b['static_kernel_address']==hex(providers[b['symbol']]['address'])
        for ins in b['instructions_not_executed']:
            at=int(ins['va'],16)-f.n.K;assert kernel[at:at+4].hex()==ins['bytes']
    assert boundary['first_callback_direct_call_to_inner']['S_plus_A']==hex(uipc.address('k_uipc_init'))
    assert boundary['ops_first_callback_pointer']==hex(uipc.section('.init.text')['base'])
    assert boundary['inner_callback_pointer']==hex(uipc.address('k_uipc_init'))
    first=json.loads((s/'native-run-20261026/attempt-failure.json').read_text())
    second=json.loads((s/'native-run-typed-plan-20261026/attempt-failure.json').read_text())
    assert not first['passing_result'] and "m.facts()" in first['traceback']
    assert not second['passing_result'] and "data['base']<=address" in second['traceback']
    assert not json.loads((s/'audit-attempt-direct-callback/attempt-failure.json').read_text())['passing_result']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(root));ev=str(npath.relative_to(root))
    summary={'created_utc':now,'status':p['status'],'module_relocations':973,
      'combined_relocation_counts':linked['combined_relocation_counts'],'unique_provider_names':54,
      'bounded_fragments':33,'stop_counts':dict(counts),'native_LIRO_OSAL_imports':4,
      'kernel_lock_body_driver_registration_allocation_reply_or_Hal_executed':False,
      'native_proof_sha256':im.sha(npath.read_bytes()),'goal_complete':False,'persistent_write_release':False}
    review={'created_utc':now,'reviewer':'Same-agent original-byte/ELF/relocation/readback/trace/hash review; no independent implementation or physical replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'previous24files_and_canonical_verified':True,'all973_relocation_fields_range_and_target_backdecoded':True,
      'no_changes_outside_relocation_fields_and_no_RWX_pages':True,
      'original_LIRO_kernel_memcpy_copies_four_verified_OSAL_relocations':True,
      'same_original_request_reaches_real_original_module_then_kernel_service_boundary':True,
      'module_zero_BSS_not_actual_runtime_state_or_camera_fault':True,
      'independent_source_prefix_setter_and_driver_pointer_array_ABI_checked':True,
      'IRQ_DAIF_SP_EL0_current_task_and_callback_allocator_dependencies_explicit':True,
      'JSON_key_registration_pointer_array_and_callback_indirection_assertion_failures_preserved':True,
      'UU_Windows_or_camera_operations':False,'outcome':'PASS_OFFLINE_LINK_AND_NATIVE_PREFIX_WITH_REAL_LINUX_AND_PHYSICAL_GAPS'}
    canonical=f.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.prev.STAGE/'goal-status-after.json').read_bytes()
    old=json.loads(before);g=json.loads(before);g['updated_utc']=now;g['latest_stage']=s.name
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      'stage63封存24件/canonical复核后，原3模块973项ABS64/PREL32/CALL26按声明客体节布局完成地址/范围/回算与字节检查，54个去重提供者名均有原来源。',
      '原LIRO源向量4个真实OSAL重定位由原内核memcpy复制，原avcam消息分支实际进入原osal_valloc_msg_wait及内部查找/锁，到原kernel _raw_spin_lock_irqsave第一条指令前。',
      '目标A5/C3及UHD、两组独立来源setter和2原模块init入口，共33段；模块节执行后保持重定位初值。驱动注册X0是栈指针数组、W1为1，未执行注册正文。',
      '静态核对锁入口先读DAIF/改IRQ/读SP_EL0及任务计数；原驱动ops首回调再间接层调用k_uipc_init，涉及页分配/字符设备/proc/线程。未伪造IRQ/任务、分配、注册回调或同步回复。',
      'JSON数字键、直接驱动指针和直接回调槽三项检查假设失败保留，改按实际原数据/代码复核；原函数未改，不输出Sony模块/ELF/刷机包。',
      '完整16要求和授权保留，实际16M hook、Linux启动/同步、硬件主录/音画长录与同机恢复未完成，未操作UU/Windows/实机。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage64_osal_offline_link']={'readme':rel+'/README.md','proof':ev,
      'link_proof':str(lpath.relative_to(root)),'kernel_boundary':rel+'/kernel-boundary-audit.json',
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json','bounded_fragments':33,
      'scope':'Offline original module relocations plus original LIRO-bound request to unexecuted kernel IRQ-lock service; independent setters/init-to-register entries only. No actual Linux service/hardware/recovery.',
      'goal_complete':False,'authorization_unchanged':True}
    addition=' stage64原3模块973重定位/54提供者按客体布局核对，原LIRO复制4个OSAL绑定，原请求实际进入原模块到内核IRQ锁入口前；33段含独立setter及模块init到驱动注册入口，模块节保持初值。IRQ/当前任务/页分配/驱动回调/线程未运行，零BSS不代表实机状态；实际16M接合、硬件主录及同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/kernel-boundary-audit.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='核对原Linux启动上下文/DAIF-SP_EL0任务状态、模块驱动注册指针数组→ops首回调→k_uipc_init的真实参数和内存池/页分配/线程依赖，再决定可扩大哪些有界原执行。不得用零BSS/伪任务/假IRQ/分配或同步回复替代真实初始化；同时保留16M真实hook、owner代次/共享锁/完成通知及全部实机主录和同机恢复要求。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    index=root/'README.md';ib=index.read_bytes();text=ib.decode()
    entry='- [2026-10-26 FX3 原OSAL离线链接与内核边界](<work/sony-firmware-20261024/stage64-osal-offline-link/README.md>)：3模块973重定位和原LIRO绑定/33段通过，请求到未执行IRQ锁、init到未执行驱动注册；真实Linux/硬件主录与恢复仍未验收。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    ia=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    im.write_json(s/'summary.json',summary);im.write_json(s/'coordinator-observations.json',review)
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(s.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage64-osal-offline-link/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
      'previous_manifest_sha256':f.PRIOR_SHA,'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
      'operations':{'original_firmware_unchanged':True,'Sony_loadable_ELF_module_or_firmware_exported':False,
        'actual_kernel_IRQ_task_driver_allocator_sync_reply_Hal_recording_or_recovery':False,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((root/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
      'latest_stage':s.name,'module_relocations':973,'bounded_fragments':33,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
