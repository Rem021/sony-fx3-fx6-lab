#!/usr/bin/env python3
"""Review bounded field provenance and preserve all real-camera gates."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import config_fields as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage82-hevc-frame-parameter-handoff/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        b=(ROOT/r['path']).read_bytes();assert len(b)==r['bytes'] and im.sha(b)==r['sha256']
    before=(STAGE/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-20261026';j=json.loads((run/'config-field-results.json').read_text())
    assert j['status']=='PASS_BOUNDED_NATIVE_HEVC_INITIAL_GEOMETRY_RATE_TO_GOP_FIELDS'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'config_fields.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'config_fields.py').read_bytes()
    assert im.sha(a.SOURCE.read_bytes())==j['source_receipt']['stage50_result_sha256']==a.SOURCE_SHA
    blob=a.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.p.a.v.VCD_PATH.relative_to(BASE))]
    sources=json.loads(a.SOURCE.read_text())['cases'][:3]
    assert len(j['cases'])==16 and j['bounded_phases']==48
    events=[]
    for c in j['cases']:
        src=next(x for x in sources if x['label']==c['source_label'])
        raw_codec=bytes.fromhex(src['codec_hex']);raw_common=bytes.fromhex(src['common_hex'])
        codec=bytes.fromhex(c['codec_input_hex']);common=bytes.fromhex(c['common_input_hex'])
        assert im.sha(raw_codec)==c['source_stage50_original_codec_sha256']
        control=c['declared_control']
        allowed_codec=set(range(0x2c,0x30)) if control=='target20M' else set()
        allowed_common=set(range(0xc,0x10)) if control=='width_guard' else set(range(0x10,0x14)) if control=='height_guard' else set()
        assert all(x==y or i in allowed_codec for i,(x,y) in enumerate(zip(codec,raw_codec)))
        assert all(x==y or i in allowed_common for i,(x,y) in enumerate(zip(common,raw_common)))
        config=bytes.fromhex(c['config_after_hex']);gop=bytes.fromhex(c['GOP_after_hex'])
        expected=bytearray([c['seed']])*4096
        expected[0x34:0x37]=codec[0x1f:0x22];expected[0x37]=0
        w=sum(a.get32(common,o) for o in (0xc,0x14,0x18))
        h=sum(a.get32(common,o) for o in (0x10,0x1c,0x20))
        assert c['geometry_pixel_sums']==[w,h]
        geometry=struct.unpack_from('<HH',config,0x38)
        assert geometry==((w+15)//16-1,(h+15)//16-1)
        struct.pack_into('<HH',expected,0x38,*geometry)
        for dest,source in ((0x80,0x30),(0x84,0x2c),(0x88,0x34)):
            expected[dest:dest+4]=codec[source:source+4]
        struct.pack_into('<I',expected,0x8c,a.get32(expected,0x8c)&~7)
        assert config==bytes(expected)
        target=20000000 if control=='target20M' else 16000000
        assert c['decoded_target_input']==target
        good=control not in ('width_guard','height_guard')
        assert c['native_GOP_copy_accepted']==good
        expected_gop=bytearray([0xb6])*4096
        if good:
            assert geometry==(119,67) and c['decoded_GOP_target']==target
            expected_gop[0x78:0x114]=config[0x34:0xd0]
            assert a.get32(gop,0xc8)==a.get32(codec,0x2c)
        else:
            assert (geometry[0]==540) if control=='width_guard' else (geometry[1]==512)
            assert c['decoded_GOP_target'] is None
        assert gop==bytes(expected_gop)
        assert c['three_independent_entries_not_one_full_initialization']
        assert c['other_unclassified_bytes_are_declared_old_values']
        assert not c['full_valid_request_current_MAIN_hardware_or_recovery']
        expected_stops=['before_chroma_helper','after_three_rate_words',
                        'after_GOP_copy_before_base_helper' if good else 'before_original_assertion_runtime']
        assert [e['stop'] for e in c['events']]==expected_stops
        events.extend(c['events'])
    for seed in (0xa5,0xc3):
        for src in sources:
            pair=[next(c for c in j['cases'] if c['seed']==seed and c['source_label']==src['label'] and c['declared_control']==ctl)
                  for ctl in (None,'target20M')]
            for key,allowed in (('config_after_hex',set(range(0x84,0x88))),('GOP_after_hex',set(range(0xc8,0xcc)))):
                left,right=(bytes.fromhex(c[key]) for c in pair)
                delta={i for i,(x,y) in enumerate(zip(left,right)) if x!=y}
                assert delta and delta<=allowed
    assert len(events)==48
    for e in events:
        assert e['original_image_and_readonly_input_unchanged']
        assert e['complete_stack_matches_only_native_prologue_stores']
        assert not e['memory_read_write_hooks_installed'] and not e['return_or_MMIO_adapter']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    review={'status':'PASS_BOUNDED_NATIVE_HEVC_INITIAL_FIELD_PROVENANCE',
            'created_utc':now,'prior_sealed_files_verified':12,'cases':16,'bounded_phases':48,
            'source_builder_fixture_not_real_camera_capture':True,
            'HEVC_type2_primary_converter_not_adjacent_AVC_type1':True,
            'target_word_codec2c_config84_declared_GOPc8':True,
            'geometry_119_67_and_original_block_limits_checked':True,
            'target16M20M_output_differences_bounded_to_target_words':True,
            'three_independent_entries_not_complete_initialization':True,
            'real_call_chain_MAIN_hardware_recording_or_recovery':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False,
            'review_scope':'Same-agent source, PC, full-region, input-delta and output-delta checks; no independent engine or camera acceptance.'}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_HEVC_initial_geometry_and_rate_field_provenance'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
      'basis':['核验stage82的12件封存与canonical；仅Mac离线，原固件与授权未改。',
               '静态分清类型2初始18cc74与类型1初始18d8cc，另有类型2后续18d62c；不执行MMIO或未知乘加指令。',
               '用stage50保存fixture经三个独立原片段：几何119/67，codec2c原字到config84，原GOP边界/156复制到c8。16M/20M差异限对应目标字，宽540/高512块字段拒绝；16例48阶段。',
               '未绑定完整转换调用/真实MAIN/硬件与恢复；声明旧值不是有效请求，全部16项验收保持。'],
      'completion_not_claimed':True}
    result_rel=rel+'/run-20261026/config-field-results.json'
    g['latest_stage_evidence']['stage83_hevc_initial_config_fields']={
      'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','result':result_rel,
      'scope':'Captured stage50 fixture bytes; independent geometry/rate/GOP entries. No full initialization, actual runtime binding or hardware request.',
      'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result_rel)
            req['stage83_scope']='类型2原初始几何/码率到声明GOP字段，119/67及16M20M目标字对照和块数边界。stage50 fixture非实机抓取，三个独立入口非完整初始化/调用链/MAIN/命令或硬件；16例48阶段，恢复与全部验收未放宽。'
    g['next_safe_offline_actions'].append('stage83继续完整HEVC初始转换中chroma/裁剪/格式助手与其它字段来源，再核对实际命令消费者。仅有几何和三码率字分类，不能用未知旧值或随意清零的缓冲提交硬件；真实调用链/MAIN/运行时与全部同机恢复门禁保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode()
    marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-26 FX3 HEVC初始几何与码率字段](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：codec2c→配置84→声明GOPc8、块数119/67与边界；16例48阶段，三个独立入口非完整初始化/MAIN/硬件，仅Mac。'
    assert entry not in text
    text=text.replace(marker,marker+'\n'+entry+'\n',1)
    # Mutate only after all scoped checks and invariant checks above succeed.
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes())
    index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{
        'schema':'fx3-stage83-initial-hevc-field-provenance/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'operations':review,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
                      'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
