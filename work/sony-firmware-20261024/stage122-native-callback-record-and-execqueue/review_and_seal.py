#!/usr/bin/env python3
"""Seal native queue and callback-record scope; no runtime lifetime guarantee."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import callback_queue as t
ROOT,BASE=t.ROOT,t.BASE
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for x in prior['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-native-owner-queue-20261027';p=out/'callback-queue-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_CALLBACK_RECORD_AND_QUEUE_POINTER_LIFETIME_SCOPE_NOT_RUNTIME_ACCEPTANCE'
    assert j['source_sha256']==digest(STAGE/'callback_queue.py') and (out/'executed-source.py').read_bytes()==(STAGE/'callback_queue.py').read_bytes()
    groups=('initializers','lookups','queues','release_boundaries');assert [len(j[k]) for k in groups]==[2,6,2,2]
    ev=[e for k in groups for c in j[k] for e in c['events']];assert len(ev)==j['bounded_phases']==54
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_MAIN_hardware_instance_recovery_or_lifetime_proven'):assert not j[k]
    for e in ev:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0x7dfa0,0x819a0,0x7f520,0x81d30,0x7f190,0x7d630,0x7c5f0,0x7d8b0,0x80ef0,0xc8c70}
    for e in ev:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['initializers']:
        assert len(bytes.fromhex(c['native384']))==384 and len(c['unwritten_padding_offsets'])==28
        assert not c['actual_malloc_lock_or_healthy_owner_proven']
    for c in j['lookups']:
        assert c['key']==17 and c['native_return']==(hex(t.OWNER) if c['create_input'] else '0x0')
        assert not c['actual_record_key_identity_lock_and_registration_lifetime_proven']
    for c in j['queues']:
        assert c['descriptor_bytes']==0x8ea0 and c['native_copied_callback_pointer']==hex(t.OWNER)
        assert c['native_indirect_target']=='0xca6e4' and c['native_worker_argument']==hex(t.OLD)
        assert all(c[k] for k in ('declared_owner_bytes_unchanged_through_native_copy_dispatch_and_pop_slices',
            'all_real_allocation_thread_services_complete_Start_and_delete_unexecuted',
            'post_job_and_post_delete_frames_not_proof_of_completion_or_free',
            'no_actual_owner_lifetime_all_async_consumers_or_safe_rollback_proven'))
    for c in j['release_boundaries']:assert not c['actual_free_release_order_or_safe_owner_reclamation_proven']
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/4';contract['refined_in_stage']=STAGE.name
    contract['callback_record_lifetime']={'allocator_ELF':'0xfbf84','allocation_bytes':384,'record_count':4,'record_stride':96,
        'constructor_unwritten_padding_bytes':28,'lookup_register_ELF':'0xfc074','release_wrapper_ELF':'0xfbff8',
        'actual_allocator_or_record_lifetime_proven':False,
        'queue_descriptor_bytes':0x8ea0,'descriptor_callback_pointer_offset':'0x30','descriptor_function_pointer_offset':'0x8e98',
        'worker_original_indirect_target_in_guest':'mpr::ExecEncStart','copied_pointer_does_not_mean_owned_snapshot':True,
        'queue_pop_delete_argument_is_queue_block_in_declared_case':True,
        'queue_empty_or_pop_not_all_async_callbacks_complete':True,
        'required_before_runtime_reclamation':['actual record allocation/instance and active-key association','all queued/current descriptors and producers observed',
            'all asynchronous error/completion callbacks finished or safely unregistered','complete cancel/stop and worker lifetime contract',
            'actual same-body backup/restore readback and independent rescue requirements remain']}
    contract['next_runtime_acceptance_requirements'].append('separate execqueue block lifetime from external384-byte callback records; do not reclaim either from a queue-empty or local return observation alone')
    put(STAGE/'diagnostic-contract.json',contract)
    targets={0xfbf84:[],0xfbff8:[],0xfc074:[]};sec=t.MPR.elf.get_section_by_name('.text');data=sec.data();base=sec['sh_addr']
    for o in range(0,len(data)-3,4):
        w=struct.unpack_from('<I',data,o)[0]
        if w&0xfc000000!=0x94000000:continue
        v=w&0x3ffffff;dest=base+o+(v-(1<<26) if v&(1<<25) else v)*4
        if dest in targets:
            pc=base+o;names=[n for n,s in t.MPR.symbols.items() if s['size'] and s['va']<=pc<s['va']+s['size']]
            targets[dest].append({'site':hex(pc),'named_contexts':names[:2]})
    ranges=((0xfbf84,0xfc168),(0xd63a4,0xd6464),(0xd64e4,0xd6530),(0xdbf94,0xdc090),
        (0xd6880,0xd688c),(0xd6948,0xd6964),(0xdc7dc,0xdc7f8))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.prev.prev.front.LIBC.path),'listings':listings,
        'direct_BL_references_only_not_indirect_or_complete_callgraph':{hex(k):v for k,v in targets.items()},
        'four_record_initialization_size_and_padding_checked':True,'native_single_element_deque_block_branch_used':True,
        'queue_block_delete_and_record_free_are_distinct_call_arguments_in_guest':True,
        'descriptor_prefix_is_declared_fixture_not_complete_EnqueueExecEncStart_output':True,
        'post_job_frame_does_not_claim_ExecEncStart_completed':True,
        'extra_guest_window_guard':'0x60000000..0x60014000 mapped only in Unicorn, full outside-declared-output comparison',
        'all_actual_allocators_pthread_signal_logs_free_delete_and_hardware_unexecuted':True,
        'no_claim_Sony_has_premature_release_or_lacks_higher_level_reference_protection':True,
        'bounded_phases':54,'original_FX3_file_or_frontend_backend_modified':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':12,'bounded_phases':54,'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_callback_record_initialization_and_execqueue_copy_dispatch_pop_lifetime_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段121十三件封存/canonical核验；12例54原片段，未运行设备或Windows。',
            '384字节四记录原初始化，28字节padding保留旧值；原查找/登记和独立free入口，真实对象/锁与释放未验。',
            '原队列单元素块分支复制8ea0描述符，原worker BLR进入ExecEncStart序言；记录指针保持，完整Start/线程服务未执行。',
            '独立post-job/pop/delete片段只推进队列块，外部记录寿命必须单独核对，不以队列空充回收/恢复完成。',
            '16项状态与权限保持，原固件及旧前后端保持，目标实录及恢复未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage122_callback_record_execqueue']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'54 bounded phases show native callback-record initialization/lookup and execqueue copy/dispatch/pop arguments. Queue block lifetime differs from external callback records; actual owner, all async consumers and safe reclamation remain unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11','G15'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage122_scope']='原四回调记录与队列复制/分派/弹出54阶段；区分队列块和外部记录寿命，post-job/delete非实际完成，不能从队列空放行回收/恢复。实机与同机恢复仍缺，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Native descriptor copy preserves an external callback-record pointer; native worker enters ExecEncStart and independent pop slices target the deque block. Record free has a separate wrapper. This does not establish actual worker completion, all async users or safe owner/module reclamation.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段122后沿NotifyAllMovieWriteFinishedParam/FileQueueStreamWriteCmp等记录释放与结果/错误回调调用者核对同一实例和复用顺序，结合完整execRecMovie任务及正常Start回复；队列块与外部384记录寿命分别验，不用队列空/局部返回代替全异步退出。仅Mac，16项主录与同机恢复独立救援不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 回调记录与执行队列寿命](<'+rel+'/README.md>)：12例54片段核对384字节记录、8ea0任务复制及原worker分派；队列块和外部记录分开验，实际完成/回收/恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage122-callback-record-queue/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':54,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
