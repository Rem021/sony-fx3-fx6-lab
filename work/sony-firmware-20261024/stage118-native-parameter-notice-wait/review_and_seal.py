#!/usr/bin/env python3
"""Review native notice/wait slices without claiming runtime synchronization."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import notice_wait as t
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
    assert digest(t.PRIOR)==t.PRIOR_SHA
    prior=json.loads(t.PRIOR.read_text())
    for x in prior['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-native-notice-and-ready-20261027-corrected';p=out/'notice-wait-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_LOAD_PARAMETER_NOTICE_WAIT_SCOPE_NOT_CODEC_OR_EPOCH_PROOF'
    assert j['source_sha256']==digest(STAGE/'notice_wait.py')
    assert (out/'executed-source.py').read_bytes()==(STAGE/'notice_wait.py').read_bytes()
    groups=('registration_cases','notice_cases','wait_cases','fulfill_cases','branch_cases','post_Set_cases')
    assert [len(j[k]) for k in groups]==[6,12,6,6,6,4]
    events=[e for k in groups for c in j[k] for e in c['events']]
    assert len(events)==j['bounded_phases']==84
    for k in ('goal_complete','persistent_write_release','Windows_UU_camera_operations','actual_async_transaction_config_epoch_or_MAIN_recording_recovery_proven'):assert not j[k]
    for e in events:
        assert all(e[k] for k in ('stack_outside_declared_b00_unchanged','scratch_outside_outputs_unchanged','whole_mapped_APP_and_libc_unchanged'))
        assert not e['actual_logs_runtime_state_or_success_return_adapters']
        assert e['reason']=='returned' or e['reason'].startswith('boundary: ')
    forbidden={0x1593ca0,0x1591d30,0x2e6c634,0x16ed554,0x273879c,0x2bccc28,0x15940a0,
        0x1594560,0x1593840,0x2bccee0,0x2bccdc8,0x15944f0,0x2bccfb4,0x2f6ff0c}
    for e in events:assert not forbidden.intersection(int(a,16) for a in e['pcs'][:-1])
    for c in j['registration_cases']:
        assert not c['actual_new_delete_registry_publish_serialization_or_epoch_proven']
        assert ('existing_node' in c['outcome'])==(c['existing_key']==0x1004)
    for c in j['notice_cases']:
        assert not c['complete_registry_erase_or_actual_fulfillment_encoder_configuration_identity_proven']
        assert c['notice_key']==0x1004 and c['opaque_word4_not_claimed_epoch'] in (0x1111,0x2222)
        assert ('registered_promise_moved' in c['result'])==c['matching_registry_key']
    for c in j['wait_cases']:
        assert not c['actual_thread_wait_wake_vcall_or_codec_Open_Start_proven']
        assert ('ready_returns' in c['outcome'])==(c['declared_ready_word']&0x7fffffff==1)
    for c in j['fulfill_cases']:assert not c['actual_TLS_call_once_provider_callback_notify_or_cleanup_proven']
    for c in j['branch_cases']:assert c['flag_not_proven_idle_or_recording_state']
    for c in j['post_Set_cases']:assert not c['actual_Set_conversion_return_or_original_app_completion_proven']
    first=STAGE/'run-native-notice-and-ready-20261027';failure=json.loads((first/'attempt-failure.json').read_text())
    assert failure['status']=='FAILED_NO_PASSING_RESULT' and 'unapproved execution 2e6f7e0' in failure['error']
    a=(first/'executed-source.py').read_text();b=(STAGE/'notice_wait.py').read_text()
    assert a.replace('(0x2e6f754,0x2e6f7e0)','(0x2e6f754,0x2e6f7e4)')==b
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    ranges=((0x2e6e478,0x2e6e5d8),(0x2e56ce4,0x2e56d38),(0x2e57a90,0x2e57b04),
        (0x2e6c7a0,0x2e6c824),(0x2e58088,0x2e580b0),(0x2e6f754,0x2e6f7ec),
        (0x2e6f9ac,0x2e6f9c4),(0x2e2a924,0x2e2a948),(0x2bcd208,0x2bcd224),
        (0x2bccc0c,0x2bccc98),(0x2bcce64,0x2bccee4),(0x2bccf34,0x2bccf74))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.APP.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.APP.md.disasm(t.APP.read(a,z-a),a)]} for a,z in ranges]
    assert t.APP.read(0x39912e0,100).split(b'\0')[0]==b'evtLoadMovieFinishedParamCallback'
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_APP_sha256':digest(t.APP.path),
        'original_libc_sha256':digest(t.prev.front.LIBC.path),'listings':listings,
        'observed_import_names':{hex(a):t.APP.plt.get(a) for a in (0x1593ca0,0x1591d30,0x1593840,0x15940a0,0x1594560,0x15941f0,0x1594030,0x15944f0)},
        'callback_name_address':'0x39912e0','observed_registry_key':'0x1004','global_registry':'0x968b120',
        'global_registry_fixture':'Artificial declared input placed before execution in original PF_W data segment; affected image baseline refreshed only for that declared input.',
        'not_real_thread_lock_allocate_insert_TLS_call_once_virtual_dispatch_or_Set':'All such bodies stopped before entering; post-gap frames are independent declared inputs.',
        'opaque_notice_plus4_is_not_claimed_epoch':True,'registry_erase_serialization_and_complete_lifecycle_unproven':True,
        'future_ready_not_codec_Open_Start_or_actual_recording_idle_proof':True,
        'failure_correction':'Only one original BL instruction at2e6f7e0 added to allowed range; destructor still stopped before execution. Original source/result retained.',
        'old_frontend_backend_and_Sony_instructions_changed':False,'goal_complete':False})
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27','sources':[{
        'url':'https://eel.is/c++draft/futures.state','observation':'A future waiting function waits for a shared state to become ready; readiness is a value/exception result mechanism.',
        'scope':'Generic C++ contract only; no Sony recording state, encoder start, profile identity or hardware behavior established.'}]})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':40,'bounded_phases':84,'failed_attempt_included_in_passing_count':False,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'no_Sony_instruction_or_frontend_backend_modification':True,'actual_camera_Windows_UU_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_parameter_notice_registry_and_future_wait_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段117十九件封存与canonical核对，Mac客体原片段40案例84阶段。',
            '额外保存分支关联LoadMovieFinishedParam通知、0x1004注册键和promise指针；缺真实线程/锁/TLS及完整生命周期。',
            '通知ready不充编码器Open/Start、真实空闲或目标配置代次证据，未据此扩大guest前端门控。',
            '首次允许范围漏一条原BL已保留失败记录，仅修正harness范围；通过记录单独封存。',
            '16项验收状态、权限、阶段75后端及117前端保持；主录/成片/恢复未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage118_parameter_notice_wait']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'84 bounded phases distinguish parameter-load notice/promise readiness from unproven codec start, idle and configuration epoch. Complete registry lifecycle and real services not executed.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G05','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json'])
            req['stage118_scope']='参数加载通知/注册关联与future局部等待84阶段；不作为编码器启动/空闲/配置代次验证，真实服务及完整生命周期仍未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Extra SetMovieRecParam branch uses a LoadMovieFinishedParam notice registry and future; observed key/pointer and ready-state mechanics do not prove target configuration epoch, recording idle, encoder start or full lifecycle.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段118后定位真实录制状态和完整配置实例/关联来源；LoadMovieFinishedParam通知及future就绪不得充编码器Open/Start、空闲或目标代次门禁。仍需完整初始化/元数据、前后端同代关联、硬件成片/音画长录及同机恢复独立救援；仅Mac，无自动设备接口或刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 参数通知与等待链](<'+rel+'/README.md>)：40例84个原片段核对通知键/promise和等待；参数加载就绪不充编码器启动、空闲或配置代次证据，主录/恢复未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage118-parameter-notice-wait/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':84,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
