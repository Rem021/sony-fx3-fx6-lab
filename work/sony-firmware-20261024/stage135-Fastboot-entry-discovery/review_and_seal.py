#!/usr/bin/env python3
"""Seal an explicitly requested Fastboot discovery, preserving all real-device gates."""
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
PRIOR = BASE / 'stage134-backup-reader-scope-and-service-extension'
PRIOR_SHA = '5ece0e5dea69b1c88e812ae42e46a07abf95316a2a6f02c34a5784b7ff6eec1d'
HELPER = BASE / 'stage133-FX5-source-availability-and-portability'
HELPER_MANIFEST_SHA = '564185c30566ef51501618ff825bd006bfb3771a41213a49fa92521d417cddf2'
REL = HERE.relative_to(ROOT).as_posix()


def put(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def interfaces(receipt):
    result = set()
    for candidate in receipt['FX3_cached_records']:
        for node in [candidate['device']] + candidate['descendants']:
            if 'bInterfaceClass' in node:
                result.add(tuple(node.get(k) for k in ('bInterfaceNumber', 'bInterfaceClass',
                                                      'bInterfaceSubClass', 'bInterfaceProtocol')))
    return sorted(result)


def main():
    assert not (HERE / 'final-receipt.json').exists()
    assert sha256((HELPER / 'final-receipt.json').read_bytes()).hexdigest() == HELPER_MANIFEST_SHA
    previous_helper = json.loads((HELPER / 'final-receipt.json').read_text())
    helper_path = HELPER / 'review_and_seal.py'
    pin = next(x for x in previous_helper['files'] if x['path'] == helper_path.relative_to(ROOT).as_posix())
    assert sha256(helper_path.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('local_seal_helper', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.HERE, helper.REL, helper.PRIOR, helper.PRIOR_SHA = HERE, REL, PRIOR, PRIOR_SHA
    helper.volume()
    previous_count = helper.check_previous()
    assert previous_count == 16
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    old = json.loads(before)
    assert len(old['requirements']) == 16 and not old['goal_complete'] and not old['persistent_write_release']
    fixed = helper.pins(old)
    caches = [json.loads((HERE / p).read_text()) for p in ('current-fastboot-cache-check.json',
              'post-enumeration/current-fastboot-cache-check.json')]
    for receipt in caches:
        assert receipt['FX3_unique_cached_roots'] == 1
        assert receipt['standard_fastboot_signature_node_count_all_vendors'] == 0
        assert interfaces(receipt) == [(0, 8, 6, 80)]
        assert not receipt['actual_fastboot_protocol_probe_or_mode_entry_executed']
    actual = json.loads((HERE / 'actual-fastboot-enumeration.json').read_text())
    assert actual['commands'] == ['fastboot --version', 'fastboot devices -l']
    assert actual['enumeration_exit_code'] == 0 and actual['listed_device_line_count'] == 0
    assert actual['enumeration_empty_stdout'] and actual['enumeration_stderr_empty']
    assert actual['per_process_network_denied']
    assert not actual['mode_entry_getvar_boot_download_flash_erase_OEM_or_unlock_commands_requested']
    assert not actual['Sony_code_or_A7IV_payload_loaded_or_executed']
    for filename in ('public-source-and-host-tool-downloads.json', 'selected-public-material-receipt.json'):
        for item in json.loads((HERE / filename).read_text())['records']:
            path = HERE / item['path']
            assert path.stat().st_size == item['bytes'] and helper.digest(path) == item['sha256']
    source = json.loads((HERE / 'Fastboot-entry-source-review.json').read_text())
    for item in source['additional_selected_sources'] + source['facts']:
        assert helper.digest(HERE / item['path']) == item['sha256']
    assert source['hardware_available_user_quote'] == '目前只有 Mac 和 Windows 电脑'
    assert not source['bridge_hardware_available'] and not source['source_or_payload_built_loaded_or_executed']
    auth = json.loads((HERE / 'authorization-change.json').read_text())
    assert auth['before'] == old['authorization']
    for key, value in old['authorization'].items():
        if key != 'scope':
            assert auth['after'][key] == value
    now = datetime.now(timezone.utc).isoformat()
    new = copy.deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = 'Explicitly requested standard Fastboot discovery: official host enumeration plus pre/post cached USB metadata and pinned A7IV entry-source review'
    new['authorization'] = auth['after']
    constraint = new['current_user_operational_constraint']
    constraint['current_scope'] = 'Mac offline preparation/cached USB metadata plus explicitly requested standard Fastboot identification; no implemented model-specific mode entry or service/flash operations'
    constraint['camera_authorization_expanded'] = True
    constraint['camera_authorization_expansion_scope'] = 'Standard Fastboot identification only; no broader service auth, driver, RAM module or firmware operation'
    constraint['latest_Fastboot_test_request_quote'] = auth['quote']
    constraint['latest_bridge_hardware_inventory_quote'] = source['hardware_available_user_quote']
    new['progress_audit']['classification'] = 'progress'
    new['progress_audit']['previous_goal_turn_classification'] = 'progress'
    new['progress_audit']['basis'].extend([
        '阶段135用户提出测试FX3 Fastboot；先后缓存显示1台054C:0DA1、接口08/06/50，标准ff/42/03全厂商节点0。',
        'Google官方Fastboot37.0.1隔离置于任务目录，实际--version及devices -l在禁止网络的进程内成功运行，枚举为空；不等于尝试进入失败或证明不能进入。',
        'A7IV固定源码表明Fastboot是串口ROM后加载的自制RAM载荷，USB前已进行CP/eMMC/USB初始化，不能当FX3自带模式或零副作用入口。',
        '用户确认目前只有Mac/Windows，没有桥接硬件；FX3电气/ROM触发/RAM及硬件初始化/退出尚未验证，未执行进入或外机载荷。',
        '仅按本次直接请求新增标准Fastboot识别范围；原服务/驱动/模块/刷写禁止项与16项验收状态保持，Windows延后。'])
    key = 'stage135_requested_Fastboot_discovery'
    assert key not in new['latest_stage_evidence']
    new['latest_stage_evidence'][key] = {
        'readme': REL + '/README.md', 'actual_host_enumeration': REL + '/actual-fastboot-enumeration.json',
        'pre_cache': REL + '/current-fastboot-cache-check.json',
        'post_cache': REL + '/post-enumeration/current-fastboot-cache-check.json',
        'source_review': REL + '/Fastboot-entry-source-review.json',
        'authorization_delta': REL + '/authorization-change.json',
        'host_fastboot_version': actual['host_tool_version_line'], 'listed_fastboot_devices': 0,
        'actual_mode_entry_or_camera_payload': False, 'independent_recovery_verified': False,
        'scope': 'Current-state discovery plus reference-source readiness only; not proof of entry failure/impossibility or recovery.'}
    prepared = new['prepared_first_device_trial']
    prepared['Fastboot_discovery_receipt'] = REL + '/actual-fastboot-enumeration.json'
    prepared['Fastboot_host_identification_executed'] = True
    prepared['Fastboot_mode_entry_executed'] = False
    prepared['Fastboot_mode_entry_procedure_ready'] = False
    new['next_safe_offline_actions'].append(
        '阶段135后，已完成标准Fastboot识别，不在无连接/模式变化时重复枚举。只有Mac/Windows，公开串口桥及FX3专用入口/载荷/退出未齐，不套用A7IV程序或猜按键。继续离线核对FX3 BootROM/板级适配可行性，并保留134认证→历史登记与真正系统备份接收器审查；不把新Fastboot测试请求扩大成Senser认证或RAM/分区写入。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'authorization', 'current_user_operational_constraint',
               'progress_audit', 'latest_stage_evidence', 'prepared_first_device_trial', 'next_safe_offline_actions'}
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for key, value in old['prepared_first_device_trial'].items():
        assert new['prepared_first_device_trial'][key] == value
    for key, value in old['latest_stage_evidence'].items():
        assert new['latest_stage_evidence'][key] == value
    for key, value in old['current_user_operational_constraint'].items():
        if key not in ('current_scope', 'camera_authorization_expanded'):
            assert new['current_user_operational_constraint'][key] == value
    encoded = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX3 Fastboot识别实测](<' + REL + '/README.md>)：官方37.0.1实际枚举为空、前后FX3仍MSC；A7IV自制载荷/串口桥不能直接套用，当前仅有电脑，尚未执行进入或刷写。'
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
    completed = {'status': 'PASS_REQUESTED_STANDARD_FASTBOOT_DISCOVERY_NOT_MODE_ENTRY_OR_RECOVERY',
        'created_utc': now, 'previous_manifest_members_verified': previous_count,
        'FX3_roots_pre_post': [1, 1], 'FX3_interfaces_pre_post': ['08/06/50', '08/06/50'],
        'actual_official_host_fastboot_executed': True, 'actual_host_listed_devices': 0,
        'cache_receipts_describe_only_their_own_collector_operations': True,
        'network_denied_for_fastboot_process': True, 'camera_mode_entry_or_partition_commands': 0,
        'Sony_A7IV_source_built_loaded_or_executed': False, 'system_install_or_driver_changes': False,
        'explicit_authorization_delta_only': True, 'all16_requirements_unchanged': True,
        'stage75_backend_and_stage117_frontend_pins': fixed,
        'canonical_equals_after': True, 'same_agent_review_not_independent_engine_or_recovery_test': True,
        'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', completed)
    files = [helper.record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage135-requested-Fastboot-discovery/1',
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
