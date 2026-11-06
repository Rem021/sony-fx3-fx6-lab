#!/usr/bin/env python3
"""Seal caller/reply identity evidence and preserve every real-device gate."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE));import open_reply as t
BASE,ROOT=t.BASE,t.ROOT
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()

def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-native-constructor-boundaries-20261027';j=json.loads((run/'open-reply-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'open_reply.py').read_bytes()
    assert (len(j['callers']),len(j['produced']),len(j['classified']),j['bounded_phases'])==(2,12,12,72)
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    assert not j['normal_MC_backend_child_input_and44_wire_to48_storage_lifetime_proven']
    assert not j['actual_logger_getter_mutex_allocator_OSAL_send_or_success_return_adapters_executed']
    for c in j['callers']:
        a=[int(x,16) for x in c['original_single_stream_arguments']]
        assert a==[t.SP-0x1c0+0x90,0x20,15,1,0,t.SP-0x1c0+0x60]
        assert c['reply_storage48_zeroed_by_native_code'] and not c['logs_locks_DMM_builders_Codec_EncOpen_or_actual_call_proven']
        assert len(c['events'])==4
    for c,q in zip(j['produced'],j['classified']):
        wire=bytes.fromhex(c['wire44_hex']);assert len(wire)==44
        assert c['Dataflow_raw_state']==2 and c['Dataflow_length']==c['native_allocation_request_length']==44
        assert c['Dataflow_source_ID']==hex(t.MANAGER_ID) and c['destination_ID']==hex(t.SOURCE)
        assert c['wire_MID']==q['MID']==0x4e0 and c['wire_subcode']==q['subcode']==(0 if c['producer']=='Ack' else 1)
        assert q['original_factor']==(1 if c['producer']=='Ack' else 0x1001)
        assert q['wire44_sha256']==sha(wire) and q['opaque_status']==c['wire_opaque_status']
        assert q['no44_to48_copy_or_real_callback_transport_claim']
        assert struct.unpack_from('<I',wire,0x14)[0]==c['wire_opaque_status']
        if c['producer']=='ExecErrorCommand':
            assert c['wire_opaque_status']==c['declared_status_input'] and len(c['events'])==3
            assert c['status_input_not_real_getter_return_or_hardware_result']
            assert not c['actual_status_getter_logs_allocation_or_send_executed']
        else:
            assert len(c['events'])==5 and c['post_log_key_phase_is_independent_input_not_lookup_success']
            assert not c['actual_normal_child_input_hardware_event_log_allocation_or_send_proven']
            assert c['wire_opaque_status']==struct.unpack_from('<I',bytes.fromhex(c['template44_hex']),0x14)[0]
        for e in c['events']:
            assert e['whole_stack_outside_declared2048_bytes_unchanged'] and e['whole_scratch_outside_outputs_unchanged']
            assert e['whole_original_relocated_images_unchanged'] and not e['success_output_return_or_logger_adapters']
    events=[e for c in j['callers']+j['produced']+j['classified'] for e in c['events']];assert len(events)==72
    forbidden={0xc8c70,0x7c5f0,0x7d8b0,0x7c350,0xb2da8,0x9f280,0x9bf10,0x9e870,0x9e710,0x9c980,t.DBASE+0x308a0}
    for e in events:
        assert not any(int(pc,16) in forbidden for pc in e['pcs'][:-1])
    fail=STAGE/'run-native-producers-20261027'
    assert not json.loads((fail/'attempt-failure.json').read_text())['passing_result']
    assert not (fail/'open-reply-results.json').exists()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def listing(n,a,z):return {'library':n.path.name,'VA_range':[hex(a),hex(z)],'bytes_sha256':sha(n.read(a,z-a)),
        'original_disassembly':n.dump(a,z) if hasattr(n,'dump') else n.disasm(a,z)}
    audit={'created_utc':now,'original_hashes':{'AV':sha(t.AV.blob),'DF':sha(t.DF.blob),'MPR':sha(t.MPR.blob),'libc':sha(t.LIBC.blob)},
        'single_stream_caller':{'function':'mpr::ExecEncOpen','entry':'0xd18d8','argument_block':'0xd1ba4..0xd1bbc',
            'original_reply_pointer':'FP+60 nonnull','native_zeroed_reply_storage_bytes':48,
            'FileFormat15_is_declared_exec_field_not_new_natural_MAIN_source':True,
            'normal_unlock_before_Open_preparation':'0xd1b74','full_outer_serialization_unproved':True,
            'whole_logs_locks_DMM_builders_Open_call_and_live_context_unexecuted':True},
        'reply_producer':{'error_getter_stop':'0xb2da8','independent_status_inputs':[0,2],
            'original_error_reply_fields':{'MID':'0x4e0','subcode':1,'status_offset':'0x14','CodecType_offset':'0x18'},
            'source_setter_and_qid_conversion_are_original_but_ManagerID_and_destination_graph_declared':True,
            'producer_and_Dataflow_and_allocation_request_lengths':44,'Dataflow_raw_state':2,
            'native_Dataflow_SetGlobalMsg_executed':True,'OSAL_allocation_and_send_unexecuted':True},
        'child_constructor':{'original_parent_Ack_args':'0xb2c4c..0xb2c68','expected_response_subcode':'0x8502',
            'outgoing_Ack_subcode':0,'outgoing_Ack_enable':1,'Comp_args':'0xb2c70..0xb2c80',
            'log_key_lookup_is_stop_and_post_lookup_key0_is_independent_input':True},
        'child_templates':'Original ErrorCommand44 bytes wrapped in declared56-byte AV storage. Normal backend child input production not proven. Remaining4 ABI storage bytes are explicit old fill and never claimed to be sent.',
        'event_identity':{'Ack_4e0_sub0':1,'Comp_or_error_4e0_sub1':4097,
            'matching_event_does_not_inspect_status_and_is_not_hardware_success':True,
            'native_MPR_classifier_only_no_callback_44_to48_copy':True},
        'wire_storage_gap':'Reply builder requests44 through Manager/Dataflow/OSAL. MPR callback has48-byte copy. Allocation extent, receive conversion, tail semantics and owner lifetime still unproved; no out-of-bounds or valid-padding verdict.',
        'independent_gaps':['MPR diagnostics and normal lock/unlock','status100b getter','constructor object allocation',
            'log-key container lookup','mandatory AV Log0/Log1','OSAL allocation/send'],
        'failed_attempt':'Original constructor reached unbound std::_Rb_tree::find through logging-key lookup. No passing result. Formal run stops before log-key lookup and declares later input separately; no fake lookup implementation or return.',
        'original_listings':[listing(t.MPR,a,z) for a,z in ((0xd18d8,0xd1954),(0xd1b5c,0xd1bc4),(0xd1c18,0xd1c84),
            (0x27e168,0x27e224),(0x28593c,0x285a08))]+
            [listing(t.AV,a,z) for a,z in ((0xb2c44,0xb2c80),(0xb2d40,0xb2de0),(0xb1dfc,0xb20fc),
            (0x127890,0x1278d4),(0x13846c,0x138548),(0x1389cc,0x138a28),(0x138ad8,0x138b78))]+
            [listing(t.DF,a,z) for a,z in ((0x31f7c,0x31ff4),(0x33e14,0x33f70))],
        'real_MAIN16M_hardware_backup_restore_and_independent_rescue_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    layout={'schema':'fx3-offline-internal-message-observations/1','status':'SPEC_ONLY_UNDEPLOYABLE',
        'source_stage':STAGE.name,'not_USB_protocol_or_permission_to_query_camera':True,
        'forward_Open':{'observed_payload_bytes':48,'source':'stage107 original MPR allocation and header copy',
            'physical_u64_offset':8,'virtual_u64_offset':40,'runtime_pointer_validity_unproven':True},
        'tested_reply_producers':{'observed_payload_bytes':44,'producers':['ExecErrorCommand','Ack ExecCmd','Comp ExecCmd'],
            'fields_little_endian':{'subcode':{'offset':2,'bytes':2},'opaque_status':{'offset':20,'bytes':4},
                'CodecType':{'offset':24,'bytes':1},'MID':{'offset':36,'bytes':4}},
            'classifier_identity':{'MID4e0_sub0':1,'MID4e0_sub1':4097},
            'do_not_parse_virtual_u64_at40_from44_bytes':True,
            'other_reply_types_and_normal_MC_input_production_unproven':True},
        'Cxx_reply_copy':{'observed_copy_bytes':48,'source':'original MPR CallbackFromAvbbc',
            '44_wire_to48_storage_allocation_extent_tail_and_lifetime_not_verified':True},
        'acceptance_requires':['actual message role and declared length','valid owning storage extent before Cxx copy',
            'expected event and instance/generation','opaque status interpretation and content readback',
            'actual hardware Open/Start and target file','raw98 lifetime and external synchronization'],
        'device_IO_or_guest_prototype_changed':False,'goal_complete':False}
    put(STAGE/'diagnostic-layout-not-deployable.json',layout)
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'caller_cases':2,'producer_fragments':12,'native_classifier_cases':12,'bounded_phases':72,
        'formal_source_matches_executed_copy':True,'failed_attempt_preserved':True,
        'same_agent_review_not_independent_engine':True,'Windows_UU_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));rr=str((run/'open-reply-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name;g['research_activity']='Mac_only_native_Open_reply_producers44_byte_framing_single_stream_caller_and_event_identity'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段110的14件封存与canonical/目标卷核对；沿用原库，仅Mac，没有新增驱动或接口访问。',
            '原单流ExecEncOpen取FP+60非空回复区，原指令清零48B并传入Codec Open；原局部normalLock解锁先于Open准备，外层串行化未证。',
            '原ExecErrorCommand、Ack/Comp片段经Manager原Dataflow SetGlobalMsg到SendASync分配前，长度44贯穿；status0/2为独立输入，日志与发送未模拟成功。',
            '原Ack构造发送子码0、期待8502；原MPR分类Ack=1，Comp/错误子码1=1001。非零状态仍有相同期待身份，不能当硬件成功。',
            '阶段11048B人工回复不证明真实44B发送到48B C++复制范围；新增离线字段说明，实际分配/接收尾部/所有权仍缺。初次日志键容器依赖失败保留，正式72阶段。',
            '原MAIN来源、FH/16M、硬件成片/音画/长录和同机恢复/独立救援未验收，16项状态、权限及阶段75原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage111_Open_reply_producers']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','layout_spec':rel+'/diagnostic-layout-not-deployable.json',
        'review':rel+'/completed-evidence-review.json','scope':'72 native bounded phases resolve nonnull single-stream reply pointer,44-byte reply producers and1/1001 identity; no actual status getter, normal MC child input, logs, allocation/send,44-to48 owning extent, hardware or recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-layout-not-deployable.json'])
            req['stage111_scope']='原单流非空回复指针与44B回复片段/事件1和1001核对。状态非零仍可事件匹配；44发送与48存储/复制关系未证，独立后端输入及日志/锁/分配/发送不代表运行验收。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Refines stage110 declared null/non-null sender modes: original single-stream ExecEncOpen passes non-null FP+60. Original reply producers request44 bytes, while older48-byte reply experiments proved only their declared storage condition. Ack0 maps1, Comp/error1 maps1001 irrespective of tested nonzero status; real transaction identity and allocation extent remain unproved.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段111后追44B回复到MPR48B回调复制的原接收/分配范围及尾部语义，正常MC后端到Ack/Comp输入的生成、非零状态上层消费与单流工作队列外层串行化。按消息方向/角色验证长度和可读存储范围，不能把事件1或1001、null模式当硬件完成。保持自然MAIN来源/FH16M缺口与Mac-only权限；实机和同机恢复/独立救援要求不变。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 单流调用与44字节回复](<'+rel+'/README.md>)：原非空回复指针、Ack/完成事件身份与发送长度72阶段；44B发送到48B存储及实际硬件/恢复仍未验收，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage111-native-Open-reply/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':72,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
