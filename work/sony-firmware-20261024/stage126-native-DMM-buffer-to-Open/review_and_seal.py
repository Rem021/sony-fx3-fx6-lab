#!/usr/bin/env python3
"""Seal native buffer-to-Open field lineage, with explicit allocation gaps."""
from pathlib import Path
import copy,datetime,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import buffer_open as t
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
    out=STAGE/'run-native-buffer-Open-20261027';p=out/'buffer-Open-results.json';j=json.loads(p.read_text())
    assert j['status']=='PASS_NATIVE_DMM_BUFFER_FIELDS_TO_OPEN_CALLER_NOT_PHYSICAL_ALLOCATION'
    assert j['source_sha256']==digest(STAGE/'buffer_open.py') and (out/'executed-source.py').read_bytes()==(STAGE/'buffer_open.py').read_bytes()
    assert j['native_frontend_source_result_sha256']==digest(t.PREVIOUS_RESULT)
    assert len(j['cases'])==8;ev=[e for c in j['cases'] for e in c['events']];assert len(ev)==j['bounded_phases']==160
    for k in ('goal_complete','persistent_write_release','camera_Windows_UU_operations','actual_DMM_allocation_MAIN_recording_or_recovery_proven'):assert not j[k]
    for e in ev:
        assert all(e[k] for k in ('stack_outside2048_unchanged','scratch_outside_outputs_unchanged','images_outside_declared_data_outputs_unchanged'))
        assert not e['actual_lock_check_log_setter_completion_or_device_executed']
    forbidden={0x7dfa0,0xc8c70,0x7c350,0xd1c84,0x7efd0}
    for e in ev:assert not forbidden.intersection(int(pc,16) for pc in e['pcs'][:-1])
    mappings=[]
    for c in j['cases']:
        assert all(c[k] for k in ('runtime_area_list_addresses_sizes_and_Model_source_are_explicit_fixtures',
            'all_real_locks_logs_prior_DMM_work_queue_access_and_Codec_Open_unexecuted'))
        assert not c['actual_DMM_allocation_physical_buffer_ownership_encoder_or_file_proven']
        table=bytes.fromhex(c['native_BufferTable760']);req=bytes.fromhex(c['native_Enqueue_request7b8'])
        assert len(table)==0x760 and len(req)==0x7b8 and req[:0x760]==table
        assert struct.unpack_from('<3I',req,0x764)==(6,6,3)
        assert c['declared_runtime_node_count']=={21:7,25:10,31:13,32:19}[c['declared_mode']]
        if c['proxy_enabled']:
            assert c['native_single_Open98'] is None and c['dual_Open_unexecuted'] and not c['original_single_Open_clear_executed']
        else:
            raw=bytes.fromhex(c['native_single_Open98']);assert len(raw)==0x98 and c['original_single_Open_clear_executed']
            assert struct.unpack_from('<HH',raw,0x68)==(1920,1080) and raw[0x66]==15 and raw[0x82]==22 and raw[0x94:0x96]==b'\0\1'
            vals={struct.unpack_from('<Q',table,i)[0]:i for i in range(0,len(table)-7,8)}
            pairs=[{'Open_offset':hex(i),'BufferTable_offset':hex(vals[v]),'declared_numeric_value':hex(v)}
                for i in range(len(raw)-7) if (v:=struct.unpack_from('<Q',raw,i)[0]) in vals and 0x70000000<=v<0x200000000]
            assert len(pairs)>=7
            mappings.append({'seed':c['seed'],'mode':c['declared_mode'],'numeric_field_matches_not_physical_address_proof':pairs})
    for mode in (21,25):
        raws=[c['native_single_Open98'] for c in j['cases'] if c['declared_mode']==mode];assert len(raws)==2 and raws[0]==raws[1]
    old=json.loads(before)
    for x in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/x['path'])==x['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for x in json.loads(p117.read_text())['files']:
        q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and digest(q)==x['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(p.relative_to(ROOT))
    contract=json.loads((t.PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/8';contract['refined_in_stage']=STAGE.name
    contract['buffer_to_Open_lineage']={'mode_unit_counts':{'21':7,'25':10,'31':13,'32':19},
        'original_unit_table_rows_preserved':True,'actual_runtime_nodes_are_declared_not_allocator_outputs':True,
        'native_SetMemTbl_output_bytes':0x760,'native_Enqueue_prefix_matches_BufferTable':True,
        'declared_Model_metadata40_44':'[1,proxy_enabled] supplied independently of sealed frontend parameter bytes',
        'single_stream_original_clear_bytes':0x98,'single_stream_known_old_fill_independence_modes':[21,25],
        'single_stream_core':{'geometry':[1920,1080],'video_byte66':15,'quality_byte82':22,'chroma94':0,'depth95':1},
        'dual_stream_setup_unexecuted_modes':[31,32],
        'numeric_address_field_propagation_not_DMA_MMU_or_ownership_proof':True,
        'complete_valid_Open_or_16M_MAIN_encoding_proven':False}
    contract['next_runtime_acceptance_requirements'].append('verify actual DMM-produced node addresses/sizes/leases and full healthy Model metadata before using buffer/Open field lineage; original clear98 removes old-fill dependence only in the tested single-stream caller')
    put(STAGE/'diagnostic-contract.json',contract)
    ranges=((0x2afb0c,0x2b035c),(0xd6700,0xd67bc),(0xd18d8,0xd1954),(0xd1b80,0xd1bc0),
        (0xd13f8,0xd18d8),(0x2af498,0x2af638),(0x2b035c,0x2b0408))
    listings=[{'range':[hex(a),hex(z)],'bytes_sha256':sha(t.MPR.read(a,z-a)),
        'disassembly':[{'pc':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
            for i in t.MPR.md.disasm(t.MPR.read(a,z-a),a)]} for a,z in ranges]
    put(STAGE/'source-and-scope-audit.json',{'created_utc':now,'original_MPR_sha256':digest(t.MPR.path),
        'original_libc_sha256':digest(t.front.LIBC.path),'listings':listings,'numeric_field_matches':mappings,
        'declared_global_head_input':'mp_AreaExtListStart points to explicit guest nodes; no actual GetDmmExtList/allocation.',
        'native_single_Open_clear_removes_old_fill_dependence_only_under_declared_inputs':True,
        'stage106_historical_unwritten_bytes_not_retroactively_claimed_initialized':True,
        'dual_stream_branch_observed_then_stopped_not_executed_as_single_stream':True,
        'no_real_region_mapping_DMM_allocation_all_lock_logs_or_Codec_Open':True,
        'original_FX3_files_and_old_frontend_backend_unchanged':True,'bounded_phases':160})
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'cases':8,'single_stream_cases':4,'dual_branch_stop_cases':4,'bounded_phases':160,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'actual_camera_Windows_UU_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_DMM_buffer_table_to_Enqueue_Open_and_original_single_caller_clear_construct_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段125十件封存/canonical核验；8例160原片段，无设备/Windows操作。',
            '原表21/25/31/32取7/10/13/19映射项，人工运行链表经SetMemTbl和Enqueue原复制/类别填充进入Open请求。',
            '原单流调用者clear98+构建器得到HD42010字段，两旧值背景输出一致；补特定旧值依赖缺口，不充实际分配/完整有效请求。',
            '代理开启按原分支止于双流准备，未强行套单流；真实区域地址/Model元数据/硬件消费仍缺。',
            '16项状态、权限及原固件/旧前后端保持，实际16M成片与同机恢复仍未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage126_buffer_Open_lineage']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'160 bounded phases trace declared runtime area nodes through native SetMemTbl/Enqueue to original single-stream clear98 and Open construction. Real allocation, Model metadata, dual construction and hardware/16M remain unproven.',
        'authorization_unchanged':True,'stage75_backend_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/diagnostic-contract.json'])
            req['stage126_scope']='原区域表种类/SetMemTbl/Enqueue与单流Open clear98及构建160阶段，单流旧值依赖补齐于声明输入范围；实际地址/分配/元数据和硬件16M编码未验，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Native buffer fields from declared area nodes pass through SetMemTbl and Enqueue, then the original single-stream caller actually clears98 and constructs HD42010 fields independent of old fill. Physical allocation, full metadata, dual path and hardware validity remain unproven.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段126后沿真实GetDmmExtList/区域分配和错误路径核对链表生产及地址/大小/租期，绑定完整Model元数据、MAIN资源FH/16M及Open实际消费；已测单流clear98不充完整有效请求，代理双流未执行。仅Mac，16项实录/同机恢复独立救援要求保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 缓冲字段到原Open调用者](<'+rel+'/README.md>)：8例160片段接原SetMemTbl/Enqueue与单流clear98构建，补特定旧值依赖；人工区域/元数据非物理分配，实录及恢复未验。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(q.relative_to(ROOT)),'bytes':q.stat().st_size,'sha256':digest(q)} for q in sorted(STAGE.rglob('*')) if q.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage126-buffer-to-Open/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':t.PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),'readme_index_entry':entry,
        'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'bounded_phases':160,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
