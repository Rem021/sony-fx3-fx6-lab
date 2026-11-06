#!/usr/bin/env python3
"""Seal actual callpath evidence and completed cached query; preserve all gates."""
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
    assert canonical.read_bytes()==before==(s.parent/'stage68-current-USB-associations/goal-status-after.json').read_bytes()
    review=json.loads((s/'completed-evidence-review.json').read_text())
    assert review['bounded_fragments']==58 and review['live_target_producer_lease_preserved']
    assert review['fresh_root_query_count']==1 and review['fresh_root_matches']==0
    assert review['public_manifest_five_file_hashes_verified'] and review['disk_candidate_count']=='UNKNOWN_NOT_QUERIED'
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(s.relative_to(h.ROOT))
    obs={'recorded_utc':now,'host':'DESKTOP-262CR7C existing FX3 Codex session',
         'root_task_user_relay':'User replied 已发送; new matching message and processing observed, then completed response.',
         'root_public_retrieval':'Six exact public filenames received via UU; final counter67; five manifest entries independently verified on Mac.',
         'root_private_files':'Not transferred; hashes are Windows-reported only.',
         'argument_task_file':'C:/Users/owo/Documents/Codex/2026-10-16/rea-2/outputs/fx3-current-root-cache-20261026T172200Z/WINDOWS_ARGUMENT_AUDIT.txt',
         'argument_task_source_sha256':review['task_sha256'],
         'argument_task_transfer':'UU exact remote filename, send success, final counter68',
         'argument_task_submission':'PENDING_USER_RELAY; one new paste attempt not visible in Windows input; no send click/message.',
         'argument_task_scope':'Read existing ordinary C project records only; no new PnP/CIM/SetupAPI or device queries.',
         'CUA_timeout':'Native file-transfer action observation timed out; rebind showed path/selection completed, then sent exactly once.',
         'keyboard_cause':'UNKNOWN; no IME explanation or settings/security change assumed.',
         'camera_interface_auth_mode_driver_media_module_WBI_flash':False}
    im.write_json(s/'UU-task-observation.json',obs)
    summary={'created_utc':now,'status':'GUEST_16M_WRITER_JOINED_TO_NATIVE_CHANNEL_PATH_CACHED_ROOT_QUERY_NO_MATCH',
             'callpath_cases':review['callpath_cases'],'bounded_fragments':58,
             'new_guest_BL':'av-cam+0x21eeb4','original_rate_query_target':16000000,
             'target_source_FH_identity_preserved':True,'target_lease_live_at_original_kernel_boundary':True,
             'true_Sony_failure_cleanup_or_rollback':False,'actual_downstream_encoder_rate_consumption':False,
             'root_cached_queries':1,'root_cached_matches':0,'disk_candidate_count':'UNKNOWN_NOT_QUERIED',
             'argument_audit_task':'Transferred, user relay pending','camera_operations':False,
             'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json',summary)
    old=json.loads(before);g=json.loads(before)
    g['updated_utc']=now;g['latest_stage']=s.name
    g['research_activity']='guest_native_channel_callsite_private16M_publication_and_completed_Windows_cached_root_receipt'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['已观察用户代发根任务执行完成，6件public收回并独立核对5件清单；新1条精确instanceid connected查询无根，树/磁盘分支未运行，候选UNKNOWN。不同时间CIM与PnP差异原因未知。',
                 '客体新增第二处原BL接编译适配器；原构造/队列→FH匹配行386/预置→严格私有写者→原查询16M→原通道/资源消息/LIRO绑定OSAL至未执行内核IRQ锁，在同一原请求/栈继续。9例58段含5个自定义拒绝边界，对照不写。',
                 '目标引用保持live1，无模拟消费/完成/复原；原局部通道返回false分支仍汇合复制输出，不把0当安全失败清理。原模块/文件、FH描述和完整16项要求保留。',
                 '仅既有记录参数审计任务已UU传出待用户代发，不重新查询设备。真实共享同步/代次/副本区域用途/下游全消费/OSAL内核/硬件主录和全部同机备份恢复尚未闭合。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage69_native_16M_callpath']={
        'readme':rel+'/README.md','review':rel+'/completed-evidence-review.json','summary':rel+'/summary.json',
        'callpath':rel+'/run-same-instance-slices-20261026/channel-callpath-results.json',
        'original_failure_branch':rel+'/original-channel-failure-branch.json',
        'Windows_root_receipt':rel+'/from-windows-root-review/receipt.json','handoff':rel+'/UU-task-observation.json',
        'scope':'Guest-only writer admission and original getter/channel/message path, not actual hook deployment or downstream hardware; fresh cached root query no match.',
        'authorization_unchanged':True,'goal_complete':False}
    for req in g['requirements']:
        if req['id'] in ('G02','G08','G10','G16'):
            req['evidence'].extend([rel+'/run-same-instance-slices-20261026/channel-callpath-results.json',
                                    rel+'/original-channel-failure-branch.json',rel+'/from-windows-root-review/receipt.json'])
            req['stage69_scope']='客体通道调用处已真实调用严格16M写者与原查询，再以原实参进入原通道/OSAL至未执行内核锁；2目标/2对照/5自定义拒绝、58段。非实机hook，控制/代次仍fixture，副本用途/共同同步/完整下游消费与失败清理/硬件和恢复未验收。Windows新精确instanceid查询零根，接口/磁盘仍UNKNOWN；仅记录参数审计任务已传待代发。'
    dep=g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({'status':'root_cache_query_completed_no_match_argument_record_audit_transferred_pending_user_relay',
                'latest_host_state':'UU online, root clarification completed and public files retrieved; offline argument audit file transferred, message not observed.',
                'camera_present_in_latest_snapshot':'17:50 UTC PnPUtil exact current instance filter no match; 17:15 UTC CIM same hash Present=True. Physical presence/cause UNKNOWN.',
                'connected_disk_candidates':'UNKNOWN_NOT_QUERIED; no fresh PnPUtil root for tree/disk branch',
                'native_query_count':1,'native_query_count_scope':'Latest root clarification only; historical snapshots retained separately.',
                'latest_completed_native_query_count':1,'pending_native_task_tag':'FX3_PNP_ARGUMENT_AUDIT_OFFLINE_ONLY',
                'awaiting_user':'Relay transferred offline argument audit read-file instruction in existing Windows Codex session.',
                'awaiting_result':'Then retrieve fx3-pnp-argument-audit-20261026T181000Z/public; no new device queries authorized by that task.',
                'root_cache_receipts_retrieved':True,'public_receipts_retrieved':True,
                'argument_audit_receipts_retrieved':False,'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False})
    g['next_authorized_cached_metadata_action'].update({
        'action':'Await user relay of transferred existing-record argument audit; inspect its results before deciding any further bounded cached inventory. Do not repeat PnPUtil/CIM or open interfaces in that audit.',
        'current_external_dependency':'Root query finished with no match, six public files retrieved; actual argument and time difference audit file transferred, not submitted yet.',
        'whole_goal_blocked':False,'active_query_ready':False,'active_query_permission_request':False})
    g['next_safe_offline_actions'][0]+=' stage69已在客体原通道调用处接入16M写者和原查询；接下来保留live生产者，追实际下游参数消费者和真实内核服务，不用该新增查询冒充Sony后续自然消费。'
    g['next_safe_offline_actions'][4]+=' stage69局部通道false分支仍复制输出，下一步追原Open错误传播及ID/handler/map-node归还，不能把自定义拒绝入口或返回0当作安全回退。'
    g['next_safe_offline_actions'][5]='已完成用户代发根缓存补查，1条精确instanceid connected查询无匹配，设备树/磁盘分支未运行；仅已有记录参数审计文件已传Windows待代发。检查JSON/WQL/实际argv和stdout/时间，不重跑设备查询。真实接口/设备控制请求/认证/模块/WBI/刷写仍未授权。'
    for key in ('objective','authorization','completion_rule'):assert g[key]==old[key]
    assert len(g['requirements'])==16 and [(r['id'],r['status']) for r in g['requirements']]==[(r['id'],r['status']) for r in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g);after=(s/'goal-status-after.json').read_bytes()
    index=h.ROOT/'README.md';ib=index.read_bytes()
    entry='- [2026-10-26 FX3私有16M进入原通道请求链](<work/sony-firmware-20261024/stage69-native-16M-callpath/README.md>)：客体新增调用处写入/原查询16M后进入原OSAL至内核锁边界，9例58段；原失败清理未证。Windows根补查零匹配，既有记录参数审计已传待代发，实机主录/救援仍未验收。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n')==1
    ia=ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes(after);index.write_bytes(ia)
    files=[{'path':str(p.relative_to(h.ROOT)),'bytes':p.stat().st_size,'sha256':im.sha(p.read_bytes())}
           for p in sorted(s.rglob('*')) if p.is_file()]
    final={'schema':'fx3-stage69-native-channel16M-and-cached-root/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
           'previous_manifest_sha256':'ac0ed314014b7dce271478f3038d0cbe8b27be7ea94906886c93565524da3880',
           'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
           'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
           'operations':summary,'requirements_retained':16,'authorization_unchanged':True}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((h.ROOT/x['path']).read_bytes())==x['sha256'] for x in files)
    assert canonical.read_bytes()==after and index.read_bytes()==ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'native_cases':9,'bounded_fragments':58,'goal_complete':False}))


if __name__=='__main__':main()
