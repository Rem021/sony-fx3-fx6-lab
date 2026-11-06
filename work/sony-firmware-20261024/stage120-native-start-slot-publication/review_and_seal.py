#!/usr/bin/env python3
"""Seal actual slot-byte origins, not MAIN encoder admission."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import slot_publication as t
ROOT,BASE=t.ROOT,t.BASE
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def bl(a):
    w=struct.unpack('<I',t.MPR.read(a,4))[0];assert w&0xfc000000==0x94000000
    v=w&0x3ffffff;return a+(v-(1<<26) if v&(1<<25) else v)*4
def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for x in prior['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    p=STAGE/'run-native-slot-publication-20261027/slot-publication-results.json';j=json.loads(p.read_text())
    mp=STAGE/'run-native-slot-map-20261027/slot-map-results.json';m=json.loads(mp.read_text())
    assert j['status']=='PASS_NATIVE_SLOT_STATUS_PUBLICATION_PRECEDES_THIS_RECSTART_QUEUE_NOT_ENCODER_COMPLETION'
    assert m['status']=='PASS_NATIVE_GETSLOTID_CAN_REGISTER_MAPPING_NOT_READ_ONLY'
    for x,source,out in ((j,'slot_publication.py',p.parent),(m,'slot_map.py',mp.parent)):
        assert x['source_sha256']==digest(STAGE/source) and (out/'executed-source.py').read_bytes()==(STAGE/source).read_bytes()
        assert not x['camera_Windows_UU_operations']
    assert m['publication_result_sha256']==digest(p)
    assert len(j['cases'])==8 and j['bounded_phases']==52 and len(m['cases'])==m['bounded_phases']==10
    assert not any(j[k] for k in ('goal_complete','persistent_write_release','actual_MAIN_recording_current_state_or_recovery_proven'))
    events=[e for c in j['cases']+m['cases'] for e in c['events']];assert len(events)==62
    for e in events:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0xc8c70,0xdc09c,0x82530,0x7f060,0x81e90,0x7fbd0,0x7b9b0,0x7fa50}
    for e in events:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['cases']:
        assert all(c[k] for k in ('selection_source_is_explicit_fixture_not_real_media_or_feasibility',
            'post_log_post_selection_and_post_lock_are_independent_frames','Open_Start_queue_or_hardware_not_executed',
            'no_actual_notification_or_complete_GetStartSlotId_return'))
        assert not c['actual_idle_epoch_or_encoder_running_proven']
        old=bytes.fromhex(c['native_status_before']);new=bytes.fromhex(c['native_status_after']);assert len(old)==len(new)==136
        assert all(int(x,16) in (0xc,0x1c,0x2c,0x3c) for x in c['actual_changed_status_offsets'])
        bindings=[x['original_symbol_binding'] for e in c['events'] for x in e['original_imports_and_returns'] if 'original_symbol_binding' in x]
        assert all(name in bindings for name,target in t.BINDINGS.values())
    for c in m['cases']:
        assert c['native_registration_write']==(c['label'] in ('first_registration','last_free_registration'))
        assert c['map_bytes_outside_ID_field_unchanged'] and not c['actual_media_table_or_card_identity_proven']
        assert (c['before_sha256']!=c['after_sha256'])==c['native_registration_write']
    assert bl(0xdc690)==0x7d510 and bl(0xdc7f8)==0x7fbd0 and bl(0xdc82c)==0x7b9b0
    assert t.MPR.plt[bl(0xdc690)]=='_ZN3mpr14GetStartSlotIdEPNS_12MovieRecInfoE'
    assert t.MPR.plt[bl(0xdc7f8)]=='_ZN3mpr18EnqueueExecEncOpenERNS_12MovieRecInfoE'
    assert t.MPR.plt[bl(0xdc82c)]=='_ZN3mpr19EnqueueExecEncStartERNS_12MovieRecInfoEhRNS_15RecSequenceInfoE'
    assert t.MPR.symbols['_ZN3mpr8msidconv9GetSlotIDEj']['va']==0x9a95c
    oldg=json.loads(before)
    for x in oldg['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT));mr=str(mp.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text())
    contract['schema']='fx3-offline-status-diagnostic-candidate/2';contract['refined_in_stage']=STAGE.name
    contract['exclude_from_read_only_diagnostic'].append('mpr::msidconv::GetSlotID (may register new media mapping)')
    contract['slot_state_evidence']={'first_byte_offset':'0x0c','stride_bytes':16,'count':4,
        'producer':'GetStartSlotId accepted slot/boolean records, before this RecStart queue calls',
        'not_encoder_Open_Start_completion_or_actual_idle':True,'all_input_indices_in_this_run_declared_0_to_3':True}
    contract['media_ID_to_slot_policy']='Do not call GetSlotID for supposedly read-only resolution. Preserve raw IDs; require separately proven existing association and bounds; reject unknown/full/sentinel indices.'
    contract['GetSlotID_body']={'entry_ELF':'0x9a95c','record_count':4,'record_stride':'0x80','ID_offset':'0x7c',
        'new_ID_can_write_first_free_slot':True,'full_no_match_return_u32':0xffffffff,'actual_current_table_not_observed':True}
    contract['next_runtime_acceptance_requirements'].extend(['distinguish selected slot byte from hardware completion for same recording instance',
        'verify existing media-to-slot mapping without introducing converter registration side effects'])
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xdc168,0xdc194),(0xdc194,0xdc208),(0xdc274,0xdc2e8),(0xdc428,0xdc504),
        (0xdc678,0xdc6a0),(0xdc7e8,0xdc850),(0x9a95c,0x9a9c0),
        (0xd9cc0,0xd9ce0),(0xd9f64,0xd9fb8),(0x12a80c,0x12a8cc))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.front.LIBC.path),'listings':listings,'explicit_original_function_bindings':t.BINDINGS,
        'slot_publication_loop':'dc47c..dc4c4 writes byte at status0c+slot*16, using original getter copy and setter',
        'RecStart_call_order_static':[{'site':'0xdc690','call':'GetStartSlotId'},{'site':'0xdc7f8','call':'conditional EnqueueExecEncOpen'},
            {'site':'0xdc82c','call':'EnqueueExecEncStart'},{'site':'0xdc840','call':'EnqueueExecEventMovieRecStarted'}],
        'Open_may_be_reused_and_no_hardware_completion_claim':True,
        'writer_stop_static_only':'x23=FP+fe0 atd9ccc; d9f9c clearsFP+fec+slot*16 in selected ProcessWriterEvtStopCmp branches; actual stop/lifetime not executed.',
        'GetSlotID_is_lookup_or_registration_not_pure_reader':True,
        'unexecuted_dependencies':['real media-ID conversion and feasibility selection','vector reallocation and complete GetStartSlotId',
            'all pthread/log/event bodies','this RecStart queue calls and actual Open/Start/completion','actual writer stop and all consumer lifetime'],
        'all_slot_indices_in_loop_fixture_0_to_3_full_caller_validation_unproven':True,
        'prior52_phase_results_reused_not_rerun_for10_map_phases':True,'bounded_phases':62,
        'original_FX3_file_or_frontend_backend_modified':False,'actual_MAIN_recording_or_recovery_proven':False})
    review={'status':'PASS_NATIVE_SLOT_PUBLICATION_AND_LOOKUP_REGISTRATION_SIDE_EFFECT_SCOPE',
        'created_utc':now,'previous_manifest_members_verified':len(prior['files']),'publication_cases':8,'map_cases':10,'bounded_phases':62,
        'formal_sources_match_executed_copies':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(oldg);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_slot_selection_status_publication_and_media_lookup_registration_side_effect'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段119十一件封存/canonical核验；18例62原片段，52片段结果复用不重复运行。',
            '原GetStartSlotId调用者loop接原ForUpdate复制/SetStatus，定位状态0c+slot*16来源为接受的槽位布尔记录；真实选择/锁/通知未验。',
            '本次RecStart先调用GetStartSlotId再排队Open/Start；状态字节不能充硬件启动/完成，writer停止仅静态范围。',
            '原GetSlotID可登记新映射，表满返回ffffffff；诊断约束排除此副作用并区分介质ID和槽位，真实映射仍缺。',
            '目标16项状态和权限不变，原固件/117前端/75后端保持，实录与恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage120_slot_publication']={'readme':rel+'/README.md','result':rr,'map_result':mr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'62 bounded phases show selected-slot byte origins and GetSlotID registration side effect; static queue order is not actual encoder completion or current media/epoch proof.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11'):
            req['evidence'].extend([rr,mr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage120_scope']='槽位状态字节源及原getter/setter调用者62阶段；GetSlotID可写登记，不能充只读。选择/排队不充真实启动/代次，实机/恢复仍缺，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Selected slot/boolean records write status0c+slot*16 before this RecStart Open/Start queue calls. GetSlotID can register a new ID rather than only read. Neither byte nor lookup establishes actual encoder completion, current media identity or config epoch.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段120后沿同一录制实例的Open/Start实际消费者与完成事件、writer停止和状态写者同步核对真实运行门控；原槽位字节只是选择结果，GetSlotID可能登记，不能做只读解析。继续绑定完整参数/介质现有映射和配置关联；仅Mac，16项验收与恢复要求不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==oldg[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in oldg['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 槽位选择与状态来源](<'+rel+'/README.md>)：18例62片段确认状态字节早于本次编码排队、GetSlotID可登记映射；诊断排除副作用，真实编码/空闲及恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage120-native-slot-publication/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':62,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
