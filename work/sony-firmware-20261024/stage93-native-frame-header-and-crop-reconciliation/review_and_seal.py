#!/usr/bin/env python3
"""Review frame/crop data agreement without claiming an encoded picture."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import frame_crop as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage92-native-geometry-builder-and-IRQ-scope/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027';j=json.loads((run/'frame-crop-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_NATIVE_FRAME_CONSTRUCTOR_HEADER_REFERENCE_BOUNDARY_AND_CROP_RECONCILIATION'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'frame_crop.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'frame_crop.py').read_bytes()
    path=a.prev.prev.prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH;blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    historical=BASE/'stage84-hevc-native-config-body/final-receipt.json'
    next_receipt=json.loads((BASE/'stage85-hevc-slice-layout-production/final-receipt.json').read_text())
    assert im.sha(historical.read_bytes())==next_receipt['previous_manifest_sha256']
    for f in json.loads(historical.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    source=BASE/'stage84-hevc-native-config-body/run-20261026/native-body-results.json'
    assert im.sha(source.read_bytes())==j['source_receipt']['stage84_result_sha256']
    sources=json.loads(source.read_text())['cases']
    assert len(j['frame_cases'])==6 and len(j['crop_cases'])==4 and j['bounded_phases']==44
    events=[];returned=0;refstops=0
    for c in j['frame_cases']:
        es=c['events'];events+=es;assert len(es)==6
        seed=c['seed'];mode=c['declared_raw_mode0e'];flag=c['declared_update_byte50']
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_pages'].items()}
        assert len(pages)==7 and all(len(v)==4096 for v in pages.values())
        f=pages[a.old.FRAME_PA];owner=pages[a.old.OWNER_PA];src=pages[a.old.SRC_PA]
        assert c['native_frame_block_units']==list(struct.unpack_from('<HH',f,4))==[120,68]
        assert c['native_frame_pixel_fields']==list(struct.unpack_from('<HH',f,0x10))==[1920,1088]
        assert struct.unpack_from('<HH',f,8)==(68,68)
        assert es[0]['stop']=='returned_via_original_jr_ra' and es[0]['SP']==hex(a.SP_FRAME)
        assert all(hex(a.IMAGE+x) in es[0]['CODE_observed_PCs'] for x in
            (0x1f8550,0x1f8bbc,0x1c27b8,0x199258,0x1f8740,0x1f87b8))
        assert a.old.word(f,0x43c)==a.old.GP-0x5d58
        assert f[0x143]==0x73 and f[0x27c:0x280]==bytes([0x73])*4
        assert f[0x4e0:0x4e4]==bytes([15])*4
        assert es[4]['stop']==a.prev.STOPS[0x131888] and es[5]['entry']==es[4]['pc']
        assert es[4]['SP']==hex(a.prev.SP_CALL-0x80)
        assert c['details']['raw_source_and_partial_owner_fields_remain_declared_not_camera_values']
        before98=int(c['details']['owner98_before'],16)
        assert before98==int.from_bytes(bytes([seed])*4,'little')
        assert a.old.word(owner,0x98)==(1-before98)&0xffffffff
        assert c['details']['owner80_90_before_hex']==(bytes([seed])*20).hex()
        assert f[0x14:0x28]==bytes([seed])*20
        flagword=int(c['details']['native_stored_flag_word'],16)
        assert flagword&255==1 and a.old.word(f,0x6c)==a.old.word(owner,0x80)==flagword
        assert f[0x4da]==f[0x4db]==1
        assert f[0x4c4]==flag
        assert not c['new_parameter_reference_completed']
        assert not c['real_MAIN_1080_crop_bitstream_hardware_or_recovery_proven']
        # The pixel field does not equal the mode0 classification helper's2176.
        assert es[2]['native_geometry_helper_arguments'][0]['a1']==(1088 if mode else 2176)
        if flag:
            refstops+=1
            assert c['native_frame_parameter_handle']==a.old.HANDLES+4==a.old.word(f,0x4c8)
            assert es[-1]['stop']==a.STOPS[0x131c20]
            assert es[-1]['SP']==hex(a.prev.SP_CALL-0x80)
            assert not c['frame_producer_returned_to_actual_caller']
            assert all(hex(a.IMAGE+x) in es[-1]['CODE_observed_PCs'] for x in (0x131b48,0x131c18,0x131c1c))
            assert hex(a.IMAGE+0x131c24) not in es[-1]['CODE_observed_PCs']
            assert flagword==0x82009f01
        else:
            returned+=1
            assert c['native_frame_parameter_handle']==a.old.word(f,0x4c8)==0
            assert c['frame_producer_returned_to_actual_caller']
            assert es[-1]['stop']==a.STOPS[0x1441e4]
            assert es[-1]['SP']==hex(a.prev.SP_CALL) and es[-1]['V0']==hex(a.old.FRAME)
            assert all(hex(a.IMAGE+x) in es[-1]['CODE_observed_PCs'] for x in (0x131cf4,0x1351c4,0x1441d8))
            assert flagword==0xd7d7d701
    assert returned==refstops==3
    for c in j['crop_cases']:
        es=c['events'];events+=es;assert len(es)==2
        height=c['declared_visible_height'];assert height in (1080,1088)
        candidate=next(x for x in sources if x['seed']==c['seed'] and x['source_label']==c['source_label'] and x['kind']==c['source_kind'])
        common=bytearray.fromhex(candidate['common_input_hex'])
        assert a.old.word(common,0x10)==1080
        struct.pack_into('<I',common,0x10,height)
        assert common.hex()==c['common_input_hex'] and candidate['codec_input_hex']==c['codec_input_hex']
        assert bytes.fromhex(c['codec_input_hex'])[0x22]==1
        cfg=bytes.fromhex(c['config_after_hex'])
        assert struct.unpack_from('<HH',cfg,0x38)==(119,67)
        assert cfg[0x47]==c['native_vertical_crop']==(4 if height==1080 else 0)
        assert c['native_crop_unit']==2 and c['native_block_units']==[120,68]
        assert c['reconciled_height']==1088-cfg[0x47]*2==height
        assert es[1]['native_crop_divisions']==[{'numerator':1088-height,'unit':2}]
        assert c['geometry_and_crop_entries_separate_from_full_HEVC_function']
        assert not c['SPS_or_actual_HEVC_bitstream_hardware_acceptance_proven']
        assert all(hex(a.IMAGE+x) in es[1]['CODE_observed_PCs'] for x in (0x18ce6c,0x198478,0x198500,0x18ce78))
    assert len(events)==44
    for e in events:
        assert e['original_image_all_pages_and_entire_stack_exact_poststate_checked']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x1f8550:'complete original frame constructor entry',0x1f8740:'native fresh parameter-handle zero store',
        0x1f87b8:'original complete frame constructor return',0x1318b0:'native frame width-unit store',
        0x1318bc:'native frame height-unit store',0x1318f4:'native frame pixel-width store',
        0x1318f8:'native frame pixel-height store',0x131a50:'old owner record load before update',
        0x131ac4:'native single-byte flag scratch store',0x131ad8:'native full-word scratch load retains padding',
        0x131ae8:'native owner record update',0x131dc4:'native owner98 state update',
        0x131c1c:'native source parameter handle assignment before reference',
        0x131c20:'unexecuted GP/reference increment boundary',0x131cf4:'original no-update frame producer return',
        0x1441e4:'unexecuted external virtual-table lookup',0x18cdf0:'original height units-minus-one store',
        0x18ce6c:'original vertical crop helper JAL',0x1984cc:'native crop unit selection',
        0x198500:'native vertical crop division',0x18ce78:'native crop result byte store',
        0x144074:'static frame allocation type5',0x144078:'static frame request size4f0',
        0x14407c:'static frame allocation dispatcher call not executed here'}
    rows=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off))
        rows.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str,'meaning':meaning})
    descriptor=struct.unpack_from('<4I',blob,0x2132d0)
    assert descriptor[0]==5 and descriptor[2]==161792 and descriptor[3]==128 and descriptor[2]//descriptor[3]==0x4f0
    im.write_json(STAGE/'native-provenance-and-boundaries.json',{'created_utc':now,'VCD_sha256':im.sha(blob),
        'instructions':rows,'type5_descriptor':{'file_offset':'0x2132d0','words':list(descriptor),'block_bytes':0x4f0},
        'stage84_manifest_sha256':im.sha(historical.read_bytes()),'stage84_sealed_files_verified':17,
        'classification_helper_height_is_not_frame_pixel_height':True,
        'numeric1088_minus_native_crop4_times_native_unit2_matches1080':True,
        'actual_same_MAIN_instance_SPS_bitstream_or_hardware_proven':False,
        'frame_type5_allocation_and_new_parameter_reference_unexecuted':True,
        'owner_history_fields_and_flag_padding_not_validated_as_camera_values':True})
    review={'status':'PASS_NATIVE_FRAME_HEADER_AND_CROP_NUMERIC_AGREEMENT_WITH_REFERENCE_BOUNDARY',
        'created_utc':now,'prior_sealed_files_verified':11,'historical_stage84_files_verified':17,
        'frame_cases':6,'crop_cases':4,'formal_phases':44,'no_update_native_returns':3,'new_reference_stops':3,
        'native_fresh_frame_parameter_handle_initially_zero':True,
        'native_crop1080_result4_unit2_and_aligned1088_result0':True,
        'review_scope':'Same-agent source/saved-result review plus exact full-image/page/stack checks by execution harness. No independent engine or real camera acceptance.',
        'actual_same_MAIN_SPS_video_hardware_IRQ_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_complete_fresh_frame_header_and_native_crop_numeric_reconciliation'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage92封存11件和canonical复核，stage84裁剪源封存17件复核；仅Mac，16项/授权保持。',
            '原新帧构造及嵌套初始化完整返回，参数句柄原为0。原帧头实写120/68及1920/1088；关闭更新原返回实际caller，开启更新原赋句柄后停GP引用增加前，没有预置新帧参数所有权。',
            '6帧/4裁剪44阶段。原HEVC几何打包和纵向助手在1080输入给crop4/unit2，1088控制给0；1088-4*2=1080仅数值对应，真实同MAIN实例/SPS/视频/硬件仍缺。',
            '细化前轮：模式0分类助手2176不等实际帧头字段1088。owner历史字段和临时标志3填充字节仍依赖声明旧值，未清零或称实机缺陷。静态类型5/4f0请求与ROM块长对应，帧分配仍未执行。全部IRQ/MAIN/硬件与同机恢复未验。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/frame-crop-results.json'
    g['latest_stage_evidence']['stage93_frame_header_crop_reconciliation']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'scope':'Complete native fresh frame construction and declared-input header; update stops before new reference, no-update returns. Independent native crop arithmetic matches1080, not same MAIN/SPS/hardware proof.',
        'authorization_unchanged':True,'goal_complete':False}
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':'stage92-native-geometry-builder-and-IRQ-scope',
        'finding':'Mode0 classification helper argument2176 must not be substituted for frame pixel height; original frame header remains1088 in this declared case. Native crop4/unit2 matches1080 numerically, actual MAIN/SPS unproved.',
        'hardware_or_visible_picture_proven':False})
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage93_scope']='6帧/4裁剪44阶段：原新帧构造及header1920/1088、原crop4/unit2数值对应1080；更新赋句柄后停GP引用前，关更新原返回。类型5原分配/历史owner真实值/同MAIN/SPS/硬件与恢复未证。'
    g['next_safe_offline_actions'].append('stage93后优先核对原类型5/4f0帧分配→原构造→原caller实链，ROM类型5块长4f0已静态对应，减少声明帧地址来源；同时追owner28/2a/31/32/35/36/37/80..90/98的实际初始化与非空参数引用/IRQ/外层虚分派和MAIN。1088-4*2=1080为两原路径参数数值一致，不替代同实例SPS/视频；不将分类助手2176当实际帧高、不清未分类填充字节来通过。全部主录/同机恢复验收保持。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 原新帧、帧头与1080参数关系](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原frame构造/header与crop4×2核对1088→1080，6帧/4裁剪44阶段；更新指针先赋后停GP引用前，非真实MAIN/SPS/视频/硬件恢复，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage93-native-frame-header-crop/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
