#!/usr/bin/env python3
"""Seal native app producer evidence without treating streaming as MAIN."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import app_qos as trial
BASE,ROOT,im=trial.BASE,trial.ROOT,trial.im


def sha(raw):return hashlib.sha256(raw).hexdigest()


def put(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=trial.PRIOR;assert sha(prior.read_bytes())==trial.PRIOR_SHA
    pm=json.loads(prior.read_text());checked=0
    for f in pm['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256'];checked+=1
    parent=BASE/'stage100-native-qos-routing-and-queue-lifetime/final-receipt.json'
    assert sha(parent.read_bytes())==pm['previous_manifest_sha256']
    for f in json.loads(parent.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256'];checked+=1
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'app_qos.py').read_bytes()
    j=json.loads((run/'app-qos-results.json').read_text())
    assert len(j['producer_cases'])==8 and len(j['metadata_prefix_cases'])==2 and len(j['handoff_cases'])==4
    assert j['bounded_phases']==50 and not j['Windows_UU_camera_operations']
    assert not j['goal_complete'] and not j['persistent_write_release']
    for c in j['producer_cases']:
        raw=bytes.fromhex(c['message50_hex'])
        assert struct.unpack_from('<HHHH',raw)==(0x2003,0x10a,0x50,1)
        assert len(raw)==80 and raw[12]==1
        assert struct.unpack_from('<I',raw,16)[0]==(c['declared_input_word']*1000)&0xffffffff
        assert c['no_OSAL_reply_identity_or_success_result_synthesized']
        for e in c['events']:
            assert e['whole_stack_outside_declared_frame_unchanged'] and e['whole_scratch_outside_declared_outputs_unchanged']
            assert not e['imports_logs_or_return_adapters_executed']
    for c in j['metadata_prefix_cases']:
        assert c['first8_after_hex']=='0000000002000000'
        assert c['constant2_not_claimed_encoder_channel']
    for c in j['handoff_cases']:
        raw=bytes.fromhex(c['app_message_hex']);lower=bytes.fromhex(c['lower_envelope_hex'])
        assert raw[8:]==lower[12:]
        assert c['raw_body_copied_between_guests_without_host_field_edits']
        assert c['pending_original_action_frames_preserved'] and c['channel_not_inferred_from_OSAL_constant2']
        assert not c['actual_transport_target_MAIN_format_or_Hal_application_proven']
    app=trial.APP;assert sha(app.blob)==sha(app.path.read_bytes())==trial.APP_SHA
    assert sha(trial.src.prev.IMAGE.read_bytes())==trial.src.prev.IMAGE_SHA
    def text(a,n=240):return app.read(a,n).split(b'\0')[0].decode()
    def listing(a,z):return {'ELF_VA_range':[hex(a),hex(z)],'original_bytes_sha256':sha(app.read(a,z-a)),
                            'original_disassembly':app.disasm(a,z)}
    section=app.elf.get_section_by_name('.text');raw=section.data();base=section['sh_addr'];branches=[]
    for at in range(0,len(raw)-3,4):
        w=struct.unpack_from('<I',raw,at)[0]
        if w&0xfc000000 in (0x94000000,0x14000000):
            n=w&0x3ffffff;n=n if n<0x2000000 else n-0x4000000
            if base+at+4*n==0x2dd1d54:branches.append(base+at)
    assert branches==[0x2d9c204,0x2db1bdc]
    assert 'sequence_set_srt_streaming_target_bitrate' in text(0x3955fd8)
    assert 'sequence_start_streaming_output::streaming_start' in text(0x395b610)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    put(STAGE/'source-and-callers-audit.json',{
        'created_utc':now,'original_app_sha256':trial.APP_SHA,
        'producer':{'public_wrapper_VA':'0x2dd1d54','detail_function_VA':'0x2df20cc',
            'bounded_packet_body_entry':'0x2df213c','direct_send_callsite':'0x2df21e8',
            'detail_type_string':text(0x3967870),'bps_diagnostic_string':text(0x3964375),
            'native_scaling':'32bit MUL: (input_word*1000)&0xffffffff',
            'complete80_byte_packet_only_not_normal_call_or_send':True},
        'literal_direct_branch_scan':{'section':'.text','VA':hex(base),'bytes':len(raw),
            'method':'Aligned A64 B/BL immediate targets only; no all-call-graph or indirect reachability claim.',
            'wrapper_target':'0x2dd1d54','matches':[hex(x) for x in branches]},
        'callers':[{'callsite':'0x2d9c204','name_string':text(0x3955fd8),'string_VA':'0x3955fd8','input_word':'object+0x1b8'},
                   {'callsite':'0x2db1bdc','name_string':text(0x395b610),'string_VA':'0x395b610','input_word':'object+0x61c'}],
        'OSAL_prefix':{'entry':'0x2de7070','first_PLT':'0x1593d20',
            'first_symbol':app.plt[0x1593d20],'later_unexecuted_tail_symbol':app.plt[0x1592b40],
            'observed_prefix_only_fields':[0,2],
            'channel_or_valid_reply_identity_not_inferred':True},
        'sender_static_imports':[{'PLT':hex(a),'symbol':app.plt[a]} for a in (
            0x15932c0,0x15925f0,0x1593c60,0x15926f0,0x15927a0,0x1594520)],
        'fixed_send_argument':'0x8057060a','actual_target_instance_and_transport_unproven':True,
        'listings':[listing(a,z) for a,z in (
            (0x2df20cc,0x2df21ec),(0x2df227c,0x2df22d8),(0x2dd1d54,0x2dd1d94),
            (0x2de7070,0x2de70a8),(0x2d9c1b4,0x2d9c210),(0x2db1708,0x2db1760),
            (0x2db1bb0,0x2db1be8),(0x2e109d0,0x2e10abc))],
        'scope':'Actual original native packet body plus explicit-byte handoff. Original source call sites are streaming/SRT; missing OSAL/logs/transport/state/instance prove no card MAIN capability yet.',
        'previous_converter_table_absence_stands':'stage101 only excluded this local libInfraAvbbc table; the newly located app direct packet producer is a distinct original path.',
        'upstream_natural_target_MAIN_HEVC_actual_media_or_recovery_proven':False})
    put(STAGE/'official-source-notes.json',{
        'reviewed_utc':now,'source_url':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1001273514.html',
        'source_title':'ILME-FX3 Help Guide: Network Streaming (movie)',
        'model_scope':'Classic ILME-FX3 Ver.2 or later; feature described from firmware6.00.',
        'verification_method':'Official exact-model Help Guide retrieved with web tool in this goal turn; no camera setting or stream was started.',
        'published_setting_facts':{'HD1080_29_97p_bit_rate_Mbps_min':3,'HD1080_29_97p_bit_rate_Mbps_max':18,
            'HD1080_29_97p_default_Mbps':6,'stream_format_list':['HEVC/H.265','AVC/H.264'],
            'RTMP_RTMPS_video':'H.264','media_recording_during_streaming_is_separate_option':True},
        'not_proven_by_page':['42010 for target stream','all format combinations or exact16M actual stream',
            'same encoder/preset as card MAIN','target HEVC card file','exact30.000','safe firmware modification or recovery'],
        'different_model_search_results_not_used':True})
    review={'status':j['status'],'created_utc':now,'prior_sealed_member_files_checked':checked,
        'producer_cases':8,'OSAL_prefix_cases':2,'byte_handoff_cases':4,'bounded_phases':50,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'actual_MAIN_transport_Hal_or_recovery_proven':False,'Windows_UU_camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT))
    result_rel=str((run/'app-qos-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_app_QoS_packet_producer_streaming_callers_and_receiver_handoff'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':[
            'stage101及其stage100依赖封存成员26件核对，canonical保持，未访问Windows/UU/相机。',
            '在原appFw.so定位2dd1d54→2df20cc，原body直接生成CID2003/MID10a/长度50命令；16000输入原乘1000得16M。原清理完整80字节，A5/C3输出一致，不依赖stage101缺映射的表。',
            '8原构包+2标识前缀+4原字节交接，共50阶段。原生消息未经字段修改进入独立av-cam接收副本/ROM动作/下层54封套，16M/20M保持；实际transport/身份/状态仍明确fixture与间隙。',
            '原直接调用者名为SRT码率调整及推流启动；不能绑定卡内MAIN。参数2涉及OSAL标识前缀，不等同下层模型通道2。',
            '官方经典FX3页确认推流功能/1080p29.97码率3..18M与H265列表；这不证明42010/实际16M/卡内MAIN，不以推流替代目标。',
            '全部16项状态、授权和stage75客体原型保持；实际HEVC主录及同机备份/恢复/独立救砖未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage102_original_app_QoS_packet_producer']={
        'readme':rel+'/README.md','result':result_rel,'source_audit':rel+'/source-and-callers-audit.json',
        'official_source_scope':rel+'/official-source-notes.json','review':rel+'/completed-evidence-review.json',
        'scope':'Original app native80-byte QoS packet from fixture16000->16M, direct streaming/SRT callers, explicit byte handoff into receiver. OSAL identity/send/reply/state/MAIN remain unproved;50 phases, no device operations.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-callers-audit.json'])
            req['stage102_scope']='原app mc_enc_set_qos直接构包及输入×1000单位链、SRT/推流调用者和原字节交接有界验证；原库表缺10a不代表所有路径缺命令。实际MAIN/质量/实例/代次/transport及硬件未证，状态保持。'
    g.setdefault('provenance_refinements',[]).append({
        'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Original app directly builds QoS packet outside stage101 converter table. Native input*1000 and exact message80 now feed bounded receiver/lower envelope. Observed direct callers are SRT/streaming; OSAL constant2 is not receiver channel evidence. No card MAIN or applied target inferred.',
        'actual_MAIN_Hal_media_or_recovery_proven':False})
    g['next_safe_offline_actions'].append(
        'stage102已找到app原生mc_enc_set_qos生产函数，不重复猜改libInfraAvbbc表或将其缺10a当全局缺命令。下一步沿SRT/streaming_start与Movie Rec During Streaming的原Open/Start、实例/资源质量、输入位深和卡内mux绑定关系，判断是否共享目标MAIN；不要将推流成功/OSAL常数2/生成16M包替代42010主录验收。所有实际send/reply/OSAL状态及相机授权保持，仍仅Mac。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint',
          'external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
    assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原应用码率请求生产与SRT范围](<'+rel+'/README.md>)：原16000输入生成16M/80字节命令，原字节接收及下层转发保持；14组/50阶段。现有调用者属推流，卡内MAIN/实录/恢复仍未证，仅Mac。'
    assert entry not in text
    updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage102-original-app-QoS-producer/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':trial.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,
        'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
                      'bounded_phases':50,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
