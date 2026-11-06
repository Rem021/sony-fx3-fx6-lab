#!/usr/bin/env python3
"""Seal static exit evidence; preserve all camera acceptance and authority gates."""
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
PRIOR = BASE / 'stage136-authentication-and-system-read-admission'
PRIOR_SHA = '0d75ee521094f453bd58c78ab28f5541998cd104c454342243c93053d73aa5c2'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


def put(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    assert not (HERE / 'final-receipt.json').exists()
    assert sha256((HELPER / 'final-receipt.json').read_bytes()).hexdigest() == '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
    pin = next(p for p in json.loads((HELPER / 'final-receipt.json').read_text())['files']
               if p['path'] == (HELPER / 'review_and_seal.py').relative_to(ROOT).as_posix())
    assert sha256((HELPER / 'review_and_seal.py').read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('fixed_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    count = helper.check_previous()
    assert count == 11
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before = (HERE / 'goal-status-before.json').read_bytes()
    index_before = (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    evidence = json.loads((HERE / 'service-exit-review.json').read_text())
    assert evidence['status'] == 'PASS_STATIC_SERVICE_EXIT_LIFETIME_NOT_DEVICE_RETURN_OR_RECOVERY'
    assert len(evidence['functions']) == 18 and len(evidence['checked_PLT_calls']) == 32
    assert len(evidence['GOT_bindings']) == 5 and len(evidence['jump_table']['event_targets']) == 7
    assert evidence['host_source_review']['stop_swallows_GenericUsbException']
    assert evidence['host_source_review']['authentication_failure_outside_local_stop_finally']
    for item in evidence['pinned_inputs']:
        path = ROOT / item['path']
        assert helper.record(path) == item
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Offline service exit/cancel/join, callback status and host cleanup-scope review; no camera operation'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段137核对18个完整原函数、32调用、7事件跳表和5GOT；无原代码执行或新设备枚举。',
        '正常event6/run_workers先join认证线程再启命令worker，但忽略join状态；补足认证应答与尾部完成的条件边界。',
        'cancel仅请求，两线程join/清理结果不充成功；stop回调即使错误也清状态，spin等待无截止时间。',
        '固定PMCA两源仅AST解析：stop吞GenericUsbException，认证在本地finally之外，不能以Done充恢复。',
        '现有仅Mac/Windows且Windows延后；BootROM桥条件和FX3适配未具备，既有Fastboot空枚举不重复。',
        '16项要求、完整授权/用户约束、旧准备字段及75/117原型保持；实机备份/恢复/主录仍未验收。'])
    key = 'stage137_service_exit_and_host_cleanup'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'static_exit_review': REL + '/service-exit-review.json',
        'static_original_functions': 18, 'checked_PLT_calls': 32,
        'normal_auth_join_is_conditional_not_host_proof': True,
        'host_stop_error_and_authentication_cleanup_gaps_identified': True,
        'new_device_or_Sony_code_execution': False, 'actual_safe_return_or_recovery_proven': False,
        'authorization_unchanged': True}
    new['prepared_first_device_trial']['service_exit_and_host_cleanup_review'] = REL + '/service-exit-review.json'
    new['prepared_first_device_trial']['service_exit_or_recovery_validated'] = False
    new['next_safe_offline_actions'].append(
        '阶段137后补Mac USB驱动归属/释放及原vendor-stop到USB事件的完整分派、超时和正常返回可观测凭据。首次活动方案需覆盖认证前后的异常清理并保留未知状态，不能用吞异常/固定等待/回调状态0证明退出，不自动重试/重启/刷写。认证条件历史写入仍在，Fastboot识别许可不扩大成服务认证；独立FX3 BootROM适配与硬件条件未具备。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('latest_stage_evidence', 'prepared_first_device_trial'):
        for key, value in old[section].items():
            assert new[section][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3服务退出与主机清理核查](<' + REL + '/README.md>)：原正常路径先join认证再启动命令线程；取消/回调/无超时等待及PMCA清理缺口已定位，实际退出与独立恢复仍未验。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent heads changed; refusing CAS'
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
    completed = {
        'status': 'PASS_STATIC_SERVICE_EXIT_REVIEW_NOT_DEVICE_RECOVERY', 'created_utc': now,
        'previous_manifest_members_verified': count, 'static_original_functions': 18,
        'checked_PLT_calls': 32, 'host_sources_AST_only': 2,
        'all16_requirements_authorization_and_user_constraints_unchanged': True,
        'old_prepared_trial_and_source_evidence_preserved': True,
        'stage75_backend_and_stage117_frontend_pins': fixed,
        'new_device_operations_or_Sony_execution': 0, 'canonical_equals_after': True,
        'same_agent_static_review_not_real_camera_acceptance': True,
        'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {
        'schema': 'fx3-stage137-service-exit-review/1', 'created_utc': now,
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
