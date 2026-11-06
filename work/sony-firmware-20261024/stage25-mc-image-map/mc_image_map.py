#!/usr/bin/env python3
"""Pinned raw-image address evidence; static reads only, never loads firmware.

The candidate file/VA models are not observations of a camera MMU, loader or
running task. No native or guest execution, device interface, patch or write.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import plistlib
import struct
import subprocess
import traceback

import capstone
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_ARM, CS_MODE_THUMB

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/sony-firmware-20261024'
STAGE = Path(__file__).resolve().parent
VOLUME = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
A64_BASE = 0xffffffc001000000
MASK64 = (1 << 64) - 1
PINS = {
 'stage2/extraction/files/nflasha3/av-cam.bin':
 '0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
 'stage2/extraction/files/nflasha8/cpapp-b.bin':
 'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'stage2/extraction/files/nflasha15/codec/vcd_firmware.bin':
 '3306f208af48d188b69bbd45da3fcc06668a1e17f7a991dd338ece1a4d2bcac0',
 'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin':
 '15e75a9732e2f9904ada1c919c631dac0da57e605ce3daa4c6fb2ebe98982b5b',
 'stage2/extraction/files/nflasha15/kmod/codec_drv.ko':
 '79a3900813685459333f5cb4907e792b226f6f5f16c083746dbec7b1ce06cc2d',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def volume():
    value = plistlib.loads(subprocess.check_output(
        ['/usr/sbin/diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert value.get('VolumeUUID') == VOLUME and value.get('MountPoint') == '/Volumes/KAFU2T', value


def write_json(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write('\n')


def cstring(blob, offset, maximum=256):
    assert 0 <= offset < len(blob) and 0 < maximum <= 512
    end = blob.find(b'\0', offset, min(len(blob), offset + maximum))
    assert end >= offset, ('unterminated bounded string', hex(offset))
    return blob[offset:end].decode('ascii')


def occurrences(blob, value):
    found, offset = [], 0
    while True:
        offset = blob.find(value, offset)
        if offset < 0:
            return found
        found.append(offset)
        offset += 1


def dump(blob, start, end, base, arch=CS_ARCH_ARM64, mode=CS_MODE_ARM):
    assert 0 <= start < end <= len(blob) and end-start <= 0x1000
    md = Cs(arch, mode)
    rows = [{'offset': hex(i.address-base), 'va': hex(i.address),
             'bytes': i.bytes.hex(), 'asm': i.mnemonic+' '+i.op_str}
            for i in md.disasm(blob[start:end], base+start)]
    assert sum(len(bytes.fromhex(i['bytes'])) for i in rows) == end-start
    return rows


def adrp_refs(blob, targets, limit=0x310000):
    """Bounded syntactic ADRP/ADD references with no intervening clobber/branch.

    Scan is a candidate code range, not a discovered executable section.
    Returned local sequences are decoded; no whole-program reachability claim.
    """
    pages = {(A64_BASE+t) & ~4095 for t in targets}
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    md.detail = True
    result = []
    for offset in range(0, min(limit, len(blob)-32), 4):
        word = struct.unpack_from('<I', blob, offset)[0]
        if word & 0x9f000000 != 0x90000000:
            continue
        immediate = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
        if immediate & 0x100000:
            immediate -= 0x200000
        page = (((A64_BASE+offset) & ~4095) + (immediate << 12)) & MASK64
        if page not in pages:
            continue
        rd = word & 31
        for n in range(1, 7):
            at = offset + n*4
            word2 = struct.unpack_from('<I', blob, at)[0]
            instruction = next(md.disasm(blob[at:at+4], A64_BASE+at), None)
            if instruction is None:
                break
            if word2 & 0xff000000 == 0x91000000 and (word2 >> 5) & 31 == rd:
                target = page + (((word2 >> 10) & 4095) << (12 if word2 & (1 << 22) else 0))
                target_offset = target-A64_BASE
                if target_offset in targets:
                    result.append({'adrp_offset': hex(offset), 'add_offset': hex(at),
                       'target_offset': hex(target_offset), 'target_va': hex(target),
                       'sequence': dump(blob, offset, at+4, A64_BASE)})
                break
            if any(instruction.group(g) for g in (capstone.CS_GRP_JUMP,
                   capstone.CS_GRP_CALL, capstone.CS_GRP_RET, capstone.CS_GRP_INT)):
                break
            _, written = instruction.regs_access()
            if any(instruction.reg_name(r) in (f'x{rd}', f'w{rd}') for r in written):
                break
    return result


def vtable(blob, offset, expected):
    typeinfo = struct.unpack_from('<Q', blob, offset+8)[0]-A64_BASE
    assert 0 <= typeinfo <= len(blob)-16
    name = struct.unpack_from('<Q', blob, typeinfo+8)[0]-A64_BASE
    actual = cstring(blob, name)
    assert actual == expected
    return {'table_offset': hex(offset), 'typeinfo_offset': hex(typeinfo),
            'name_offset': hex(name), 'raw_type_name': actual,
            'scope': 'Static table/typeinfo/name pointer consistency only; no object instance.'}


def cpapp(blob):
    h = 0x20000
    assert len(blob) == 0xf3d818
    assert blob[:16].hex() == '04109fe5041081e201f0a0e10c801000'
    assert occurrences(blob, blob[h:h+0x17c]) == [h]
    specs = [(0x124, 0, 0x9a29f0, 0x128000),
             (0x130, 0x9a3000, 0x4085fc, 0xacb000),
             (0x13c, 0xdac000, 0x131818, 0xed4000),
             (0x148, 0xedf000, 0x4dd280, 0x1007000)]
    descriptors = []
    for field, source, size, address in specs:
        assert struct.unpack_from('<III', blob, h+field) == (source, size, address)
        start, end = h+source, h+source+size
        descriptors.append({'metadata_offset': hex(h+field), 'raw_source': hex(source),
          'raw_size': hex(size), 'raw_virtual': hex(address),
          'candidate_file_start': hex(start), 'candidate_file_end': hex(end),
          'within_file': end <= len(blob),
          'candidate_mapping': 'VA=0x108000+file_offset; descriptor source relative to file0x20000'})
    last_backed_end = h+0xdac000+0x131818
    assert len(blob)-last_backed_end == 0x40000
    # A fixed inline name record, not a function pointer or receiver table.
    assert struct.unpack_from('<H', blob, 0xc27e18)[0] == 0x57
    assert cstring(blob, 0xc27e1a) == 'MCODEC'
    thumb = dump(blob, 0x7bc08, 0x7bc20, 0x108000, CS_ARCH_ARM, CS_MODE_THUMB)
    assert thumb[0]['asm'] == 'push {r4, r5, r6, r7, lr}'
    assert any(i['asm'] == 'movw r8, #0xb015' for i in thumb)
    assert thumb[-1]['asm'] == 'movt r8, #0x2000'
    return {'size': len(blob), 'bootstrap_candidate_base': '0x108000',
      'metadata_file_offset': hex(h), 'metadata_size': '0x17c',
      'descriptor_triplets': descriptors,
      'unexplained_bytes_after_first_three_candidate_segments': len(blob)-last_backed_end,
      'fourth_descriptor_past_EOF': True,
      'MCODEC_inline_record': {'file_offset': '0xc27e18', 'u16_group': '0x57',
          'name': 'MCODEC', 'receiver_function_identified': False},
      'bootstrap': dump(blob, 0, 0xc, 0x108000, CS_ARCH_ARM),
      'bootstrap_metadata_copy_site': dump(blob, 0x398, 0x3d0, 0x108000, CS_ARCH_ARM),
      'mixed_ISA_example': thumb,
      'scope': 'Candidate app-segment mapping; fourth descriptor and trailing bytes unresolved. ARM boot plus Thumb example does not prove all code modes or runtime MMU. Never emulated boot.'}


def avcam(blob):
    assert len(blob) == 13348560 and blob[8:12] == b'ORIL'
    entries = {0:0x58, 0x10:0x6c, 0x18:0xa8, 0x20:0x1a4, 0x28:0xe0,
               0x30:0x118, 0x38:0x150, 0x40:0x188, 0x48:0x18c, 0x50:0x190}
    for slot, offset in entries.items():
        assert struct.unpack_from('<Q', blob, slot)[0] == A64_BASE+offset
    names = {
      0x4026a8:'[CdSeqCtrlEnc][MC:%d]CdSeqCtrlEnc::SendEncOpenCommand()',
      0x402732:'void CdSeqCtrlEnc::SendEncOpenCommand(const CdSeqCtrlEnc::enc_seq_open_param_t &)',
      0x404eb2:'[CdSeqCtrlEncIf]CdSeqCtrlEncIf::ExecMovieCodecMsg() msgid = 0x%04x\n',
      0x44431d:'[IMLENCSTAT]imola unsupported format. MPR set invalid enc_open params(not error. possible operation as specified)',
      0x44438f:'[IMLENCSTAT]imola resource layer expect enc_close',
    }
    for offset, expected in names.items():
        assert cstring(blob, offset) == expected, (hex(offset), cstring(blob, offset))
    refs = adrp_refs(blob, set(names)|{0x33f3f0, 0x33db30})
    assert any(r['adrp_offset']=='0x87fbc' and r['target_offset']=='0x4026a8' for r in refs)
    assert any(r['adrp_offset']=='0x24b3b0' and r['target_offset']=='0x44431d' for r in refs)
    tables = [vtable(blob, at, expected) for at, expected in [
      (0x33d310,'10CdCtrlCore'), (0x33d658,'8CdMemEnc'),
      (0x33da08,'14CdSeqCtrlDecIf'), (0x33d848,'12CdSeqCtrlDec'),
      (0x33db30,'12CdSeqCtrlEnc'), (0x33f3f0,'N8sfmc_enc8sfmc_encE')]]
    # Exact original sequences, not inferred solely from a matching byte literal.
    constants = []
    for start, end, value in [(0x87fa4,0x87fac,0x805700f9),
         (0x7c1e0,0x7c1e8,0x805700f9),(0x7c1f4,0x7c1fc,0x805720f9)]:
        words = struct.unpack_from('<II', blob, start)
        first, second = words
        opcode = (first >> 29) & 3
        assert opcode in (0,2) and first & 0x1f800000 == 0x12800000 and first >> 31 == 0
        actual = ((first >> 5) & 65535) << (((first >> 21) & 3)*16)
        if opcode == 0:
            actual = (~actual) & 0xffffffff
        assert (second >> 29) & 3 == 3 and (first & 31) == (second & 31)
        shift = ((second >> 21) & 3)*16
        actual = (actual & ~(65535 << shift)) | (((second >> 5) & 65535) << shift)
        assert actual == value
        constants.append({'value': hex(value), 'instructions': dump(blob,start,end,A64_BASE)})
    regions = [('entry wrappers',0x58,0x1a4),
       ('CdCtrlCore two memory-object construction calls',0x7c1b4,0x7c214),
       ('CdMemEnc constructor stores channel+0xb40',0x803a8,0x803e0),
       ('CdSeqCtrlEnc SendEncOpenCommand candidate complete function',0x87f88,0x885d4),
       ('CdSeqCtrlEncIf ExecMovieCodecMsg',0x8bb3c,0x8bc68),
       ('sfmc_enc constructor vtable and first dependencies',0xa60dc,0xa6188),
       ('imola channel-creation callback through response flag',0x24b2ec,0x24b448)]
    # This byte is an invalid channel selector at the callback, not a dimensions table.
    assert blob[0x44fcea] == 0xff
    return {'size':len(blob), 'candidate_base':hex(A64_BASE),
      'magic':'ORIL','raw_header_u32_0c':struct.unpack_from('<I',blob,0xc)[0],
      'header_pointer_entries':[{'file_offset':hex(k),'entry_va':hex(A64_BASE+v),
                                'target_offset':hex(v)} for k,v in entries.items()],
      'model_validation':'Header pointers, A64 PC-relative diagnostic references and independent C++ table/typeinfo/name pointers agree with the same static file/VA model. Runtime load/permissions not observed.',
      'bounded_strings':[{'offset':hex(k),'text':v} for k,v in names.items()],
      'local_ADRP_ADD_references':refs, 'original_wide_constants':constants,
      'typeinfo_pointer_chains':tables,
      'static_regions':[{'name':n,'start_offset':hex(s),'end_offset_exclusive':hex(e),
                        'instructions':dump(blob,s,e,A64_BASE)} for n,s,e in regions],
      'imola_invalid_channel_branch':{
        'channel_loaded_from':'object+0x18', 'sentinel_file_offset':'0x44fcea',
        'sentinel_value':255, 'compare_offset':'0x24b37c',
        'equal_path':'Logs unsupported/expected close, then sets reply flag0; create dependency at0x246154 skipped.',
        'not_equal_path':'Calls config getter0x22ba98 and create dependency0x246154, then sets reply flag1.',
        'scope':'Channel-selector branch only. Earlier selector assignment/configuration, actual resource layer and success/error status not executed. Does not bind target HD HEVC.'},
      'actual_MC_registration_and_Open_payload_binding_verified':False}


def run(out):
    previous = BASE/'stage24-receiver-dispatch/final-receipt.json'
    prior = json.loads(previous.read_text())
    assert all(sha((ROOT/v['path']).read_bytes()) == v['sha256'] for v in prior['files'])
    assert sha(previous.read_bytes()) == 'e123a4bca1ed9ab845966898e2338e0a355c80bd7b9dc295bfffabf4cd4d55c7'
    inputs = {}
    blobs = {}
    for name, expected in PINS.items():
        data = (BASE/name).read_bytes()
        assert sha(data) == expected, name
        inputs[str((BASE/name).relative_to(ROOT))] = {'size':len(data),'sha256':expected}
        blobs[Path(name).name] = data
    proof = {'status':'PASS_PINNED_RAW_IMAGE_STATIC_ADDRESS_EVIDENCE_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'cpapp':cpapp(blobs['cpapp-b.bin']), 'avcam':avcam(blobs['av-cam.bin']),
      'codec_payloads':[{'name':name,'header_hex':blobs[name][:0x40].hex(),
         'scope':'Pinned original bytes only. ISA, active variant selection, firmware load and hardware execution unresolved.'}
         for name in ('vcd_firmware.bin','vcd_firmware_imola2.bin')],
      'findings':[
        'av-cam.bin is a stronger next encoder-code candidate than the generic CPapp MCODEC inline group name: a consistent static A64 model binds encoder diagnostics, CdSeqCtrlEnc and sfmc_enc typeinfo.',
        'Original avcam sequences construct 0x805700f9 and0x805720f9, matching upstream MC destination values. The containing CdCtrlCore/CdMemEnc paths and CdSeqCtrlEnc sender are static evidence, not yet the registered receiver for the upstream packet.',
        'The Imola unsupported-format diagnostic is guarded here by channel selector0xff, not a width/height/HEVC comparison. Upstream selector generation, full validation and replies remain open.',
        'CPapp metadata supports a partial candidate map with ARM bootstrap and a Thumb example; a fourth descriptor exceeds EOF and0x40000 trailing bytes are unresolved. Do not infer a whole-image flat runtime map.',
        'No original code ran in this stage. Static address consistency cannot establish MAIN HEVC acceptance, runtime processor routing or a recoverable firmware flash.'],
      'full_MC_receiver_or_format_acceptance_verified':False,
      'native_or_guest_firmware_executed':False,
      'camera_or_remote_access_attempted':False,
      'modified_firmware_or_flash_tool_exported':False,
      'goal_complete':False, 'persistent_write_release':False}
    # Verify no input mutated during analysis.
    assert all(sha((ROOT/name).read_bytes()) == value['sha256'] for name,value in inputs.items())
    summary = {key:proof[key] for key in ('status','full_MC_receiver_or_format_acceptance_verified',
       'native_or_guest_firmware_executed','camera_or_remote_access_attempted',
       'modified_firmware_or_flash_tool_exported','goal_complete','persistent_write_release')}
    summary.update(avcam_candidate_base=hex(A64_BASE),
       avcam_typeinfo_chains=len(proof['avcam']['typeinfo_pointer_chains']),
       avcam_local_diagnostic_or_table_references=len(proof['avcam']['local_ADRP_ADD_references']),
       cpapp_fourth_descriptor_past_EOF=True, cpapp_unexplained_tail_bytes=0x40000,
       unsupported_diagnostic_branch_compares='channel selector to0xff; not target format validation')
    write_json(out/'mc-image-map-results.json',proof)
    write_json(out/'summary.json',summary)
    write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
       'script_sha256':sha(Path(__file__).read_bytes()), 'capstone_version':capstone.__version__,
       'inputs':inputs, 'volume_uuid':VOLUME, 'previous_manifest_sha256':sha(previous.read_bytes()),
       'result_sha256':sha((out/'mc-image-map-results.json').read_bytes()),
       'summary_sha256':sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    volume()
    out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    try:
        run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as handle:
            handle.write(Path(__file__).read_bytes())
        write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':
    main()
