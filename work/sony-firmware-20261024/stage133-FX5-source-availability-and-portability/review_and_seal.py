#!/usr/bin/env python3
"""Review local evidence and append progress; no camera, Windows or downloaded code."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import copy
import json
import os
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
PRIOR = BASE / 'stage132-public-recovery-and-service-interfaces'
PRIOR_SHA = '2d4715011c2498828f0886dce8f13b0a9587074d308397a830db022d4c6266a4'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def digest(path):
    with path.open('rb') as handle:
        hasher = sha256()
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def record(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def put(name, value):
    with (HERE / name).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def volume():
    result = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert result['VolumeUUID'] == UUID and result['WritableVolume']


def check_previous():
    assert digest(PRIOR / 'final-receipt.json') == PRIOR_SHA
    receipt = json.loads((PRIOR / 'final-receipt.json').read_text())
    for member in receipt['files']:
        path = ROOT / member['path']
        if member['path'] == 'README.md':
            path = PRIOR / 'readme-after.md'
        elif member['path'] == 'work/sony-firmware-20261024/GOAL_STATUS.json':
            path = PRIOR / 'goal-status-after.json'
        assert path.stat().st_size == member['bytes'] and digest(path) == member['sha256'], member['path']
    return len(receipt['files'])


def pins(goal):
    records = []
    for pin in goal['current_guest_adapter_prototype']['bundle'].values():
        path = ROOT / pin['path']
        assert digest(path) == pin['sha256']
        records.append(record(path))
    prior = BASE / 'stage117-native-audio-proxy-admission/final-receipt.json'
    assert digest(prior) == 'ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
    selected = [m for m in json.loads(prior.read_text())['files']
                if Path(m['path']).name in ('scoped_frontend.c', 'scoped_frontend.a64.o')]
    assert len(selected) == 2
    for pin in selected:
        path = ROOT / pin['path']
        assert digest(path) == pin['sha256'] and path.stat().st_size == pin['bytes']
        records.append(record(path))
    assert len(records) == 6
    return records


def main():
    volume()
    assert not (HERE / 'final-receipt.json').exists()
    previous_count = check_previous()
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before, index_before = (HERE / 'goal-status-before.json').read_bytes(), (HERE / 'readme-before.md').read_bytes()
    assert canonical.read_bytes() == before == (PRIOR / 'goal-status-after.json').read_bytes()
    assert index.read_bytes() == index_before
    goal = json.loads(before)
    assert goal['latest_stage'] == PRIOR.name and len(goal['requirements']) == 16
    assert not goal['goal_complete'] and not goal['persistent_write_release']
    fixed = pins(goal)
    downloads = json.loads((HERE / 'fx5-gpl-download-receipt.json').read_text())
    assert len(downloads['records']) == 5
    for item in downloads['records']:
        path = HERE / item['path']
        assert item['status'] == 'DOWNLOADED_NOT_EXECUTED' and item['official_content_md5_verified']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    for name, field in [('gpl-source-selection-receipt.json', 'archives'), ('fx3-gpl-reference-receipt.json', None)]:
        receipt = json.loads((HERE / name).read_text())
        files = [m for a in receipt[field] for m in a['selected_regular_sources']] if field else receipt['selected_files']
        for item in files:
            path = HERE / item['path']
            assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    table = json.loads((HERE / 'fx5-recording-table-review.json').read_text())
    assert len(table['expanded_rows']) == 52 and len(table['rows_at_29_97']) == 7 and len(table['HS_L_rows']) == 10
    assert not table['published_HS_L_1080_rows'] and not table['published_HS_L_29_97_rows']
    code = json.loads((HERE / 'code-portability-review.json').read_text())
    assert code['FX3_reference_source_version'] == '4.9.337' and code['FX5_source_version'] == '5.15.179'
    for item in code['facts']:
        path = HERE / item['path']
        assert digest(path) == item['sha256']
        lines = path.read_text().splitlines()
        for match in item['matches']:
            for line in match['matches']:
                assert lines[line['line'] - 1].strip() == line['text']
    stage131 = BASE / 'stage131-stock-parser-filecontrol-availability'
    preserved131 = [record(p) for p in sorted(stage131.rglob('*')) if p.is_file()]
    assert not (stage131 / 'final-receipt.json').exists()
    now = datetime.now(timezone.utc).isoformat()
    put('source-availability-and-scope.json', {
        'created_utc': now, 'user_requested_FX5_system_portability_research': True,
        'latest_user_source_preference_quote': '没有，按公开资料继续',
        'official_FX5_model_confirmed': 'ILME-FX5 / ILME-FX5B',
        'complete_FX5_device_firmware_obtained': False, 'latest_released_FX5_firmware_number_verified': False,
        'FX5_complete_image_UFU_FDAT_boot_partition_ELF_or_application_reverse_engineered': False,
        'FX5_official_GPL_archives_downloaded_and_statically_read': 5,
        'FX5_GPL_total_archive_bytes': sum(x['bytes'] for x in downloads['records']),
        'official_Japan_support_no_updates_text_captured': True,
        'US_SG_web_tool_pages_list_apps_only': True,
        'US_SG_direct_HTTP_403_not_evidence_of_absence': True,
        'China_product_download_icon_not_model_specific_package': True,
        'release_2_0_is_future_2027_plan_not_downloaded_release': True,
        'no_claim_that_public_search_excludes_all_private_or_regional_firmware': True,
        'whole_system_cross_flash_release': False,
        'application_UI_port_is_unproven_and_not_substituted_for_full_system': True,
        'exact_body_SoC_selected_DTB_RAM_keys_boot_chain_and_actual_application_ABI_unknown': True,
        'FX3_main_recording_goal_and_all16_requirements_unchanged': True,
        'previous_goal_turn_classification': 'progress',
        'previous_progress_evidence': 'stage132 sealed public recovery report, source notes and canonical update',
        'stage131_preservation_only_unsealed_not_adopted_as_hardware_evidence': preserved131,
        'new_device_Windows_UU_or_downloaded_code_execution': False,
        'authorization_expanded': False, 'goal_complete': False, 'persistent_write_release': False})
    after = copy.deepcopy(goal)
    after['updated_utc'] = now
    after['latest_stage'] = HERE.name
    after['research_activity'] = 'FX5 official source acquisition and offline code/recording-table portability assessment; no body firmware or camera operation'
    after['progress_audit']['classification'] = 'progress'
    after['progress_audit']['previous_goal_turn_classification'] = 'progress'
    after['progress_audit']['basis'].extend([
        '阶段133应用户新请求，取得FX5五个官方GPL包，完整长度/Content-MD5/SHA校验，静态读取内核与存储组件。',
        'FX5源码5.15.179/CXD90201相关平台与FX3参考4.9.337/CXD90057区别已固定；不将源码配置当实机芯片、内存或安全启动测量。',
        'FX5当前官方52行XAVC主录表中HEVC1080及29.97均未列，16M HD条目属于AVC，代理HEVC不充MAIN。',
        '尚未取得FX5整机更新包与实际版本；没有完成FX5镜像解包/重包或互刷。按用户确认继续公开资料。',
        '16项要求、授权、用户Mac-only约束及75/117固定原型不变；131保留未封存。主录/同机备份恢复/独立救援仍缺实机证据。'])
    evidence = 'stage133_FX5_source_availability_and_portability'
    assert evidence not in after['latest_stage_evidence']
    after['latest_stage_evidence'][evidence] = {
        'readme': REL + '/README.md', 'source_scope': REL + '/source-availability-and-scope.json',
        'GPL_downloads': REL + '/fx5-gpl-download-receipt.json',
        'source_selection': REL + '/gpl-source-selection-receipt.json',
        'code_comparison': REL + '/code-portability-review.json',
        'recording_table': REL + '/fx5-recording-table-review.json',
        'complete_FX5_firmware_or_camera_test': False,
        'whole_system_port_or_flash_ready': False, 'authorization_unchanged': True,
        'scope': 'Public model-associated source and manual analysis only; no actual body identity or recovery/output proof.'}
    after['next_safe_offline_actions'].append(
        '阶段133后，FX5完整更新包尚未取得；只有可核验官方实际包出现后才继续离线包头/版本/分区/ELF/应用与HAL分析。源码参考平台不同，整机互刷不放行；FX5当前表无目标HEVC MAIN，不用UI/代理替代原目标。继续FX3自身真正适用备份读家族/接收器与大小/路径/退出边界；131已有WIP保留不复跑。')
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit', 'latest_stage_evidence', 'next_safe_offline_actions'}
    for key in goal:
        if key not in allowed:
            assert after[key] == goal[key], key
    for key, value in goal['latest_stage_evidence'].items():
        assert after['latest_stage_evidence'][key] == value
    encoded = (json.dumps(after, ensure_ascii=False, indent=2) + '\n').encode()
    (HERE / 'goal-status-after.json').write_bytes(encoded)
    entry = '- [2026-10-27 FX5系统移植FX3核查](<' + REL + '/README.md>)：五个官方GPL包静态拆读，5.15/CXD90201与FX3参考平台不同；当前表无目标HEVC主录，完整FX5机身固件未取得，互刷未放行。'
    marker = '## 相机与固件研究\n'
    text = index_before.decode()
    assert text.count(marker) == 1 and entry not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    (HERE / 'readme-after.md').write_bytes(index_after)
    volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent progress change; CAS refused'
    assert pins(goal) == fixed
    assert [record(p) for p in sorted(stage131.rglob('*')) if p.is_file()] == preserved131
    for target, data, name in [(canonical, encoded, '.goal-write.tmp'), (index, index_after, '.index-write.tmp')]:
        temporary = HERE / name
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    assert canonical.read_bytes() == encoded and index.read_bytes() == index_after
    check_previous()
    review = {'status': 'PASS_FX5_PUBLIC_SOURCE_PORTABILITY_REVIEW_NOT_DEVICE_OR_FLASH_RELEASE',
              'created_utc': now, 'previous_manifest_members_verified_via_snapshots': previous_count,
              'five_archives_length_MD5_SHA_verified': True, 'selected_sources_hashes_verified': True,
              'recording_table_rows': 52, 'code_fact_groups': len(code['facts']),
              'stage75_bundle_and_stage117_frontend_pins': fixed,
              'all16_requirements_and_authorization_unchanged': True,
              'canonical_equals_after': True, 'stage131_unsealed_preserved': True,
              'same_agent_local_review_not_independent_engine_or_real_camera_acceptance': True,
              'goal_complete': False, 'persistent_write_release': False}
    put('completed-evidence-review.json', review)
    members = [record(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('final-receipt.json', {'schema': 'fx3-stage133-FX5-portability/1', 'created_utc': now,
        'volume_uuid': UUID, 'files': members, 'member_count': len(members),
        'previous_manifest_sha256': PRIOR_SHA,
        'previous_stage132_mutable_heads_validated_via_immutable_after_snapshots': True,
        'mutable_progress': {'canonical_before_sha256': sha256(before).hexdigest(), 'canonical_after_sha256': sha256(encoded).hexdigest(),
                             'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'mutable_project_heads_not_manifest_members': True, 'allowed_goal_keys_changed': sorted(allowed),
        'operations': review})
    print(json.dumps({'manifest_sha256': digest(HERE / 'final-receipt.json'), 'members': len(members),
                      'canonical_after_sha256': digest(canonical), 'goal_complete': False, 'persistent_write_release': False}))


if __name__ == '__main__':
    main()
