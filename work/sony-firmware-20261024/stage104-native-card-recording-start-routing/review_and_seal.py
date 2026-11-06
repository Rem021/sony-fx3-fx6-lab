#!/usr/bin/env python3
"""Review bounded media-start evidence and retain the full camera/recovery goal."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import movie_start as t
BASE,ROOT=t.BASE,t.ROOT


def sha(raw):return hashlib.sha256(raw).hexdigest()


def put(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    t.im.volume();assert not (STAGE/'final-receipt.json').exists()
    assert sha(t.PRIOR.read_bytes())==t.PRIOR_SHA
    pm=json.loads(t.PRIOR.read_text())
    for f in pm['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(t.PRIOR.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-consumer-bound-20261027';j=json.loads((run/'movie-start-results.json').read_text())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'movie_start.py').read_bytes()
    assert [len(j[k]) for k in ('caller_arguments','movie_event_packets','prepare_media_packets',
        'recstart_media_packets','original_MPR_consumers')]==[4,2,8,14,6]
    assert j['bounded_phases']==82 and not j['goal_complete'] and not j['persistent_write_release']
    assert not j['Windows_UU_camera_operations']
    for key in ('caller_arguments','movie_event_packets','prepare_media_packets','recstart_media_packets','original_MPR_consumers'):
        for row in j[key]:
            for e in row['events']:
                assert e['whole_stack_outside_declared_frame_unchanged']
                assert e['whole_scratch_outside_declared_outputs_unchanged']
                assert e['mapped_original_ELF_guest_readonly_and_no_patch_or_resolution_requested']
                assert not e['imports_logs_or_return_adapters_executed']
    for c in j['caller_arguments']:
        assert c['key_clear_input_hex']==c['movie_event_input_hex']=='00000000'
        assert not c['whole_sequence_recording_or_shared_encoder_proven']
    for p in j['recstart_media_packets']:
        raw=bytes.fromhex(p['request38_hex']);assert len(raw)==0x38
        assert struct.unpack_from('<I',raw,0)[0]==6
        assert struct.unpack_from('<I',raw,8)[0]==p['native_media_count']
    for c in j['original_MPR_consumers']:
        assert c['native_SetRecStartInfo_argument_preserved_and_pending_frame_unchanged']
        assert any(p['request38_hex']==c['original_app_request38_hex'] and p['seed']==c['seed'] for p in j['recstart_media_packets'])
        assert not c['complete_validation_actual_ID_registry_or_recording_proven']
    initial=json.loads((STAGE/'run-initial-20261027/attempt-failure.json').read_text())
    assert not initial['passing_result'] and 'AssertionError' in initial['traceback']
    intermediate=json.loads((STAGE/'run-trace-call-bound-20261027/movie-start-results.json').read_text())
    assert intermediate['bounded_phases']==70
    app,mpr=t.APP,t.pp.MPR
    assert sha(app.path.read_bytes())==t.prev.APP_SHA==j['original_app_sha256']
    assert sha(mpr.path.read_bytes())==j['original_mpr_sha256']=='9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'
    section=app.elf.get_section_by_name('.text');data=section.data();base=section['sh_addr']
    calls={0x2dd4ad4:[],0x2dd89d4:[]}
    for n,(w,) in enumerate(struct.iter_unpack('<I',data)):
        if w&0x7c000000!=0x14000000:continue
        imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm
        pc=base+n*4;dest=pc+imm*4
        if dest in calls:calls[dest].append(hex(pc))
    assert calls[0x2dd4ad4]==['0x2da8cf8','0x2db0f4c'] and len(calls[0x2dd89d4])==14
    pairs=((app,0x1593910,mpr,'_ZN3mpr15PrepareRecStartERKNS_22prepareRecStartInParamEPNS_23prepareRecStartOutParamE'),
           (app,0x1593ec0,mpr,'_ZN3mpr8RecStartERKNS_15recStartInParamE'),
           (mpr,0x80eb0,mpr,'_ZN3mpr15SetRecStartInfoERKNS_15recStartInParamEPNS_12MovieRecInfoE'),
           (mpr,0x7ca10,mpr,'_ZN3mpr20CheckRecStartInParamERKNS_15recStartInParamE'))
    bindings=[]
    for n,a,d,s in pairs:
        assert n.plt[a]==s and d.symbols[s]['size']>0
        bindings.append({'caller_library':n.path.name,'PLT_VA':hex(a),'original_symbol':s,
            'defined_in':d.path.name,'defined_VA':hex(d.symbols[s]['va']),
            'definition_size':d.symbols[s]['size'],'dynamic_loader_not_executed':True})
    def listing(n,a,z):return {'library':n.path.name,'VA_range':[hex(a),hex(z)],
        'original_bytes_sha256':sha(n.read(a,z-a)),'original_disassembly':n.disasm(a,z)}
    def text(a):return app.read(a,220).split(b'\0')[0].decode()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    audit={
        'created_utc':now,'original_app_sha256':j['original_app_sha256'],
        'original_mpr_sha256':j['original_mpr_sha256'],'bindings':bindings,
        'direct_call_scan':{'section':'.text','VA':hex(base),'bytes':len(data),
            'method':'Decode aligned original immediate B/BL instructions only.',
            'targets':{hex(k):v for k,v in calls.items()},'indirect_calls_excluded':True},
        'original_names':[{'VA':hex(a),'text':text(a)} for a in (0x395a108,0x395b650,0x3959fd0,
            0x395a070,0x3959b53,0x3959cd0,0x398cdc0,0x3989eb5)],
        'app_listings':[listing(app,a,z) for a,z in (
            (0x2da8c48,0x2da8d60),(0x2db0ea4,0x2db0fa0),(0x2dd4ad4,0x2dd4b14),
            (0x2e3f628,0x2e3f684),(0x2e3f580,0x2e3f5cc),(0x2e25338,0x2e25344),
            (0x2daaa08,0x2daaa80),(0x2da9700,0x2da9714),
            (0x2da9b50,0x2da9b98),(0x2da9dd8,0x2da9e18),
            (0x2ddaf54,0x2ddafd4),(0x2e5c5e8,0x2e5c724),(0x2e76854,0x2e769f0),
            (0x2e76ae8,0x2e76af8))],
        'mpr_listings':[listing(mpr,a,z) for a,z in (
            (0xdc504,0xdc560),(0xdc674,0xdc694),(0xdc7e0,0xdc84c),
            (0xccbdc,0xccc8c),(0xcc1c4,0xcc248),(0xcc4ac,0xcc4d4))],
        'new_relation':'Original card sequence has MPR media-prepare/start calls separately from shared EID3001. RecStart statically calls SetRecStartInfo, which calls CheckRecStartInParam. Bounded native-produced parameters reach the original count/first-ID consumer only.',
        'shared_event_scope':'Does not prove event is acquisition-only, no-card-effect, or shared encoder. Full event consumer remains unknown.',
        'original_recstart_queued_calls':[{'callsite':hex(i.address),'PLT':hex(int(i.op_str[1:],16)),
            'symbol':mpr.plt[int(i.op_str[1:],16)]}
            for i in mpr.md.disasm(mpr.read(0xdc504,0x79c),0xdc504)
            if i.mnemonic=='bl' and i.op_str.startswith('#') and 'EnqueueExec' in mpr.plt.get(int(i.op_str[1:],16),'')],
        'not_normal_runtime':'Post-log/runtime entries are independent; no locks, event state, valid media registry, complete validation, encoder Open/Start, mux or actual file.',
        'failure_correction':'Initial host range excluded original2f6ddac call. Range extended by4 bytes to2f6ddb0 to reach existing trace-identity boundary. Firmware unchanged; initial failure and70-phase intermediate retained.',
        'official_crosscheck':{'url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1001273514.html',
            'checked_utc':now,'classic_FX3_scope':True,
            'facts':['Network streaming requires firmware6.00 or later.',
                'Movie Rec During Streaming separately enables recording to media.',
                'The guide lists restrictions linking stream resolution/frame rate to media recording format/frame rate.'],
            'not_evidence_for_internal_shared_instance_or_target_MAIN_codec':True},
        'actual_MAIN16M_42010_SPS_audio_longrun_recovery_or_safe_flash_proven':False}
    put(STAGE/'source-and-scope-audit.json',audit)
    review={'status':j['status'],'created_utc':now,'prior_files_verified':len(pm['files']),
        'bounded_phases':82,'caller_cases':4,'event_cases':2,'prepare_cases':8,'start_cases':14,'MPR_cases':6,
        'formal_source_matches_executed_copy':True,'static_imports_to_definitions_verified':len(bindings),
        'same_agent_review_not_independent_engine':True,'Windows_UU_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT))
    result_rel=str((run/'movie-start-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_native_shared_movie_event_and_MPR_media_recording_start_routing'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'no_progress',
        'basis':[
            '上一goal轮仅检查Orca消息与复核stage103封存，未新增技术证据，归类no_progress；本轮采取可用的Mac离线下一步。',
            'stage103全部11件与canonical核对；没有Windows/UU/相机操作。',
            '普通录制/推流共享movie事件且原生输入均0，原事件ID3001；不能仅凭cam_start_movie_rec名称证明MAIN或复用编码器。',
            '原卡内序列另调用MPR PrepareRecStart/RecStart；原28/56字节介质参数构造，4选择对照、索引参数对照及A5/C3核对。',
            '原RecStart到SetRecStartInfo及Check导入/定义静态绑定，原生成56字节不改进入原检查前缀，停实际介质ID查找或零数量诊断。共82有界阶段，不是正常连续执行。',
            '转向MPR配置/真实MovieRecInfo与编码队列消费者，未把媒体启动等同目标HEVC42010/16M配置；全部16项状态和权限保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage104_MPR_media_start_routing']={
        'readme':rel+'/README.md','result':result_rel,'source_audit':rel+'/source-and-scope-audit.json',
        'review':rel+'/completed-evidence-review.json','bounded_phases':82,
        'scope':'Shared event3001 input0 differs from separately located MPR media-prepare/start route. Native media packets reach original checker prefix; full media validation/state/Open/codec/MUX/MAIN/recovery remain unproved.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage104_scope']='原普通录制另有MPR介质Prepare/Start链；28/56字节原构包和原Set/Check入口核对，不是目标MAIN编码配置、有效介质状态、完整Open/Start或成片。共享EID3001不能证明编码器复用；状态保持。'
    g.setdefault('provenance_refinements',[]).append({
        'stage':STAGE.name,'prior_stage':t.PRIOR.parent.name,
        'finding':'Both native model callers pass zero to shared movie-event wrapper; card sequence separately targets MPR PrepareRecStart/RecStart. Static MPR Set/Check binding and bounded original media-packet checks refine the next direction, without proving event is acquisition-only or completing MAIN state/codec/mux.',
        'actual_MAIN_SPS_shared_instance_or_recovery_proven':False})
    g['next_safe_offline_actions'].append(
        'stage104后从MPR PrepareRecStart/RecStart的实际录制配置准备、MovieRecInfo来源和EnqueueExecEncOpen/Ready/Start消费者追MAIN初始化，核对介质注册/实际上下文/配置代次。共享movie事件3001和输入0不证明共享编码器，也不证明事件绝无写卡作用；不把介质启动参数当HEVC42010/16M初始化。保留stage102更新候选，stage103推流4208配置不套用MAIN。仅Mac离线，实际协议/写入/同机恢复及实录要求保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint',
          'external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in keys:assert g[k]==old[k]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
    assert text.count(marker)==1
    entry='- [2026-10-27 FX3 共享movie事件与MPR介质录制启动](<'+rel+'/README.md>)：普通录制另有Prepare/RecStart链，原介质构包及检查前缀82阶段；共享事件不是编码器复用证明。目标主录/恢复未验收，仅Mac。'
    assert entry not in text
    updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.im.volume();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            d=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(d),'sha256':sha(d)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage104-native-media-start/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':t.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,
        'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
                      'bounded_phases':82,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
