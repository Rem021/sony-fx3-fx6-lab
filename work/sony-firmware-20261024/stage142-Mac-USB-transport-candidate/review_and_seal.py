#!/usr/bin/env python3
"""Seal candidate/build/fixture evidence; do not release actual USB or writes."""
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
PRIOR=BASE/'stage141-public-auth-digest-and-original-verifier'
PRIOR_SHA='2800a952e5a4a960ba9c98463048cdebf6e4f27a0c1ae8b48fe6be3cae162866'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    assert sha256((HELPER/'final-receipt.json').read_bytes()).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin=next(x for x in json.loads((HELPER/'final-receipt.json').read_text())['files']
             if x['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_stage133_helper',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous_count=helper.check_previous();assert previous_count==19
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed=helper.pins(old)
    assert not old['authorization']['active_query'] and old['authorization']['Mac_cached_USB_metadata_authorized']
    source=json.loads((HERE/'source-inputs.json').read_text())
    archive=HERE/'work/libusb-1.0.30.tar.bz2'
    assert helper.digest(archive)==source['archive_sha256'] and archive.stat().st_size==source['archive_bytes']
    patch=json.loads((HERE/'private-source-patch.json').read_text())
    darwin=HERE/'work/libusb-1.0.30/libusb/os/darwin_usb.c'
    assert helper.digest(darwin)==patch['patched_sha256']=='c3e724698fe36e94df77b87e7cd02650b3ec51e91ffacae122b6bb9f8a2a5d2e'
    assert patch['fixed_PIDs']==['0DA1'] and patch['explicit_device_descriptor_requests_per_initialized_process_at_most']==1
    assert patch['descriptor_error_consumes_budget_no_retry'] and patch['multiple_configurations_rejected_before_GetConfiguration']
    assert patch['two_rejected_service_IOObjects_released'] and patch['OS_configuration_metadata_API_wire_activity_not_counted_or_guaranteed']
    build=json.loads((HERE/'native-build-receipt.json').read_text())
    assert build['status']=='BUILT_PRIVATE_DARWIN_LIBRARY_NOT_LOADED_OR_INITIALIZED'
    assert build['library_init_or_device_operations']==0 and all(x['returncode']==0 for x in build['runs'])
    assert build['private_source_sha256']==patch['patched_sha256']
    assert helper.record(ROOT/build['library']['path'])==build['library']
    transport=json.loads((HERE/'run-transport-tests/results.json').read_text())
    assert transport['descriptor_scenario_count']==len(transport['descriptor_scenarios'])==33
    assert len(transport['gate_cases'])==2 and len(transport['private_source_policy_cases'])==13
    assert transport['guard_precedes_native_device_user_client_creation'] and not transport['real_private_libusb_loaded_or_initialized']
    assert transport['camera_or_driver_operations']==0
    for current,snapshot in [('descriptor_transport.py','transport-executed.py'),('test_descriptor_transport.py','test-executed.py')]:
        assert (HERE/current).read_bytes()==(HERE/'run-transport-tests'/snapshot).read_bytes()
    probe=json.loads((HERE/'run-probe-tests/results.json').read_text())
    assert probe['case_count']==len(probe['cases'])==19 and probe['real_native_load_USB_driver_or_camera_operations']==0
    for current,snapshot in [('descriptor_probe.py','probe-executed.py'),('test_descriptor_probe.py','test-executed.py')]:
        assert (HERE/current).read_bytes()==(HERE/'run-probe-tests'/snapshot).read_bytes()
    assert not (HERE/'descriptor-probe-claim.json').exists() and not (HERE/'descriptor-probe-result.json').exists()
    cache=json.loads((HERE/'current-cache-target.json').read_text())
    assert cache['candidate_count']==1 and cache['unique_target_location']==cache['candidates'][0]['locationID']
    assert not cache['USB_interface_or_camera_protocol_access'] and not cache['real_libusb_initialized'] and not cache['raw_tree_or_serial_saved']
    assert helper.digest(HERE/'cached_target_selection.py')==cache['collector_sha256']
    plan=json.loads((HERE/'first-descriptor-trial-plan.json').read_text())
    assert plan['status']=='PREPARED_NOT_RELEASED_FOR_REAL_USB' and plan['native_library']==build['library']
    assert plan['target']=={'locationID':cache['unique_target_location'],'VID':0x054c,'PID':0x0da1}
    assert plan['explicit_device_GET_DESCRIPTOR_budget']==1 and not plan['native_library_loaded_by_this_plan']
    for path in HERE.rglob('*'):
        if path.is_symlink():assert path.resolve().is_relative_to(HERE),path
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Private Mac MSC descriptor candidate built and bounded offline; cache only on hardware, real USB release withheld'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段142核验141的19个成员及6个既有固定原型；完成私有libusb Mac元数据候选构建，真实动态库未加载/初始化。',
        '源码审查确认通用Darwin枚举含OpenSeize/配置/挂起重试；私有候选提前过滤位置+054C/0DA1，单次显式读取额度，多配置/0336拒绝及IOObject释放。',
        '33描述符夹具、2加载前授权边界、13精确私有函数模拟IOKit及19首次入口/超时例通过，共67例，均非真实USB验收。',
        '已授权Mac缓存查询见1台FX3；本次树没有接口/端点及二进制描述符，不保存原始树/序列号，不充实机健康/同机证明。',
        '一次描述符读取的具体入口与方案已备但未授权/放行；15秒期限、2秒终止观察、超时UNKNOWN与保留单次凭据，不认证切模式/接管驱动/刷写。',
        '用户只有Mac/Windows，无RP2040/UART；Windows延后约束不变，A7IV BootROM不能充FX3独立救援。全部16要求、旧授权及准备证据保持。'])
    key='stage142_Mac_USB_transport_candidate';assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key]={
        'readme':REL+'/README.md','source_patch':REL+'/private-source-patch.json',
        'native_build':REL+'/native-build-receipt.json','cache_receipt':REL+'/current-cache-target.json',
        'transport_tests':REL+'/run-transport-tests/results.json','probe_tests':REL+'/run-probe-tests/results.json',
        'first_metadata_trial_plan':REL+'/first-descriptor-trial-plan.json','offline_cases':67,
        'private_native_library_loaded_or_initialized':False,'new_active_USB_camera_or_driver_operations':0,
        'new_already_authorized_cache_query':True,'actual_auth_backup_recovery_or_recording_proven':False,
        'authorization_unchanged':True,'real_metadata_trial_released':False}
    new['prepared_first_device_trial']['Mac_descriptor_metadata_candidate']={
        'entrypoint':REL+'/descriptor_probe.py','transport':REL+'/descriptor_transport.py',
        'plan':REL+'/first-descriptor-trial-plan.json','library':build['library'],
        'offline_cases':67,'ordinary_MSC_only':True,'real_USB_library_not_initialized':True}
    new['prepared_first_device_trial']['Mac_descriptor_probe_released']=False
    new['next_safe_offline_actions'].append(
        '阶段142后仅在取得具体一次MSC设备/配置描述符读取授权并复核相机连接后，才放行对应入口；当前加载前拒绝。独立继续离线审查真实端点角色、传输期限/取消结束及驱动接管归还，不能将描述符成功替代认证、同机完整备份/恢复、独立救援或HEVC主录。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,value in old[section].items():assert new[section][k]==value
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    (HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3 Mac描述符传输候选](<'+REL+'/README.md>)：私有MSC限定构建/67离线例通过，缓存见1台；真实描述符读取尚未放行，无认证/刷写/恢复验收。'
    marker='## 相机与固件研究\n';text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-write.tmp'),(index,index_after,'.index-write.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    completed={'status':'PASS_MAC_METADATA_CANDIDATE_BUILD_AND_FIXTURES_NOT_REAL_USB',
        'created_utc':now,'previous_manifest_members_verified':previous_count,'offline_cases':67,
        'own_C_layout_and_mock_DSOs_executed':True,'real_private_libusb_loaded_or_initialized':False,
        'already_authorized_Mac_cache_query':True,'active_USB_camera_or_driver_operations':0,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'real_metadata_trial_released':False,
        'same_agent_local_review_not_real_camera_acceptance':True,'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage142-Mac-metadata-candidate/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
                      'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
