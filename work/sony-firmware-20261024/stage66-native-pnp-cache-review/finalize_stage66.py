#!/usr/bin/env python3
"""Review the public native PnP snapshot, preserve private/raw evidence boundaries."""
from pathlib import Path
import datetime
import json
import re
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    im, root, s = h.im, h.ROOT, STAGE
    im.volume()
    assert not (s/'final-receipt.json').exists()
    prior = h.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes()) == '0dd6dd689d4a8598f80add00512306a465937661c1aa2e77c4971e4a597df45b'
    sealed = load(prior)
    assert len(sealed['files']) == 64
    for row in sealed['files']:
        raw = (root/row['path']).read_bytes()
        assert len(raw) == row['bytes'] and im.sha(raw) == row['sha256']
    before = (s/'goal-status-before.json').read_bytes()
    canonical = h.BASE/'GOAL_STATUS.json'
    assert canonical.read_bytes() == before == (h.STAGE/'goal-status-after.json').read_bytes()
    assert im.sha(before) == 'd7df2cca842c5257f1da12007324fc80d0ff81e2846184a46f6e6c507263f5ee'
    p = s/'from-windows-public'
    expected = {'commands.json','node-relations.json','private-file-sha256.json','protected-files-after.json',
                'protected-files-before.json','receipt.json','report-generation-error.txt','sanitized-enumeration.txt',
                'summary.txt','token-context.json'}
    assert {x.name for x in p.iterdir()} == expected
    receipt, nodes, commands = load(p/'receipt.json'), load(p/'node-relations.json'), load(p/'commands.json')['commands']
    assert receipt['task_state'] == 'CACHED_ONLY_COMPLETE_NO_CURRENT_CONNECTED_CANDIDATE'
    assert receipt['commands'] == commands and receipt['observations'] == nodes
    assert len(commands) == 7 and all(x['exit_code'] == 0 for x in commands)
    for x in commands:
        assert x['started_utc'] <= x['finished_utc']
        assert x['command_public'].startswith(('Get-ExecutionPolicy -List','C:/Windows/System32/pnputil.exe /?','C:/Windows/System32/pnputil.exe /enum-'))
    assert [x['id'] for x in commands] == ['01-execution-policy','02-pnputil-help','03-fx3-usb','04-fx3-tree','05-fx3-disk1','06-fx3-disk2','07-fx3-disk3']
    usb, disks = nodes['usb_root'], nodes['disk_nodes']
    assert (usb['vid'],usb['pid'],usb['model']) == ('054C','0DA1','ILME-FX3')
    assert nodes['counts'] == {'matched_usb_roots':1,'cached_disk_candidates':3,'current_connected_usb_roots':0,'current_connected_disk_candidates':0}
    assert len(disks) == len(nodes['relations']) == 3 and nodes['traced_node_count'] == 4
    assert nodes['binding_status'] == 'MISSING_CURRENT_CONNECTED_CANDIDATE'
    ids = {usb['node_sha256']} | {x['node_sha256'] for x in disks}
    assert len(ids) == 4 and all(re.fullmatch('[0-9a-f]{64}', x) for x in ids)
    for disk in disks:
        assert disk['parent_sha256'] == usb['node_sha256'] and disk['parent_matches_fx3_usb_root']
        assert any(r['parent_sha256'] == usb['node_sha256'] and r['child_sha256'] == disk['node_sha256'] and r['exact_parent_hash_matches_fx3'] for r in nodes['relations'])
    for node in [usb]+disks:
        assert node['status'] == 'Disconnected'
        props = node['properties']
        assert props['DEVPKEY_Device_IsPresent'] == 'FALSE' and props['DEVPKEY_Device_HasProblem'] == 'FALSE'
        assert props['DEVPKEY_Device_ProblemCode'] == props['DEVPKEY_Device_DevNodeStatus'] == 'UNKNOWN'
        assert props['DEVPKEY_Device_DriverProvider'] == 'Microsoft'
        if node is usb:
            assert props['DEVPKEY_Device_Service'] == 'USBSTOR' and props['DEVPKEY_Device_DriverInfPath'] == 'usbstor.inf'
            assert props['DEVPKEY_Device_DriverVersion'] == '10.0.26100.9444'
        else:
            assert props['DEVPKEY_Device_Service'] == 'disk' and props['DEVPKEY_Device_DriverInfPath'] == 'disk.inf'
            assert props['DEVPKEY_Device_DriverVersion'] == '10.0.26100.9711'
    interfaces = nodes['interfaces']
    assert len(interfaces) == 4 and {x['node_sha256'] for x in interfaces} == ids
    assert all(x['enabled_state'] == 'DISABLED' and not x['raw_path_exported'] for x in interfaces)
    assert sum(x['interface_class_guid'] == '53f56307-b6bf-11d0-94f2-00a0c91efb8b' for x in interfaces) == 3
    assert not any(receipt['boundaries'].values()) and receipt['automatic_retries'] == 0
    assert receipt['privacy']['private_files_not_uploaded']
    token = load(p/'token-context.json')
    assert not token['current_token_is_administrator'] and not token['elevation_requested']
    protected_before, protected_after = load(p/'protected-files-before.json'), load(p/'protected-files-after.json')
    assert len(protected_before['files']) == len(protected_after['files']) == 13 and protected_after['all_unchanged']
    old_files = h.STAGE/'from-windows-host-attempt-2'
    for x in protected_before['files']:
        digest = im.sha((old_files/x['name']).read_bytes())
        assert x['sha256'] == digest
        y = next(r for r in protected_after['files'] if r['name'] == x['name'])
        assert y['unchanged'] and y['sha256_before'] == y['sha256_after'] == digest
    private_manifest = load(p/'private-file-sha256.json')
    assert private_manifest['private_files_not_transferred'] and len(private_manifest['files']) == 16
    assert all(re.fullmatch('[0-9a-f]{64}', x['sha256']) for x in private_manifest['files'])
    public_text = '\n'.join(x.read_text(encoding='utf-8-sig') for x in p.iterdir())
    assert not re.search(r'(?i)USBSTOR\\[^\s"]+', public_text)
    assert not re.search(r'(?i)USB\\VID_[0-9a-f]{4}&PID_[0-9a-f]{4}\\[^\s"]+', public_text)
    assert not re.search(r'\\\\\?\\', public_text)
    config = load(s/'kernel-config-presence.json')
    assert config['script_sha256'] == im.sha((s/'audit_kernel_config_presence.py').read_bytes())
    assert not config['actual7_02_dot_config_recovered'] and not config['kernel_or_downloaded_source_executed']
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(root))
    review = {
        'created_utc': now,
        'reviewer': 'Same-agent public receipt/schema/hash/graph review plus visible Windows final answer. Private raw output and instance-hash recomputation not independently reviewed on Mac.',
        'prior64_sealed_files_verified': True,
        'UU_transfer_counter': {'before':39,'after':49,'received_public_files':10},
        'Windows_task_complete_observed_in_UI': True,
        'query_count':7,'all_query_exit_codes_zero':True,
        'matched_cached_usb_roots':1,'cached_disk_children':3,'connected_candidates':0,
        'all_four_disconnected_and_interfaces_disabled':True,
        'public_graph_and_duplicate_receipt_consistent':True,
        'old13_file_hashes_before_after_and_Mac_copies_equal':True,
        'private16_file_hash_manifest_received_but_originals_not_transferred':True,
        'public_raw_identifier_and_interface_prefix_scan':'PASS bounded pattern scan; not a general privacy proof',
        'source_public_file_hashes_independently_compared_with_Windows':'NOT_PERFORMED; UU completion and file/schema/duplicate checks only',
        'host_generated_metadata_path_escaping_issue':'Some parsed path strings contain doubled backslashes; originals preserved, never executed. Canonical path below follows the observed UU directory.',
        'normalized_Windows_public_path':r'C:\Users\owo\Documents\Codex\2026-10-16\rea-2\outputs\fx3-native-pnp-20261026T160454Z\public',
        'policy_context':'This query reports LocalMachine RemoteSigned, other scopes Undefined. Earlier separate PS1 UnauthorizedAccess preserved; cross-context cause not established, no policy changed.',
        'actual_device_binding_driver_signature_hardware_or_recovery_acceptance':False,
        'original_kernel_version_marker_found_but_actual_config_not_recovered':True,
        'camera_authorization_unchanged':True,
        'user_connection_status_question':'Pending; no answer inferred from elapsed time',
        'previous_goal_turn_classification':'progress','this_goal_turn_classification':'progress',
        'goal_complete':False,'persistent_write_release':False,
    }
    im.write_json(s/'coordinator-observations.json', review)
    summary = {'created_utc':now,'status':receipt['task_state'],'public_files':10,'queries':7,
               'cached_USB_root':1,'cached_disk_children':3,'current_connected_disk_candidates':0,
               'driver_cache_USB':'usbstor.inf /10.0.26100.9444','driver_cache_disk':'disk.inf /10.0.26100.9711',
               'camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'summary.json', summary)
    old, g = json.loads(before), json.loads(before)
    g['updated_utc'],g['latest_stage'] = now,s.name
    g['research_activity'] = 'authorized_Windows_native_cached_PnP_snapshot_and_offline_kernel_config_scope_check'
    g['progress_audit'] = {'classification':'progress','previous_goal_turn_classification':'progress','basis':[
        'stage65封存64件/canonical复核；原Windows会话原生PnPUtil缓存盘点完成，7条内置查询均0退出，10件public回传。',
        '1个054C0DA1/ILME-FX3根节点与3磁盘子节点摘要关系一致；4节点断开/IsPresentFALSE，4接口禁用，当前连接候选0，未声称得到当前唯一设备绑定。',
        '本次USBSTOR和disk驱动缓存版本及报告签名者补齐，缺失ProblemCode/当前DevNode状态仍UNKNOWN；13旧文件哈希与Mac原副本一致。16私有原件留Windows，仅传哈希，Mac不宣称独立原文复核。',
        '报告写入曾因命令过长拒绝启动，已换文件写入而未重跑查询；部分报告路径转义问题保留，规范路径另记，未作为命令执行。',
        '原7.02 kernel横幅确认4.9.337-scel+/SMP PREEMPT，本Image无IKCONFIG标记，未恢复真实完整.config，不把7.00参考配置当全量精确构建。',
        '相机连接确认已另向用户请求且仍待回复；授权仅缓存PnP，完整16项主录/同步/长录/同机恢复目标保留，无接口/命令/认证/模式/驱动/模块/WBI/刷写。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage66_native_pnp_cache_review'] = {'readme':rel+'/README.md','review':rel+'/coordinator-observations.json',
        'public_receipt':rel+'/from-windows-public/receipt.json','node_relations':rel+'/from-windows-public/node-relations.json',
        'kernel_config_scope':rel+'/kernel-config-presence.json','scope':'Native cached metadata snapshot; disconnected historical relation only, no current binding or hardware acceptance.',
        'goal_complete':False,'authorization_unchanged':True}
    for req in g['requirements']:
        if req['id'] == 'G01':
            req['evidence'].append(rel+'/from-windows-public/node-relations.json')
            req['remaining'] += ' stage66新增本次缓存USB父节点到3磁盘子节点摘要关系，均断开，当前候选0；仍缺当前唯一机身绑定及实机程序指纹。'
        if req['id'] == 'G10':
            req['evidence'].append(rel+'/kernel-config-presence.json')
            req['remaining'] += ' stage66原7.02 Image版本横幅与公开源码版本族相符，但未提取实际完整.config，参考配置不可视作全量精确匹配。'
    dep = g['external_dependencies']['Windows_cached_association_handoff']
    dep.update({'status':'native_cached_snapshot_complete_all_FX3_nodes_disconnected_current_binding_missing',
                'latest_host_state':'UU online, original Windows FX3 Codex task complete; cached camera nodes all disconnected',
                'camera_present_in_latest_snapshot':False,'native_query_count':7,'connected_disk_candidates':0,
                'public_receipts_retrieved':True,'pending_native_task_tag':None,
                'awaiting_user':'Camera connection status confirmation; no response inferred',
                'cached_only_authorization_unchanged':True,'active_camera_authorization_granted':False})
    g['next_authorized_cached_metadata_action'].update({
        'action':'After user confirms camera connected in ordinary MSC, take a new native PnPUtil metadata snapshot in a new ordinary local output directory. Recheck current present parent/child/interface/driver and candidate cardinality; no interface handle, auth/mode/driver change or camera command.',
        'current_external_dependency':'Host online and native snapshot complete. Camera nodes disconnected and historical disk cardinality3, current candidates0. User connection confirmation pending.',
        'whole_goal_blocked':False,'active_query_ready':False,'active_query_permission_request':False})
    g['next_safe_offline_actions'][5] = '等待用户确认FX3普通MSC连接后，另新目录补本次原生PnPUtil当前缓存快照；保留stage66断开/3历史磁盘记录，不改写为当前连接。不要重跑旧PS1或更改策略，接口/命令/认证/模块/WBI/写入授权仍未取得。'
    for key in ('objective','authorization','completion_rule'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16 and [(x['id'],x['status']) for x in g['requirements']] == [(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s/'goal-status-after.json',g)
    after = (s/'goal-status-after.json').read_bytes()
    index = root/'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3原生PnP缓存关联复核](<work/sony-firmware-20261024/stage66-native-pnp-cache-review/README.md>)：7条查询通过、10件脱敏回执取回；USB父节点与3磁盘子节点均断开，当前候选0；主录、当前绑定及恢复仍未验收。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n') == 1
    ia = ib.decode().replace('## 相机与固件研究\n','## 相机与固件研究\n\n'+entry,1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    files = [{'path':str(x.relative_to(root)),'bytes':x.stat().st_size,'sha256':im.sha(x.read_bytes())} for x in sorted(s.rglob('*')) if x.is_file()]
    final = {'schema':'fx3-stage66-native-pnp-cache-review/1','created_utc':now,'volume_uuid':im.VOLUME,'files':files,
             'previous_manifest_sha256':im.sha(prior.read_bytes()),
             'mutable_progress':{'path':str(canonical),'before_sha256':im.sha(before),'after_sha256':im.sha(after)},
             'readme_index_entry':entry,'readme_index_before_sha256':im.sha(ib),'readme_index_after_sha256':im.sha(ia),
             'operations':{'UU_received_public_files':10,'cached_native_queries':7,'old13_files_unchanged':True,
                           'camera_interface_commands_auth_mode_driver_media_module_WBI_flash':False,
                           'current_connected_binding_verified':False,'actual_recording_or_recovery':False,
                           'goal_complete':False,'persistent_write_release':False}}
    im.write_json(s/'final-receipt.json',final)
    assert all(im.sha((root/x['path']).read_bytes()) == x['sha256'] for x in files)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':im.sha((s/'final-receipt.json').read_bytes()),
                      'latest_stage':s.name,'public_files':10,'current_connected_candidates':0,'requirements_retained':16,'goal_complete':False}))


if __name__ == '__main__':
    main()
