#!/usr/bin/env python3
"""Fixed-path offline drafts only; no transport, auth or camera-file APIs."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import posixpath
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
FIXED_TARGETS = ('/usr/lib/libsencore.so', '/usr/lib/libJiritsu.so')


def main():
    source = BASE / 'stage134-backup-reader-scope-and-service-extension/audit_readers.py'
    manifest = json.loads((source.parent / 'final-receipt.json').read_text())
    pin = next(p for p in manifest['files'] if p['path'] == source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest() == pin['sha256']
    spec = importlib.util.spec_from_file_location('prior_static_reader', source)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    image = prior.Image('libJiritsu.so', 'bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9')
    functions = [image.function(n) for n in ('adj_cmd_set_file_path', 'get_access_filename',
        '_ZN11CFileAccess4openEPKci', '_ZN11CFileAccess4readEPvm',
        '_ZN11CFileAccess4statEPKcP13tag_FILE_INFO', '_ZN6DmmMgr13CheckUnitTypeEm',
        '_ZN6DmmMgr9dmm_allocEj')]
    checked = []
    for address, name in [(0x93a8, 'snprintf'), (0xeb7c, 'strncmp'), (0xed00, 'open'),
                          (0xef6c, 'read'), (0xfb08, 'strncmp')]:
        checked.append(image.expect_call(address, name))
    assert image.string(0x11d7e) == '%s/%s'
    assert image.string(0x11dd7) == '%s'
    assert image.string(0x31375) == '/mnt'
    assert image.instructions(0xeb80, 4)[0]['asm'] == 'cbnz w0, #0xecd4'
    assert image.instructions(0xecd8, 4)[0]['asm'] == 'mov x2, x23'
    assert image.instructions(0xecf4, 4)[0]['asm'] == 'mov w1, w20'
    assert image.instructions(0x938c, 4)[0]['asm'] == 'mov x3, x22'
    # The native setter only converts backslashes and rejects selected control/
    # delimiter characters. Dot bytes are not rejected by its reviewed bit test.
    denied_mask = (0x1000 << 32) | 0x2400
    assert not (denied_mask >> ord('.') & 1)
    codec = BASE / 'stage9-protocol/host/offline_codec.py'
    assert sha256(codec.read_bytes()).hexdigest() == '38d2c77bcf4403f600726eb88868d714e2186627564653d8578cef4e98e23977'
    drafts = []
    for target in FIXED_TARGETS:
        local = BASE / 'stage2/extraction/files/nflasha15/lib' / Path(target).name
        raw = local.read_bytes()
        relative = '../..' + target
        assembled = '/tmp/jiritsu/' + relative
        assert posixpath.normpath(assembled) == target and not assembled.startswith('/mnt')
        assert len(relative) <= 510 and len(raw) + 4 <= 0x4fffff
        arguments = b'\0' + relative.encode('ascii') + b'\0'
        payload = struct.pack('<HH', 0x1001, 15) + arguments
        setpath = struct.pack('<IHHBBBB', len(payload), 0x40, 1, 0, 0, 0, 0) + payload
        payload = struct.pack('<HH', 0x1001, 17) + b'\0\xff\0'
        read = struct.pack('<IHHBBBB', len(payload), 0x40, 2, 0, 0, 0, 0) + payload
        drafts.append({'fixed_target': target, 'source_reference_bytes': len(raw),
            'source_reference_sha256': sha256(raw).hexdigest(), 'native_global_path_candidate': relative,
            'native_assembled_path_candidate': assembled, 'Linux_lexical_resolution_candidate': target,
            'expected_source_size_class_for_N_plus4': '0x304',
            'setpath_frame_hex_offline_only': setpath.hex(), 'read_frame_hex_offline_only': read.hex(),
            'live_send_implemented_or_permitted': False})
    result = {'status': 'PASS_STATIC_DIRECT_POSIX_BRANCH_AND_FIXED_PATH_DRAFT_NOT_READY_TO_SEND',
        'original_Jiritsu_sha256': sha256(image.raw).hexdigest(), 'functions': functions,
        'checked_PLT_targets': checked, 'fixed_read_drafts': drafts,
        'size_class_static_ranges': [
            {'max_inclusive': 0x4fffff, 'unit': '0x304'}, {'max_inclusive': 0xefffff, 'unit': '0x3c8'},
            {'max_inclusive': 0x31fffff, 'unit': '0x288'}, {'max_inclusive': 0x63fffff, 'unit': '0x307'},
            {'above_last': True, 'result': '0xffffffff, not an admitted dmm_alloc unit'}],
        'source_Main_appFw_so_bytes': (BASE / 'stage2/extraction/files/nflasha15/lib/appFw.so').stat().st_size,
        'full_MAIN_application_backup_not_substituted_by_two_library_drafts': True,
        'path_resolution_reference': 'https://raw.githubusercontent.com/mkerrisk/man-pages/master/man7/path_resolution.7',
        'old_codec_unchanged': True,
        'actual_body_path_resolution_mounts_symlinks_or_file_sizes_verified': False,
        'admission_gaps': [
            'A lexical path and libc open branch do not establish current process root/mount/symlink state.',
            'No device-side requested length bound is added by these bytes; coarse DMM classes do not prove current capacity/free memory.',
            'The existing service mount and conditional auth history/log side effects remain.',
            'Driver ownership, exact FX3 wire framing/replies, bounded timeouts and orderly stop/join remain unverified.',
            'No active read transport is implemented or released; no camera/file/driver/auth operations authorised by this draft.'],
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'system-read-admission-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'functions_reviewed': len(functions),
                      'fixed_inert_drafts': len(drafts), 'live_send': False,
                      'MAIN_app_reference_bytes': result['source_Main_appFw_so_bytes']}))


if __name__ == '__main__':
    main()
