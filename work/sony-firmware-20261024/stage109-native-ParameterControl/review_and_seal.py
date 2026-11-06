#!/usr/bin/env python3
"""Seal parameter-storage evidence without converting guest scope to runtime proof."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import parameter_control as t
BASE,ROOT=t.BASE,t.ROOT


def sha(data):return hashlib.sha256(data).hexdigest()


def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while data:=f.read(8*1024*1024):h.update(data)
    return h.hexdigest()


def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert file_sha(t.PRIOR)==t.PRIOR_SHA
    prior=json.loads(t.PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and file_sha(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    receipt=json.loads((STAGE/'extraction-receipt.json').read_text())
    for path,digest in ((receipt['source_image'],receipt['source_sha256']),(receipt['reader'],receipt['reader_sha256']),(receipt['output'],receipt['output_sha256'])):
        p=ROOT/path;assert p.is_file() and not p.is_symlink() and file_sha(p)==digest
    assert receipt['read_only_regular_file_extraction'] and not receipt['mount_or_native_host_execution']
    run=STAGE/'run-original-table-and-storage-20261027';j=json.loads((run/'parameter-control-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'parameter_control.py').read_bytes()
    assert file_sha(ROOT/j['source'])==j['source_sha256'] and file_sha(t.MWF.path)==j['original_MWF_sha256']==t.MWF_SHA
    assert (len(j['cases']),len(j['negative_missing_parameter']),len(j['original_table_prefix']),j['bounded_phases'])==(4,4,2,62)
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    assert not j['actual_mutex_malloc_new_free_or_return_output_success_adapters_executed']
    for c in j['cases']:
        assert c['command38_hex']==c['temporary38_hex']==c['Struct_storage38_hex']
        assert c['Struct_value_pointer']==hex(t.OWNED) and c['Struct_length']==56 and c['Struct_opaque_extra']==0
        assert c['original_blob_setter_slot60']=='0xa37a0' and c['original_bool_setter_slot10']=='0xa32b4'
        assert c['native_bool1057']==1 and c['nested_raw_virtual_pointer_retained']==hex(t.VBASE)
        assert c['raw98_unchanged_and_not_part_of_56_byte_Struct_copy']
        assert c['post_mutex_allocator_free_entries_are_independent_inputs_not_success_returns']
        assert not c['actual_parameter_map_population_allocation_synchronization_or_raw_buffer_lifetime_proven']
        assert not c['full_SetParameter_MAIN16M_hardware_or_recovery_proven']
        assert len(c['original_ABS64_vtable_relocations'])==25
        assert all(x['kind']==257 for x in c['original_ABS64_vtable_relocations'])
        assert len(c['events'])==11
        pcs={int(pc,16) for e in c['events'] for pc in e['pcs']}
        assert {0xb2998,0xa37a0,0xb29d8,0xa32b4,t.WBASE+0x2f778,t.WBASE+0x2e940}<=pcs
        assert any(t.CBASE+0x7aad0<=p<t.CBASE+0x7acdc for p in pcs)
        assert any(t.CBASE+0x7a380<=p<t.CBASE+0x7a558 for p in pcs)
    for c in j['negative_missing_parameter']:
        assert c['original_GetParam_returned_null'] and c['no_parameter_store_or_allocator_branch']
        assert c['original_wrapper_returned_after_independent_mutex_gaps']
        assert c['original_callsite_has_no_return_admission_check'] and not c['actual_camera_missing_parameter_or_mutex_effects_proven']
        assert len(c['events'])==4
    for c in j['original_table_prefix']:
        assert c['first_original_record']==[0x1001,11,56] and c['native_first_Struct_allocation_requested_bytes']==56
        assert not c['actual_new_AddParam_map_population_or_runtime_instance_proven'] and len(c['events'])==1
    events=[e for c in j['cases']+j['negative_missing_parameter']+j['original_table_prefix'] for e in c['events']]
    assert len(events)==62
    stopped=set()
    for e in events:
        assert e['whole_stack_outside_declared_512_bytes_unchanged'] and e['whole_scratch_outside_declared_outputs_unchanged']
        assert e['whole_original_relocated_images_unchanged'] and not e['output_return_logging_or_vcall_adapters']
        if e['reason']=='returned':assert e['callee_saved_X19_X29_D8_D15_preserved_on_complete_return']
        else:stopped.add(e['reason'])
    assert {'boundary: before_unexecuted_malloc','boundary: before_unexecuted_free',
        'boundary: before_unexecuted_array_new','boundary: before_unexecuted_mutex_lock',
        'boundary: before_unexecuted_mutex_unlock'}<=stopped
    for dirname,phases in (('run-original-vcalls-20261027',44),('run-original-vcalls-and-missing-keys-20261027',60)):
        old=json.loads((STAGE/dirname/'parameter-control-results.json').read_text())
        assert old['bounded_phases']==phases and not old['goal_complete']
    table=t.AV.read(0x1b62b0,0x414);rows=[list(struct.unpack_from('<3I',table,o)) for o in range(0,len(table),12)]
    assert len(rows)==87 and rows[-1]==[0x1000,2,0]
    assert [x for x in rows if x[0] in (0x1001,0x1057)]==[[0x1001,11,56],[0x1057,0,1]]
    # Raw table type0 branch points to the original bool constructor case.
    delta=struct.unpack('<h',t.AV.read(0x141dfc,2))[0]
    assert 0xa3ee4+4*delta==0xa3ee4
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def listing(n,a,z):return {'library':n.path.name,'VA_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(n.read(a,z-a)),'original_disassembly':n.dump(a,z)}
    audit={'created_utc':now,'original_MWF_sha256':t.MWF_SHA,'extraction':'extraction-receipt.json',
        'original_AV_sha256':sha(t.AV.blob),'original_libc_sha256':sha(t.LIBC.blob),
        'ABI_primary_source':{'url':'https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst',
            'checked_date':'2026-10-27','rule':'R_AARCH64_ABS64 numeric257 stores S+A in64bits.',
            'scope':'Official Arm ABI. No exact current commit or Sony runtime symbol-preemption claim.'},
        'vtable':{'symbol':t.VT,'symbol_record':t.AV.symbols[t.VT],'vptr':'0x1a70f0',
            'original_ABS64_entries':j['cases'][0]['original_ABS64_vtable_relocations'],
            'slot60_blob_setter':'0xa37a0','slot10_bool_setter':'0xa32b4',
            'prior_limited_helper_did_not_resolve_ABS64_and_prior_zero_targets_were_explicit_controls':True},
        'original_MovieEncoder_constructor':{'callsite':'0xad5a0','parameter_table_VA':'0x1b62b0',
            'owner_ID_argument':'0x80550122','controller_store_at_parent':'this+0x80',
            'whole_constructor_allocation_actual_map_population_and_instance_binding_not_executed':True},
        'original_PARAMETER_TABLE':{'VA':'0x1b62b0','raw_hex':table.hex(),'sha256':sha(table),
            'active_records':86,'records_including_terminator':rows,'raw_type0_bool_branch':'0xa3ee4',
            'raw_type11_Struct_branch':'0xa40f0','third_field_not_assumed_to_be_live_or_default_value':True},
        'declared_graph_scope':'Original ctor creates empty ObjMsg. Original Struct/bool ctors create typed values. Populated ObjMsgBody and sorted two-entry ParamMap are independent inputs, not actual AddParam initialization.',
        'independent_gaps':['pthread_mutex_lock','pthread_mutex_unlock','malloc temporary56','new[] Struct56','free temporary56'],
        'ownership':'Original wrapper and Struct each memcpy exactly56 command bytes. Nested CMD+30 retains the external raw98 virtual pointer; no deep raw98 copy. Allocator/mutex/previous value deletion and actual lifetime unproved.',
        'negative_scope':'Missing1001/1057 declared controls return without store under debug0 after independent mutex gaps. Original SetParameter callsites do not check setter returns. This does not mean real FX3 lacks those parameters.',
        'original_listings':[listing(t.AV,a,z) for a,z in ((0xa32b4,0xa332c),(0xa37a0,0xa386c),
            (0xa3d98,0xa417c),(0xad584,0xad5ac),(0xb2958,0xb29e4))]+
            [listing(t.MWF,t.MWF.symbols[n]['va'],t.MWF.symbols[n]['va']+t.MWF.symbols[n]['size']) for n in t.NAMES],
        'no_runtime_MAIN16M_hardware_backup_restore_or_independent_rescue_proven':True}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'previous_manifest_members_verified':len(prior['files']),
        'storage_cases':4,'missing_key_controls':4,'original_table_prefix_controls':2,'bounded_phases':62,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'all_native_virtual_calls_bound_to_original_symbols':True,
        'all_mutex_allocators_free_remain_stops_with_independent_later_inputs':True,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));rr=str((run/'parameter-control-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_ParameterControl_vtable_MWF_storage_and_nested_pointer_lifetime'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段108的16件封存、canonical和目标卷重新核对；仅Mac，原MWF库从既有校验镜像只读提取。',
            '原虚表25项ABS64按Arm ABI解析，原构造器生成vptr；两处虚调用实质为1001命令56B和1057布尔setter。',
            '原MovieEncoder构造传1b62b0表及80550122；原表86活动行含1001/11/56及1057/0/1。原表首行执行到56B new[]请求，未模拟成功。',
            '声明映射下原MWF二分查找、命令两次56B memcpy、Struct字段与bool存储执行；CMD+30仍引用外部raw98，不是深层参数快照。',
            '缺项控制原setter不写入即可返回，调用点未检查返回；后续诊断需条目和内容回读。锁/分配/free始终停止，后段独立输入，62阶段不证明同步/生命周期/真实实例。',
            '原MAIN来源、FH/16M、实际硬件成片/音画/长录及同机恢复仍缺；16项状态、权限和阶段75不可部署原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage109_ParameterControl_storage']={'readme':rel+'/README.md','result':rr,
        'source_audit':rel+'/source-and-scope-audit.json','review':rel+'/completed-evidence-review.json',
        'scope':'62 bounded phases resolve original two virtual calls, original MovieEncoder table and MWF lookup/copies under declared graph. Header storage retains external raw pointer; mutex/allocator/free/real instance and hardware remain unproved.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json'])
            req['stage109_scope']='原ParameterControl两虚调用与MovieEncoder原表绑定、原MWF查找/Struct56B复制和缺项对照；声明图不代表当前对象，锁/分配/释放及外部raw98寿命未证，不能提交或当硬件准入。状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original local ABS64 vtable targets refine stage108 explicit zero-vcall boundaries. Original MovieEncoder table includes Struct command1001 length56 and bool1057. Native storage copies the command structure twice, retaining its raw98 pointer; it does not deep-copy the external payload. Declared map population and independent mutex/allocation/free gaps are not current-object, synchronization or lifetime proof.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段109后追原AddParam与控制对象初始化/编码实例绑定；结合原MovieEncoder参数表核对查询/回读的ID与类型，不把setter返回当写入成功。核对ReceiveASync/OSAL成帧、固定raw98参数区映射/外层同步/回复寿命；Struct56B保存仍保留CMD+30外部指针。保持MAIN自然来源及FH/16M资源缺口，仅Mac，实机和同机恢复/独立救援门槛不变。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原参数控制与外部参数寿命](<'+rel+'/README.md>)：原虚表、MovieEncoder参数表、MWF存储及缺项对照62阶段；56B命令复制仍引用外部raw98，锁/分配和实机验收保持未证，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':file_sha(p)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage109-ParameterControl/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':file_sha(STAGE/'final-receipt.json'),
        'bounded_phases':62,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
