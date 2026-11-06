#!/usr/bin/env python3
"""Record native workspace ownership and separated guest-only storage scope."""
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
    prior=s.parent/'stage74-rate-result-ABI-fix/final-receipt.json'
    assert im.sha(prior.read_bytes())=='97807cfbfd33a2cedb88a71e579dec44b4b40264e66fdb63ab39502e91621a13'
    assert before==canonical.read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    review=json.loads((s/'completed-evidence-review.json').read_text())
    proof=s/'run-20261026/private-storage-results.json';result=json.loads(proof.read_text())
    assert review['total_bounded_fragments']==40 and result['bounded_fragments']==37
    assert review['original_workspace_not_exclusive_scratch'] and not review['actual_target_natural_collision_proven']
    assert review['guest_target_workspace_other_owner_and_guards_unchanged']
    assert review['fixed56_result_ABI_retained_saved_slots_preserved']
    assert review['single_controller_guard_rejects_before_dereference']
    assert not review['actual_owned_allocation_shared_lock_completed_consumers_main_recording_or_recovery_proven']
    assert result['source_receipt']['script_sha256']==im.sha((s/'private_storage.py').read_bytes())
    assert (proof.parent/'executed-source.py').read_bytes()==(s/'private_storage.py').read_bytes()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    files_needed={'writer_source':s/'resource_alias.c','writer_object':proof.parent/'resource_alias.a64.o',
                  'adapter_source':s/'channel_adapter.c','adapter_object':proof.parent/'channel_adapter.a64.o'}
    bundle={k:{'path':str(v.relative_to(h.ROOT)),'sha256':im.sha(v.read_bytes())} for k,v in files_needed.items()}
    correction={'recorded_utc':now,'status':'NATIVE_WORKSPACE_USE_PROVEN_EXCLUSIVE_SCRATCH_NOT_ESTABLISHED',
        'earlier_model_storage':'COMMON+e010..e10f',
        'original_evidence':'Original226364 copies/edits256 bytes there and publishes it atCOMMON+e000; direct caller21ebb8.',
        'actual_target_natural_path_collision_or_concurrency_proven':False,
        'guest_change':'Single-controller trial slot113a1000, fixed controller113a0000; original workspace and other owner unchanged in bounded target path.',
        'remaining_shared_state':'COMMON+e000 selection can still be cleared/replaced by original writers; real locks/epoch/mode exclusion and consumers not bound.',
        'real_camera_owned_allocation_or_deployment_proven':False,
        'previous_stage74_result_ABI_fix_retained':True,'old_files_modified_or_deleted':False,
        'evidence':rel+'/native-workspace-and-shared-selection-audit.json'}
    im.write_json(s/'workspace-ownership-correction.json',correction)
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage74 sealed21 files/canonical verified; old24 caller quarantined and56 result container checked.',
        'new_evidence':'Original create-start-param path owns/uses the earlier256-byte trial workspace. Dedicated guest copy removes that storage assumption; original selected-pointer synchronization remains open.',
        'verification':'2target/2independent native workspace/2regression/1wrong-controller cases,40 bounded fragments.',
        'latest_user_operational_instruction':'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn':0,'camera_operations':False,
        'full_goal_requirements_retained':16,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_NATIVE_WORKSPACE_IDENTIFIED_GUEST_COPY_SEPARATED',
        'target_cases':2,'native_workspace_cases':2,'regression_controls':2,'controller_guard_cases':1,
        'bounded_fragments':40,'native_workspace':'COMMON+e010..e10f',
        'trial_private_slot':'113a1000; harness contract, not real camera memory',
        'target_original_workspace_other_owner_and_guards_unchanged':True,
        'retained56_container_saved_slots_intact':True,'target_rate':16000000,
        'original_selected_pointer_lock_epoch_and_all_consumers_proven':False,
        'real_owned_allocation_main_recording_or_recovery':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_original_preset_workspace_ownership_and_separated_single_controller_trial_storage'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage74封存21件/canonical核对。原226364/21ebb8与原日志证明COMMONe010起256字节有原生用途；两组独立原入口实际改写并发布该空间，不把它当原型独占空闲区，也不声称目标自然触发或发生并发缺陷。',
                 '新客体写者副本移到单控制器试验槽113a1000，限制Control地址113a0000；56结果容器保持。两组目标原路径读16M、保存槽/原工作区/另一common/两侧64字节guard保持，到原内核停点；UHD和关闭入口对照保持。',
                 '另一个未映射Control地址被BAD_ABI拒绝，未解引用且整个arena不变。共7例40段通过回读；试验槽只是harness声明，不是实际相机分配或ELF加载地址。',
                 '原函数仍可清理/替换COMMONe000选择指针，真实共享锁/配置代次/模式排斥/消费者和生命周期缺口保留。无原通道返回、硬件主录或同机恢复验收；完整16项和Mac-only/原相机授权不变。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage75_private_preset_storage']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'result':rel+'/run-20261026/private-storage-results.json',
        'controller_guard':rel+'/controller-identity-result.json',
        'native_workspace_audit':rel+'/native-workspace-and-shared-selection-audit.json',
        'compiled_guest_bundle':bundle,
        'scope':'Dedicated single-controller trial slot; original workspace use proven, actual target collision, real allocation/selection synchronization and hardware remain unproven.',
        'authorization_unchanged':True,'goal_complete':False}
    g['corrections_to_prior_stage']['COMMON_e010_trial_copy_exclusive_storage_assumption']=correction
    g['current_guest_adapter_prototype']={'stage':s.name,'bundle':bundle,'result_container_size':56,
        'private_trial_slot':'0x113a1000','only_controller':'0x113a0000',
        'scope':'UNDEPLOYABLE_GUEST_ONLY; model copy separated from original256-byte workspace. No real allocator, shared Sony lock, actual selected-pointer lifetime or hardware proof.',
        'stage74_result_ABI_fix_retained':True,'older_stage69_object':'QUARANTINED_24BYTE_RESULT_OVERWRITES_SAVED_LR',
        'camera_or_persistent_use_permitted':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-20261026/private-storage-results.json',rel+'/workspace-ownership-correction.json'])
            req['stage75_scope']='原COMMONe010..e10f有create-start-param原生用途，独占scratch未证。客体副本移至单控制器试验槽，目标16M/56结果保存槽/原工作区/其它owner/guard保持，原路径到内核边界；其它Control拒绝先于解引用。原选择指针互斥、配置代次、真实分配/消费者/主录和恢复仍缺，不将独立入口称目标碰撞或全部安全完成。'
    g['next_safe_offline_actions'][1]+=' stage75COMMONe010..e10f原生用途已证，客体副本已移到独立试验槽；这不保护COMMONe000选择指针。继续原226364/其它选择器对dff8/e000/e008的同步、模式切换、代次与全部消费者，不能将试验固定地址当机身已分配内存。'
    for key in ('objective','authorization','completion_rule','current_user_operational_constraint'):
        assert g[key]==old[key]
    assert g['external_dependencies']==old['external_dependencies'] and len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3 客体预置副本与原工作区分离](<work/sony-firmware-20261024/stage75-private-preset-storage/README.md>)：原COMMON+e010有原生用途；客体副本移至单控制器试验槽，16M/56字节返回容器/原区/其它owner/guard保持，7例40段复核。原选择指针同步与真实分配/主录/恢复未证；仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    rows=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
          for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage75-native-workspace-and-single-controller-trial-storage/1',
        'created_utc':now,'volume_uuid':im.VOLUME,'files':rows,'previous_manifest_sha256':im.sha(prior.read_bytes()),
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in rows)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(rows),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'guest_storage_only':True,'goal_complete':False}))


if __name__=='__main__':main()
