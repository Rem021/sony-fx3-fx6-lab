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
PRIOR = BASE / 'stage182-boot-selector-and-recovery-admission'
PRIOR_SHA = '874847808039f583b5bfce9874da4b95d5a0c8b65e68d8dded5bb79c49f1db0f'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
REPORT = HERE / 'reports/FX3 请求处理 独立启动.md'
NOTE_DIR = HERE / 'research_notes/FX3 请求处理 独立启动'
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
    assert not (HERE / 'final-receipt.json').exists(), 'Stage183 already sealed'
    assert not (ROOT / '.git').exists(), 'Mac root unexpectedly became Git-managed'
    prior = verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    assert len(prior['files']) == 641
    canonical, index = BASE / 'GOAL_STATUS.json', ROOT / 'README.md'
    before = canonical.read_bytes()
    assert before == (PRIOR / 'goal-status-after.json').read_bytes(), 'Canonical drift'
    old = json.loads(before)
    assert old['latest_stage'] == PRIOR.name and len(old['requirements']) == 16
    assert old['goal_complete'] is False and old['persistent_write_release'] is False
    assert old['research_priority']['mode'] == 'recovery-first'
    notes = [NOTE_DIR / name for name in ('usb-main-dependency.md', 'queue-consumer.md', 'early-selector.md')]
    inputs = notes + [REPORT, PRIOR / 'reports/FX3 恢复启动 版本准入.md', PRIOR / 'final-receipt.json']
    fingerprints = [record(path) for path in inputs]
    link_count = sum(local_links(path) for path in notes + [REPORT])
    queue = json.loads((HERE / 'evidence/queue-consumer/source-manifest.json').read_text())
    early = json.loads((HERE / 'evidence/early-selector/early-selector-evidence.json').read_text())
    usbdir = HERE / 'evidence/usb-main-dependency'
    usb = json.loads((usbdir / 'manifest.json').read_text())
    verify_records(usb['files'])
    graph = json.loads((usbdir / 'process-registration-dependency-graph.json').read_text())
    closure = json.loads((usbdir / 'static-dependency-closure.json').read_text())
    assert len(closure['resolved_members']) == 18 and not closure['missing']
    source_records = queue + graph['prior_sources']
    source_records.append({'path': early['source'], 'bytes': early['bytes'], 'sha256': early['sha256']})
    upm = Path(early['upm']['source'])
    source_records.append({'path': str(upm), 'bytes': upm.stat().st_size, 'sha256': early['upm']['sha256']})
    for r in closure['partitions']:
        path = BASE / f"stage2/extraction/nflasha{r['part']}.img"
        source_records.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': r['sha256']})
    verify_records(source_records)
    now = datetime.now(timezone.utc).isoformat()
    put('provenance.json', {
        'schema': 'fx3-stage183-research-provenance/1', 'recorded_utc': now,
        'report_complete_notes_and_prior_report': fingerprints,
        'source_manifest_paths': [REL + '/evidence/queue-consumer/source-manifest.json', REL + '/evidence/early-selector/early-selector-evidence.json', REL + '/evidence/usb-main-dependency/manifest.json', REL + '/evidence/usb-main-dependency/ap-topology.json', REL + '/evidence/usb-main-dependency/static-dependency-closure.json'],
        'source_records_rehashed': source_records, 'source_records_rehashed_count': len(source_records),
        'usb_evidence_members_rehashed': len(usb['files']),
        'complete_notes_before_synthesis': True, 'local_links_checked': link_count,
        'synthesis_uses_completed_notes_and_existing_evidence_only': True,
        'tools_and_scope': REL + '/evidence/queue-consumer/scope.json',
        'registrar_installs_test_runs_firmware_execution_or_device_operations': 0,
        'scope': 'Configured NOR static VA, kernel section offsets and ELF link VA are not observed runtime PC. Conditional early mode consumption and independent sen topology do not prove recovery. Queue0x376 real business recipient remains unresolved.'})
    new = deepcopy(old)
    new['updated_utc'] = now
    new['latest_stage'] = HERE.name
    new['research_activity'] = '恢复优先静态研究完成：当前NOR含早期mode存在性消费者及所选mode到UPM的Backup桥，FAT/远端mode/p1选择未闭；queue0x376第一跳纠正为OSAL唤醒/包装/用户pending交接，实际业务收件人仍缺；独立sen.elf条件启动与自建USB/事件循环已证，命令/看护/故障态恢复未证。未新增设备动作或放行。'
    next_action = '恢复优先：仅用现有官方原件，先从sen.elf+0x401f80及libsencore+0xb094/+0xceb0/+0xcc1c恢复独立模式Worker/Cooperator、命令表和鉴权后文件/请求下游IPC，核对bootin/watchdog与UPM/LIRO存活前提；再识别queue0x376实际登记/阻塞收件来源并追其真正第二跳，保留NOR FAT-ready/当前partition、SPI bootdata+0x30远端生产及当前p1/p3选择缺件。无相机命令或标志/持久写入。'
    new['next_safe_offline_actions'] = [next_action] + old['next_safe_offline_actions']
    audit = new['progress_audit']
    audit['previous_goal_turn_classification'] = old['progress_audit']['classification']
    audit['classification'] = 'progress'
    audit['basis'].extend([
        '183当前NOR先cache/内存word，再在FAT-ready且当前partition2前提下检查updater/mode存在；SPI字段4/7、loader枚举和argv5/6分域。NOR Backup0x0051000F写与UPM同项同址读已接通，但非请求因果、当前机身命中或p1/p3选择证明。',
        '183纠正182通用queue walker第一跳语义：node+0x10公开构造为阻塞接收唤醒/内核包装/用户pending交接；真正业务在线程醒后、node+0x20或用户代理32f0。queue0x376实际节点仍缺，LIRO导入及av-cam配置记录不补作收件人。',
        '183普通NIN/libObj与appFw共属im.elf线程/动态装载；独立sen在MODE非0、非BIS、预置可读UU时先启，仍启bootin。自建USB/事件循环及18文件静态闭包已证；命令/Cooperator、动态插件、watchdog/UPM/LIRO、故障态写回/退出/归还未证。',
        '183只综合静态研究、核验来源/182封存及最小CAS登记；无原固件/脚本/guest执行、新测试/安装或设备/USB/admin/Windows/UU/GUI动作；保留16要求、目标、ALL授权/prepared/research_priority，goal_complete和persistent_write_release仍false。'])
    new['latest_stage_evidence']['stage183_request_consumer_and_early_entry'] = {
        'readme': REL + '/README.md', 'report': REPORT.relative_to(ROOT).as_posix(), 'provenance': REL + '/provenance.json',
        'queue_original_pins': REL + '/evidence/queue-consumer/annotated-pins.txt',
        'early_selector_evidence': REL + '/evidence/early-selector/early-selector-evidence.json',
        'process_dependency_graph': REL + '/evidence/usb-main-dependency/process-registration-dependency-graph.json',
        'static_dependency_closure': REL + '/evidence/usb-main-dependency/static-dependency-closure.json',
        'current_NOR_conditional_mode_file_consumer_proven': True,
        'NOR_chosen_mode_Backup_to_UPM_bridge_proven': True,
        'queue_0x376_actual_business_recipient_proven': False,
        'independent_sen_ELF_startup_USB_and_event_loop_topology_proven': True,
        'independent_sen_command_watchdog_or_failure_survival_proven': False,
        'current_p1_p3_selection_or_recovery_proven': False, 'new_device_operations_or_test_runs': 0}
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
    fresh('README.md', '''# 第183轮：请求交接与独立恢复入口

2026-10-29。经典ILME-FX3 7.02的1080p29.97 HEVC主录目标继续，优先解决修改失败后的退回。

[综合报告](<reports/FX3 请求处理 独立启动.md>) · [三份最终笔记](<research_notes/FX3 请求处理 独立启动/>) · [来源与复核](provenance.json)。当前NOR有带FAT-ready/当前partition2前提的mode存在性消费者；所选mode经Backup0x0051000F进入UPM观测，但远端mode与p1/p3装载仍缺。

queue0x376第一跳是OSAL唤醒/内核包装/用户pending交接，业务收件人仍未找到。普通NIN与appFw共属im.elf；独立sen有条件后台启动、自建USB与事件循环，但仍启bootin，命令、Cooperator与看护/故障态存活未闭。下一项先查独立sen命令准入及bootin/watchdog前提，再按实际来源追queue第二跳。

全部16项状态、目标、ALL授权/prepared及research_priority原样保留；goal_complete=false、persistent_write_release=false。仅静态综合与哈希登记，无新增相机/USB/admin/Windows/UU/GUI动作、原固件/脚本/guest执行、新测试/安装或原生goal manager操作。

登记重验182清单641成员、canonical与182 after逐字一致；Mac入口新鲜读取并CAS保留并发内容。最终清单覆盖实际分析脚本、原件/指令证据、反汇编、笔记和来源回执，明确排除.venv、__pycache__及pip/依赖缓存且不删除。工具见[范围回执](evidence/queue-consumer/scope.json)，封存见[final-receipt.json](final-receipt.json)。
'''.encode())
    index_before = index.read_bytes()
    text = index_before.decode()
    marker = '## 相机与固件研究\n'
    entry = f'- [2026-10-29 FX3请求交接与独立恢复入口](<{REL}/README.md>)：NOR早期mode条件消费者和独立sen进程已证；queue0x376仍停OSAL交接，下一项查独立sen命令与看护依赖，无新增设备动作。'
    assert text.count(marker) == 1 and REL not in text
    index_after = text.replace(marker, marker + '\n' + entry + '\n', 1).encode()
    fresh('readme-before.md', index_before)
    fresh('readme-after.md', index_after)
    volume()
    assert canonical.read_bytes() == before and index.read_bytes() == index_before, 'Concurrent mutable-head drift'
    cas(canonical, before, after, '.canonical-stage183.tmp')
    cas(index, index_before, index_after, '.index-stage183.tmp')
    verify_records(fingerprints)
    verify_manifest(PRIOR / 'final-receipt.json', PRIOR_SHA)
    put('registration-verification.json', {
        'schema': 'fx3-stage183-registration-verification/1', 'recorded_utc': now,
        'previous182_manifest_sha256': PRIOR_SHA, 'previous182_members_verified': len(prior['files']),
        'canonical_before_byte_equal_to182_after': True,
        'objective_all16_requirements_statuses_all_authorizations_and_all_prepared_fields_unchanged': True,
        'research_priority_exactly_unchanged': True, 'all_unrelated_top_level_sections_unchanged': True,
        'all_old_evidence_and_next_actions_retained': True,
        'canonical_after_byte_equal_to183_after': canonical.read_bytes() == after,
        'root_README_fresh_read_CAS_and_exact_after_match': index.read_bytes() == index_after,
        'local_note_and_report_links_checked': link_count, 'source_records_rehashed': len(source_records),
        'usb_evidence_members_verified': len(usb['files']), 'native_goal_manager_untouched': True,
        'registrar_installs_new_test_runs_original_firmware_or_device_operations': 0,
        'goal_complete': False, 'persistent_write_release': False})
    files, omitted = inventory()
    put('final-receipt.json', {
        'schema': 'fx3-stage183-request-consumer-and-early-entry/1', 'created_utc': now, 'volume_uuid': UUID,
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
                      'previous182_members_verified': len(prior['files']), 'sources_rehashed': len(source_records),
                      'usb_members_rehashed': len(usb['files']), 'excluded_paths': omitted,
                      'canonical_matches183_after': True, 'objective_requirements_authorizations_prepared_priority_unchanged': True,
                      'goal_complete': False, 'persistent_write_release': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
