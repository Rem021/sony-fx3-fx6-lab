#!/usr/bin/env python3
"""Review actual saved native results, preserve scope, then seal stage101."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import receive_snapshot as trial
BASE,ROOT,im=trial.BASE,trial.ROOT,trial.im


def sha(raw):return hashlib.sha256(raw).hexdigest()


def put(path,value):
    with path.open('x') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=trial.PRIOR;assert sha(prior.read_bytes())==trial.PRIOR_SHA
    pm=json.loads(prior.read_text())
    for f in pm['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-upstream-converter-20261027'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'receive_snapshot.py').read_bytes()
    j=json.loads((run/'receive-snapshot-results.json').read_text())
    assert len(j['routes'])==len(j['MID_controls'])==6 and j['bounded_phases']==104
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    for c in j['routes']:
        if c['declared_numeric_state']==3:
            assert c['source_mutation_does_not_change_context_copy'] and c['suspended_original_frames_preserved']
            assert trial.prev.u32(bytes.fromhex(c['lower_envelope_hex']),20)==16000000
            assert trial.prev.u32(bytes.fromhex(c['source_wire_after_hex']),16)==20000000
        elif c['second_receive_fixture']:
            assert c['target_now_at_same_queued_pointer']==20000000
            assert c['reply_word_now_at_same_queued_pointer']==trial.REPLY2
            assert not c['actual_second_delivery_eligibility_race_or_defect_proven']
        else:
            assert c['source_mutation_does_not_change_queued_context_copy']
            assert trial.prev.u32(bytes.fromhex(c['context_snapshot_hex']),8)==16000000
        for e in c['events']:
            assert e['whole_original_image_unchanged'] and e['whole_arena_outside_declared_outputs_unchanged']
            assert e['whole_stack_outside_declared_1280_byte_range_unchanged']
    up=j['upstream_converter'];assert len(up['rows_including_terminator'])==44 and len(up['probes'])==8
    assert not any(x['output']==0x10a for x in up['rows_including_terminator'])
    assert {(x['input_fixture'],x['observed_output']) for x in up['probes']}=={
        (0x520,0x201),(0x529,0x107),(0x530,0x108),(0x531,0x109),
        (0x532,0xffff),(0x10a,0xffff),(0x50a,0),(0x10529,0x107)}
    for p in up['probes']:
        assert p['event']['reason']=='returned' and not p['event']['stores']
        assert p['original_table_and_resolved_slot_unchanged']
    blob=trial.prev.IMAGE.read_bytes();assert sha(blob)==trial.prev.IMAGE_SHA
    av=trial.r.d.AV
    assert sha(av.path.read_bytes())==up['original_ELF_sha256']=='87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26'
    md=trial.r.capstone.Cs(trial.r.capstone.CS_ARCH_ARM64,trial.r.capstone.CS_MODE_LITTLE_ENDIAN)
    def listing(a,z):return {'file_range':[hex(a),hex(z)],'bytes_sha256':sha(blob[a:z]),
        'instructions':[{'file_offset':hex(i.address),'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str}
                        for i in md.disasm(blob[a:z],a)]}
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    put(STAGE/'source-and-scope-audit.json',{
        'created_utc':now,'original_avcam_sha256':sha(blob),'original_ELF_sha256':sha(av.blob),
        'original_ELF_path':str(av.path.relative_to(ROOT)),
        'MID_table':{'offset':'0x36b970','entries':[
            {'MID':hex(0x107+n),'target_file_offset':hex(struct.unpack_from('<Q',blob,0x36b970+n*8)[0]-trial.V)}
            for n in range(4)]},
        'context_snapshot':{'original_copy_file_offset':'0x177dac','source':'input_message+8',
            'copy_bytes':72,'destination':'context+0x358','reply_word_destination':'context+0x3a0',
            'reply_word_source':'original W2 caller argument preserved inW20',
            'reply_name_string_file_offset':'0x41e2d6',
            'reply_name_string':blob[0x41e2d6:blob.index(0,0x41e2d6)].decode(),
            'queue_receives':'context+0x358, not external message pointer in this executed slice'},
        'listings':[listing(a,z) for a,z in ((0x177934,0x177980),(0x177d28,0x177ddc))],
        'upstream_converter':{
            'function':av.dump(0x140eac,0x140eec),'original_table_hex':av.read(0x16aff8,176).hex(),
            'symbol_relocation_slot':'0x1b2678','relocation_type':1025,
            'local_defined_symbol':'_ZN16ObjAvbbcCmnTable16midConvTableToMcE',
            'table_rows_including_terminator':up['rows_including_terminator'],
            'no0x10a_output_in_this_original_table':True,
            'runtime_symbol_interposition_other_routes_and_global_API_absence_not_proven':True},
        'unexecuted_gaps':['task-hook lookup and indirect call','diagnostic/logger bodies','parameter dump17a9a4',
            'full factory/context ownership and normal state transitions','actual MC construction/send/Hal','real MAIN and recovery'],
        'sequential_counterexample_scope':'Second caller-declared delivery reuses same context snapshot before lower busy check. Unknown task-hook/source serialization prevents any actual race/defect conclusion.',
        'prior_stage100_scope_retained':'Pointer queue mechanics and explicit host request mutation still stand within old fixtures; normal receive-copy origin is more specific and must not be replaced by raw external-buffer borrowing.',
        'guest_prototype_or_camera_changed':False})
    review={'status':j['status'],'created_utc':now,'prior_sealed_files_verified':len(pm['files']),
        'receive_route_cases':6,'MID_controls':6,'converter_probes':8,'bounded_phases':104,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'natural_MAIN_policy_actual_encoding_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT))
    result_rel=str((run/'receive-snapshot-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_QoS_receive_context_snapshot_and_upstream_converter_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':[
            'stage100的15件封存/canonical核对；无Windows/UU/相机操作。',
            '原MID表107..10a分派；原48字节复制到context358并保存W2回复字到3a0，原尾声把上下文副本送入状态机。任务hook/日志/打印仍为明确间隙，非正常接收验收。',
            '外部输入16->20M明确宿主变更后，上下文/队列/原下层54字节封套仍16M；正常路径局部指向上下文副本，不能推广为直接借外部缓冲。',
            '重复交付fixture先复用同一context副本及回复字，后到下游忙检查；实际串行约束/可达调度未证，不认定相机竞态。',
            '原libInfraAvbbc64字节转换函数及176字节原表/本地重定位核对，8探针完整返回；该表输出无10a，不能从已有相邻映射推导可调用码率入口。其它API/库/直接MC/符号替换未排除。',
            '12接收/分派对照96阶段加8转换探针共104阶段；全部16项要求/授权/stage75原型保持，实录及恢复未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage101_receive_snapshot_converter_boundary']={
        'readme':rel+'/README.md','result':result_rel,'source_audit':rel+'/source-and-scope-audit.json',
        'review':rel+'/completed-evidence-review.json',
        'scope':'Native MID demux/context-local48-byte snapshot+reply word with explicit hook/log/dump gaps; original local-bound converter table has no0x10a result. Real producer/MAIN/serialization/Hal/recovery unproved.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage101_scope']='原接收片段先复制48参数及回复字到context358；队列指向该副本。重复交付/串行代次仍需绑定；原库当前本地转换表无10a输出，不能直接推导现有上层入口。真实MAIN/Hal/模块退出未证，状态保持。'
    g.setdefault('provenance_refinements',[]).append({
        'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Original receive slice copies source48+reply into context-local4c before event delivery; stage100 pointer mechanics do not establish direct borrowing of external wire. Repeated declared delivery can reuse context before queue busy check, with real serialization unproved. Current original locally-bound converter table has no0x10a result, not global API absence.',
        'actual_MAIN_policy_normal_serialization_or_recovery_proven':False})
    g['next_safe_offline_actions'].append(
        'stage101后追原上层其它调用路径/实际符号绑定及合法配置代次；已核对libInfraAvbbc的本地midConvTableToMc原表无10a，不要将532/直接10a或相邻映射当可用接口。接收参数副本来自context358、回复字3a0，任务hook及真正串行/工厂/状态来源未运行；先解决生产者/重复交付约束，不重做外部缓冲即队列参数的假设。仍仅Mac，全部实录和同机恢复要求保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint',
          'external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();txt=ib.decode();marker='## 相机与固件研究\n'
    assert txt.count(marker)==1
    entry='- [2026-10-27 FX3 接收参数副本与上层转换边界](<'+rel+'/README.md>)：原48字节上下文副本/回复关联及复用范围，12对照加8原转换探针，共104阶段；当前原转换表无10a，真实MAIN生产者/实录/恢复仍未证，仅Mac。'
    assert entry not in txt
    updated=txt.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
    put(STAGE/'final-receipt.json',{
        'schema':'fx3-stage101-native-QoS-receive-context-snapshot/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':trial.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,
        'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
        'bounded_phases':104,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
