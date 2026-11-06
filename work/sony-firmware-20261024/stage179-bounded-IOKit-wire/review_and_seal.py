"""Seal offline fixture evidence, preserving all device authority and prior records."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PREVIOUS = BASE/'stage178-integrated-user-receipt-controller'
PREVIOUS_SHA = '97750af585c57dd51a1f74201529b145906a003521316318a1342ef373944036'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def volume():
    data = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert data['VolumeUUID'] == UUID


def put(name, value):
    with (HERE/name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    volume()
    assert not (HERE/'final-receipt.json').exists()
    previous = PREVIOUS/'final-receipt.json'
    assert digest(previous) == PREVIOUS_SHA
    prior = json.loads(previous.read_text())
    for rec in prior['files']:
        path = ROOT/rec['path']
        assert path.stat().st_size == rec['bytes'] and digest(path) == rec['sha256'], rec['path']
    assert len(prior['files']) == 252
    before = (HERE/'goal-status-before.json').read_bytes()
    canonical, index = BASE/'GOAL_STATUS.json', ROOT/'README.md'
    assert canonical.read_bytes() == before == (PREVIOUS/'goal-status-after.json').read_bytes()
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    assert not old['authorization']['service_auth_mode_or_stop']
    source = json.loads((HERE/'source-derivation.json').read_text())
    assert digest(ROOT/source['old_policy']) == source['old_policy_sha256']
    for rec in source['SDK_headers']:
        assert digest(Path(rec['path'])) == rec['sha256']
    build = json.loads((HERE/'build-receipt.json').read_text())
    for rec in build['sources']:
        assert digest(HERE/rec['path']) == rec['sha256']
    for key in ('native_object', 'fixture'):
        rec = build[key]
        assert '-Werror' in rec['argv'] and digest(Path(rec['argv'][-1])) == rec['sha256']
    assert build['native_object_linked_or_loaded'] is False and build['new_root_or_USB_operations'] == 0
    deps = build['fixture']['dependencies'].splitlines()[2:]
    assert len(deps) == 1 and '/usr/lib/libSystem.B.dylib' in deps[0]
    result = json.loads((HERE/'run-tests-v2/results.json').read_text())
    assert result['status'] == 'PASS_SDK_TYPED_IOKIT_FAKE_VTABLE_AND_INERT_CONTROLLER_ONLY'
    assert result['case_count'] == len(result['cases']) == 55
    assert result['flow_count'] == len(result['inert_flows']) == 2
    assert result['real_USB_or_camera_operations'] == result['root_admin_or_privacy_changes'] == 0
    for name, want in result['sources'].items():
        assert digest(HERE/name) == want == digest(HERE/'run-tests-v2'/name)
    for flow in result['inert_flows']:
        assert flow['fixture_calls'] == [3, 14, 14]
        assert flow['all_body_mode_driver_and_physical_evidence_synthetic']
        assert flow['controller_report']['phase'] == 'FLOW_FINISHED'
        assert not flow['controller_report']['evidence']['worker_completion']
        for action in flow['actions']:
            assert not action['device_effect_or_queue_worker_completion_proven']
            for call in action['calls']:
                if call['operation'] == 'BULK_OUT':
                    assert call['actual_count_known'] is False and call['transferred'] is None
    first = json.loads((HERE/'run-tests/results.json').read_text())
    assert first['status'] == 'FAIL' and first['case_count'] == 55 and first['flow_count'] == 0
    now = datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json', {
        'created_utc': now, 'stage178_members_verified': 252,
        'current_fixture_cases': 55, 'inert_controller_flows': 2,
        'native_object_compiled_only': True,
        'executed_DSO_only_libSystem': True,
        'SDK_typed_vtable_calls_exercised_in_same_process_fixture': True,
        'real_blocked_fake_callback_no_automatic_close_retry_or_reset': True,
        'foreign_PID_rejection_test_is_simulated_not_real_IPC': True,
        'write_request_return_does_not_invent_actual_byte_count': True,
        'missing_old_build_receipt_and_first_fixture_failure_preserved': True,
        'native_owner_linkage_IPC_identity_pipe_mapping_and_global_budget_not_implemented': True,
        'native_SERVICE_profile_denied_outside_fixture': True,
        'authentication_exit_backup_restore_rescue_and_target_recording_not_proven': True,
        'new_root_USB_camera_Sony_auth_or_persistent_write_operations': 0,
        'old05_formal_UNKNOWN_interface_return_and_screen_receipts_unchanged': True,
        'same_agent_local_review_not_device_acceptance': True,
    })
    new = deepcopy(old)
    new['updated_utc'], new['latest_stage'] = now, HERE.name
    new['research_activity'] = ('Implemented bounded same-process IOKit650 adapter and typed own-fixture controller bridge; '
                                '55 current checks and two inert flows passed. Real owner linkage/IPC and global native '
                                'session authority remain open; no new camera operation. The old native goal-manager '
                                'blocked state describes an earlier manual-ejection wait, not a current execution receipt.')
    new['progress_audit']['previous_goal_turn_classification'] = old['progress_audit']['classification']
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段179复核178封存252成员、旧147策略及固定本机SDK头；重启后保留未归档编译产物，不重复05真机试验。',
        '同进程IOKit650 C有界收发及注册夹具Python桥已实现；原生仅编译对象，自写SDK形状vtable实际执行55项及两条惰性控制器流程，每流程3control/14OUT/14IN。',
        '正值超时、pipeRef与端点地址分离、IN恰好516、原始IOReturn、OUT实际长度未知、真实阻塞假回调及生命周期保护均有夹具证据；不充相机或跨进程IPC实测。',
        '自身install-name误报依赖及夹具浮点纳秒差异的旧产物/失败记录保留，当前源码与成功执行快照、构建哈希一致。',
        '真实root拥有者尚未链接该适配，身份/实际管道映射/全局预算及IPC未落地；SERVICE形状只在夹具开放，live工厂仍拒绝。',
        '旧05正式UNKNOWN及接口归还和正常屏幕证据保留；未新增设备、管理员、Sony认证或写入，16要求/授权/限制/目标未缩减。',
    ])
    evidence = {
        'readme': REL+'/README.md', 'adapter': REL+'/iokit_wire.c', 'bridge': REL+'/iokit_fixture_api.py',
        'wire_policy': REL+'/iokit_wire.py', 'verification': REL+'/run-tests-v2/results.json',
        'review': REL+'/completed-local-review.json', 'build': REL+'/build-receipt.json',
        'own_fixture_cases': 55, 'inert_controller_flows': 2, 'real_USB_or_camera_operations': 0,
        'native_owner_integration_IPC_and_global_budget_ready': False,
        'actual_camera_authentication_exit_backup_restore_rescue_or_MAIN_recording_proven': False,
    }
    new['latest_stage_evidence']['stage179_bounded_IOKit650_adapter'] = evidence
    new['prepared_first_device_trial']['bounded_IOKit650_wire_candidate'] = REL+'/iokit_wire.c'
    new['prepared_first_device_trial']['bounded_IOKit650_wire_fixture_receipt'] = REL+'/run-tests-v2/results.json'
    new['prepared_first_device_trial']['bounded_IOKit650_wire_live_ready'] = False
    new['next_safe_offline_actions'].append(
        '179仅完成同进程IOKit适配和夹具控制器连接；继续把收发接入真正持有接口的原生进程，以身份/代次/单次请求和全局预算约束IPC。先用无USB进程夹具验证在途/父进程退出/归还顺序。不得跨进程传原始指针或复用05；认证条件写入、真实退出和完整备份恢复/独立救砖/目标主录仍未放行。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for section in ('latest_stage_evidence', 'prepared_first_device_trial'):
        for key, value in old[section].items():
            assert new[section][key] == value, (section, key)
    encoded = (json.dumps(new, ensure_ascii=False, indent=2)+'\n').encode()
    with (HERE/'goal-status-after.json').open('xb') as f:
        f.write(encoded)
    # Other project work has appended to README during this stage. Preserve its current bytes.
    index_before = index.read_bytes()
    with (HERE/'readme-rebased-before.md').open('xb') as f:
        f.write(index_before)
    entry = ('- [2026-10-29 FX3同进程IOKit有界收发适配](<'+REL+'/README.md>)：'
             '55项自写SDK夹具和两条控制器模拟流程通过；原生仅编译，真实拥有者IPC/服务/备份恢复仍未接通，无新增相机操作。')
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker+'\n'+entry+'\n', 1).encode()
    with (HERE/'readme-after.md').open('xb') as f:
        f.write(index_after)
    volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'concurrent heads changed; CAS refused'
    for path, data, temp_name in ((canonical, encoded, '.goal-final.tmp'), (index, index_after, '.index-final.tmp')):
        tmp = HERE/temp_name
        with tmp.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    files = []
    for path in sorted(HERE.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            files.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    put('final-receipt.json', {
        'schema': 'fx3-stage179-bounded-IOKit650-fixture/1', 'created_utc': now, 'volume_uuid': UUID,
        'previous_manifest_sha256': PREVIOUS_SHA, 'files': files, 'member_count': len(files),
        'mutable_heads_not_manifest_members': True, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
                             'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'new_root_USB_camera_or_Sony_operations': 0, 'goal_complete': False, 'persistent_write_release': False,
    })
    print(json.dumps({'manifest_sha256': digest(HERE/'final-receipt.json'), 'members': len(files),
                      'current_cases': 55, 'inert_flows': 2, 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
