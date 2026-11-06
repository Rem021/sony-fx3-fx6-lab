#!/usr/bin/env python3
"""Seal original normal-cooperator checkpoint evidence; no live authorization change."""
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
PRIOR=BASE/'stage148-initial-MSC-handler-inventory'
PRIOR_SHA='3e59ddb2f6b31e8164921e6857e82b666a9a7a56c17337139fe31969769649e1'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin=next(x for x in json.loads(raw)['files'] if x['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==pin['sha256']
    spec=importlib.util.spec_from_file_location('fixed_normal_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();count=helper.check_previous();assert count==25
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['service_auth_mode_or_stop'] and not old['authorization']['driver_change']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    assert (HERE/'normal_cooperator.py').read_bytes()==(HERE/'static-executed.py').read_bytes()
    assert (HERE/'normal_cooperator.py').read_bytes()==(HERE/'run-original-checkpoint/static-reader-executed.py').read_bytes()
    assert (HERE/'run_normal_checkpoint.py').read_bytes()==(HERE/'run-original-checkpoint/test-executed.py').read_bytes()
    spec=importlib.util.spec_from_file_location('reviewed_normal_source',HERE/'normal_cooperator.py')
    source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source);obj,core=source.images()
    static=json.loads((HERE/'normal-cooperator-static.json').read_text())
    assert len(static['object_functions'])==15 and len(static['core_functions'])==11
    assert static['normal_cooperator']['onComplete_ignores_incoming_result_and_requests_resource']
    assert static['normal_cooperator']['register_hasp_method_is_ret']
    for image,section in [(obj,'object_functions'),(core,'core_functions')]:
        for f in static[section]:assert sha256(image.read(int(f['VA'],16),f['bytes'])).hexdigest()==f['sha256']
    result=json.loads((HERE/'run-original-checkpoint/results.json').read_text())
    assert result['case_count']==len(result['cases'])==5 and result['original_function_entries']==590
    assert result['test_sha256']==helper.digest(HERE/'run_normal_checkpoint.py')
    assert not result['initial_MSC_digest_algorithm_proven'] and not result['full_NinThread_exit_history_or_cleanup_executed']
    assert result['new_host_USB_camera_driver_or_Windows_operations']==0
    for c in result['cases']:
        correct=c['digest_style']=='service_full512_plus_material'
        assert c['native_verifier_returns']==[0 if correct else -2]*3
        assert c['native_comparisons']==[correct]*3 and c['normal_callback_levels']==[3 if correct else -1]
        assert c['native_verifier_rounds']==([1,2,3] if correct else [1,1,1])
        assert c['public_response_codes']==[8,4,8,4,8,4,6] and c['final_reply_first_byte']==1
        assert c['original_entry_count']==len(c['original_entries'])==118
        assert c['original_entries'].count('0xe9ed8')==c['original_entries'].count('0xe9ef8')==7
        assert len(c['driver_fixture_calls'])==14 and len(c['resource_requests'])==1
        assert c['resource_requests'][0]['returned_fixture']==c['resource_result_fixture']
        assert c['original_object_state_after_callback']==2 and not c['thread_completion_proven']
        assert c['stack_above_entry_guard_and_original_code_unchanged'] and c['all_guest_writes_bounded']
        assert c['stopped_before_original_tlog_file_check']
    assert [c['resource_result_fixture'] for c in result['cases']]==[0,0,0,0,-5]
    now=datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json',{
        'created_utc':now,'original_object_functions_statically_checked':15,'original_core_functions_statically_checked':11,
        'joint_guest_cases':5,'original_function_entries':590,
        'failed_original_digest_comparisons_can_precede_same_final_reply_and_normal_resource_request_in_guest':True,
        'normal_virtual_hasp_registration_ret_not_zero_persistence_guarantee':True,
        'resource_error_fixture_can_coexist_with_internal_state2':True,
        'checkpoint_before_tlog_file_check_not_thread_exit':True,
        'CPU_bridges_and_fixture_transport_not_actual_runtime_registration_or_USB':True,
        'new_camera_driver_or_Windows_operations':0,'same_agent_local_review_only':True})
    new=copy.deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Original normal SenUsbIf constructor/vtable/IO and NIN joined in five bounded guests; final reply/resource request not auth or mode proof'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段149重验148全部25成员及6固定原型，上一轮532ELF盘点与原普通应用动态NIN入口为实际进展。',
        '原RTTI/重定位/init_array将2ce108对象确认为Senser::SenUsbIf协作者；原构造设置虚表252340，收发getter接事件保存的传输表。Hasp虚方法ret仅属此对象，不推出整条流程零写入。',
        '五组原构造/事件/动态加载封装/收发/NinThread联合guest，共590原函数进入；完整512B加材料两例三轮成功，前4B三例三轮均返回-2，但均收到同样8/4/8/4/8/4/6及最终1，并调用普通回调请求资源。',
        '普通onComplete覆盖输入结果，内部状态2/资源请求可先于真实成功；资源返回-5夹具时也如此。原NIN回调后才检查失败循环，本轮停bf30并未证明线程退出/历史尾部或当前MSC实际映射。',
        '本轮用户询问FX5/VENICE电影菜单，官方确认FX3 7.00起已有六区HOME；菜单层重排可研究，完整跨机型应用/系统适配仍未实现，不代替原HEVC主录目标。',
        '无新增USB/相机/Windows操作，一次描述符权限保持消耗，全部16要求及完整同机恢复/独立救援保持。'])
    new['latest_stage_evidence']['stage149_normal_cooperator_original_NIN_checkpoint']={
        'readme':REL+'/README.md','static_audit':REL+'/normal-cooperator-static.json',
        'joint_guest':REL+'/run-original-checkpoint/results.json','review':REL+'/completed-local-review.json',
        'guest_cases':5,'original_entries':590,'original_normal_cooperator_and_io_binding_in_fixture':True,
        'final_reply_or_internal_state_not_digest_authentication_or_mode_success':True,
        'actual_MSC_registration_thread_exit_or_no_persistent_effects_proven':False,
        'new_device_operations':0,'authorization_unchanged':True}
    new['prepared_first_device_trial']['normal_application_NIN_checkpoint_guest']=REL+'/run-original-checkpoint/results.json'
    new['prepared_first_device_trial']['protocol_final_reply_or_internal_state_not_authentication_or_mode_proof']=True
    new['next_safe_offline_actions'].append(
        '阶段149原SenUsbIf协作者与NinThread联合guest证实摘要失败也可出最终6/1并请求资源，不能再把首段最终回复当作摘要接受或模式成功。后续追资源Acquire异步回调、普通应用停止恢复及失败轮线程取消/等待，区分真实MSC注册/对象代次；日志/文件尾部尚未执行。菜单移植继续限定已有程序/资源证据，不擅自互刷；USB owner/驱动归还与完整主录恢复仍未放行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,v in old[section].items():assert new[section][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    marker='## 相机与固件研究\n';text=index_before.decode()
    entry='- [2026-10-27 FX3普通协作者与NIN联合验证](<'+REL+'/README.md>)：五组原指令guest/590进入，错误摘要也可出最终回复并请求资源；内部状态不充实机模式或线程完成，无新增设备操作。'
    assert text.count(marker)==1 and entry not in text
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
        'status':'PASS_ORIGINAL_NORMAL_NIN_CHECKPOINT_NOT_AUTH_MODE_THREAD_OR_CAMERA_ACCEPTANCE',
        'created_utc':now,'previous_manifest_members_verified':count,'joint_guest_cases':5,'original_entries':590,
        'new_device_operations':0,'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage149-normal-cooperator-NIN-checkpoint/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
            'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
