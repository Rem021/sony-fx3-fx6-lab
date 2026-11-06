#!/usr/bin/env python3
"""Seal compiled fixed entry and own fixtures; do not authorize native launch."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import copy
import difflib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage154-isolated-owner-supervisor'
PRIOR_SHA='179ccacabb5c1cd30f6ad85c704499a27f15e2952ad6309fa80087742fdbc8bf'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==member['sha256']
    spec=importlib.util.spec_from_file_location('fixed_helper_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous=helper.check_previous();assert previous==208
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    original_index=(HERE/'readme-before.md').read_bytes();index_before=index.read_bytes()
    # Preserve the latest unrelated index edits verbatim; never roll them back.
    old_research=[x for x in original_index.decode().splitlines() if 'work/sony-firmware-20261024/' in x]
    assert all(x in index_before.decode().splitlines() for x in old_research)
    with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(index_before)
    put('index-rebase-review.json',{'original_before_sha256':sha256(original_index).hexdigest(),
        'rebased_before_sha256':sha256(index_before).hexdigest(),'all_existing_firmware_entries_preserved':True,
        'concurrent_diff':list(difflib.unified_diff(original_index.decode().splitlines(),index_before.decode().splitlines(),lineterm=''))})
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['driver_change'] and not old['authorization']['service_auth_mode_or_stop']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert not old['prepared_first_device_trial']['Mac_owner_trial_released']
    build=json.loads((HERE/'helper-build-receipt.json').read_text())
    assert build['ABI']==3 and not build['native_helper_executed_or_IOKit_loaded']
    assert not build['administrator_prompt_requested'] and build['applescript_compiled_not_executed']
    for m in build['sources']:assert helper.digest(HERE/m['path'])==m['sha256']
    for label in ['native','fixture','ipc']:
        m=build[label];assert helper.digest(HERE/m['path'])==m['sha256']
    for label in ['fixture','ipc']:
        assert 'IOKit' not in build[label]['dependencies'] and 'libusb' not in build[label]['dependencies']
    assert (HERE/'build_helpers.py').read_bytes()==(HERE/'build-executed.py').read_bytes()
    assert (HERE/'prepare_sources.py').read_bytes()==(HERE/'prepare-executed.py').read_bytes()
    derivation=json.loads((HERE/'source-derivation.json').read_text())
    assert derivation['prior_manifest_sha256']==PRIOR_SHA
    for m in derivation['files']:assert helper.digest(ROOT/m['source_path'])==m['source_sha256']
    core=json.loads((HERE/'run-core-regression/results.json').read_text())
    assert core['case_count']==len(core['cases'])==37 and not core['actual_IOKit_candidate_loaded']
    assert core['actual_USB_or_device_operations']==0
    for name in ['owner_trial.h','owner_core.c','owner_fixture.c','owner_binding.py','test_core_regression.py']:
        assert (HERE/name).read_bytes()==(HERE/'run-core-regression'/name).read_bytes()
    regression=json.loads((HERE/'regression-derivation.json').read_text())
    assert helper.digest(ROOT/regression['source_path'])==regression['source_sha256']
    assert helper.digest(HERE/'test_core_regression.py')==regression['output_sha256']
    tests=json.loads((HERE/'fixed-helper-tests.json').read_text())
    assert tests['checks']==len(tests['cases'])==13 and tests['fixture_process_count']==14
    assert tests['all_fixture_processes_terminal'] and not tests['native_IOKit_helper_or_admin_script_executed']
    assert tests['new_device_operations']==0
    assert (HERE/'test_fixed_helper.py').read_bytes()==(HERE/'helper-test-executed.py').read_bytes()
    cache_tests=json.loads((HERE/'cache-observer-tests.json').read_text())
    assert cache_tests['count']==len(cache_tests['checks'])==14 and not cache_tests['real_cache_queried_by_test']
    for a,b in [('test_cache_observer.py','cache-test-executed.py'),('cache_observer.py','cache-observer-tested.py')]:
        assert (HERE/a).read_bytes()==(HERE/b).read_bytes()
    cache=json.loads((HERE/'current-cache-observation.json').read_text())
    assert cache['cached_only'] and not cache['raw_tree_serial_or_privacy_key_saved']
    assert cache['collector_sha256']==helper.digest(HERE/'cache_observer.py') and cache['selected_count']==1
    selected=cache['selected'][0]
    assert selected['model_matches'] and selected['cached_identity_usable'] and selected['MSC_interface0_observed']
    assert selected['storage_driver_classes']
    review=json.loads((HERE/'local-source-and-lifetime-review.json').read_text())
    for m in review['production_sources']:assert helper.digest(HERE/m['path'])==m['sha256']
    assert review['no_matching_helper_processes_currently_present'] and review['all_fixture_processes_terminal_by_Popen']
    assert not review['real_native_or_administrator_script_executed'] and review['USB_active_or_driver_operations']==0
    assert review['authorized_cached_metadata_queries']==1 and len(review['critical_remaining'])==7
    plan=json.loads((HERE/'candidate-plan.json').read_text())
    assert plan['ABI']==3 and not plan['Mac_owner_trial_released'] and not plan['authorization_changed']
    assert plan['native_candidate']['sha256']==build['native']['sha256']
    now=datetime.now(timezone.utc).isoformat()
    new=copy.deepcopy(old);new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='ABI3 fixed C entry compiled;13 fixed fixture executable checks/14 processes,37 C regressions,14 independent cache observer checks;one authorized cache observation;live parent and release remain missing'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段155重验154全部208成员，保留原件后派生ABI3，在创建用户客户端之前核对预选同机HMAC标签。固定C入口及仅IPC库已编译，原生IOKit helper与管理员脚本从未执行。',
        '13项固定fixture检查/14进程含跨进程与并发重复启动拒绝、内核PID出生身份、错机身及权限/链接/路径负例通过。37项C回归保留旧35项并验证缺失/错误预选机身标签。均为自写无IOKit夹具，不充设备验收。',
        '独立缓存观察器14项自写检查通过；现有Mac缓存授权内实际采集一次，当时指定端口FX3/MSC及存储驱动链在；原序列号不落盘，规划HMAC键未保留，该标签不直接复用为实机任务身份。缓存关联不充驱动功能或恢复。',
        '单次占用目前仅限同一共享文件；live调用端/管理员中继与root真正进程监管、固定物理grant跨新文件租约、用户可写外置卷路径替换及挂载竞态尚未补齐。候选仍未放行，不请求或执行提权。',
        '首次刷入不能给日期：尚无专用可刷包、完整同机健康备份/恢复回读、独立救援或目标原片。16项要求/设备权限保持，下一实机候选仍是接管归还而非刷写。'])
    ev={'readme':REL+'/README.md','plan':REL+'/candidate-plan.json','build':REL+'/helper-build-receipt.json',
        'C_core_regression':REL+'/run-core-regression/results.json','fixed_fixture_tests':REL+'/fixed-helper-tests.json',
        'cache_observer_fixture_tests':REL+'/cache-observer-tests.json','cache_observation':REL+'/current-cache-observation.json',
        'review':REL+'/local-source-and-lifetime-review.json','ABI':3,'C_checks':37,'fixed_helper_checks':13,'fixture_processes':14,
        'cache_observer_checks':14,'authorized_cache_queries':1,'native_executable_sha256':build['native']['sha256'],
        'native_helper_or_administrator_executed':False,'physical_acceptance':False,'active_device_operations':0}
    new['latest_stage_evidence']['stage155_fixed_owner_entry_and_independent_cache']=ev
    key='Mac_owner_trial_ABI3_fixed_entry_candidate'
    new['prepared_first_device_trial'][key]={'plan':REL+'/candidate-plan.json','build':REL+'/helper-build-receipt.json',
        'native_candidate_sha256':build['native']['sha256'],'test':REL+'/fixed-helper-tests.json',
        'clock_domain':'CLOCK_MONOTONIC','state':'FIXED_ENTRY_COMPILED_FIXTURE_TESTED_LIVE_PARENT_AND_RELEASE_MISSING'}
    selector='Mac_owner_trial_current_candidate_key'
    new['prepared_first_device_trial'][selector]=key
    new['next_safe_offline_actions'].append('155固定C入口/同机标签/独立缓存观察器已经离线验证，真实入口仍缺调用端、管理员中继与root实际PID监管、跨新文件的物理授权租约，以及外置卷路径替换/挂载竞态审查。不得直接调用AppleScript或native helper；仅同一共享文件的CAS不等于整份实机授权单次。后续完成具体方案并单独授权后，才可试USB接管归还；备份/恢复回读、独立救援、临时HEVC实录及持久刷入仍未放行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ['latest_stage_evidence','prepared_first_device_trial']:
        for k,v in old[section].items():
            if section=='prepared_first_device_trial' and k==selector:continue
            assert new[section][k]==v,(section,k)
    assert new['authorization']==old['authorization'] and new['requirements']==old['requirements']
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
    marker='## 相机与固件研究\n'
    entry='- [2026-10-28 FX3固定原生入口与独立缓存观察](<'+REL+'/README.md>)：13项固定fixture进程检查/37项C回归/14项观察器检查；一次已授权缓存采集，真实提权/接管入口仍未放行，无可刷包。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    with (HERE/'readme-after.md').open('xb') as f:f.write(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after
    helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_FIXED_C_ENTRY_FIXTURES_AND_CACHE_OBSERVER_NOT_NATIVE_OR_CAMERA_ACCEPTANCE',
        'created_utc':now,'previous_manifest_members_verified':previous,'C_core_checks':37,'fixed_fixture_checks':13,
        'fixture_processes':14,'cache_observer_checks':14,'authorized_cache_queries':1,'native_helper_or_administrator_executed':False,
        'all16_requirements_authorization_constraints_and_previous_candidates_preserved':True,
        'only_existing_prepared_selector_updated':selector,'fixed_guest_backend_frontend_pins':fixed,
        'goal_complete':False,'persistent_write_release':False,'Mac_owner_trial_released':False,'active_device_operations':0})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage155-fixed-owner-entry-and-cache/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,'allowed_goal_keys_changed':sorted(allowed),
        'mutable_project_heads_not_manifest_members':True,'mutable_progress':{'before_sha256':sha256(before).hexdigest(),
        'after_sha256':sha256(encoded).hexdigest(),'readme_before_sha256':sha256(index_before).hexdigest(),
        'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
