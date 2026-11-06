"""Cross-check exact source/PLT identities and existing offline receipts.

Does not rerun any guest, public client, root helper or camera operation.
"""
from pathlib import Path
from hashlib import sha256
import io, json, zipfile
from elftools.elf.elffile import ELFFile
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
def digest(p):
    return sha256(p.read_bytes()).hexdigest()
def plt(e):
    start = e.get_section_by_name('.plt')['sh_addr']
    names = e.get_section_by_name('.dynsym')
    return {start + 32 + i * 16: names.get_symbol(r['r_info_sym']).name
            for i, r in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}
core_path = BASE / 'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/lib/libsencore.so'
jir_path = BASE / 'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so'
core, jir = [ELFFile(io.BytesIO(p.read_bytes())) for p in (core_path, jir_path)]
core_expected = {0xa260: 'memset', 0xa580: '_Z9SerializePFiPhmEPvm',
                 0xa450: '_Z10cpp_logrechPKcj', 0xa440: 'osal_valloc_msg_wait', 0x9f10: 'testcmd_init'}
jir_expected = {0x5b70: 'sys_mount', 0x5ee0: '_ZN11CFileAccess5mountEPKcS1_S1_mPKv',
                0x67b0: '_ZN11CFileAccess15selection_mountEPKcS1_S1_S1_mPKv',
                0x5ca0: '_ZN11CFileAccessC1Ev', 0x6540: '__errno_location',
                0x62d0: 'strncmp', 0x5e60: 'memset', 0x61a0: 'mount', 0x6090: '_ZN11CFileAccess5closeEv'}
for e, expected in ((core, core_expected), (jir, jir_expected)):
    actual = plt(e)
    for va, name in expected.items():
        assert actual[va] == name, (hex(va), actual[va], name)

d = json.loads((HERE / 'dispatch-guest-results.json').read_text())
assert digest(core_path) == d['source_sha256']
assert len(d['term_cases']) == 24
assert all(r['stop'] == 'original_return' and r['return_w0'] == 128 for r in d['term_cases'])
assert [r['boundary'] for r in d['positive_route_controls_stopped_before_external_call']] == ['0xa440', '0x9f10']
f = json.loads((HERE / 'fixed-loader-prefix-results.json').read_text())
assert digest(jir_path) == f['source_sha256'] and len(f['cases']) == 4
assert [r['stop'] for r in f['cases']] == ['before_external_call', 'original_return', 'before_external_call', 'before_external_call']
assert not d['original_instructions_or_table_replaced'] and not f['actual_mount_return_or_current_mount_state_fabricated']
assert d['new_camera_operations'] == f['actual_mount_file_write_dlopen_or_camera_operations'] == 0
i = json.loads((HERE / 'AP-terminal-inventory.json').read_text())
assert i['ELFs_reverified'] == 532 and i['camera_operations'] == 0
fifo = json.loads((HERE / 'fifo-route-review.json').read_text())
assert fifo['AP_regular_files_searched'] == 797
exact = [r['path'] for r in fifo['literal_hits'] if any('sen_host_' in s for s in r['strings'])]
assert exact == ['/lib/libsencore.so']
client = json.loads((HERE / 'public-client-review.json').read_text())
assert digest(HERE / 'pmca-sony-source.txt') == client['sha256']
assert client['commit'] == 'a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0'
prior = BASE / 'stage188-static-ELF-link-and-explicit-entry/final-receipt.json'
assert digest(prior) == 'aa3c1606b9752ed2f6d6595f50e7626383f7bbf434609322440fa38f225dd6c5'
archive = ROOT / 'outputs/fx3-recovery-adapter/releases/fx3-recovery-adapter-0.4.0.zip'
assert digest(archive) == '43343ddd7f516886f9d4ad354937f900710288dfd854c4d20b47ec7f915c636f'
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist()) == 19
    for member in z.namelist():
        relative = member.removeprefix('fx3-recovery-adapter/')
        assert relative != member and (ROOT / 'outputs/fx3-recovery-adapter' / relative).is_file()
        assert z.read(member) == (ROOT / 'outputs/fx3-recovery-adapter' / relative).read_bytes()

members = ['audit_dispatch.py', 'dispatch-guest-results.json', 'audit_fixed_loader.py',
           'fixed-loader-prefix-results.json', 'audit_fifo_and_client.py', 'fifo-route-review.json',
           'public-client-review.json', 'pmca-sony-source.txt', 'AP-terminal-inventory.json', 'verify_receipts.py']
report = {'status': 'PASS_SOURCE_BINDINGS_AND_OFFLINE_RECEIPTS', 'original_guest_cases': 30,
          'original_ARM64_instructions_run_in_Unicorn': True,
          'real_Linux_loader_kernel_USB_or_camera_run': False,
          'PLT_symbols_independently_reconciled': len(core_expected) + len(jir_expected),
          'only_fixed_FIFO_full_path_literal_owner_identified_in_AP': exact,
          'tool_0_4_source_and_archive_unchanged': True,
          'prior_47_tool_tests_not_rerun_or_counted_as_new_tests': True,
          'files': [{'path': p, 'bytes': (HERE / p).stat().st_size, 'sha256': digest(HERE / p)} for p in members],
          'new_camera_operations': 0}
with (HERE / 'verification-receipt.json').open('x') as out:
    json.dump(report, out, indent=2); out.write('\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
