#!/usr/bin/env python3
"""Offline, guarded FX3 timing CPIO derivation. Never starts a VM."""
from pathlib import Path
import hashlib
import importlib.util
import json
import plistlib
import struct
import subprocess

HERE = Path(__file__).resolve().parent
USABILITY = HERE.parent
ROOT = USABILITY.parents[3]
OLD = USABILITY / 'vmopt-20261103-try2-mss-all-v3'
BUILD = USABILITY / 'mss-all-key-contrast/passive-timing-next/build'
NEW = HERE / 'vmopt-20261103-try2-passive-timing-v4'
BASE_SHA = '2382063eacb5f185e8553c2596be2c644654efe7234adc1e4578f7464ab99a05'
REPLACEMENTS = {
    'simulation/fx3-rm-empty-provider-v3-setup.so': ('rm-timing.so', '6acb0e52e610cb0d13721f38fcf1c7c27b0e5a48e687d7a4feda5fde9f9bcd14', 'ff38874e128d517147b1712588bf68d24412dae781a390eaa8bd7d230c3c1707'),
    'simulation/fx3-preset-context-v2-screen.so': ('ap-timing.so', 'eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170', '52ed3b5b2cdadc46e1c78c596a60d06a3fd865bb9bb5420a0bb5f2492df12392'),
    'simulation/fx3-osd-headless-v5.so': ('osd-timing.so', '816bbf9019ff422c2e24ca5a601a41dc144fa82e7baf39a563d638a55a841dbb', '8023300a7b02e69cb1ea39c1489214cabce403cc3cab39058ac00bf06cd2a636'),
}

def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()

def aligned(n):
    return (n + 3) & ~3

def copy_span(src, dst, amount):
    while amount:
        data = src.read(min(amount, 1 << 20))
        if not data:
            raise ValueError('truncated source CPIO')
        dst.write(data)
        amount -= len(data)

def member_rows(path):
    rows = []
    with path.open('rb') as src:
        while True:
            head = src.read(110)
            if head[:6] not in (b'070701', b'070702') or len(head) != 110:
                raise ValueError('invalid newc header')
            fields = [int(head[6 + i * 8:14 + i * 8], 16) for i in range(13)]
            name_bytes = src.read(fields[11])
            if not name_bytes.endswith(b'\0'):
                raise ValueError('invalid member name')
            name = name_bytes[:-1].decode()
            src.seek(aligned(110 + fields[11]) - (110 + fields[11]), 1)
            data_hash = hashlib.sha256()
            remaining = fields[6]
            while remaining:
                data = src.read(min(remaining, 1 << 20))
                if not data:
                    raise ValueError('truncated member')
                data_hash.update(data)
                remaining -= len(data)
            src.seek(aligned(fields[6]) - fields[6], 1)
            if name == 'TRAILER!!!':
                if fields[6]:
                    raise ValueError('nonempty trailer')
                break
            rows.append({'name': name, 'mode': fields[1], 'size': fields[6], 'sha256': data_hash.hexdigest()})
    return rows

def derive_cpio(source, target):
    seen = set()
    with source.open('rb') as src, target.open('xb') as dst:
        while True:
            head = src.read(110)
            if head[:6] not in (b'070701', b'070702') or len(head) != 110:
                raise ValueError('invalid newc header')
            fields = [int(head[6 + i * 8:14 + i * 8], 16) for i in range(13)]
            nlen, size = fields[11], fields[6]
            name_bytes = src.read(nlen)
            if nlen < 1 or not name_bytes.endswith(b'\0'):
                raise ValueError('invalid member name')
            name = name_bytes[:-1].decode()
            name_pad = src.read(aligned(110 + nlen) - (110 + nlen))
            if name in REPLACEMENTS:
                if name in seen:
                    raise ValueError('duplicate replacement member')
                seen.add(name)
                filename, old_sha, new_sha = REPLACEMENTS[name]
                old_hash = hashlib.sha256()
                remaining = size
                while remaining:
                    chunk = src.read(min(remaining, 1 << 20))
                    if not chunk:
                        raise ValueError('truncated old member')
                    old_hash.update(chunk)
                    remaining -= len(chunk)
                if old_hash.hexdigest() != old_sha:
                    raise ValueError('old member SHA mismatch: ' + name)
                src.read(aligned(size) - size)
                replacement = BUILD / filename
                if sha(replacement) != new_sha:
                    raise ValueError('new SO SHA mismatch: ' + name)
                new_size = replacement.stat().st_size
                dst.write(head[:54] + f'{new_size:08x}'.encode() + head[62:])
                dst.write(name_bytes)
                dst.write(name_pad)
                with replacement.open('rb') as inp:
                    copy_span(inp, dst, new_size)
                dst.write(b'\0' * (aligned(new_size) - new_size))
            else:
                dst.write(head)
                dst.write(name_bytes)
                dst.write(name_pad)
                copy_span(src, dst, aligned(size))
            if name == 'TRAILER!!!':
                copy_span(src, dst, source.stat().st_size - src.tell())
                break
    if seen != set(REPLACEMENTS):
        raise ValueError('missing replacement members: ' + repr(set(REPLACEMENTS)-seen))

