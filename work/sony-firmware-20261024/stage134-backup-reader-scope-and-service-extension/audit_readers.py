#!/usr/bin/env python3
"""Static original-ELF review only. Does not load or execute Sony code."""
from pathlib import Path
from hashlib import sha256
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
import io
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
LIB = BASE / 'stage2/extraction/files/nflasha15/lib'


class Image:
    def __init__(self, name, expected):
        self.path = LIB / name
        self.raw = self.path.read_bytes()
        assert sha256(self.raw).hexdigest() == expected
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.loads = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.dynsym = self.elf.get_section_by_name('.dynsym')
        self.symbols = {s.name: s for s in self.dynsym.iter_symbols() if s.name}
        table, relocations = self.elf.get_section_by_name('.plt'), self.elf.get_section_by_name('.rela.plt')
        self.plt = {table['sh_addr'] + 32 + 16 * n: self.dynsym.get_symbol(r['r_info_sym']).name
                    for n, r in enumerate(relocations.iter_relocations())}
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

    def read(self, address, length):
        segment = next(s for s in self.loads if s['p_vaddr'] <= address and
                       address + length <= s['p_vaddr'] + s['p_filesz'])
        offset = address - segment['p_vaddr']
        return segment.data()[offset:offset + length]

    def string(self, address):
        return self.read(address, 128).split(b'\0', 1)[0].decode('ascii')

    def instructions(self, address, size):
        output = []
        for ins in self.md.disasm(self.read(address, size), address):
            target = int(ins.op_str[1:], 16) if ins.mnemonic in ('bl', 'b') and ins.op_str.startswith('#0x') else None
            output.append({'pc': hex(ins.address), 'bytes': ins.bytes.hex(),
                           'asm': ins.mnemonic + ' ' + ins.op_str, 'PLT_symbol': self.plt.get(target)})
        assert sum(len(bytes.fromhex(x['bytes'])) for x in output) == size
        return output

    def function(self, name):
        symbol = self.symbols[name]
        assert symbol['st_shndx'] != 'SHN_UNDEF' and symbol['st_info']['type'] == 'STT_FUNC'
        address, size = symbol['st_value'], symbol['st_size']
        return {'name': name, 'VA': hex(address), 'bytes': size,
                'sha256': sha256(self.read(address, size)).hexdigest(),
                'instructions': self.instructions(address, size)}

    def expect_call(self, address, name):
        ins = self.instructions(address, 4)[0]
        assert ins['PLT_symbol'] == name, ins
        return ins


