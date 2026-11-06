#!/usr/bin/env python3
"""Seal record-result and write-finish ordering without a quiescence claim."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import record_finish as t
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
    out=STAGE/'run-native-record-finish-20261027';p=out/'record-finish-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_RECORD_RESULT_AND_WRITE_FINISH_SCOPE_NOT_GLOBAL_QUIESCENCE'
    assert j['source_sha256']==digest(STAGE/'record_finish.py') and (out/'executed-source.py').read_bytes()==(STAGE/'record_finish.py').read_bytes()
    groups=('aggregate_cases','error_cases','notifier_cases');assert [len(j[k]) for k in groups]==[10,8,4]
    ev=[e for k in groups for c in j[k] for e in c['events']];assert len(ev)==j['bounded_phases']==86
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_MAIN_hardware_quiescence_free_restore_or_rescue_proven'):assert not j[k]
    for e in ev:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0x7dfa0,0x80ef0,0x7d630,0xfbe5c,0xc8c70,0xfc244,0xd714c,0x81e90}
    for e in ev:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    for c in j['aggregate_cases']:
        assert c['native_first_nonzero']==next((x for x in c['declared_results'] if x),0)
        assert c['zero_result_not_all_callbacks_finished_proof'] and not c['actual_locks_current_records_and_lifecycle_proven']
    for c in j['error_cases']:
        expect=c['declared_error']!=0 and c['declared_active'] and c['declared_callback']
        assert ('before_unexecuted_call' in c['outcome'])==bool(expect)
        assert c['active_flag_not_cleared_by_this_slice'] and not c['actual_callback_execution_locks_completion_or_current_instance_proven']
    for c in j['notifier_cases']:
        assert c['native_aggregate']==next((x for x in c['declared_results'] if x),0)
        assert all(c[k] for k in ('all_free_thread_log_signal_event_and_upstream_finish_gate_unexecuted',
            'event_has_type_and_result_not_record_snapshot_or_config_epoch','no_claim_real_records_released_or_all_async_users_finished'))
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/5';contract['refined_in_stage']=STAGE.name
    contract['record_result_and_finish']={'aggregate_ELF':'0xfc3a0','aggregate_scope':'first nonzero of four result words at record+8; no active/callback tests in executed scan',
        'aggregate_zero_is_not_global_quiescence':True,'single_error_handler_ELF':'0xfc168',
        'callback_pointer_cleared_before_unlock_and_actual_call':True,'zero_callback_pointer_is_not_callback_return_proof':True,
        'notifier_symbol':'mpr::NotifyAllMovieWriteFinishedParam','notifier_ELF':'0xcb508',
        'record_free_call_precedes_event_preparation':True,'event_type':0x100a,'event_payload_bytes':8,
        'event_payload_scope':'type and aggregate result only; not record snapshot or config epoch',
        'capture_record_information_before_free_with_verified_allocation_lease':True,
        'source_MovieRecInfo_pointer_clear_or_queued_Close_does_not_prove_release_completion':True,
        'actual_upstream_gate_full_Close_all_async_callbacks_and_recovery_proven':False}
    contract['next_runtime_acceptance_requirements'].append('observe in-flight callback entry/return and capture owned instance data before actual record free; do not gate on aggregate0, callback-pointer0 or event100a alone')
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xfc168,0xfc29c),(0xfc3a0,0xfc43c),(0xcb508,0xcb5c0),(0xfbff8,0xfc074),
        (0xd9600,0xd9684),(0xd988c,0xd98d0))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.prev.prev.prev.front.LIBC.path),'listings':listings,
        'initializer_bytes_reused_from_sealed_stage122_without_rerunning_initializer':True,
        'callback_clear_before_call':'fc290 clears record+10; fc244 is later BLR after unlock; actual callback never executed.',
        'all_write_notifier_order':'aggregate atcb564, record release atcb570, event preparation atcb574..cb580; free and SetIssueEvent bodies not executed.',
        'upstream_static_only':'FileQueueStreamWriteCmp related branch queues EncClose, then AllMovieWriteFinished, then clears MovieRecInfo+a48; complete gate/lifetime not executed.',
        'no_claim_real_pending_callbacks_exist_or_Sony_premature_free_bug':True,
        'all_actual_thread_services_callbacks_event_and_free_unexecuted':True,'bounded_phases':86,
        'original_FX3_file_or_frontend_backend_modified':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':22,'bounded_phases':86,'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_record_result_callback_clear_and_write_finish_release_event_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段122十件封存/canonical核验；22例86原片段，无设备/Windows操作。',
            '原结果汇总只读四条+8结果，活动/回调不参与；汇总0不充全退出，非活动错误仍参与。',
            '单记录非零错误保存并清回调指针后才准备调用；指针0不充回调返回，真实callback/锁未执行。',
            'AllMovieWriteFinished原通知先汇总/记录释放路径，再准备100a事件8字节；实际free/上游gate/Close/事件未验，不能事后追读旧pointer。',
            '原固件/旧前后端、16项状态及权限保持，真实主录/同机恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage123_record_finish']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'86 bounded phases show result-only aggregation, callback clear before unexecuted call, and release-before-event order. None proves global quiescence, actual free, hardware or recovery.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G08','G10','G11','G15'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage123_scope']='结果汇总/回调清除/写入完成通知86阶段；汇总0、callback-pointer0和100a事件均非全退出证据，实际free/Close/上游gate未验，不能放行回收/恢复；状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Result aggregation ignores active/callback state; callback pointer is cleared before the indirect call; write-finish notifier traverses record-free wrapper before preparing type/result event100a. Actual upstream completion, callback return and free remain unexecuted, so no quiescence or safe reclamation claim.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段123后核对完整Close/AllMovieWriteFinished上游条件、同一实例的正常Start回复/异步错误和回调返回，实际数据须在free前形成有租期的独立快照。聚合0、callback-pointer0、事件100a/源pointer清空均不充全退出。仅Mac，16项实录与同机恢复/独立救援不降级。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 回调结果与写入完成顺序](<'+rel+'/README.md>)：22例86片段核对结果汇总、回调清除及记录释放/事件先后；零值或完成事件不充全退出，实际主录和恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage123-record-result-finish/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':86,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
