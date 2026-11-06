#!/usr/bin/env python3
"""Seal conditional message/node lifetime evidence; keep live gates intact."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import release_order as t
BASE,ROOT=t.BASE,t.ROOT
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    assert digest(t.MODULE)==t.MODULE_SHA
    f47=next(f for f in json.loads((BASE/'stage47-runtime-provider-binding/final-receipt.json').read_text())['files'] if f['path']==str(t.MODULE.relative_to(ROOT)))
    assert f47['sha256']==t.MODULE_SHA and f47['bytes']==t.MODULE.stat().st_size
    run=STAGE/'run-original-refcount-and-cleanup-20261027';p=run/'release-order-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_ORIGINAL_MESSAGE_RELEASE_AND_DISTINCT_PENDING_CALLBACK_NODE_SCOPE'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'release_order.py').read_bytes()
    assert j['source_sha256']==digest(STAGE/'release_order.py') and j['module_sha256']==t.MODULE_SHA
    assert not any(j[k] for k in ['goal_complete','persistent_write_release','Windows_UU_camera_operations','real_kernel_service_message_lifetime_MAIN_or_recovery_proven'])
    groups=('free_cases','tail_controls','missing_client_cases','finish_cases','user_cleanup_cases','pending_cleanup_cases')
    assert tuple(len(j[k]) for k in groups)==(12,2,2,8,2,2)
    events=[e for k in groups for c in j[k] for e in c['events']];assert len(events)==j['bounded_phases']==110
    for c in j['free_cases']+j['tail_controls']:
        refs=c['declared_refs'];assert c['header_ref_after']==refs-1 and c['client_count_after']==(1 if refs>1 else 0)
        assert not c['actual_pool_free_or_reuse_executed'] and not c['free_slice_checks_trailer']
        # Independently check overlapping accesses, not only exact read offsets.
        assert not any(x['offset']<112 and x['offset']+x['size']>108 for x in c['events'][-1]['declared_block_reads'])
        if refs>1:
            assert c['outcome']=='reference_retained_no_pool_call' and c['events'][-1]['return_u32_if_returned']==0
            assert c['events'][-1]['native_saved_registers_verified_on_return'] and c['native_pool_free_args'] is None
        else:
            private=not c['declared_client_flags']&8 and int(c['declared_private_pool'],16)!=0
            assert c['native_pool_free_args']==[int(c['declared_private_pool'],16) if private else t.BBASE+0x3740,t.BLOCK,128]
    assert all(c['declared_tail']=='0x12345678' and c['outcome']=='last_reference_to_pool_free_boundary' for c in j['tail_controls'])
    for c in j['missing_client_cases']:
        assert c['events'][-1]['return_u32_if_returned']==0xfffffc00 and not c['events'][-1]['declared_block_reads']
        assert not c['actual_lookup_executed']
    for c in j['finish_cases']:
        assert c['node_pending_count_after']==0 and not c['actual_lock_queue_service_pool_free_or_callback_runtime_proven']
        delta=1 if c['kind'] in ('broadcast_ref1','broadcast_ref2') else 0
        assert c['header_ref_after']==c['declared_refs']-delta
        if c['kind'] in ('nonbroadcast','broadcast_no_chain'):assert not c['events'][-1]['declared_block_reads']
    for c in j['user_cleanup_cases']:
        assert c['original_QID']==hex(t.old.SOURCE) and c['original_free_operation_low32']=='0x8000000b'
        assert c['message_pointer']==hex(t.DATA) and not c['actual_ioctl_or_previous_callback_completion_proven']
        calls=c['events'][0]['native_returns_and_original_symbol_bindings']
        assert sum(x.get('original_MPR_PLT_binding')=='osal_free_msg' for x in calls)==1
        assert sum(x.get('symbol')=='u_osal_free_msg' for x in calls)==1
    for c in j['pending_cleanup_cases']:
        assert c['next_user_operation_low32']=='0x8000000d' and c['pending_slot_cleared_before_finish_call']
        assert c['original_finish_args']==[hex(t.NODE),hex(t.HEADER)] and c['node_record_lifetime_is_not_message_data_lease']
        assert not c['actual_receive_unlock_finish_continuity_proven']
    forbidden={t.KBASE+a for a in [0x2938,0x32d8,0x3420,0x3508,0x3498,0x4720,0x4768,0x478c,
        0x5400,0x54e0,0x54c4,0x5558,0x5568,0x29d8,0x2ee8,0x35b8,0x382c,0x37a8,0x38e4,0x38f0,0x984,0x998,0xa78]}|{0x2530,0x2800,0x32f0}
    executed=set()
    for e in events:
        assert all(e[k] for k in ['whole_images_unchanged','scratch_outside_outputs_unchanged','stack_outside2048_unchanged'])
        assert not e['actual_services_or_success_return_adapters']
        assert not forbidden.intersection(int(p,16) for p in e['pcs'][:-1])
        executed.update(int(p,16) for p in e['pcs'][:-1])
    changed={i for i,(a,b) in enumerate(zip(t.old.TEXT,t.TEXT)) if a!=b}
    assert not any(any(pc-t.KBASE+i in changed for i in range(4)) for pc in executed if t.KBASE<=pc<t.KBASE+len(t.TEXT))
    assert j['added_original_local_ABS64']==t.ADDED_RELOCS
    name='_ZN3mpr5Codec17CallbackFromAvbbcEPvS1_';s=t.old.MPR.symbols[name];assert s=={'va':0x28593c,'size':400}
    mi=list(t.old.DF.md.disasm(t.old.MPR.read(s['va'],s['size']),s['va']))
    assert [x.address for x in mi if x.mnemonic=='ret']==[0x285a08]
    assert next(x for x in mi if x.address==0x2859f8).op_str=='#0x83370'
    assert t.old.MPR.plt[0x83370]=='osal_free_msg' and t.old.OSAL.plt[0x2470]=='u_osal_free_msg'
    symbol_table=t.ELF.get_section_by_name('.symtab');finish_reloc=[]
    for sec in t.ELF.iter_sections():
        if sec['sh_type']=='SHT_RELA' and t.ELF.get_section(sec['sh_info']).name=='.text':
            for rr in sec.iter_relocations():
                if rr['r_offset']==0xa78:
                    sym=symbol_table.get_symbol(rr['r_info_sym']);assert rr['r_info_type']==283 and sym.name=='finish_callback' and sym['st_value']==0x53c8
                    finish_reloc.append({'offset':'0xa78','type':'R_AARCH64_CALL26','original_symbol':sym.name,'symbol_offset':'0x53c8'})
    assert len(finish_reloc)==1
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    listings=[]
    for a,z in [(0x4650,0x47a0),(0x53c8,0x5574),(0x968,0xa7c),(0x36e8,0x38f8)]:
        listings.append({'module_text_range':[hex(a),hex(z)],'original_bytes_sha256':sha(t.old.TEXT[a:z]),
            'original_disassembly':[{'offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in t.old.DF.md.disasm(t.old.TEXT[a:z],a)]})
    listings.extend([{'library':t.old.MPR.path.name,'range':['0x28593c','0x285acc'],'original_disassembly':t.old.MPR.disasm(0x28593c,0x285acc)},
        {'library':t.old.OSAL.path.name,'range':['0x32e8','0x3318'],'original_disassembly':t.old.OSAL.dump(0x32e8,0x3318)},
        {'library':t.old.OSAL.path.name,'range':['0x3f28','0x3fb0'],'original_disassembly':t.old.OSAL.dump(0x3f28,0x3fb0)}])
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27','sources':[
        {'url':'https://github.com/QAQLeonard/a7c2-fl23-research/issues/31','kind':'primary first-person reports in model-specific project',
         'event_dates':['2026-10-23','2026-10-25','2026-10-26','2026-10-27'],
         'fresh_observation':'Oct27 original reporter says starting in the still-working Movie path restored Still startup while modifications remained. Earlier replies report recovery through Movie mode.',
         'evidence_limit':'Self-reports, model/application-specific. Not proof of Sony service outcome, all bricks, flash corruption or an independent FX3 rescue.',
         'project_inference':'Do not make healthy Movie startup the independent recovery premise when modifying FX3 MAIN recording.'},
        {'url':'https://github.com/DavidBuchanan314/ILCE-7M4-RE','kind':'primary maintainer documentation',
         'observation':'A7IV bare-metal fastboot payload is described for eMMC backup/restore; transparent crypto explicitly excludes boot0 support.',
         'evidence_limit':'A7IV-specific, no tested FX3 transfer or full encrypted-boot recovery guarantee.'},
        {'url':'https://github.com/morluto/rea/discussions/3027','kind':'primary request, current direct fetch failed',
         'observation':'Search index shows Oct13 FX3 7.02 battery/homebrew request with zero indexed comments.',
         'evidence_limit':'Index crawled last week; direct refresh failed. Not relied on as a current or exhaustive support list.'}]})
    put(STAGE/'diagnostic-lifetime-refinement.json',{'schema':'fx3-guest-only-diagnostic-lifetime/1','status':'SPEC_ONLY_UNDEPLOYABLE',
        'refines_stages':[111,112,113],'original_normal_callback_exit_requests_message_free':True,
        'free_request_is_not_actual_success':True,'original_message_pointer_must_not_escape_as_readable_lease':True,
        'proposed_snapshot_rule':'Only copy needed bytes while a verified live message lease and readable extent exist, before the native free request; consumers get owned copies, not raw pointers.',
        'reply_wire_bytes':44,'conditional_copy_storage_bytes':48,
        'four_extra_bytes_are_allocator_tail_under_stage112_conditions_not_wire_payload':True,
        'raw98_parameter_body_ownership_is_a_separate_unproved_requirement':True,
        'pending_callback_registration_node_is_not_message_storage':True,
        'generic_free_return0_does_not_prove_last_reference_or_completed_pool_return':True,
        'marker77777777_not_checked_in_executed_free_slice':True,
        'runtime_proofs_still_needed':['actual client flags and callback ownership','real mapped readable extent',
            'real reference/queue synchronization and owned snapshot allocation','actual free and independent backup/restore readback',
            'real MAIN profile, hardware encoded file and long-run acceptance'],
        'guest_prototype_changed':False,'camera_or_persistent_use_permitted':False,'goal_complete':False})
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'module':str(t.MODULE.relative_to(ROOT)),'module_sha256':t.MODULE_SHA,
        'stage47_original_member_verified':True,'retained_stage113_local_data_relocations':t.prev.RELOCS,
        'added_original_local_data_relocations':t.ADDED_RELOCS,'original_executed_instruction_bytes_unchanged':True,
        'MPR_callback_symbol':name,'MPR_callback_bytes':400,'only_native_RET':'0x285a08','common_free_request':'0x2859ec..0x2859f8',
        'independent_common_cleanup_to_original_OSAL_free_ioctl_stop':True,'actual_previous_callback_completed':False,
        'next_pending_finish_original_relocation':finish_reloc,
        'message_header_ref_offset':10,'client_block_counter_offset':2,
        'original_allocation_geometry_reexecuted_before_message_free_controls':True,
        'independent_inputs':['client result after stopped dynamic lookup','pool block after stopped allocator',
            'reference2 control after original header generation','declared post-lock finish frame','independent MPR cleanup frame',
            'independent post-callback worker frame','independent pending-node fields and post-unlock frame'],
        'tail_control_is_guest_only_no_actual_corrupt_message_or_free':True,
        'single_guest_atomic_updates_are_not_real_concurrency_proof':True,
        'nonbroadcast_empty_queue_finish_does_not_read_declared_message_header':True,
        'broadcast_control_ownership_depends_on_flags_and_callback_chain':True,
        'actual_pool_free_reuse_ioctl_lookup_lock_scheduler_or_device_executed':False,
        'original_listings':listings,'goal_complete':False,'persistent_write_release':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'case_counts':{k:len(j[k]) for k in groups},'bounded_phases':110,'added_local_ABS64_data_relocations':2,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'actual_kernel_services_or_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_message_free_reference_updates_and_distinct_callback_node_retirement_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11314件封存/canonical及目标卷核对；复用阶段47官方模块，无设备操作。',
            '原MPR公共返回出口请求释放消息，原用户OSAL生成8000000b；下一轮接收8000000d清理的登记记录与消息数据不是同一寿命。',
            '原分配头接独立free引用更新：2→1可返回0不归还，1→0到128B池归还前；不同尾值在该片段无检查。',
            '非broadcast空后续队列finish不读消息头；broadcast受flags/链结构影响，共110阶段。原lookup/锁/池/ioctl均停前，未模拟成功。',
            'A7CII故障帖Oct27反馈仍依赖健康Movie启动，A7IV维护者fastboot文档仍有boot0例外；不构成修改FX3 MAIN的独立救援。',
            '下一步转回自然MAIN生产者及FH/16M资源；实际成片/音画/长录和同机恢复仍缺，16项状态/权限/原型保持。'],'completion_not_claimed':True}
    g['latest_stage_evidence']['stage114_callback_message_release']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','lifetime_refinement':rel+'/diagnostic-lifetime-refinement.json',
        'public_sources':rel+'/public-source-notes.json','review':rel+'/completed-evidence-review.json',
        'scope':'Original common free request, conditional reference updates and distinct later callback-node finish;110 bounded phases, no real pool/ioctl/lease/hardware/recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-lifetime-refinement.json'])
            req['stage114_scope']='原MPR释放请求/原引用更新/待结束登记记录与消息不同寿命110阶段；只导出释放前有权读取的副本，实际lease/映射/池归还及硬件未证。状态保持。'
        if req['id']=='G16':
            req['evidence'].append(rel+'/public-source-notes.json')
            req['stage114_scope']='公开A7CII Oct27用户恢复反馈依赖健康Movie；A7IV fastboot仍有boot0例外。非FX3独立救援保证，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original MPR return exit requests message free before the worker next receive. Later pending callback-node finish is a separate lifetime, with nonbroadcast/broadcast distinctions. Native references can return0 while retaining storage; tail marker is not checked by the executed free slice. Real transport, locks, pool return and FX3 rescue remain unproved.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段114已把消息数据与回调登记记录寿命分开；下一轮优先回自然MAIN生产者与FH/16M资源映射，利用释放前独立快照约束筛选最小诊断点。不要仅沿传输微片段继续扩大局部通过。真实lease/同步、同机健康备份、可回读恢复和独立FX3救援未证，Windows延后；不自动实机/刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 消息释放与回调登记寿命](<'+rel+'/README.md>)：原MPR释放请求/引用更新及不同finish分支110阶段；登记记录不是消息lease，真实MAIN实录/同机恢复仍未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage114-callback-release-order/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':110,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
