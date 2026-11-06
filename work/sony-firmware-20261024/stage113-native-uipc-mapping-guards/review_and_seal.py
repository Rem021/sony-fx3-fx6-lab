#!/usr/bin/env python3
"""Review and seal original UIPC local rules without promoting runtime gates."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import mapping_guards as t
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
    run=STAGE/'run-inclusive-address-limit-20261027';p=run/'mapping-guard-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_ORIGINAL_DISPATCH_MAPPING_GUARDS_AND_DECLARED_AFFINE_POINTER_SLICES'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'mapping_guards.py').read_bytes()
    assert j['source_sha256']==digest(STAGE/'mapping_guards.py') and j['module_sha256']==t.MODULE_SHA
    assert not any(j[k] for k in ['goal_complete','persistent_write_release','Windows_UU_camera_operations','real_ioctl_kernel_services_mapping_hardware_or_recovery_proven'])
    groups=('dispatch_cases','allocation_entry_cases','mapping_flows','free_range_cases','mmap_length_cases','mmap_status_cases')
    assert tuple(len(j[k]) for k in groups)==(30,10,4,10,6,4)
    events=[e for k in groups for c in j[k] for e in c['events']];assert len(events)==j['bounded_phases']==112
    expected_table={hex(0x340+i*8):hex(t.KBASE+a) for i,a in enumerate(t.TARGETS)}
    rs=j['local_ABS64_relocations'];assert rs==t.RELOCS and len(rs)==21
    assert {x['offset']:x['guest_value'] for x in rs if x['section']=='.rodata'}==expected_table
    roots=[x for x in rs if x['section']=='.text' and x['offset']!='0x5b8']
    assert len(roots)==3 and all(x['target_section']=='.bss' and x['original_addend']=='0x50' for x in roots)
    for c in j['dispatch_cases']:
        assert not c['actual_copy_dispatch_registration_mapping_or_process_binding_proven']
        ptr,limit=int(c['declared_user_record_pointer'],16),int(c['declared_address_limit'],16)
        admitted=ptr+15<=limit and ptr+15<=0xffffffffffffffff
        assert c['last_byte_range_admitted_before_copy']==admitted
        if not admitted:assert c['outcome']=='user_record_range_rejected'
        elif c['outcome']=='declared_copy_fault_rejected':assert c['events'][-1]['return_u32_if_returned']==0xffffffea
        elif int(c['declared_opcode'],16)&0x7fffffff>16 or not c['declared_mapping_present'] and int(c['declared_opcode'],16)&0x7fffffff!=16:
            assert c['outcome']=='opcode_or_mapping_rejected'
        elif not c['declared_owner_matches']:assert c['outcome']=='owner_mismatch_route'
        else:assert c['outcome']=='original_table_target_before_call'
    for c in j['allocation_entry_cases']:
        assert not c['actual_user_copy_or_allocation']
        if c['case'] in ('short_limit','wrap'):assert c['outcome']=='parameter_range_rejected'
        elif c['case']=='null_outcell':assert c['outcome']=='null_outcell_rejected'
        else:assert c['outcome']=='original_allocator_args_before_call'
    for c in j['mapping_flows']:
        assert c['independent_slices_not_real_allocation_queue_user_mapping_or_lifetime']
        user=int(c['declared_userbase'],16)+c['declared_data_offset']
        assert int(c['original_alloc_user_pointer'],16)==int(c['original_callback_user_pointer'],16)==user
        assert int(c['original_free_kernel_pointer'],16)==t.KPOOL+c['declared_data_offset']
        assert len(c['events'])==4
    for c in j['free_range_cases']:
        assert c['native_range_admitted_before_free']==(0<=c['declared_pointer_offset']<t.POOLSIZE)
        assert c['single_pointer_check_not_object_extent_refcount_or_generation_validation'] and not c['actual_free_executed']
    for c in j['mmap_length_cases']:
        assert c['exact_length_admitted_before_PFN_math']==(c['declared_length']==t.POOLSIZE)
        assert not c['actual_PFN_math_remap_or_mapping_creation']
    for c in j['mmap_status_cases']:
        assert c['context_base_after']==('0x48000000' if c['independent_declared_remap_status']==0 else '0x40000000')
        assert c['actual_remap_success_or_failure_not_simulated']
    forbidden={t.KBASE+a for a in [0x530,0x580,0x590,0xcbc,0xcd8,0xd28,0xd48,0x7a0,0xa24,0xd9c,0xe20]}
    executed=set()
    for e in events:
        assert all(e[k] for k in ['all_mapped_images_unchanged','scratch_outside_declared_outputs_unchanged',
            'stack_outside_declared2048_bytes_unchanged','SP_EL0_fixture_unchanged'])
        assert not e['executed_external_services_or_return_adapters']
        executed.update(int(a,16) for a in e['pcs'][:-1])
        assert not forbidden.intersection(int(a,16) for a in e['pcs'][:-1])
        assert all(set(c)=={'return_instruction','return_x0'} for c in e['native_returns'])
    # No executed instruction has been changed by data-pointer relocation.
    changed={i for i,(a,b) in enumerate(zip(t.prev.TEXT,t.TEXT)) if a!=b}
    assert not any(any(pc-t.KBASE+i in changed for i in range(4)) for pc in executed if t.KBASE<=pc<t.KBASE+len(t.TEXT))
    for folder in ['run-original-pointer-guards-20261027','run-native-return-observer-20261027']:
        f=STAGE/folder;failure=json.loads((f/'attempt-failure.json').read_text())
        assert failure['status']=='FAILED_NO_PASSING_RESULT' and not (f/'mapping-guard-results.json').exists() and (f/'executed-source.py').exists()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    listing=[]
    for a,z in [(0x4d8,0x5b8),(0x778,0x7b8),(0x9f0,0xa28),(0xc70,0xd68),(0xd70,0xe60)]:
        listing.append({'section_relative_range':[hex(a),hex(z)],'original_bytes_sha256':sha(t.prev.TEXT[a:z]),
            'original_disassembly':[{'offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
                for i in t.prev.DF.md.disasm(t.prev.TEXT[a:z],a)]})
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27',
        'primary_source':'https://docs.kernel.org/core-api/mm-api.html#c.remap_pfn_range',
        'observation':'Generic Linux documentation describes remapping kernel physical page frames into a user VMA, requiring the relevant MM lock; zero indicates success.',
        'scope':'Generic function contract, not Sony mapping success, task ABI or rescue evidence.',
        'extra_reference_fetch':{'url':'https://raw.githubusercontent.com/torvalds/linux/v4.9/arch/arm64/include/asm/uaccess.h',
            'result':'web fetch429; not relied on for range semantics. Original Sony instructions and explicit last-byte controls used.'}})
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_module':str(t.MODULE.relative_to(ROOT)),
        'module_sha256':t.MODULE_SHA,'stage47_member_verified':True,'local_ABS64_relocations':rs,
        'root_relocation_section':'.bss+0x50, pool pointer at root+0x40; not .data',
        'guest_text_base':hex(t.KBASE),'guest_rodata_base':hex(t.RBASE),'guest_bss_base':hex(t.BBASE),
        'original_executed_instruction_bytes_unchanged':True,'actual_kernel_module_loader_executed':False,
        'declared_inputs':['virtual CPU SP_EL0/task fields/address-limit/mm','per-open owner/mapping context',
            'copied argument record after stopped copy','pool and data pointers after stopped allocation',
            'pending callback fields after stopped queue/lock logic','independent remap status after stopped PFN/remap'],
        'guard_scope':'16-byte range uses last byte pointer+15 <= declared limit; passing does not establish actual readable mapping.',
        'dispatch_table_original_offsets':t.TARGETS,'mapping':'user = userbase + kernelData - kernelPool',
        'callback_header_to_data_bytes':24,'free_range':'unsigned(user-userbase)<=0x1fffff, single pointer only',
        'mmap_length_required':t.POOLSIZE,'PFN_math_remap_usercopies_alloc_free_dispatch_lock_logging_executed':False,
        'conditional_remap_publication':'Independent status0 writes VMA start to context+30; independent nonzero retains oldbase.',
        'failure_scope':'First harness incorrectly prohibited original RET observation; second assumed exclusive limit. Both failed runs/source retained. Fixed observer and inclusive last-byte expectation only; no Sony instruction/output or successful dependency adapter.',
        'original_listings':listing,'goal_complete':False,'persistent_write_release':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'case_counts':{k:len(j[k]) for k in groups},'bounded_phases':112,'local_ABS64_data_relocations':21,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'original_executed_instruction_bytes_unchanged':True,'actual_kernel_services_camera_or_Windows_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_UIPC_dispatch_guards_affine_pointer_translation_and_conditional_mapping_publication'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11215件封存/canonical/目标卷核对，复用阶段47固定SHA原模块，未装载模块。',
            '原分发范围、操作号、mmap前提、mm归属及原17项表来源；所有用户复制/BLR/内核服务停前，输入分段声明。',
            '原分配和回调的userbase+(Kdata-Kpool)及释放反算，单指针2MiB边界；原mmap精确2MiB及独立状态条件发布，共112阶段。',
            '局部21项ABS64原数据重定位在guest应用；原指令不变；根为.bss+50，保留两次测试脚本假设失败。',
            '互逆转换不是实际用户映射/池/回调寿命证据；自然MAIN和FH16M、成片、音画长录及同机恢复与独立救援保持未验收。',
            '16项目标状态、权限、Mac-only与阶段75不可部署原型保持，不能放行刷写。'],'completion_not_claimed':True}
    g['latest_stage_evidence']['stage113_uipc_mapping_guards']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'Original dispatch/range/mmap guards and independent affine pointer slices; 112 bounded phases. No real mapping, client/pool/queue lifetime, Open/file or rescue.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json'])
            req['stage113_scope']='原UIPC分发/mmap前提/进程归属和独立指针正反转换112阶段；单指针范围不等于消息容量/身份/寿命，实际映射/线程/硬件未证。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original UIPC kernel slices establish affine user/pool conversion and inverse, dispatch mapping/owner checks and exact2MiB map gate. Root literal relocates to .bss+50. Last-byte range controls correct an interim harness assumption; actual usercopies/remap/queue lifetime remain unexecuted.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段113后追原客户端/池建立及释放引用代次，继续正常MC回复、MAIN自然参数和FH/16M资源匹配；将当前规则纳入具体同机诊断/健康备份方案。用户映射、实际编码成片和独立救援仍需实机证据；Windows继续延后，仅Mac，不能因单指针范围或互逆算术放行刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原UIPC映射与分发守卫](<'+rel+'/README.md>)：原操作分发/归属/2MiB映射限制及独立指针正反转换112阶段；真实映射、寿命、MAIN实录与恢复仍未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage113-uipc-mapping-guards/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':112,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
