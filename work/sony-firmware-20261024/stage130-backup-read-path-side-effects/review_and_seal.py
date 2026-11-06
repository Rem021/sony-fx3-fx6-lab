#!/usr/bin/env python3
"""Seal explicit Mac cache authorization/results and restricted backup audit."""
from pathlib import Path
import copy,datetime,hashlib,json,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import read_path_audit as t
BASE,ROOT=t.BASE,t.ROOT
PRIOR=BASE/'stage129-AP-DMM-config-and-device-trial-plan/final-receipt.json'
PRIOR_SHA='67199d5dd0fd70df1051377a939289d4c0b49bd167bfe40bd2fa36fbea3e14e4'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,j):
    with p.open('x') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    t.previous.shared_volume_check();assert not (STAGE/'final-receipt.json').exists()
    assert digest(PRIOR)==PRIOR_SHA;prior=json.loads(PRIOR.read_text())
    for f in prior['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    canonical=BASE/'GOAL_STATUS.json';before=(STAGE/'goal-status-before.json').read_bytes()
    assert before==canonical.read_bytes()==(PRIOR.parent/'goal-status-after.json').read_bytes()
    out=STAGE/'run-explicit-null-root-boundary-20261027';result=out/'read-path-results.json';j=json.loads(result.read_text())
    assert j['status']=='PASS_GET_FILE2_SPECIAL_BRANCH_AND_BACKUP_LIMIT_AUDIT_NOT_READ_ONLY_DEVICE_RELEASE'
    assert j['source_sha256']==digest(STAGE/'read_path_audit.py')==digest(out/'executed-source.py')
    assert not any(j[k] for k in ('actual_Mac_cache_camera_Windows_file_or_host_service_operations','goal_complete','persistent_write_release'))
    assert len(j['cases'])==7 and sum(len(c['events']) for c in j['cases'])==j['native_phases']==8
    for c in j['cases']:
        assert c['inputs_after_unexecuted_path_resolution_and_constructor_are_explicit'] and not c['real_runtime_reachability_or_any_file_operation_proven']
        if c['label']=='pending_jit_log':assert c['original_special_branch_selected'] and c['native_prepared_open_arguments'][-1]==0x441
        else:assert not c['original_special_branch_selected']
        for e in c['events']:
            assert e['all_images_stack_scratch_unchanged'] and not e['constructor_file_open_write_sync_stat_mount_or_transport_executed']
            assert not e['original_stores']
    null=next(c for c in j['cases'] if c['label']=='global_null');assert null['events'][0]['reason']=='before_unconditional_global_root_dereference'
    assert null['null_root_observer_fence_is_not_a_native_guard']
    oldrun=STAGE/'run-original-decision-20261027';failed=json.loads((oldrun/'attempt-failure.json').read_text())
    assert failed['status']=='FAILED_NO_PASSING_RESULT' and failed['source_sha256']==digest(oldrun/'executed-source.py')
    assert 'UC_ERR_READ_UNMAPPED' in failed['error']
    limits=j['backup_candidate_limits'];assert limits['official_AP_file_bytes']==66796 and limits['stage9_max_host_data']==65536
    assert limits['official_AP_exceeds_old_host_limit_by']==1260 and not limits['AP_backup_current_adapter_ready']
    assert limits['stage9_setpath_rejects_plain_AP_path'] and limits['plain_absolute_AP_path_native_format_candidate']=='/tmp/jiritsu/setting/DmmCfg.bin'
    association=json.loads((STAGE/'mac-cache-association-review.json').read_text())
    assert association['physical_USB_device_roots_in_cache']==1 and association['raw_Sony_identifier_records_in_service_cache']==4
    assert association['VID_hex']=='054C' and association['PID_hex']=='0DA1'
    assert association['interface_class_subclass_protocol_hex']==['08','06','50']
    assert not association['camera_interface_or_media_files_accessed'] and not association['live_device_commands_sent']
    for f in association['source_files']:assert digest(STAGE/f['path'])==f['sha256']
    usb=json.loads((STAGE/'mac-cache-20261027T183151Z/sanitized-cache-receipt.json').read_text())
    service=json.loads((STAGE/'mac-service-cache-20261027T1834Z/sanitized-service-cache-receipt.json').read_text())
    assert usb['source']=='explicit_mac_IORegistry_cache_query' and service['source']=='explicit_mac_IORegistry_IOService_USB_device_cache'
    assert usb['collector_source_sha256']==digest(PRIOR.parent/'mac_cached_usb_inventory.py')
    assert service['collector_source_sha256']==digest(STAGE/'mac_usb_service_cache.py')
    for receipt in (usb,service):
        assert not receipt['raw_source_saved'] and not receipt['USB_interfaces_opened_camera_commands_or_media_reads']
        forbidden=('USB Serial Number','IOUSBSerialNumberString','BSD Name','IORegistryEntryID')
        def walk(x):
            if isinstance(x,dict):
                assert not any(k in x for k in forbidden)
                for v in x.values():walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        walk(receipt)
    old=json.loads(before)
    for f in old['current_guest_adapter_prototype']['bundle'].values():assert digest(ROOT/f['path'])==f['sha256']
    p117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json';assert digest(p117)=='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    for f in json.loads(p117.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();rel=str(STAGE.relative_to(ROOT));rr=str(result.relative_to(ROOT))
    auth=copy.deepcopy(old['authorization']);auth['scope']='Windows_and_Mac_cached_USB_metadata_only'
    auth['Mac_cached_USB_metadata_authorized']=True
    constraint=copy.deepcopy(old['current_user_operational_constraint'])
    constraint['current_scope']='Mac offline research/reversible preparation plus explicitly authorized Mac USB system-cache metadata collection only'
    constraint['latest_Mac_cache_authorization_quote']='可以，仅查 Mac USB 缓存'
    constraint['Mac_cached_metadata_scope_expanded']=True
    assert all(auth[k] is False for k in ('active_query','service_auth_mode_or_stop','driver_change','camera_file_access',
        'module_upload_or_native_execution','WBI_or_boot_write','settings_or_firmware_write'))
    put(STAGE/'authorization-change.json',{'source':'latest direct user reply to explicit Mac cache scope question',
        'user_quote':'可以，仅查 Mac USB 缓存','recorded_utc':now,'before':old['authorization'],'after':auth,
        'allowed_delta':'Read Mac IORegistry cached USB metadata, filter/sanitize and save association evidence.',
        'actual_queries':['IOUSB plane cached properties','IOService USB device subtree cached properties'],
        'unchanged_denials':['active USB/SCSI/PTP/vendor','service authentication/mode/stop','driver changes','camera/media file access','module/native upload','WBI/boot/settings/firmware write'],
        'new_user_permission_is_not_inferred_from_goal_or_web_content':True})
    contract=json.loads((PRIOR.parent/'diagnostic-contract.json').read_text());contract['schema']='fx3-offline-status-diagnostic-candidate/12';contract['refined_in_stage']=STAGE.name
    contract['authorized_Mac_cache_result']={'VID':'054C','PID':'0DA1','product':'ILME-FX3','physical_device_roots':1,
        'interface':0,'class_subclass_protocol':['08','06','50'],'cached_driver':'IOUSBMassStorageDriver',
        'raw_identifier_records4_are_inherited_not4_cameras':True,'actual_camera_interface_commands_or_file_access':False,
        'firmware_hash_backup_or_rescue_proven':False}
    contract['prepared_first_device_step'].update({'actual_query_executed':True,'new_Mac_cache_query_authorization_granted':True})
    contract['backup_GetFile2_side_effect_review']={'kind0_selector3_pending_log_may_prepare_write_create_append':True,
        'native_prepared_open_flags':'0x441','actual_write_operation_executed':False,
        'ff_selector_only_bypasses_special_fragment_not_all_side_effects':True,
        'sys_mount_input_MS_RDONLY_bit':0,'native_global_root_validity_required_no_native_null_guard_proven':True,
        'normal_read_has_stat_whole_file_DMM_and_fsync_close_dependencies':True,
        'plain_AP_path_not_direct_target_in_static_prefix_format':'/tmp/jiritsu/setting/DmmCfg.bin',
        'old_host_limit':65536,'official_AP_bytes':66796,'old_AP_backup_adapter_ready':False,
        'PMCA_ff01_cmd2_is_separate_and_model_mapping_unproven':True}
    contract['next_runtime_acceptance_requirements'].append('Mac cache identity complete within approved metadata scope. Before active/file access, resolve a genuinely scoped backup reader: GetFile2 pending-log/mount/path/whole-file allocation/fsync behavior and protocol-family distinction must not be assumed read-only.')
    put(STAGE/'diagnostic-contract.json',contract)
    review={'status':j['status'],'created_utc':now,'new_Mac_cache_authorization_explicit':True,'actual_Mac_cache_queries':2,
        'cached_FX3_roots':1,'interface_class_subclass_protocol':['08','06','50'],'native_branch_cases':7,'native_fragments':8,
        'first_failed_harness_assumption_preserved':True,'native_null_root_guard_not_claimed':True,
        'actual_camera_commands_file_access_or_driver_change':False,'backup_RAM_or_flash_ready':False,
        'formal_source_matches_executed_copy':True,'same_agent_review_not_independent_engine':True,
        'stage117_frontend_and_stage75_backend_unchanged':True,'goal_complete':False,'persistent_write_release':False,
        'previous_manifest_members_verified':len(prior['files'])}
    put(STAGE/'completed-evidence-review.json',review)
    g=copy.deepcopy(old);g['updated_utc']=now;g['latest_stage']=STAGE.name;g['authorization']=auth;g['current_user_operational_constraint']=constraint
    g['research_activity']='Explicitly_authorized_Mac_cached_USB_identity_and_interface_associations_plus_offline_GetFile2_backup_side_effect_review'
    g['progress_audit']={'classification':'progress','previous_goal_turn_classification':'progress',
        'basis':['阶段129封存24件/canonical核验；用户明确批准仅Mac USB缓存后执行两次限定缓存查询，无主动相机命令。',
            'Sony ILME-FX3 054C/0DA1、接口0 08/06/50、原生MSC驱动缓存关联；4条继承标识记录归并为1设备，不保存序列号/原始IOReg。',
            '原GET_FILE2特殊分支8片段，声明待日志条件准备441写开参数；ff候选仍有挂载/路径/整文件分配/同步依赖，不充只读备份可用。',
            '旧保守codec拒绝AP路径且64K主机限小于官方AP文件，另一个PMCA文件家族未建立FX3映射；先补读入口审查而非扩大或直接执行。',
            '仅用户明确Mac缓存授权作增量；16项状态/实际主录/备份恢复缺口及旧前后端保持。'],
        'completion_not_claimed':True}
    g['latest_stage_evidence']['stage130_Mac_cache_and_backup_read_review']={'readme':rel+'/README.md','result':rr,
        'cache_associations':rel+'/mac-cache-association-review.json','authorization_change':rel+'/authorization-change.json',
        'backup_addendum':rel+'/BACKUP_READ_REVIEW.md','source_audit':rel+'/source-and-scope-audit.json',
        'contract':rel+'/diagnostic-contract.json','review':rel+'/completed-evidence-review.json',
        'scope':'Authorized Mac system-cache identity/MSC interface associations only; offline8 GET_FILE2 decision fragments and unsafe backup assumptions identified. No active camera/file/driver/RAM/flash operation.',
        'authorization_delta':'explicit Mac cached metadata only','stage75_backend_changed':False,'goal_complete':False}
    g['prepared_first_device_trial'].update({'live_Mac_cache_query_executed':True,'new_Mac_cache_query_authorized':True,
        'Mac_cache_receipt':rel+'/mac-cache-association-review.json','backup_read_review':rel+'/BACKUP_READ_REVIEW.md',
        'scope':'Mac cached metadata explicitly approved and collected; active protocols, backup, RAM and flash remain unapproved/unready.'})
    for req in g['requirements']:
        if req['id']=='G01':
            req['evidence'].extend([rel+'/mac-cache-association-review.json',rel+'/authorization-change.json'])
            req['stage130_scope']='Mac缓存FX3 054C/0DA1及MSC接口/驱动关联；未读固件/序列号/机身文件，不充同机哈希及健康备份，状态保持。'
        if req['id'] in ('G05','G07','G08','G15','G16'):
            req['evidence'].extend([rr,rel+'/source-and-scope-audit.json',rel+'/BACKUP_READ_REVIEW.md'])
            req['stage130_scope']='主动接口/认证未执行；GET_FILE2只读假设收紧，备份仍不可部署。Mac缓存许可不扩大到文件/驱动/模块/WBI/刷写，状态保持。'
    g.setdefault('provenance_refinements',[]).append({'stage':STAGE.name,'prior_stage':PRIOR.parent.name,
        'finding':'Explicit user Mac-cache approval yielded one FX3 MSC identity with inherited properties deduplicated. GET_FILE2 can prepare pending-log writes and has mount/path/whole-file dependencies; current conservative codec cannot back up the AP config. No active camera/file operations or recovery acceptance.',
        'actual_MAIN_hardware_backup_recovery_proven':False,'old_sealed_files_preserved':True})
    g['next_safe_offline_actions'].append('阶段130后不重复已完成的Mac缓存盘点；在现有范围内继续定位真正适用的备份读家族/接收器与文件大小/路径/退出边界。主动接口、认证和文件访问须完成具体方案及对应授权，Mac缓存批准不能代替。')
    stable=('objective','completion_rule','external_dependencies','current_guest_adapter_prototype','next_authorized_cached_metadata_action')
    for k in stable:assert g[k]==old[k]
    assert len(g['requirements'])==16 and [(x['id'],x['status']) for x in g['requirements']]==[(x['id'],x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release'];put(STAGE/'goal-status-after.json',g)
    index=ROOT/'README.md';ib=index.read_bytes();text=ib.decode();marker='## 相机与固件研究\n';assert text.count(marker)==1
    entry='- [2026-10-27 FX3 Mac缓存盘点与备份读路径](<'+rel+'/README.md>)：明确授权后缓存确认1台054C/0DA1、接口08/06/50及MSC驱动；GET_FILE2待日志写分支/路径/容量假设收紧，主动文件/备份/刷写仍未放行。'
    assert entry not in text;updated=text.replace(marker,marker+'\n'+entry+'\n',1)
    t.previous.shared_volume_check();assert canonical.read_bytes()==before and index.read_bytes()==ib
    canonical.write_bytes((STAGE/'goal-status-after.json').read_bytes());index.write_text(updated)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(STAGE.rglob('*')) if p.is_file()]
    put(STAGE/'final-receipt.json',{'schema':'fx3-stage130-Mac-cache-and-backup-read/1','created_utc':now,
        'volume_uuid':'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B','files':files,'previous_manifest_sha256':PRIOR_SHA,
        'operations':review,'mutable_progress':{'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':digest(canonical)},
        'readme_index_before_sha256':hashlib.sha256(ib).hexdigest(),'readme_index_after_sha256':digest(index),
        'readme_index_entry':entry,'requirements_retained':16,'authorization_change':'explicitly approved Mac cached metadata only',
        'invariants_retained':list(stable)})
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':digest(STAGE/'final-receipt.json'),
        'Mac_cache_device_roots':1,'active_device_commands':False,'goal_complete':False,'persistent_write_release':False}))
if __name__=='__main__':main()
