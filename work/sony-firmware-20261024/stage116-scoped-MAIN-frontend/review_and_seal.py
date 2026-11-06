#!/usr/bin/env python3
"""Seal a guest-only frontend without changing camera/backend authorization."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import frontend_trial as t
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
    for x in prior['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-scoped-original-data-writes-20261027';p=run/'frontend-trial-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_GUEST_ONLY_SCOPED_MAIN_COPY_AND_ORIGINAL_PARAMETER_AUXILIARY_ALIAS_SCOPE'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'frontend_trial.py').read_bytes()
    assert j['source_sha256']==digest(STAGE/'frontend_trial.py')
    assert j['C_source_sha256']==digest(STAGE/'scoped_frontend.c') and j['object_sha256']==digest(STAGE/'scoped_frontend.a64.o')
    assert (len(j['positive_cases']),len(j['negative_cases']),len(j['app_callsite_cases']),j['bounded_phases'])==(8,30,4,78)
    assert not any(j[k] for k in ['goal_complete','persistent_write_release','Windows_UU_camera_operations','real_frontend_hook_synchronization_MAIN_file_or_recovery_proven'])
    assert j['own_link_veneers']==t.LINKS and len(t.LINKS)==3
    assert {x['original_target'] for x in t.LINKS}=={hex(0xc9e84),hex(0x9a2ac),hex(t.core.CBASE+t.LIBC.symbols['memcpy']['va'])}
    cases=j['positive_cases']+j['negative_cases'];events=[e for c in cases for e in c['events']]
    assert len(events)+len(j['app_callsite_cases'])==78
    for c in j['positive_cases']:
        assert c['return_status']==0 and c['semantic_changed_offsets']==[0x170]
        assert not c['actual_synchronization_full_setter_return_or_owned_runtime_snapshot_proven']
        assert c['events'][0]['native_saved_registers_preserved']
        assert c['original_getter_aux_pointer']==(hex(t.AUXSTORE) if c['declared_aux_bytes'] else '0x0')
        if c['declared_aux_bytes']:
            assert c['declared_aux_bytes']==48 and c['native_setter_aux_copy_and_getter_pointer_alias_proven_under_inputs']
            assert c['prior_getter_struct_unchanged_but_pointed_data_changed_after_second_setter'] and len(c['events'])==6
        else:assert len(c['events'])==5
    for c in j['negative_cases']:
        assert c['return_status'] in (1,2,3,4,5,6) and len(c['events'])==1
        assert not c['events'][0]['stores'] or all(t.SP-0x800<=int(w['address'],16)<t.SP for w in c['events'][0]['stores'])
    forbidden={0xf0ec0,0x7fd00,0x7c5f0,0x82530,0x81860,0x82f40}
    for e in events:
        assert all(e[k] for k in ['stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'])
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
        assert not forbidden.intersection(int(a,16) for a in e['pcs'][:-1])
        assert all('stub' not in c for c in e['original_imports_and_returns'])
    assert all(not c['actual_prior_app_full_construction_or_adapter_interposition_proven'] for c in j['app_callsite_cases'])
    failed=STAGE/'run-native-copy-and-aux-alias-20261027';f=json.loads((failed/'attempt-failure.json').read_text())
    assert f['status']=='FAILED_NO_PASSING_RESULT' and 'write outside stack/scratch' in f['error']
    assert not (failed/'frontend-trial-results.json').exists()
    old=json.loads(before)
    for m in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/m['path'])==m['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    ctor=t.MPR.read(0x9a2ac,28);assert t.MPR.plt[0x7d6b0]=='memset' and t.MPR.plt[0x7b9d0]=='memcpy'
    def listing(a,z):return {'range':[hex(a),hex(z)],'original_bytes_sha256':sha(t.MPR.read(a,z-a)),'original_disassembly':t.MPR.disasm(a,z)}
    put(STAGE/'compile-receipt.json',{'compiler':'Apple clang21.0.0 (clang-2100.3.27.1)',
        'executable':'/usr/bin/xcrun clang','arguments':['--target=aarch64-none-elf','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-c'],
        'exit_code':0,'source_sha256':j['C_source_sha256'],'object_sha256':j['object_sha256'],
        'initial_unrun_source_and_object_retained':True,'actual_Sony_module_or_firmware_image':False})
    put(STAGE/'frontend-contract.json',{'schema':'fx3-MAIN-frontend-trial/1','status':'UNDEPLOYABLE_GUEST_ONLY',
        'copy_preparer_only_not_setter_hook':True,'source_value_span':445,'destination_constructed_bytes':448,
        'declared_source_core':[5,6,3],'candidate_core':[6,6,3],'native_VPC_helper_inputs':[1,2,0,1,0],
        'only_semantic_changed_byte':'0x170','logical_quality6_and_frame3_preserved':True,
        'callsite_allowlist':['0x2e6f7bc','0x2e6f9b0'],'callsite_values_and_gate_fields_are_untrusted_fixture_inputs':True,
        'opaque_external_length_offset':'0x118','opaque_external_pointer_offset':'0x120',
        'prepared_pointer_borrowed_until_actual_setter_copy_completes':True,
        'GetMovieRecParam_external_pointer_is_shared_alias_not_owned_snapshot':True,
        'actual_external_buffer_capacity_not_established_by_48byte_control':True,
        'real_frontend_requirements':['actual authenticated full parameter baseline','trusted target selector and callsite binding',
            'original complete audio/proxy/media state','shared synchronization and real epoch/idle state',
            'external data capacity/ownership through setter completion','model/query/cache/mux/16M encoder alignment',
            'healthy same-body backup,limited restore/readback and independent rescue'],
        'stage75_backend_unchanged_and_still_undeployable':True,'camera_or_persistent_use_permitted':False,'goal_complete':False})
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR':str(t.MPR.path.relative_to(ROOT)),
        'original_MPR_sha256':digest(t.MPR.path),'original_libc_sha256':digest(t.LIBC.path),
        'our_object_and_veneers':t.LINKS,'own_code_and_guest_relocation_only':True,
        'original_ctor_zero_bytes':448,'original_Set_Get_value_copy_bytes':445,
        'setter_shared_object':'0x38c810','setter_external_copy_destination':'0x38cc78',
        'original_library_data_writes_are_guest_only_and_phase_fenced':True,
        'independent_gaps':['complete app source construction','actual adapter interposition','setter diagnostic and parameter check',
            'setter mutex/write lock','getter read lock','unlock and complete function return'],
        'source_full_bytes_are_declared_not_actual_valid_camera_configuration':True,
        'byte_preservation_not_audio_proxy_or_metadata_semantic_acceptance':True,
        'original_setter_external_copy_getter_alias_and_second_setter_effect_proven_under_inputs':True,
        'concurrency_shared_buffer_capacity_or_source_lifetime_proven':False,
        'failure_scope':'Initial execution observer fenced all writes outside stack/scratch; stopped original guest shared-data copy. Formal observer adds only each phase exact original data output spans, with all other image bytes compared; no Sony logic change.',
        'initial_unrun_candidate_scope':'Control/source/destination and borrowed auxiliary overlap guards added before formal candidate tests. Initial C/object are retained but never accepted or deployed.',
        'original_listings':[listing(0x9a2ac,0x9a2c8),listing(0xf0ff0,0xf1120),listing(0xf1238,0xf1284)],
        'goal_complete':False,'persistent_write_release':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'positive_cases':8,'negative_cases':30,'app_callsite_cases':4,'bounded_phases':78,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage75_backend_physically_unchanged':True,'actual_camera_or_Windows_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_compiled_scoped_MAIN_copy_preparer_and_original_full_parameter_external_alias_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11511件封存/canonical及目标卷核对；新自编译前端仅guest运行，无相机/Windows操作。',
            '候选经原typed helper/原构造器/原memcpy生成受限[6,6,3]副本，有效445B只差170，质量和帧率保留；30拒绝对照。',
            '两个原应用调用点独立片段传整包指针，未接入真实应用或可信profile/epoch/idle gate。',
            '原Set/Get独立保存复制与48B外部数据重指针；第二次保存使旧读回结构的共享指向内容改变。不能把结构复制称完整拥有的快照。',
            '正式78阶段；初次guest数据写边界失败保留，精确逐阶段输出范围修正，没有执行日志/检查/锁/完整setter或修改Sony指令。',
            '源整包仍声明数据、完整音频代理/代次/实际16M编码与同机恢复未证，16项状态及阶段75后端/授权保持。'],'completion_not_claimed':True}
    g['latest_stage_evidence']['stage116_scoped_MAIN_frontend']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','frontend_contract':rel+'/frontend-contract.json',
        'review':rel+'/completed-evidence-review.json','scope':'Guest-only compiled copy-preparer and independent original Set/Get spans,78 phases. No real frontend interposition, trusted source/epoch/synchronization, full recording or rescue.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G05','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/frontend-contract.json'])
            req['stage116_scope']='自编译guest-only受限前端副本与原Set/Get/外部数据别名78阶段；445B字段保留不等于完整配置有效或owned snapshot，真实source/选择/同步/epoch及上机仍缺。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'New guest-only frontend prepares a typed nativeVPC6 copy while preserving quality6/frame3 and other445-byte value fields. Original Set separately copies external length/pointer payload and Get returns its shared alias; later Set changes pointed content without changing prior struct. Real baseline, adapter binding and shared lifetime/synchronization remain unproved.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段116后核对原源参数完整初始化、音频/代理helper及两保存分支额外控制；把声明的copy-preparer接到可核对的实际参数生产/目标选择和同步代次方案。外部payload需容量/所有权及setter完成前存活，Get结构不能单作owned快照。阶段75后端不变；真实成片/备份恢复/独立救援仍缺，仅Mac，Windows延后，不自动设备或刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 受限MAIN前端与外部参数寿命](<'+rel+'/README.md>)：guest编译副本/原Set-Get外部共享别名及拒绝对照78阶段；真实前端/完整配置/编码和恢复仍未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage116-scoped-MAIN-frontend/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':78,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
