#!/usr/bin/env python3
"""Seal the one authorized descriptor trial and consumed authority, no USB I/O."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage142-Mac-USB-transport-candidate'
PRIOR_SHA='dd277f6ebc8acace359fec079e5d17182751975d46bea6a6f20e0e985df5a86e'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    assert sha256((HELPER/'final-receipt.json').read_bytes()).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin=next(x for x in json.loads((HELPER/'final-receipt.json').read_text())['files']
             if x['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();count=helper.check_previous();assert count==451
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes();consumed=(HERE/'goal-status-one-shot-consumed.json').read_bytes()
    index_before=(HERE/'readme-before.md').read_bytes()
    assert before==(PRIOR/'goal-status-after.json').read_bytes()
    assert canonical.read_bytes()==consumed and index.read_bytes()==index_before
    old=json.loads(before);current=json.loads(consumed);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    permission=json.loads((HERE/'explicit-permission-and-preflight.json').read_text())
    assert permission['explicit_user_reply']=='允许，仅一次 USB 描述符读取' and permission['maximum_active_probe_invocations']==1
    release=json.loads((HERE/'goal-status-one-shot-released.json').read_text())
    assert release['authorization']['Mac_active_USB_descriptor_read_authorized'] is True
    assert release['prepared_first_device_trial']['Mac_descriptor_probe_released'] is True
    assert current['authorization']['Mac_active_USB_descriptor_read_authorized'] is False
    assert current['authorization']['Mac_descriptor_probe_authorization_consumed'] is True
    assert current['prepared_first_device_trial']['Mac_descriptor_probe_released'] is False
    for k in old['authorization']:assert old['authorization'][k]==current['authorization'][k]
    execution=json.loads((HERE/'execution-and-consumption.json').read_text())
    assert execution['actual_probe_invocations']==1 and execution['actual_probe_process_exit_code']==0
    assert execution['new_active_descriptor_permission_consumed_and_disabled']
    for name in ('descriptor-probe-claim.json','descriptor-probe-result.json'):
        assert (HERE/name).read_bytes()==(PRIOR/name).read_bytes()
    claim=json.loads((HERE/'descriptor-probe-claim.json').read_text())
    result=json.loads((HERE/'descriptor-probe-result.json').read_text())
    assert claim['probe_id']==result['probe_id']==permission['probe_id']
    assert result['status']=='METADATA_RETURNED_NOT_AUTH_BACKUP_OR_RECOVERY'
    desc=result['descriptors'];assert (desc['VID'],desc['PID'],desc['USB_BCD'],desc['configuration'],desc['total_length'])==(0x054c,0x0da1,0x0210,1,32)
    assert len(desc['interfaces'])==1
    iface=desc['interfaces'][0]
    assert [iface[k] for k in ('interface','alternate','class','subclass','protocol')]==[0,0,8,6,0x50]
    assert [(x['address'],x['transfer_type'],x['max_packet_size']) for x in iface['endpoints']]==[(0x81,2,512),(2,2,512)]
    assert not desc['authentication_or_service_endpoint_roles_proven'] and not desc['actual_recording_authentication_backup_or_recovery_proven']
    cache=json.loads((HERE/'post-trial-cache-reviewed.json').read_text())
    assert cache['selected_count']==1 and cache['offline_sanitization_cases']==4
    assert helper.digest(HERE/'post_trial_cache.py')==cache['collector_sha256']
    assert cache['source_is_IORegistry_cache_not_active_USB'] and not cache['raw_tree_or_serial_saved']
    assert 'IOUSBMassStorageDriver' in cache['selected'][0]['storage_driver_classes']
    assert any(x.get('bInterfaceClass')==8 and x.get('bInterfaceProtocol')==0x50 for x in cache['selected'][0]['interfaces'])
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(current)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='One explicitly authorized Mac MSC USB descriptor trial succeeded and authority consumed; authentication modes still unresolved'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段144核验142全部451成员；用户明确允许一次USB描述符读取后临时放行，实际执行一次且进程退出0；随后授权关闭、单次凭据保留。',
        '真实返回054C/0DA1、bcdUSB0210、配置1/32B、接口0 alt0 08/06/50；Bulk IN81/OUT02均512B。没有认证、切模式、接管驱动、读卡或刷写。',
        '后置IORegistry缓存仍见固定位置1台IOUSBHostDevice及MSC/SCSI/BlockStorage驱动链；原嵌套3节点计数和夹具递归错误均保留，四例清洗通过；未重跑主动读取。',
        '公开主机对MSC与0336摘要输入有分支；141六轮仿真的MSC部分使用同一服务校验器，不能证明初始MSC认证。原服务算法/材料证据保留，双模式认证仍未可用。',
        '所有16项完整验收、旧权限值及受限原型保持，新增权限仅一次描述符现已消耗；实机认证/同机完整备份恢复/独立救援/目标主录尚未证明。'])
    key='stage144_single_Mac_descriptor_trial';assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key]={
        'readme':REL+'/README.md','permission':REL+'/explicit-permission-and-preflight.json',
        'execution':REL+'/execution-and-consumption.json','actual_descriptors':REL+'/descriptor-probe-result.json',
        'post_cache':REL+'/post-trial-cache-reviewed.json','actual_probe_invocations':1,'actual_probe_process_exit_code':0,
        'real_private_USB_library_initialized_for_selected_MSC_target':True,
        'interface':0,'bulk_IN':0x81,'bulk_OUT':2,'max_packet_size':512,
        'post_cache_driver_chain_present':True,'driver_restoration_or_physical_health_proven':False,
        'authentication_endpoint_roles_or_both_digest_paths_proven':False,
        'active_descriptor_permission_consumed':True,'new_auth_driver_mode_camera_file_or_firmware_actions':0}
    new['prepared_first_device_trial']['Mac_descriptor_metadata_candidate']['real_USB_library_not_initialized']=False
    new['prepared_first_device_trial']['Mac_descriptor_actual_receipt']=REL+'/descriptor-probe-result.json'
    new['prepared_first_device_trial']['Mac_descriptor_actual_trial_completed']=True
    new['prepared_first_device_trial']['initial_MSC_auth_digest_path_proven']=False
    new['prepared_first_device_trial']['stage141_MSC_labeled_inert_rounds_not_initial_MSC_verifier_evidence']=True
    new['next_safe_offline_actions'].append(
        '阶段144真实MSC描述符已得且一次授权耗尽，不重试或外推认证端点。继续离线定位初始MSC验证器/摘要分支并加显式模式分派，修正141六轮夹具的MSC证据范围，再完善真实传输/驱动归还；新的认证、切模式或读文件需具体方案与对应授权。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions','authorization'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for k,value in old['prepared_first_device_trial'].items():
        if k=='Mac_descriptor_metadata_candidate':
            for field,v in value.items():
                if field!='real_USB_library_not_initialized':assert new['prepared_first_device_trial'][k][field]==v
        else:assert new['prepared_first_device_trial'][k]==value
    for k,value in old['latest_stage_evidence'].items():assert new['latest_stage_evidence'][k]==value
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3单次USB描述符实测](<'+REL+'/README.md>)：明确授权后实际读取成功，MSC接口0/Bulk81与02/512B，后置缓存驱动链仍在；一次权限已消耗，无认证或刷写。'
    marker='## 相机与固件研究\n';text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==consumed and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    completed={'status':'PASS_ONE_AUTHORIZED_REAL_MSC_DESCRIPTOR_QUERY_NOT_AUTH_BACKUP_RECORDING_OR_RECOVERY',
        'created_utc':now,'previous_manifest_members_verified':count,'actual_active_probe_invocations':1,
        'process_exit_code':0,'temporary_permission_consumed_and_disabled':True,
        'post_cache_one_selected_device_and_storage_driver_chain':True,'all16_requirements_and_old_permission_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'same_agent_review_not_physical_record_or_recovery_acceptance':True,
        'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage144-single-authorized-Mac-descriptor/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
                      'canonical_sha256':helper.digest(canonical),'actual_probe_invocations':1,'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
