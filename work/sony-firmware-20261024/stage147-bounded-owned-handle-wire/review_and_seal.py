#!/usr/bin/env python3
"""Seal own ABI fixture evidence without expanding any device authorization."""
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
PRIOR=BASE/'stage146-original-kernel-symbol-and-vendor-route'
PRIOR_SHA='8f8c1ab7f4cb8f0ac05aceb0fb748992d21cbaa894ef5b00521060b1435fbf4a'
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
    helper.volume();count=helper.check_previous();assert count==32
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['service_auth_mode_or_stop'] and not old['authorization']['driver_change']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    fixed=helper.pins(old)
    source=json.loads((HERE/'source-and-scope.json').read_text())
    header=ROOT/source['libusb_header']['path']
    assert header.stat().st_size==source['libusb_header']['bytes'] and helper.digest(header)==source['libusb_header']['sha256']
    result=json.loads((HERE/'run-wire-tests/results.json').read_text())
    assert result['case_count']==len(result['cases'])==78 and result['flow_count']==len(result['inert_flows'])==2
    assert result['status']=='PASS_OWNED_HANDLE_WIRE_ABI_FAULTS_AND_INERT_CONTROLLER_FLOWS_NO_REAL_USB'
    assert result['real_USB_library_loaded_initialized_device_interface_claim_or_driver_operations']==0
    assert result['live_factory_currently_rejects_before_native_binding']
    assert type(result['compile_argv']) is list and result['compile_argv'][0]=='/usr/bin/clang'
    assert '-Werror' in result['compile_argv'] and result['compile_argv'][-1]==str(HERE/'artifacts/fake-wire.dylib')
    assert 'IOKit' not in result['fixture_dependencies'] and '/libusb' not in result['fixture_dependencies']
    assert helper.digest(HERE/'bounded_wire.py')==result['wire_sha256']
    assert helper.digest(HERE/'test_bounded_wire.py')==result['test_sha256']
    for name,saved in [('bounded_wire.py','wire-executed.py'),('test_bounded_wire.py','test-executed.py'),('fake_wire.c','fixture-executed.c')]:
        assert (HERE/name).read_bytes()==(HERE/'run-wire-tests'/saved).read_bytes()
    for directory,cases in [(HERE/'initial48-before-scope-review',48),
                            (HERE/'before-lifetime-and-concurrency-review',69),
                            (HERE/'before-build-receipt-correction',78),
                            (HERE,78)]:
        r=json.loads((directory/'run-wire-tests/results.json').read_text())
        assert r['case_count']==len(r['cases'])==cases and r['flow_count']==2
        lib=directory/'fake-wire.dylib' if directory!=HERE else HERE/'artifacts/fake-wire.dylib'
        assert helper.digest(lib)==r['fixture_library']['sha256'] and lib.stat().st_size==r['fixture_library']['bytes']
    for flow in result['inert_flows']:
        assert flow['native_fixture_call_counts']==[3,14,14,1000,1000,0]
        assert flow['all_hardware_identity_owner_capture_driver_mode_auth_replies_and_physical_acceptance_are_fixtures']
        assert flow['controller_result']['phase']=='FLOW_FINISHED'
        assert not flow['controller_result']['evidence']['worker_completion']
        assert all(not x['device_effect_or_queue_worker_completion_proven'] for x in flow['wire_actions'])
    now=datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json',{
        'created_utc':now,'own_fixture_cases':78,'inert_controller_flows':2,
        'only_control_and_bulk_native_ABI_implemented':True,
        'borrowed_handle_owner_identity_driver_and_endpoint_roles_are_unimplemented_live_dependencies':True,
        'strict_endpoint_range_shared_nonblocking_guard_and_DSO_lifetime_reviewed':True,
        'compile_argv_metadata_collision_preserved_corrected_and_retested':True,
        'completed_STALL_not_normalized_to_controller_success':True,
        'real_USB_worker_deadline_or_cancellation_not_proven':True,
        'initial_MSC_authentication_reference_not_actual_verifier':True,
        'new_USB_camera_auth_driver_or_firmware_operations':0,
        'all16_requirements_and_authorization_unchanged':True,
        'same_agent_local_review_not_real_camera_acceptance':True})
    new=copy.deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Implemented bounded borrowed-handle control/bulk ABI; own C fixture only, no real USB'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段147复核146全部32成员与6固定原型，完成仅control/bulk两函数借用句柄实现；无库加载/枚举/open/claim/驱动/文件/模块API。',
        '自写C夹具包含固定libusb头文件编译，仅libSystem依赖；78项故障/身份/时限/并发检查及两条惰性流程通过，每流程3control/14OUT/14IN且无timeout0。',
        '已审查并修正端点超8位截断、共享会话并发重入、DSO强引用；编译参数回执变量冲突原件保留，更正后重新通过，源码与执行快照一致。',
        '真实归属/身份/驱动/端点角色和模式转换仍未实现验证，MSC为公开参考；STALL不自动充控制器成功，真实worker结束/取消仍缺。',
        '本轮未新增设备访问，一次描述符授权保持消耗；目标MAIN/同机完整备份恢复/独立救援和全部16要求保持未替代。'])
    new['latest_stage_evidence']['stage147_bounded_borrowed_handle_wire']={
        'readme':REL+'/README.md','wire':REL+'/bounded_wire.py','fixture_source':REL+'/fake_wire.c',
        'verification':REL+'/run-wire-tests/results.json','review':REL+'/completed-local-review.json',
        'own_C_fixture_cases':78,'inert_controller_flows':2,'real_USB_or_camera_operations':0,
        'native_transfer_ABI_implemented_for_borrowed_owned_handle':True,
        'complete_live_owner_capture_restore_or_pilot_implemented':False,
        'real_worker_completion_cancellation_or_initial_MSC_verifier_proven':False,
        'authorization_unchanged':True}
    prepared=new['prepared_first_device_trial']
    prepared['bounded_borrowed_handle_wire_candidate']=REL+'/bounded_wire.py'
    prepared['bounded_borrowed_handle_wire_fixture_receipt']=REL+'/run-wire-tests/results.json'
    prepared['bounded_borrowed_handle_wire_live_ready']=False
    new['next_safe_offline_actions'].append(
        '阶段147仅有两函数借用句柄收发层，78项C夹具及两条惰性流程不能替代实机。接续真实owner身份/代次/角色与驱动接管归还及工作进程寿命准备；已结束STALL需明确控制器适配，不能吞异常或重试。沿原注册/回调追初始MSC认证者。一次描述符授权保持关闭，主录/同机健康完整备份恢复/独立救援仍为实机门槛。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,v in old[section].items():assert new[section][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3有界USB收发层](<'+REL+'/README.md>)：借用句柄的control/bulk实现，78项自写C夹具检查及两条惰性流程通过；真实接管/归还/初始MSC认证及救砖未验，无新增相机操作。'
    marker='## 相机与固件研究\n';text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    put('completed-evidence-review.json',{
        'status':'PASS_BORROWED_HANDLE_ABI_OWN_FIXTURE_NOT_LIVE_PILOT',
        'created_utc':now,'previous_manifest_members_verified':count,'own_fixture_cases':78,'inert_flows':2,
        'real_USB_or_camera_operations':0,'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{
        'schema':'fx3-stage147-bounded-borrowed-handle-wire/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
            'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
