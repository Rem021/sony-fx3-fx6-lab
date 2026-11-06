#!/usr/bin/env python3
"""One-shot, scoped source cleanup; never launches QEMU or edits the runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import plistlib
import re
import shutil
import stat
import subprocess

HOST = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host')
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
OUT = ROOT / 'outputs/fx3-vm'
SOURCE = HOST / 'sources/qemu-11.1.2'
ARCHIVE = HOST / 'downloads/qemu-11.1.2.tar.xz'
DTC = SOURCE / 'subprojects/dtc'
SUPPORT = HOST / 'source-cleanup-support'
RECEIPT = HOST / 'third-party-source-cleanup-receipt.json'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(args, **kwargs):
    p = subprocess.run(args, capture_output=True, text=True, check=True, **kwargs)
    return p.stdout


def write_json(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def volume_guard():
    p = subprocess.run(['diskutil', 'info', '-plist', '/Volumes/KAFU2T'],
                       capture_output=True, check=True)
    info = plistlib.loads(p.stdout)
    assert info['VolumeUUID'].upper() == UUID
    assert info['MountPoint'] == '/Volumes/KAFU2T'
    return {k: info[k] for k in ('VolumeUUID', 'MountPoint', 'DeviceIdentifier')}


def stats(path):
    result = {'path': str(path), 'regular_files': 0, 'regular_file_bytes': 0,
              'directories': 0, 'symlinks': 0, 'symlink_text_bytes': 0,
              'other_entries': 0}
    paths = [path]
    if path.is_dir():
        paths.extend(p for base, dirs, files in os.walk(path, followlinks=False)
                     for p in [*(Path(base) / n for n in dirs),
                               *(Path(base) / n for n in files)])
    for p in paths:
        s = p.lstat()
        if stat.S_ISREG(s.st_mode):
            result['regular_files'] += 1
            result['regular_file_bytes'] += s.st_size
        elif stat.S_ISLNK(s.st_mode):
            result['symlinks'] += 1
            result['symlink_text_bytes'] += s.st_size
        elif stat.S_ISDIR(s.st_mode):
            result['directories'] += 1
        else:
            result['other_entries'] += 1
    return result


def frozen_check():
    seal = json.loads((OUT / 'metadata/file-manifest.json').read_text())
    results = []
    for item in seal['files']:
        p = OUT / item['path']
        got = sha(p)
        assert got == item['sha256'], (p, got, item['sha256'])
        assert p.stat().st_size == item['bytes']
        results.append({'path': str(p), 'sha256': got, 'bytes': p.stat().st_size})
    for p in [OUT / 'metadata/file-manifest.json',
              HOST / 'writer-ready.json', HOST / 'source-receipt.json',
              HOST / 'internal-dtc-receipt.json', HOST / 'final-deployment-summary.json',
              ROOT / 'work/fx3-vm-20261101/research_notes/FX3 Mac 虚拟机部署研究/host-deployment.md']:
        results.append({'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size})
    kernel = json.loads((OUT / 'manifest.json').read_text())['kernel']
    p = Path(kernel['path'])
    assert sha(p) == kernel['sha256'] and p.stat().st_size == kernel['bytes']
    results.append({'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size})
    return results


def closure_check():
    result = []
    for rel in ['bin/qemu-system-aarch64', 'lib/libglib-2.0.0.dylib',
                'lib/libpcre2-8.0.dylib', 'lib/libintl.8.dylib']:
        p = OUT / rel
        deps = run(['otool', '-L', str(p)])
        commands = run(['otool', '-l', str(p)])
        assert 'cmd LC_RPATH\n' not in commands
        parsed = []
        for line in deps.splitlines()[1:]:
            dep = line.strip().split(' (compatibility version', 1)[0]
            if not dep:
                continue
            if dep.startswith(('/usr/lib/', '/System/Library/')):
                parsed.append({'path': dep, 'system': True})
            else:
                assert dep.startswith('@loader_path/'), dep
                resolved = (p.parent / dep.removeprefix('@loader_path/')).resolve()
                assert resolved.is_relative_to(OUT) and resolved.is_file(), resolved
                parsed.append({'path': dep, 'system': False,
                               'resolved': str(resolved), 'sha256': sha(resolved)})
        signature = run(['codesign', '--verify', '--strict', str(p)])
        result.append({'path': str(p), 'sha256': sha(p), 'dependencies': parsed,
                       'LC_RPATH_count': 0, 'signature_verified': True,
                       'otool_L': deps, 'codesign_stdout': signature})
    return result


def task_qemu_processes():
    result = []
    for line in run(['ps', '-axo', 'pid=,comm=,args=']).splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2 and Path(parts[1]).name == 'qemu-system-aarch64':
            result.append(line)
    return result


def main():
    assert not RECEIPT.exists(), 'One-shot receipt exists; do not repeat deletion.'
    volume = volume_guard()
    assert SOURCE.is_dir() and not SOURCE.is_symlink()
    assert SOURCE.resolve() == SOURCE
    assert ARCHIVE.is_file() and not ARCHIVE.is_symlink()
    assert ARCHIVE.parent == HOST / 'downloads'
    assert sha(ARCHIVE) == '731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016'
    assert sha(SOURCE / 'hw/arm/virt.c') == 'c87dcfffc0934812284dba05fd525ab0f400b0021b3b90896371f455f6f3289d'
    dtc_head = run(['git', '-C', str(DTC), 'rev-parse', 'HEAD']).strip()
    assert dtc_head == 'b6910bec11614980a21e46fbccc35934b671bd81'
    assert run(['git', '-C', str(DTC), 'diff', '--binary', 'HEAD']) == ''
    dtc_status = run(['git', '-C', str(DTC), 'status', '--porcelain=v1'])
    assert dtc_status.strip() == '?? .meson-subproject-wrap-hash.txt'
    assert task_qemu_processes() == [], 'QEMU process present; defer source removal.'
    before = frozen_check()
    closure_before = closure_check()
    SUPPORT.mkdir(exist_ok=False)
    (SUPPORT / 'licenses').mkdir()
    patch_source = HOST / 'patches/fx3-esram-high-ddr.patch'
    patch = SUPPORT / 'qemu-original-to-fx3-complete.patch'
    shutil.copyfile(patch_source, patch)
    assert sha(patch) == '23052b0e06f3adc6a3500d22aad8ea51688a49fa6d09f0693fb435954d1fbba7'
    patch_dry_run = run(['patch', '--dry-run', '-R', '-p1', '-i', str(patch)], cwd=SOURCE)
    licenses = [
        (SOURCE / 'COPYING', 'QEMU-COPYING'),
        (SOURCE / 'COPYING.LIB', 'LGPL-2.1-standard-text'),
        (SOURCE / 'LICENSE', 'QEMU-LICENSE'),
        (DTC / 'BSD-2-Clause', 'DTC-BSD-2-Clause'),
        (DTC / 'GPL', 'DTC-GPL'),
        (DTC / 'README.license', 'DTC-README.license'),
        (HOST / 'deps/pcre2/10.49/LICENCE.md', 'PCRE2-LICENCE.md'),
        (HOST / 'deps/pcre2/10.49/COPYING', 'PCRE2-COPYING'),
    ]
    license_records = []
    for source, name in licenses:
        dest = SUPPORT / 'licenses' / name
        shutil.copyfile(source, dest)
        license_records.append({'path': str(dest), 'copied_from': str(source),
                                'sha256': sha(dest), 'bytes': dest.stat().st_size})
    deps_metadata = []
    for formula, version in [('glib', '2.90.1'), ('gettext', '1.0'), ('pcre2', '10.49')]:
        formula_file = HOST / f'deps/{formula}/{version}/.brew/{formula}.rb'
        text = formula_file.read_text()
        deps_metadata.append({'formula': formula, 'version': version,
                              'preserved_formula_path': str(formula_file),
                              'formula_sha256': sha(formula_file),
                              'upstream_source_url': re.search(r'^  url "([^"]+)"', text, re.M)[1],
                              'upstream_source_sha256': re.search(r'^  sha256 "([^"]+)"', text, re.M)[1]})
    write_json(SUPPORT / 'library-license-sources.json', {
        'glib': 'LGPL-2.1-or-later; recorded in preserved Homebrew formula',
        'libintl': 'LGPL-2.1-or-later; formula explicitly distinguishes libintl/libasprintf from gettext GPL tools',
        'pcre2': 'See preserved PCRE2-LICENCE.md and PCRE2-COPYING',
        'standard_LGPL_text_origin': 'QEMU COPYING.LIB, standard version 2.1 text; not represented as a copied GLib source member',
        'sources': deps_metadata, 'license_texts': license_records})
    write_json(SUPPORT / 'source-delta-audit.json', {
        'method': 'Read-only tar-member SHA256 comparison before cleanup, 2026-11-01; no archive extraction',
        'archive_regular_file_members_compared': 78695,
        'code_members_different': ['hw/arm/virt.c'],
        'current_changed_code_sha256': sha(SOURCE / 'hw/arm/virt.c'),
        'complete_patch': {'path': str(patch), 'sha256': sha(patch)},
        'patch_reverse_dry_run_exit': 0, 'patch_reverse_dry_run_stdout': patch_dry_run,
        'non_code_link_differences': [
            {'path': 'roms/edk2/EmulatorPkg/Unix/Host/X11IncludeHack',
             'tar_target': '/opt/X11/include', 'local_state': 'absent; external absolute symlink not extracted'},
            {'path': 'subprojects/libvduse/linux-headers/linux',
             'tar_target': '../../../linux-headers/linux/', 'local_target': '../../../linux-headers/linux'},
            {'path': 'subprojects/libvduse/standard-headers/linux',
             'tar_target': '../../../include/standard-headers/linux/', 'local_target': '../../../include/standard-headers/linux'}],
        'added_entry_count': 382,
        'added_entry_classification': {'subprojects/dtc_including_git_metadata': 354,
                                       'scripts/qapi_generated_pycache': 17,
                                       'scripts/tracetool_generated_pycache': 10,
                                       'subprojects/.wraplock': 1},
        'dtc_head': dtc_head, 'dtc_tracked_diff': '', 'dtc_status': dtc_status,
        'dtc_generated_wrap_hash_text': (DTC / '.meson-subproject-wrap-hash.txt').read_text(),
        'build_tree_deleted': False,
        'build_tree_note': 'Build products/cache preserved, including generated C, object files, original build metadata/logs and source symlinks. No original implementation is deleted from this tree.'})
    scopes = [stats(SOURCE), stats(ARCHIVE)]
    nested_dtc = stats(DTC)
    archived_sha = sha(ARCHIVE)
    volume_guard()
    shutil.rmtree(SOURCE)
    ARCHIVE.unlink()
    assert not SOURCE.exists() and not ARCHIVE.exists()
    after = frozen_check()
    closure_after = closure_check()
    assert before == after and closure_before == closure_after
    assert task_qemu_processes() == []
    readme = SUPPORT / 'README.md'
    readme.write_text('''# 本轮第三方源码清理说明

仅删除本轮 `host/sources/qemu-11.1.2`（含固定提交的内嵌 DTC）及 `host/downloads/qemu-11.1.2.tar.xz`。没有操作其他项目、旧材料、Sony 固件、原运行记录或正式交付包。

`qemu-original-to-fx3-complete.patch` 完整保存本轮唯一代码改动；对照源归档检查了 78,695 个普通文件成员。其余三项差异仅为一个未提取的绝对符号链接和两个尾斜杠规范化的相对链接。DTC 已跟踪文件无改动。来源 URL、版本、SHA 与 DTC commit 在上级回执和既有来源回执中。

保留 `host/build` 的编译产物及日志/元数据、`build-venv`、`deps`、`pkgconfig`、二进制 bottle 缓存。它们是本轮局部构建环境，不是正式运行包的依赖；`build` 中指向已清源码的符号链接会失效，恢复同版源码后才可重新构建。本轮未扩大清理到这些可复用缓存。

按固定 QEMU URL 重取并核 SHA 后，在原 `sources/qemu-11.1.2` 路径展开，应用本目录完整 patch；Meson 会按 `internal-dtc-receipt.json` 固定提交取 DTC。依赖来源以既有 `source-receipt.json` 和 `dtc-source-receipt.json` 为准。重建配置/命令与日志保留在 `configure-02-command.json`、`build-command.json`、`configure-02.log`、`build.log`；正式包重定位和重新签名过程另见封存的 `outputs/fx3-vm/metadata/`。清理后未执行重建，也未再次启动 VM。

`licenses/` 只新增许可证文本；`library-license-sources.json` 记录三份非系统动态库的许可与可重取来源。封存的 `outputs/fx3-vm` 及原 FX3 输入保持原 SHA。完整逐文件核对、Mach-O 相对路径闭包、无 LC_RPATH 与签名只读核验结果见上级清理回执。
''')
    support_files = [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size}
                     for p in sorted(SUPPORT.rglob('*')) if p.is_file()]
    receipt = {
        'status': 'COMPLETED_SOURCE_CLEANUP_RUNTIME_UNCHANGED',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'authorization': 'Parent supplied the coordinated closeout cleanup window; user AGENTS requires third-party source copies removed after recording URL/commit.',
        'volume': volume,
        'sources': [
            {'name': 'QEMU', 'version': '11.1.2',
             'url': 'https://download.qemu.org/qemu-11.1.2.tar.xz', 'sha256': archived_sha,
             'commit': None, 'identity': 'Official release archive, fixed SHA; not a Git checkout'},
            {'name': 'embedded DTC', 'url': 'https://gitlab.com/qemu-project/dtc.git',
             'commit': dtc_head}],
        'deleted_scopes': scopes,
        'nested_dtc_scope_included_in_qemu_totals_do_not_add_again': nested_dtc,
        'deleted_regular_file_count': sum(s['regular_files'] for s in scopes),
        'deleted_logical_regular_file_bytes': sum(s['regular_file_bytes'] for s in scopes),
        'byte_accounting': 'Logical st_size sum, not claimed APFS physical free-space delta; symlinks recorded separately; directories include each deleted root.',
        'deleted_paths_verified_absent': [str(SOURCE), str(ARCHIVE)],
        'retained': [
            {'path': str(HOST / p), 'reason': reason} for p, reason in [
                ('patches', 'Original own model patches retained unchanged'),
                ('source-cleanup-support', 'Independent complete patch, source audit, license texts and reconstruction notes'),
                ('build', 'Original compile products, generated build files, logs and metadata; retained local cache; no formal runtime dependency'),
                ('build-venv', 'Local Meson/Ninja/Python build tools'),
                ('deps', 'Local binary build dependencies and tool cache, original formulas/license metadata'),
                ('pkgconfig', 'Local build dependency configuration'),
                ('downloads', 'Only binary Homebrew bottle/tool caches remain; no QEMU source archive'),
                ('metadata', 'Pinned download/dependency source metadata'),
                ('runs', 'All original VM run logs, raw traces, observations and receipts')]],
        'preserved_support_files': support_files,
        'frozen_files_before': before, 'frozen_files_after': after,
        'frozen_files_all_identical': True,
        'runtime_macho_closure_after': closure_after,
        'runtime_non_system_macho_file_count': len(closure_after),
        'runtime_dependency_on_deleted_sources': False,
        'runtime_rerun_performed': False,
        'task_qemu_processes_remaining': [],
        'original_receipts_notes_modified': False,
        'reconstruction': 'Fixed URL/SHA plus complete saved patch and pinned DTC commit; see source-cleanup-support/README.md. No post-cleanup rebuild claimed.'}
    write_json(RECEIPT, receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': str(RECEIPT),
                      'deleted_files': receipt['deleted_regular_file_count'],
                      'deleted_logical_bytes': receipt['deleted_logical_regular_file_bytes'],
                      'qemu_sha256': sha(OUT / 'bin/qemu-system-aarch64'),
                      'frozen_files_checked': len(after)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
