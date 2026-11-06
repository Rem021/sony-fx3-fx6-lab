#!/usr/bin/env python3
"""Seal native Start evidence and thumbnail source correction."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import start_caller as t
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
    p=STAGE/'run-native-Start-caller-20261027/start-caller-results.json';j=json.loads(p.read_text())
    op=STAGE/'run-native-Start-owner-20261027/start-owner-results.json';o=json.loads(op.read_text())
    assert j['status']=='PASS_NATIVE_START_CALLER_RETURN_LAYERS_NOT_HARDWARE_COMPLETION'
    assert o['status']=='PASS_NATIVE_START_CALLBACK_RECORD_POINTER_HANDOFF_NOT_REAL_INSTANCE_BINDING'
    for data,name,path in ((j,'start_caller.py',p.parent),(o,'start_owner.py',op.parent)):
        assert data['source_sha256']==digest(STAGE/name) and (path/'executed-source.py').read_bytes()==(STAGE/name).read_bytes()
        assert not data['camera_Windows_UU_operations']
    assert o['prior_Start_results_sha256']==digest(p)
    assert [len(j[k]) for k in ('producer_cases','return_cases','classifier_cases')]==[4,8,6]
    assert j['bounded_phases']==94 and len(o['cases'])==4 and o['bounded_phases']==12
    assert not any(j[k] for k in ('goal_complete','persistent_write_release','actual_Start_hardware_profile_file_backup_or_recovery_proven'))
    events=[e for k in ('producer_cases','return_cases','classifier_cases') for c in j[k] for e in c['events']]+[e for c in o['cases'] for e in c['events']]
    assert len(events)==106
    for e in events:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0xc8c70,0x136468,0x81340,0x7e350,0x82b20,0x7d8b0,0x27dba8,0x80ef0,0x7dfa0,0xfc29c,0xd714c}
    for e in events:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['producer_cases']:
        assert len(bytes.fromhex(c['native_Start128']))==128 and len(bytes.fromhex(c['declared_exec56']))==56
        assert c['native_call_args']=={'CodecType':32,'FileFormat':15,'count':1,'ViewId':0,'reply_bytes':48,'reply_pointer_nonnull':True}
        assert c['original_GPS_metadata_logging_and_Codec_Start_unexecuted'] and c['no_actual_full_request_producer_or_Main_profile_epoch_hardware_acceptance']
        assert c['sequence_byte_at_Start5c'] in (7,255) # Legacy key; source correction below is authoritative.
    for c in j['return_cases']:
        assert c['native_post_wait_sender_bool']==int(c['declared_wait_return']==0)
        assert c['native_Codec_post_send_status']==(0 if c['declared_wait_return']==0 else 2)
        assert c['all_send_wait_unlock_logging_and_reply_arrival_are_unexecuted_gaps']
        assert c['not_a_complete_Send_or_EncStart_or_hardware_failure_success_demonstration']
    for c in j['classifier_cases']:
        assert c['native_factor']==(1 if c['kind']=='synthetic_sub2' else 0x1003)
        assert c['actual_Start_reply_producer_or_current_expected_event_unproven']
    for c in o['cases']:
        assert c['callback_record_count']==4 and c['callback_record_stride']==96 and c['callback_ELF_VA']=='0xd714c'
        assert not c['actual_owner_active_records_error_delivery_and_recording_instance_proven']
        assert c['all_thread_lock_unlock_logging_error_fanout_and_callback_bodies_unexecuted']
    relocs=[]
    for sec in t.MPR.elf.iter_sections():
        if sec['sh_type']=='SHT_RELA':
            sy=t.MPR.elf.get_section(sec['sh_link'])
            for x in sec.iter_relocations():
                if x['r_offset'] in (0x2fafd0,0x2fad98,0x2f9b50):
                    s=sy.get_symbol(x['r_info_sym']);assert x['r_info_type']==1025
                    relocs.append({'GOT':hex(x['r_offset']),'type':'R_AARCH64_GLOB_DAT','symbol':s.name,'ELF_VA':hex(s['st_value']),'bytes':s['st_size']})
    assert len(relocs)==3
    th=next(x for x in relocs if x['GOT']=='0x2fafd0');assert th['symbol']=='_ZN3mpr13s_thumbnailIdE' and th['bytes']==1 and th['ELF_VA']=='0x375505'
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT));orr=str(op.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/3';contract['refined_in_stage']=STAGE.name
    contract['Start_observation']={'single_stream_request':{'CodecType':32,'declared_FileFormat':15,'count':1,'ViewId':0},
        'reply_storage_bytes':48,'wire_valid_length_and_allocation_lease_not_proven':True,
        'expected_factor':0x1003,'synthetic_matching_reply':{'MID':0x4e0,'subcode':3,'factor':0x1003},
        'post_wait_bool_and_API_return_do_not_check_declared_reply_status14':True,
        'capture_fields_required':['native API return','actual wait/error state','expected event and raw reply event','reply status+14',
            'actual valid payload length and allocation/owned snapshot lifetime','real request/callback-record/recording-instance identity','later async error/completion and actual encoded file'],
        'Start5a_source':'request+1; static Enqueue source is ConvertWriterIdListForShotId',
        'Start5c_source':'request+2 from s_thumbnailId; thumbnail identifier, not config epoch',
        'callback_records':{'request_pointer_offset':'0x30','static_Enqueue_origin':'MovieRecInfo+0xa48','count':4,'stride':'0x60','callback_offset':'0x10',
            'on_declared_API_zero':'prepare NotifyMovieRecError pointers','on_declared_nonzero':'same pointer/error-code handoff before fanout',
            'actual_owner_lifetime_active_entries_and_instance_binding_proven':False}}
    contract['legacy_run_label_correction']={'field':'sequence_byte_at_Start5c','correct_meaning':'thumbnail_id_at_Start5c',
        'reason':'Original s_thumbnailId GOT relocation and byte handoff; raw executed source/result retained without rewriting.',
        'does_not_rename_other_independent_STOP_seq_id_fields':True}
    contract['next_runtime_acceptance_requirements'].extend(['normal Start reply producer and event/status content for same actual instance',
        'actual callback-record allocation/registration/reuse and execRecMovie serialization','do not use thumbnailId as configuration epoch or return0 as hardware success'])
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xca6e4,0xca81c),(0xca4a4,0xca5c4),(0x27e0cc,0x27e244),(0x27fd64,0x27fee8),
        (0x27df44,0x27e0cc),(0x27f494,0x27f558),(0xfc4c0,0xfc550),
        (0xdc81c,0xdc854),(0xd6828,0xd6834),(0xd68dc,0xd68f0),(0xd6938,0xd6954))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.prev.front.LIBC.path),'relevant_original_relocations':relocs,'listings':listings,
        'Start5c_thumbnail_provenance':'RecStart loads byte through s_thumbnailId GOT; Enqueue truncates its byte argument and stores request+2; builder loads request+2 to Start+5c.',
        'raw_executed_source_sequence_label_is_historical_not_epoch_semantics':True,
        'return_matrix_is_independent_post_gap_evidence_not_complete_error_or_success_transaction':True,
        'reply_arrival_and_backend_status_handling_unexecuted_no_Sony_bug_claim':True,
        'wire_valid_Start_reply_length_not_proven_by48_byte_caller_storage':True,
        'callback_record_pointer_source_static_only_and_actual_lifetime_unproven':True,
        'original94_phases_reused_for12_owner_phases_not_rerun':True,'bounded_phases':106,
        'original_FX3_file_or_frontend_backend_modified':False,'actual_MAIN_hardware_file_or_recovery_proven':False})
    review={'status':'PASS_NATIVE_START_CALLER_RETURN_AND_CALLBACK_RECORD_SCOPE','created_utc':now,
        'previous_manifest_members_verified':len(prior['files']),'producer_cases':4,'return_cases':8,'classifier_cases':6,'callback_record_cases':4,
        'bounded_phases':106,'same_agent_review_not_independent_engine':True,'formal_sources_match_executed_copies':True,
        'thumbnailId_source_correction_explicit_and_raw_test_labels_preserved':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_Start_caller_return_layers_and_error_callback_record_pointer_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段120十三件封存/canonical核验；22例106阶段，94原结果复用补12回调记录阶段。',
            '原Start清零128/构建器/原调用点，非空48回复区；Start期待1003，人工comp-sub3同类，真实回复生产/消费未验。',
            '独立post-wait/Send返回层不因声明回复status14区分结果，API返回0不足充硬件成功；未构造完整失败/成功事务或Sony缺陷结论。',
            '原API零分支向四条记录登记NotifyMovieRecError，非零传同指针/错误码至fanout前；真实owner/活跃/寿命未验。',
            '原GOT核准Start5c源为s_thumbnailId，修正本轮初始sequence测试标签，不能充配置代次。',
            '16项验收状态与权限保持；原固件/旧前后端保持，主录成片及备份恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage121_Start_caller_return']={'readme':rel+'/README.md','result':rr,'callback_record_result':orr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'106 bounded phases cover original Start caller/parameter builder, expected-event classification, independent post-wait return layers and callback-record pointer handoff. Real services, hardware, owner and config epoch remain unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11'):
            req['evidence'].extend([rr,orr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage121_scope']='Start调用者/128参数/事件1003/局部返回与四条错误回调记录106阶段；Start5c为thumbnailId而非代次，API返回0不充硬件成功。真实实例/服务/编码和恢复未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Single-stream Start has a nonnull48-byte reply store and expected event1003; independently declared post-wait bool/API returns do not establish status14 or hardware success. Request+30 associates four error-callback records but not a proven live owner. Original Start+5c source is thumbnailId, correcting this run legacy sequence label.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段121后追MovieRecInfo+a48四条回调记录的创建/登记/复用、execRecMovie工作队列和正常Start回复生产/消费；分别记录API码/事件/回复状态/异步错误及真实成片。Start5c的thumbnailId不充配置代次，声明pointer不充当前实例。仅Mac，16项主录及恢复验收不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 Start调用者与返回分层](<'+rel+'/README.md>)：22例106片段核对128字节参数、事件1003与错误回调记录；Start5c源为thumbnailId，局部API零返回不充硬件成功，主录恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage121-native-Start-caller/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':106,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