def main():
    jiritsu = Image('libJiritsu.so', 'bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9')
    core = Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    functions = [jiritsu.function(n) for n in ('adj_cmd_get_file', 'adj_cmd_get_file_hash',
                 'cmd_high_capacity_get_file', 'get_jiritsu_area_filename', 'get_access_filename')]
    core_functions = [core.function(n) for n in ('Regist_HaspId', '_ZN19WorkerThreadManager12registHaspIdEi',
                      'LoadSenserMode', 'StoreSenserMode', '_Z15GetPluginModulePKcth')]
    calls = []
    for address, name in [
        (0x9080, 'sys_mount'), (0x90b0, '_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'),
        (0x917c, '_ZN6DmmMgr9dmm_allocEj'), (0x9198, '_ZN11CFileAccess4openEPKci'),
        (0x91f4, '_ZN11CFileAccess4readEPvm'), (0x9210, '_ZN11CFileAccess5fsyncEv'),
        (0x9218, '_ZN11CFileAccess5closeEv'), (0xadd8, 'sys_mount'),
        (0xae60, 'sys_media_mount'), (0xaefc, '_ZN6DmmMgr9dmm_allocEj'),
        (0xaf28, '_ZN11CFileAccess4openEPKci'), (0xaf88, '_ZN11CFileAccess4readEPvm'),
        (0xafdc, 'libCommuMD5'), (0xb17c, 'adj_cmd_get_file'),
        (0xb1f0, 'adj_cmd_get_file_hash'), (0xb20c, 'adj_cmd_get_file2'),
        (0xb21c, '_ZN6DmmMgr8dmm_freeEv')]:
        calls.append(jiritsu.expect_call(address, name))
    for address, name in [(0x1447c, '_ZN8DeviceIo4openEPKci'),
                          (0x1448c, '_ZNK8DeviceIo5writeEPKvm'), (0x144ec, 'sync'),
                          (0xc194, 'Regist_HaspId')]:
        calls.append(core.expect_call(address, name))
    strings = {hex(a): jiritsu.string(a) for a in (0x30e17, 0x30e29, 0x31375)}
    strings['core:0x55121'] = core.string(0x55121)
    assert list(strings.values()) == ['/tmp/jiritsu', '/dev/nflasha6', '/mnt', '/setting/.hasp']
    for address, asm in [(0x918c, 'mov w2, #0'), (0x91f0, 'mov x0, x21'),
                         (0x91dc, 'cmp w0, #1'), (0x91fc, 'mov x2, x19'),
                         (0x9158, 'ldr x22, [x29, #0x878]')]:
        assert jiritsu.instructions(address, 4)[0]['asm'] == asm
    assert core.instructions(0x14470, 4)[0]['asm'] == 'mov w2, #0x1241'
    assert core.instructions(0x14478, 4)[0]['asm'] == 'movk w2, #0x10, lsl #16'
    assert core.instructions(0x14488, 4)[0]['asm'] == 'mov x2, #0x58'
    pending = BASE / 'stage131-stock-parser-filecontrol-availability'
    old = json.loads((pending / 'run-stock-table-lookup-20261027/parser-results.json').read_text())
    source = pending / 'parser_audit.py'
    executed = pending / 'run-stock-table-lookup-20261027/executed-source.py'
    assert source.read_bytes() == executed.read_bytes() and old['source_sha256'] == sha256(source.read_bytes()).hexdigest()
    assert old['status'] == 'PASS_STOCK_PFUNC_TABLES_EXCLUDE_FF01_FF03_WITH_ORIGINAL_PARSE_LOOKUP_NOT_DEVICE_PROTOCOL'
    assert len(old['cases']) == 10 and len(old['stock_tables']) == 3
    preserved = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                  'sha256': sha256(p.read_bytes()).hexdigest()} for p in sorted(pending.rglob('*')) if p.is_file()]
    result = {
        'status': 'PASS_STATIC_LEGACY_AND_HIGH_CAPACITY_READ_SCOPE_NOT_DEVICE_BACKUP_RELEASE',
        'Jiritsu_original_SHA256': sha256(jiritsu.raw).hexdigest(), 'core_original_SHA256': sha256(core.raw).hexdigest(),
        'functions': functions, 'core_functions': core_functions, 'checked_PLT_calls': calls, 'original_strings': strings,
        'legacy_get_file': {'kind0': 'service area selector; sys_mount(/dev/nflasha6,/tmp/jiritsu)',
             'kind1': 'path assembled with /mnt prefix; not a direct /setting or /usr reader',
             'size_source': 'stat FILE_INFO field; low32 drives read; no reviewed request offset/count field',
             'read_model': 'whole file allocation/read; read-only open argument0 then fsync/close; no bounded chunk backup proof'},
        'high_capacity_wrapper': {'meaning': 'DMM/bulk-transfer session wrapper; not a bounded file-range API',
             'type1': 'replace/create global DMM manager using caller size class',
             'type4': 'dispatch existing old/file2/hash/list whole-file handlers',
             'type16': 'dmm_free/global manager cleanup requiring valid object state',
             'null_global_or_failed_init_or_disconnect_recovery_not_proven': True},
        'hash_reader': 'Reads/allocates whole source before producing MD5; hash result is not healthy backup data',
        'hasp_history': {'path': '/setting/.hasp', 'open_flags': '0x101241', 'write_bytes': 88,
             'conditional': 'existing history path, Read_Hasp success and accepted header/state; no claim every authentication writes',
             'tail_caller': 'WorkerThreadManager::registHaspId -> Regist_HaspId',
             'full_authentication_call_chain_actual_file_presence_or_write_not_tested': True,
             'normal_auth_registration_must_not_be_assumed_RAM_only': True},
        'pending131_adopted_scope': {'preserved_files': preserved, 'previous_cases_replayed': False,
             'scope': 'Three shipped tables and original Parse lookup prefixes only; actual auth level, dynamic/custom tables and plugin mutations remain unproved',
             'no_blanket_PMCA_or_service_file_API_absence_claim': True},
        'no_Sony_code_or_camera_device_Windows_or_IO_executed': True,
        'goal_complete': False, 'persistent_write_release': False}
    with (HERE / 'reader-scope-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'whole_original_functions': len(functions) + len(core_functions),
                      'PLT_targets_checked': len(calls), 'native_cases_replayed': 0, 'device_backup_ready': False}))


if __name__ == '__main__':
    main()
