"""Register completed static research; do not run firmware or access any device."""
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
PRIOR = BASE / 'stage181-recovery-first-research'
PRIOR_SHA = '999ba00c2c6d983436eb434405004a66d087fe10e76e34e4357a32eef6dfe10c'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
REPORT = HERE / 'reports/FX3 恢复启动 版本准入.md'
NOTE_DIR = HERE / 'research_notes/FX3 恢复启动 版本准入'
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
    assert not (HERE / 'final-receipt.json').exists(), 'Stage182 already sealed'
    assert not (ROOT / '.git').exists(), 'Mac root unexpectedly became Git-managed'
    prior = verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before = canonical.read_bytes()
    assert before == (PRIOR / 'goal-status-after.json').read_bytes(), 'Canonical drift: stop and rebase only necessary fields'
    old = json.loads(before)
    assert old['latest_stage'] == PRIOR.name and len(old['requirements']) == 16
    assert old['goal_complete'] is False and old['persistent_write_release'] is False
    assert old['research_priority']['mode'] == 'recovery-first'

    notes = [NOTE_DIR / name for name in ('boot-request.md', 'current-updater.md', 'version-admission.md')]
    inputs = notes + [REPORT, PRIOR / 'reports/FX3 改机失败 恢复路线.md', PRIOR / 'final-receipt.json']
    fingerprints = [record(path) for path in inputs]
    link_count = sum(local_links(path) for path in notes + [REPORT])
    boot = json.loads((HERE / 'evidence/boot-request/source-manifest.json').read_text())
    admission = json.loads((HERE / 'version-admission/static-admission-evidence.json').read_text())['sources']
    assets = json.loads((HERE / 'current-updater-evidence/current-updater-asset-audit.json').read_text())['sources']
    source_records = boot + admission + assets
    verify_records(source_records)
    now = datetime.now(timezone.utc).isoformat()
    urls = sorted(set(re.findall(r'https://[^\s)<>]+', '\n'.join(path.read_text() for path in notes + [REPORT]))))
    put('provenance.json', {
        'schema': 'fx3-stage182-research-provenance/1', 'recorded_utc': now,
        'report_complete_notes_and_prior_report': fingerprints,
        'primary_source_urls_in_notes_and_report': urls,
        'source_manifest_paths': [REL + '/evidence/boot-request/source-manifest.json',
                                  REL + '/version-admission/static-admission-evidence.json',
                                  REL + '/current-updater-evidence/current-updater-asset-audit.json'],
        'source_records_rehashed_by_registrar': len(source_records),
        'complete_notes_before_synthesis': True, 'local_links_checked': link_count,
        'synthesis_uses_completed_notes_and_existing_evidence_only': True,
        'dependency_versions_and_location': REL + '/evidence/boot-request/static-tools-and-scope.json',
        'registrar_installs_test_runs_firmware_execution_or_device_operations': 0,
        'scope': 'Old2.04/2.05 admission is not current p1; current7.02 body/MAIN evidence does not prove recovery entry. Queue0x376 actual registered callback remains unresolved.'})

    new = deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = '恢复优先静态研究完成：旧sauu同版comp缺失续行及-s真跳版本、旧SD严格比较已区分；当前7.02 body先写dat4后写comp，整包未含独立p1载荷；启动请求追至queue0x376间接回调但消费者未解。未新增设备动作或放行。'
    next_action = '恢复优先：仅用现有官方原件，恢复osal_uipc.ko queue0x376的回调登记节点+0x10 target（.text+0x3644 blr x3），从osal_reg_msg_queue_cb/reg_msg_queue_cb登记者或可识别WBI结构绑定0/2/5/6真实效果，继续追selector及p1/p3选择；不可见时输出精确缺件/只读获取合同，不拿旧p1替代，不执行相机命令或持久写入。'
    new['next_safe_offline_actions'] = [next_action] + old['next_safe_offline_actions']
    audit = new['progress_audit']
    audit['previous_goal_turn_classification'] = old['progress_audit']['classification']
    audit['classification'] = 'progress'
    audit['basis'].extend([
        '182原代码证实旧普通sauu同版时comp缺失可放版本门，-s直接跳比较，旧sdfileinput严格大于且不消费comp；不将任何旧分支直接套给当前7.02 p1。当前body的dat4写入先于comp创建，程序顺序窗口已定位，未声称实机掉电持久结果。',
        '182当前7.02 helper经Backup0x004b0000首字节1/2门发送原argv，经/dev/uipc和ioctl0x80000004到queue0x376登记节点+0x10的间接调用；0返回可掩盖未发送或接收-1022，实际消费者/持久selector及独立启动尚未证明。',
        '182重验官方整包哈希/UFU与FDAT全槽/全部TAR及105 SUM，无独立p1载荷；p3 kernel/initrd属于MAIN。p1声明容量25100288字节和配套p2当前状态/映射仍缺，同机原件不能由旧p1或U-body替代。',
        '182保留recovery-first原字段、目标全部16项状态、ALL授权与prepared字段；来源/链接/181封存复核仅为宿主核验，无原固件执行、设备/USB/admin/Windows/UU/GUI动作或新测试。缺少修改包不是离线阻断，goal_complete与persistent_write_release仍false。'])
    new['latest_stage_evidence']['stage182_boot_selector_and_recovery_admission'] = {
        'readme': REL + '/README.md', 'report': REPORT.relative_to(ROOT).as_posix(),
        'provenance': REL + '/provenance.json',
        'boot_request_source_manifest': REL + '/evidence/boot-request/source-manifest.json',
        'boot_request_tools_and_scope': REL + '/evidence/boot-request/static-tools-and-scope.json',
        'version_admission_evidence': REL + '/version-admission/static-admission-evidence.json',
        'current_asset_audit': REL + '/current-updater-evidence/current-updater-asset-audit.json',
        'table_and_sum_validation': REL + '/current-updater-evidence/table-and-sum-validation.json',
        'old_sauu_same_version_and_skip_branches_proven': True,
        'current_body_dat4_before_comp_order_proven': True,
        'current_package_independent_p1_payload_found': False,
        'queue_0x376_actual_callback_or_independent_recovery_proven': False,
        'current_installed_p1_and_p2_state_acquired': False,
        'new_device_operations_or_test_runs': 0}
    allowed = {'updated_utc', 'latest_stage', 'research_activity', 'progress_audit',
               'latest_stage_evidence', 'next_safe_offline_actions'}
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

    fresh('README.md', '''# 第182轮：恢复启动请求与版本准入

2026-10-29。经典ILME-FX3 7.02的1080p29.97 HEVC主录目标继续，优先解决修改失败后的退回。

[综合报告](<reports/FX3 恢复启动 版本准入.md>) · [三份最终笔记](<research_notes/FX3 恢复启动 版本准入/>) · [来源与复核](provenance.json)。旧sauu同版comp缺失续行和-s跳版本已由原代码证明，旧SD仍严格比较；当前7.02 body先dat4后comp，不能预设失败后版本仍旧。完整7.02包未找到独立p1载荷，MAIN kernel/initrd和U-body不代作p1。

7.02请求经Backup门、/dev/uipc及ioctl到queue0x376间接回调；实际登记target未解，helper返回0不能证明发送或进入恢复。下一项仅从原登记节点+0x10和osal_reg_msg_queue_cb/reg_msg_queue_cb/WBI结构追真实消费者及selector，不重复泛查或执行设备方案。

全部16项状态、目标、授权、prepared与原research_priority原样保留；goal_complete=false、persistent_write_release=false。未新增相机/USB/admin/Windows/UU/GUI操作、测试或原固件执行，未触碰原生goal manager。

登记重验181清单13成员，canonical与181 after逐字相同；新鲜读取Mac入口并以CAS保留并发内容。最终清单覆盖实际分析脚本、反汇编、证据和回执，明确排除.venv、__pycache__与pip/依赖缓存，保留这些目录不删除。依赖位置及版本见[工具回执](evidence/boot-request/static-tools-and-scope.json)。封存见[final-receipt.json](final-receipt.json)。
'''.encode())
    index_before = index.read_bytes()
    text = index_before.decode()
    marker = '## 相机与固件研究\n'
    entry = f'- [2026-10-29 FX3恢复启动与版本准入](<{REL}/README.md>)：旧同版续行/跳版本与当前body写点已定位；7.02请求追至内核间接回调，整包无独立p1载荷，下一项查queue0x376登记消费者，无新增相机动作。'
    assert text.count(marker) == 1 and REL not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    fresh('readme-before.md', index_before)
    fresh('readme-after.md', index_after)
    volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent mutable-head drift'
    cas(canonical, before, after, '.canonical-stage182.tmp')
    cas(index, index_before, index_after, '.index-stage182.tmp')
    verify_records(fingerprints)
    verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    put('registration-verification.json', {
        'schema': 'fx3-stage182-registration-verification/1', 'recorded_utc': now,
        'previous181_manifest_sha256': PRIOR_SHA, 'previous181_members_verified': len(prior['files']),
        'canonical_before_byte_equal_to181_after': True,
        'objective_all16_requirements_statuses_all_authorizations_and_all_prepared_fields_unchanged': True,
        'research_priority_exactly_unchanged': True, 'all_unrelated_top_level_sections_unchanged': True,
        'all_old_evidence_and_next_actions_retained': True,
        'canonical_after_byte_equal_to182_after': canonical.read_bytes() == after,
        'root_README_fresh_read_CAS_and_exact_after_match': index.read_bytes() == index_after,
        'local_note_and_report_links_checked': link_count,
        'research_source_records_rehashed': len(source_records),
        'native_goal_manager_untouched': True,
        'registrar_installs_new_test_runs_original_firmware_or_device_operations': 0,
        'goal_complete': False, 'persistent_write_release': False})
    files, omitted = inventory()
    put('final-receipt.json', {
        'schema': 'fx3-stage182-boot-selector-and-recovery-admission/1',
        'created_utc': now, 'volume_uuid': UUID,
        'previous_manifest_path': (PRIOR / 'final-receipt.json').relative_to(ROOT).as_posix(),
        'previous_manifest_sha256': PRIOR_SHA, 'previous_manifest_members_verified': len(prior['files']),
        'files': files, 'member_count': len(files), 'mutable_heads_not_manifest_members': True,
        'exclusion_rules': {'directory_names_any_depth': sorted(EXCLUDED_DIRS),
                            'file_suffixes': ['.pyc', '.pyo'],
                            'self_manifest': 'final-receipt.json',
                            'reason': 'Exclude rebuildable dependency environments, pip/dependency caches and compiled caches; retain analysis scripts, original/disassembly evidence, notes and receipts.',
                            'excluded_paths_retained_without_deletion': True},
        'excluded_paths': omitted, 'allowed_goal_keys_changed': sorted(allowed),
        'mutable_progress': {'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(after).hexdigest(),
                             'readme_before_sha256': sha256(index_before).hexdigest(),
                             'readme_after_sha256': sha256(index_after).hexdigest()},
        'research_priority_exactly_preserved': True, 'native_goal_manager_untouched': True,
        'new_device_operations_or_test_runs': 0, 'goal_complete': False, 'persistent_write_release': False})
    final_sha = digest(HERE / 'final-receipt.json')
    verify_manifest(HERE / 'final-receipt.json', final_sha)
    verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    assert canonical.read_bytes() == after and index.read_bytes() == index_after
    print(json.dumps({'report': str(REPORT), 'manifest_sha256': final_sha, 'members': len(files),
                      'previous181_members_verified': len(prior['files']), 'excluded_paths': omitted,
                      'canonical_matches182_after': True, 'objective_requirements_authorizations_prepared_priority_unchanged': True,
                      'goal_complete': False, 'persistent_write_release': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
