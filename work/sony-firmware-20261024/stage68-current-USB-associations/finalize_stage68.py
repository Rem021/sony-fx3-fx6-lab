#!/usr/bin/env python3
"""Seal completed evidence; distinguish a transferred task from its execution."""
from pathlib import Path
import datetime
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();s=STAGE;im=h.im
    assert not (s/'final-receipt.json').exists()
    before=(s/'goal-status-before.json').read_bytes();canonical=h.BASE/'GOAL_STATUS.json'
    assert before==canonical.read_bytes()==(s.parent/'stage67-connected-native-pnp/goal-status-after.json').read_bytes()
    review=json.loads((s/'completed-evidence-review.json').read_text())
    assert review['previous_sealed_files_verified']==27 and review['all_four_present_OK_error0']
    assert review['current_CIM_USB_roots_matching_prior_identity']==1 and review['current_CIM_Sony_DSC_disk_nodes']==3
    assert review['original_handler_RAM_cases']==40 and review['root_clarification_result']=='NOT_RETRIEVED_NOT_CLAIMED'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    observation={'recorded_utc':now,'host':'DESKTOP-262CR7C, existing Windows FX3 Codex session',
                 'previous_user_relay':'User said 已发送; the presence-crosscheck message and completed report were visibly observed.',
                 'retrieved_presence_public_files':5,'retrieval_confirmed_by':'UU received status/counter60 plus local files',
                 'clarification_transfer_confirmed_by':'UU remote root filename, sent status, counter61, ordinary C destination',
                 'clarification_source_sha256':review['root_clarification_source_sha256'],
                 'clarification_remote_file':'C:/Users/owo/Documents/Codex/2026-10-16/rea-2/outputs/fx3-presence-crosscheck-20261026T165500Z/WINDOWS_ROOT_CLARIFICATION.txt',
                 'clarification_submission':'PENDING_USER_RELAY; requested asynchronously after verified file transfer',
                 'latest_remote_view':'Presence-crosscheck completed response remains visible; no clarification user bubble/processing observed.',
                 'keyboard':'Prior repeated remote paste/type attempts did not appear in Windows input; no exact cause established.',
                 'new_keyboard_retries_or_settings_permissions_changes':False,
                 'task_execution_or_root_results_claimed':False,'camera_scope':'Cached PnP metadata only, unchanged',
                 'camera_operations':False}
    im.write_json(s/'UU-task-observation.json',observation)
    summary={'created_utc':now,'status':'CIM_CURRENT_IDENTITY_REVIEWED_ORIGINAL_HANDLER_RAM_ONLY_ROOT_FOLLOWUP_PENDING',
             'CIM_snapshot_utc':'2026-10-26T17:15:31.086Z','CIM_queries':1,'USB_roots_matching_previous_identity':1,
             'current_Sony_DSC_disk_nodes':3,'all_four_present_OK_error0':True,'VID':'054C','PID':'0DA1',
             'current_parent_interface_started_driver_details':'UNKNOWN_PENDING_FOLLOWUP',
             'earlier_exact_filter_difference_cause':'UNKNOWN','bounded_handler_cases':40,
             'original_kernel_memcpy_body_executed_in_emulator':True,'root_followup_task_transferred':True,
             'root_followup_message_observed':False,'root_followup_result':'PENDING_USER_RELAY',
             'camera_interface_commands_or_flash':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='completed_current_cached_CIM_identity_and_bounded_original_INQUIRY_handler_RAM_observation'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['已取回并复核1条CIM查询的5件公开结果；1个同摘要USB根和3个Sony DSC磁盘节点均Present=True/OK/错误码0，实际VID/PID054C0DA1。未把早先零匹配改写为断线或协议故障。',
                 '当前CIM并未查询父子/接口/Started/驱动；澄清根节点唯一与磁盘目标唯一的不同，后续缓存任务已UU传出，待用户代发读取指令；未声称执行或得到当前绑定。',
                 '原7.02 inquiry_std与原内核memcpy在受限RAM里40组输入通过；正常复制配置身份数据并更新状态/sense。没有USB分派、实际驱动、真实LUN或Linux启动，查询亦不能保证机内零状态变化。',
                 '16项完整目标和相机缓存只读权限原样保留，未打开接口或执行相机命令；实际1080p29.97 HEVC主录、音画长录、同机健康备份及独立恢复仍未验收。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage68_current_USB_associations']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'Windows_public_receipt':rel+'/from-windows-presence/receipt.json',
        'original_handler_RAM_result':rel+'/inquiry-handler-emulation.json','handoff_observation':rel+'/UU-task-observation.json',
        'scope':'CIM current nodes, no current relation/driver result yet; bounded already-dispatched handler RAM only.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G01','G08','G16'):
            req['evidence'].extend([rel+'/from-windows-presence/receipt.json',rel+'/inquiry-handler-emulation.json'])
            req['stage68_scope']='CIM当前身份摘要与1USB/3磁盘节点已补；父子/接口/驱动尚未查询，任务已传待代发。原INQUIRY函数40组RAM仿真不是实机协议、固件身份、主录或恢复验收。'
    dep=g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({'status':'current_CIM_identity_reviewed_root_cache_task_transferred_pending_user_relay',
                'latest_host_state':'UU online, Windows FX3 Codex presence report complete; clarification file transferred, new message not observed.',
                'camera_present_in_latest_snapshot':'CIM Present=True for exact prior-root hash; no body protocol identity/version queried',
                'CIM_USB_root_count':1,'CIM_current_disk_node_count':3,
                'connected_disk_candidates':'3 current CIM disk nodes, relation/interface/driver readiness UNKNOWN',
                'latest_completed_native_query_count':1,'pending_native_task_tag':'FX3_ROOT_CACHE_CLARIFICATION',
                'awaiting_user':'Relay the already transferred root clarification read-file instruction in existing Windows Codex session.',
                'awaiting_result':'Then retrieve fx3-current-root-cache-20261026T172200Z/public',
                'presence_public_receipts_retrieved':True,'root_cache_receipts_retrieved':False,
                'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False})
    g['next_authorized_cached_metadata_action'].update({
        'action':'Await user relay of the transferred root clarification; observe the existing Windows session, then retrieve fresh root/child PnPUtil public receipts into a new stage. Do not repeat CIM or exact hardware-ID query.',
        'current_external_dependency':'Clarification file transferred via UU, but not yet observed as a Windows Codex message; no root followup execution/result claimed.',
        'whole_goal_blocked':False,'active_query_ready':False,'active_query_permission_request':False})
    g['next_safe_offline_actions'][5]='后续缓存根/子节点任务已传Windows，等待用户代发读取指令并核对新消息和结果；取新目录public回执，分开根唯一和实际诊断接口唯一，保留当前/历史及早先筛选差异UNKNOWN。不重跑CIM或精确硬件ID筛选，不把多个磁盘等同多台相机；相机接口、设备控制请求、认证/模块/WBI/刷写仍未授权。'
    for key in ('objective','authorization','completion_rule'):assert g[key]==old[key]
    assert len(g['requirements'])==16
    assert [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3当前缓存身份与查询处理范围](<work/sony-firmware-20261024/stage68-current-USB-associations/README.md>)：新CIM快照1个同摘要USB根和3磁盘节点均在线正常；父子/驱动后续任务已传待代发。原查询处理函数40组RAM仿真通过，不能替代实际接口、刷写或救砖验收。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage68-current-USB-cache-and-bounded-handler/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
           'previous_manifest_sha256':'74a63d7ac2cbb7167c5b11c53f5a54e0e3b57447d1d17b4455b6e1f20f59bd8a',
           'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
           'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
           'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/r['path']).read_bytes())==r['sha256'] for r in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'root_followup':'pending_user_relay','goal_complete':False}))


if __name__=='__main__':main()
