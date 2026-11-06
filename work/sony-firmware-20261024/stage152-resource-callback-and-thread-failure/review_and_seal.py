#!/usr/bin/env python3
"""Seal original resource failure flow and host capture source evidence."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import copy
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
PRIOR = BASE / 'stage151-latest-A7CII-HEVC-evidence'
PRIOR_SHA = '9a511f3b70ab5d2cb596ea9ce20a7fec4e2e300f1d544d8174db8252afb82c54'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(name, value):
    with (HERE / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    raw = (HELPER / 'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    member = next(m for m in json.loads(raw)['files'] if m['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == member['sha256']
    helper = load('fixed_resource_sealer', HELPER / 'review_and_seal.py')
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    previous_count = helper.check_previous()
    assert previous_count == 185
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert not old['authorization']['service_auth_mode_or_stop'] and not old['authorization']['driver_change']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    fixed = helper.pins(old)
    assert (HERE / 'original_resource.py').read_bytes() == (HERE / 'static-executed.py').read_bytes()
    assert (HERE / 'original_resource.py').read_bytes() == (HERE / 'run-original-resource/source-executed.py').read_bytes()
    assert (HERE / 'run_resource_failure.py').read_bytes() == (HERE / 'run-original-resource/test-executed.py').read_bytes()
    assert (HERE / 'audit_host_capture.py').read_bytes() == (HERE / 'host-audit-executed.py').read_bytes()
    source = load('reviewed_resource_static', HERE / 'original_resource.py')
    unused, obj, mwf = source.images()
    static = json.loads((HERE / 'original-resource-static.json').read_text())
    assert len(static['object_functions']) == 10 and len(static['middleware_functions']) == 5
    for image, section in [(obj, 'object_functions'), (mwf, 'middleware_functions')]:
        for f in static[section]:
            assert sha256(image.read(int(f['VA'], 16), f['bytes'])).hexdigest() == f['sha256']
    results = json.loads((HERE / 'run-original-resource/results.json').read_text())
    assert results['test_sha256'] == helper.digest(HERE / 'run_resource_failure.py')
    assert results['case_count'] == 14 and results['original_function_entries'] == 102
    assert results['new_device_Windows_USB_operations'] == 0
    assert not results['real_queue_delivery_thread_exit_dlclose_or_mode_transition_proven']
    assert not results['actual_initial_MSC_auth_or_runtime_registration_proven']
    callbacks, workers = results['callback_cases'], results['worker_cases']
    assert len(callbacks) == 8 and len(workers) == 6
    assert callbacks[1]['resource_thread_flag_after'] == 1 and callbacks[1]['last_return_low32'] == 0
    assert callbacks[1]['thread_create_calls'][0]['result_fixture'] == 11 and callbacks[1]['sem_post_calls'] == [22]
    assert workers[1]['join_calls'] == [3] and workers[1]['old_thread_token_after'] == '0x71' and workers[1]['internal_state_after'] == 4
    assert workers[2]['dlclose_calls'] == [-1] and workers[2]['loader_token_after'] == '0x0'
    for c in callbacks + workers:
        assert c['original_code_unchanged_and_entry_stack_guard_preserved']
    capture = json.loads((HERE / 'host-capture-source-receipt.json').read_text())
    for item in capture['items']:
        path = HERE / item['path'] if item['path'].startswith('work/public-source/') else ROOT / item['path']
        assert path.stat().st_size == item['bytes'] and helper.digest(path) == item['sha256']
    audit = json.loads((HERE / 'host-capture-audit.json').read_text())
    upstream = HERE / capture['items'][0]['path']
    lines = upstream.read_text().splitlines()
    assert len(audit['facts']) == 5 and not audit['downloaded_source_compiled_imported_or_executed']
    for f in audit['facts']:
        text = '\n'.join(lines[f['first_line'] - 1:f['last_line']])
        assert sha256(text.encode()).hexdigest() == f['sha256_of_line_excerpt']
        assert all(marker in text for marker in f['checked_markers'])
    now = datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json', {
        'created_utc': now, 'original_functions_checked': 15, 'guest_cases': 14, 'original_entries': 102,
        'resource_create_failure_can_coexist_with_callback_zero_and_flag1': True,
        'join_failure_can_coexist_with_internal_state4': True,
        'dlclose_failure_control_clears_loader_token': True,
        'whole_device_capture_and_capture_reopen_vs_attach_reenumeration_distinguished_in_release_source': True,
        'actual_mode_thread_exit_driver_return_or_recording_acceptance': False,
        'new_device_operations': 0, 'same_agent_local_review_only': True})
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Original resource/worker failure flow checked in14 CPU cases; Darwin libusb capture scope and restore-return boundary audited as source'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段152重验151全部185成员；上一轮一手A7CII演示资料是进展，本轮公开搜索未取得具体HEVC补丁/原片，未把重复搜索充新实现。',
        '接续150原MWF提取工作，核对15原函数及构造回调重定位，14组有界CPU实验/102原进入。key/pending、资源回调、线程创建失败、取消/等待及加载器失败边界有新原指令证据。',
        'pthread_create返回11时仍置资源标志1，下次回调转sem_post；post返回22时MWF仍可返回0。取消/等待失败后原worker仍可到内部状态4，不能作真实线程结束或模式/恢复成功依据。',
        '固定libusb1.0.30官方Darwin源码确认整设备capture；capture路径重开而非普通重新枚举，最终attach走非capture重新枚举。restore有条件配置恢复，自动release可忽略attach失败。上机owner设计须纳入全部卷/驱动/连接代次和隐含操作。',
        'CPU外部OS/消息/列表/加载器均为夹具，未验证真实资源队列或驱动归还；未执行下载工具，无新增USB/相机/Windows/UU或权限操作，原16要求及全部旧准备值保留。'])
    new['latest_stage_evidence']['stage152_resource_worker_failures_and_Mac_capture_scope'] = {
        'readme': REL + '/README.md', 'static': REL + '/original-resource-static.json',
        'guest': REL + '/run-original-resource/results.json', 'host_capture_audit': REL + '/host-capture-audit.json',
        'review': REL + '/completed-local-review.json', 'cases': 14, 'original_entries': 102,
        'internal_flags_and_wrapper_returns_not_completion_proof': True,
        'capture_scope_entire_device_in_libusb1_0_30_source': True,
        'actual_OS_or_device_acceptance': False, 'new_device_operations': 0}
    new['prepared_first_device_trial']['resource_callback_worker_failure_audit'] = REL + '/run-original-resource/results.json'
    new['prepared_first_device_trial']['Mac_whole_device_capture_scope_audit'] = REL + '/host-capture-audit.json'
    new['prepared_first_device_trial']['internal_state_and_host_release_not_recovery_acceptance'] = True
    new['next_safe_offline_actions'].append('实现真实Mac owner前先固定native后端及整设备capture/归还范围，审核全部相机卷、重开身份与连接代次、隐含配置恢复和工作进程寿命。禁止auto-detach；release0/STOP回复/内部状态1或4不充恢复。原MWF回调和worker失败证据已取得，不再用局部状态代替实际线程结束。一次性服务试验仍未放行，HEVC原片/补丁与全部主录/完整恢复/独立救援要求保持。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit', 'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('prepared_first_device_trial', 'latest_stage_evidence'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    marker = '## 相机与固件研究\n'
    entry = '- [2026-10-27 FX3资源回调/线程失败与Mac整设备接管](<' + REL + '/README.md>)：14组原指令guest确认内部标志不充完成；固定Darwin源码区分capture重开和attach重新枚举，驱动返回另验，无新增设备操作。'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent head change; CAS refused'
    assert helper.pins(old) == fixed
    for target, data, name in [(canonical, encoded, '.goal-final.tmp'), (index, index_after, '.index-final.tmp')]:
        temp = HERE / name
        with temp.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    helper.check_previous()
    put('completed-evidence-review.json', {
        'status': 'PASS_ORIGINAL_RESOURCE_FAILURE_AND_HOST_CAPTURE_SCOPE_NOT_CAMERA_ACCEPTANCE', 'created_utc': now,
        'previous_manifest_members_verified': previous_count, 'guest_cases': 14, 'original_entries': 102,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved': True,
        'fixed_guest_backend_frontend_pins': fixed, 'new_device_operations': 0,
        'goal_complete': False, 'persistent_write_release': False, 'same_agent_local_review_only': True})
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage152-resource-worker-failure-and-host-capture/1',
        'created_utc': now, 'volume_uuid': helper.UUID, 'files': files, 'member_count': len(files),
        'previous_manifest_sha256': PRIOR_SHA, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
        'canonical_sha256': helper.digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
