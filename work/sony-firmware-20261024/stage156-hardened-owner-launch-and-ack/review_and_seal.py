#!/usr/bin/env python3
"""Seal a specific trial candidate, without changing any real authorization."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import copy
import difflib
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
REL=HERE.relative_to(ROOT).as_posix()
PRIOR=BASE/'stage155-fixed-owner-helper-and-independent-cache'
PRIOR_SHA='af9db5f51bc87174e4fb0b7d1eae20a592d84bd6d3532e9ccde45c83d86e8e98'
HELPER=BASE/'stage133-FX5-source-availability-and-portability'


def put(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (HERE/'final-receipt.json').exists()
    raw=(HELPER/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member=next(m for m in json.loads(raw)['files'] if m['path']==(HELPER/'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER/'review_and_seal.py').read_bytes()).hexdigest()==member['sha256']
    spec=importlib.util.spec_from_file_location('fixed_grant_sealer',HELPER/'review_and_seal.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.HERE,helper.REL,helper.PRIOR,helper.PRIOR_SHA=HERE,REL,PRIOR,PRIOR_SHA
    helper.volume();previous=helper.check_previous();assert previous==69
    canonical,index=BASE/'GOAL_STATUS.json',ROOT/'README.md'
    before=(HERE/'goal-status-before.json').read_bytes()
    assert canonical.read_bytes()==before==(PRIOR/'goal-status-after.json').read_bytes()
    original=(HERE/'readme-before.md').read_bytes();index_before=index.read_bytes()
    assert all(line in index_before.decode().splitlines() for line in original.decode().splitlines() if 'work/sony-firmware-20261024/' in line)
    with (HERE/'readme-rebased-before.md').open('xb') as f:f.write(index_before)
    put('index-rebase-review.json',{'original_sha256':sha256(original).hexdigest(),'rebased_sha256':sha256(index_before).hexdigest(),
        'all_previous_firmware_entries_preserved':True,'diff':list(difflib.unified_diff(original.decode().splitlines(),index_before.decode().splitlines(),lineterm=''))})
    old=json.loads(before);fixed=helper.pins(old)
    assert len(old['requirements'])==16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['driver_change'] and not old['authorization']['service_auth_mode_or_stop']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed'] and not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert not old['prepared_first_device_trial']['Mac_owner_trial_released']
    build=json.loads((HERE/'helper-build-receipt.json').read_text())
    assert build['ABI']==3 and build['entry_schema']==2 and not build['native_helper_executed_or_IOKit_loaded'] and not build['administrator_prompt_requested']
    for m in build['sources']:assert helper.digest(HERE/m['path'])==m['sha256']
    for label in ['native','fixture','ipc']:
        m=build[label];assert helper.digest(HERE/m['path'])==m['sha256']
        if label!='native':assert 'IOKit' not in m['dependencies'] and 'libusb' not in m['dependencies']
    assert (HERE/'build_helpers.py').read_bytes()==(HERE/'build-executed.py').read_bytes()
    derived=json.loads((HERE/'source-derivation.json').read_text());assert derived['parent_manifest_sha256']==PRIOR_SHA
    for m in derived['sources']:assert helper.digest(ROOT/m['source'])==m['source_sha256']
    for name in ['owner_trial.h','owner_core.c','owner_iokit.c','owner_fixture.c','owner_ipc.c','owner_binding.py','cache_observer.py']:
        assert (HERE/name).read_bytes()==(PRIOR/name).read_bytes()
    tests=json.loads((HERE/'hardened-entry-tests.json').read_text());observer=json.loads((HERE/'recorded-observer-tests.json').read_text())
    assert tests['checks']==len(tests['cases'])==12 and tests['fixture_jobs']==9 and tests['additional_fixture_processes']==1
    assert tests['all_fixture_relays_terminal'] and not tests['root_or_native_IOKit_helper_or_administrator_prompt_executed']
    assert observer['checks']==len(observer['cases'])==5 and observer['fixture_helpers']==2 and observer['orphan_parent_processes']==1
    assert not observer['native_IOKit_or_admin_executed']
    assert (HERE/'test_hardened_entry.py').read_bytes()==(HERE/'entry-test-executed.py').read_bytes()
    assert (HERE/'test_recorded_observer.py').read_bytes()==(HERE/'observer-test-executed.py').read_bytes()
    assert (HERE/'owner_supervisor.py').read_bytes()==(HERE/'supervisor-tested.py').read_bytes()==(HERE/'observer-supervisor-tested.py').read_bytes()
    cases={c['name']:c for c in tests['cases']}
    pending=cases['watchdog_deadline_sets_stop_pending_helper_stays_alive']['state']
    assert pending['verified_helper_alive'] and pending['final_deadline_passed'] and pending['active_native_call_phase']==4
    assert cases['exit_zero_wrong_receipt_keeps_provider_state_unknown']['state']['status']=='UNKNOWN_TERMINAL_RECEIPT_MISMATCH'
    assert cases['unacknowledged_helper_times_out_without_any_provider']['result']['receipt']['fixture_calls']==[0]*12
    review=json.loads((HERE/'local-source-and-lifetime-review.json').read_text())
    assert review['current_launch_fixture_checks']==12 and review['current_recorded_observer_checks']==5
    assert review['actual_own_parent_exit_tested'] and review['no_matching_fixture_helper_processes_currently_present']
    assert not review['root_IOKit_executable_or_administrator_prompt_executed'] and review['new_device_or_cache_queries']==0
    bundle_raw=(HERE/'release-bundle.json').read_bytes();bundle_sha=sha256(bundle_raw).hexdigest();bundle=json.loads(bundle_raw)
    assert bundle_sha==review['bundle_sha256']=='e099d58b73261c076491fc0c08c9b1b4b72f5a844fe3af22b3d8060110a956a4'
    assert bundle['grant_id']==build['grant_id']=='fx3-702-msc-owner-20261028-01'
    for m in bundle['files']:assert helper.digest(HERE/m['path'])==m['sha256']
    assert not (HERE/'physical-grant-attempt.claim').exists()
    assert not Path('/private/tmp/fx3-702-msc-owner-20261028-01').exists()
    now=datetime.now(timezone.utc).isoformat();new=copy.deepcopy(old)
    new['updated_utc']=now;new['latest_stage']=HERE.name
    new['research_activity']='Fixed grant/root-private hashed staging, actual helper ACK and independent recorded observer implemented;12 current launch checks plus5 recorded observer/own parent-exit checks;native/admin/device remain unexecuted'
    new['progress_audit']['classification']='progress';new['progress_audit']['previous_goal_turn_classification']='progress'
    new['progress_audit']['basis'].extend([
        '阶段156重验155全部69成员；上轮固定C入口/37核心及14观察器检查是进展，本轮将固定grant的root staging、共享文件openat/fstat、父监管ACK和看门线程实现为具体候选。',
        '管理员中继与实际helper分开核对：内核PID/UID/出生时间/固定可执行路径确认后才ACK；缺失元数据另查内核PID存在性，不把查询失败当终止。运行包固定源码/构建/目标/编号，root私有复制件按精确SHA核验，跨新共享文件亦有固定root入口租约。',
        '当前12项启动夹具/9任务+1直接C重用反例，以及5项记录观察/2 helper+1真实自写父进程退出检查通过。超时保留原在途helper，只请求停止；父进程消失后看门线程请求停止，释放自写夹具后单次归还关闭，无重启。收尾未见相关helper。',
        '所有实际运行对象均为不链接IOKit的自写fixture；真实root helper和管理员脚本从未执行，本轮连缓存查询也未增加。无法以夹具证明root元数据可见性、真实Seize/capture/MSC归还或相机恢复。SDK capture排除MSC终止的限制保留，驱动仍在则claim前中止。',
        '形成单次试验具体审阅版本，尚未取得设备/驱动/管理员授权且release=false；未扩大原授权。16项主录/同机健康恢复/独立救援及无可刷包/无刷入日期保持。'])
    new['latest_stage_evidence']['stage156_fixed_grant_owner_launch_and_ACK']={
        'readme':REL+'/README.md','bundle':REL+'/release-bundle.json','bundle_sha256':bundle_sha,'build':REL+'/helper-build-receipt.json',
        'launch_checks':REL+'/hardened-entry-tests.json','recorded_observer_checks':REL+'/recorded-observer-tests.json',
        'review':REL+'/local-source-and-lifetime-review.json','entry_schema':2,'ABI':3,'current_checks':17,
        'native_executable_sha256':build['native']['sha256'],'native_IOKit_or_admin_executed':False,'new_device_or_cache_queries':0,'physical_acceptance':False}
    key='Mac_owner_trial_fixed_grant_ACK_candidate'
    new['prepared_first_device_trial'][key]={'readme':REL+'/README.md','bundle':REL+'/release-bundle.json','bundle_sha256':bundle_sha,
        'grant_id':build['grant_id'],'build':REL+'/helper-build-receipt.json','native_candidate_sha256':build['native']['sha256'],
        'state':'SPECIFIC_AUTHORIZATION_REVIEW_CANDIDATE_NOT_NATIVE_OR_DEVICE_ACCEPTANCE','released':False}
    selector='Mac_owner_trial_current_candidate_key';new['prepared_first_device_trial'][selector]=key
    new['next_safe_offline_actions'].append('156固定grant/复制后哈希/root入口租约/实际helper ACK/看门线程/记录观察已经离线实现，17项当前自写检查通过。下一步可请求具体一次USB接管归还与本机管理员staging授权；必须先人工推出该机所有卷并保持MSC，绑定固定编号和运行包SHA，现有缓存/已消耗描述符/UU权限均不覆盖。若未授权，继续离线完善真实备份读取/恢复入口，不调用admin或live helper。实际root元数据/SDK capture/驱动归还未验；Unknown不重置重试。刷写/主录/完整健康恢复/独立救援仍未放行。')
    allowed={'updated_utc','latest_stage','research_activity','progress_audit','latest_stage_evidence','prepared_first_device_trial','next_safe_offline_actions'}
    for k in old:
        if k not in allowed:assert new[k]==old[k],k
    for section in ['latest_stage_evidence','prepared_first_device_trial']:
        for k,v in old[section].items():
            if section=='prepared_first_device_trial' and k==selector:continue
            assert new[section][k]==v
    assert new['authorization']==old['authorization'] and new['requirements']==old['requirements']
    encoded=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    with (HERE/'goal-status-after.json').open('xb') as f:f.write(encoded)
    marker='## 相机与固件研究\n';entry='- [2026-10-28 FX3固定单次接管与实际进程确认](<'+REL+'/README.md>)：17项当前自写检查通过，含真实fixture父进程退出；root私有哈希staging/独立入口租约/ACK与记录观察已实现，真实管理员及设备仍未执行。'
    text=index_before.decode();assert text.count(marker)==1 and entry not in text
    index_after=text.replace(marker,marker+'\n'+entry+'\n',1).encode()
    with (HERE/'readme-after.md').open('xb') as f:f.write(index_after)
    helper.volume();assert canonical.read_bytes()==before and index.read_bytes()==index_before,'Concurrent heads changed; CAS refused'
    assert helper.pins(old)==fixed
    for target,data,name in [(canonical,encoded,'.goal-final.tmp'),(index,index_after,'.index-final.tmp')]:
        temp=HERE/name
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    assert canonical.read_bytes()==encoded and index.read_bytes()==index_after;helper.check_previous()
    put('completed-evidence-review.json',{'status':'PASS_FIXED_GRANT_ACK_AND_RECORDED_FIXTURES_NOT_ADMIN_OR_CAMERA_ACCEPTANCE','created_utc':now,
        'previous_manifest_members_verified':previous,'current_launch_checks':12,'current_recorded_observer_checks':5,
        'all16_requirements_authorization_constraints_and_old_candidates_preserved':True,'only_existing_prepared_selector_updated':selector,
        'fixed_guest_backend_frontend_pins':fixed,'goal_complete':False,'persistent_write_release':False,'Mac_owner_trial_released':False,
        'root_native_helper_or_administrator_executed':False,'new_device_or_cache_queries':0})
    files=[helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json',{'schema':'fx3-stage156-fixed-grant-and-ACK/1','created_utc':now,'volume_uuid':helper.UUID,
        'files':files,'member_count':len(files),'previous_manifest_sha256':PRIOR_SHA,'allowed_goal_keys_changed':sorted(allowed),
        'mutable_project_heads_not_manifest_members':True,'mutable_progress':{'before_sha256':sha256(before).hexdigest(),
        'after_sha256':sha256(encoded).hexdigest(),'readme_before_sha256':sha256(index_before).hexdigest(),'readme_after_sha256':sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256':helper.digest(HERE/'final-receipt.json'),'members':len(files),
        'canonical_sha256':helper.digest(canonical),'goal_complete':False,'persistent_write_release':False}))


if __name__=='__main__':main()
