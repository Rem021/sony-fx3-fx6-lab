#!/usr/bin/env python3
"""Seal quality-domain evidence without changing prototype or live acceptance."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import quality_domains as t
BASE,ROOT=t.BASE,t.ROOT
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*1024*1024):h.update(b)
    return h.hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def pin(p):
    manifest=json.loads((p.parent/'final-receipt.json').read_text())
    member=next(x for x in manifest['files'] if x['path']==str(p.relative_to(ROOT)))
    assert p.stat().st_size==member['bytes'] and digest(p)==member['sha256'];return member

def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for x in prior['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-original-quality-domains-20261027';p=run/'quality-domain-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_ORIGINAL_MAIN_QUALITY_DOMAINS_DISTINGUISH_FH16K_FROM_FF25K'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'quality_domains.py').read_bytes()
    assert j['source_sha256']==digest(STAGE/'quality_domains.py')
    assert not any(j[k] for k in ['goal_complete','persistent_write_release','Windows_UU_camera_operations','actual_MAIN_source_runtime_hardware_or_recovery_proven'])
    assert tuple(len(j[k]) for k in ['app_cases','scalar_cases','FF_produced','FF_classified','resource_cases'])==(8,2,2,2,4)
    source_pins=[pin(Path(m.__file__)) for m in (t.mp,t.main,t.main.prev,t.matcher,t.matcher.s)]
    assert digest(t.MPR.path)==t.mp.MPR_SHA
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert sha(blob)==t.matcher.r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    assert j['app_quality_table']==t.table_inventory() and len(j['app_quality_table']['rows'])==26
    for c in j['app_cases']:
        assert c['native_MAIN_core']==[5 if c['format_selector']==6 else 1,6 if c['quality_selector']==2 else 8,3]
        assert not c['actual_menu_reachability_audio_full_parameter_or_HS_HD_producer_proven']
    scalar_events=[]
    for s in j['scalar_cases']:
        assert len(s['generic_VPC_cases'])==5 and len(s['quality_cases'])==2
        assert [c['native_VPC'] for c in s['generic_VPC_cases']]==[6,5,8,13,1]
        assert [(c['MAIN_quality'],c['native_API_quality'],c['native_nominal_query'],c['native_SIDB_slice_u16']) for c in s['quality_cases']]==[(6,22,16000,16),(8,24,25000,25)]
        for c in s['generic_VPC_cases']+s['quality_cases']:scalar_events.extend(c['events'])
    sidb=list(t.MPR.md.disasm(t.MPR.read(0xd3068,1396),0xd3068))
    assert any(i.address==0xd30e0 and i.mnemonic=='mov' and i.op_str=='w20, #0x3e8' for i in sidb)
    assert t.MPR.plt[0x7cf70]=='_ZN3mpr5pconv15GetVideoBitrateEN9DefStruct8VQualityE'
    packet_diffs=[]
    for produced,c in zip(j['FF_produced'],j['FF_classified']):
        assert produced['declared_core_vpc_quality_frame']==[6,8,3] and produced['core_fields']['quality82']==24
        assert produced['core_fields']['geometry']==[1920,1080] and len(produced['unwritten_output_offsets'])==51
        assert c['decoded']['quality']['original_name']=='FF' and c['decoded']['quality']['native_enum']==6
        assert c['decoded']['coding']['original_name']=='HEVC_MP4' and c['decoded']['frame']['original_name']=='29_97'
        assert c['decoded']['chroma']['original_name']=='CHROMA_420' and c['decoded']['depth']['original_name']=='BIT_DEPTH_10'
        old=next(x for x in j['reused_FH_original_outputs'] if x['seed']==produced['seed'])
        x,y=bytes.fromhex(old['raw98_hex']),bytes.fromhex(produced['raw98_hex'])
        diff=[i for i,(a,b) in enumerate(zip(x,y)) if a!=b];assert diff==[0x82] and x[0x82]==22 and y[0x82]==24
        packet_diffs.append({'seed':produced['seed'],'offsets':['0x82'],'old':22,'new':24})
    for rec in (j['reused_FH_receipt'],j['reused_descriptor_receipt']):assert digest(ROOT/rec['path'])==rec['sha256']
    for c in j['resource_cases']:
        m=c['match'];expected=-1 if m['label']=='retained_target_FH_control' else 386
        assert m['independent_matcher']['matched_row']==expected
        assert c['quality_field_only_handoff_not_complete_MPR_receiver_or_real_image_tail']
        assert not m['full_matcher_with_diagnostics_or_hardware_executed']
        if expected==386:assert m['matched_row']['preset_id_untyped']=='0x19450'
    events=[e for c in j['app_cases'] for e in c['events']]+scalar_events
    events.extend(e for c in j['FF_produced'] for q in c['category_queries'] for e in q['events'])
    events.extend(e for c in j['FF_produced'] for e in c['original_builder_events'])
    events.extend(e for c in j['FF_classified'] for e in c['events'])
    assert len(events)+len(j['resource_cases'])*2==j['new_bounded_phases']==130
    assert not j['reused_old_FH_phases_counted_as_new']
    for e in scalar_events:
        assert e['whole_stack_outside_200_byte_declared_frame_unchanged'] and e['whole_scratch_outside_declared_outputs_unchanged']
        assert e['whole_original_relocated_ELF_image_unchanged'] and not e['stubs_logger_or_success_return_adapters_executed']
        assert all('stub' not in x for x in e['original_local_PLT_and_return_observations'])
    old=json.loads(before)
    # Prototype is preserved physically as well as in canonical references.
    for member in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/member['path'])==member['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    put(STAGE/'public-source-notes.json',{'checked_date':'2026-10-27',
        'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000868279.html',
        'observation':'Classic FX3 Ver2+ File Format page lists XAVC HS4K, XAVC S4K/HD and XAVC S-I4K/HD/DCI4K; does not list XAVC HS HD.',
        'scope':'Public format baseline, not an exhaustive internal type table, hardware prohibition or recovery guarantee.'})
    put(STAGE/'profile-domain-contract.json',{'schema':'fx3-offline-profile-domain-contract/1','status':'SPEC_ONLY_UNDEPLOYABLE',
        'logical_target_MAIN_core':[6,6,3],'logical_target_nominal_query':16000,
        'native_MAIN_quality6_API22_resource4_FH':True,
        'native_MAIN_quality8_API24_resource6_FF_nominal25000':True,
        'do_not_globally_replace_MAIN_quality6_with8_to_force_resource_match':True,
        'existing_stage75_strategy':'A bounded temporary resource-matching view may map FH to FF while retaining the source descriptor. Existing guest-only writer separately targets16M; real scope, lifecycle and consumer coverage remain unproved.',
        'new_generic_type_source':{'entry':'libmpr+0xc9e84','declared_typed_inputs':[1,2,0,1,0],'native_output':6,
            'actual_FX3_application_MAIN_callsite_binding_proven':False},
        'future_frontend_requirements':['exact target selector and callsite','same full MovieRecParam audio/proxy/media state',
            'trusted configuration epoch and synchronization','model/query/cache/mux identity16M',
            'temporary FF resource view plus actual16M encoder application and readback'],
        'hardware_file_audio_longrun_backup_restore_and_independent_rescue_required':True,
        'prototype_changed':False,'camera_or_persistent_use_permitted':False,'goal_complete':False})
    def listing(n,a,z):return {'image':n.path.name,'range':[hex(a),hex(z)],'original_bytes_sha256':sha(n.read(a,z-a)),
        'original_disassembly':n.dump(a,z) if hasattr(n,'dump') else n.disasm(a,z)}
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'imported_sources_verified_against_existing_seals':source_pins,
        'original_MPR_sha256':t.mp.MPR_SHA,'original_avcam_sha256':sha(blob),
        'app_quality_jump_table':j['app_quality_table'],'MPR_original_quality_table6_8':{'address':'0x2cbb88','values':{'6':22,'8':24}},
        'original_nominal_table':{'address':'0x2e0a70','index':'MAIN_VQuality-2','values':{'6':16000,'8':25000}},
        'SIDB_scope':'Original d30e0 initializes W20=1000. Independent d318c query/divide/store frame writes16/25, stopsd319c. No full SIDB update, mux or actual encoder readback.',
        'generic_VPC_scope':'Original helper can produce6 under typed declared inputs. App MAIN examples remain5/1, not natural target source proof.',
        'new_native_FF_packet_differences_from_reused_FH':packet_diffs,
        'resource_scope':'Native receiver quality scalar is handed to prior original HD descriptor fixture. Other fields and (2,10) tail remain independent historical controls. Not a complete new receiver or actual current image tail.',
        'retained_unwritten_output_bytes':51,'all_logging_gaps_are_independent_inputs_not_successful_returns':True,
        'actual_current_buffer_instance_epoch_or_loader_proven':False,'stage75_prototype_physical_hashes_retained':True,
        'old_FH_production_reused_not_reexecuted':j['reused_FH_receipt'],
        'original_listings':[listing(t.APP,0x2e6ed88,0x2e6efac),listing(t.MPR,0xc9e84,0xc9fcc),
            listing(t.MPR,0xd0758,0xd0800),listing(t.MPR,0x2c0ce0,0x2c0d04),listing(t.MPR,0xd30d0,0xd30f0),listing(t.MPR,0xd318c,0xd319c)],
        'actual_MAIN_hardware_or_recovery_proven':False,'goal_complete':False,'persistent_write_release':False})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'app_cases':8,'new_FF_Open_cases':2,'resource_cases':4,'new_bounded_phases':130,
        'old_FH_outputs_reused':2,'old_phases_counted_as_new':False,'formal_source_matches_executed_copy':True,
        'same_agent_review_not_independent_engine':True,'stage75_prototype_unchanged':True,
        'actual_camera_or_Windows_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_MAIN_quality_source_nominal_SIDB_scalars_generic_VPC_and_resource_domain_alignment'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段11411件封存/canonical及目标卷核对；原MPR/avcam和复用记录校验，无设备操作。',
            '原应用质量表26项及两格式/两质量独立转换；selector2→MAIN6，selector4→MAIN8，原应用类型仍5/1而非6。',
            '原通用MPR typed helper在声明输入生成VPC6；原质量6→API22/FH4/nominal16000，8→API24/FF6/25000；SIDB原片段16/25，非实测码率。',
            '新FF Open接原标量接收，与已封存FH原包只差82；独立描述符质量交接在声明tail下使matcher由-1变386。新增130阶段，旧FH未冒充重跑。',
            '不能为命中FF全局把MAIN质量改8；保留逻辑16M与临时资源视图域分离，stage75物理文件及canonical原型保持不可部署。',
            '完整前端来源/参数代次/51未写字节与实际硬件成片/同机恢复仍缺，16项状态及权限保持。'],'completion_not_claimed':True}
    g['latest_stage_evidence']['stage115_MAIN_quality_domains']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','domain_contract':rel+'/profile-domain-contract.json',
        'review':rel+'/completed-evidence-review.json','scope':'130 new bounded phases distinguish MAIN6/FH nominal16000 from MAIN8/FF nominal25000 and give generic native VPC6 provenance; no actual app target source, current instance/16M hardware/mux or recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/profile-domain-contract.json'])
            req['stage115_scope']='原质量6/FH/16000与质量8/FF/25000及SIDB16/25、原通用VPC6来源130新阶段；全局改质量会改名义身份，原应用MAIN仍无目标自然来源。临时资源视图/实际16M编码/完整参数及恢复未证，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original app selector4 yields MAIN quality8; native Open changes only API byte82 versus quality6, but original nominal and SIDB scalars change16000/16 to25000/25. Native FF matches resource row386 only under explicit descriptor/tail input. Generic original MPR helper producesVPC6 without making existing app MAIN a natural producer.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段115后优先在已定位应用MAIN构包/SetMovieRecParam保存调用点形成受限前端与诊断方案，用原typed helper产生目标VPC6，核对完整音频/代理/媒体元数据和配置代次。不要全局quality6→8；保持逻辑16M、临时FF匹配视图与实际16M编码目标分别可验证。实际成片与同机健康备份/恢复/独立救援仍缺，Windows延后，仅Mac，不自动设备或刷写。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 MAIN质量与码率身份分域](<'+rel+'/README.md>)：原质量6/FH名义16000与8/FF25000、SIDB16/25及通用VPC6来源130新阶段；实际前端/16M编码及恢复未验，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage115-main-quality-domains/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'new_bounded_phases':130,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
