#!/usr/bin/env python3
"""Combine the proven service guest with SHA-pinned same-FX3 AP resources."""
from pathlib import Path
import datetime
import hashlib
import json
import plistlib
import stat
import struct
import subprocess
from cpio_audit import parse, audit

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'original-uipc'
DEST = ROOT / 'ap10-full-v4'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert vol['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert not DEST.exists(), 'Do not overwrite a prior AP build'
    DEST.mkdir()
    original_candidate = json.loads((SOURCE / 'candidate09.json').read_text())
    baseline_cpio = Path(original_candidate['initrd']['path'])
    assert sha(baseline_cpio) == original_candidate['initrd']['sha256']
    report, contents = parse(baseline_cpio)
    entries = {m['path']: {'name': m['path'], 'mode': int(m['mode'], 8),
                           'rdev_major': m['rdev_major'], 'rdev_minor': m['rdev_minor'],
                           'data': contents[m['path']], 'source': 'candidate09'}
               for m in report['members']}
    manifest_path = SOURCE / 'ap-projection/full-v4/projection-manifest-full-v4.json'
    manifest_sha = sha(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest['status'] == 'FULL_ORIGINAL_FILES_PREPARED_NOT_EXECUTED'
    assert manifest_sha == '3e295b9f0b362754c46ec507abeb8a607aa328a166eb3b89e13a51672f91aa77'
    collisions = []
    sources = []
    for m in manifest['members']:
        name = m['name']
        assert name and not name.startswith('/') and '..' not in Path(name).parts
        mode = m['mode']
        if m['type'] == 'regular':
            path = Path(m['local_file'])
            assert path.is_file() and not path.is_symlink()
            assert path.stat().st_size == m['bytes'] and sha(path) == m['sha256']
            entry = {'name': name, 'mode': mode, 'file': path, 'uid': m.get('uid', 0),
                     'gid': m.get('gid', 0), 'mtime': m.get('mtime', 0),
                     'size': m['bytes'], 'sha256': m['sha256'], 'source': str(path)}
            sources.append({'name': name, 'path': str(path), 'sha256': m['sha256'], 'bytes': m['bytes'],
                            'source_partition': m.get('partition'), 'source_inode': m.get('inode'),
                            'source_uid': m.get('uid'), 'source_gid': m.get('gid'),
                            'source_nlink': m.get('nlink'),
                            'guest_inode_policy': 'Independent sequential newc inode, nlink1; no SHA hardlink dedup'})
        elif m['type'] == 'symlink':
            payload = bytes.fromhex(m['data_hex'])
            assert hashlib.sha256(payload).hexdigest() == m['sha256']
            entry = {'name': name, 'mode': mode, 'data': payload, 'source': 'original symlink payload only'}
        elif m['type'] == 'directory':
            entry = {'name': name, 'mode': mode, 'data': b'', 'source': 'original parent directory'}
        else:
            raise ValueError(m['type'])
        if name in entries:
            old = entries[name]
            assert stat.S_IFMT(old['mode']) == stat.S_IFMT(mode)
            expected = entry.get('sha256', hashlib.sha256(entry.get('data', b'')).hexdigest())
            same_content = hashlib.sha256(old['data']).hexdigest() == expected
            if not same_content and stat.S_ISLNK(mode):
                # Original symlink payloads may differ from the minimal guest's
                # equivalent aliases. Keep the exact full-source guest link.
                entries[name] = entry
                collisions.append({'name': name, 'same_bytes': False, 'kept': 'full original symlink payload',
                                   'baseline_target_hex': old['data'].hex(),
                                   'original_target_hex': entry['data'].hex()})
                continue
            assert same_content, ('Projection content mismatch', name)
            collisions.append({'name': name, 'same_bytes': True, 'baseline_mode': oct(old['mode']),
                               'projected_mode': oct(mode), 'kept': 'baseline byte/mode'})
        else:
            entries[name] = entry
    # The source proof binds these exact argv and documents fork/execve inheritance.
    launch_proof = SOURCE / 'original-bootin-launch-contract.json'
    assert launch_proof.is_file()
    init = contents['init'].decode()
    start = init.index(' echo FX3_IM_AFTER_ORIGINAL_UIPC_BEGIN\n')
    end = init.index('\nelse\n echo FX3_UIPC_DEPENDENCY_OR_NODE_NOT_READY', start)
    natural = ''' echo FX3_AP_NATURAL_BOOTIN_BEGIN
 echo FX3_AP_ARGV_target_qemu_WITH_TRAILING_SPACE_dmode3
 LD_PRELOAD=/simulation/ioctl-trace.so /usr/bin/bootin.elf 'target=qemu ' dmode=3 &
 launcher=$!
 echo FX3_AP_BOOTIN_LAUNCH_PID=$launcher
 for turn in 1 2 3; do
  /bin/busybox sleep 10
  echo FX3_AP_SNAPSHOT_${turn}_BEGIN
  /bin/busybox ps
  /bin/busybox ls -l /proc/[0-9]*/exe
  for procdir in /proc/[0-9]*; do
   if /bin/busybox grep -q '/usr/bin/im.elf' "$procdir/maps" 2>/dev/null; then
    echo FX3_AP_IM_PROCESS=${procdir##*/}
    /bin/busybox cat "$procdir/cmdline"
    echo
    /bin/busybox cat "$procdir/status" "$procdir/maps" "$procdir/wchan"
   fi
  done
  /bin/busybox ls -l /proc/osal /tmp /setting
  echo FX3_AP_SNAPSHOT_${turn}_END
 done
 echo FX3_AP_NATURAL_OBSERVATION_END
'''
    init = init[:start] + natural + init[end:]
    # Three ABI gates remain; no independently executed updater/Jiritsu payload.
    assert 'FX3_TRACE_ABI_VERIFY_RC' in init
    assert "'target=qemu ' dmode=3" in init
    assert 'kill -TERM "$p"' not in init
    entries['init']['data'] = init.encode()
    entries['init']['source'] = 'new reviewed natural bootin init, based on candidate09'
    for name in list(entries):
        for parent in Path(name).parents:
            if str(parent) == '.':
                continue
            if str(parent) not in entries:
                entries[str(parent)] = {'name': str(parent), 'mode': 0o40755, 'data': b'',
                                        'source': 'explicit missing parent directory'}
    ordered = sorted(entries.values(), key=lambda e: (len(Path(e['name']).parts),
                     not stat.S_ISDIR(e['mode']), e['name']))
    archive = DEST / 'fx3-original-ap10.cpio'
    partial = DEST / 'fx3-original-ap10.cpio.partial'
    with partial.open('xb') as f:
        def pad():
            f.write(b'\0' * ((-f.tell()) % 4))
        for inode, e in enumerate(ordered, 1):
            name = e['name'].encode() + b'\0'
            size = e.get('size', len(e.get('data', b'')))
            fields = [inode, e['mode'], e.get('uid', 0), e.get('gid', 0), 2 if stat.S_ISDIR(e['mode']) else 1,
                      e.get('mtime', 0), size, 0, 0, e.get('rdev_major', 0), e.get('rdev_minor', 0), len(name), 0]
            f.write(b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name)
            pad()
            if 'file' in e:
                h = hashlib.sha256()
                actual = 0
                with e['file'].open('rb') as src:
                    for chunk in iter(lambda: src.read(1024 * 1024), b''):
                        f.write(chunk); h.update(chunk); actual += len(chunk)
                assert actual == size and h.hexdigest() == e['sha256']
            else:
                f.write(e['data'])
            pad()
        name = b'TRAILER!!!\0'
        fields = [len(ordered) + 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(name), 0]
        f.write(b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name)
        pad()
    partial.replace(archive)
    assert sha(manifest_path) == manifest_sha
    dtb_source = Path(original_candidate['dtb']['path'])
    assert sha(dtb_source) == original_candidate['dtb']['sha256']
    dtb_bytes = bytearray(dtb_source.read_bytes())
    h = struct.unpack_from('>10I', dtb_bytes)
    off = h[2]; stack = []; updated = 0
    while off < h[2] + h[9]:
        token = struct.unpack_from('>I', dtb_bytes, off)[0]; off += 4
        if token == 1:
            end = dtb_bytes.index(0, off); stack.append(bytes(dtb_bytes[off:end]).decode()); off = (end + 4) & ~3
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name_off = struct.unpack_from('>II', dtb_bytes, off); off += 8
            name_end = dtb_bytes.index(0, h[3] + name_off)
            name = bytes(dtb_bytes[h[3] + name_off:name_end]).decode()
            if stack == ['', 'chosen'] and name == 'linux,initrd-end':
                assert length == 8
                struct.pack_into('>Q', dtb_bytes, off, 0x408000000 + archive.stat().st_size); updated += 1
            off = (off + length + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            break
        else:
            raise ValueError(token)
    assert updated == 1 and 0x408000000 + archive.stat().st_size < 0x480000000
    dtb = DEST / 'virt-original-ap10.dtb'; dtb.write_bytes(dtb_bytes)
    cpio_report = audit(archive, Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio'))
    assert cpio_report['safe_to_unpack']
    (DEST / 'cpio-audit.json').write_text(json.dumps(cpio_report, ensure_ascii=False, indent=2) + '\n')
    (DEST / 'init-reviewed.sh').write_text(init)
    candidate = {'dtb': {'path': str(dtb), 'sha256': sha(dtb)},
                 'initrd': {'path': str(archive), 'sha256': sha(archive)},
                 'required_markers': ['FX3_CPUSET_READY', 'FX3_BACKUP_INSMOD_RC=0',
                                      'FX3_ULOGIO_INSMOD_RC=0', 'FX3_AP_NATURAL_BOOTIN_BEGIN'],
                 'scope': 'Natural original FX3 bootin target=qemu[space] dmode=3 with full original rootfs7/usr15/appli projection. File presence is not execution. Five original service modules only preloaded. No manufactured menu/ACK, no physical devices/network/host disk. Original library idle init allowed; independent updater/Jiritsu workflow not invoked.',
                 'known_unclosed_layout': 'DMM/LIRO and CP fixed RAM spans not accepted by this probe; failures may be absent service/hardware/layout, not evidence of ABI incompatibility. No new timer/DMA/DMM model added.'}
    (DEST / 'candidate10.json').write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + '\n')
    result = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'baseline_candidate09': str(SOURCE / 'candidate09.json'),
              'baseline_candidate09_sha256': sha(SOURCE / 'candidate09.json'),
              'projection_manifest': str(manifest_path), 'projection_manifest_sha256': manifest_sha,
              'bootin_contract': str(launch_proof), 'bootin_contract_sha256': sha(launch_proof),
              'original_projected_regular_sources': sources, 'same_content_collisions': collisions,
              'guest_entries': len(ordered), 'initrd_bytes': archive.stat().st_size,
              'initrd_start': hex(0x408000000), 'initrd_end': hex(0x408000000 + archive.stat().st_size),
              'FDT_change': 'Exactly chosen linux,initrd-end 8 bytes; reserve and all other bytes unchanged',
              'candidate': candidate, 'guest_started': False,
              'shader_sensor_DMM_models_added': False,
              'original_symlinks_created_on_host': False}
    result['guest_regular_inode_policy'] = 'Unique sequential newc ino and nlink1 per guest file; input SHA names deduplicate only host payload sources. Source uid/gid/inode namespace retained in provenance.'
    (DEST / 'build-receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'candidate': str(DEST / 'candidate10.json'), 'entries': len(ordered),
                      'initrd_bytes': archive.stat().st_size, 'cpio_sha256': sha(archive),
                      'dtb_sha256': sha(dtb), 'sources_verified': len(sources),
                      'CPIO_parent_and_original_ELF_gate_passed': True}, indent=2))


if __name__ == '__main__':
    main()
