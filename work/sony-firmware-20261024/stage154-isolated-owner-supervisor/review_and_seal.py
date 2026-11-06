#!/usr/bin/env python3
"""Seal ABI2/process-fixture evidence, without changing device permissions."""
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
PRIOR=BASE/'stage153-Mac-owned-interface-trial'
PRIOR_SHA='27fbc16f5e22e122de6bb144116be44454f5a52b5c07d9eef2361ae681f57460'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as handle:
        json.dump(value,handle,ensure_ascii=False,indent=2);handle.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==member['sha256']
    spec=importlib.util.spec_from_file_location('fixed_isolated_owner_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous_count=helper.check_previous();assert previous_count==41
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before,index_before=(HERE/'goal-status-before.json').read_bytes(),(HERE/'readme-rebased-before.md').read_bytes()
    rebase=json.loads((HERE/'index-rebase-review.json').read_text())
    assert sha256(index_before).hexdigest()==rebase['rebased_before_sha256']
    assert sha256((HERE/'readme-before.md').read_bytes()).hexdigest()==rebase['original_before_sha256']
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    assert index.read_bytes()==index_before
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert not old['authorization']['driver_change'] and not old['authorization']['service_auth_mode_or_stop']
    assert not old['prepared_first_device_trial']['Mac_owner_trial_released']
    build=json.loads((HERE/'build-receipt.json').read_text())
    assert build['ABI']==2 and not build['native_candidate_loaded'] and build['new_device_operations']==0
    for m in build['sources']:assert helper.digest(HERE/m['path'])==m['sha256']
    for label in ['fixture','native']:
        item=build[label];assert helper.digest(HERE/item['path'])==item['sha256']
    assert 'IOKit' not in build['fixture']['dependencies'] and 'libusb' not in build['fixture']['dependencies']
    assert (HERE/'build_candidates.py').read_bytes()==(HERE/'build-executed.py').read_bytes()
    assert (HERE/'prepare_sources.py').read_bytes()==(HERE/'prepare-executed.py').read_bytes()
    derived=json.loads((HERE/'source-derivation.json').read_text())
    assert derived['prior_manifest_sha256']==PRIOR_SHA
    for m in derived['files']:assert helper.digest(ROOT/m['source_path'])==m['source_sha256']
    core=json.loads((HERE/'run-core-regression/results.json').read_text())
    assert core['case_count']==len(core['cases'])==35 and not core['actual_IOKit_candidate_loaded']
    assert core['actual_USB_or_device_operations']==0
    for name in ['owner_trial.h','owner_core.c','owner_fixture.c','owner_binding.py','test_core_regression.py']:
        assert (HERE/name).read_bytes()==(HERE/'run-core-regression'/name).read_bytes()
    regression=json.loads((HERE/'regression-derivation.json').read_text())
    assert helper.digest(HERE/'test_core_regression.py')==regression['output_sha256']
    processes=json.loads((HERE/'run-process-tests/results.json').read_text())
    assert processes['checks']==len(processes['cases'])==14 and processes['fixture_worker_jobs']==9
    assert processes['all_created_fixture_workers_terminal']
    assert not processes['real_IOKit_candidate_loaded_or_device_operations'] and not processes['actual_driver_return_or_HEVC_recording_proven']
    assert (HERE/'test_supervisor.py').read_bytes()==(HERE/'run-process-tests/test-executed.py').read_bytes()
    cases={c['name']:c for c in processes['cases']}
    pending=cases['actual_handle_verified_alive_after_deadline']['state']
    assert pending['verified_worker_alive'] and pending['final_deadline_passed'] and pending['active_native_call_phase']==4
    assert pending['stop_requested'] and not pending['restarted_or_killed']
    assert cases['deadline_does_not_kill_or_retry_pending_native_call']['state']['status']=='UNKNOWN_PROVIDER_STATE'
    assert cases['own_fixture_death_keeps_native_state_unknown']['state']['status']=='UNKNOWN_TERMINAL_WITHOUT_VALID_RECEIPT'
    assert cases['simulated_authority_pass_still_no_live_worker']['rejected_before_process_or_native_load']
    life=json.loads((HERE/'all-workers-terminal.json').read_text())
    assert life['count']==len(life['records'])==15 and all(not p['same_nonce_worker_present_now'] for p in life['records'])
    source_review=json.loads((HERE/'local-source-and-lifetime-review.json').read_text())
    for p in source_review['production_modules']:assert helper.digest(HERE/p['path'])==p['sha256']
    assert source_review['clock_domain']=='CLOCK_MONOTONIC' and not source_review['true_native_library_loaded']
    plan=json.loads((HERE/'candidate-plan.json').read_text())
    assert plan['ABI']==2 and not plan['Mac_owner_trial_released'] and not plan['authorization_changed']
    assert plan['native_candidate']['sha256']==build['native']['sha256']
    now=datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json',{
        'created_utc':now,'C_core_checks':35,'isolated_process_checks':14,'current_fixture_workers':9,
        'all_recorded_fixture_workers_terminal':15,'real_Popen_wait_kept_across_pending_timeout':True,
        'terminal_without_valid_receipt_remains_unknown':True,'clock_domain_unified_to_CLOCK_MONOTONIC':True,
        'framework_reexec_whitelist_birth_nonce_and_fixed_argv_verified':True,
        'strong_kill_only_in_own_non_IOKit_fixture_fault_injection':True,
        'native_IOKit_library_loaded_or_actual_driver_or_camera_acceptance':False,
        'real_privileged_launch_and_independent_driver_return_still_missing':True,
        'same_agent_local_review_only':True,'new_device_operations':0})
    new=copy.deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='ABI2 cooperative stop/shared progress and isolated own-fixture supervisor implemented;14 checks/9 processes plus35 C regressions; actual IOKit worker remains unreleased'
    new['progress_audit']['previous_goal_turn_classification']='progress';new['progress_audit']['classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段154重验153全部41成员；上一轮编译未加载的原生接管候选为进展，本轮实现ABI2停止块、原子在途观察、隔离fixture worker和实际Popen监管。',
        '14项进程检查/9个当前自写fixture子进程，通过同一Popen及当前ps身份确认仍存活；期限已过仍不杀不重启，待调用返回再单次清理。无回执/错误回执/进程消失保持UNKNOWN，旧单次记录不重用。全部15个含历史/诊断fixture已查无原nonce进程。',
        '实际测得Python mach_absolute_time与C CLOCK_MONOTONIC本机当时差约4.54秒，已统一绝对截止时间为显式CLOCK_MONOTONIC；Python Framework重执行前缀变化改以启动时间/白名单解释器/固定参数/nonce核对，保留失败原件。',
        'ABI2 C核心35项回归含提前停止与错误控制块ABI通过。真实IOKit库只编译未加载，worker仅fixture，管理员/一次性实机入口和独立驱动回读尚未实现，不将进程验收充实机恢复或录像。',
        '无新增相机/USB/Windows/UU/驱动/提权/权限操作，一次描述符权限仍消耗，原16主录/完整同机恢复与独立救援要求及全部旧准备值保持。'])
    evidence={'readme':REL+'/README.md','plan':REL+'/candidate-plan.json','build':REL+'/build-receipt.json',
        'C_core_regression':REL+'/run-core-regression/results.json','isolated_processes':REL+'/run-process-tests/results.json',
        'review':REL+'/completed-local-review.json','ABI':2,'C_checks':35,'process_checks':14,'current_fixture_jobs':9,
        'real_native_candidate_sha256':build['native']['sha256'],'real_IOKit_loaded':False,'physical_acceptance':False,'new_device_operations':0}
    new['latest_stage_evidence']['stage154_isolated_owner_supervisor']=evidence
    key='Mac_owner_trial_ABI2_supervisor_candidate'
    new['prepared_first_device_trial'][key]={'plan':REL+'/candidate-plan.json','build':REL+'/build-receipt.json',
        'native_candidate_sha256':build['native']['sha256'],'process_regression':REL+'/run-process-tests/results.json',
        'clock_domain':'CLOCK_MONOTONIC','state':'FIXTURE_PROCESS_SUPERVISION_VERIFIED_NATIVE_WORKER_UNRELEASED'}
    new['prepared_first_device_trial']['Mac_owner_trial_current_candidate_key']=key
    new['next_safe_offline_actions'].append('154 ABI2已验证fixture进程监管和35项C核心；后续实现实际IOKit worker绑定、管理员一次性入口及按固定物理grant/build/target消耗的凭据，独立采集前后driver/media并复核卸载/自动挂载竞态。所有绝对期限必须CLOCK_MONOTONIC；进程重接比对启动时间/固定argv/nonce而非整行前缀。未知在途不杀不重试。完整HEVC MAIN/同机恢复/独立救援和具体新授权仍保留。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ['prepared_first_device_trial','latest_stage_evidence']:
        for k,v in old[section].items():assert new[section][k]==v
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode();(HERE/'goal-status-after.json').write_bytes(encoded)
    marker='## 相机与固件研究\n'
    entry='- [2026-10-28 FX3隔离接管监管与Mac时钟修正](<'+REL+'/README.md>)：14项真实fixture进程检查/35项C回归，超时保留同一在途进程；统一CLOCK_MONOTONIC，真实IOKit与提权入口仍关闭，无新增设备操作。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode();(HERE/'readme-after.md').write_bytes(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_ABI2_AND_ISOLATED_FIXTURE_SUPERVISION_NOT_IOKIT_OR_CAMERA_ACCEPTANCE',
        'created_utc':now,'previous_manifest_members_verified':previous_count,'C_core_checks':35,'process_checks':14,
        'all16_requirements_authorization_constraints_and_old_prepared_values_preserved':True,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False,
        'Mac_owner_trial_released':False,'new_device_operations':0})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage154-isolated-owner-supervisor/1','created_utc':now,
        'volume_uuid':helper.UUID,'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,
        'allowed_goal_keys_changed':sorted(allowed),'mutable_project_heads_not_manifest_members':True,
        'mutable_progress':{'before_sha256':sha256(before).hexdigest(),'after_sha256':sha256(encoded).hexdigest(),
            'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
