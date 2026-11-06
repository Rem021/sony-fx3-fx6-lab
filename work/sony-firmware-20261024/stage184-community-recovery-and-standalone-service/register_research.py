"""Stage184 minimal registration, reusing the stage183 hash/CAS helpers unchanged. No device or firmware execution."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote
import json
import os
import plistlib
import re
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()
PRIOR = BASE / 'stage183-request-consumer-and-early-entry'
PRIOR_SHA = '900dfc4c3f8e348376e285a12f354f62be1e754559c9c1898c669df2606d2c0c'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
REPORT = HERE / 'reports/索尼 社区救砖 独立服务.md'
NOTE_DIR = HERE / 'research_notes/索尼 社区救砖 独立服务'
EXCLUDED_DIRS = {'.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache',
                 '.ruff_cache', '.cache', 'pip-cache', 'pip_cache', '.pip-cache',
                 '.pip_cache', 'dependency-cache', 'dependency_cache'}


def digest(path):
    h = sha256()
    with path.open('rb') as source:
        while chunk := source.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def volume():
    v = plistlib.loads(subprocess.check_output(
        ['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert v.get('VolumeUUID') == UUID and v.get('MountPoint') == '/Volumes/KAFU2T'
    assert ROOT.resolve() == Path('/Volumes/KAFU2T/AI/Projects/Mac')


def fresh(name, data):
    volume()
    with (HERE / name).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def put(name, value):
    fresh(name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def record(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return {'path': path.relative_to(ROOT).as_posix(),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def verify_records(records):
    for rec in records:
        path = Path(rec['path'])
        if not path.is_absolute():
            path = ROOT / path
        assert path.resolve().is_relative_to(ROOT.resolve()) and not path.is_symlink()
        assert path.stat().st_size == rec['bytes'] and digest(path) == rec['sha256'], str(path)


def verify_manifest(path, expected):
    assert digest(path) == expected, 'Previous manifest drift'
    manifest = json.loads(path.read_text())
    assert manifest['member_count'] == len(manifest['files'])
    verify_records(manifest['files'])
    return manifest


def inventory():
    files, omitted = [], []
    for directory, names, filenames in os.walk(HERE, followlinks=False):
        directory = Path(directory)
        for name in list(names):
            path = directory / name
            if name in EXCLUDED_DIRS:
                omitted.append({'path': path.relative_to(ROOT).as_posix(), 'kind': 'directory',
                                'reason': 'rebuildable dependency environment or cache; retained untouched'})
                names.remove(name)
            else:
                assert not path.is_symlink(), str(path)
        for name in filenames:
            path = directory / name
            if name == 'final-receipt.json':
                continue
            if path.suffix in {'.pyc', '.pyo'}:
                omitted.append({'path': path.relative_to(ROOT).as_posix(), 'kind': 'file',
                                'reason': 'compiled Python cache; retained untouched'})
                continue
            files.append(record(path))
    return sorted(files, key=lambda r: r['path']), sorted(omitted, key=lambda r: r['path'])


def local_links(path):
    checked = []
    for raw in re.findall(r'\]\(([^\n]+?)\)', path.read_text()):
        raw = raw.strip().strip('<>')
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', raw) or raw.startswith('#'):
            continue
        target = (path.parent / unquote(raw.split('#', 1)[0])).resolve()
        assert target.exists() and target.is_relative_to(ROOT.resolve()), (str(path), raw)
        checked.append(raw)
    return len(checked)


def cas(destination, expected, data, temp):
    fresh(temp, data)
    volume()
    assert destination.read_bytes() == expected, 'CAS refused concurrent drift: ' + str(destination)
    os.replace(HERE / temp, destination)
    assert destination.read_bytes() == data


def main():
    volume()
    assert not (HERE / 'final-receipt.json').exists(), 'Stage184 already sealed'
    assert not (ROOT / '.git').exists(), 'Mac root unexpectedly became Git-managed'
    prior = verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    assert len(prior['files']) == 122
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before = canonical.read_bytes()
    assert before == (PRIOR / 'goal-status-after.json').read_bytes(), 'Canonical drift'
    old = json.loads(before)
    assert old['latest_stage'] == PRIOR.name and len(old['requirements']) == 16
    assert old['goal_complete'] is False and old['persistent_write_release'] is False
    assert old['research_priority']['mode'] == 'recovery-first'
    notes = [NOTE_DIR / name for name in ('a7c2-recovery.md', 'community-independent.md', 'standalone-commands.md')]
    inputs = notes + [REPORT, PRIOR / 'reports/FX3 请求处理 独立启动.md', PRIOR / 'final-receipt.json']
    fingerprints = [record(path) for path in inputs]
    link_count = sum(local_links(path) for path in notes + [REPORT])
    a7dir = HERE / 'evidence/a7c2-recovery'
    sendir = HERE / 'evidence/standalone-commands'
    community = NOTE_DIR / 'community-evidence'
    capture = json.loads((a7dir / 'source-capture.json').read_text())
    reused = json.loads((a7dir / 'reused-source-inventory.json').read_text())
    legacy = json.loads((a7dir / 'legacy-library-size-hash-comparison.json').read_text())
    community_sources = json.loads((community / 'source-manifest.json').read_text())['sources']
    sen_sources = json.loads((sendir / 'sources.json').read_text())['sources']
    sen_members = json.loads((sendir / 'manifest.json').read_text())['files']
    source_records = list(reused) + list(sen_sources)
    for row in capture:
        if 'bytes' in row and 'sha256' in row:
            source_records.append(dict(path=str(a7dir / row['path']), bytes=row['bytes'], sha256=row['sha256']))
    for row in community_sources:
        if 'local' in row and 'bytes' in row and 'sha256' in row:
            source_records.append(dict(path=str(community / row['local']), bytes=row['bytes'], sha256=row['sha256']))
    for row in legacy:
        source_records.append(dict(path=row['path'], bytes=row['size'], sha256=row['sha256']))
    sen_records = [dict(row, path=str(sendir / row['path'])) for row in sen_members]
    verify_records(source_records)
    verify_records(sen_records)
    now = datetime.now(timezone.utc).isoformat()
    put('provenance.json', {
        'schema': 'fx3-stage184-research-provenance/1', 'recorded_utc': now,
        'report_complete_notes_and_prior_report': fingerprints,
        'source_manifest_paths': [REL + '/evidence/a7c2-recovery/source-capture.json', REL + '/evidence/a7c2-recovery/reused-source-inventory.json', REL + '/research_notes/索尼 社区救砖 独立服务/community-evidence/source-manifest.json', REL + '/evidence/standalone-commands/sources.json', REL + '/evidence/standalone-commands/manifest.json'],
        'source_records_rehashed': source_records, 'source_records_rehashed_count': len(source_records),
        'standalone_evidence_members_rehashed': len(sen_records),
        'failed_download_records_preserved_not_counted_as_captured_sources': sum('error' in r for r in capture + community_sources),
        'complete_notes_before_synthesis': True, 'local_links_checked': link_count,
        'synthesis_uses_completed_notes_and_existing_evidence_only': True,
        'registrar_hash_CAS_inventory_helpers_reused_from': str(PRIOR / 'register_research.py'),
        'registrar_installs_test_runs_firmware_execution_or_device_operations': 0,
        'scope': 'Community methods distinguished by failure layer: service checkpoint/field restoration, mode bypass, modded DAT and temporary p1 gates, model-specific BootROM/RAM payload. No independent FX3 7.02 restoration demonstrated; Jiritsu file provider remains in im loading domain. A7IV six backup names are preserved literally without inferring B0/B1 mapping.'})
    new = deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = '社区恢复与FX3独立服务定向研究完成：A7CII模式绕行、checkpoint/逆修改与YuuLuo修改DAT+p1门控分层；A7IV/ZVE10型号专用BootROM/RAM恢复及覆盖/验收边界已核。FX3独立sen有等级命令表，但GET/SET仍依赖im装载的Jiritsu queue016f0480，自身模式和固定p5/p8读不能替代文件恢复。未新增设备动作或持久写放行。'
    next_action = '仅离线：按现有原件先限定可达提供者与固定小目标读取合同（路径、设备分配/读取上限、完整长度、内外错误、认证副作用和UPM同步寿命），再对已有当前p1证据或后续获授权取得的原件逐库核对完整SHA与符号，判断YuuLuo共享门控语义能否迁移。保留MAIN故障态独立写回、早启p1选择与看护缺口；不启动相机读取、p1/modDAT或标志写入。'
    new['next_safe_offline_actions'] = [next_action] + old['next_safe_offline_actions']
    audit = new['progress_audit']
    audit['previous_goal_turn_classification'] = old['progress_audit']['classification']
    audit['classification'] = 'progress'
    audit['basis'].extend([
        '184社区有具体不同退路：A7CII#31本人明确不运行恢复、Movie绕行后恢复；QAQ checkpoint/原窗口还原依赖服务，#25四字节CP逆修改有完整文件回读和冷启视频验收；#44为自改工具反馈，#57认证成功不等于目标文件可读。',
        '184 YuuLuo确为修改DAT整包安装，官方2.01生成2.00、CRC/重加密保留0x110尾部且无新签名；RAM MENU版号门与持久p1两库窗口门分开。restore-only依赖MSC/服务/root工作器，只撤p1门控；原生回滚是本调用RAM旧片段+checksum及回读，不能跨全部旧步骤或断电自救。',
        '184 triple 72864B原库完整SHA与历史FX3 2.04/2.05 corecommon相同，两点定位RVchk4PI::chkFirmInfo_before；不证明当前7.02身份。dual 60600B库不同，不按偏移赋予签名/机型语义。A7IV仅p2触发并保持update_completed=false；ZVE10为CXD90045的16用户分区恢复，不含boot0/1/PT；A6700恢复尚未验成。',
        '184 FX3独立sen分等级发布命令；GET/SET_FILE经testcmd仅发IPC，queue016f0480由im域libJiritsu初始化。独立SEN_MODE只写smode UU/清理，固定裸读仅p5/p8；认证有条件持久历史/日志/模式副作用，UPM同步及故障看护未闭。',
        '184仅综合已完成笔记和静态证据、哈希复核/183清单验证与最小CAS登记；无新研究扩展、测试/安装、原固件/脚本/guest执行或设备/USB/admin/Windows/UU/GUI动作，16要求/目标/ALL授权/prepared/research_priority及false放行状态保留。'])
    new['latest_stage_evidence']['stage184_community_recovery_and_standalone_service'] = {
        'readme': REL + '/README.md', 'report': REPORT.relative_to(ROOT).as_posix(), 'provenance': REL + '/provenance.json',
        'a7c2_recovery_note': notes[0].relative_to(ROOT).as_posix(),
        'community_independent_note': notes[1].relative_to(ROOT).as_posix(),
        'standalone_commands_note': notes[2].relative_to(ROOT).as_posix(),
        'shared_legacy_library_comparison': REL + '/evidence/a7c2-recovery/legacy-library-size-hash-comparison.json',
        'standalone_provider_dependency': REL + '/evidence/standalone-commands/provider-dependency.json',
        'community_moded_DAT_and_temporary_p1_workflow_distinguished': True,
        'independent_sen_file_provider_im_dependency_proven': True,
        'FX3_7_02_independent_fault_recovery_or_current_p1_identity_proven': False,
        'new_device_operations_or_test_runs': 0}
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit', 'latest_stage_evidence', 'next_safe_offline_actions'}
    assert set(new) == set(old)
    for key in old:
        if key not in allowed:
            assert new[key] == old[key], key
    for key, value in old['latest_stage_evidence'].items():
        assert new['latest_stage_evidence'][key] == value
    assert new['requirements'] == old['requirements'] and new['authorization'] == old['authorization']
    assert new['prepared_first_device_trial'] == old['prepared_first_device_trial']
    assert new['research_priority'] == old['research_priority'] and new['objective'] == old['objective']
    assert new['next_safe_offline_actions'][1:] == old['next_safe_offline_actions']
    after = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    fresh('goal-status-before.json', before)
    fresh('goal-status-after.json', after)
    fresh('README.md', '''# 第184轮：社区救砖与独立服务边界

2026-10-29。经典ILME-FX3 7.02的1080p29.97 HEVC主录目标继续，优先研究修改失败后的退回。

[综合报告](<reports/索尼 社区救砖 独立服务.md>) · [三份最终笔记](<research_notes/索尼 社区救砖 独立服务/>) · [来源与复核](provenance.json)。A7CII已有模式绕行本人反馈、checkpoint/逆修改及YuuLuo改DAT+p1门控流程；后者的恢复环境与单步回滚不等于断电独立救砖。A7IV/ZVE10的BootROM/RAM入口需型号专用硬件与payload，未证适用于经典FX3 7.02。

FX3独立sen确有等级命令表，但Jiritsu文件消费者仍由im装载；自身SEN_MODE及固定p5/p8裸读不替代任意文件恢复。下一项仅离线限定提供者/固定小目标读取合同与当前p1库完整身份，不盲写p1或修改DAT。

登记复用183哈希/CAS逻辑，重验183清单122成员、canonical与183 after逐字一致；Mac入口新鲜读取并CAS。目标、全部16要求/状态、ALL授权/prepared/research_priority原样保留；goal_complete=false、persistent_write_release=false。最终清单覆盖本轮脚本、原件/指令证据、笔记与来源回执，排除.venv、__pycache__及pip/依赖缓存且不删除。

无相机/USB/admin/Windows/UU/GUI动作、原固件/脚本/guest执行、新测试/安装或原生goal manager操作。封存见[final-receipt.json](final-receipt.json)。
'''.encode())
    index_before = index.read_bytes()
    text = index_before.decode()
    marker = '## 相机与固件研究\n'
    entry = f'- [2026-10-29 索尼社区救砖与FX3独立服务](<{REL}/README.md>)：已核A7CII模式绕行、文件回退与改DAT/p1流程，以及A7IV/ZVE10早启恢复；FX3文件服务仍依赖im，下一项仅离线限定读取合同和当前p1库身份，无新增设备动作。'
    assert text.count(marker) == 1 and REL not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    fresh('readme-before.md', index_before)
    fresh('readme-after.md', index_after)
    volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent mutable-head drift'
    cas(canonical, before, after, '.canonical-stage184.tmp')
    cas(index, index_before, index_after, '.index-stage184.tmp')
    verify_records(fingerprints)
    verify_records(source_records)
    verify_records(sen_records)
    verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    put('registration-verification.json', {
        'schema': 'fx3-stage184-registration-verification/1', 'recorded_utc': now,
        'previous183_manifest_sha256': PRIOR_SHA, 'previous183_members_verified': len(prior['files']),
        'canonical_before_byte_equal_to183_after': True,
        'objective_all16_requirements_statuses_all_authorizations_and_all_prepared_fields_unchanged': True,
        'research_priority_exactly_unchanged': True, 'all_unrelated_top_level_sections_unchanged': True,
        'all_old_evidence_and_next_actions_retained': True,
        'canonical_after_byte_equal_to184_after': canonical.read_bytes() == after,
        'root_README_fresh_read_CAS_and_exact_after_match': index.read_bytes() == index_after,
        'local_note_and_report_links_checked': link_count, 'source_records_rehashed': len(source_records),
        'standalone_evidence_members_verified': len(sen_records), 'native_goal_manager_untouched': True,
        'registrar_installs_new_test_runs_original_firmware_or_device_operations': 0,
        'goal_complete': False, 'persistent_write_release': False})
    files, omitted = inventory()
    put('final-receipt.json', {
        'schema': 'fx3-stage184-community-recovery-and-standalone-service/1', 'created_utc': now, 'volume_uuid': UUID,
        'previous_manifest_path': (PRIOR / 'final-receipt.json').relative_to(ROOT).as_posix(),
        'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_members_verified': len(prior['files']),
        'files': files, 'member_count': len(files), 'mutable_heads_not_manifest_members': True,
        'exclusion_rules': {'directory_names_any_depth': sorted(EXCLUDED_DIRS), 'file_suffixes': ['.pyc', '.pyo'],
                            'self_manifest': 'final-receipt.json',
                            'reason': 'Exclude rebuildable dependency environments, pip/dependency caches and compiled caches; retain analysis scripts, original/disassembly evidence, notes, provenance and receipts.',
                            'excluded_paths_retained_without_deletion': True},
        'excluded_paths': omitted, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(after).hexdigest(),
                             'readme_before_sha256': sha256(index_before).hexdigest(), 'readme_after_sha256': sha256(index_after).hexdigest()},
        'research_priority_exactly_preserved': True, 'native_goal_manager_untouched': True,
        'new_device_operations_or_test_runs': 0, 'goal_complete': False, 'persistent_write_release': False})
    final_sha = digest(HERE / 'final-receipt.json')
    verify_manifest(HERE / 'final-receipt.json', final_sha)
    verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    assert canonical.read_bytes() == after and index.read_bytes() == index_after
    print(json.dumps({'report': str(REPORT), 'manifest_sha256': final_sha, 'members': len(files),
                      'previous183_members_verified': len(prior['files']), 'sources_rehashed': len(source_records),
                      'standalone_members_rehashed': len(sen_records), 'excluded_paths': len(omitted),
                      'canonical_matches184_after': True, 'objective_requirements_authorizations_prepared_priority_unchanged': True,
                      'goal_complete': False, 'persistent_write_release': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
