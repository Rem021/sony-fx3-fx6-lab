#!/usr/bin/env python3
"""Verify static provenance and report bounded length/data-identity conclusions."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import plistlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from capture_contract import read_va

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK = HERE.parent


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(name, value):
    path = HERE / name
    assert not path.exists(), 'Preserve existing audit outputs'
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert not (HERE / 'verification-receipt.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    previous = TASK / 'Pro-catalog-sources-20261030'
    prior_seal = previous / 'final-receipt.json'
    assert sha(prior_seal) == 'e0127129704d93735aff6aeeb2637c6c45f606b5f02b4cbc60c96fcd18b4630d'
    previous_rows = json.loads(prior_seal.read_text())['files']
    for row in previous_rows:
        path = previous / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    source_seal = TASK / 'input-20261028/final-receipt.json'
    assert sha(source_seal) == 'f49bd30b46c82a992e58f36ec0a2a79733485e580578ed43441e62a6466b9064'
    sealed_index = {row['path']: row for row in json.loads(source_seal.read_text())['files']}
    libs = {}
    all_functions = []
    all_vtables = []
    for name in ['original-contract.json', 'flow-contract.json', 'tail-flow-contract.json']:
        data = json.loads((HERE / name).read_text())
        for lib in data['source_libraries']:
            source = ROOT / lib['source']
            expected_row = sealed_index[str(source.relative_to(source_seal.parent))]
            assert lib['sha256'] == expected_row['sha256'] == sha(source)
            assert lib['bytes'] == expected_row['bytes'] == source.stat().st_size
            assert lib['byte_identical_to_2_04']
            old = Path(str(source).replace('/engine-rootfs/2.05/', '/engine-rootfs/2.04/'))
            old_pin = sealed_index[str(old.relative_to(source_seal.parent))]
            assert old_pin['sha256'] == lib['sha256'] == sha(old)
            libs[source.name] = lib
            with source.open('rb') as stream:
                elf = ELFFile(stream)
                for function in lib['functions']:
                    code = read_va(elf, int(function['VA'], 16), function['bytes'])
                    assert code == (HERE / function['raw']).read_bytes()
                    assert hashlib.sha256(code).hexdigest() == function['sha256']
                    all_functions.append((source.name, function))
                for vt in lib['vtables']:
                    assert hashlib.sha256(read_va(elf, int(vt['VA'],16), vt['bytes'])).hexdigest() == vt['sha256']
                    all_vtables.append((source.name, vt))
    assert len(all_functions) == 51 and len({(l, f['name']) for l, f in all_functions}) == 51

    # Confirm exact instructions underlying the claims, without running them.
    instructions = {}
    cd = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    for lib, f in all_functions:
        for ins in cd.disasm((HERE / f['raw']).read_bytes(), int(f['VA'], 16)):
            instructions[(lib, ins.address)] = (ins.mnemonic, ins.op_str)
    anchors = [
        ('libsdfileinputupdaterapi.so', 0x9a6c, 'and', 'w21, w20, #0x40000000'),
        ('libsdfileinputupdaterapi.so', 0x9a7c, 'mov', 'w1, w21'),
        ('libsdfileinputupdaterapi.so', 0x9ab4, 'stp', 'xzr, x19, [x0, #0x10]'),
        ('libsdfileinputupdaterapi.so', 0x9abc, 'add', 'x19, x19, x23'),
        ('libsdfileinputupdaterapi.so', 0x9af4, 'add', 'x23, x19, #0x180, lsl #12'),
        ('libsdfileinputupdaterapi.so', 0x9b18, 'add', 'x19, x19, #0x80, lsl #12'),
        ('libsdfileinputupdaterapi.so', 0x9b38, 'sub', 'x20, x20, x0'),
        ('libsdfileinputupdaterapi.so', 0x9b4c, 'stp', 'x20, xzr, [x0, #0x20]'),
        ('libsdfileinputupdaterapi.so', 0xa25c, 'cmp', 'x0, w20, uxtw'),
        ('libsdfileinputupdaterapi.so', 0xa260, 'b.hs', '#0xa2a4'),
        ('libsdfileinputupdaterapi.so', 0xa320, 'ldr', 'w1, [x29, #0x78]'),
        ('libsdfileinputupdaterapi.so', 0x91d0, 'str', 'x1, [x0, #0x540]'),
        ('libsdfileinputupdaterapi.so', 0x9630, 'ldr', 'x2, [x19, #0x540]'),
        ('libsdfileinputupdaterapi.so', 0x9670, 'sub', 'w1, w21, #0x100'),
        ('libsdfileinputupdaterapi.so', 0x967c, 'sub', 'x1, x21, #0x100'),
        ('libsdfileinputupdaterapi.so', 0x96bc, 'cbz', 'w0, #0x972c'),
        ('libsdfileinputupdaterapi.so', 0x9750, 'sub', 'x1, x21, #0x110'),
        ('libsdfileinputupdaterapi.so', 0x9754, 'str', 'x1, [x19, #0x538]'),
        ('libsdfileinputupdaterapi.so', 0xace8, 'ldr', 'w1, [x19, #8]'),
        ('libsdfileinputupdaterapi.so', 0xad14, 'cmp', 'w0, #1'),
        ('libsdfileinputupdaterapi.so', 0xad18, 'b.eq', '#0xad40'),
        ('libupdatercorecommon.so', 0xb340, 'ldp', 'x1, x2, [x20, #0x18]'),
        ('libupdatercommon.so', 0x9498, 'stp', 'x1, x2, [x0, #8]'),
        ('libupdatercommon.so', 0x949c, 'stp', 'x1, x1, [x0, #0x18]'),
        ('libupdatercommon.so', 0x96f0, 'csel', 'x20, x20, x21, ls'),
        ('libupdatercommon.so', 0x97a8, 'str', 'x0, [x22]'),
        ('libupdatercommon.so', 0x97e0, 'str', 'x0, [x22]'),
        ('libupdatercommon.so', 0x9b94, 'str', 'x0, [x19, #0x18]'),
        ('libupdatercommon.so', 0x9bf0, 'str', 'x0, [x19, #0x28]'),
    ]
    for lib, address, mnemonic, operands in anchors:
        assert instructions[(lib, address)] == (mnemonic, operands), (lib, hex(address), instructions.get((lib, address)))
    # Vtable offsets below are relative to the object address point, i.e. symbol+0x10.
    def slot(lib, name, displacement):
        tables = [vt for n, vt in all_vtables if n == lib and vt['name'] == name]
        assert tables and all(vt == tables[0] for vt in tables)
        row = next(r for r in tables[0]['slots'] if int(r['offset_from_symbol'], 16) == displacement + 0x10)
        return row['symbol']
    vtable_links = [
        ('libsdfileinputupdaterapi.so', '_ZTVN7Updater13BufferManagerE', 0x28, '_ZN7Updater13BufferManager17GetFirmwareBufferEv'),
        ('libsdfileinputupdaterapi.so', '_ZTVN7Updater17SDDecryptorModuleE', 0xa0, '_ZN7Updater18UFPDecryptorModule29WaitForFirmwareCopyCompletionEv'),
        ('libsdfileinputupdaterapi.so', '_ZTVN7Updater17SDDecryptorModuleE', 0xa8, '_ZN7Updater17SDDecryptorModule11SetBuffSizeEm'),
        ('libsdfileinputupdaterapi.so', '_ZTVN7Updater21SDUUDConditionCheckerE', 0x28, '_ZN7Updater21SDUUDConditionChecker23SkipContentsInformationERNS_15FsysFileHandlerE'),
        ('libsdfileinputupdaterapi.so', '_ZTVN7Updater21SDUUDConditionCheckerE', 0x58, '_ZN7Updater21SDUUDConditionChecker10searchFDATERNS_15FsysFileHandlerE'),
        ('libupdatercorecommon.so', '_ZTVN7Updater12BaseFirmwareE', 0x30, '_ZN7Updater12BaseFirmware9WriteDataEPKhmb'),
        ('libupdatercommon.so', '_ZTVN7Updater10RingBufferE', 0x48, '_ZN7Updater10RingBuffer19ReadDataWithoutCopyEPPhm'),
        ('libupdatercommon.so', '_ZTVN7Updater10RingBufferE', 0x40, '_ZN7Updater10RingBuffer8ReadDataEPhm'),
        ('libupdatercommon.so', '_ZTVN7Updater10RingBufferE', 0x38, '_ZN7Updater10RingBuffer9WriteDataEPKhmb'),
    ]
    for lib, vt, offset, name in vtable_links:
        assert slot(lib, vt, offset) == name

    # Reuse sealed RSA evidence without rerunning RSA/mutation tests or handling private material.
    rsa_path = TASK / 'input-20261028/official-key-rsa-verification-results.json'
    assert sha(rsa_path) == '323965d979d40bf71497fb4311cffe55e924fde6c431ded07662c304d10d503b'
    rsa = json.loads(rsa_path.read_text())
    frames = []
    for prior in rsa['packages']:
        path = Path(prior['source'])
        assert sha(path) == prior['source_sha256']
        size = path.stat().st_size
        chunks = []
        with path.open('rb') as f:
            assert f.read(8) == b'\x89UFU\r\n\x1a\n'
            for _ in range(32):
                pos = f.tell()
                header = f.read(8)
                assert len(header) == 8
                length = int.from_bytes(header[:4], 'big')
                assert pos + 8 + length <= size
                row = {'header_offset': pos, 'payload_offset': pos + 8, 'tag': header[4:].decode('ascii'), 'bytes': length}
                chunks.append(row)
                if header[4:] == b'FDAT':
                    assert pos + 8 == prior['fdat_offset'] and length == prior['fdat_bytes']
                    break
                f.seek(length, 1)
            else:
                raise AssertionError('No bounded first FDAT')
            tail_offset = prior['fdat_offset'] + prior['fdat_bytes']
            f.seek(tail_offset)
            tail = f.read(32)
        assert len(tail) == size - tail_offset == 12 and tail[:8] == b'\0\0\0\x04DEND'
        frames.append({'source': str(path.relative_to(ROOT)), 'bytes': size, 'sha256': prior['source_sha256'],
                       'chunks_through_first_FDAT': chunks, 'trailing_DEND_bytes': len(tail),
                       'ciphertext_bytes': prior['ciphertext_body_bytes'], 'signed_bytes': prior['ciphertext_body_bytes'] + 16,
                       'signature_offset_in_FDAT': prior['fdat_bytes'] - 256,
                       'IV_offset_in_FDAT': prior['fdat_bytes'] - 272,
                       'existing_RSA_evidence_reused': True, 'RSA_not_reexecuted': True})
    save('original-wrapper-frames.json', {'packages': frames, 'scope': 'Original file framing and existing signed interval evidence only; no altered package.'})

    capacities = []
    for page_size in [4096, 16384, 65536]:
        allocation = ((-page_size) & 0xffffffff) & 0x40000000
        capacity = allocation - page_size - 3 * 0x80000
        assert 272 < capacity < 2**30
        assert all(p['chunks_through_first_FDAT'][-1]['bytes'] <= capacity for p in frames)
        capacities.append({'assumed_positive_page_size': page_size, 'allocation_bytes': allocation,
                           'firmware_buffer_bytes': capacity, 'hex_capacity': hex(capacity),
                           'measured_live_page_size': False})
    analysis = {
        'historical_engine_only': True,
        'buffer_formula': 'M = uint32(-P) & 0x40000000; C = M - P - 3*0x80000, for successful allocation and positive page size P',
        'page_size_examples_not_hardware_measurements': capacities,
        'length_contract': 'searchFDAT reads big-endian uint32 L and rejects L > current empty buffer; SetBuffSize stores zero-extended L at object+0x540. ReadDataWithoutCopy returns N <= min(L, contiguous capacity, available bytes). Under normal initialized buffer state, 0 <= N < 2^30.',
        'signed_interval': 'If Pdata is returned pointer, digest length is uint32(N-256), signature pointer Pdata+N-256, signature length 256. IV is subsequently read from Pdata+N-272. For N>=272, signed bytes and IV use the same returned N and the uint32 digest length does not wrap.',
        'data_identity_contract': 'ReadDataWithoutCopy returns current ring read pointer without advancing it or reducing queued count. updateData subsequently invokes ReadData on this ring and readFromBuffer advances that same pointer/count. This is static same-buffer routing, not proof of runtime immutability or race freedom.',
        'admission_decision': 'VerifySignature requires RSA_verify result exactly 1, returns 0 after cleanup, and execWriteFirm continues past 0x96bc only for returned 0. Other shown paths allocate/throw ApiException; exception unwind and real write completion were not executed.',
        'normal_length_truncation_bypass_supported': False,
        'whole_modified_firmware_admission_proven': False,
        'not_exhaustive_malformed_input_safety': [
            'searchFDAT does not establish an N>=272 minimum at the shown size gate; N<256 can underflow the hash length and N<272 can place IV before returned data.',
            'Initial magic read and later header-info read do not check exact positive byte counts at all shown sites; some Seek boolean results are not checked by callers.',
            'No whole malformed input was submitted to original code or a camera; no conclusion that those gaps yield control or installation.',
            'Current installed 7.02 updater and actual concurrency/allocation state remain uncaptured. Historical ABI is not asserted to match it.',
        ],
        'private_keys_or_signing': False, 'original_code_execution': False,
        'device_actions': 0, 'modified_package_created': False,
    }
    save('length-and-data-identity-analysis.json', analysis)
    readiness = json.loads((TASK / 'Pro-catalog-sources-20261030/verification-receipt.json').read_text())['requirements_preserved']
    save('verification-receipt.json', {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_STATIC_HISTORICAL_ADMISSION_CONTRACT_NOT_FLASH_READINESS',
        'prior_checkpoint_files_verified': len(previous_rows), 'prior_checkpoint_seal': sha(prior_seal),
        'source_checkpoint_seal_verified': sha(source_seal), 'historical_libraries_verified_in_both_versions': len(libs),
        'complete_original_functions_verified': len(all_functions), 'exact_instruction_anchors_verified': len(anchors),
        'original_vtable_links_verified': len(vtable_links), 'original_packages_framed': len(frames),
        'existing_RSA_evidence_sha256': sha(rsa_path), 'RSA_tests_repeated': False,
        'no_new_original_program_execution_or_hardware': True, 'modified_package_created': False,
        'requirements_preserved': readiness, 'whole_goal_complete': False,
        'progress_classification': 'New original input length bound, same-buffer routing, and strict verifier return decision; full admission and donor gates remain open.',
        'confirmation_pending_for_this_task': False,
    })
    print(json.dumps({'status': 'PASS_SCOPED_STATIC_CONTRACT', 'functions': len(all_functions), 'anchors': len(anchors), 'vtables': len(vtable_links), 'packages': len(frames)}))


if __name__ == '__main__':
    main()
