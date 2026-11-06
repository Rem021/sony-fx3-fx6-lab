#!/usr/bin/env python3
"""Read historical Sony updater ELF data; never load or execute vendor code."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import plistlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE.parent / 'input-20261028'
SELECT = {
    'libsdfileinputupdaterapi.so': [
        '_ZN7Updater25SDFileInputUpdaterManager10InitializeEPKcS2_',
        '_ZN7Updater25SDFileInputUpdaterManager18VerifyUUDConditionEv',
        '_ZN7Updater25SDFileInputUpdaterManager12BurnFirmwareEv',
        '_ZN7Updater21SDUUDConditionChecker10searchFDATERNS_15FsysFileHandlerE',
        '_ZN7Updater21SDUUDConditionChecker21getUpdateFirmwareInfoEPKcRN10UpdaterAPI22firmware_information_t11informationE',
        '_ZN7Updater13BufferManager10InitializeEv',
        '_ZN7Updater13BufferManager17GetFirmwareBufferEv',
        '_ZN7Updater18UFPDecryptorModuleC2Ev',
        '_ZN7Updater18UFPDecryptorModule30FirmwareCopyCompletionCallbackEv',
        '_ZN7Updater18UFPDecryptorModule29WaitForFirmwareCopyCompletionEv',
        '_ZN7Updater17SDDecryptorModule11SetBuffSizeEm',
        '_ZN7Updater17SDDecryptorModuleC2Ev',
        '_ZN7Updater17SDDecryptorModule13execWriteFirmEv',
        '_ZN7Updater17SDDecryptorModule7decryptEv',
        '_ZN7Updater21SignatureVerification15VerifySignatureENS_13verify_info_tEPKc',
    ],
    'libupdatercorecommon.so': [
        '_ZN7Updater15BufferContainer4FreeEv',
        '_ZN7Updater10BaseModule18GetEmptyBufferSizeEv',
        '_ZN7Updater10BaseModule10InitializeEPNS_15BufferContainerEPS0_PNS_17CallbackInterfaceE',
        '_ZN7Updater15DecryptorModule10updateDataEv',
        '_ZN7Updater15DecryptorModule7setDataEv',
    ],
    'libupdatercommon.so': [
        '_ZN7Updater15FsysFileHandlerC2Ev',
        '_ZN7Updater15FsysFileHandler4ReadEPvm',
        '_ZN7Updater15FsysFileHandler4SeekEliPm',
        '_ZN7Updater15FsysFileHandler4SeekEl',
    ],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_va(elf, address, size):
    for segment in elf.iter_segments():
        if segment['p_type'] == 'PT_LOAD' and segment['p_vaddr'] <= address and address + size <= segment['p_vaddr'] + segment['p_filesz']:
            start = address - segment['p_vaddr']
            return segment.data()[start:start + size]
    raise ValueError((hex(address), size))


def capture(selection, result_name, namespace='', include_vtable_terms=None):
    assert not (HERE / result_name).exists(), 'Already captured; preserve prior outputs'
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    inventory = json.loads((SOURCE / 'original-initrd-inventory.json').read_text())
    indexed = {version['version']: {row['path']: row for row in version['entries']} for version in inventory['packages']}
    listing_dir = HERE / (namespace + '-listings' if namespace else 'listings')
    bytes_dir = HERE / (namespace + '-original-spans' if namespace else 'original-spans')
    listing_dir.mkdir(exist_ok=True)
    bytes_dir.mkdir(exist_ok=True)
    rows = []
    for filename, names in selection.items():
        path = SOURCE / 'engine-rootfs/2.05/usr/lib' / filename
        raw = path.read_bytes()
        pin = indexed['2.05']['/usr/lib/' + filename]['sha256']
        assert digest(raw) == pin
        old = SOURCE / 'engine-rootfs/2.04/usr/lib' / filename
        old_bytes = old.read_bytes()
        assert digest(old_bytes) == indexed['2.04']['/usr/lib/' + filename]['sha256']
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            table = elf.get_section_by_name('.dynsym')
            symbols = list(table.iter_symbols())
            byname = {s.name: s for s in symbols if s['st_shndx'] != 'SHN_UNDEF'}
            labels = {s['st_value']: s.name for s in symbols if s['st_value']}
            plt = elf.get_section_by_name('.plt')
            rela = elf.get_section_by_name('.rela.plt')
            if rela is not None:
                assert plt is not None and plt['sh_size'] == 32 + 16 * rela.num_relocations()
                for i, relocation in enumerate(rela.iter_relocations()):
                    labels[plt['sh_addr'] + 32 + 16 * i] = table.get_symbol(relocation['r_info_sym']).name
            functions = []
            disasm = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
            for name in names:
                symbol = byname[name]
                address, size = symbol['st_value'], symbol['st_size']
                code = read_va(elf, address, size)
                assert size and size % 4 == 0
                stem = filename + '-' + hex(address)
                byte_path = bytes_dir / (stem + '.bin')
                text_path = listing_dir / (stem + '.txt')
                assert not byte_path.exists() and not text_path.exists()
                byte_path.write_bytes(code)
                instructions, calls = [], []
                for ins in disasm.disasm(code, address):
                    line = f'{ins.address:08x} {ins.mnemonic:9} {ins.op_str}'
                    if ins.mnemonic == 'bl':
                        target = int(ins.op_str.removeprefix('#'), 16)
                        label = labels.get(target)
                        if label:
                            line += ' ; ' + label
                        calls.append({'address': hex(ins.address), 'kind': 'direct', 'target': hex(target), 'symbol': label})
                    elif ins.mnemonic == 'blr':
                        calls.append({'address': hex(ins.address), 'kind': 'indirect', 'operand': ins.op_str})
                    instructions.append(line)
                assert len(instructions) * 4 == len(code)
                text_path.write_text(name + '\n' + '\n'.join(instructions) + '\n')
                functions.append({'name': name, 'VA': hex(address), 'bytes': size, 'sha256': digest(code),
                                  'raw': str(byte_path.relative_to(HERE)), 'listing': str(text_path.relative_to(HERE)), 'calls': calls})
            vtables = []
            relocs = {r['r_offset']: r for r in elf.get_section_by_name('.rela.dyn').iter_relocations()}
            for name, symbol in byname.items():
                terms = include_vtable_terms or ['SDDecryptorModule', 'UFPDecryptorModule', 'SDUUDConditionChecker', 'BufferContainer']
                if not name.startswith('_ZTV') or not any(x in name for x in terms):
                    continue
                address, size = symbol['st_value'], symbol['st_size']
                data = read_va(elf, address, size)
                slots = []
                for offset in range(0, size, 8):
                    relocation = relocs.get(address + offset)
                    row = {'offset_from_symbol': hex(offset), 'raw_word': hex(int.from_bytes(data[offset:offset+8], 'little'))}
                    if relocation is not None:
                        s = table.get_symbol(relocation['r_info_sym'])
                        row.update(relocation_type=relocation['r_info_type'], symbol=s.name, addend=relocation['r_addend'])
                        if s['st_shndx'] != 'SHN_UNDEF':
                            row['resolved_link_VA'] = hex(s['st_value'] + relocation['r_addend'])
                    slots.append(row)
                vtables.append({'name': name, 'VA': hex(address), 'bytes': size, 'sha256': digest(data), 'slots': slots})
            rows.append({'source': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': pin,
                         'version': '2.05 historical intermediate updater initrd', 'byte_identical_to_2_04': raw == old_bytes,
                         'functions': functions, 'vtables': vtables})
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_libraries': rows,
              'scope': 'Original historical intermediate updater data, not a current-body engine capture. Static only; no original execution, helper stubs, hardware, signing, or modified firmware.'}
    (HERE / result_name).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'libraries': len(rows), 'functions': sum(len(x['functions']) for x in rows), 'vtables': sum(len(x['vtables']) for x in rows)}))


if __name__ == '__main__':
    capture(SELECT, 'original-contract.json')
