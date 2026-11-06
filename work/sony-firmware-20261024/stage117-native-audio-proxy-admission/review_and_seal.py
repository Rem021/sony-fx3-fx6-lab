#!/usr/bin/env python3
"""Seal native audio/proxy evidence, not runtime admission or recording."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import audio_proxy as t
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
    run=STAGE/'run-original-helpers-and-admission-20261027';p=run/'audio-proxy-results.json';j=json.loads(p.read_text())
    gp=STAGE/'run-new-object-guard-regression-20261027/guard-results.json';gates=json.loads(gp.read_text())
    ap=STAGE/'run-borrowed-auxiliary-control-20261027/aux-borrow-results.json';aux=json.loads(ap.read_text())
    assert j['status']=='PASS_NATIVE_AUDIO_PROXY_PRODUCTION_AND_GUEST_ONLY_ADMISSION_REFINEMENT'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'audio_proxy.py').read_bytes()
    assert j['source_sha256']==digest(STAGE/'audio_proxy.py') and j['C_sha256']==digest(STAGE/'scoped_frontend.c')
    assert j['object_sha256']==digest(STAGE/'scoped_frontend.a64.o') and j['own_link_veneers']==t.LINKS
    assert tuple(len(j[k]) for k in ('audio_matrix','proxy_matrix','caller_cases','admission_cases','MPR_queries'))==(40,32,12,16,3)
    assert not any(j[k] for k in ('goal_complete','persistent_write_release','Windows_UU_camera_operations','actual_MAIN_audio_proxy_file_or_recovery_proven'))
    events=[e for k in ('audio_matrix','proxy_matrix','caller_cases','MPR_queries') for c in j[k] for e in c['events']]
    admits=list(j['admission_cases'])
    for x,src in ((gates,'guard_regression.py'),(aux,'aux_borrow_control.py')):
        assert x['passing_result'] and x['reused_native_inputs_sha256']==digest(p) and x['object_sha256']==j['object_sha256']
        assert (gp.parent if src=='guard_regression.py' else ap.parent).joinpath('executed-source.py').read_bytes()==(STAGE/src).read_bytes()
        assert x['source_sha256']==digest(STAGE/src)
    assert len(gates['cases'])==gates['bounded_phases']==22 and len(aux['cases'])==aux['bounded_phases']==2
    assert len(events)+len(j['admission_cases'])==j['bounded_phases']==127
    for c in j['audio_matrix']:
        if c['local_returned']:assert c['native_audio_pair'] in ([0,1],[1,1],[1,2])
        assert c['not_real_capture_format_or_full_parameter_admission']
    for c in j['proxy_matrix']:
        assert c['local_helper_does_not_validate_format_quality_pair_or_actual_frame']
        if c['local_returned'] and c['proxy_selector20']==0:assert c['native_proxy_fields']['proxyFrameRate']==c['declared_MAIN_frame']
    assert [c['native_nominal_value'] for c in j['MPR_queries']]==[16000,9000,6000]
    for c in j['caller_cases']:
        assert c['native_fields']['MAIN_core']==[5,6,3] and len(bytes.fromhex(c['native_param_hex']))==448
        assert c['earlier_other_initializers_and_later_model_metadata_save_unexecuted'] and not c['whole_valid_source_or_real_configuration_proven']
        assert any(o.get('original_symbol_binding')=='memset' for e in c['events'] for o in e['original_returns_and_bindings'])
    assert sum(c['admitted_in_guest'] for c in j['admission_cases'])==8
    for c in admits+aux['cases']:
        assert not c['actual_live_profile_or_full_audio_proxy_hardware_support_proven']
        assert c['events'][0]['return_u32_if_returned']==(0 if c['admitted_in_guest'] else 6)
    for c in gates['cases']:
        assert c['events'][0]['return_u32_if_returned']==c['expected_status'] and not c['actual_gate_epoch_or_camera_permission_proven']
    for c in aux['cases']:assert c['explicit_borrowed_auxiliary_fixture']['bytes']==48 and c['explicit_borrowed_auxiliary_fixture']['not_generated_by_audio_proxy_helper']
    forbidden={0x2f6fe3c,0x2f6ff0c,0x2e6e638,0x2e6f0a8}
    app_events=[e for k in ('audio_matrix','proxy_matrix','caller_cases') for c in j[k] for e in c['events']]
    for e in app_events:
        assert all(e[k] for k in ('stack_outside_declared_b00_unchanged','scratch_outside_outputs_unchanged','whole_mapped_APP_and_libc_unchanged'))
        assert not e['actual_logs_runtime_state_or_success_return_adapters']
        assert not forbidden.intersection(int(a,16) for a in e['pcs'][:-1])
    front_events=[e for c in admits+aux['cases']+gates['cases'] for e in c['events']]
    for e in front_events:
        assert e['native_saved_registers_preserved'] and e['scratch_outside_outputs_unchanged'] and e['images_outside_declared_data_outputs_unchanged']
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    assert len(events)+len(front_events)==151
    for vpc,dims in ((6,(1920,1080)),(11,(1280,720))):assert struct.unpack('<HH',t.front.MPR.read(0x2cb108+vpc*24+4,4))==dims
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    oldc=(t.front.STAGE/'scoped_frontend.c').read_text();newc=(STAGE/'scoped_frontend.c').read_text();anchor='    u64 aux=*(const u64*)(src+0x120);'
    assert newc.startswith(oldc.split(anchor)[0]) and newc.split(anchor,1)[1]==oldc.split(anchor,1)[1]
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    sources=[{'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html',
        'observation':'Official proxy table lists1920x1080 HEVC42010 at16/9Mbps and1280x720 AVC4208 at6Mbps; normal proxy max59.94/50p with listed high-rate restrictions.',
        'scope':'Proxy support and listed combinations, not the new MAIN profile or actual resource/encoder acceptance.'},
        {'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868278.html',
         'observation':'Current classic FX3 movie settings table remains a separate public MAIN baseline.',
         'scope':'No inference that internal helper output equals a supported new MAIN setting.'}]
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27','sources':sources})
    put(STAGE/'frontend-admission-contract.json',{'schema':'fx3-guest-audio-proxy-admission/1','status':'UNDEPLOYABLE_GUEST_ONLY',
        'recognized_main_audio_pairs':[[0,1],[1,1],[1,2]],'audio_physical_capture_codec_rate_or_sync_proven':False,
        'proxy_disabled_fields':{'active':0,'vpc':13,'quality':255,'frame':12,'audio':5,'channel':255},
        'recognized_enabled_proxy_tuples':[{'vpc':6,'quality':6},{'vpc':6,'quality':26},{'vpc':11,'quality':28}],
        'enabled_proxy_other_fields':{'active':1,'frame':3,'audio':3,'channel':1},
        'preserves_MAIN_quality6_frame3_and_other_value_fields':True,
        'native_helper_return_not_complete_format_or_frame_validation':True,
        'borrowed_auxiliary48_control_is_not_owned_snapshot_or_capacity_proof':True,
        'original_gate_and_overlap_guards_rechecked':22,
        'still_required':['actual healthy full parameter source','all omitted initializers and metadata writers',
            'real target selector,callsite,synchronization and epoch','actual audio/proxy and MAIN resource/16M encoding',
            'file/audio/timing/longrun/coldboot','same-body backup/restore readback and independent rescue'],
        'stage75_backend_and_stage116_sealed_files_unchanged':True,'camera_or_persistent_use_permitted':False,'goal_complete':False})
    listings=[]
    for a,z in ((0x2e5349c,0x2e53710),(0x2e50bf0,0x2e50e58),(0x2e6e628,0x2e6e638),(0x2e6f040,0x2e6f0a8)):
        listings.append({'APP_range':[hex(a),hex(z)],'original_bytes_sha256':sha(t.APP.read(a,z-a)),
            'original_disassembly':[{'address':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in t.APP.md.disasm(t.APP.read(a,z-a),a)]})
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_APP_sha256':digest(t.APP.path),
        'original_MPR_sha256':digest(t.front.MPR.path),'original_libc_sha256':digest(t.front.LIBC.path),
        'own_object_sha256':j['object_sha256'],'own_C_sha256':j['C_sha256'],'own_link_veneers':t.LINKS,
        'original_diag_field_names':{hex(a):t.APP.read(a,180).split(b'\0')[0].decode() for a in (0x398a3b5,0x398a3da,0x398a418,0x398a4b0,0x398a4d4,0x398a4f9,0x398a51b)},
        'original_audio_param_and_channel_offsets':['0x184','0x188'],
        'original_proxy_offsets':['0x196','0x198','0x19c','0x1a0','0x1ac','0x1b0'],
        'input_selector_numbers_are_not_user_menu_indices':True,
        'combined_caller_gaps':['first original logger','other earlier initializers/naming/proxy metadata setup',
            'all later model/metadata/record control and actual saving'],
        'original448_byte_clear_not_proof_omitted_writers_normally_leave_zeros':True,
        'unlisted_proxy_pairs_return_locally_not_claimed_hardware_valid':True,
        'only_own_guest_frontend_changed_no_Sony_patch':True,'old_matrix_results_reused_for_extra_controls_not_rerun':True,
        'original_listings':listings,'bounded_phases':151,'goal_complete':False,'persistent_write_release':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'audio_matrix_cases':40,'proxy_matrix_cases':32,'caller_cases':12,'new_admission_cases':16,
        'original_nominal_queries':3,'extra_guard_cases':22,'extra_borrowed_auxiliary_cases':2,
        'bounded_phases':151,'formal_sources_match_executed_copies':True,'same_agent_review_not_independent_engine':True,
        'stage75_backend_physically_unchanged':True,'actual_camera_or_Windows_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_audio_proxy_fields_and_stricter_guest_frontend_combination_admission'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11617件封存/canonical及目标卷核对；无相机/Windows操作。',
            '原音频/代理helper矩阵，原调用者memset和原调用点执行；MAIN帧率传代理，原局部helper不校验全部格式/质量/帧率配对。',
            'Sony代理原表核对；自编译guest前端保留已识别音频与代理配对，拒绝未列配对/通道和帧率不一致；原门控22及借用辅助数据2例补回归。',
            '151有界阶段，原矩阵未重复计数；完整源/模型/元数据与其它初始化仍缺，原清零不代表正常缺省。',
            '逻辑16M与临时MAIN FF视图/真实编码仍需一致；音频字段不是采音/同步验收；16项状态/权限和阶段75后端保持。'],'completion_not_claimed':True}
    g['latest_stage_evidence']['stage117_audio_proxy_admission']={'readme':rel+'/README.md','result':rr,
        'guard_result':str(gp.relative_to(ROOT)),'aux_result':str(ap.relative_to(ROOT)),
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/frontend-admission-contract.json',
        'review':rel+'/completed-evidence-review.json','scope':'151 bounded phases give native audio/proxy origins and improve only guest frontend admission. Omitted full source/model/epoch, actual capture/resource/recording/recovery remain unproved.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G05','G08','G10','G11','G13'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/frontend-admission-contract.json'])
            req['stage117_scope']='原音频/代理参数与帧率来源及guest准入151阶段；局部返回非整组有效，已拒绝识别的不一致声明配对。完整来源/物理采音与同步/资源和编码/恢复仍缺，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Native app helper output is now known for audio/proxy and coupled caller fields. Proxy helper copies MAIN frame and accepts independently converted unlisted quality pairs, so guest frontend adds recognized-pair/channel/frame predicates. Clear and byte preservation do not establish omitted initialization, actual device state or valid recording.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段117后核对未执行的完整初始化/命名/元数据及两保存分支额外控制，建立真实目标选择、同步、配置代次与前后端同代关联方案。音频/代理helper局部返回不能充整组验证，准入条件只是guest候选。逻辑16M与MAIN临时FF视图、实际编码/成片/音画及同机备份恢复独立救援仍缺；仅Mac，Windows延后，不自动接口或刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原音频/代理与前端配对检查](<'+rel+'/README.md>)：原helper/调用者与guest准入补强151阶段；局部返回非整组有效，完整配置/采音同步/编码及恢复未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage117-audio-proxy-admission/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':151,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
