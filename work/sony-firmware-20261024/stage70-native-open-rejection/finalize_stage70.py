#!/usr/bin/env python3
"""Seal Mac-only rejection/Close evidence without changing full completion gates."""
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
    assert before==canonical.read_bytes()==(s.parent/'stage69-native-16M-callpath/goal-status-after.json').read_bytes()
    review=json.loads((s/'completed-evidence-review.json').read_text())
    assert review['formal_cases']==3 and review['bounded_fragments']==28
    assert review['case_counts']=={'unexecuted_storage_release':2,'file_initial_conditional_local_release':1}
    assert review['static_factory_initial_bytes_zero']==668848 and review['static_buffer_field_slots_verified']==6
    assert not review['actual_cleanup_or_recording_or_recovery_proven']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'previous_goal_turn_classification':'progress',
        'previous_evidence':'stage69 sealed50 files and canonical verified before this turn; actual guest callpath plus completed cached query.',
        'Windows_start_of_turn_observation':'Old completed root-query response remained visible; no new argument-audit message observed.',
        'latest_user_instruction':'现在Windows不能用了，你先拿Mac这边研究。',
        'Windows_actions_after_that_instruction':0,'current_operational_scope':'Mac offline only; do not access UU/Windows until user makes it available again.',
        'argument_audit':'Existing transferred task retained; not observed submitted/executed; deferred, no current relay request.',
        'native_experiments':'3 formal cases/28 bounded fragments; 2 unexecuted storage-release boundaries, 1 conditional file-initial local Close.',
        'original_message_callback_full_error_propagation_retry_modified16M_rollback':'NOT_VERIFIED',
        'current_camera_scope':'Cached PnP authorization unchanged; no active camera access.',
        'camera_interface_auth_mode_driver_media_module_WBI_flash':False}
    im.write_json(s/'coordinator-observations.json',observation)
    summary={'created_utc':now,'status':'MAC_ONLY_ORIGINAL_FH_REJECTION_CONDITIONAL_CLOSE_AND_FILE_INITIAL_PROVENANCE',
        'cases':3,'bounded_fragments':28,'unchanged_original_matcher_result':-1,'common_sentinel':255,
        'pools_before_pending_callback':[7,5,5],'old_storage_unexecuted_release_cases':2,
        'file_initial_conditional_local_release_cases':1,'conditional_local_pools_after_Close':[8,6,6],
        'file_initial_factory_bytes_zero':668848,'real_callback_cleanup_retry_or_modified16M_rollback':False,
        'Windows':'Deferred by user; Mac offline only','camera_operations':False,
        'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='Mac_only_original_Open_rejection_and_conditional_explicit_Close_resource_scope'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['stage69封存50件与canonical复核；原FH未修改matcher/通道指令，真实no-row分支返回-1→common FF→factory0，到未执行请求回调。队列0但借出池7/5/5/树注册仍在，不认定完整生命周期结束或实机泄漏。',
                 '原诊断expect enc_close与虚表槽/原Close路径核对。独立Close在A5/C3字段输入到未执行存储释放入口；未清零未补成功。原文件初值对应的零输入仅局部归还8/6/6/空树，原查找null；不运行第二次Close/合法重试/真实回调。',
                 '原固定factory668848字节和6槽1040..104f均零，给零输入补原文件来源；不代替实际装载/WBI/冷启动/当前owner/复用/共享同步或已修改16M回退。3例28段与两份早期运行保留。',
                 '用户当前明确Windows不可用只用Mac，之后Windows/UU操作0；既有记录参数审计已传但未观察提交/执行，延后而非当前等待代发。完整16项与相机缓存授权不变，硬件主录/同机恢复仍未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage70_native_open_rejection']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'formal_result':rel+'/run-storage-scope-controls-20261026/open-rejection-results.json',
        'original_diagnostic_contract':rel+'/failure-contract-static.json',
        'initial_file_provenance':rel+'/storage-file-initial-provenance.json',
        'user_scope_observation':rel+'/coordinator-observations.json',
        'scope':'Unmodified unsupported FH rejection, independent partial/conditional Close, static file initial bytes; not actual callback lifecycle or modified runtime recovery.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-storage-scope-controls-20261026/open-rejection-results.json',
                                    rel+'/storage-file-initial-provenance.json',rel+'/failure-contract-static.json'])
            req['stage70_scope']='Mac原FH no-row至未执行回调，ID/MAIN/map-node仍7/5/5，原文expect enc_close。独立Close两旧值到未执行1040/1048存储释放，原文件初值对照才局部归还8/6/6/树空/lookup null；未运行回调/合法重试/第二次Close，非已修改16M回退。六槽字段零与factory668848字节文件初值核对不等于真实冷启动/WBI/复用或硬件验收。当前用户要求仅Mac，Windows延后。'
    g['current_user_operational_constraint']={'source':'latest direct user message','instruction':'Windows unavailable; use Mac for now.',
        'current_scope':'Mac offline research and reversible local preparation only',
        'Windows_UU_device_polling_or_task_dispatch':'Deferred; do not access until user makes Windows available again.',
        'whole_goal_paused':False,'camera_authorization_expanded':False}
    dep=g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({'status':'deferred_by_user_Windows_unavailable_Mac_only',
        'latest_host_state':'UNKNOWN_CURRENT; not checked after user deferred Windows. Previous completed snapshots retained as historical.',
        'UI_scope':'No UU/Windows interaction while latest Mac-only instruction applies.',
        'pending_native_task_tag':None,'deferred_task_tag':'FX3_PNP_ARGUMENT_AUDIT_OFFLINE_ONLY',
        'argument_audit_state':'Transferred earlier, no submission/execution observed; deferred.',
        'awaiting_user':None,'awaiting_result':None,
        'resume_condition':'User makes Windows available again; then inspect actual state before resuming any existing task.',
        'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False})
    g['next_authorized_cached_metadata_action'].update({
        'scope':'Deferred by latest user instruction; Mac offline research only for now.',
        'action':'Do not poll or access UU/Windows or request relay now. Retain prepared existing-record argument audit; resume only after user makes Windows available again and current state is checked.',
        'current_external_dependency':'User says Windows unavailable; no task/process confirmed live or being awaited.',
        'whole_goal_blocked':False,'active_query_ready':False,'active_query_permission_request':False})
    g['next_safe_offline_actions'][4]+=' stage70原失败到未执行回调仍有借出注册，旧值Close依赖1040/1048存储字段，仅文件初值对照局部归还；继续完整生产/转交/清除、原回调/Close队列/共享锁/全部消费者，不把此对照当16M修改后恢复或真实冷启动。'
    g['next_safe_offline_actions'][5]='当前用户明确Windows不可用只用Mac；不访问UU/Windows、不轮询设备、不再催代发。已有记录参数审计文件和过去缓存结果保留为延后材料，待用户恢复可用后先核实实际状态；当前继续Mac离线主录、缓冲/失败/恢复路径研究。'
    for key in ('objective','authorization','completion_rule'):assert g[key]==old[key]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3原失败与条件Close范围](<work/sony-firmware-20261024/stage70-native-open-rejection/README.md>)：原FH失败至未执行回调仍有借出注册；3例28段，两个旧值Close到存储释放边界，原文件初值对照仅局部归还。Windows按用户要求延后，仅Mac；实机主录/回退/救援仍未验收。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage70-Mac-only-original-rejection-conditional-close/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':'417033856d0b31e1019bd64b932199d826ebdefcc9321a96dae1334fae8c1d8e',
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'Mac_only':True,'goal_complete':False}))


if __name__=='__main__':main()
