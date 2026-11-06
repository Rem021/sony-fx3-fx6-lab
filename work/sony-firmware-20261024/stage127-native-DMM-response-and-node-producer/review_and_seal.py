#!/usr/bin/env python3
"""Review original DMM layout evidence and seal with unchanged acceptance gates."""
from pathlib import Path
import copy,datetime,difflib,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import dmm_response as t
BASE,ROOT=t.BASE,t.ROOT
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def events(j):
    return [e for c in j['response_cases'] for e in c['events']]+[
        e for c in j['node_cases'] for e in c['events']]+[
        e for c in j['node_cases'] for p in c['providers'] for e in p['events']]
def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert digest(t.PRIOR)==t.PRIOR_SHA;prior=json.loads(t.PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-zeroed-BufferTable-20261027';result=out/'DMM-response-results.json';j=json.loads(result.read_text())
    oldout=STAGE/'run-original-DMM-layout-20261027';first=json.loads((oldout/'DMM-response-results.json').read_text())
    passed='PASS_NATIVE_DMM_LAYOUT_AND_NODE_CONSTRUCTION_NOT_ALLOCATION_OR_RECORDING'
    assert j['status']==first['status']==passed
    assert digest(STAGE/'dmm_response.py')==j['source_sha256']==digest(out/'executed-source.py')
    assert digest(oldout/'executed-source.py')==first['source_sha256']
    source_diff=list(difflib.unified_diff((oldout/'executed-source.py').read_text().splitlines(),
        (out/'executed-source.py').read_text().splitlines(),fromfile='preserved-first',tofile='formal-zero-BufferTable',lineterm=''))
    assert source_diff
    ev=events(j);assert len(ev)==j['bounded_phases']==140
    assert len(j['response_cases'])==9 and len(j['node_cases'])==2 and sum(len(c['nodes']) for c in j['node_cases'])==17
    assert not any(j[k] for k in ('camera_Windows_UU_or_host_services_executed','goal_complete','persistent_write_release'))
    stopped={0x7fbf0,0x7e350,0x7c010,0x7d7d0,0x7dd50,0x83370,0x819a0,0x2ae900,0x7d4f0,0x2af120,0x7d630}
    for e in ev:
        for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'):assert e[k]
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
        assert not stopped.intersection(int(p,16) for p in e['pcs'][:-1])
    cp=j['response_cases']; normal={c['n']:c for c in cp if c['status']==0 and c['kind']==0x8020}
    assert set(normal)=={0,1,2,8,9,10}
    for n,c in normal.items():
        assert c['offline_admission']['accepted']==(1<=n<=8)
        assert c['events'][-1]['reason']=='returned' and not c['service_result_success_claimed']
        assert not c['real_allocation_or_reachable_firmware_bug_proven']
        raw=bytes.fromhex(c['declared_reply']);b=bytes.fromhex(c['native_output_a8'])
        expected=bytearray(0xa8);length=0x18+n*16 if n else 0x28
        expected[:min(0xa8,length)]=raw[:min(0xa8,length)]
        firstaddr=struct.unpack_from('<Q',raw,0x18)[0]
        struct.pack_into('<QQ',expected,0x98,firstaddr+t.OFFSET,t.OFFSET)
        struct.pack_into('<I',expected,0x10,c['unit']);assert b==bytes(expected)
        assert c['changed_offsets_beyond_original_a8_layout_in_padded_guest']==([hex(i) for i in range(0xa8,0xb8)] if n==10 else [])
    ninth=normal[9];rr=bytes.fromhex(ninth['declared_reply']);bb=bytes.fromhex(ninth['native_output_a8'])
    alias={'declared_ninth_chunk_address_size':list(struct.unpack_from('<QI',rr,0x98)),
        'observed_after_original_translation_address_size':list(struct.unpack_from('<QI',bb,0x98)),
        'tenth_chunk_changed_bytes_beyond_nominal_output':normal[10]['changed_offsets_beyond_original_a8_layout_in_padded_guest']}
    assert alias['declared_ninth_chunk_address_size']!=alias['observed_after_original_translation_address_size']
    for c in cp:
        if c['status'] or c['kind']!=0x8020:
            assert not c['offline_admission']['accepted'] and c['native_output_a8'] is None
            assert c['events'][-1]['reason']=='boundary: before_DMM_diagnostic'
    for c in j['node_cases']:
        assert len(c['nodes'])=={21:7,25:10}[c['mode']]
        assert c['BufferTable_initial_zero_is_independent_input'] and c['native_BufferTable_store_count']>0
        assert c['native_node_producer_executed_with_declared_post_service_and_allocation_inputs']
        assert not c['physical_allocation_mapping_or_ownership_proven'] and not c['actual_MAIN_or_recovery_proven']
        for i,(node,p,row) in enumerate(zip(c['nodes'],c['providers'],c['original_rows'])):
            b=bytes.fromhex(node['native_bytes']);reply=bytes.fromhex(p['declared_reply'])
            expected=bytearray(0x30+16*p['n'])
            nxt=int(c['nodes'][i+1]['address'],16) if i+1<len(c['nodes']) else 0
            struct.pack_into('<IIIIQ',expected,0,row['buffer_kind'],42,42+i,row['unit_type'],nxt)
            struct.pack_into('<H',expected,0x18,p['n']);struct.pack_into('<Q',expected,0x20,int(p['native_translated_numeric_first_address'],16));expected[0x2c]=1
            total=0;used=0
            for k in range(p['n']):
                a,n=struct.unpack_from('<QI',reply,0x18+k*16)
                if not a:break
                struct.pack_into('<QI',expected,0x30+k*16,a,n);total+=n;used+=1
            struct.pack_into('<I',expected,0x28,total)
            assert b==bytes(expected) and node['native_sum']==total and node['nonzero_chunks_copied']==used
    old=json.loads(before)
    for f in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/f['path'])==f['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for f in json.loads(p117.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(result.relative_to(ROOT))
    listings=[]
    for a,z in ((0x2aec74,0x2af13c),(0x2af498,0x2af638),(0x2afb0c,0x2b035c)):
        raw=t.MPR.read(a,z-a);listings.append({'range':[hex(a),hex(z)],'sha256':hashlib.sha256(raw).hexdigest(),
            'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in t.MPR.md.disasm(raw,a)]})
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text())
    contract['schema']='fx3-offline-status-diagnostic-candidate/9';contract['refined_in_stage']=STAGE.name
    contract['DMM_reply_layout_and_node_producer']={
        'native_request_command':0x20,'native_request_bytes':0x28,'original_fixed_output_bytes':0xa8,
        'chunk_count_offset':8,'area_key_offset':12,'chunks_offset':0x18,'chunk_stride':16,
        'extra_numeric_fields_offsets':[0x98,0xa0],
        'extra_values':'[first numeric chunk address + declared global word, declared global word]',
        'GetDmmExtList_frame_bytes':0x120,'GetDmmExtList_temp_offset':0x78,
        'offline_admission_expected_type':0x8020,'offline_admission_status':0,
        'offline_admission_chunk_min':1,'offline_admission_chunk_max':8,
        'admission_requires_full_declared_bytes_and_nonzero_first_chunk':True,
        'max_is_conservative_caller_layout_constraint_not_official_protocol_limit':True,
        'native_9th_descriptor_overlaps_extra_fields':True,'synthetic_10_chunks_exceed_a8_by':16,
        'synthetic_probe_padded_destination_bytes':0x200,'reachable_device_bug_proven':False,
        'node_count_by_declared_mode':{'21':7,'25':10},'native_node_initializer_linker_sum_and_SetMemTbl_executed':True,
        'services_and_malloc_remain_unexecuted_gaps':True,'real_mapping_ownership_MAIN_recording_or_recovery_proven':False}
    contract['next_runtime_acceptance_requirements'].append('identify actual DMM command20/reply8020 producer, enforce available-byte/count/mapping boundaries from trusted runtime data and verify failure cleanup; synthetic reply/node tests cannot authorize live use')
    put(STAGE/'diagnostic-contract.json',contract)
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.prev.front.LIBC.path),'listings':listings,
        'unexecuted_service_plt':{hex(x):t.MPR.plt.get(x,'local diagnostic or direct provider') for x in sorted(stopped)},
        'declared_offset_global_ELF':'0x3d5718','declared_offset_value':hex(t.OFFSET),
        'native_global_word_semantics_are_numeric_only_not_authenticated_runtime_mapping':True,
        'nominal_layout_overlap_and_copy_evidence':alias,'first_vs_formal_source_diff':source_diff,
        'positive_status_diagnostic_continuation_unexecuted_not_claimed_native_rejection':True,
        'node20_is_native_first_plus_offset_not_buffer_end_or_span_proof':True,
        'response_lengths_keys_chunks_allocations_and_zero_BufferTable_are_declared_inputs':True,
        'actual_failure_rollback_service_limits_maps_and_ownership_unproven':True,
        'no_original_binary_or_old_frontend_backend_modified':True,'formal_bounded_phases':140,
        'preserved_first_run_bounded_phases':first['bounded_phases'],'previous_manifest_members_verified':len(prior['files'])})
    review={'status':passed,'created_utc':now,'formal_bounded_phases':140,'response_cases':9,'node_cases':2,'native_nodes':17,
        'preserved_first_run':True,'formal_source_matches_executed_copy':True,
        'same_agent_review_not_independent_engine':True,'stage117_frontend_and_stage75_backend_unchanged':True,
        'actual_camera_Windows_UU_or_service_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_DMM_reply_layout_and_GetDmmExtList_node_construction_with_explicit_service_gaps'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'no_progress',
        'basis':['上一轮状态回复仅复核已存材料与公开项目范围，本轮转入原DMM生产者并增加证据。',
            '140正式有界片段：原命令20构包/回复布局、0/1/2/8/9/10块及状态/类型对照；没有执行OSAL或分配器。',
            '原GetDmmExtList按原表生产17节点，原清零/链接/求和/区域键更新/返回后接SetMemTbl；替换宿主人工拼完整节点，服务输入仍人工声明。',
            '人工9块与附加字段重叠，10块在加大客体容器中超出原布局16字节；候选仅准入1至8且完整字节，服务端可达性/真实上限仍未证。',
            '16项要求状态、权限及原固件/旧前后端不变，MAIN成片与同机恢复独立救援均未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage127_DMM_reply_and_nodes']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json',
        'review':rel+'/completed-evidence-review.json',
        'scope':'Native request/reply layout and original GetDmmExtList builds17 nodes under declared service/malloc inputs; conservative reply bound protects a8 layout. No real allocation, mapping, MAIN or recovery.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage127_scope']='原回复ABI及区域节点生产140正式片段，17原生节点接SetMemTbl；服务/分配输入仍声明，真实映射/所有权/硬件未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Node20 comes from original provider output98 = first numeric chunk plus declared offset; earlier start+span was only a synthetic choice. Original nodes now built by native producer, but all service, address and malloc inputs remain declared.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段127后定位服务侧DMM command20/reply8020处理器，核对块数/长度/映射生产及失败回收；本轮1至8仅保守布局边界，不充官方最大块数或真实分配。仅Mac，16项实录/同机恢复独立救援要求保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']] and len(g['requirements'])==16
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 DMM回复边界与原节点生产](<'+rel+'/README.md>)：140正式片段、17原节点接SetMemTbl；人工9/10块输入暴露布局重叠/复制边界，候选保守拒绝，真实分配/映射/主录与恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage127-DMM-layout-node-producer/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':digest(canonical)},
        'readme_index_before_sha256':hashlib.sha256(ib).hexdigest(),'readme_index_after_sha256':digest(index),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'formal_bounded_phases':140,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
