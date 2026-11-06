#!/usr/bin/env python3
"""Seal original-kernel parsing and guest evidence, preserving all device gates."""
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
PRIOR=BASE/'stage145-initial-MSC-native-route'
PRIOR_SHA='2aeee45831cca4cfa09c2e4c20500ff0dfbc56cb752fde928998e0223b5f002d'
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
    helper.volume();count=helper.check_previous();assert count==41
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-before.md').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before);assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    fixed=helper.pins(old)
    review=json.loads((HERE/'completed-local-review.json').read_text())
    assert review['symbol_count']==41269 and review['original_export_pair_crosschecks']==6089
    assert review['sampled_original_name_expansion_guest_calls']==1007
    assert review['original_vendor_arm_cases']==11 and review['original_module_callback_entries']==8
    assert review['queue_attempt_can_precede_original_kernel_halt_request']
    assert review['queue_failure_can_coexist_with_no_halt_and_internal_zero_after_later_callback']
    assert review['w19_is_internal_helper_or_handled_result_not_host_USB_success']
    assert review['new_host_USB_camera_or_driver_operations']==0
    source=json.loads((HERE/'kernel-symbol-recovery.json').read_text())
    assert source['symbol_count']==41269 and source['original_kernel_sha256']==review['original_kernel_sha256']
    assert helper.digest(HERE/'work/kernel-symbol-catalog.json')==source['catalog_sha256']
    names=json.loads((HERE/'run-symbol-verification/results.json').read_text())
    assert names['recovered_symbols']==41269 and names['original_export_entries']==6089
    assert names['original_leaf_guest_calls']==len(names['original_leaf_cases'])==1007
    assert not names['all_41269_names_guest_executed']
    vendor=json.loads((HERE/'run-vendor-dispatch/results.json').read_text())
    assert vendor['case_count']==len(vendor['cases'])==vendor['original_kernel_vendor_arm_entries']==11
    assert vendor['original_module_callback_entries']==8 and vendor['new_host_USB_or_camera_operations']==0
    for current,directory,saved in [('kernel_symbols.py','run-symbol-verification','parser-executed.py'),
                                    ('verify_kernel_symbols.py','run-symbol-verification','test-executed.py'),
                                    ('run_vendor_dispatch_guest.py','run-vendor-dispatch','test-executed.py')]:
        assert (HERE/current).read_bytes()==(HERE/directory/saved).read_bytes()
    assert helper.digest(HERE/'kernel_symbols.py')==names['parser_sha256']==source['parser_sha256']
    assert helper.digest(HERE/'run_vendor_dispatch_guest.py')==vendor['test_sha256']
    for rec in review['reference_source_files']:
        path=HERE/rec['path'];assert path.stat().st_size==rec['bytes'] and helper.digest(path)==rec['sha256']
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Recovered original7.02 kernel symbols; original vendor arm and SEN callback joined in bounded guests, no live USB'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段146复核145全部41成员及6固定原型；上一轮显式模式摘要及103检查/两流程属于实际准备进展，本轮无新增设备访问。',
        '从原7.02 kernel的6个LDR literal恢复41269压缩符号及相对地址；原独立导出表6089对全匹配，原名称展开函数1007抽样guest通过名称/下一偏移/保护/SP/保存寄存器。',
        '实际静态函数被编译器变换/内联，使用constprop.1与原delayed_setup_thread跳表第4项定位vendor arm，没有强造独立函数地址。',
        '11个原7.02分派片段接8次原usbg_sen回调进入：排队尝试后仍可调用HALT桥；排队失败后后续回调0也可清内部标志/内部零值。源指令不等于实际driver/事件队列或线上的USB结果。',
        'IRQ/停其他driver/事件队列/HALT/printk/memcmp/其他回调为声明桥或夹具，线程前序参数/锁为合成，未启动Linux或实际服务；权限及全部16验收要求保持。'])
    key='stage146_original_kernel_symbols_and_vendor_route';assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key]={
        'readme':REL+'/README.md','kernel_symbol_parser':REL+'/kernel_symbols.py',
        'catalog':REL+'/work/kernel-symbol-catalog.json','symbol_verification':REL+'/run-symbol-verification/results.json',
        'vendor_guest':REL+'/run-vendor-dispatch/results.json','local_review':REL+'/completed-local-review.json',
        'recovered_original_symbols':41269,'independent_original_export_pairs':6089,'sampled_original_name_guest_calls':1007,
        'original_vendor_cases':11,'original_SEN_callback_entries':8,
        'bounded_original_702_conditional_halt_branch_proven':True,
        'actual_registration_queue_worker_or_USB_wire_proven':False,
        'initial_MSC_verifier_or_real_authentication_proven':False,'new_camera_or_driver_operations':0,
        'authorization_unchanged':True}
    new['prepared_first_device_trial']['original_702_kernel_symbol_parser']=REL+'/kernel_symbols.py'
    new['prepared_first_device_trial']['original_702_vendor_callback_guest_receipt']=REL+'/run-vendor-dispatch/results.json'
    new['prepared_first_device_trial']['original_kernel_internal_zero_or_halt_not_wire_or_queue_proof']=True
    new['next_safe_offline_actions'].append(
        '阶段146原7.02分派片段与模块联合guest已证条件HALT/内部零值边界，仍不能推实机USB/排队或线程完成。后续受限真实收发后端须区分已结束STALL、超时/在途、断开并无自动重试，驱动归还及协议状态单独验；沿已恢复符号/注册回调追初始MSC验证者，不再假设7.00参考静态布局。一次描述符权限仍消耗，完整主录/备份恢复/独立救援保持。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ('prepared_first_device_trial','latest_stage_evidence'):
        for k,value in old[section].items():assert new[section][k]==value
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    entry='- [2026-10-27 FX3原内核符号与控制分派联合验证](<'+REL+'/README.md>)：41269符号/6089导出对照、1007名称guest，11分派场景接原SEN回调；内部HALT/零值不充实际USB或排队成功，实机权限未增。'
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
    completed={'status':'PASS_ORIGINAL_SYMBOL_AND_VENDOR_GUEST_BOUNDARIES_NOT_REAL_KERNEL_OR_CAMERA_ACCEPTANCE',
        'created_utc':now,'previous_manifest_members_verified':count,'recovered_original_symbols':41269,
        'independent_original_export_pairs':6089,'original_leaf_name_guest_calls':1007,
        'original_vendor_arm_cases':11,'original_module_callback_entries':8,
        'new_USB_auth_driver_camera_file_or_firmware_operations':0,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'same_agent_local_review_not_real_camera_acceptance':True,
        'goal_complete':False,'persistent_write_release':False}
    put('completed-evidence-review.json',completed)
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage146-original-kernel-symbols-vendor/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
                           'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()},
        'operations':completed})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
                      'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
