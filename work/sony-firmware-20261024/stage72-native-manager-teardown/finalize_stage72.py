#!/usr/bin/env python3
"""Seal Mac-only local exit evidence without relaxing the complete goal."""
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
    previous=s.parent/'stage71-native-buffer-record-fifo/final-receipt.json'
    assert im.sha(previous.read_bytes())=='0418d0922bf7b2b6fd433009d01e6072ca20c894a114bb2378a4a71b1ebbf101'
    assert before==canonical.read_bytes()==(previous.parent/'goal-status-after.json').read_bytes()
    for row in json.loads(previous.read_text())['files']:
        assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    review=json.loads((s/'completed-evidence-review.json').read_text())
    result_path=s/'run-through-original-ret-20261026/manager-teardown-results.json'
    result=json.loads(result_path.read_text())
    assert review['cases']==8 and review['total_bounded_fragments']==40
    assert review['prior_sealed_files_verified']==19
    assert result['source_receipt']['script_sha256']==im.sha((s/'manager_teardown.py').read_bytes())
    assert (result_path.parent/'executed-source.py').read_bytes()==(s/'manager_teardown.py').read_bytes()
    assert not review['physical_release_completed_consumers_main_recording_or_recovery_proven']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage71 sealed19 files and canonical checked; original ROI numeric FIFO and independent12-byte clear/output handoff.',
        'latest_user_instruction':'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'new_scope':'Original local master-descriptor exit and reference-cache cases; static lineage to request fields.',
        'local_queue_count_interpretation':'Count1 means one queued numeric record; available/in-flight/real ownership semantics not established.',
        'outer_return0_is_not_a_free_receipt':True,
        'first_attempt':'Offline guest allow-range omitted a native ret; failed source/state retained, then boundary extended4 bytes. Not a firmware failure or brick.',
        'full_goal_requirements_retained':16,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_ORIGINAL_MANAGER_EXIT_AND_STATIC_REQUEST_FIELD_LINEAGE',
        'cases':8,'bounded_fragments':40,'ROI_queue_unchanged_in_all_cases':True,
        'zero_ID_negative_control':'Original helper error1, outer clears master and returns0; not an actual allocated-buffer state.',
        'declared_shared_reference2':'Original decrements to1, retains cache, skips unit-free request; not a leak claim.',
        'declared_last_reference1':'Original clears cache then stops before original unit-free body; master still live.',
        'static_output58_to_request68':True,'static_output60_low32_to_request70':True,
        'address_translation_submission_hardware_release_or_consumers_complete':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_original_manager_local_exit_reference_counts_and_static_request_reference_lineage'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage71封存19件与canonical复核；本轮两组旧存储填充值、4类声明输入共8例40段原函数执行，未修改Sony指令或伪造返回/回复。',
                 '原manager局部退出在无主句柄时返回0；零ID负向对照原助手错误1、外层清主描述符仍返回0。不得以外层返回0或描述符清空验收实际释放；不把合成负向对照当实机缺陷。',
                 '声明缓存引用2降1保留缓存且跳过底层请求；最后引用1降0先清缓存，再停于27c1a8原释放入口前，主描述符仍保留。全例本地ROI队列保持，计数不直接判作在途/泄漏/可用缓冲。',
                 '原输出58/60字段静态接到请求68/70，途中条件地址转换/同步/提交与完成均未执行。完整16项和Mac-only约束保持，Windows/UU/相机操作0；主录和同机恢复未完成。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage72_native_manager_teardown']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'result':rel+'/run-through-original-ret-20261026/manager-teardown-results.json',
        'scope':'Original local exit on declared descriptors/cache only; last reference stops before unit-free body; static output-to-request field correspondence.',
        'outer_return0_is_not_physical_release_or_full_cleanup':True,
        'authorization_unchanged':True,'goal_complete':False}
    g['corrections_to_prior_stage']['stage71_master_descriptor_static_scope_extended']={
        'prior':'stage71 separate209b8/c0/c4 descriptor and teardown were static only.',
        'new_scope':'Now executed only declared local exit/cache cases. Actual allocation, consumers, physical release and hardware reply are not proven.',
        'nonempty_queue_semantics':'A queued record is not automatically an in-flight frame, leak or available-buffer count.',
        'evidence':rel+'/run-through-original-ret-20261026/manager-teardown-results.json',
        'old_sealed_files_unchanged':True}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-through-original-ret-20261026/manager-teardown-results.json',
                                    rel+'/completed-evidence-review.json'])
            req['stage72_scope']='Mac原局部退出8例40段；无主句柄与零ID负向对照均可外层return0，后者助手错误后仍清描述符。声明共享引用2降1不实际释放；最后引用1降0清缓存后停在27c1a8原释放体前。全部队列不变，其数量不证明占用/在途/泄漏。输出58/60到请求68/70仅静态字段对应，真实转换/提交/消费者/底层释放/主录与同机恢复未证，完整16项保持。'
    g['next_safe_offline_actions'][1]+=' stage72已静态接到出站请求68/70字段，下一步追真实地址映射、提交后的消费者和完成通知；当前不能把原数值当硬件地址，或把队列计数当所有权证明。'
    g['next_safe_offline_actions'][4]+=' stage72局部退出return0/主描述符清空不保证底层释放，零ID负向对照说明需保留助手错误与实际完成凭据；声明引用2降1及最后引用释放入口前停止不是实机成功释放。继续原释放传输/完成及完整调用者，不能提前回收代码/数据或宣称救砖可用。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):
        assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies']
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 原管理退出与释放凭据](<work/sony-firmware-20261024/stage72-native-manager-teardown/README.md>)：Mac离线8例40段；外层返回0/描述符清空不保证实际释放，共享引用与最后引用分支分开核对。输出字段接到请求仅静态，真实消费者/物理释放/主录和救援未证；Windows延后。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage72-Mac-only-original-manager-exit-and-reference-scope/1',
        'created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':im.sha(previous.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'Mac_only':True,'goal_complete':False}))


if __name__=='__main__':main()
