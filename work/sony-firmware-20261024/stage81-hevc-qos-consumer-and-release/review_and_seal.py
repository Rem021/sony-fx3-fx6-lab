#!/usr/bin/env python3
"""Seal HEVC-specific partial consumer and independent release-mask evidence."""
from pathlib import Path
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE))
import hevc_consumer as a
im,BASE,ROOT,IMAGE=a.im,a.BASE,a.ROOT,a.IMAGE


def main():
    im.volume();s=STAGE;assert not (s/'final-receipt.json').exists()
    prior=BASE/'stage80-vcd-pending-and-timing/final-receipt.json'
    assert im.sha(prior.read_bytes())=='d4b7808e3690b8c5fea35237dad9a0bfd164bb92052b96bc9d0c46f944e11c9f'
    previous=json.loads(prior.read_text())['files'];assert len(previous)==35
    for row in previous:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    before=(s/'goal-status-before.json').read_bytes();canonical=BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    result=s/'run-20261026/hevc-consumer-results.json';j=json.loads(result.read_text())
    assert j['status']=='PASS_HEVC_SPECIFIC_TARGET_CONSUMPTION_AND_BOUNDED_RELEASE_MASKS'
    assert j['source_receipt']['script_sha256']==im.sha((s/'hevc_consumer.py').read_bytes())
    assert (result.parent/'executed-source.py').read_bytes()==(s/'hevc_consumer.py').read_bytes()
    origin=prior.parent/'run-final-observer-20261026/pending-timing-results.json'
    assert j['source_receipt']['stage80_result_sha256']==im.sha(origin.read_bytes())
    assert j['source_receipt']['corrected_observer_source_sha256']==im.sha((a.p.STAGE/'pending_timing.py').read_bytes())
    blob=a.p.a.v.VCD_PATH.read_bytes()
    assert im.sha(blob)==j['source_receipt']['VCD_sha256']==im.PINS[str(a.p.a.v.VCD_PATH.relative_to(BASE))]
    assert j['source_identity']['HEVC_GOP_path']==im.cstring(blob,0x21cf70)
    assert j['source_identity']['AVC_path_excluded']==im.cstring(blob,0x21eb38)
    assert '/enc/HEVC/gop_ctrl_hevc.cxx' in j['source_identity']['HEVC_GOP_path']
    assert struct.unpack_from('<I',blob,0xd9364)[0]&0xffff==0x8022
    assert struct.unpack_from('<I',blob,0xd936c)[0]&0xffff==0xcf70
    assert len(j['target_cases'])==10 and len(j['release_cases'])==6 and j['bounded_phases']==22
    for seed in (0xa5,0xc3):
        cases=[x for x in j['target_cases'] if x['seed']==seed]
        assert len(cases)==5
        assert [x['decoded_GOP_target_after'] for x in cases]==[16000000,20000000,16000000,16000000,16000000]
        for x in cases:
            assert x['backend_flags_unchanged'] and x['source_parameter_buffer_unchanged']
            assert not x['full_GOP_callback_actual_main_binding_or_hardware_proven']
            first=x['events'][0]
            assert first['entry']==hex(IMAGE+0xd9204)
            b=bytes.fromhex(x['GOP_before_hex']);z=bytes.fromhex(x['GOP_after_hex'])
            assert b[:0xc8]==z[:0xc8] and b[0xcc:]==z[0xcc:]
            if x['declared_control']=='backend40_off':
                assert first['reason']=='boundary: before_other_HEVC_updates' and b==z
            elif x['declared_control']=='parameter_bit29_off':
                assert first['reason']=='boundary: after_target_before_other_fields' and b==z
                assert hex(IMAGE+0xd949c) not in first['pcs']
            elif x['source_label']=='native query tail with existing handle':
                assert first['reason']=='boundary: before_other_HEVC_updates' and b==z
                assert x['timing_getter']['raw8_hex']=='80a90300481f0000'
                assert len(x['events'])==3 and all(e['reason']=='returned' for e in x['events'][1:])
            else:
                assert hex(IMAGE+0xd949c) in first['pcs'] and hex(IMAGE+0xd94c8) in first['pcs']
        releases=[x for x in j['release_cases'] if x['seed']==seed]
        assert len(releases)==3
        for x in releases:
            assert x['parameter_buffer_unchanged'] and not x['physical_free_hardware_ack_or_recovery_completion_proven']
            b=bytes.fromhex(x['context_before_hex']);z=bytes.fromhex(x['context_after_hex'])
            assert b[:0x130]==z[:0x130] and b[0x134:]==z[0x134:]
            if x['kind']=='two_declared_flags':
                assert len(x['events'])==2 and x['events'][0]['reason']=='returned'
                assert x['events'][1]['reason']=='boundary: before_unknown_GP_release_state'
                assert z[0x130:0x134]==bytes(4) and z[0x10c:0x110]==struct.pack('<I',a.p.HANDLE)
                assert x['handle_still_present_after_last_flag_clear']
            else:
                assert x['events'][0]['reason']=='returned'
    for x in j['target_cases']+j['release_cases']:
        for e in x['events']:
            assert not e['memory_read_write_hooks_installed'] and e['memory_read_write_access_trace'] is None
            assert e['original_image_input_and_declared_handle_unchanged']
            assert e['stack_outside_declared_0x200byte_frame_window_unchanged']
            assert not e['native_output_PC_or_service_return_adapter']
    assert not j['Windows_UU_camera_operations'] and not j['goal_complete'] and not j['persistent_write_release']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(ROOT))
    review={
        'created_utc':now,'status':'PASS_HEVC_TARGET_FRAGMENT_AND_RELEASE_MASK_SCOPE',
        'prior_sealed_files_verified':35,'target_cases':10,'release_cases':6,'bounded_phases':22,
        'HEVC_source_identity_checked_AVC_not_substituted':True,
        'both_update_flags_required_for_target_copy_to_declared_GOP_c8':True,
        'getters_leave_update_flags_and_buffer_unchanged':True,
        'last_flag_zero_before_unknown_GP_release_handle_still_present':True,
        'full_GOP_initialization_Main_binding_physical_release_hardware_recording_or_recovery_proven':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False,
        'review_scope':'Same agent source/PC/poststate check; no independent emulator or physical acceptance.',
    }
    im.write_json(s/'completed-evidence-review.json',review);im.write_json(s/'summary.json',review)
    im.write_json(s/'coordinator-observations.json',{
        'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage80 sealed35 files/canonical verified; pending drained but backend state remains.',
        'new_evidence':'HEVC-specific GOP target fragment consumes captured target only with both flags. Independent getter/release cases distinguish retrieval, flag clearing and unexecuted real release.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'requirements_retained':16,'goal_complete':False,'persistent_write_release':False,
    })
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_HEVC_specific_GOP_target_consumption_and_release_mask_boundaries'
    g['progress_audit']={
        'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':[
            'stage80封存35件与canonical复核；沿用修正CODE-only/完整内存前后核对，无内存读写钩子或Sony字节/结果修改。',
            '按原源码引用绑定HEVC gop_ctrl_hevc而非相似AVC分支；原d9204/d949c读取后端40及参数bit29，把原20M字复制到声明GOP+c8。任一标志关则跳过，原缓冲/标志保持，在其它字段前停，不是完整GOP/真实MAIN。',
            '原尾参数谓词/指针getter完整返回原8字节位置不清标志；独立清40有剩余位则保留句柄，声明两位组合清最后位写0后停原GP释放前，句柄/原缓冲仍在。组合不作自然运行状态证明。',
            '10组消费/6组清理22阶段核对。实际GOP构造/代次同步/分配释放/硬件Open-Start/成片和全部同机恢复仍缺，16项与Mac-only授权不变。',
        ],'completion_not_claimed':True,
    }
    g['latest_stage_evidence']['stage81_hevc_qos_consumer_and_release']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json',
        'result':rel+'/run-20261026/hevc-consumer-results.json',
        'scope':'Original HEVC target fragment and independent release wrappers, captured trial RAM inputs and declared GOP; not actual MAIN/full controller/hardware or recovery.',
        'authorization_unchanged':True,'goal_complete':False,
    }
    for req in g['requirements']:
        if req['id'] in ('G02','G10','G11','G16'):
            req['evidence'].append(rel+'/run-20261026/hevc-consumer-results.json')
            req['stage81_scope']='HEVC专属原GOP目标消费需后端40及参数bit29，20M字进入声明GOP+c8，单标志关不更新；只跑目标段，非真实MAIN/完整GOP。独立清最后位先写0再到未执行GP释放，句柄/缓冲仍在。10消费6清理22阶段，不证明硬件/资源归还/恢复。'
    g['next_safe_offline_actions'].append(
        'stage81继续HEVC GOP+c8的真实码率控制消费者、GOP/流构造与MAIN绑定，及后端缓冲引用/提交回复/最终释放。不可把AVC相似代码作HEVC证据、声明两位清理组合作自然运行顺序、flags0或getter当回收完成。原GP/释放/硬件及全部实机与同机恢复要求保留。')
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint',
                'external_dependencies','current_guest_adapter_prototype'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 HEVC目标消费与清理边界](<work/sony-firmware-20261024/stage81-hevc-qos-consumer-and-release/README.md>)：原HEVC GOP消费两层更新位及目标字，清最后位仍未释放句柄；10消费/6清理22阶段，完整GOP/硬件/主录/恢复未证，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={
        'schema':'fx3-stage81-hevc-consumer-release/1','created_utc':now,'volume_uuid':im.VOLUME,
        'files':files,'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':review,'requirements_retained':16,'authorization_unchanged':True,
    }
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'hardware_recording_or_recovery_proven':False,'goal_complete':False}))


if __name__=='__main__':main()
