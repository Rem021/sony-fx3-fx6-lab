#!/usr/bin/env python3
"""Seal compiled-but-unloaded native owner candidate; keep every live gate closed."""
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
PRIOR = BASE / 'stage152-resource-callback-and-thread-failure'
PRIOR_SHA = '6795ddfd08f79151fdfcc500a91531573cf331dba7eb697f7ca3a4f54eb8141e'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'


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
    spec = importlib.util.spec_from_file_location('fixed_native_owner_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    previous_count = helper.check_previous()
    assert previous_count == 23
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-rebased-before.md').read_bytes()
    rebase = json.loads((HERE / 'index-rebase-review.json').read_text())
    assert sha256(index_before).hexdigest() == rebase['rebased_before_sha256']
    assert sha256((HERE / 'readme-before.md').read_bytes()).hexdigest() == rebase['original_before_sha256']
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    assert old['authorization']['Mac_descriptor_probe_authorization_consumed']
    assert not old['authorization']['Mac_active_USB_descriptor_read_authorized']
    assert not old['authorization']['driver_change'] and not old['authorization']['service_auth_mode_or_stop']
    assert not old['prepared_first_device_trial']['Mac_descriptor_probe_released']
    fixed = helper.pins(old)
    run = HERE / 'run-owner-fixtures'
    result = json.loads((run / 'results.json').read_text())
    assert result['case_count'] == len(result['cases']) == 33
    assert result['actual_USB_or_device_operations'] == 0 and not result['actual_IOKit_candidate_loaded']
    assert not result['real_process_supervision_one_shot_entry_or_driver_return_proven']
    assert result['fixture_dso_sha256'] == helper.digest(run / 'owner-fixture.dylib')
    assert 'IOKit' not in result['fixture_dependencies'] and 'libusb' not in result['fixture_dependencies']
    for name in ['owner_trial.h', 'owner_core.c', 'owner_fixture.c', 'owner_binding.py', 'test_owner_core.py']:
        assert (HERE / name).read_bytes() == (run / name).read_bytes()
    cases = {c['name']: c for c in result['cases']}
    assert cases['native_work_boundary_failure_1']['raw_status'] == 2
    assert cases['MSC_driver_remains_after_capture']['calls']['7'] == 0
    assert cases['late_capture_return_cleanup_still_runs']['calls']['10'] == 1
    assert cases['late_capture_return_cleanup_still_runs']['calls']['11'] == 1
    assert cases['different_body_after_return']['raw_status'] == 2
    for name in ['live_gate_current', 'live_gate_future_flags_without_supervisor']:
        assert cases[name]['rejected_before_native_symbol_lookup']
    build = json.loads((HERE / 'native-build-receipt.json').read_text())
    assert not build['actual_native_candidate_loaded_or_run'] and build['new_device_operations'] == 0
    assert build['native_dylib_sha256'] == helper.digest(HERE / 'owner-iokit.dylib')
    assert build['exported_symbols'] == ['_fx3_owner_run']
    assert (HERE / 'build_native.py').read_bytes() == (HERE / 'build-executed.py').read_bytes()
    for m in build['sources']:
        assert (HERE / m['path']).stat().st_size == m['bytes'] and helper.digest(HERE / m['path']) == m['sha256']
    for m in build['SDK_header_audit']:
        path = Path(m['path'])
        assert helper.digest(path) == m['sha256']
        lines = path.read_bytes().decode(m['inspection_encoding']).splitlines()
        for match in m['matches']:
            assert lines[match['line'] - 1].strip() == match['text']
    seize = json.loads((HERE / 'sdk-seize-note.json').read_text())
    assert helper.digest(Path(seize['path'])) == seize['header_sha256']
    assert not seize['actual_OS_behavior_verified']
    plan = json.loads((HERE / 'candidate-plan.json').read_text())
    assert plan['native_candidate_sha256'] == build['native_dylib_sha256']
    assert not plan['Mac_owner_trial_released'] and not plan['current_authorization_expanded']
    now = datetime.now(timezone.utc).isoformat()
    put('completed-local-review.json', {
        'created_utc': now, 'native_candidate_compiled_and_inspected_not_loaded': True,
        'native_core_fixture_checks': 33, 'fixture_dependencies_no_IOKit_or_USB': True,
        'failed_partial_baseline_not_used_as_identity_proof': True,
        'MSC_driver_remains_blocks_claim': True,
        'permanent_live_rejection_until_separate_supervisor_and_release': True,
        'SDK_Seize_may_fail_and_capture_excludes_MSC_driver_distinguished': True,
        'underlying_IOKit_operations_process_lifetime_actual_driver_return_or_camera_acceptance_verified': False,
        'same_agent_local_review_only': True, 'new_device_operations': 0})
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Native IOKit owner candidate compiled but never loaded; shared C core33 fixture checks; live entry remains permanently unreleased pending supervisor'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段153重验152全部23成员；上一轮原资源/线程失败和Mac接管源码审计是进展。本轮将约束落实为实际IOKit C候选与共用流程核心，真实库只编译/检查，没有加载。',
        '自写无IOKit/libusb依赖DSO执行共用C核心，33项检查含边界错误、挂载/连接变化、驱动仍在、清理失败、时钟及真实入口拒绝；修正了失败初始snapshot部分字段被当作比较基线的问题并保留旧构建。',
        'Apple SDK补充Seize可被已有客户端拒绝、capture不终止MSC接口驱动；候选显式Seize/capture后再核对驱动，否则拒绝claim；归还使用SDK release选项，不套称为libusb零选项路径。',
        '候选没有索尼协议或USB载荷接口，也未与147收发层接通。同步系统调用仍缺工作进程/在途/单次入口监管，真实绑定即使授权标志改true也拒绝；不能用编译或33项夹具替代实际IOKit/驱动归还。',
        '无新增设备、Mac USB库初始化、Windows/UU、卸载卷、sudo或驱动变更；一次描述符权限保持消耗，16项主录/完整恢复与独立救援要求和全部旧准备值保留。'])
    new['latest_stage_evidence']['stage153_native_Mac_owner_candidate'] = {
        'readme': REL + '/README.md', 'plan': REL + '/candidate-plan.json',
        'build': REL + '/native-build-receipt.json', 'fixture_checks': REL + '/run-owner-fixtures/results.json',
        'review': REL + '/completed-local-review.json', 'native_candidate_sha256': build['native_dylib_sha256'],
        'native_candidate_compiled_not_loaded': True, 'fixture_cases': 33,
        'process_supervisor_or_actual_driver_return_proven': False, 'live_released': False, 'new_device_operations': 0}
    new['prepared_first_device_trial']['Mac_owner_trial_native_candidate'] = {
        'build': REL + '/native-build-receipt.json', 'plan': REL + '/candidate-plan.json',
        'candidate_sha256': build['native_dylib_sha256'], 'state': 'COMPILED_NOT_LOADED_OR_RELEASED'}
    new['prepared_first_device_trial']['Mac_owner_trial_released'] = False
    new['next_safe_offline_actions'].append('153原生IOKit候选已编译，33项C核心夹具通过但真实入口仍永久拒绝。后续实现隔离工作进程、共享在途阶段、单次凭据、停止/迟到/进程消失监管；不得超时杀进程后充归还成功。复核全部卷/自动挂载竞态、显式Seize与capture的MSC例外、release选项后实际驱动判据，再形成新授权的一次性物理方案。未取得HEVC补丁/原片，不能跳过MAIN和同机完整恢复/独立救援。')
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
    entry = '- [2026-10-28 FX3 Mac原生接管候选](<' + REL + '/README.md>)：IOKit库编译未加载，共用C流程33项夹具；SDK补充MSC capture例外，真实入口因缺监管仍拒绝，无新增设备操作。'
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
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    helper.check_previous()
    put('completed-evidence-review.json', {
        'status': 'PASS_COMPILED_UNLOADED_NATIVE_OWNER_AND33_FIXTURES_NOT_REAL_DRIVER_OR_CAMERA_ACCEPTANCE',
        'created_utc': now, 'previous_manifest_members_verified': previous_count, 'fixture_checks': 33,
        'all16_requirements_authorization_user_constraints_and_old_prepared_values_preserved': True,
        'fixed_guest_backend_frontend_pins': fixed, 'goal_complete': False,
        'persistent_write_release': False, 'Mac_owner_trial_released': False, 'new_device_operations': 0})
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage153-native-owner-candidate/1', 'created_utc': now,
        'volume_uuid': helper.UUID, 'files': files, 'member_count': len(files), 'previous_manifest_sha256': PRIOR_SHA,
        'allowed_goal_keys_changed': sorted(allowed), 'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()}})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
        'canonical_sha256': helper.digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
