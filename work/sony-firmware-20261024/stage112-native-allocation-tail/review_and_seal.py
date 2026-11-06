#!/usr/bin/env python3
"""Seal conditional allocation/trailer evidence; do not waive runtime gates."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE));import allocation_tail as t
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
    assert digest(t.MODULE)==t.MODULE_SHA
    m47=BASE/'stage47-runtime-provider-binding/final-receipt.json';old47=json.loads(m47.read_text())
    member=next(f for f in old47['files'] if f['path']==str(t.MODULE.relative_to(ROOT)))
    assert member['sha256']==t.MODULE_SHA and member['bytes']==t.MODULE.stat().st_size
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-native-client-branches-20261027';j=json.loads((run/'allocation-tail-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'allocation_tail.py').read_bytes()
    assert digest(ROOT/j['source'])==j['source_sha256'] and j['kernel_module_sha256']==t.MODULE_SHA
    assert (len(j['geometry_cases']),len(j['rejected_client_controls']),len(j['user_ioctl_argument_cases']),len(j['callback_registration_cases']),j['bounded_phases'])==(16,2,4,2,70)
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    assert not j['actual_kernel_registry_pool_user_mapping_ioctl_callback_thread_or_hardware_proven']
    flows=[]
    for c in j['geometry_cases']:
        length=c['requested_length'];a=(length+3)&~3;extra=40 if int(c['declared_qid'],16)&0x80000000 else 0
        b=(a+24+4+extra+63)&~63
        assert c['native_aligned_length']==a and c['native_block_size_request']==b==128
        assert c['native_data_offset_from_pool_block']==24+extra
        assert c['native_length_metadata']==length and c['native_trailer_offset_from_payload']==a
        assert c['native_trailer_hex']=='77777777' and c['native_counter_after']==1
        assert c['bytes_from_payload_to_block_end']>=a+4
        assert c['events'][-1]['reason']=='returned' and c['events'][-1]['native_saved_registers_restored_on_return_after_independent_inputs']
        assert not c['actual_kernel_client_registry_pool_allocation_or_user_mapping_proven']
        if 'independent_flow' in c:
            f=c['independent_flow'];flows.append(f)
            assert c['requested_length']==44 and c['declared_qid']==hex(t.SOURCE)
            assert bytes.fromhex(f['native_reply48_hex'])==bytes.fromhex(f['wire44_hex'])+bytes.fromhex('77777777')
            assert f['native_user_dispatch_pointer_equals_payload_pointer'] and f['native_copy_in_declared_block_extent']
            assert not f['actual_ioctl_callback_thread_mutex_or_mapping_continuity_proven'] and len(f['events'])==5
    assert len(flows)==2
    for c in j['rejected_client_controls']:
        assert c['rejection_log_route_before_pool_and_header_body'] and not c['actual_camera_configuration_or_error_return_proven']
        assert c['events'][-1]['reason']=='boundary: before_unexecuted_kernel_configuration_error_log'
    for c in j['user_ioctl_argument_cases']:
        assert c['native_qid']==hex(t.SOURCE) and not c['actual_ioctl_or_device_handle_opened']
        if c['kind']=='allocate':assert c['native_ioctl_operation_low32']=='0x8000000a' and c['native_parameter_values']==[t.OUT,44,1]
        else:assert c['native_ioctl_operation_low32']=='0x80000008' and c['native_parameter_values']==[t.MBASE+0x28593c,0]
    for c in j['callback_registration_cases']:
        assert c['original_registration_arguments']==[hex(t.SOURCE),hex(t.SP-0x70+0x40),'0x28593c','0x0']
        assert not c['actual_Init_lock_thread_create_registration_or_current_callback_proven']
    cases=j['geometry_cases']+j['rejected_client_controls']+j['user_ioctl_argument_cases'];events=[e for c in cases for e in c['events']]
    events.extend(e for f in flows for e in f['events']);assert len(events)==66
    forbidden={t.KBASE+0x2938,t.KBASE+0x32d8,t.KBASE+0x3420,t.KBASE+0x3508,t.KBASE+0x3498,
        0x2530,0x2800,0x32f0,t.DBASE+0x30780,t.MBASE+0x80460}
    executed_kernel=set()
    for e in events:
        assert e['whole_stack_outside_declared2048_bytes_unchanged'] and e['whole_scratch_outside_outputs_unchanged']
        assert e['whole_mapped_images_and_unrelocated_kernel_text_unchanged'] and not e['actual_lookup_pool_ioctl_thread_or_success_return_adapters']
        assert not any(int(p,16) in forbidden for p in e['pcs'][:-1])
        executed_kernel.update(int(p,16)-t.KBASE for p in e['pcs'][:-1] if t.KBASE<=int(p,16)<t.KBASE+len(t.TEXT))
    text_index=t.ELF.get_section_index('.text');relocations=[]
    sy=t.ELF.get_section_by_name('.symtab')
    for sec in t.ELF.iter_sections():
        if sec['sh_type']=='SHT_RELA' and sec['sh_info']==text_index:
            for rr in sec.iter_relocations():
                relocations.append({'text_offset':rr['r_offset'],'kind':rr['r_info_type'],
                    'symbol':sy.get_symbol(rr['r_info_sym']).name,'addend':rr['r_addend']})
    assert not executed_kernel.intersection(x['text_offset'] for x in relocations)
    failed=STAGE/'run-native-tail-and-callback-20261027'
    assert not json.loads((failed/'attempt-failure.json').read_text())['passing_result'] and not (failed/'allocation-tail-results.json').exists()
    interim=json.loads((STAGE/'run-native-call-instruction-scope-20261027/allocation-tail-results.json').read_text())
    assert interim['bounded_phases']==54 and not interim['goal_complete']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def listing(n,a,z):return {'library':n.path.name,'VA_range':[hex(a),hex(z)],'bytes_sha256':sha(n.read(a,z-a)),
        'original_disassembly':n.dump(a,z) if hasattr(n,'dump') else n.disasm(a,z)}
    def kernel(a,z):return {'module':t.MODULE.name,'section':'.text','section_relative_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(t.TEXT[a:z]),'unrelocated_original_disassembly':[
            {'offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.DF.md.disasm(t.TEXT[a:z],a)]}
    source={'checked_date':'2026-10-27','url':'https://man7.org/linux/man-pages/man2/ioctl.2.html',
        'observation':'The Linux man-pages project describes the operation and argument semantics as driver-dependent.',
        'scope':'Generic interface only. Does not establish Sony handler dispatch, pointer mapping, resource lifetime or recovery.'}
    put(STAGE/'public-source-notes.json',source)
    audit={'created_utc':now,'kernel_module':str(t.MODULE.relative_to(ROOT)),'kernel_module_sha256':t.MODULE_SHA,
        'stage47_manifest_current_sha256':digest(m47),'original_section_text_sha256':sha(t.TEXT),
        'original_sample_hashes':{'user_OSAL':sha(t.OSAL.blob),'DF':sha(t.DF.blob),'MPR':sha(t.MPR.blob),'libc':sha(t.LIBC.blob)},
        'kernel_execution_scope':'Unrelocated text only. Dynamic-client lookup, global-pool literal access, private pool call, fixed block allocation and error logger are stop boundaries. No kernel data/ELF relocations/init/locks/pool service run.',
        'executed_kernel_instructions_have_no_relocation_sites':True,'kernel_text_relocations':relocations,
        'rejection_literal_scope':'Rejected-config route reads unrelocated log-string literals only as parameters to a stopped printk call; never dereferences them or uses them as geometry/control evidence.',
        'geometry':{'entry_offset':'0x3248','original_export_caller':'osal_valloc_msg_wait text+44c0 calls internal3248 at4500',
            'independent_client_entry':'0x3294','pre_pool_stops':['0x32d8','0x3420','0x3508'],
            'independent_declared_block_entry':'0x32f0','aligned_length':'align4(L)',
            'ordinary_overhead_sum_constant':'0x5b =63+24+4','bit31_branch_overhead_sum_constant':'0x83 =63+40+24+4',
            'block_request':'align64(align4(L)+24+4+extra40)','data_offset':'24+extra40',
            'trailer':'original32fc..3330 stores0x77777777 at data+align4(L)',
            'tested_lengths':[44,45,48],'tested_client_modes':[['flags0','pool0'],['flags0','nonzero pool'],['flags8','nonzero pool']],
            'rejection_control':['flags8','pool0'],'actual_runtime_client_configuration_and_pool_success_not_known':True},
        'link_experiment':'Declared kernel-shaped128-byte block, original Dataflow memcpy44 and source setter, independently declared user notification, native pointer delivery, independent MPR post-lock memcpy48. Result44 bytes+77777777 stays inside that declared block; no actual transition continuity.',
        'callback':{'MPR_Init_original_callback_offset':'0x28593c','registration_QID':'0x80c70047','userdata':0,
            'user_worker':'0x3260','ioctl_stop':'0x2530','independent_notification_entry':'0x32e8','BLR_stop':'0x32f0',
            'user_worker_does_not_pad_or_copy_data_before_BLR':True,
            'declared_MPR_load_bias_for_shared_guest':hex(t.MBASE),'MPR48_copy':'0x285998..0x2859bc',
            'actual_registered_callback_thread_mmap_conversion_and_lifetime_not_executed':True},
        'user_ioctl':{'allocation_low32':'0x8000000a','registration_low32':'0x80000008',
            'FD_is_ELF_initial_guest_storage_not_open_device_handle':True,'both_stop_before_ioctl':True,
            'actual_kernel_handler_dispatch_and_mapping_for_these_operations_unverified':True},
        'failure_scope':'Initial instruction range excluded original BL at MPR2859bc, causing stop without passing result. Added that original instruction; no byte patch/output adapter. Interim54 then branch controls70 passed; all versions retained.',
        'original_listings':[kernel(a,z) for a,z in ((0x3248,0x3518),(0x44c0,0x4628),(0x6998,0x69d8))]+
            [listing(t.OSAL,a,z) for a,z in ((0x67b0,0x686c),(0x3e98,0x3f28),(0x3cd8,0x3d68),(0x3260,0x3318))]+
            [listing(t.MPR,a,z) for a,z in ((0x27ddc8,0x27de88),(0x285998,0x2859c8))],
        'real_camera_44_to48_mapping_safety_MAIN16M_backup_restore_or_independent_rescue_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    refinement={'schema':'fx3-offline-internal-storage-observations/1','status':'SPEC_ONLY_UNDEPLOYABLE',
        'refines':'stage111 diagnostic-layout-not-deployable.json','old_sealed_spec_preserved':True,
        'observed_original_reply_wire_bytes':44,'observed_original_MPR_copy_bytes':48,
        'conditional_original_allocator_explanation':{'tested_QID':'0x80c70047','requested_bytes':44,
            'block_request_bytes':128,'data_offset':64,'data_to_block_end':64,'tail_offset':44,'tail_hex':'77777777',
            'copied48_equals_declared_wire44_plus_original_tail4':True},
        'tail_is_allocator_marker_not_additional_wire_payload_or_virtual_pointer':True,
        'conditional_fixture_result_not_global_device_safe_flag':True,
        'live_evidence_still_required':['actual client configuration','actual pool allocation extent/owner',
            'ioctl handler and user pointer conversion','user readable extent covering48 bytes',
            'callback identity and valid storage through copy','message release/refcount generation',
            'real hardware Open/Start,target file and corresponding recovery'],
        'not_USB_protocol_or_authorization_to_open_camera':True,'guest_prototype_changed':False,'goal_complete':False}
    put(STAGE/'diagnostic-storage-refinement.json',refinement)
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'geometry_cases':16,'rejected_configuration_cases':2,'ioctl_argument_cases':4,'registration_cases':2,
        'linked_independent_flows':2,'bounded_phases':70,'formal_source_matches_executed_copy':True,
        'same_agent_review_not_independent_engine':True,'actual_kernel_services_or_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));rr=str((run/'allocation-tail-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name;g['research_activity']='Mac_only_native_allocation_geometry_tail_marker_user_callback_routing_and_conditional44_to48_extent'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11112件封存/canonical及目标卷核对；复用阶段47原osal_uipc.ko并校验固定SHA，未装载模块。',
            '原内部分配算术/头尾写入在声明客户端/块条件下执行：44B请求128B块，负值ID数据偏移64，data+44尾标记77777777。',
            '原Dataflow44B发送后段保留尾标记，用户回调原代码原样传指针，独立MPR48B复制得到44B+4B尾标记且在声明块内；不是实际ioctl/映射/回调线程/锁连续运行。',
            '客户端三种有效声明模式、flags8无池拒绝及44/45/48对齐对照，原注册与ioctl参数封装核对；正式70阶段。原BL范围遗漏失败及54阶段中间结果保留。',
            '阶段11144/48差异有条件原代码解释，实际客户端配置、池结果、用户可读映射和释放代次仍缺，不能作全机安全标记。',
            'MAIN自然来源、FH/16M、实机成片/音画/长录及同机备份恢复/独立救援仍未验收，16项状态、权限与阶段75不可部署原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage112_allocation_tail_and_callback']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','storage_refinement':rel+'/diagnostic-storage-refinement.json',
        'review':rel+'/completed-evidence-review.json','scope':'70 bounded phases show original conditional128-byte allocation geometry and77777777 trailer explaining44-to48 copy in declared storage; no live registry,pool,ioctl,user mapping,thread lifetime or hardware/recovery proof.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-storage-refinement.json'])
            req['stage112_scope']='原分配分支与尾标记、用户回调指针及声明块内44+4复制70阶段；当前客户端/池/mmap/释放生命周期未证，不把有条件容量解释当实际设备安全或硬件验收。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original kernel allocator reserves aligned header/prefix/trailer space. For tested44-byte80c70047 branches request128,data+64,guard77777777 at data+44; original44 copy and48 reply copy fit declared block and include guard. Refines prior unresolved wire/storage difference conditionally; real ioctl mapping,active client/pool and lifetime unproved.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段112后追原ioctl处理/用户指针转换、客户端池初始化与真实释放/引用代次；44B与48B已有原128B块/尾标记条件解释，但不能替代当前用户可读范围与所有权验证。继续正常MC回复来源/非零状态上层消费/单流外层串行化，保留自然MAIN和FH16M缺口；仅Mac，实机录制与同机恢复及独立救援要求不变。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 分配空间与回复尾标记](<'+rel+'/README.md>)：原128B块/77777777尾标记解释声明条件下44→48复制，70阶段；实际池/用户映射/寿命及硬件恢复仍待验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage112-allocation-tail/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':70,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
