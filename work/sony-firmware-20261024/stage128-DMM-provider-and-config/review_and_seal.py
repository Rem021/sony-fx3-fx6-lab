#!/usr/bin/env python3
"""Review pinned module/config and native leaves without promoting hardware gates."""
from pathlib import Path
import copy,datetime,difflib,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import provider_audit as t
BASE,ROOT=t.BASE,t.ROOT
PRIOR=BASE/'stage127-native-DMM-response-and-node-producer/final-receipt.json'
PRIOR_SHA='d1f81c654f5f8394bd7ebc25822fd65bbc8a524a1557edc34be81b4778712b52'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    t.prep.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(PRIOR)==PRIOR_SHA;prior=json.loads(PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-bytes-input-20261027';result=out/'provider-results.json';j=json.loads(result.read_text())
    assert j['status']=='PASS_DMM_STATIC_ROUTE_CONFIG_MISMATCH_AND_NATIVE_LEAF_SCOPE_NOT_RUNTIME_ALLOCATION'
    assert digest(STAGE/'provider_audit.py')==j['source_sha256']==digest(out/'executed-source.py')
    assert not any(j[k] for k in ('camera_Windows_host_services_or_module_loading','goal_complete','persistent_write_release'))
    failures=[]
    for name in ('run-original-leaves-20261027','run-corrected-reply-types-20261027'):
        p=STAGE/name;f=json.loads((p/'attempt-failure.json').read_text())
        assert f['status']=='FAILED_NO_PASSING_RESULT' and f['source_sha256']==digest(p/'executed-source.py')
        failures.append({'path':name,'error':f['error'],'source_sha256':f['source_sha256'],
            'formal_source_diff':list(difflib.unified_diff((p/'executed-source.py').read_text().splitlines(),
                (STAGE/'provider_audit.py').read_text().splitlines(),fromfile=name,tofile='formal',lineterm=''))})
    inputs=json.loads((STAGE/'input-receipt.json').read_text());assert len(inputs['files'])==2
    for f in inputs['files']:
        p=ROOT/f['output'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
        assert f['partition_official_size_crc_matched']
    assert digest(t.MOD)==t.MOD_SHA and digest(t.CFG)==t.CFG_SHA
    cfg=json.loads((STAGE/'DmmCfg-decoded.json').read_text());assert cfg==t.decode_cfg(t.CFG.read_bytes())
    binding=j['config_binding'];assert len(cfg['roots'])==1 and len(cfg['rules'])==164 and len(cfg['units'])==348
    assert cfg['total_consumed_bytes']==43320 and len(binding['target_MPR_unit_types'])==20
    assert not binding['matching_target_units'] and not binding['AP_runtime_or_MPR_config_binding_proven']
    assert max(len(u['extent_types']) for u in cfg['units'])==1 and len(binding['truncated_inputs_rejected'])==5
    assert len(j['length_cases'])==21 and len(j['open_cases'])==15
    ev=[e for k in ('length_cases','open_cases') for c in j[k] for e in c['events']]
    assert len(ev)==j['native_phases']==36
    for e in ev:
        assert e['SP_saved_registers_and_memory_outside_outputs_preserved']
        assert not e['kernel_OSAL_locks_allocator_or_device_executed']
        pcs=[int(p,16) for p in e['pcs']]
        assert pcs[-1]==t.STOP and all(t.TC+0x5e90<=p<t.TC+0x5ee8 or t.TC+0x91e8<=p<t.TC+0x9350 for p in pcs[:-1])
    for c in j['length_cases']:
        n=c['declared_count'];wanted=0x18+16*n if c['reply_type'] in (0x8020,0x802a) and 1<=n<=12 else 0x28
        assert c['native_bytes']==wanted and c['fallback_length_not_count_rejection_or_buffer_validity_proof']
    mutations=[]
    for c in j['open_cases']:
        old=bytes.fromhex(c['before_unit']);after=bytes.fromhex(c['after_unit']);at=2*0x70;wanted=bytearray(old)
        assert c['native_status_u32']==c['expected_status']&0xffffffff
        assert c['runtime_unit_extent_and_generation_inputs_are_declared'] and not c['real_allocation_mapping_owner_or_read_only_protocol_proven']
        if c['expected_status']==0:
            assert c['native_count_storage_u16']==c['n']
            if c['flags'] in (0,1):wanted[at+9]=c['opens']+1;struct.pack_into('<H',wanted,at+0xc,2)
            elif c['flags']==4:wanted[at+9]=1;struct.pack_into('<H',wanted,at+0xc,3)
            desc=bytes.fromhex(c['native_descriptor_storage'])
            for i in range(c['n']):assert struct.unpack_from('<QI',desc,i*16)==(0x70000000+i*0x01001000,0x200000+i*0x1000)
        elif c['expected_status'] in (-0x205,-0x105):assert c['native_count_storage_u16']==0xffff
        else:assert c['native_count_storage_u16']==0
        assert after==bytes(wanted)
        mutations.append({'case':c['label'],'changed_unit_offsets':[hex(i) for i,(a,b) in enumerate(zip(old,after)) if a!=b],
            'status':c['expected_status'],'count_storage':c['native_count_storage_u16']})
    audit=json.loads((STAGE/'source-and-scope-audit.json').read_text())
    assert len(audit['local_leaf_literal_links_only'])==2 and len(audit['module_command20_tables'])==2
    assert audit['module_static_queue_ID']=='0x61003c' and not audit['full_module_relocation_or_kernel_initialization_proven']
    image=t.Image();elf=image.elf;sy=image.sy;sec=elf.get_section_by_name('.init.text');raw=sec.data()
    rels={r['r_offset']:r for r in elf.get_section_by_name('.rela.init.text').iter_relocations()}
    loader=[]
    for i in image.md.disasm(raw,0):
        r=rels.get(i.address);ref=None
        if r:
            s=sy.get_symbol(r['r_info_sym']);ref={'name':s.name,'type':r['r_info_type'],
                'section':elf.get_section(s['st_shndx']).name if isinstance(s['st_shndx'],int) else s['st_shndx'],
                'target_offset':hex(s['st_value']+r['r_addend'])}
        loader.append({'section_offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,'relocation':ref})
    params=[]
    for r in elf.get_section_by_name('.rela__param').iter_relocations():
        s=sy.get_symbol(r['r_info_sym']);params.append({'offset':hex(r['r_offset']),'name':s.name,'type':r['r_info_type'],
            'section':elf.get_section(s['st_shndx']).name if isinstance(s['st_shndx'],int) else s['st_shndx'],
            'target_offset':hex(s['st_value']+r['r_addend'])})
    assert any(x['offset']=='0x20' and x['section']=='.bss' and x['target_offset']=='0x18' for x in params)
    assert b'parmtype=DmmConfig:charp\0' in elf.get_section_by_name('.modinfo').data()
    put(STAGE/'config-loader-static.json',{'module_sha256':t.MOD_SHA,'init_text_sha256':hashlib.sha256(raw).hexdigest(),
        'init_text_disassembly':loader,'parameter_relocations':params,
        'parameter':'DmmConfig:charp','parameter_pointer_field':'.bss+0x18','native_initial_config_read_request_bytes':0x25800,
        'actual_boot_parameter_value_runtime_file_or_loading_success_proven':False,
        'kernel_file_operations_or_initialization_executed':False})
    old=json.loads(before)
    for f in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/f['path'])==f['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for f in json.loads(p117.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(result.relative_to(ROOT))
    contract=json.loads((PRIOR.parent/'diagnostic-contract.json').read_text())
    contract['schema']='fx3-offline-status-diagnostic-candidate/10';contract['refined_in_stage']=STAGE.name
    contract['DMM_module_and_config_binding']={
        'module_sha256':t.MOD_SHA,'static_queue_ID':'0x61003c','static_command20_handler_text_offset':'0x5488',
        'module_native_reply_length_counts':[1,12],'module_reply_length_fallback_for_outside_counts':0x28,
        'fallback_does_not_prove_count_rejection':True,'no_module_8_chunk_guard_established':True,
        'stage127_MPR_layout_conservative_max8_retained':True,
        'ordinary_unit_Open_mutates_open_count_and_state':True,
        'error_status_must_be_checked_before_count_some_errors_leave_old_count':True,
        'DmmConfig_module_param_field':'.bss+0x18','actual_parameter_value_or_AP_config_unproven':True,
        'extracted_config_version':cfg['version_ascii'],'config_units':348,'target_MPR_unit_types':20,'matching_target_units':0,
        'config_one_extent_per_unit_not_evidence_for_target_recording_chain':True,
        'kernel_module_loading_messages_allocation_mapping_and_MAIN_hardware_unproven':True}
    contract['next_runtime_acceptance_requirements'].append('bind actual DmmConfig boot parameter/loading source to all target MPR unit types; module length fallback and unrelated ipsxcp config cannot establish MPR max8, resource ownership or allocation safety; ordinary Open is stateful')
    put(STAGE/'diagnostic-contract.json',contract)
    review={'status':j['status'],'created_utc':now,'native_phases':36,'native_length_cases':21,'native_open_cases':15,
        'config_units':348,'target_unit_matches':0,'two_failed_harness_attempts_preserved':True,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_or_host_services':False,
        'goal_complete':False,'persistent_write_release':False,'previous_manifest_members_verified':len(prior['files']),
        'native_unit_mutations':mutations,'harness_corrections':failures}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_pinned_DMM_module_static_route_native_leaf_reply_length_Open_side_effects_and_config_mismatch'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段127封存12件/canonical核验；从官方分区只读提取dmm.ko与DmmCfg.bin并重验SHA/CRC。',
            '原模块静态0x61003c队列、命令20表到5488与Alloc/Open对应；真实注册/传输/分配不充已执行。',
            '36原叶函数例证实回复长度可算1至12块、越界回退40非拒绝；普通Open改打开计数/状态，部分错误留旧数量。',
            '配置有界解析完整43320字节、348单位均单extent，但目标20单位号零匹配，实际DmmConfig参数值未取得，不套用此上限。',
            '16项要求、权限、原固件及旧前后端保持；硬件主录、备份/恢复/独立救援仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage128_DMM_module_config']={'readme':rel+'/README.md','result':rr,
        'inputs':rel+'/input-receipt.json','source_audit':rel+'/source-and-scope-audit.json','config_loader':rel+'/config-loader-static.json',
        'contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'Static queue/command mapping,36 native leaf cases and decoded ipsxcp config with zero target unit matches. Actual config/runtime allocation/hardware/recovery unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json',rel+'/config-loader-static.json'])
            req['stage128_scope']='同包DMM模块静态分发表/36原叶例/配置零目标匹配；实际配置/初始化/消息/分配与硬件未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':PRIOR.parent.name,
        'finding':'DMM module length selector supports1..12 and fallback40 is not rejection; ordinary Open mutates counters. Extracted ipsxcp config has348 single-extent units but none of20 target MPR units, so cannot establish their live count or safety. Actual DmmConfig path must be bound.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段128后定位官方启动链的DmmConfig参数/实际AP配置加载源，绑定20个目标MPR单位号和其extent规则、块数/大小及失败回收；保持MPR保守max8而不套用ipsxcp配置或长度回退。仅Mac。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in old['requirements']]==[(x['id'],x['status']) for x in g['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();txt=ib.decode();marker='## 相机与固件研究\n';assert txt.count(marker)==1
    entry='- [2026-10-27 FX3 DMM模块与配置适用范围](<'+rel+'/README.md>)：同包模块/配置重验，36原叶例确认长度回退非8块守卫、Open改计数；ipsxcp配置348单位与目标20单位零匹配，实际配置/分配/主录恢复未验。'
    assert entry not in txt;updated=txt.replace(marker,marker+'\n'+entry+'\n',1)
    t.prep.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage128-DMM-module-and-config/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':PRIOR_SHA,
        'operations':{k:v for k,v in review.items() if k not in ('native_unit_mutations','harness_corrections')},
        'mutable_progress':{'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':digest(canonical)},
        'readme_index_before_sha256':hashlib.sha256(ib).hexdigest(),'readme_index_after_sha256':digest(index),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'native_phases':36,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
