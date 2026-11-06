#!/usr/bin/env python3
"""Seal completed evidence; keep the submitted crosscheck result explicitly pending."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    im,root,s=h.im,h.ROOT,STAGE
    im.volume()
    assert not (s/'final-receipt.json').exists()
    review=json.loads((s/'completed-evidence-review.json').read_text())
    assert review['previous18_sealed_files_and_canonical_verified']
    assert review['new_original_USB_files_verified']==7 and review['initial_inquiry_templates']==3
    assert review['matched_roots']==0 and review['disk_candidate_count']=='UNKNOWN_NOT_QUERIED'
    assert review['crosscheck_new_message_and_processing_observed_in_UU']
    before=(s/'goal-status-before.json').read_bytes()
    canonical=h.BASE/'GOAL_STATUS.json'
    assert canonical.read_bytes()==before==(h.BASE/'stage66-native-pnp-cache-review/goal-status-after.json').read_bytes()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel=str(s.relative_to(root))
    observation={'observed_utc':now,'host':'Existing DESKTOP-262CR7C, original FX3 Codex session',
        'user_reports':['已接好，保持 MSC','已发送读取交叉核对任务文件的指令'],
        'connected_filter_task':'Completed, one query exit0, exact VID054C PID0DA1 present filter no match',
        'crosscheck_task_file_sha256':'c3a5c02b8e1f3609a49b73d7a7e47571d73d29f45780e443ce85ede3da37f078',
        'crosscheck_task_file_sent_via_UU':True,
        'crosscheck_message_observed':True,
        'crosscheck_latest_UI':'New relay message, assistant scope acknowledgment, processing counter and stop button visible',
        'crosscheck_result_at_seal':'PENDING_NOT_RETRIEVED_OR_REVIEWED',
        'crosscheck_Windows_public_path':'C:/Users/owo/Documents/Codex/2026-10-16/rea-2/outputs/fx3-presence-crosscheck-20261026T165500Z/public',
        'keyboard_finding':'Followup paste/type not visible in Windows input; exact cause not established; user relay succeeded',
        'keyboard_mapping_permissions_drivers_or_execution_policy_changed':False,
        'CUA_only_for_UI':True,'camera_authorization':'Windows cached PnP only, unchanged',
        'camera_interface_auth_mode_driver_media_module_WBI_flash':False}
    im.write_json(s/'UU-crosscheck-observation.json',observation)
    summary={'created_utc':now,'status':'EXACT_CONNECTED_FILTER_NO_MATCH_USB_STATIC_EVIDENCE_COMPLETE_CROSSCHECK_PENDING',
        'connected_filter_queries':1,'exact_filter_matched_roots':0,'disk_candidate_count':'UNKNOWN_NOT_QUERIED',
        'new_public_files_received':5,'new_original_USB_files':7,'original_inquiry_templates':3,'pointer_aliases':5,
        'source_module_functions_static_only':3,'crosscheck_result':'PENDING',
        'camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old,g=json.loads(before),json.loads(before)
    g['updated_utc'],g['latest_stage']=now,s.name
    g['research_activity']='authorized_cached_connected_filter_and_original_USB_protocol_static_correlation'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress','basis':[
        'stage66封存18件/canonical复核；用户确认MSC接好后，唯一一次原生connected+054C0DA1缓存筛选退出0但无匹配，5件脱敏回执已取回；磁盘分支未运行、候选数UNKNOWN，不推断相机物理未连接。',
        'Sony厂商/FX3型号CIM缓存交叉核对文件已UU传出，用户代发读取指令后可见新消息和处理状态；最终结果仍待回传，未声称已有不同PID、当前绑定或驱动通过。',
        '官方7.02固定哈希镜像读取7件原USB模块/库/脚本；没有挂载或执行。原inquiry_std等3函数的CALL26字段/符号范围与哈希核对，原模板3份和5个ABS64指针别名区分。',
        '原初始响应模板revision1.00而非7.02、product初为空格；公开vendor源码逐LUN配置和事件携带LUN与原函数选点对应。普通INQUIRY不可当实际固件版本/同机指纹，USB父节点不可代替接口选择。',
        '微软SPTI对齐、描述符及通用存储栈重试/超时定义已复核；未来设备控制请求与当前缓存权限区分，未承诺单次总线传输或硬性3秒结束。',
        '完整16项要求和授权保留；无相机接口/命令/认证/模式/驱动/卡/模块/WBI/刷写，实际主录/音画长录、健康备份与恢复仍未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage67_connected_native_pnp']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'connected_snapshot':rel+'/from-windows-public/receipt.json','USB_original_extraction':rel+'/usb-original-extraction.json',
        'USB_source_correlation':rel+'/usb-inquiry-source-correlation.json','crosscheck_observation':rel+'/UU-crosscheck-observation.json',
        'scope':'Exact current hardware-ID filter no match; static original USB modules/templates only. Vendor/model crosscheck submitted, final result pending.',
        'goal_complete':False,'authorization_unchanged':True}
    for req in g['requirements']:
        if req['id'] in ('G01','G08','G16'):
            req['evidence'].extend([rel+'/from-windows-public/receipt.json',rel+'/usb-inquiry-source-correlation.json'])
            req['remaining']+=' stage67当前精确VID/PID筛选无匹配但不证明物理未连，厂商/型号交叉核对最终结果待取；原INQUIRY模板通用revision1.00和LUN配置仅静态对应，不能替代当前接口、实机程序指纹、主录或同机恢复验收。'
    dep=g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({'status':'user_reports_MSC_connected_exact_filter_no_match_vendor_model_crosscheck_processing',
        'user_response':'已接好，保持MSC；已发送读取交叉核对文件指令',
        'latest_host_state':'UU online, Windows FX3 Codex crosscheck submitted and processing observed',
        'camera_present_in_latest_snapshot':'UNKNOWN; exact connected hardware-ID filter has zero matches only',
        'connected_disk_candidates':'UNKNOWN_NOT_QUERIED','latest_completed_native_query_count':1,
        'pending_native_task_tag':'FX3_PRESENCE_CROSSCHECK_20261026',
        'awaiting_user':None,'awaiting_result':'Vendor/model filtered cached crosscheck public receipt',
        'public_receipts_retrieved':True,'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False})
    g['next_authorized_cached_metadata_action'].update({
        'action':'Poll the already submitted Windows vendor/model filtered cached crosscheck; retrieve its public receipts into a new phase and review. Do not repeat the exact filter or restart the task merely because a UI observation is delayed.',
        'current_external_dependency':'User reports MSC connected; exact054C0DA1 current filter no match. Vendor/model cached crosscheck was user-relayed and its processing is visibly observed; final result pending.',
        'whole_goal_blocked':False,'active_query_ready':False,'active_query_permission_request':False})
    g['next_safe_offline_actions'][5]='继续观察已提交的Sony厂商/FX3型号缓存交叉核对任务，另目录取public回执，区分当前/历史、实际VID/PID与当前接口。不要因观察延迟重启或重跑精确筛选，不改驱动/策略。接口、设备控制请求、认证/模块/WBI/刷写仍未授权。'
    for key in ('objective','authorization','completion_rule'):
        assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g)
    after=(s/'goal-status-after.json').read_bytes()
    index=root/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3重新连接筛选与原USB身份模板](<work/sony-firmware-20261024/stage67-connected-native-pnp/README.md>)：精确当前ID筛选无匹配，厂商/型号交叉核对已提交待结果；原7件USB组件、3模板/5指针别名核对，通用INQUIRY不能代替固件版本和当前接口验证。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage67-connected-cache-original-USB/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
        'previous_manifest_sha256':'0369c6a18e2c319d58120b0d7467d309a45b93d340e84f9e5207c49a0eea229f',
        'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
        'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
        'operations':{'completed_connected_filter_queries':1,'original_USB_files_read':7,'original_module_or_kernel_execution':False,
        'crosscheck_file_sent_and_user_submission_observed':True,'crosscheck_result_at_seal':'PENDING',
        'camera_interface_commands_auth_mode_driver_media_module_WBI_flash':False,
        'actual_recording_or_recovery':False,'goal_complete':False,'persistent_write_release':False}}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((root/r['path']).read_bytes())==r['sha256'] for r in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
        'latest_stage':s.name,'crosscheck_result':'pending','requirements_retained':16,'goal_complete':False}))


if __name__=='__main__':
    main()
