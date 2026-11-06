#!/usr/bin/env python3
"""Seal frontend/DMM selection evidence, not actual allocation or recording."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import frontend_dmm as t
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
    member_counts={}
    for manifest,expected in ((t.PRIOR,t.PRIOR_SHA),(t.P117,t.P117_SHA)):
        assert digest(manifest)==expected;prior=json.loads(manifest.read_text())
        for x in prior['files']:
            p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and digest(p)==x['sha256']
        member_counts[manifest.parent.name]=len(prior['files'])
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-native-frontend-DMM-20261027';p=out/'frontend-DMM-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_FRONTEND_DMM_MODE_CONSISTENCY_NOT_ALLOCATION_OR_RECORDING'
    assert j['source_sha256']==digest(STAGE/'frontend_dmm.py') and (out/'executed-source.py').read_bytes()==(STAGE/'frontend_dmm.py').read_bytes()
    assert j['stage117_source_result_sha256']==digest(t.RESULT117)
    assert len(j['profiles'])==8 and len(j['table_free_cases'])==12
    ev=[e for k in ('profiles','table_free_cases') for c in j[k] for e in c['events']];assert len(ev)==j['bounded_phases']==192
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_DMM_allocation_release_MAIN_hardware_or_recovery_proven'):assert not j[k]
    for e in ev:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0xc8c70,0x7cbc0,0x822e0,0x7fd00,0x7c5f0,0x82530,0x81860}
    for e in ev:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    pair_count=0
    for c in j['profiles']:
        assert len(bytes.fromhex(c['frontend_native_candidate448']))==448
        assert all(c[k] for k in ('earlier_omitted_initializers_real_Model_word0_and_live_configuration_unproven',
            'same_DMM_mode_not_allocation_buffer_or_hardware_acceptance_proof','actual_FRONT_gate_hook_and_Main_recording_unproven'))
        assert len(c['pairs'])==2
        for q in c['pairs']:
            pair_count+=1;assert q['original_type']==5 and q['candidate_type']==6
            assert q['native_original_mode']==q['native_candidate_mode'] and q['actual_changed_Model_byte_offsets']==['0x1c8']
    assert pair_count==16
    modes=sorted({q['native_candidate_mode'] for c in j['profiles'] for q in c['pairs']});assert modes==[21,25,31,32]
    for c in j['table_free_cases']:
        mode=c['declared_mode'];valid=mode in modes
        assert bool(int(c['native_table_pointer_ELF'],16))==valid
        assert c['native_free_return_for_noop_only']==(None if valid else int(mode>38))
        assert not c['actual_area_removal_ExtList_free_allocated_memory_or_runtime_table_proven']
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/7';contract['refined_in_stage']=STAGE.name
    contract['frontend_DMM_selection']={'reused_frontend_stage':'stage117-native-audio-proxy-admission','source_result_sha256':digest(t.RESULT117),
        'native_param_value_copy_bytes':445,'native_Model_parameter_offset':'0x58','original_type':5,'candidate_type':6,
        'paired_cases':16,'observed_modes':[21,25,31,32],'all_paired_modes_equal':True,
        'Model_word0_inputs':[1,2],'word0_actual_business_source_unproven':True,
        'earlier_parameter_initialization_complete_and_natural_menu_reachability_proven':False,
        'same_mode_does_not_establish_physical_allocation_size_owner_or_encoder_support':True,
        'actual_DMM_allocation_or_usable_MAIN_recording_proven':False}
    contract['DMM_free_return_scope']={'valid_observed_modes':'original table selected; stopped before RemoveAreaExtList',
        'positive_out_of_range_mode39_native_return':1,'negative_mode_minus1_native_return':0,
        'true_can_come_from_no_removal_range_branch':True,'no_claim_real_callers_use_invalid_mode_or_actual_leak':True}
    contract['next_runtime_acceptance_requirements'].append('bind actual DMM mode flags and full healthy parameter source; verify allocation/buffer geometry/ownership and downstream MAIN16M acceptance, not only type-only mode equality or free bool')
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0xccafc,0xccb18),(0xcd5c4,0xcd700),(0x2af638,0x2af810),(0x2af9ec,0x2afa58),(0x2afa58,0x2afa98))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.front.LIBC.path),'own_frontend_C_sha256':digest(t.P117.parent/'scoped_frontend.c'),
        'own_frontend_object_sha256':digest(t.P117.parent/'scoped_frontend.a64.o'),'listings':listings,
        'native_DMM_mode_input_offsets':['Model+1ee byte','Model+1cc word','Model+91 byte','Model+0 word','Model+1ed byte','Model+214 byte'],
        'main_type_at_Model1c8_not_read_by_this_selector':True,
        'full_source_and_actual_Model_values_are_not_proven_by_original_helper_outputs':True,
        'no_actual_DMM_allocation_or_area_removal_ExtList_free_hardware_encoding_or_recovery':True,
        'original_FX3_files_and_stage117_frontend_stage75_backend_unchanged':True,'bounded_phases':192})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':member_counts,
        'source_profiles':8,'paired_cases':16,'table_free_cases':12,'bounded_phases':192,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_pinned_frontend_original_parameter_copy_and_DMM_mode_pair_consistency'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段124十件/阶段117十九件封存及canonical核验；原前端对象未改。',
            '前端候选接原445字节复制和GetDmmModeId，16配对原/候选模式一致，192有界片段。',
            'Model首字/前期完整初始化仍为声明前提，类型改6不改变此选择器结果不充实际分配/资源或主录可用。',
            '有效模式21/25/31/32进原表后止于区域移除前；人工39返回真但未移除，布尔真不充DMM释放。',
            '16项状态、权限及75后端/原固件保持，硬件成片与同机备份恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage125_frontend_DMM_consistency']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'192 bounded phases couple the pinned frontend with original parameter copy and DMM mode selection; all16 declared before/after pairs match. Real source initialization, allocation, encoder support and recovery remain unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11','G15'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage125_scope']='固定前端/原参数复制接DMM选择192阶段，16组声明输入模式一致；未证明完整健康源/真实Model/分配/资源16M编码。FreeDmm真可为范围no-op，恢复仍未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Type-only frontend transformation preserves DMM selection in16 declared pairs because the native selector reads other retained fields. This is not allocation/geometry/encoder proof. Original free(mode39) returns true without area removal; actual callers and release remain unproven.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段125后优先核对目标DMM模式的实际分配/缓冲表和Open消费，绑定完整健康参数源与真实Model字段及前后端同代；模式一致不充物理分配/所有权/16M编码，释放真不充实际回收。仅Mac，实录音画长录/同机恢复独立救援要求保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 前端与DMM模式一致性](<'+rel+'/README.md>)：固定前端接原参数复制/内存模式选择，16组声明输入前后一致、192片段；真实分配/资源16M编码与恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage125-frontend-DMM-consistency/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'paired_cases':16,'bounded_phases':192,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
