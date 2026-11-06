#!/usr/bin/env python3
"""Seal mode-provider and original/reference boundaries without changing authority."""
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
PRIOR=BASE/'stage144-single-Mac-descriptor-trial'
PRIOR_SHA='9c27bcf95ed409f987b724f3717c50def41e5464520d8f8eadaffc757f9fb7cc'
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
    helper.volume();count=helper.check_previous();assert count==20
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert old['authorization']['Mac_active_USB_descriptor_read_authorized'] is False
    assert old['prepared_first_device_trial']['Mac_descriptor_probe_released'] is False
    fixed=helper.pins(old)
    reference=json.loads((HERE/'official-gcore-reference.json').read_text());assert len(reference['records'])==21
    for rec in reference['records']:
        p=HERE/rec['path'];assert helper.digest(p)==rec['sha256'] and p.stat().st_size==rec['bytes']
    audit=json.loads((HERE/'mode-and-vendor-boundary-review.json').read_text())
    assert audit['original_callback_returns_constant_2'] and not audit['original_queue_return_checked']
    assert audit['reference_THRU_value']==2 and audit['reference_STALL_value']==1
    assert not audit['actual_702_gcore_runtime_registration_order_and_wire_STALL_proven']
    assert audit['initial_MSC_digest_verifier_not_located'] and audit['camera_or_Windows_operations']==0
    assert helper.record(ROOT/audit['original_module']['path'])==audit['original_module']
    for rec in audit['adopted_unsealed143_evidence_pins']:assert helper.record(ROOT/rec['path'])==rec
    assert len(audit['adopted_unsealed143_evidence_pins'])==6
    kernel=json.loads((HERE/'native-kernel-usb-exports.json').read_text())
    raw=(ROOT/kernel['kernel_path']).read_bytes()
    assert sha256(raw).hexdigest()==kernel['kernel_sha256']=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
    assert len(kernel['exports'])==3 and not kernel['original_kernel_executed_or_camera_access']
    for row in kernel['exports']:
        offset=int(row['file_offset'],16)
        assert sha256(raw[offset:offset+row['prefix_bytes']]).hexdigest()==row['prefix_sha256']
    tests=json.loads((HERE/'run-mode-tests/results.json').read_text())
    assert tests['MSC_reference_case_count']==len(tests['MSC_reference_cases'])==48
    assert tests['native_service_case_count']==len(tests['native_service_cases'])==24
    assert sum(x['original_return']==0 for x in tests['native_service_cases'])==12
    assert sum(x['original_return']==-2 for x in tests['native_service_cases'])==12
    assert tests['invalid_input_cases']==11 and len(tests['binding_rejections'])==20
    assert len(tests['inert_integrations'])==2 and tests['original_guest_function_entries']==120
    assert tests['legacy_faulty_SHA1_four_byte_length_equivalence'] and tests['new_USB_or_camera_driver_operations']==0
    assert not tests['initial_FX3_MSC_verifier_located_or_actual_authentication_proven']
    for current,saved in [('mode_digest_provider.py','provider-executed.py'),('test_mode_digest.py','test-executed.py')]:
        assert (HERE/current).read_bytes()==(HERE/'run-mode-tests'/saved).read_bytes()
    assert helper.digest(HERE/'mode_digest_provider.py')==tests['provider_sha256']
    assert helper.digest(HERE/'test_mode_digest.py')==tests['test_sha256']
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Explicit MSC/service CPU digest dispatch corrected; native callback and reference STALL boundary audited; no live USB'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段145核验144全部20成员及6个固定原型；上一轮属于一次获准真实描述符读取的实际进展，权限已消耗，本轮没有新增设备操作。',
        '实现显式MSC/0DA1与SERVICE/0336摘要分派，初始MSC参考挑战2/8只取前4B；服务原挑战8保留512B+512B算法，拒绝错误模式/PID/任务绑定及重复。',
        '48项MSC公开参考、24项服务原校验(12接受/12拒绝错误MSC摘要)、11无效输入、20绑定拒绝通过；两条惰性流程的MSC部分明确仅参考，对应服务原函数共120次进入。',
        '原7.02 usbg_sen回调尝试停其他驱动/排队后仍返回2且不验排队返回；21份官方7.00 GPL参考表明全部THRU时可最终报错，不能重试或假称无副作用，未假称精确7.02运行已证。',
        '从已固定7.02内核Image恢复3个USB导出候选与各0x120前缀；初始MSC验证者与完整7.02分派器仍未闭合，旧141双模式夹具证据已收紧，服务原校验证据保留。',
        '所有16项完整验收、完整授权/Mac-only及已消耗一次读取状态保持；没有新USB初始化、认证/切模式、驱动、机身文件或刷写。'])
    key='stage145_initial_MSC_mode_digest_and_vendor_boundary';assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key]={
        'readme':REL+'/README.md','provider':REL+'/mode_digest_provider.py','tests':REL+'/run-mode-tests/results.json',
        'original_and_reference_vendor_boundary':REL+'/mode-and-vendor-boundary-review.json',
        'kernel_exports':REL+'/native-kernel-usb-exports.json','official_reference_files':21,
        'MSC_public_reference_cases':48,'service_original_verifier_cases':24,'invalid_inputs':11,
        'binding_rejections':20,'inert_mode_flows':2,'original_guest_function_entries':120,
        'initial_FX3_MSC_native_verifier_or_live_authentication_proven':False,
        'reference_STALL_boundary_not_exact_702_wire_proof':True,'adopted143_external_pins':audit['adopted_unsealed143_evidence_pins'],
        'new_USB_camera_or_driver_operations':0,'authorization_unchanged':True}
    new['prepared_first_device_trial']['preferred_mode_bound_CPU_digest_provider']=REL+'/mode_digest_provider.py'
    new['prepared_first_device_trial']['mode_bound_CPU_digest_receipt']=REL+'/run-mode-tests/results.json'
    new['prepared_first_device_trial']['MSC_public_reference_challenge2_and8_prefix4_digest_implemented']=True
    new['prepared_first_device_trial']['completed_STALL_and_inflight_timeout_need_distinct_real_backend_handling']=True
    new['next_safe_offline_actions'].append(
        '阶段145后使用显式模式CPU摘要提供者，不能用旧141同服务验证器六轮夹具充初始MSC证明。沿原内核3项导出/注册回调继续追踪初始MSC验证者及完整7.02控制分派；实际传输补已结束STALL与未知超时/取消、端点角色及驱动归还，当前不放行服务会话。一次描述符权限保持消耗，不重新执行；全部主录、完整备份恢复和独立救援要求保持。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,value in old[section].items():assert new[section][k]==value
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3按模式摘要与控制请求边界](<'+REL+'/README.md>)：MSC公开参考/服务原函数分开验证，103项检查及两条惰性流程；原模块返回THRU的副作用边界已定位，初始MSC实机认证仍未证。'
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
    completed={'status':'PASS_MODE_DIGEST_FIX_AND_ORIGINAL_REFERENCE_BOUNDARIES_NOT_INITIAL_MSC_OR_DEVICE_AUTH',
        'created_utc':now,'previous_manifest_members_verified':count,'MSC_public_reference_cases':48,
        'service_original_verifier_cases':24,'invalid_inputs':11,'binding_rejections':20,'inert_mode_flows':2,
        'original_guest_function_entries':120,'official_reference_files':21,'native_kernel_export_candidates':3,
        'new_device_USB_library_initialization_authentication_driver_or_camera_file_operations':0,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'same_agent_local_review_not_camera_or_recovery_acceptance':True,
        'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage145-mode-digest-native-route/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
