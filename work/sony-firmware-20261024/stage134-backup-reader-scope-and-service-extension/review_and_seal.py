#!/usr/bin/env python3
"""Seal static findings and append progress without device or native firmware execution."""
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
PRIOR = BASE / 'stage133-FX5-source-availability-and-portability'
PRIOR_SHA = '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
REL = HERE.relative_to(ROOT).as_posix()


def put(name, data):
    with (HERE / name).open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def main():
    previous_raw = (PRIOR / 'final-receipt.json').read_bytes()
    assert sha256(previous_raw).hexdigest() == PRIOR_SHA
    previous = json.loads(previous_raw)
    helper_path = PRIOR / 'review_and_seal.py'
    pin = next(p for p in previous['files'] if p['path'] == helper_path.relative_to(ROOT).as_posix())
    assert sha256(helper_path.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('prior_local_sealer', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    count = helper.check_previous()
    assert count == 182 and not (HERE / 'final-receipt.json').exists()
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before = (HERE / 'goal-status-before.json').read_bytes()
    index_before = (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    review = json.loads((HERE / 'reader-scope-review.json').read_text())
    wrappers = json.loads((HERE / 'deviceio-and-upstream-review.json').read_text())
    assert review['status'] == 'PASS_STATIC_LEGACY_AND_HIGH_CAPACITY_READ_SCOPE_NOT_DEVICE_BACKUP_RELEASE'
    assert len(review['functions']) + len(review['core_functions']) == 10
    assert len(review['checked_PLT_calls']) == 21 and len(wrappers['core_functions']) == 2
    assert wrappers['open_flags_forwarded_unchanged'] and not wrappers['device_code_IO_or_Sony_execution']
    preserved131 = review['pending131_adopted_scope']['preserved_files']
    for item in preserved131:
        path = ROOT / item['path']
        assert path.stat().st_size == item['bytes'] and helper.digest(path) == item['sha256']
    upstream = json.loads((HERE / 'upstream-read-interface-review.json').read_text())
    for item in upstream['records']:
        path = HERE / item['path']
        assert path.stat().st_size == item['bytes'] and helper.digest(path) == item['sha256']
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Offline original legacy/high-capacity/hash read scope and conditional service-history write review; no device operation'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段134静态读取10个原函数、21处PLT，并补2个DeviceIo包装器；旧GET、hash、高容量包装均不构成受限系统原件备份。',
        '旧GETkind1为/mnt前缀；高容量是DMM会话/传输包装，不能以主机分片或上限替代设备整文件分配边界。',
        'Regist_HaspId条件分支准备/setting/.hasp写入88B及sync，DeviceIo向libc转交写入flags；未证明每次认证必经或实机实际写入。',
        '131的10组已有Parse前缀证据校验后限定引用，不复跑、不把三个表推广为全部动态服务不可用；131原样未封存。',
        '首次静态核对地址标注9190应为918c，失败源及原因保留；更正后通过，不是Sony代码或设备缺陷结论。',
        '仅Mac离线及固定上游源码下载；16项要求/授权/用户约束和原前后端保持，主录/同机备份恢复实机证据仍缺。'])
    key = 'stage134_backup_reader_scope_and_service_registration'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'reader_scope': REL + '/reader-scope-review.json',
        'DeviceIo_and_upstream': REL + '/deviceio-and-upstream-review.json',
        'static_functions_reviewed': 12, 'native_cases_replayed': 0,
        'pending131_preserved_not_full_service_absence_proof': True,
        'conditional_hasp_history_write_discovered': True,
        'actual_authentication_history_write_or_device_read_proven': False,
        'healthy_backup_or_flash_ready': False, 'authorization_unchanged': True}
    new['next_safe_offline_actions'].append(
        '阶段134后优先追实际认证到registHaspId的调用链、/setting挂载与.hasp存在/记录分支，形成含条件历史更新的具体授权说明；再定位真正适用的系统读取接收器/插件和长度/退出边界。高容量、MD5、主机分片和/mnt路径不能充系统备份；131旧例不重复跑且不外推全部动态路由。')
    new['prepared_first_device_trial']['backup_reader_scope_review'] = REL + '/README.md'
    new['prepared_first_device_trial']['service_history_side_effect_review'] = REL + '/deviceio-and-upstream-review.json'
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'next_safe_offline_actions', 'prepared_first_device_trial'}
    for k in old:
        if k not in allowed:
            assert new[k] == old[k], k
    for k, value in old['latest_stage_evidence'].items():
        assert new['latest_stage_evidence'][k] == value
    for k, value in old['prepared_first_device_trial'].items():
        assert new['prepared_first_device_trial'][k] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3备份读取范围与登记副作用](<' + REL + '/README.md>)：旧GET/hash/高容量会话未形成受限系统备份；条件.hasp历史写入已定位，认证不能统称零写入，实机/刷写未放行。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    helper.volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent progress change; CAS refused'
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
    completed = {'status': 'PASS_STATIC_BACKUP_SCOPE_AND_CONDITIONAL_HASP_WRITE_REVIEW_NOT_DEVICE_RELEASE',
                 'created_utc': now, 'previous_members_verified': count, 'original_functions_reviewed': 12,
                 'named_PLT_targets_in_main_review': 21, 'Sony_instructions_or_camera_operations_executed': 0,
                 'previous_native_cases_replayed': 0, 'stage131_originals_preserved': True,
                 'initial_address_typo_failure_preserved': True, 'all16_requirements_unchanged': True,
                 'authorization_user_constraint_and_old_prepared_trial_fields_unchanged': True,
                 'stage75_backend_and_stage117_frontend_pins': fixed,
                 'canonical_equals_after': True, 'same_agent_review_not_real_device_validation': True,
                 'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage134-reader-scope/1', 'created_utc': now,
        'files': files, 'member_count': len(files), 'previous_manifest_sha256': PRIOR_SHA,
        'volume_uuid': helper.UUID, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
                             'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'operations': completed})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'),
                      'members': len(files), 'canonical_sha256': helper.digest(canonical),
                      'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
