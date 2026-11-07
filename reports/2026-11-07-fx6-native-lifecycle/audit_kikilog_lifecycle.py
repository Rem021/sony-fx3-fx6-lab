#!/usr/bin/env python3
"""Read-only BYOF check of Candidate 290's device and native lifecycle contract.

No firmware is extracted or executed. Requires pyelftools. Reuses the previous
full newc member index, including records following TRAILER!!!. This is a
static contract audit, not proof that any guest initializer ran.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import mmap
from pathlib import Path
import plistlib
import struct
import subprocess

from elftools.elf.elffile import ELFFile

EXPECTED = {
    "usr/lib/libInfraKikiLogGenerator.so": "be7abc37ceb019b203a3853eba633d5d703d86d9a24ec2a6081b74873dd71917",
    "usr/kmod/kikilog.ko": "78fb1e9d73a729c99781af7a72a8384f662342f7878b7c931bb8cc96cbdbb3d2",
    "kmod/devno.ko": "cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23",
}
IMDB_SHA = "a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896"


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Elf:
    def __init__(self, data):
        self.data = data
        self.elf = ELFFile(io.BytesIO(data))
        if self.elf['e_machine'] != 'EM_AARCH64':
            raise ValueError("expected AArch64")

    def read(self, address, count):
        for s in self.elf.iter_segments():
            if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= address and address + count <= s['p_vaddr'] + s['p_filesz']:
                off = s['p_offset'] + address - s['p_vaddr']
                return self.data[off:off + count]
        raise ValueError(f"unbacked VMA {address:#x}")

    def string(self, address):
        return self.read(address, 96).split(b'\0', 1)[0].decode('ascii')

    def call_symbol(self, address):
        word = struct.unpack('<I', self.read(address, 4))[0]
        if word & 0xfc000000 != 0x94000000:
            raise ValueError('expected direct BL to PLT')
        imm = word & 0x3ffffff
        if imm & 0x2000000:
            imm -= 0x4000000
        target = address + imm * 4
        symbols = list(self.elf.get_section_by_name('.dynsym').iter_symbols())
        base = self.elf.get_section_by_name('.plt')['sh_addr'] + 32
        for i, rel in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations()):
            if base + i * 16 == target:
                return symbols[rel['r_info_sym']].name
        raise ValueError('BL target is not a known PLT entry')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--fx6-imdb', type=Path, required=True)
    args = ap.parse_args()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if volume.get('VolumeUUID') != 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('external volume identity mismatch')
    helper = Path(__file__).resolve().parent.parent / '2026-11-07-fx6-parallel-native-ui' / 'inspect_cpio_binding.py'
    spec = importlib.util.spec_from_file_location('binding', helper)
    binding = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(binding)
    raw_manifest = args.manifest.read_bytes()
    manifest = json.loads(raw_manifest)
    cpio = Path(manifest['initrd']['path'])
    before = cpio.stat()
    with cpio.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
        if digest(data)['sha256'] != manifest['initrd']['sha256'] or len(data) != manifest['initrd']['bytes']:
            raise ValueError('container binding mismatch')
        histories, trailers = binding.scan(data)
        payloads = {}
        for name in (*EXPECTED, 'init', 'usr/lib/libIMDB.so'):
            versions = histories.get(name)
            if versions:
                row = versions[-1]
                payloads[name] = data[row['offset']:row['offset'] + row['bytes']]
        for name, expected in EXPECTED.items():
            if digest(payloads[name])['sha256'] != expected:
                raise ValueError(f'{name}: this contract applies only to the pinned input')
    after = cpio.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or args.manifest.read_bytes() != raw_manifest:
        raise ValueError('inputs changed during read')
    kiki = Elf(payloads['usr/lib/libInfraKikiLogGenerator.so'])
    if struct.unpack('<i', kiki.read(0x162b0, 4))[0] != -1:
        raise ValueError('Kikilog initial fd differs')
    # Assert the exact branch between original initialization and callback use.
    for address, expected in {0x2988: 0xb9033c20, 0x2998: 0xb942b000,
                              0x390c: 0xb942b260, 0x3918: 0x52800041}.items():
        if struct.unpack('<I', kiki.read(address, 4))[0] != expected:
            raise ValueError(f'Kikilog instruction mismatch at {address:#x}')
    device_path = kiki.string(0x4798)
    if device_path != '/dev/usb/kikilog':
        raise ValueError('Kikilog device path differs')
    low, high = struct.unpack('<II', kiki.read(0x2990, 8))
    if low & 0xff80001f != 0xd2800001 or high & 0xff80001f != 0xf2800001:
        raise ValueError('callback command is not the expected MOVZ/MOVK pair')
    callback_command = ((low >> 5) & 0xffff) | (((high >> 5) & 0xffff) << (((high >> 21) & 3) * 16))
    if callback_command != 0x80044a10 or kiki.call_symbol(0x299c) != 'ioctl' or kiki.call_symbol(0x3920) != 'open':
        raise ValueError('open/ioctl callback contract differs')
    # The module references a specific descriptor in the actual devno provider.
    module = Elf(payloads['usr/kmod/kikilog.ko']).elf
    syms = list(module.get_section_by_name('.symtab').iter_symbols())
    refs = [(r['r_offset'], r['r_addend']) for sec in module.iter_sections()
            if sec['sh_type'] == 'SHT_RELA' and sec.name == '.rela.init.text'
            for r in sec.iter_relocations() if syms[r['r_info_sym']].name == 'udif_devnodes']
    if refs != [(0x88, 624)]:
        raise ValueError('Kikilog devnode relocation differs')
    # Match the actual loaded kernel handler, not the donor's different module.
    text = module.get_section_by_name('.text').data()
    kernel_low, kernel_high = struct.unpack_from('<II', text, 0xfd8)
    kernel_command = ((kernel_low >> 5) & 0xffff) | (((kernel_high >> 5) & 0xffff) << 16)
    arg_load, state_load, id_store = struct.unpack_from('<III', text, 0x11fc)
    if kernel_command != callback_command or arg_load != 0xf9400421 or id_store != 0xb903f001:
        raise ValueError('kernel callback-ID scalar handling differs')
    devno = Elf(payloads['kmod/devno.ko']).elf
    devsyms = list(devno.get_section_by_name('.symtab').iter_symbols())
    sym = next(s for s in devsyms if s.name == 'udif_devnodes')
    row = sym['st_value'] + refs[0][1]
    section = devno.get_section(sym['st_shndx'])
    kind, major, minor, count = struct.unpack_from('<HHHH', section.data(), row + 8)
    name_refs = [r for sec in devno.iter_sections()
                 if sec['sh_type'] == 'SHT_RELA' and sec['sh_info'] == sym['st_shndx']
                 for r in sec.iter_relocations() if r['r_offset'] == row]
    if len(name_refs) != 1:
        raise ValueError('ambiguous devnode name relocation')
    ref = name_refs[0]
    rsym = devsyms[ref['r_info_sym']]
    raw_names = devno.get_section(rsym['st_shndx']).data()
    noff = rsym['st_value'] + ref['r_addend']
    name = raw_names[noff:raw_names.index(b'\0', noff)].decode()
    if (name, kind, major, minor, count) != ('usb/kikilog', 0, 248, 10, 1):
        raise ValueError('devnode contract differs')
    imdb_data = args.fx6_imdb.read_bytes()
    if digest(imdb_data)['sha256'] != IMDB_SHA:
        raise ValueError('FX6 lifecycle reference hash mismatch')
    imdb = Elf(imdb_data)
    lifecycle = []
    for base, library, initializer in [(0x1f198, 'libInfraKikiLogGenerator.so', 'KikiLogGenerator_init'),
                                        (0x1f270, 'libMWF.so', 'MWF_Init')]:
        ptrs = struct.unpack('<QQ', imdb.read(base + 0x10, 16))
        if tuple(imdb.string(v) for v in ptrs) != (library, initializer):
            raise ValueError('lifecycle record mismatch')
        lifecycle.append({'record_vma': hex(base), 'library': library, 'initializer': initializer})
    result = {'schema': 'fx6-kikilog-static-lifecycle-contract-v1',
        'manifest': {'path': str(args.manifest), **digest(raw_manifest)},
        'initrd': manifest['initrd'], 'archive_trailers': trailers,
        'candidate_members': {n: digest(b) for n, b in payloads.items()},
        'fx6_lifecycle_reference': {'path': str(args.fx6_imdb), **digest(imdb_data)},
        'lifecycle_records': lifecycle,
        'device': {'path': device_path, 'udif_index': 39, 'kind': 'character',
                   'major': major, 'minor': minor, 'count': count,
                   'archive_has_node': 'dev/usb/kikilog' in histories},
        'kikilog_user_abi': {'fd_slot': '0x162b0', 'initial_fd': -1,
            'init_function': 'KikiLogGenerator_init', 'open_path_function': '0x38f8',
            'callback_function': '0x2978', 'callback_ioctl': hex(callback_command),
            'open_and_ioctl_plt_checked': True, 'loaded_kernel_scalar_arg_handler_checked': True,
            'callback_arg': '32-bit message/queue ID passed as scalar, not a callback function pointer',
            'nonzero_ioctl_return_maps_to': -127},
        'boundary': 'No guest execution. Archive node absence does not prove absence after devtmpfs/mdev/runtime creation. Lifecycle table layout does not prove execution order. No private keys or resource payloads exported.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
