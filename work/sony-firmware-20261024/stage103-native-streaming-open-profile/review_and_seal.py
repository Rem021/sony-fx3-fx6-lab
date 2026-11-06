#!/usr/bin/env python3
"""Seal native streaming profile evidence without claiming actual bitstreams."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import open_profile as trial
BASE,ROOT,im=trial.BASE,trial.ROOT,trial.im


def sha(raw):return hashlib.sha256(raw).hexdigest()


def put(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=trial.PRIOR;assert sha(prior.read_bytes())==trial.PRIOR_SHA
    pm=json.loads(prior.read_text())
    for f in pm['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-native-frame-corrected-20261027'
    assert (run/'executed-source.py').read_bytes()==(STAGE/'open_profile.py').read_bytes()
    j=json.loads((run/'open-profile-results.json').read_text())
    assert len(j['produced_profiles'])==len(j['native_classifications'])==10 and j['bounded_phases']==150
    assert not j['goal_complete'] and not j['persistent_write_release'] and not j['Windows_UU_camera_operations']
    for p in j['produced_profiles']:
        raw=bytes.fromhex(p['raw98_at_first_dump_hex'])
        assert raw[0x94:0x96]==bytes(2) and raw[0x96:]==bytes([p['seed']])*2
        assert not p['whole_raw_packet_initialization_or_normal_Open_proven']
        for e in p['events']:
            assert e['whole_stack_outside_declared_frame_unchanged'] and e['whole_scratch_outside_declared_outputs_unchanged']
            assert not e['imports_logs_or_return_adapters_executed']
    for c in j['native_classifications']:
        d=c['decoded'];assert d['depth']['original_name']=='BIT_DEPTH_8'
        assert d['chroma']['original_name']=='CHROMA_420'
        assert d['coding']['original_name'] in ('STREAMING_HEVC_BSF','STREAMING_AVC_BSF')
        assert c['native_module_selector']==(2 if d['coding']['original_name']=='STREAMING_HEVC_BSF' else 1)
        assert not c['whole_receiver_descriptor_builder_instance_or_real_SPS_proven']
        for e in c['events']:
            assert e['whole_arena_outside_declared_outputs_unchanged'] and e['whole_stack_outside_declared_1280_byte_range_unchanged']
            assert e['whole_original_image_unchanged']
    target=[c for c in j['native_classifications'] if c['label']=='HEVC_HD_29_97']
    assert len(target)==2
    assert all(c['decoded']['frame']['original_name']=='29_97' and c['decoded']['quality']['original_name']=='QT18M' for c in target)
    assert all(len(p['old_seed_dependent_byte_offsets'])==47 for p in j['old_value_scope'])
    failure=json.loads((STAGE/'run-initial-20261027/attempt-failure.json').read_text())
    assert not failure['passing_result'] and 'AssertionError' in failure['traceback']
    assert 'HEVC_HD_base0' in (STAGE/'run-initial-20261027/executed-source.py').read_text()
    app=trial.APP;blob=trial.prev.src.prev.IMAGE.read_bytes()
    assert sha(app.path.read_bytes())==trial.prev.APP_SHA
    assert sha(blob)==trial.prev.src.prev.IMAGE_SHA
    md=trial.r.capstone.Cs(trial.r.capstone.CS_ARCH_ARM64,trial.r.capstone.CS_MODE_LITTLE_ENDIAN)
    def avlisting(a,z):return {'file_range':[hex(a),hex(z)],'original_bytes_sha256':sha(blob[a:z]),
        'original_disassembly':[{'file_offset':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str}
                                for i in md.disasm(blob[a:z],a)]}
    def applisting(a,z):return {'ELF_VA_range':[hex(a),hex(z)],'original_bytes_sha256':sha(app.read(a,z-a)),
        'original_disassembly':app.disasm(a,z)}
    def text(a):return app.read(a,240).split(b'\0')[0].decode()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    put(STAGE/'source-and-scope-audit.json',{
        'created_utc':now,'original_app_sha256':trial.prev.APP_SHA,'original_avcam_sha256':sha(blob),
        'app_production':{'parent_wrapper':'0x2dd1c14 ->0x2df1958','detail_open':'0x2de7364',
            'detail_name':text(0x396a118),'parent_signature':text(0x3967c10),
            'executed_prologue':'0x2de7364 -> first logger','independent_post_DMM_entry':'0x2de74a8',
            'output_address':'Explicit register fixture, not allocated/mapped/translated by original runtime.',
            'fixed_zero_chroma_depth_stores':['0x2de77d8 ->raw94','0x2de77dc ->raw95'],
            'app_field_semantics_from_original_dump':['fileFormat','targetVideoFormat','pictureSizeH','pictureSizeV',
                'framePerSec','scanMode','pictureQuality'],
            'not_a_complete_valid_request':True},
        'native_argument_sources':{
            'owner_copy_prefix':'raw98 stored at owner+20 in earlier verified builder; this turn invokes scalar converters independently.',
            'coding':['outer format byte','raw66'],'frame':['raw80','raw7a'],
            'scan':['raw81'],'quality':['raw82'],'chroma':['raw94'],'depth':['raw95'],
            'whole_builder_or_actual_context_not_proven':True},
        'module_selector':{'original_entry':'0x22c3cc','HEVC_profile_result':2,'AVC_profile_result':1,
            'shared_module_category_not_same_encoder_instance_or_MAIN':True},
        'app_listings':[applisting(a,z) for a,z in (
            (0x2db1780,0x2db17ec),(0x2dd1c14,0x2dd1c54),(0x2df1958,0x2df1a9c),
            (0x2de7364,0x2de73dc),(0x2de74a8,0x2de759c),(0x2de76ec,0x2de77e4),
            (0x2de7d10,0x2de7d3c),(0x2de7fa8,0x2de7fc0))],
        'avcam_listings':[avlisting(a,z) for a,z in (
            (0x134a58,0x134ad8),(0x134b38,0x134b58),(0x134bf4,0x134cc4),
            (0x134d44,0x134ec0),(0x1352f8,0x135400),(0x22c3cc,0x22c430))],
        'next_recording_relationship_anchors':[
            {'name':text(0x395b650),'name_VA':'0x395b650','lexical_ADRP_ADD':['0x2db0ebc','0x2db0ed0'],
             'candidate_entry':'0x2db0ea4','first_observed_wrapper_call':'0x2dd89d4'},
            {'name':text(0x3960098),'name_VA':'0x3960098','lexical_ADRP_ADD':['0x2dc90e4','0x2dc90f4'],
             'candidate_prefix':'0x2dc90d0','first_observed_wrapper_call':'0x2dd89d4'}],
        'anchor_prefixes':[applisting(0x2db0ea4,0x2db0f04),applisting(0x2dc90d0,0x2dc913c)],
        'anchor_scope':'Names and lexical address pairs are not card-write, MAIN, shared instance or complete reachability proof. cam_start_movie_rec may concern acquisition; investigate its actual API/consumer.',
        'frame_expectation_correction':'Initial fixture scalar0 was incorrectly expected29_97; original result is59_94. Corrected target scalar2 producesraw3 then29_97; scalar4 producesraw2 then25_00. No original code changed.',
        'retained47_bytes_scope':'Declared post-DMM output beginsA5/C3; earlier allocation/clear is not executed. The retained dependencies do not establish a camera defect or useless padding.',
        'actual_stream_SPS_or_card_MAIN_Hal_recovery_proven':False})
    review={'status':j['status'],'created_utc':now,'prior_sealed_files_checked':len(pm['files']),
        'producer_profiles':10,'native_classifications':10,'bounded_phases':150,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'declared_profile_4208_classification_not_actual_stream_depth':True,
        'whole_Open_transport_instance_MAIN_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    put(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=copy.deepcopy(old);rel=str(STAGE.relative_to(ROOT))
    result_rel=str((run/'open-profile-results.json').relative_to(ROOT))
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_original_streaming_Open_profile_and_native_type_depth_classification'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':[
            'stage102的10件封存与canonical核对；仅Mac，未访问Windows/UU/相机。',
            '原app post-DMM Open体生成HD29.97字段，再由原av-cam转换/名称函数识别STREAMING_HEVC_BSF/QT18M/420/8bit；59.94、25、AVC及UHD对照分别核对，共10源配置/150阶段。',
            'HEVC模块选择值2不是相同实例或MAIN证据；当前推流Open不能替代目标HEVC_MP4/42010，原16M更新命令仍须绑定目标初始化/状态。',
            '初轮把输入帧率标量0误期望29.97，修正为原59.94；目标标量2经原代码成为29_97。失败保留，不改原固件；精确30.000仍未证。',
            '98字节输出47字节受声明旧值影响；DMM/头/清理/完整Open未执行，不把原片段输出当可提交包或固件缺陷。',
            '定位cam_start/stop_movie_rec名称及原前缀作为下一处连接，但未证明写卡或实例复用。全部16项状态/授权/stage75原型保持，实录及恢复未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage103_streaming_Open_profile_classification']={
        'readme':rel+'/README.md','result':result_rel,'source_audit':rel+'/source-and-scope-audit.json',
        'review':rel+'/completed-evidence-review.json',
        'scope':'10 declared post-DMM profiles and original scalar conversions:HD29.97 STREAMING_HEVC_BSF/QT18M/4208; not card MAIN42010 or actual SPS.150 bounded phases; actual allocation/state/instance/transport/Open remains missing.',
        'authorization_unchanged':True,'guest_prototype_changed':False,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10'):
            req['evidence'].extend([result_rel,rel+'/source-and-scope-audit.json'])
            req['stage103_scope']='原推流Open字段在目标HD29.97输入中识别为STREAMING_HEVC_BSF/QT18M/4208；HEVC模块类别2不能证明MAIN或同一实例。未执行完整Open/DMM/实际SPS，不能代替目标42010；状态保持。'
    g.setdefault('provenance_refinements',[]).append({
        'stage':STAGE.name,'prior_stage':prior.parent.name,
        'finding':'Stage102 QoS producer is retained, but associated declared streaming Open profile natively classifies asSTREAMING_HEVC_BSF/4208, not targetHEVC_MP4/42010. Original module selector2 is only a category. Frame scalar0 maps59_94; target scalar2 maps29_97. Retained post-DMM bytes and cam_rec names are not normal Open/card-write proof.',
        'actual_MAIN_SPS_shared_instance_or_recovery_proven':False})
    g['next_safe_offline_actions'].append(
        'stage103后不把SRT/推流Open的STREAMING_HEVC_BSF/4208借作HEVC_MP4/42010目标MAIN；原码率更新可保留为候选，但要绑定MAIN正确初始化/质量/代次。下一步追cam_start_movie_rec2db0ea4及cam_stop前缀2dc90d0、共同包装器2dd89d4，先确定是采集控制还是卡内记录，再追实际Movie Rec During Streaming设置和实例/mux关系。帧率标量0不是29.97；不用未完成DMM的98字节片段作为可提交请求。仍仅Mac，全部实机及恢复验收保持。')
    keys=('objective','authorization','completion_rule','current_user_operational_constraint',
          'external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for key in keys:assert g[key]==old[key]
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert len(g['requirements'])==16 and not g['goal_complete'] and not g['persistent_write_release']
    put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n'
    assert text.count(marker)==1
    entry='- [2026-10-27 FX3 推流Open与目标MAIN差别](<'+rel+'/README.md>)：原HD29.97分支识别STREAMING_HEVC_BSF/QT18M/4208；10源配置/150阶段，帧率预期已校正。相同HEVC模块类别不是MAIN实例证明，实录/恢复仍未证，仅Mac。'
    assert entry not in text
    updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[]
    for p in sorted(STAGE.rglob('*')):
        if p.is_file():
            raw=p.read_bytes();files.append({'path':str(p.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)})
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage103-streaming-Open-profile/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':trial.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':sha(before),'after_sha256':sha(canonical.read_bytes())},
        'readme_index_before_sha256':sha(ib),'readme_index_after_sha256':sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True,
        'invariants_retained':list(keys)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':sha((STAGE/'final-receipt.json').read_bytes()),
                      'bounded_phases':150,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
