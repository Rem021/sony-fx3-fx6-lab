#!/usr/bin/env python3
"""Review existing native request/module provenance, seal without replay."""
import ast
import collections
import datetime
import io
import json
import struct
from elftools.elf.elffile import ELFFile
import resource_message as f
import osal_dependency_audit as audit


def main():
    im=f.im;im.volume();s=f.STAGE;root=f.ROOT
    assert not (s/'final-receipt.json').exists()
    prior=f.last.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==f.PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((root/x['path']).read_bytes())==x['sha256']
    run=s/'run-native-message-constructor-20261026';path=run/'resource-message-results.json'
    p=json.loads(path.read_text());receipt=json.loads((run/'source-receipt.json').read_text())
    assert im.sha((s/'resource_message.py').read_bytes())==receipt['script_sha256']==im.sha((run/'executed-source.py').read_bytes())
    for node in ast.walk(ast.parse((s/'resource_message.py').read_text())):
        if isinstance(node,ast.FunctionDef) and node.name in ('code','store'):
            assert not any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute)
              and x.func.attr in ('reg_write','mem_write') for x in ast.walk(node))
    blob=(f.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==receipt['avcam_sha256']==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for file,key in ((f.n.STAGE/'official-files/nflasha15/kmod/liro.ko','LIRO_sha256'),
      (f.n.STAGE/'official-files/nflasha3/vmlinux.bin','kernel_sha256'),
      (f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o','wrapper_object_sha256')):
        assert im.sha(file.read_bytes())==receipt[key]
    assert p['status']=='PASS_NATIVE_RESOURCE_MESSAGE_TO_UNBOUND_OSAL_ALLOCATION'
    cases=p['cases'];assert len(cases)==3
    assert [(c['seed'],c['native_row']) for c in cases]==[(0xa5,386),(0xc3,386),(0xc3,431)]
    events=[e for c in cases for e in c['events']];counts=collections.Counter(e['reason'] for e in events)
    assert len(events)==p['bounded_fragments']==21
    assert counts=={'boundary: after_original_kernel_memcpy_before_next_diagnostic':3,'returned':12,
      'boundary: before_original_buffer_channel_preparation':3,
      'boundary: before_unbound_osal_valloc_msg_wait_indirect_branch':3}
    global0=None;payload0=None
    for c in cases:
        for e in c['events'][2:5]:assert e['full_guest_arena_outside_constructed_object_unchanged']
        assert c['source_and_common_descriptor_unchanged']
        assert c['channel_entry']['body_executed'] and c['channel_entry']['x0_x4'][0]==hex(f.last.MANAGER)
        assert c['resource_provider_entry']['body_executed']
        ctor=c['original_resource_metadata_constructor']
        assert ctor['object']==hex(f.G) and ctor['LR']==hex(f.V+0x27bdfc) and ctor['initial_global_object_zero']
        globalraw=bytes.fromhex(c['global_metadata_object_hex']);assert len(globalraw)==f.GSIZE
        assert struct.unpack_from('<I',globalraw,0x2000)[0]==c['global_record_count']==202
        assert globalraw[0x2008:0x2010]==struct.pack('<Q',1)
        if global0 is None:global0=globalraw
        assert globalraw==global0
        stores=c['original_global_stores'];assert len(stores)==1416
        for z in stores:
            pc,at,size=int(z['pc'],16),int(z['address'],16),z['size']
            assert f.G<=at and at+size<=f.G+f.GSIZE
            assert f.V+0x27bca0<=pc<f.V+0x27bd8c or (pc==f.V+0x27be00 and at==f.FLAG and size==8)
        assert sum(x['pc']==hex(f.V+0x27be00) for x in stores)==1
        msg=c['native_message'];payload=bytes.fromhex(msg['inline_payload216_hex'])
        expected=bytearray(216);struct.pack_into('<HHI',expected,0,0x20,0,0x470)
        struct.pack_into('<HH',expected,0x14,0x1111,0x11)
        assert payload==bytes(expected) and msg['payload_created_by_native_code']
        assert msg['state_u32']==2 and msg['size_u16']==216 and msg['source_u32']=='0x806800f3'
        if payload0 is None:payload0=payload
        assert payload==payload0
        alloc=c['unbound_allocation']
        assert alloc['branch_X4']=='0x0' and alloc['x0_x3']==['0x61003c','0x10007548','0xd8','0x1']
        assert alloc['LR']==hex(f.V+0x9911c) and not alloc['indirect_branch_executed']
        assert not alloc['buffer_or_OSAL_return_adapter']
        e=c['events'][-1];assert not e['independent_entry_fixture'] and e['stop_pc']==hex(f.V+0x2f038)
        assert c['events'][-2]['stop_pc']==e['start_pc']==hex(f.V+0x21dd54)
        seq=[0x27bdb4,0x27bca0,0x27be00,0x27bec8,0x960a4,0x96240,0x964ac,0x99004,0x992b4,0x99118,0x2f028,0x2f038]
        positions=[e['pcs'].index(hex(f.V+x)) for x in seq];assert positions==sorted(positions)
        assert not c['OSAL_buffer_allocation_sync_send_reply_real_thread_or_Hal_executed']
    for region in p['original_regions']:
        for ins in region['instructions']:
            at=int(ins['va'],16)-f.V;assert blob[at:at+4].hex()==ins['bytes']
    failure=json.loads((s/'run-20261026/last-phase-at-failure.json').read_text())
    assert failure['stop_pc']==hex(f.V+0x960a4) and failure['reason']=='boundary: before_message_object_constructor_and_transport'
    assert (s/'run-20261026/attempt-source.py').is_file()
    deps=json.loads((s/'osal-dependency-audit.json').read_text())
    assert deps['undefined_symbol_count']==47 and deps['relocation_counts_all_sections']=={'257':326,'283':430,'261':56}
    assert deps['resolution_counts']=={'unique_kernel_candidate':44,'module_definition_requires_export_and_relocation_check':2,'missing_in_current_assets':1}
    modraw=(root/deps['module_path']).read_bytes();assert im.sha(modraw)==deps['module_sha256']
    elf=ELFFile(io.BytesIO(modraw));syms=elf.get_section_by_name('.symtab');exports=audit.exports(elf,syms)
    assert deps['four_public_message_symbols_paired_export_records']=={name:exports[name] for name in deps['four_public_message_symbols_paired_export_records']}
    kernel=(f.n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    for row in deps['static_provider_resolution']:
        if row['resolution_status']!='unique_kernel_candidate':continue
        candidate=row['static_kernel_export_candidates'][0]
        for neighbor in candidate['valid_sorted_name_neighbors']:
            off=int(neighbor['entry_offset'],16);value,ptr=struct.unpack_from('<QQ',kernel,off)
            assert value==int(neighbor['value'],16) and audit.string(kernel,ptr-f.n.K)==neighbor['name']
    ex=json.loads((s/'devno-extraction.json').read_text())
    assert ex['entry']['path']=='/kmod/devno.ko' and ex['entry']['type']==0x8000
    assert ex['partition_sha256']=='ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7'
    assert im.sha((root/ex['partition']).read_bytes())==ex['partition_sha256']
    assert im.sha((root/ex['reader']).read_bytes())==ex['reader_sha256']
    assert im.sha((root/ex['output']).read_bytes())==ex['sha256']=='cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23'
    add=json.loads((s/'additional-provider-audit.json').read_text())
    assert add['total_original_import_names']==47 and add['kernel_unique_neighbor_validated_candidates']==44
    assert add['candidate_export_values_outside_kernel_file']==['kmalloc_caches','system_freezing_cnt']
    assert {x['symbol'] for x in add['additional_actual_module_export_records']}=={'osal_create_waitable_thread','osal_wait_thread_exit','udif_devnodes'}
    for row in add['additional_actual_module_export_records']:
        raw=(root/row['provider']).read_bytes();assert im.sha(raw)==row['sha256']
        e=ELFFile(io.BytesIO(raw));assert audit.exports(e,e.get_section_by_name('.symtab'))[row['symbol']]==row['export_record']
    assert not add['relocation_runtime_mapping_kernel_state_module_init_callbacks_threads_or_hardware_executed']
    for faildir in ('audit-attempt-symbol-labels','extract-attempt-nflasha15'):
        assert not json.loads((s/faildir/'attempt-failure.json').read_text())['passing_result']
        assert (s/faildir/'attempt-source.py').is_file()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(root));ev=str(path.relative_to(root))
    summary={'created_utc':now,'status':p['status'],'bounded_fragments':21,'stop_counts':dict(counts),
      'native_global_resource_metadata_records':202,'per_case_original_global_stores':1416,
      'native_resource_message_bytes':216,'unbound_allocation_branch_executed':False,
      'OSAL_original_import_names_with_static_sources':47,'kernel_candidates':44,'module_export_records':3,
      'module_link_or_init_actual_OS_state_or_hardware':False,'proof_sha256':im.sha(path.read_bytes()),
      'goal_complete':False,'persistent_write_release':False}
    review={'created_utc':now,'reviewer':'Same-agent original-byte/source/trace/export/partition/hash review; no independent or physical replay.',
      'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
      'original_global_object_ctor_not_host_seed_or_success_flag':True,
      'native_payload216_and_source_metadata_match_across_target_old_values_and_UHD':True,
      'first_unbound_OSAL_branch_stopped_before_execution_no_return_or_buffer_adapter':True,
      'actual_export_records_not_named_local_symbol_assumptions':True,
      'kernel_candidate_neighbors_checked_but_not_runtime_proof':True,
      'two_kernel_data_candidates_beyond_file_explicit':True,
      'devno_from_correct_same_package_nflasha7_no_mount_or_execution':True,
      'initial_native_stop_and_audit_extraction_assumption_failures_preserved':True,
      'UU_Windows_or_camera_operations':False,'outcome':'PASS_NATIVE_MESSAGE_PREFIX_WITH_REAL_OSAL_AND_HARDWARE_GAPS'}
    canonical=f.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(f.last.STAGE/'goal-status-after.json').read_bytes()
    old=json.loads(before);g=json.loads(before);g['updated_utc']=now;g['latest_stage']=s.name
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
      'stage62封存15件及canonical复核，继续原资源提供者/消息依赖。',
      '同原请求执行27bdb4及原27bca0资源元数据构造202条，原代码生成216字节内联请求，目标A5/C3及UHD共21段通过；不是202个实际硬件缓冲区。',
      '全局数据写精确限制0x2010字节及原写PC，原文件不改；到原2f038间接分支前目标为0，未申请缓冲区、未发同步消息或伪造回复。',
      'osal_uipc47外部符号/812重定位静态审计；44个内核候选加osal_utm的2个及从原nflasha7只读补提devno的1个实际导出，47符号均有静态来源。两项内核数据候选在文件外，未补初始化。',
      '旧消息边界、具名导出符号假设和误查nflasha15失败源码/说明保留；未重定位或执行OSAL模块、真实线程、当前任务或硬件。',
      '完整16要求/相机授权/主录与同机恢复仍保留；未操作UU或Windows。'],
      'completion_not_claimed':True}
    g['latest_stage_evidence']['stage63_resource_message_boundary']={'readme':rel+'/README.md','proof':ev,
      'summary':rel+'/summary.json','review':rel+'/coordinator-observations.json',
      'dependency_audit':rel+'/osal-dependency-audit.json','provider_closure':rel+'/additional-provider-audit.json',
      'extraction':rel+'/devno-extraction.json','bounded_fragments':21,
      'scope':'Original resource metadata and216byte message to first unbound OSAL allocation branch. Static47 import provenance, no module linking/init or real message buffers/replies/OS/Hal.',
      'goal_complete':False,'authorization_unchanged':True}
    addition=' stage63同原请求生成资源元数据202条及216字节资源消息，目标A5/C3和UHD21段通过，停原OSAL分支2f038前，未申请/发送/回复。原osal_uipc47导入已有44内核候选+3模块实际导出来源，devno从同包nflasha7只读补提；未重定位/初始化模块，2内核数据候选在文件外。实际OSAL/线程/锁/owner代次/16M真实hook/硬件成片及同机恢复仍缺。'
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([ev,rel+'/additional-provider-audit.json']);req['remaining']+=addition
    g['next_safe_offline_actions'][0]='用原osal_uipc47静态提供者来源核对AArch64节布局及812项ABS64/PREL32/CALL26重定位、osal_utm/devno依赖导出及初始化边界；区分内核文件外BSS数据、真实锁/线程/当前任务/内存池和消息回复，不伪造分配或成功。继续实际16M writer调用接合、全局寿命/完成通知、日志/MMU同步与全部硬件及同机恢复要求。'
    for key in ('objective','authorization','completion_rule','external_dependencies','next_authorized_cached_metadata_action'):
        assert g[key]==old[key],key
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    index=root/'README.md';ib=index.read_bytes();text=ib.decode()
    entry='- [2026-10-26 FX3 原资源消息与OSAL依赖](<work/sony-firmware-20261024/stage63-resource-message-boundary/README.md>)：原216字节消息到未绑定申请分支21段通过；47导入静态来源补齐，OSAL加载/初始化、缓冲区/回复、硬件主录与恢复仍未验收。'
    assert entry not in text and text.count('## 相机与固件研究\n')==1
    ia=text.replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    im.write_json(s/'summary.json',summary);im.write_json(s/'coordinator-observations.json',review)
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())}
      for x in sorted(s.rglob('*')) if x.is_file()]
    final={'schema':'fx3-stage63-resource-message-boundary/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
      'previous_manifest_sha256':f.PRIOR_SHA,
      'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
      'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
      'operations':{'original_firmware_unchanged':True,'Sony_loadable_payload_exported':False,
        'actual_OSAL_module_load_threads_allocation_sync_reply_Hal_recording_or_recovery':False,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((root/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
      'latest_stage':s.name,'bounded_fragments':21,'requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':main()
