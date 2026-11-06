#!/usr/bin/env python3
"""Seal the offline authentication/read-admission review, preserving device gates."""
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
PRIOR = BASE / 'stage135-Fastboot-entry-discovery'
PRIOR_SHA = 'af16faee7623b7d3e729502911664aa6826a04bb067e04a09194b46791197da5'
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
    spec = importlib.util.spec_from_file_location('local_sealer', HELPER / 'review_and_seal.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    count = helper.check_previous()
    assert count == 79
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    auth = json.loads((HERE / 'authentication-publication-review.json').read_text())
    reader = json.loads((HERE / 'system-read-admission-review.json').read_text())
    assert auth['status'] == 'PASS_STATIC_AUTH_CALLBACK_PUBLICATION_AND_HISTORY_ORDER_NOT_DEVICE_AUTHENTICATION'
    assert reader['status'] == 'PASS_STATIC_DIRECT_POSIX_BRANCH_AND_FIXED_PATH_DRAFT_NOT_READY_TO_SEND'
    assert len(auth['functions']) == 12 and len(reader['functions']) == 7
    assert len(reader['fixed_read_drafts']) == 2 and not reader['actual_body_path_resolution_mounts_symlinks_or_file_sizes_verified']
    assert reader['source_Main_appFw_so_bytes'] == 79015712
    assert auth['onComplete_table_mapping'] == {'1': 'pFunc_level_C', '2': 'pFunc_level_B', '3': 'pFunc_level_A', 'other': None}
    assert auth['callback_invoked_for_other_null_table_levels_in_this_function']
    for draft in reader['fixed_read_drafts']:
        path = BASE / 'stage2/extraction/files/nflasha15/lib' / Path(draft['fixed_target']).name
        assert path.stat().st_size == draft['source_reference_bytes'] and helper.digest(path) == draft['source_reference_sha256']
        assert not draft['live_send_implemented_or_permitted']
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Offline authentication final-reply/history/publication ordering plus fixed system-read admission drafts; no device operations'
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段136静态接通NinThread虚调用与Worker vtable：最终认证应答早于.hasp登记、命令表发布及后续.etools/模式文件分支。',
        'onComplete等级1/2/3选择C/B/A，其他清pFunc仍可回调；完成回调不充可用命令表或所有写者退出。',
        '新增.etools既存日志4096B读取/编码/写回边界；官方fstab表明/tmp位于可写nflasha10，不按目录名认作RAM。',
        'CFileAccess非/mnt路径可走POSIX分支，固定两个库文件的惰性请求草稿已成；真实命名空间/分配/传输/退出未验，不可发送。',
        'MAIN appFw.so原件79015712B仍需完整同机备份/恢复，不以两个小库或静态完成缩减目标。',
        '全程19原函数静态解析，无新枚举、认证/机身文件或Sony代码执行；16项要求、135授权/用户约束和75/117原型保持。'])
    key = 'stage136_authentication_and_system_read_admission'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'authentication_publication': REL + '/authentication-publication-review.json',
        'system_read_admission': REL + '/system-read-admission-review.json',
        'static_original_functions': 19, 'new_native_execution_or_device_tests': 0,
        'fixed_inert_library_read_drafts': 2, 'drafts_ready_to_send': False,
        'authentication_final_reply_not_writer_completion': True,
        'tmp_configured_flash_backed_not_assumed_RAM': True,
        'actual_backup_or_recovery_proven': False, 'authorization_unchanged': True}
    new['prepared_first_device_trial']['service_authentication_effects_review'] = REL + '/authentication-publication-review.json'
    new['prepared_first_device_trial']['fixed_system_read_draft'] = REL + '/system-read-admission-review.json'
    new['prepared_first_device_trial']['service_authentication_or_file_read_ready'] = False
    new['next_safe_offline_actions'].append(
        '阶段136后优先核对服务退出/取消join与全部历史/模式写入结束，再核对固定系统读候选的进程根/挂载/符号链接、设备DMM/传输及超时回收。最终认证应答/完成回调不作写者完成，/tmp不作RAM。原79MB MAIN应用完整备份/恢复仍保留；两个惰性库帧草稿不发送，Fastboot识别许可不扩成服务认证或文件读取。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for key, value in old['prepared_first_device_trial'].items():
        assert new['prepared_first_device_trial'][key] == value
    for key, value in old['latest_stage_evidence'].items():
        assert new['latest_stage_evidence'][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3认证完成与同机读取准备](<' + REL + '/README.md>)：认证最终应答早于条件历史/日志结束；/tmp配置在闪存，两个固定库读取仅惰性草稿，退出/传输及实机备份未放行。'
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
    completed = {'status': 'PASS_STATIC_AUTHENTICATION_AND_SYSTEM_READ_ADMISSION_NOT_ACTIVE_RELEASE',
        'created_utc': now, 'previous_manifest_members_verified': count, 'static_original_functions': 19,
        'worker_vtable_slots_verified': 7, 'new_Sony_execution_or_device_operations': 0,
        'fixed_inert_drafts': 2, 'live_read_or_auth_ready': False,
        'all16_requirements_authorization_and_user_constraints_unchanged': True,
        'old_prepared_trial_and_source_evidence_preserved': True,
        'stage75_backend_and_stage117_frontend_pins': fixed,
        'canonical_equals_after': True, 'same_agent_review_not_live_authentication_or_recovery': True,
        'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage136-auth-and-read-admission/1',
        'created_utc': now, 'volume_uuid': helper.UUID, 'files': files, 'member_count': len(files),
        'previous_manifest_sha256': PRIOR_SHA, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_project_heads_not_manifest_members': True,
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(encoded).hexdigest(),
                            'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'operations': completed})
    print(json.dumps({'manifest_sha256': helper.digest(HERE / 'final-receipt.json'), 'members': len(files),
                      'canonical_sha256': helper.digest(canonical), 'goal_complete': False,
                      'persistent_write_release': False}))


if __name__ == '__main__':
    main()