def main():
    vol = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if vol.get('VolumeUUID') != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('volume UUID mismatch')
    if NEW.exists():
        raise FileExistsError(NEW)
    base_manifest = OLD / 'candidate.json'
    if sha(base_manifest) != BASE_SHA:
        raise ValueError('base manifest SHA mismatch')
    candidate = json.loads(base_manifest.read_text())
    source_cpio = Path(candidate['initrd']['path'])
    if source_cpio != OLD / 'guest.cpio' or sha(source_cpio) != candidate['initrd']['sha256']:
        raise ValueError('base CPIO identity mismatch')
    source_dtb = Path(candidate['dtb']['path'])
    if source_dtb != OLD / 'guest.dtb' or sha(source_dtb) != candidate['dtb']['sha256']:
        raise ValueError('base DTB identity mismatch')
    seed = candidate['native_Backup_seed']
    if sha(seed['path']) != seed['sha256']:
        raise ValueError('English seed SHA mismatch')
    NEW.mkdir(parents=False)
    output = NEW / 'guest.cpio'
    derive_cpio(source_cpio, output)
    before, after = member_rows(source_cpio), member_rows(output)
    if [x['name'] for x in before] != [x['name'] for x in after]:
        raise ValueError('member order changed')
    changed = []
    for a, b in zip(before, after):
        if a['mode'] != b['mode']:
            raise ValueError('mode changed: ' + a['name'])
        if a['sha256'] != b['sha256']:
            changed.append({'member': a['name'], 'old_sha256': a['sha256'], 'new_sha256': b['sha256'], 'old_size': a['size'], 'new_size': b['size']})
    if {x['member'] for x in changed} != set(REPLACEMENTS):
        raise ValueError('unexpected changed payload')
    fdt_path = ROOT / 'fx3-audit/prepare_virt_dtb.py'
    spec = importlib.util.spec_from_file_location('fx3_fdt', fdt_path)
    fdt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fdt)
    tree, _, reserve, meta = fdt.parse(source_dtb.read_bytes())
    chosen = next(node for kind, node in tree['items'] if kind == 'node' and node['name'] == 'chosen')
    old_end = 0x440000000 + source_cpio.stat().st_size
    old_values = [value for kind, (key, value) in chosen['items'] if kind == 'prop' and key == 'linux,initrd-end']
    if old_values != [struct.pack('>Q', old_end)]:
        raise ValueError('source DTB initrd-end does not match source CPIO')
    new_end = 0x440000000 + output.stat().st_size
    chosen['items'] = [(kind, (key, struct.pack('>Q', new_end)) if kind == 'prop' and key == 'linux,initrd-end' else value) for kind, value in chosen['items'] for key in ([value[0]] if kind == 'prop' else [None])]
    dtb = NEW / 'guest.dtb'
    dtb.write_bytes(fdt.encode(tree, reserve, meta))
    old_dtb_bytes = source_dtb.read_bytes()
    new_dtb_bytes = dtb.read_bytes()
    if len(old_dtb_bytes) != len(new_dtb_bytes) or old_dtb_bytes.replace(struct.pack('>Q', old_end), struct.pack('>Q', new_end), 1) != new_dtb_bytes:
        raise ValueError('DTB changed outside initrd-end')
    candidate['initrd'] = {'path': str(output), 'sha256': sha(output)}
    candidate['dtb'] = {'path': str(dtb), 'sha256': sha(dtb)}
    candidate['passive_timing_contract'] = {'base_candidate': str(base_manifest), 'base_sha256': BASE_SHA, 'changed_members': changed, 'clock_id': 1, 'runtime_validated': False, 'English_seed_sha256': seed['sha256']}
    manifest = NEW / 'candidate.json'
    manifest.write_text(json.dumps(candidate, indent=2) + '\n')
    receipt = {'candidate': str(manifest), 'candidate_sha256': sha(manifest), 'base_candidate_sha256': BASE_SHA, 'initrd_sha256': sha(output), 'dtb_sha256': sha(dtb), 'changed_members': changed, 'other_member_payloads_and_modes_unchanged': True, 'member_count': len(after), 'initrd_end_old': hex(old_end), 'initrd_end_new': hex(new_end), 'dtb_only_initrd_end_changed': True, 'seed_sha256': seed['sha256'], 'QEMU_started': False, 'guest_validated': False}
    (NEW / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
