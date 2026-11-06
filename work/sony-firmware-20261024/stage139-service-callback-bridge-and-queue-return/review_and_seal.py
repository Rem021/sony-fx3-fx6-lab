#!/usr/bin/env python3
"""Seal callback evidence and bounded queue-counterexample fixtures, not camera proof."""
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
PRIOR = BASE / 'stage138-USB-stop-dispatch-and-Mac-ownership'
PRIOR_SHA = 'c387c72cb1ed59ab08da9ad3287ac6e24b290221166b12198475a2b35c20a297'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def put(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    assert sha256((HELPER / 'final-receipt.json').read_bytes()).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin = next(x for x in json.loads((HELPER / 'final-receipt.json').read_text())['files']
               if x['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('fixed_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    count = helper.check_previous()
    assert count == 33
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    bridge = json.loads((HERE / 'callback-bridge-review.json').read_text())
    guest = json.loads((HERE / 'run-queue-return/results.json').read_text())
    contract = json.loads((HERE / 'first-service-trial-contract.json').read_text())
    assert bridge['status'] == 'PASS_STATIC_FX3_STOP_CALLBACK_BRIDGE_WITH_QUEUE_STATUS_GAP_NOT_LIVE_EXIT'
    assert len(bridge['original_functions']) == 18 and len(bridge['local_original_spans']) == 3
    assert len(bridge['checked_PLT_calls']) == 13
    assert guest['status'] == 'PASS_ORIGINAL_QUEUE_RETURN_COUNTEREXAMPLES_IN_DECLARED_GUEST_FIXTURES_NOT_DEVICE_EXIT'
    assert guest['case_count'] == 8 and guest['original_function_entries'] == 15
    assert guest['guest_original_AArch64_executed'] and not guest['Sony_native_host_or_camera_code_driver_or_module_execution']
    assert (HERE / 'run_queue_return.py').read_bytes() == (HERE / 'run-queue-return/executed-source.py').read_bytes()
    assert helper.digest(HERE / 'run_queue_return.py') == guest['execution_source_sha256']
    assert helper.digest(HERE / 'audit_callback_bridge.py') == guest['helper_source_sha256']
    cases = {x['fixture']['id']: x for x in guest['cases']}
    for name in ('full_but_request_returns0', 'wrap_full_but_request_returns0'):
        assert cases[name]['original_request_return'] == 0 and not cases[name]['ring_copy_observed']
    assert cases['unlock_failure_after_enqueue']['original_request_return'] == 5
    assert cases['unlock_failure_after_enqueue']['ring_copy_observed']
    assert cases['signal_failure_after_enqueue']['original_request_return'] == 0
    assert cases['signal_failure_after_enqueue']['synthetic_external_call_returns']['signal'] == 22
    assert not contract['future_pilot_acceptance_is_not_the_whole_goal']['live_release']
    assert not contract['current_authority']['service_capture_authentication_or_stop']
    assert not contract['current_authority']['driver_detach_or_reattach']
    assert contract['intended_later_scope_for_separate_concrete_review']['maximum_initial_MSC_authentication_sequences'] == 1
    assert contract['intended_later_scope_for_separate_concrete_review']['maximum_post_switch_service_authentication_sequences'] == 1
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Original service callback bridge and bounded AArch64 guest queue-return counterexamples; no camera operations'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段139核对18完整原函数/3原片段/13调用，接通原gadget事件3至Senser2/内部5及stop，原登记表与两次80B复制已对应。',
        'Unicorn中8声明场景/15原函数进入，原request与queue直接接通；外部锁/条件变量为返回值桩，非真实线程或相机。',
        '原函数反例：队列满仍返回0；排队后unlock失败返回5；signal失败仍可返回0。不能凭返回值充消费/完成或盲目重试。',
        '新增不可执行首次会话约束：最多一次MSC认证和一次重枚举后认证，异常清理覆盖首个传输，超时未知，不宣称零写入。',
        '没有设备/驱动/原生Sony执行；16项要求、全部授权/用户约束、旧准备字段与75/117原型保持，实机编码及恢复仍缺。'])
    key = 'stage139_service_callback_bridge_and_queue_return'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'callback_bridge': REL + '/callback-bridge-review.json',
        'guest_counterexamples': REL + '/run-queue-return/results.json',
        'first_service_contract': REL + '/first-service-trial-contract.json',
        'static_original_functions': 18, 'local_original_spans': 3,
        'bounded_original_guest_cases': 8, 'original_guest_function_entries': 15,
        'request_zero_not_queue_admission_or_completion_proof': True,
        'request_error_not_non_execution_proof': True,
        'new_native_host_camera_or_driver_operation': False,
        'live_exit_or_independent_recovery_proven': False, 'authorization_unchanged': True}
    new['prepared_first_device_trial']['service_callback_bridge_review'] = REL + '/callback-bridge-review.json'
    new['prepared_first_device_trial']['queue_return_counterexamples'] = REL + '/run-queue-return/results.json'
    new['prepared_first_device_trial']['first_service_session_contract'] = REL + '/first-service-trial-contract.json'
    new['prepared_first_device_trial']['first_service_controller_implemented_and_released'] = False
    new['next_safe_offline_actions'].append(
        '阶段139后按首次会话约束实现离线会话控制器和明确Mac传输边界：记录进入意图/实际发送/未知状态，异常覆盖两次认证和重枚举；不得将request0充排队/消费/退出，不在错误或超时后自动重发。先做故障注入/单机选择/驱动配对和期限审查，再形成具体实机授权方案；原16项完整备份/恢复/MAIN实录目标不缩减。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('prepared_first_device_trial', 'latest_stage_evidence'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3退出回调与队列返回反例](<' + REL + '/README.md>)：回调静态接通，8组原指令guest反例说明返回0未必排队、报错也可能已排队；首次会话约束已备，实机/刷写未放行。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent heads changed; CAS refused'
    assert helper.pins(old) == fixed
    for target, data, name in [(canonical, encoded, '.goal-write.tmp'), (index, index_after, '.index-write.tmp')]:
        temporary = HERE / name
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    helper.check_previous()
    completed = {'status': 'PASS_CALLBACK_BRIDGE_AND_GUEST_QUEUE_COUNTEREXAMPLES_NOT_LIVE_RELEASE',
        'created_utc': now, 'previous_manifest_members_verified': count,
        'static_original_functions': 18, 'local_original_spans': 3, 'checked_PLT_calls': 13,
        'bounded_guest_cases': 8, 'original_guest_function_entries': 15,
        'guest_original_execution_not_native_host_or_camera': True,
        'new_device_or_driver_operations': 0,
        'all16_requirements_authorization_and_user_constraints_unchanged': True,
        'old_prepared_trial_and_source_evidence_preserved': True,
        'stage75_backend_and_stage117_frontend_pins': fixed, 'canonical_equals_after': True,
        'same_agent_review_not_real_camera_acceptance': True,
        'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {
        'schema': 'fx3-stage139-callback-queue-return/1', 'created_utc': now,
        'volume_uuid': helper.UUID, 'files': files, 'member_count': len(files),
        'previous_manifest_sha256': PRIOR_SHA, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
                            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'operations': completed})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
                      'canonical_sha256': helper.digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
