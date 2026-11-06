#!/usr/bin/env python3
"""Seal native status lock contract; no live idle or epoch acceptance."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import record_status as t
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
    out=STAGE/'run-native-status-lock-20261027';p=out/'record-status-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_RECORD_STATUS_COPY_LOCK_CONTRACT_NOT_LIVE_IDLE_OR_EPOCH'
    assert j['source_sha256']==digest(STAGE/'record_status.py') and (out/'executed-source.py').read_bytes()==(STAGE/'record_status.py').read_bytes()
    groups=('constructors','getters','explicit_unlocks','setters','integration_mutex_sites','public_wrappers')
    assert [len(j[k]) for k in groups]==[2,4,2,14,6,2]
    events=[e for k in groups for c in j[k] for e in c['events']]
    assert len(events)==j['bounded_phases']==50
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_record_idle_configuration_epoch_MAIN_encoding_or_recovery_proven'):assert not j[k]
    for e in events:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0x81860,0x82530,0x7f060,0x7c5f0,0x81e90,0x820e0}
    for e in events:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['constructors']:assert c['bytes']==136 and c['header']==83 and c['zeros_not_claimed_idle_or_live_slots']
    for c in j['getters']:
        assert c['lock_object']==hex(t.LOCK) and c['pthread_lock_pointer']==hex(t.LOCK+8) and c['copy_bytes']==136
        assert c['ForUpdate_not_a_read_only_diagnostic_candidate']==c['ForUpdate'] and c['source_not_real_camera_status']
        assert c['original_return_does_not_prove_actual_lock_or_live_state']
        assert len(c['events'])==(2 if c['ForUpdate'] else 3)
    for c in j['setters']:
        changed=c['kind'] in ('global_word44','first_group_row2','second_group_row3')
        assert c['global_copied']==changed and c['notification_prepared']==(changed or c['force_input'])
        assert c['preheld_lock_is_declared_not_acquired'] and c['no_actual_event_dispatch_recording_or_epoch_proof']
    for c in j['integration_mutex_sites']:
        assert c['original_mutex_object']==hex(t.INTEG) and not c['actual_mutual_exclusion_current_thread_all_writers_or_start_completion_proven']
    assert t.LOCK!=t.PARAM_LOCK!=t.INTEG
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    # Stage117's frontend remains sealed even though the immediate predecessor is118.
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract={'schema':'fx3-offline-status-diagnostic-candidate/1','status':'UNDEPLOYABLE_UNAUTHORIZED_DEVICE_USE',
        'model':'classic ILME-FX3','firmware_sample':'7.02','address_kind':'ELF virtual addresses; actual process base and same-body identity missing',
        'candidate_reader':{'symbol':'mpr::GetMovieRecStatusInternal','ELF_entry':hex(0xf3f7c),'output_bytes':136,
            'scope':'native reader/copy/unlock call order only; runtime pthread and caller context unverified'},
        'exclude_from_read_only_diagnostic':['GetMovieRecStatusForUpdate','SetMovieRecStatus','UnlockMovieRecStatus',
            'SetMovieRecParam','RecStart','RecStop'],
        'status_header':83,'constructor_zero_body_does_not_mean_idle':True,
        'state_and_parameter_queries_do_not_provide_atomic_joint_snapshot':True,
        'three_sync_objects':{'status_rwlock':hex(t.LOCK),'parameter_rwlock':hex(t.PARAM_LOCK),'integration_API_mutex':hex(t.INTEG)},
        'shared_integration_mutex_covers_all_async_writers_or_epoch':False,
        'auxiliary_parameter_pointer_policy':'Collect length/pointer metadata only; no dereference until actual bounded region, lifetime and synchronization proven.',
        'next_runtime_acceptance_requirements':['exact same-body loaded program identity/base and ABI','authorized non-device-writing observation route',
            'normal caller/thread context and lock order/reentrancy','real valid entries, media/slot and state semantics',
            'full immutable value/auxiliary ownership snapshot and actual record instance relation',
            'all Start/Stop/async completion and config writers mapped into a verified synchronization/lifetime contract'],
        'runtime_idle_epoch_or_record_start_admission_available':False,'camera_interface_or_code_load_or_persistent_write_permitted':False,
        'actual_MAIN_hardware_recording_backup_restore_or_rescue_proven':False}
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xc9660,0xc9690),(0xf3d2c,0xf3edc),(0xf3f7c,0xf3fc8),(0xf4168,0xf41a8),
        (0xf41ec,0xf4230),(0xf4250,0xf4270),(0xf0fe8,0xf0ff0),(0xf1238,0xf1284),
        (0xf1054,0xf1088),(0xdc554,0xdc55c),(0xd84a8,0xd84b0),(0xccd08,0xccd3c),
        (0xd9f7c,0xd9fac),(0xdc46c,0xdc4c8),(0xb7f44,0xb7f9c),(0xb8158,0xb8190))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    relocs=[];wanted={0x2fae70:'_ZN3mpr13s_movieRWlockE',0x2faae8:'_ZN3mpr16s_movieRecStatusE',0x2f9418:'_ZN3mpr15g_integApiMutexE'}
    for sec in t.MPR.elf.iter_sections():
        if sec['sh_type']=='SHT_RELA':
            sy=t.MPR.elf.get_section(sec['sh_link'])
            for x in sec.iter_relocations():
                if x['r_offset'] in wanted:
                    s=sy.get_symbol(x['r_info_sym']);assert x['r_info_type']==1025 and s.name==wanted[x['r_offset']]
                    relocs.append({'GOT':hex(x['r_offset']),'type':'R_AARCH64_GLOB_DAT','symbol':s.name,'target_ELF_VA':hex(s['st_value']),'symbol_bytes':s['st_size']})
    assert len(relocs)==3 and digest(t.MPR.path)=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.front.LIBC.path),'same_firmware_data_relocations':relocs,'listings':listings,
        'native_public_overload_not_executed':'f3fc8 includes logging, optional media-rate checks and internal getter; wrapper stops at its PLT entry.',
        'native_status_writer_has_no_acquire_but_unlocks':'f3d2c relies on pre-held update contract; no actual lock was held in this guest.',
        'same_event_integer_not_cross_namespace_identity':'0x1004 and nine change flags are not an epoch or binding to APP callback registry.',
        'status_semantics_and_live_media_identity_unproven':True,'original_FX3_file_or_frontend_backend_modified':False,
        'all_runtime_pthread_logs_SetIssueEvent_and_recording_calls_unexecuted':True,'bounded_phases':50})
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27','sources':[{
        'url':'https://support.d-imaging.sony.co.jp/app/sdk/en/','observation':'Sony lists classic FX3 Ver2.00+ as supported; device-specific API/interface support must be checked in API reference.',
        'scope':'No FX3-specific status property table obtained, no private module/firmware recovery or runtime state binding established.'}],
        'failed_fetches':[{'url':'https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_rwlock_rdlock.html','error':'403'},
            {'url':'https://pubs.opengroup.org/onlinepubs/9699919799/functions/pthread_rwlock_wrlock.html','error':'403'}],
        'pthread_implementation_not_executed':True})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':30,'bounded_phases':50,'same_agent_review_not_independent_engine':True,
        'formal_source_matches_executed_copy':True,'stage117_frontend_and_stage75_backend_unchanged':True,
        'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_record_status_copy_update_lock_contract_and_common_API_mutex_candidates'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段118十二件封存/canonical与目标卷核验；状态原代码30例50阶段。',
            '录制状态136字节、独立读写锁与参数445字节/另一锁区分；ForUpdate保留写锁，SetStatus依赖配对锁并解锁，排除于只读候选。',
            '原Set/Start/Stop同一g_integApiMutex调用实参核对；真实锁、异步写者覆盖/重入和实际状态语义仍未验。',
            '状态选择字段比较及通知不充合法性/代次，构造全零不充空闲；形成不可部署诊断约束。',
            '原固件与旧前后端保留，16项状态和权限保持；硬件/成片/恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage119_record_status_lock_contract']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'50 native bounded phases distinguish status reader/update lock ownership and three synchronization objects. Common API mutex references are a candidate boundary, not proof of all async writers or actual idle/epoch.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage119_scope']='原状态读取/更新锁配对及Set/Start/Stop同一API互斥锁引用50阶段；排除ForUpdate等只读误用。真实状态/锁和全写者/配置代次仍缺，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'ForUpdate returns a copied136-byte state without unlocking, and status setter relies on a pre-held update lock. The status and parameter rwlocks differ; shared Set/Start/Stop integration mutex references provide a boundary candidate only. No real idle or configuration epoch inferred.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段119后沿实际录制实例和介质/槽位状态写者核对可信状态语义、共同API锁顺序及异步覆盖，再接完整参数与Start消费者；只读候选排除ForUpdate/Set/Unlock。状态与参数独立读取非共同快照，通知数值不充代次；仍仅Mac，主录成片及恢复验收不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 录制状态与锁配对](<'+rel+'/README.md>)：30例50个原片段区分状态读取/更新事务和参数锁，定位Set/Start/Stop共用API互斥锁候选；实际空闲/代次/编码恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage119-record-status-lock-contract/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':50,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
