#!/usr/bin/env python3
"""Seal ROI record semantics and bounded output handoff; all hardware gates stay."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();s=STAGE;im=h.im;assert not (s/'final-receipt.json').exists()
    canonical=h.BASE/'GOAL_STATUS.json';before=(s/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(s.parent/'stage70-native-open-rejection/goal-status-after.json').read_bytes()
    review=json.loads((s/'completed-evidence-review.json').read_text())
    assert review['total_bounded_fragments']==72 and review['prior_sealed_files_verified']==18
    assert review['queue_raw_word_pair_not_pointer_validation'] and review['COMMON12_clear_preserves_upper32_and_output_pointer']
    assert not review['actual_main_recording_callback_buffer_origin_consumer_exit_or_recovery_proven']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage70 sealed18 files and canonical verified; original rejection/conditional Close and exact static-file zero provenance.',
        'latest_user_instruction':'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'new_scope':'Original numeric ROI-map record queue plus independent copy-to-output/COMMON12-clear tail.',
        'named_queue':'roi_map_queue, original diagnostic strings verified',
        'semantic_correction':'Old unexecuted storage-release boundary name does not mean physical free; enqueue primitive is now directly observed.',
        'scope_exclusions':'Actual referenced memory origin, ownership, output-consumer completion, real target later flag branch, physical deallocation, main recording and recovery are not proved.',
        'full_goal_requirements_retained':16,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_ORIGINAL_ROI_RECORD_FIFO_AND_INDEPENDENT_HANDOFF',
        'FIFO_cases':2,'FIFO_fragments':56,'handoff_cases':2,'handoff_fragments':16,'total_bounded_fragments':72,
        'named_queue':'roi_map_queue','COMMON_clear_bytes':12,'output_pointer_retained':True,'COMMON_second_word_upper32_retained':True,
        'target_static_row8a_flag':0,'target_later_flag_branch_executed':False,
        'actual_buffer_validation_deallocation_or_complete_Close':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_original_ROI_map_record_FIFO_and_output_reference_handoff_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage70封存18件/canonical复核；原22da80/22d9b0实际执行两组容量/满空/回绕/FIFO56段，原日志名roi_map_queue，数值记录未指向已验证缓冲，操作返回不证明实际分配/释放/指针验证。',
                 '两组原构造/原入出队及独立21ef30..21ef60片段16段，源COMMON指针/低32位共12字节清零，输出仍持有指针，高32位保留。没有先前分配/后续条件/实际消费者退出或硬件目标请求验收。',
                 '原目标表行386与UHD431的8a字段0，原复制与条件局部核对，不能把独立记录对照当目标走flag1证明。独立manager209b8/c0/c4描述符与退出分支只有静态依据。',
                 'stage70未执行边界storage-release称呼细化为ROI记录入队，不读成物理释放。完整16项和仅Mac操作约束保持，Windows/UU/相机操作0，主录及同机恢复未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage71_native_buffer_record_fifo']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'FIFO_result':rel+'/run-generic-log-decoder-20261026/buffer-record-fifo-results.json',
        'handoff_result':rel+'/run-handoff-20261026/handoff-tail-results.json',
        'original_ROI_names_and_master_scope':rel+'/roi-map-name-and-backing-scope.json',
        'scope':'Original local numeric record queue and independent output handoff, not pointer validation, physical release, full Close or target hardware execution.',
        'authorization_unchanged':True,'goal_complete':False}
    g['corrections_to_prior_stage']['stage70_storage_release_boundary_name']={
        'prior':'before_unexecuted_manager_storage_release at av-cam+22da80 was an unexecuted boundary label.',
        'refinement':'Original function now verified to enqueue two raw words into roi_map_queue; it is not proof of physical free or referenced-buffer validity.',
        'evidence':rel+'/roi-map-name-and-backing-scope.json','old_sealed_files_unchanged':True}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-generic-log-decoder-20261026/buffer-record-fifo-results.json',
                                    rel+'/run-handoff-20261026/handoff-tail-results.json',
                                    rel+'/roi-map-name-and-backing-scope.json'])
            req['stage71_scope']='Mac原roi_map_queue两数值字段FIFO2例56段通过，非物理释放/指针验证。独立转交2例16段，COMMON清12字节但输出保留指针、原第二字高32保留；语义/消费者退出仍缺。目标row386字段8a=0仅静态局部，不把独立对照称目标flag1执行。底层主描述符只有静态范围；主录/运行时回退/同机恢复和完整16项未完成。'
    g['next_safe_offline_actions'][1]+=' stage71独立原转交后COMMON指针清零而输出+58仍保留，继续追该输出及+60低32字段的实际消费者、完成通知和全部引用，不把队列空/源清12字节当生命周期结束；高32位语义未知，不能自行清零。'
    g['next_safe_offline_actions'][4]+=' stage71原日志将22da80称roi_map_queue记录入队，底层分配/释放不在本轮证明范围；追manager独立209b8/c0/c4描述符初始化/退出与原ROI记录来源，保留真实MAIN/回退全部要求。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies']
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 ROI记录队列与输出转交](<work/sony-firmware-20261024/stage71-native-buffer-record-fifo/README.md>)：原FIFO两组56段、独立转交两组16段；COMMON清12字节后输出仍保留指针。旧释放边界名细化为记录入队，缓冲来源/真实消费者/物理释放/主录和恢复未证；仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage71-Mac-only-original-ROI-records-and-handoff/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':'ec99ebf0d9cdbb5c80bba00e4c54635f30d57f14e4055ea8b51f08845a6e6b78',
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'Mac_only':True,'goal_complete':False}))


if __name__=='__main__':main()
