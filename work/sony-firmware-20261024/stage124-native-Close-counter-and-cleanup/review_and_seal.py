#!/usr/bin/env python3
"""Seal Close counter and cleanup scope; never a hardware shutdown claim."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import close_counter as t
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
    out=STAGE/'run-native-Close-counter-20261027';p=out/'close-counter-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_CLOSE_COUNTER_DECISION_AND_CLEANUP_SCOPE_NOT_FULL_SHUTDOWN'
    assert j['source_sha256']==digest(STAGE/'close_counter.py') and (out/'executed-source.py').read_bytes()==(STAGE/'close_counter.py').read_bytes()
    groups=('decision_cases','cleanup_cases','classifier_cases');assert [len(j[k]) for k in groups]==[8,4,6]
    ev=[e for k in groups for c in j[k] for e in c['events']];assert len(ev)==j['bounded_phases']==108
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_Close_global_quiescence_MAIN_recording_or_recovery_proven'):assert not j[k]
    for e in ev:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0x7dfa0,0x80ef0,0xc8c70,0x7f6f0,0x7fe70,0x82ca0}
    for e in ev:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['decision_cases']:
        count=c['initial_count'];remain=count-(1 if c['request_control24']==0 and count else 0)
        assert c['native_remaining_count']==remain and ('bypassed' in c['outcome'])==bool(remain)
        assert c['sum_uses_native_GetRecordCounter_from_declared_global_bytes']
        assert c['all_log_lock_Codec_call_and_real_counter_runtime_values_unexecuted'] and not c['actual_complete_Close_hardware_or_shared_owner_quiescence_proven']
        names=[x.get('original_symbol_binding') for e in c['events'] for x in e['original_imports_and_returns']]
        assert '_ZN3mpr16GetRecordCounterEjPh' in names
        assert ('_ZN3mpr16SetRecordCounterEjh' in names)==bool(c['request_control24']==0 and count)
    for c in j['cleanup_cases']:
        assert c['native_mode_word_cleared'] and c['mode_word_zero_not_DMM_release_or_full_Close_completion_proof']
        assert not c['actual_free_or_Codec_completion_proven']
    for c in j['classifier_cases']:
        assert c['native_factor']==(1 if c['kind']=='synthetic_sub8' else 0x1006)
        assert not c['actual_Close_reply_generation_or_arrival_proven']
    relocs=[]
    for sec in t.MPR.elf.iter_sections():
        if sec['sh_type']=='SHT_RELA':
            sy=t.MPR.elf.get_section(sec['sh_link'])
            for x in sec.iter_relocations():
                if x['r_offset'] in (0x2f9c40,0x2f9c70,0x2f9658,0x2fa670):
                    s=sy.get_symbol(x['r_info_sym']);assert x['r_info_type']==1025
                    relocs.append({'GOT':hex(x['r_offset']),'type':'R_AARCH64_GLOB_DAT','symbol':s.name,'ELF_VA':hex(s['st_value']),'bytes':s['st_size']})
    assert len(relocs)==4
    counter=next(x for x in relocs if x['GOT']=='0x2f9c40')
    assert counter['symbol']=='_ZN3mpr15s_recordCounterE' and counter['ELF_VA']==hex(t.COUNTERS) and counter['bytes']==4
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/6';contract['refined_in_stage']=STAGE.name
    contract['Close_observation']={'counter_symbol':'mpr::s_recordCounter','counter_bytes':4,'counter_elements_are_bytes':True,
        'Close_sum_uses_s_movieRecInfo_index_list':True,'tested_list_count':1,'tested_valid_indices':[0,1,2,3],
        'control_word_request24_static_origin':'MovieRecInfo+a6c','remaining_nonzero_can_bypass_Codec_Close':True,
        'counter_is_not_proven_reference_count_of_all_hardware_consumers':True,
        'single_Close_call':{'CodecType':32,'declared_FileFormat':15,'count':1,'ViewId':0,'parameter_bytes':16,'reply_storage_bytes':48},
        'expected_factor':0x1006,'synthetic_matching_reply':{'MID':0x4e0,'subcode':9,'factor':0x1006},
        'mode_word_cleared_in_both_declared_DMM_false_and_true_tail':True,
        'mode_word_zero_or_Close_task_return_not_shutdown_or_DMM_free_proof':True,
        'observed_nested_lock_order':'ExecEncClose integration-record lock then record-counter lock; actual locks/reentrancy and complete hierarchy unverified',
        'observe_actual_Codec_reply_DMM_and_stream_buffer_delete_results':True,'actual_global_quiescence_recovery_proven':False}
    contract['next_runtime_acceptance_requirements'].append('capture all relevant record counts/index provenance, actual Close dispatch/reply and each buffer/DMM cleanup outcome; mode-word0 or completed Close task alone cannot release the runtime gate')
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xcf0d0,0xcf3ac),(0xce824,0xce8e4),(0xcebe0,0xcec9c),(0xd6e20,0xd6e7c),
        (0x27e2c0,0x27e320),(0x27dfd0,0x27dffc),(0x27f534,0x27f558))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    sys.path.insert(0,str(BASE/'stage116-scoped-MAIN-frontend'));import frontend_trial as front
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(front.LIBC.path),'relevant_original_relocations':relocs,'listings':listings,
        'counter_getter_and_setter_original_bodies_executed_no_success_return_adapters':True,
        'global_counter_and_list_values_are_declared_guest_inputs_not_current_camera':True,
        'remaining_count_skip_Close_is_observed_native_branch_not_claimed_defect':True,
        'DMM_low_byte_results_are_independent_tail_inputs_not_actual_FreeDmmMemory_returns':True,
        'real_Codec_Close_reply_all_lock_log_buffer_delete_DMM_release_unexecuted':True,
        'only_declared_counter_bytes_and_mode_word_allowed_as_guest_ELF_data_outputs':True,
        'no_claim_Sony_leak_or_failed_cleanup_on_real_hardware':True,'bounded_phases':108,
        'original_FX3_file_or_frontend_backend_modified':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':18,'bounded_phases':108,'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_Close_record_counter_decision_reply_factor_and_cleanup_tail_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段123十件封存/canonical核验；18例108原片段，无设备/Windows操作。',
            '原Close接Get/SetRecordCounter实际字节读写，剩余非零跳过CodecClose；源列表/计数是人工输入，索引0..3。',
            '原单流Close参数16/回复48指针与事件期待1006；实际CodecClose及回复未验。',
            '独立DMM真假尾部都清a6c控制字，清零不充释放成功；原嵌套锁顺序定位，完整并发层级未验。',
            '16项状态、权限、原固件/旧前后端保持，真实主录/全退出及同机恢复未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage124_Close_counter_cleanup']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'108 native bounded phases show record-counter-dependent Close dispatch/bypass, event factor1006, and common mode-word clear under independent DMM boolean inputs. Real shutdown, buffer release and recovery remain unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11','G15'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage124_scope']='原Close计数读写/分支/事件1006及清理尾部108阶段；剩余计数非零可不关闭Codec，控制字清零不充DMM释放成功。实际关闭/全部消费者/恢复未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Native Close may bypass Codec close while record counts remain; common mode-word clear occurs under both independently declared DMM boolean outcomes. Actual Close dispatch/reply and buffer cleanup must be observed separately, not inferred from a task return or flag0.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段124后核对完整Close/流缓冲删除/DMM释放及其实际结果传播、全部记录计数/列表来源和嵌套锁调用上下文，再关联AllMovieWriteFinished上游条件/正常Start回复。任务返回、非零计数分支、控制字0均不充全关闭/全退出。仅Mac，16项实录与同机恢复/独立救援不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 Close计数与清理结果](<'+rel+'/README.md>)：18例108片段接原计数器与Close分支，剩余计数可跳过关闭；模式字清零非DMM释放证明，真实主录/全退出/恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage124-Close-counter-cleanup/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':108,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
