#!/usr/bin/env python3
"""Review native Dataflow/libc scope and retain every real-device gate."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import dataflow_copy as t
BASE,ROOT=t.BASE,t.ROOT


def sha(data):return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while chunk:=f.read(8*1024*1024):h.update(chunk)
    return h.hexdigest()


def put(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def needed(native):
    return [x.needed for s in native.elf.iter_sections() if s.name=='.dynamic'
        for x in s.iter_tags() if x.entry.d_tag=='DT_NEEDED']


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert file_sha(t.PRIOR)==t.PRIOR_SHA
    pm=json.loads(t.PRIOR.read_text())
    for f in pm['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and file_sha(p)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    receipts=[]
    for name in ('extraction-receipt.json','libc-extraction-receipt.json'):
        item=json.loads((STAGE/name).read_text())
        for path,expected in ((item['source_image'],item['source_sha256']),(item['output'],item['output_sha256'])):
            p=ROOT/path;assert p.is_file() and not p.is_symlink() and file_sha(p)==expected
        assert item['read_only_regular_file_extraction']
        if 'reader' in item:assert file_sha(ROOT/item['reader'])==item['reader_sha256']
        receipts.append(name)
    run=STAGE/'run-native-payload-and-header-20261027';j=json.loads((run/'dataflow-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'dataflow_copy.py').read_bytes()
    assert (len(j['messages']),len(j['AV_consumers']),len(j['MPR_payload_copies']),j['bounded_phases'])==(8,4,4,64)
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    assert not j['actual_ReceiveASync_process_mapping_main_record_or_recovery_proven']
    assert j['partial_header_controls_not_forwarded_to_AV'] and j['native_memcpy_memset_no_output_or_return_adapters']
    assert file_sha(ROOT/j['header_source'])==j['header_source_sha256']
    assert file_sha(ROOT/j['profile_source'])==j['profile_source_sha256']
    messages=j['messages'];consumers=j['AV_consumers'];senders=j['MPR_payload_copies']
    assert [(x['declared_stored_len'],x['declared_capacity'],x['copied_len']) for x in messages]==[(48,48,48),(48,48,48),(16,48,16),(48,16,16)]*2
    assert sum(x['header_complete'] for x in messages)==4
    for x in messages:
        assert x['native_state_length_srcid_and_stored_payload_cleared']
        assert x['events'][4]['return_u32_if_returned']==0 and x['events'][5]['return_u32_if_returned']==0xffffffe5
        assert x['same_firmware_imports_in_execution_order']==['memcpy','memcpy','memset']
        assert not x['actual_ReceiveASync_transport_Sony_loader_payload_ownership_or_runtime_mapping_proven']
        assert bytes.fromhex(x['received38_before_prefix_hex'])[8:8+x['copied_len']]==bytes.fromhex(x['original_header30_hex'])[:x['copied_len']]
    for i,x in enumerate(consumers):
        assert x['declared_view']==i%2 and x['native_loaded_virtual_pointer']==hex(t.VBASE)
        assert x['native_selected_opaque_tag']==hex(0x805720f9 if i%2 else 0x805700f9)
        assert x['two_vcall_targets_explicit_zero_and_both_calls_unexecuted']
        assert x['post_vcall_phase_is_independent_input_not_fabricated_vcall_return']
        assert not x['actual_process_map_ParameterControl_admission_Open_or_hardware_proven']
        assert bytes.fromhex(x['command38_hex'])[8:]==bytes.fromhex(messages[(i//2)*4+i%2]['original_header30_hex'])
    for x in senders:
        assert x['source_raw_unchanged_and_native_copy_byte_exact']
        assert not x['actual_fixed_mapping_OSAL_transport_or_live_buffer_ownership_proven']
        assert len(bytes.fromhex(x['copied_raw98_hex']))==0x98
    events=[e for x in messages+consumers+senders for e in x['events']]
    assert len(events)==64
    for e in events:
        assert e['whole_stack_outside_declared_512_bytes_unchanged']
        assert e['whole_scratch_outside_declared_outputs_unchanged']
        assert e['whole_original_relocated_images_unchanged']
        assert not e['output_return_logging_or_vcall_adapters']
        if e['reason']=='returned':assert e['callee_saved_X19_X29_D8_D15_preserved_on_complete_return']
        assert not any(int(pc,16) in (0x3109c,0xb2998,0xb29d8) for pc in e['pcs'][:-1])
    # Original function class, not host IFUNC resolution or a replacement routine.
    libc_symbols={s.name:s for s in t.LIBC.elf.get_section_by_name('.dynsym').iter_symbols() if s.name in ('memcpy','memset')}
    assert all(libc_symbols[n]['st_info']['type']=='STT_FUNC' for n in ('memcpy','memset'))
    assert 'dataflowInfraFramework.so' in needed(t.AV) and 'libc.so.6' in needed(t.DF)
    get_name=t.AV.plt[0x9bd70];assert get_name=='_ZN16DataflowInfraMsg6GetMsgEPvt'
    assert t.DF.symbols[get_name]=={'va':0x32070,'size':292}
    # Earlier successful intermediate run is retained under its own executed source.
    first=json.loads((STAGE/'run-original-libraries-20261027/dataflow-results.json').read_text())
    assert first['bounded_phases']==60 and not first['goal_complete']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    def listing(native,a,z):
        return {'library':native.path.name,'VA_range':[hex(a),hex(z)],
            'original_bytes_sha256':sha(native.read(a,z-a)),
            'original_disassembly':native.dump(a,z) if hasattr(native,'dump') else native.disasm(a,z)}
    audit={'created_utc':now,'extraction_receipts':receipts,'source_images_and_regular_files_rehashed':True,
        'original_hashes':{'Dataflow':t.DF_SHA,'libc':t.LIBC_SHA,'AV':sha(t.AV.blob),'MPR':sha(t.MPR.blob)},
        'original_needed':{'Dataflow':needed(t.DF),'AV':needed(t.AV),'libc':needed(t.LIBC)},
        'original_binding':{'AV_PLT_GetMsg':'0x9bd70','Dataflow_GetMsg':'0x32070',
            'Dataflow_memcpy_PLT':'0x30460','Dataflow_memset_PLT':'0x30760','MPR_memcpy_PLT':'0x7b9d0',
            'libc_memcpy':t.LIBC.symbols['memcpy'],'libc_memset':t.LIBC.symbols['memset'],
            'libc_guest_load_bias':hex(t.CBASE),'symbols_STT_FUNC_not_IFUNC':True,
            'binding_is_declared_guest_fixture_not_actual_dynamic_loader_evidence':True},
        'state_and_length':{'raw_global_state':2,'state_offset':'0x8','length_u16_offset':'0xc',
            'srcid_offset':'0x10','inline_payload_offset':'0x18','maximum_SetGlobalMsg_length':383,
            'native_GetMsg_raw_copy':'min(stored length, request capacity); returns0 then clears stored message',
            'state0_repeat_return':-27,'structured_state1_not_conflated':True},
        'pointer_and_ViewId':{'MPR_payload_physical_domain':'header+8','MPR_payload_virtual_domain':'header+28',
            'AV_virtual_domain':'CMD+30','AV_native_raw_field_read':'raw+64',
            'ViewId':'header+1a / CMD+22','opaque_tags':['0x805700f9','0x805720f9'],
            'hardware_channel_identity_not_bound':True},
        'independent_inputs':['Original stage107 headers from declared fixed mapping.',
            'Original stage106 target raw98, still contains unbound buffers and 51 old-value bytes.',
            'Post-CreateMessage MPR frame and raw source for bounded original memcpy slice.',
            'Inter-guest byte handoff; no actual ReceiveASync/OSAL/process map.',
            'Readable ParameterControl graph with two zero targets; stop before both calls.',
            'Post-first-vcall original segment is separate input, not a fabricated vcall return.'],
        'logger_scope':'Original Seterr_general returns natively before backend for observed0/-27. No logger adapter; other paths unproved.',
        'ownership_scope':'Message clear only clears inline metadata. Fixed raw98 pool ownership, mapping, serialization and response lifetime still unproved.',
        'original_listings':[listing(t.DF,a,z) for a,z in ((0x31f58,0x32210),(0x3128c,0x31318))]+
            [listing(t.LIBC,t.LIBC.symbols[n]['va'],t.LIBC.symbols[n]['va']+t.LIBC.symbols[n]['size']) for n in ('memcpy','memset')]+
            [listing(t.AV,a,z) for a,z in ((0x138e78,0x138fa0),(0xb2958,0xb29dc))]+[listing(t.MPR,0x282d6c,0x282da0)],
        'source_and_scope_only_not_actual_MAIN16M_backup_restore_or_rescue':True}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(pm['files']),
        'message_cases':8,'complete_header_AV_consumers':4,'native_raw98_copies':4,'bounded_phases':64,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'original_source_images_libraries_and_code_rehashed':True,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT));result_rel=str((run/'dataflow-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_Dataflow_libc_copy_clear_and_AV_virtual_pointer_consumption'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['重启后核对阶段107的17件封存与canonical；阶段108两份原库已提取，不重复提取；没有遗留研究进程。',
            '从既有镜像提取的原Dataflow库与同固件libc复核；原STT_FUNC memcpy/memset有界执行，只有声明的PC导入绑定，无输出/返回补写。',
            '原MPR参数复制完整152字节；原Dataflow48字节复制/Clear/来源ID和状态清理、重复空读-27；16/48截断对照返回0但不转交AV。',
            '原AV从CMD+30取虚拟指针并读raw+64，ViewId0/1选两个不透明值；两个ParameterControl虚调用停止且未假造返回。共64有界阶段。',
            '重新核对公开FX3请求、A7CII失败/应用模式恢复和A7IVboot0例外，仍无本机FX3独立救援验收。',
            '原MAIN生产者缺VPC6、FH/16M资源、真实消息/映射/生命周期/硬件及同机恢复仍缺；全部16项状态、权限及阶段75不可部署原型保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage108_original_Dataflow_and_libc']={'readme':rel+'/README.md','result':result_rel,
        'source_audit':rel+'/source-and-scope-audit.json','public_sources':rel+'/public-source-notes.json',
        'review':rel+'/completed-evidence-review.json',
        'scope':'64 native bounded phases: original same-firmware memcpy/memset, MPR152-byte copy, Dataflow48-byte copy/clear, truncation controls, independent AV virtual-pointer read; no live transport, mapping, ParameterControl calls, hardware or recovery.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G11'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage108_scope']='同固件原libc/Dataflow完成声明消息和参数复制/清理；AV读取虚拟域及ViewId标签。完整消息路径/当前对象/硬件/16M资源及上游自然MAIN仍未证；状态保持，不可上机提交。'
        if req['id'] in ('G15','G16'):
            req['evidence'].append(rel+'/public-source-notes.json')
            req['stage108_scope']='复查原公开失败、应用模式恢复及A7IVboot0限制；不是FX3同机受限恢复回读或独立救援证据，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Original same-firmware libc now executes the previously unexecuted MPR payload memcpy in an independent declared post-constructor frame. Original Dataflow raw/global setter/GetMsg/Clear executes separately; AV consumes their exact produced bytes in another guest. This refines earlier copy gaps, not actual transport, process mapping, instance or buffer lifetime.',
        'truncation_scope':'Raw/global GetMsg returns0 after min-length copy and message clear; partial controls were never passed to AV and are not evidence of real camera malformed transport.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段108后追ReceiveASync/OSAL实际成帧与SetGlobalMsg来源、原ParameterControl两个虚调用的对象/vtable和功能、固定参数区实际映射/序列化/回复寿命。保留MAIN生产者缺VPC6与quality22/FH对16M资源匹配缺口；GetMsg返回0不能证明完整48B。仅Mac，全部实机主录/音画/长录/同机备份恢复及独立救援门槛保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint','external_dependencies',
        'current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原消息库与参数复制](<'+rel+'/README.md>)：同固件原memcpy/memset、Dataflow复制/清理、截断对照和AV虚拟指针消费64阶段；硬件与恢复未验收，仅Mac。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':file_sha(p)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage108-original-Dataflow-copy/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':file_sha(STAGE/'final-receipt.json'),
        'bounded_phases':64,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
