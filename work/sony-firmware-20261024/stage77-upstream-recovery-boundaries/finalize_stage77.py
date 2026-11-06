#!/usr/bin/env python3
"""Seal public-source/backup-range review, without device recovery claims."""
from pathlib import Path
import datetime
import json
import sys

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE.parent / 'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume()
    s, im = STAGE, h.im
    assert not (s / 'final-receipt.json').exists()
    canonical = h.BASE / 'GOAL_STATUS.json'
    before = (s / 'goal-status-before.json').read_bytes()
    prior = s.parent / 'stage76-native-reselection-and-packet-lifetime/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '9832673d38a3888c91d7d593719978823701cb5ce5c38e184528f5b8f1997014'
    prior_rows = json.loads(prior.read_text())['files']
    assert len(prior_rows) == 15
    for row in prior_rows:
        assert im.sha((h.ROOT / row['path']).read_bytes()) == row['sha256']
    assert before == canonical.read_bytes() == (prior.parent / 'goal-status-after.json').read_bytes()
    review = json.loads((s / 'completed-evidence-review.json').read_text())
    assert review['status'] == 'PASS_PINNED_SOURCE_SCOPE_AND_REFERENCE_ARITHMETIC_NOT_DEVICE_RECOVERY'
    assert review['prior_sealed_files_verified'] == 15
    assert review['reference_user_chunks'] == 112
    assert review['documented_range_sum_bytes'] == 1872756736
    assert review['official_FX3_package_hash_reverified']
    assert not any(review[k] for k in (
        'actual_camera_backup_full_restore_or_independent_FX3_rescue_proven',
        'reference_payload_or_vendor_tool_executed', 'Windows_UU_camera_operations',
        'goal_complete', 'persistent_write_release'))
    # Check source bytes against the completed audit's receipts without rerunning
    # the original image analysis or treating a manifest as a camera readback.
    sources = json.loads((s / 'source-manifest.json').read_text())
    for row in sources['sources']:
        assert im.sha((h.ROOT / row['saved_path']).read_bytes()) == row['sha256']
    rea = json.loads((s / 'REA-source-receipt.json').read_text())
    assert im.sha((s / 'public-source-snapshots/REA-firmware-analysis.md').read_bytes()) == rea['sha256']
    coverage = json.loads((s / 'reference-backup-coverage.json').read_text())
    tool = json.loads((s / 'REA-input-and-native-admission-scope.json').read_text())
    matrix = json.loads((s / 'FX3-independent-recovery-transfer-matrix.json').read_text())
    assert coverage['full_capacity_coverage_percentage'] is None
    assert not coverage['actual_raw_images_or_double_read_hashes_verified_here']
    assert not coverage['full_restore_demonstrated']
    assert not tool['package_within_documented_firmware_input_limit']
    assert not tool['REA_session_or_firmware_engine_launched_here']
    assert all(not x['FX3_supported'] for x in matrix['candidates'])
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rel = str(s.relative_to(h.ROOT))
    observation = {
        'recorded_utc': now, 'previous_goal_turn_classification': 'progress',
        'previous_evidence': 'stage76 sealed15 files and canonical reverified; original/native fragment evidence not rerun this stage.',
        'new_evidence': 'Pinned recovery-source review, quantified A6700 documented backup ranges, REA firmware-entry size/format bound checked against actual local FX3 package.',
        'new_implementation_or_device_acceptance': False,
        'A7CII_main_unchanged_from_stage46_not_counted_as_new_port': True,
        'latest_user_operational_instruction': 'Windows unavailable; use Mac for now.',
        'Windows_UU_actions_this_turn': 0, 'camera_operations': False,
        'full_goal_requirements_retained': 16, 'goal_complete': False,
        'persistent_write_release': False,
    }
    im.write_json(s / 'coordinator-observations.json', observation)
    summary = {
        'created_utc': now,
        'status': 'MAC_ONLY_PINNED_UPSTREAM_RECOVERY_SCOPE_AND_REA_INPUT_BOUNDARIES',
        'prior_sealed_files_verified': 15, 'reference_models': ['ILCE-7CM2/2.01', 'ILCE-6700/2.00', 'ILCE-7M4'],
        'new_A7CII_workaround_confirmation': 'Community self-report; no FX3 replication.',
        'A6700_documented_ranges_total_bytes': 1872756736,
        'A6700_documented_user_chunks': 112,
        'actual_camera_backup_or_double_read_verified': False,
        'A6700_whole_physical_capacity_or_full_restore_proven': False,
        'FX3_independent_recovery_proven': False,
        'REA_documented_firmware_input_limit_bytes': 134217728,
        'actual_local_official_FX3_package_bytes': 811876768,
        'REA_engine_or_reference_payload_executed': False,
        'new_main_recording_or_hardware_encoder_acceptance': False,
        'Windows_UU_camera_operations': False, 'goal_complete': False,
        'persistent_write_release': False,
    }
    im.write_json(s / 'summary.json', summary)
    old = json.loads(before)
    g = json.loads(before)
    g['updated_utc'] = now
    g['latest_stage'] = s.name
    g['research_activity'] = 'Mac_only_pinned_upstream_recovery_scope_backup_range_and_REA_input_boundaries'
    g['progress_audit'] = {
        'classification': 'progress', 'previous_goal_turn_classification': 'progress',
        'basis': [
            'stage76封存15件与canonical复核；本轮仅来源核对、参考区间计算和本地官方样本哈希复核，不重跑原型、不新增设备验收。',
            'A7CII main与stage46相同不算新移植；3.0.3仍只支持7CM2/2.01。10月26日新增旁路成功确认是社区自述，依赖存活模式，不能用于承诺FX3救砖。',
            'A6700参考文档范围共1872756736字节，用户区112块；物理总容量、实际备份文件、双读哈希和完整恢复未在本轮验证。参考RAM入口会改变相机执行环境，非缓存PnP权限，也不是FX3存储常量。',
            'REA文档固件入口上限128MiB；实际官方包811876768字节超过上限，av-cam非ELF。后续必须保留来源/偏移并分别确认格式与工具支持；未运行REA引擎，不把覆盖完成当完整重建。',
            '四条参考恢复路线均无本轮FX3独立入口/同机健康备份/受限写回与实际启动恢复验证；主录、音画长录、冷启动与恢复16项目标和Mac-only授权保持。',
        ],
        'completion_not_claimed': True,
        'source_review_not_new_runtime_or_hardware_acceptance': True,
    }
    g['latest_stage_evidence']['stage77_upstream_recovery_boundaries'] = {
        'readme': rel + '/README.md', 'review': rel + '/completed-evidence-review.json',
        'summary': rel + '/summary.json', 'sources': rel + '/upstream-observation-receipt.json',
        'backup_reference': rel + '/reference-backup-coverage.json',
        'tool_input_scope': rel + '/REA-input-and-native-admission-scope.json',
        'recovery_matrix': rel + '/FX3-independent-recovery-transfer-matrix.json',
        'scope': 'Pinned source review and reference arithmetic; no actual camera backup, payload execution, REA session, recovery or new main-recording proof.',
        'authorization_unchanged': True, 'goal_complete': False,
    }
    evidence = {
        'G03': ['REA-input-and-native-admission-scope.json', 'REA-source-receipt.json'],
        'G05': ['upstream-observation-receipt.json', 'FX3-independent-recovery-transfer-matrix.json'],
        'G07': ['reference-backup-coverage.json', 'FX3-independent-recovery-transfer-matrix.json'],
        'G15': ['FX3-independent-recovery-transfer-matrix.json', 'upstream-observation-receipt.json'],
        'G16': ['FX3-independent-recovery-transfer-matrix.json', 'reference-backup-coverage.json'],
    }
    scopes = {
        'G03': '官方包实际哈希再核一致，但811876768字节超过REA文档固件入口128MiB；av-cam非ELF，子文件支持及Mac工具可用性仍须分别确认，未运行REA。',
        'G05': 'A7CII发布修复和社区恢复旁路仅属其它机型来源；没有新增FX3真实认证/退出/USB完整传输或设备验收。',
        'G07': 'A6700文档参考范围复算112块用户区加两个引导区前缀，非FX3备份；物理总容量/实际双读文件及完整恢复未证，不能把范围一致视为完整同机健康备份。',
        'G15': 'A7CII存活模式旁路、应用恢复与其它机型Pico/Fastboot不等于FX3独立受限恢复；未写回、回读或验证机身启动/录像，无新增恢复完成证据。',
        'G16': '整理应用依赖恢复、存活模式旁路、硬件独立启动各自前提；A6700 RAM程序不属缓存PnP授权，FX3专用入口/身份/内存存储映射/恢复仍未证。',
    }
    for req in g['requirements']:
        if req['id'] in evidence:
            req['evidence'].extend(rel + '/' + name for name in evidence[req['id']])
            req['stage77_scope'] = scopes[req['id']]
    g['next_safe_offline_actions'].append(
        'stage77固定公开来源后继续FX3自身独立恢复入口、同机备份几何/范围/格式与受限恢复器的离线适配。A6700参考区间/RAM地址、A7CII产品标签/模式旁路和A7IV载荷均不得直接套用；REA先核对应入口大小、格式、主机与原始来源关系，覆盖完成不当作重建或安全刷回。当前仍不执行设备/RAM载荷/认证/切模式或Windows任务。')
    for key in ('objective', 'authorization', 'completion_rule', 'current_user_operational_constraint',
                'external_dependencies', 'current_guest_adapter_prototype'):
        assert g[key] == old[key]
    assert len(g['requirements']) == 16
    assert [(x['id'], x['status']) for x in g['requirements']] == [(x['id'], x['status']) for x in old['requirements']]
    assert not g['goal_complete'] and not g['persistent_write_release']
    im.write_json(s / 'goal-status-after.json', g)
    after = (s / 'goal-status-after.json').read_bytes()
    index = h.ROOT / 'README.md'
    ib = index.read_bytes()
    entry = '- [2026-10-26 FX3 上游恢复与REA入口核对](<work/sony-firmware-20261024/stage77-upstream-recovery-boundaries/README.md>)：其它机型恢复不能替代FX3保障；A6700参考范围复算与REA入口限制已核清，未新增实际备份/恢复/主录验收，仅Mac。'
    assert entry not in ib.decode() and ib.decode().count('## 相机与固件研究\n') == 1
    ia = ib.decode().replace('## 相机与固件研究\n', '## 相机与固件研究\n\n' + entry, 1).encode()
    assert canonical.read_bytes() == before and index.read_bytes() == ib
    canonical.write_bytes(after)
    index.write_bytes(ia)
    rows = [
        {'path': str(p.relative_to(h.ROOT)), 'bytes': p.stat().st_size, 'sha256': im.sha(p.read_bytes())}
        for p in sorted(s.rglob('*')) if p.is_file()
    ]
    final = {
        'schema': 'fx3-stage77-upstream-recovery-and-tool-scope/1', 'created_utc': now,
        'volume_uuid': im.VOLUME, 'files': rows,
        'previous_manifest_sha256': im.sha(prior.read_bytes()),
        'mutable_progress': {'path': str(canonical), 'before_sha256': im.sha(before), 'after_sha256': im.sha(after)},
        'readme_index_entry': entry, 'readme_index_before_sha256': im.sha(ib), 'readme_index_after_sha256': im.sha(ia),
        'operations': summary, 'requirements_retained': 16, 'authorization_unchanged': True,
    }
    im.write_json(s / 'final-receipt.json', final)
    assert all(im.sha((h.ROOT / x['path']).read_bytes()) == x['sha256'] for x in rows)
    assert canonical.read_bytes() == after and index.read_bytes() == ia
    print(json.dumps({
        'sealed_files': len(rows), 'manifest_sha256': im.sha((s / 'final-receipt.json').read_bytes()),
        'latest_stage': s.name, 'actual_FX3_backup_or_recovery_proven': False, 'goal_complete': False,
    }))


if __name__ == '__main__':
    main()
