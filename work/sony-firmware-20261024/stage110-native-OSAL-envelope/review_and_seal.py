#!/usr/bin/env python3
"""Seal original framing/reply evidence; leave transport and device gates open."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import osal_envelope as t
BASE,ROOT=t.BASE,t.ROOT


def sha(data):return hashlib.sha256(data).hexdigest()


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while data:=f.read(8*1024*1024):h.update(data)
    return h.hexdigest()


def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA
    prior=json.loads(t.PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    receipt=json.loads((STAGE/'extraction-receipt.json').read_text())
    for path,expected in ((receipt['source_image'],receipt['source_sha256']),(receipt['reader'],receipt['reader_sha256']),(receipt['output'],receipt['output_sha256'])):
        p=ROOT/path;assert p.is_file() and not p.is_symlink() and digest(p)==expected
    assert receipt['read_only_regular_file_extraction'] and not receipt['mount_or_native_host_execution']
    run=STAGE/'run-native-callback-boundary-20261027';j=json.loads((run/'osal-envelope-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'osal_envelope.py').read_bytes()
    assert digest(ROOT/j['source'])==j['source_sha256'] and digest(t.OSAL.path)==j['original_user_OSAL_sha256']==t.OSAL_SHA
    assert (len(j['receive_cases']),len(j['sender_expectation_cases']),len(j['reply_cases']),j['bounded_phases'])==(12,4,12,74)
    assert not j['actual_receive_free_mutex_condition_or_success_return_adapters_executed']
    assert not j['Windows_UU_camera_operations'] and not j['goal_complete'] and not j['persistent_write_release']
    for c in j['receive_cases']:
        assert c['envelope_unchanged_by_receive_metadata_and_copy']
        assert c['GetMsg_is_independent_from_unexecuted_OSAL_free_and_unwind']
        assert not c['actual_transport_envelope_allocation_free_full_ReceiveASync_or_MAIN_proven']
        assert c['native_copy_length']==min(c['declared_OSAL_payload_length'],384)
        if c['label']=='synthetic_marker_nonpublic_state1':assert c['native_message_state']==1 and c['GetMsg'] is None
        else:assert c['native_message_state']==2 and c['native_stored_length_u16_when_raw']==c['native_copy_length']
        if c['GetMsg']:
            q=c['GetMsg'];assert q['native_return']==0 and q['copied_len']==c['declared_OSAL_payload_length']
            assert q['all48_bytes_present']==(c['label']=='original_header48')
            assert q['native_object_state_length_source_and_stored_inline_bytes_cleared']
        calls=[call.get('original_user_OSAL_binding') for e in c['events'] for call in e['original_calls_and_returns'] if 'original_user_OSAL_binding' in call]
        assert calls==['osal_get_msg_src','osal_msg_size']
    assert sum(bool(c['GetMsg'] and c['GetMsg']['all48_bytes_present']) for c in j['receive_cases'])==4
    for c in j['sender_expectation_cases']:
        assert c['native_expected_factor']==(0x1001 if c['declared_caller_reply_pointer_provided'] else 1)
        assert not c['actual_expectation_store_send_wait_or_current_call_mode_proven']
    wanted=['expected_reply_copy','expected_reply_copy','record_movie_callback_unbound',
        'record_movie_callback_unbound','ignore_unrecognized_then_free','async_event_queue']*2
    assert [c['native_route'] for c in j['reply_cases']]==wanted
    for c in j['reply_cases']:
        if c['native_route']=='expected_reply_copy':assert c['copied_reply48_hex']==c['declared_packet48_hex']
        else:assert c['copied_reply48_hex'] is None
        assert not c['actual_reply_generation_transport_mutex_state_clear_signal_or_payload_release_proven']
        assert c['declared_expected']['explicit_global_input_not_actual_SetExpectedCodecEvent_execution']
    all_cases=j['receive_cases']+j['sender_expectation_cases']+j['reply_cases'];events=[e for c in all_cases for e in c['events']]
    assert len(events)==74
    forbidden={0x30850,0x30e80,0x7c5f0,0x83370,0x80460,0x81d30,0x2859e8}
    for e in events:
        assert e['whole_stack_outside_declared_512_bytes_unchanged'] and e['whole_scratch_outside_declared_outputs_unchanged']
        assert e['whole_original_relocated_images_unchanged'] and not e['output_return_logging_or_vcall_adapters']
        if e['reason']=='returned':assert e['callee_saved_X19_X29_D8_D15_preserved_on_complete_return']
        assert not any(int(pc,16) in forbidden for pc in e['pcs'][:-1])
    failed=STAGE/'run-native-envelope-and-replies-20261027'
    assert not json.loads((failed/'attempt-failure.json').read_text())['passing_result']
    assert not (failed/'osal-envelope-results.json').exists()
    assert (failed/'executed-source.py').read_bytes()!=(STAGE/'osal_envelope.py').read_bytes()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def listing(n,a,z):return {'library':n.path.name,'VA_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(n.read(a,z-a)),
        'original_disassembly':n.dump(a,z) if hasattr(n,'dump') else n.disasm(a,z)}
    global_slots=j['reply_cases'][0]['declared_expected']
    globals_named={key:[name for name,s in t.MPR.symbols.items() if s['va']==int(global_slots[key],16)]
        for key in ('factor_slot','payload_pointer_slot')}
    source_notes={'checked_date':'2026-10-27',
        'source':{'url':'https://man7.org/linux/man-pages/man3/pthread_cond_wait.3.html',
            'observation':'The Linux man-pages project describes condition waiting as releasing the mutex while blocked and acquiring it again before returning.',
            'scope':'Generic API semantics only, not Sony scheduler, active pthread state, actual wakeups or verified payload lifetime.'},
        'official_POSIX_fetch_attempts':[{'url':'https://pubs.opengroup.org/onlinepubs/9799919799/functions/pthread_cond_wait.html','result':'HTTP403'},
            {'url':'https://pubs.opengroup.org/onlinepubs/9699919799/functions/pthread_cond_wait.html','result':'HTTP403'}],
        'no_runtime_threading_device_or_recovery_operations':True}
    put(STAGE/'public-source-notes.json',source_notes)
    audit={'created_utc':now,'extraction':'extraction-receipt.json','original_user_OSAL_sha256':t.OSAL_SHA,
        'original_Dataflow_sha256':sha(t.DF.blob),'original_MPR_sha256':sha(t.MPR.blob),
        'metadata_layout':{'pointer':'Declared user OSAL data pointer P','source_u32':'P-0xc','payload_length_u32':'P-8',
            'pure_original_setter':'0x7e20','pure_original_getter':'0x7e28','pure_original_size':'0x7e08',
            'all_other_envelope_allocator_refcounts_links_and_ownership_are_unproven':True},
        'original_sender_constants':{'source':'0x80c70047','queue':'0x8055001f',
            'source_setup':'0x27e194..0x27e1a0','send_arguments':'0x27e1a4..0x27e1b0'},
        'receive':{'entry':'0x33964','unexecuted_OSAL_receive':'0x30850',
            'independent_entry_with_declared_error0_and_stack_envelope_pointer':'0x3399c',
            'native_source_get_PLT':'0x30880','native_size_PLT':'0x30630','copy_cap':384,
            'unexecuted_OSAL_free':'0x30e80','SetGlobalMsg_not_called':True,
            'generic_marker':'0xa0a0a0a0','special_source_raw_priority':['0x00c00695','0x0061003c','0x80c2019f','0x00c20219','0x01590438'],
            'GetMsg_after_unexecuted_free_is_another_independent_experiment':True},
        'sender_expectation':{'original_GetExpEvt':'0x27df44','provided_pointer_210_sub0':4097,
            'null_pointer_branch_factor':1,'null_branch_storage':'SendMsg FP+50',
            'all_SetExpected_stores_OSAL_send_wait_and_actual_call_mode_unexecuted':True},
        'reply':{'original_callback':'0x28593c','original_converter':'0x27f494',
            'explicit_global_slots_and_symbol_names':globals_named,'declared_global_inputs':global_slots,
            'declared_packet_4e0_sub1_factor':4097,'declared_packet_4e0_sub2_factor':1,
            'matching_excludes_reserved_expected2':True,'match_copy_after_independent_lock_gap':'0x285998..0x2859bc',
            'subsequent_state_clear_and_signal_are_unexecuted':True,
            'unmatched_specific_event_routing_also_depends_on_format1c':'format44 queue; tested other format unbound record-movie callback',
            'unbound_callback_stop':'0x2859e8','unknown_reply_conversion2_goes_to_unexecuted_free':True,
            'reply_templates_not_actual_generated_AV_traffic':True},
        'wait_lifetime_scope':'Original SendMsg calls pthread_cond_wait, not timedwait, after OSAL send; generic wait releases mutex while waiting. Whole outer serialization, watchdog/cancel, actual thread state, response generation and raw98 lifetime are unproved; not a camera race or deadlock allegation.',
        'prior_scope_refinement':'stage108 independently executed SetGlobalMsg. Original ReceiveASync here populates inline metadata directly; it does not call that setter. Both old and new are bounded experiments, not transport proof.',
        'failure_refinement':'Initial harness missed record-movie BLR boundary and assumed all mismatches reached queue. Declared zero callback led to PC0 termination with no passing result. Formal run stops before BLR and distinguishes format44 route; no callback fixup or success adapter.',
        'original_listings':[listing(t.OSAL,t.OSAL.symbols[n]['va'],t.OSAL.symbols[n]['va']+t.OSAL.symbols[n]['size'])
            for n in ('osal_set_msg_src','osal_get_msg_src','osal_msg_size')]+
            [listing(t.DF,a,z) for a,z in ((0x31358,0x31368),(0x33920,0x33bec),(0x32070,0x32194))]+
            [listing(t.MPR,a,z) for a,z in ((0x27ddac,0x27ddc8),(0x27de88,0x27deac),(0x27df44,0x27e244),
                (0x27f494,0x27fa34),(0x28593c,0x285acc))],
        'actual_MAIN16M_hardware_backup_restore_or_independent_rescue_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'receive_cases':12,'sender_expectation_cases':4,'declared_reply_cases':12,'bounded_phases':74,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'failed_attempt_retained_without_passing_result':True,'Windows_UU_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));rr=str((run/'osal-envelope-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_user_OSAL_metadata_ReceiveASync_classification_and_expected_reply_routes'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段109的15件封存、canonical与目标卷核对，原用户态OSAL从既有校验镜像只读提取，未重复或运行内核驱动。',
            '原用户OSAL源字段P-c/长度P-8真实指令与原Dataflow接收后翻译、复制、分类接通；未调用SetGlobalMsg。48B/16B/400->384及标记/特殊来源对照。',
            '原发送期待分支与ConvertAvconEvent/GetExpectedCodecEvent/CallbackFromAvbbc核对：匹配才复制48B同步回复；不匹配还有格式相关回调/队列，未知事件走释放边界。',
            '接收/释放/互斥锁/期待写入/条件信号均停止，后段独立输入；初始缺回调停止点失败保留并更正，正式74阶段。',
            '核对通用cond_wait释放/重取锁语义，不能据发送锁宣称固定raw98贯穿等待受保护；实际外层串行化、回复生成及寿命仍缺。',
            'MAIN自然来源、FH/16M资源、硬件成片/音画/长录、同机备份恢复和独立救援门槛保持，16状态和权限不变。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage110_user_OSAL_envelope_and_reply']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'74 bounded phases: original user OSAL metadata, independent post-receive Dataflow copy/classification, original expectation and reply comparison/copy. No live receive/free/mutex/signal or actual generated reply/raw98 lifetime proof.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json'])
            req['stage110_scope']='原OSAL元数据/接收后路径及期待事件和回复路由74阶段；独立声明封装/错误/全局状态/回复，不证明实际消息/锁/实例/固定区寿命或硬件接受。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original ReceiveASync directly reads user OSAL metadata and copies/classifies inline messages, without SetGlobalMsg. Correct matched replies differ from other event routes. Pure original OSAL candidates and native code execute under explicit envelope/global/packet inputs; actual transport, state mutation, signals, serialization and raw98 lifetime remain unproved.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段110后追原匹配回复的实际AV生成、Codec::EncOpen调用者的回复指针/期待/编码实例及外层串行化；结合原AddParam填充与回读形成事务身份、长度/类型/代次及raw98有效期检查，不能用消息释放或条件信号代替编码确认。保持MAIN自然来源和FH/16M资源缺口，仅Mac，实机成片/音画/长录及同机恢复/独立救援不变。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原OSAL封装与回复匹配](<'+rel+'/README.md>)：原接收分类、长度边界与同步/其他回复路由74阶段；真实传输、锁、固定参数寿命与实机验收仍缺，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage110-user-OSAL-envelope/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':74,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
