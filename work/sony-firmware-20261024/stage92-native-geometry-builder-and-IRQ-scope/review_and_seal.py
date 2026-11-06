#!/usr/bin/env python3
"""Review full native geometry returns, keeping real IRQ/hardware acceptance open."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import geometry_builder as a
im,BASE,ROOT=a.im,a.BASE,a.ROOT


def main():
    im.volume();assert not (STAGE/'final-receipt.json').exists()
    prior=BASE/'stage91-native-type4-first-cache-buffer/final-receipt.json'
    assert im.sha(prior.read_bytes())==a.PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    run=STAGE/'run-initial-20261027';j=json.loads((run/'geometry-builder-results.json').read_text())
    assert not (run/'failed-attempt.json').exists()
    assert j['status']=='PASS_NATIVE_COMPLETE_GEOMETRY_BUILDER_RETURNS_THROUGH_ACTUAL_FRAME_CALLER'
    assert j['source_receipt']['script_sha256']==im.sha((STAGE/'geometry_builder.py').read_bytes())
    assert (run/'executed-source.py').read_bytes()==(STAGE/'geometry_builder.py').read_bytes()
    path=a.prev.prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH;blob=path.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(path.relative_to(BASE))]
    assert blob[0x24817a:0x24817c]==bytes([1,2])
    assert len(j['cases'])==9 and j['bounded_phases']==27 and len(j['observer_calibration'])==3
    for p in j['observer_calibration']:
        e=p['event'];assert p['numerator']==121
        assert hex(a.IMAGE+0x13489c) in e['CODE_observed_PCs']
        assert e['native_interrupts']==([] if p['declared_divisor'] else [18])
    events=[];updated=0;odd=0
    for c in j['cases']:
        mode=c['declared_raw_mode_byte0e'];flag=c['declared_update_byte50'];units=c['declared_units'];seed=c['seed']
        assert mode in (0,1) and flag in (0,0x10) and seed in (0xa5,0xc3) and c['declared_raw_byte10']==0
        if units==[119,67]:
            odd+=1;assert mode==1 and flag==0x10
        else:assert units==[120,68]
        pages={int(k,16):bytes.fromhex(v) for k,v in c['final_pages'].items()}
        assert len(pages)==7 and all(len(v)==4096 for v in pages.values())
        owner=pages[a.old.OWNER_PA];source=pages[a.old.SRC_PA];packet=pages[a.old.PACK_PA]
        assert a.old.word(owner,0x9c)==c['native_owner_mode9c']==mode
        assert source[0xe]==mode and source[0x10]==0 and source[0x50]==flag
        assert struct.unpack_from('<HH',source,0x14)==tuple(units)
        assert struct.unpack_from('<HH',packet,0xec)==(units[0]-1,units[1]-1)
        data=bytes([2,1 if mode else 2,0,0,30,34 if mode else 17,0,1])
        assert owner[8:16]==data and c['native_geometry8_hex']==data.hex()
        assert owner[0x20:0x24]==bytes(4) and owner[0x1c:0x20]==bytes(4)
        es=c['events'];events+=es;assert len(es)==3
        assert es[0]['stop']=='returned_via_original_jr_ra'
        assert es[1]['stop']==a.STOPS[0x1315d0] and es[1]['SP']==hex(a.SP_SEL-0x60)
        assert es[2]['stop']==a.STOPS[0x131888] and es[2]['SP']==hex(a.SP_CALL-0x80)
        assert es[2]['RA']==hex(a.IMAGE+0x1351c0)
        dims=(units[0]*16,units[1]*(16 if mode else 32))
        assert [(x['a0'],x['a1']) for x in es[1]['native_geometry_helper_arguments']]==[dims]
        assert all(hex(a.IMAGE+p) in es[1]['CODE_observed_PCs'] for p in (0x1315bc,0x1315c8,0x13380c,0x1338bc))
        assert all(hex(a.IMAGE+p) in es[2]['CODE_observed_PCs'] for p in (0x1441d0,0x1351b8,0x131844))
        if flag:
            updated+=1
            assert struct.unpack_from('<HH',owner,0x24)==tuple(units)
            assert [(x['a0'],x['a1']) for x in es[2]['native_geometry_helper_arguments']]==[dims]
            assert all(hex(a.IMAGE+p) in es[2]['CODE_observed_PCs'] for p in
                (0x131e60,0x13380c,0x66bb8,0x1338bc,0x131e68,0x134fa0,0x1441c8))
        else:
            assert owner[0x24:0x27]==bytes(3) and owner[0x27]==seed
            assert not es[2]['native_geometry_helper_arguments']
            assert hex(a.IMAGE+0x13380c) not in es[2]['CODE_observed_PCs']
        assert c['full_geometry_return_and_actual_JAL_frame_binding']
        assert not c['outer_mode_setup_message_work_and_actual_scheduling_completed']
        assert not c['real_MAIN_cropped_dimensions_hardware_or_recovery_proven']
    assert len(events)==27 and updated==5 and odd==1
    for e in events:
        assert e['original_image_all_pages_and_entire_stack_exact_poststate_checked']
        assert not e['memory_read_write_hooks_installed'] and not e['native_interrupts']
        assert e['PC_observation_may_include_annulled_delay_slots'] and not e['MMIO_instruction_patch_or_fake_return']
    public=json.loads((STAGE/'public-encoding-reference.json').read_text())
    assert public['HTTP_status']==200 and public['bytes']==1711
    assert public['matched_encodings']['70020026']=='mtic $2,$0'
    assert not public['third_party_code_executed'] and not public['full_source_body_saved']
    assert public['executed_fetch_script_sha256']==im.sha((STAGE/'fetch_encoding_reference.py').read_bytes())
    assert not any(j[k] for k in ('Windows_UU_camera_operations','goal_complete','persistent_write_release'))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT))
    md=a.cs.Cs(a.cs.CS_ARCH_MIPS,a.cs.CS_MODE_MIPS32|a.cs.CS_MODE_LITTLE_ENDIAN)
    offsets={0x1352f0:'original default-field initializer entry',0x1315ac:'declared raw mode-byte source',
        0x1315bc:'native owner mode9c store',0x1315c8:'original complete geometry call',
        0x13380c:'complete geometry body entry',0x133850:'native conditional height scaling',
        0x133878:'original classification helper call',0x134890:'original geometry divide',
        0x13489c:'calibrated annulled BREAK or actual divide-zero trap',
        0x1338bc:'original geometry return',0x131e60:'actual caller geometry builder JAL now executed',
        0x131e68:'actual setter tail after geometry return',0x134fa0:'actual wrapper tail after setter',
        0x1441c8:'actual caller reload after full geometry return',0x1441d0:'actual caller frame-wrapper JAL',
        0x9e00:'unexecuted CP0 read in IRQ-state helper',0x9e40:'unexecuted CP0 write in IRQ-state helper',
        0x5b618:'unexecuted lock-ID creator calls IRQ-state helper',0x5d5b4:'unexecuted returned lock-ID store',
        0x140d04:'unexecuted GP lock-ID read',0x140d0c:'unexecuted extension encoding70000026',
        0x140d3c:'unexecuted extension encoding70020026'}
    rows=[]
    for off,meaning in offsets.items():
        ins=next(md.disasm(blob[off:off+4],a.IMAGE+off),None)
        rows.append({'VA':hex(a.IMAGE+off),'word_hex':blob[off:off+4].hex(),
            'instruction':ins.mnemonic+' '+ins.op_str if ins else 'extension_not_decoded_by_selected_Capstone_mode',
            'meaning':meaning})
    im.write_json(STAGE/'native-provenance-and-IRQ-boundaries.json',{'created_utc':now,
        'VCD_sha256':im.sha(blob),'instructions':rows,
        'geometry_no_body_gap_or_fake_return':True,'outer_mode_message_and_frame_header_unexecuted':True,
        'IRQ_CP0_extension_controller_state_and_lock_ID_initialization_unexecuted':True,
        'GNU_encoding_match_does_not_identify_FX3_processor_or_hardware_state':True,
        'public_source':public['source_url'],'PSP_emulator_behavior_imported':False})
    review={'status':'PASS_COMPLETE_NATIVE_GEOMETRY_RETURNS_TO_ACTUAL_FRAME_CALLER',
        'created_utc':now,'prior_sealed_files_verified':14,'formal_cases':9,'formal_phases':27,
        'observer_calibrations':3,'actual_caller_full_geometry_return_cases':5,
        'odd_units_native_ceil_control':1,'native_owner_mode_field_not_host_set':True,
        'geometry_no_internal_body_gap':True,
        'review_scope':'Same-agent source and saved-result review; exact all-page/full-stack checks by execution harness. No independent engine or camera acceptance.',
        'actual_IRQ_scheduling_MAIN_cropped_height_hardware_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(STAGE/'completed-evidence-review.json',review)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=STAGE.name
    g['research_activity']='Mac_only_complete_native_geometry_return_and_IRQ_applicability_audit'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage91封存14件及canonical复核；仅Mac，16项/授权保持。',
            '原默认函数/原元数据0e与10分类写owner9c，原完整13380c及助手返回；实际144124几何setter自然返回1441c8后原JAL绑定Frame/owner/raw，消除旧131e60几何内部缺口。两个外层入口仍分开，完整帧头/消息调度未执行。',
            '9例27阶段及3除法/取消延迟槽校准；120/68在原助手为1920/1088，模式0控制为1920/2176，119/67控制1904/1072仍有相同分行结果。不是可见1080或成片证明，不能混同模式字节与实际拍摄模式。',
            '公开GNU固定版本测试匹配MTIC/MFIC编码，CP0/锁ID创建及控制器状态仍未验收；不拿PSP或编码相同代替FX3硬件。全部MAIN/硬件/音视频/同机恢复要求保留。'],
        'completion_not_claimed':True}
    result=rel+'/run-initial-20261027/geometry-builder-results.json'
    g['latest_stage_evidence']['stage92_complete_geometry_and_IRQ_scope']={'readme':rel+'/README.md',
        'review':rel+'/completed-evidence-review.json','result':result,
        'IRQ_audit':rel+'/native-provenance-and-IRQ-boundaries.json',
        'scope':'Complete native geometry bodies and actual setter returns/frame JAL on declared metadata and owned descriptors. Outer mode message/scheduling/frame header and visible1080 crop unproved; IRQ hardware applicability unproved.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11'):
            req['evidence'].append(result)
            req['stage92_scope']='9例27阶段，原owner默认/原模式9c分类及完整几何助手返回，实际caller经setter回原JAL；119/67等单位向上取整控制。1920/1088内部参数不代替可见1080，真实模式/帧头/MAIN/IRQ/硬件和恢复未证。'
    g['next_safe_offline_actions'].append('stage92后继续原131818完整帧头对原几何和有效区域的消费，核对1088内部网格到1080可见高度的裁剪字段及真实模式/MAIN绑定。几何内部不再人为跳过；两个外层入口/消息调度仍未证。GNU编码匹配不代表FX3 IRQ/CPU身份，保留CACHE/CP0/MTIC/锁ID真实初始化缺口及全部实机/恢复验收。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 完整几何返回与IRQ适用范围](<'+str(STAGE.relative_to(ROOT))+'/README.md>)：原几何完整返回接实际帧JAL，9例27阶段；内部1920×1088不代替可见1080，真实模式/帧头/MAIN/IRQ及硬件恢复未验，仅Mac。'
    assert entry not in text;text=text.replace(marker,marker+'\n'+entry+'\n',1)
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(text)
    files=[]
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append({'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':im.sha(raw)})
    im.write_json(STAGE/'final-receipt.json',{'schema':'fx3-stage92-native-geometry-and-IRQ-scope/1',
        'created_utc':now,'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,
        'previous_manifest_sha256':a.PRIOR_SHA,'operations':review,
        'mutable_progress':{'before_sha256':im.sha(before),'after_sha256':im.sha(canonical.read_bytes())},
        'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(index.read_bytes()),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_unchanged':True})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((STAGE/'final-receipt.json').read_bytes()),
        'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
