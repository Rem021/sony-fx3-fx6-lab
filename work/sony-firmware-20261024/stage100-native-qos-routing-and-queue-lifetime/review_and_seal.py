#!/usr/bin/env python3
"""Review bounded evidence and preserve full goal/authorization before seal."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import qos_routing as trial
BASE,ROOT,im = trial.BASE,trial.ROOT,trial.im


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path,value):
    with path.open('x') as f:
        json.dump(value,f,ensure_ascii=False,indent=2)
        f.write('\n')


def main():
    im.volume()
    assert not (STAGE/'final-receipt.json').exists()
    prior = trial.PRIOR
    assert sha(prior.read_bytes()) == trial.PRIOR_SHA
    manifest = json.loads(prior.read_text())
    for f in manifest['files']:
        raw = (ROOT/f['path']).read_bytes()
        assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
    before = (STAGE/'goal-status-before.json').read_bytes()
    canonical = BASE/'GOAL_STATUS.json'
    assert before == canonical.read_bytes() == (prior.parent/'goal-status-after.json').read_bytes()
    blob = trial.IMAGE.read_bytes()
    assert sha(blob)==trial.IMAGE_SHA
    run = STAGE/'run-state21-corrected-coupled-20261027'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'qos_routing.py').read_bytes()
    j = json.loads((run/'qos-routing-results.json').read_text())
    assert len(j['routes'])==10 and len(j['queues'])==4 and len(j['state_cases'])==18
    assert j['bounded_phases']==118 and j['image_sha256']==trial.IMAGE_SHA
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    for c in j['routes']:
        assert c['pending_original_action_frame_preserved_by_separate_lower_stack']
        if c['timing_update_fixture']:
            assert c['envelope_before_unexecuted_constructor_hex'] is None
        else:
            raw=bytes.fromhex(c['envelope_before_unexecuted_constructor_hex'])
            assert raw[12:]==bytes.fromhex(c['request_hex'])[:0x48]
            assert struct.unpack_from('<HHHHI',raw)==(0x2103,0x10a,0x54,0,2)
    for c in j['queues']:
        if not c['busy_fixture']:
            assert c['target_at_popped_pointer']==20000000
            assert c['popped_request_native_state_dispatch_reached_timing_logger_with_queue_already_zero']
            assert c['original_enqueue_frame_SP_and_callee_saved_x19_to_x29_restored_across_explicit_diagnostic_gaps']
    for c in j['state_cases']:
        s=c['declared_numeric_state']
        if s in (21,22):
            assert c['events'][-1]['reason']=='returned' and c['state_word_after']==22
            assert c['events'][-1]['x0_to_x5'][0]=='0x0'
        assert not c['normal_back_constructor_real_state_transition_or_MAIN_proven']
    for c in j['routes']+j['queues']+j['state_cases']:
        for e in c['events']:
            assert e['whole_original_image_unchanged']
            assert e['whole_arena_outside_declared_outputs_unchanged']
            assert e['whole_stack_outside_declared_1280_byte_range_unchanged']
    failure = json.loads((STAGE/'run-state-dispatch-20261027/attempt-failure.json').read_text())
    assert not failure['passing_result'] and 'AssertionError' in failure['traceback']
    # Primary local evidence: exact ROM words and original instruction bytes.
    md=trial.r.capstone.Cs(trial.r.capstone.CS_ARCH_ARM64,trial.r.capstone.CS_MODE_LITTLE_ENDIAN)
    def listing(a,z):
        return {'file_range':[hex(a),hex(z)],'bytes_sha256':sha(blob[a:z]),
                'instructions':[{'file_offset':hex(i.address),'bytes':i.bytes.hex(),
                                 'mnemonic':i.mnemonic,'operands':i.op_str}
                                for i in md.disasm(blob[a:z],a)]}
    tables=[]
    for table in (0x35c7e8,0x367b20,0x36bca8,0x370c10):
        tables.append({'table':hex(table),'entries':[
            {'slot':hex(off),'pointer':hex(struct.unpack_from('<Q',blob,table+off)[0]),
             'target_file_offset':hex(struct.unpack_from('<Q',blob,table+off)[0]-trial.V)}
            for off in (0,8,0x10,0x18,0x20)]})
    rows=[]
    for s in range(23):
        vals=struct.unpack_from('<3Q',blob,0x36c8e8+s*24)
        rows.append({'numeric_state':s,'file_offset':hex(0x36c8e8+s*24),
                     'condition_action_next_file_offsets':[hex(v-trial.V) for v in vals]})
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    put(STAGE/'topology-and-ROM-audit.json',{
        'created_utc':now,'original_avcam_sha256':sha(blob),'guest_VA_base':hex(trial.V),
        'scope':'Static exact original words and bounded instruction listings. No whole-program xref completeness, dynamic MAIN graph, source policy, protocol or camera validation.',
        'constructor_graph':{
            'timing':'Original a61f4 constructs parent+115a10 via a6eb0.',
            'receiver':'Original a624c constructs parent+116588 via139894, with x3=parent+116988;1398d4 stores that argument at receiver+338.',
            'wrapper':'Original a6270 constructs parent+116988 via a7020; its table367b20 slot18 points168fd0, which dispatches selected object table slot8.',
            'receiver_slot18':'35c7e8+18 points13a464; it loads receiver+338 then invokes that distinct object slot18. It is not a direct binding to timing189ce8.',
            'trial_binding':'Original timing constructor and17792c setter executed on explicit caller-supplied objects; actual full state factory/normal producer/MAIN not established.'},
        'tables':tables,'QoS_event_ROM_table':{'offset':'0x36c8e8','stride':24,'statically_listed_rows':rows,
            'dynamic_states':[0,1,3,8,18,21,22],'numeric_state_names_unmapped':True,
            'all23_states_dynamically_validated':False},
        'listings':[listing(a,z) for a,z in (
            (0xa61c4,0xa61f8),(0xa6220,0xa6274),(0x139894,0x1398dc),
            (0x13a464,0x13a474),(0xa7020,0xa7084),(0x168fc8,0x168fe0),
            (0x169108,0x169134),(0x17792c,0x177934),(0x17effc,0x17f1b8),
            (0x17dfc4,0x17e044),(0x17b4d8,0x17b520))],
        'counterexample_scope':'Explicit host16M->20M source mutation after pointer enqueue, followed by original pop/ROM dispatch. Not a physical-camera race/reachable schedule or applied target.',
        'unexecuted_boundaries':['diagnostic/logger bodies','actual message object construction/send','back factory and normal lifecycle transitions','nested4c copy provider','complete codec/HAL consumption','actual MAIN and recovery'],
        'other_prototype_or_camera_change':False})
    rel=str(STAGE.relative_to(ROOT))
    result_rel=str((run/'qos-routing-results.json').relative_to(ROOT))
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(manifest['files']),
            'route_cases':10,'queue_cases':4,'state_cases':18,'bounded_phases':118,
            'formal_source_matches_executed_copy':True,'same_agent_evidence_review_not_independent_engine':True,
            'initial_state21_expectation_corrected_to_native22':True,
            'new_real_MAIN_policy_or_applied_target_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_QoS_ROM_state_dispatch_and_queued_request_lifetime'
    g['progress_audit']={
        'classification':'progress','previous_goal_turn_classification':'no_progress',
        'previous_turn_basis':'Previous inbox/status turn verified existing state but ran no new experiment or live wait; no usable result was added.',
        'basis':[
            'stage99的11件封存与canonical核对；未访问Windows/UU/相机。',
            '完整原时序构造/原绑定setter，原ROM按状态1排队、3/8/18转发到码率入口；数字状态无实机名称/MAIN绑定。',
            '独立较低栈的原48请求/54封套复制，原暂停栈保持；0目标/更新关闭也仅证明转发，不证明编码接受。',
            '原指针入队/出队与同客体ROM分派对照：队列0时请求调用仍暂停，旧指针槽保留；宿主16->20M改动只是寿命试验，不是相机竞态或已应用码率。',
            '核对不同接口的原构造指针，13a464不能因同虚表偏移而直接绑定189ce8；MAIN策略生产者仍缺。',
            '32组118阶段；初轮错误预期state21不变修正为原生变22，失败材料保留。全部16项要求/授权/客体原型保持，实录与同机恢复未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage100_QoS_ROM_dispatch_queue_lifetime']={
        'readme':rel+'/README.md','result':result_rel,'topology':rel+'/topology-and-ROM-audit.json',
        'review':rel+'/completed-evidence-review.json',
        'scope':'32 declared-input cases/118 phases. Native ROM event selection and constructor-installed timing dispatch, independent lower forwarding, pointer enqueue/pop lifetime. Real producer/MAIN/HAL/recovery unproved.',
        'guest_prototype_changed':False,'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10'):
            req['evidence'].extend([result_rel,rel+'/topology-and-ROM-audit.json'])
            req['stage100_scope']='原QoS事件ROM状态分派、独立48字节转发及一层指针队列寿命有界验证；同偏移接口不能混接。真实MAIN/策略/代次/模块全局退出及实际编码未证，状态保持。'
    g.setdefault('provenance_refinements',[]).append({
        'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Native event ROM selects enqueue versus forward on declared numeric states; pointer pop can zero queue while original request dispatch remains suspended. Distinct constructor graphs prevent equating receiver+338 wrapper slot18 with timing slot18. No actual MAIN policy producer or runtime completion inferred.',
        'actual_MAIN_applied_target_module_exit_or_recovery_proven':False})
    g['next_safe_offline_actions'].append(
        'stage100后优先追177840→183efc原工厂/状态来源及真正enc_set_qos_param_command生产/接收路径，绑定MAIN、质量和配置代次。不要把构造入参fixture或同虚表偏移当自然链；指针出队0不是应用完成/代码退出。嵌套4c复制提供者未执行，不能推广单队列寿命。仍仅Mac；不重跑已有局部片段冒充新进展，不更换stage75原型或进入相机。')
    invariant_keys=('objective','authorization','completion_rule','current_user_operational_constraint',
                    'external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in invariant_keys:
        assert old[key]==g[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();txt=ib.decode();marker='## 相机与固件研究\n'
    assert txt.count(marker)==1
    entry='- [2026-10-27 FX3 原QoS状态分派与请求寿命](<'+rel+'/README.md>)：32组/118阶段，原ROM选择排队或转发；指针出队0不代表请求完成。不同接口原指针已区分，MAIN策略/实录/恢复仍未证，仅Mac。'
    assert entry not in txt
    updated=txt.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes())
    index.write_text(updated)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
    put(STAGE/'final-receipt.json',{
        'schema':'fx3-stage100-native-QoS-state-routing-queue-lifetime/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':trial.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,
        'invariants_retained':list(invariant_keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
                      'route_cases':10,'queue_cases':4,'state_cases':18,'phases':118,
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':
    main()
