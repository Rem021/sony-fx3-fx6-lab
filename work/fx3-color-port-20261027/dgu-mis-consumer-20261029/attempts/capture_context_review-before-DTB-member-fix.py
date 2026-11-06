#!/usr/bin/env python3
"""Inventory original MIS record prefixes, dispatch sources, and current DTB UARTs."""
import collections
import hashlib
import json
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
FW = HERE.parents[2]/'work/sony-firmware-20261024'
DGU_BASE = 0xfe040800
PINS = dict(DGU='39eeb6d572a060149194463507800ed66b866a20dceb8ed49b01a04eb6fb2ba7',
            MIS='4cd3e9bc3a0a4aec4793bff77e7ca4dccdba8637212cd632cdc5ecbe550daf98')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fdt_properties(blob):
    h = struct.unpack_from('>10I',blob)
    assert h[0] == 0xd00dfeed and h[1] <= len(blob)
    off, strings, end = h[2], blob[h[3]:h[3]+h[8]], h[2]+h[9]
    assert end <= len(blob) and h[3]+h[8] <= len(blob)
    stack, rows = [], []
    while off < end:
        token = struct.unpack_from('>I',blob,off)[0]
        off += 4
        if token == 1:
            z = blob.index(b'\0',off,end)
            stack.append(blob[off:z].decode())
            off = (z+4)&~3
        elif token == 2:
            assert stack
            stack.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from('>II',blob,off)
            off += 8
            assert off+length <= end and nameoff < len(strings)
            z = strings.index(b'\0',nameoff)
            rows.append(('/'+'/'.join(x for x in stack if x),strings[nameoff:z].decode(),blob[off:off+length]))
            off = (off+length+3)&~3
        elif token == 4:
            continue
        elif token == 9:
            assert not stack
            return rows
        else:
            raise AssertionError(('FDT token',token,off))
    raise AssertionError('FDT END missing')


def main():
    out = HERE/'DGU-MIS-context-review.json'
    assert not out.exists()
    originals = FW/'stage198-AP-CP-loaders-and-partition-selection/originals'
    dgu, mis = [(originals/(n+'.bin')).read_bytes() for n in ['DGU','MIS']]
    for key,data in [('DGU',dgu),('MIS',mis)]:
        assert sha(data) == PINS[key]
    parsed = []
    observed = set()
    for lo,hi in [(0xa00,0xc200),(0xc200,0x13200),(0x13200,len(mis))]:
        start = lo+struct.unpack_from('<H',mis,lo)[0]
        pos = start
        records, comments = [], []
        while pos+4 <= hi:
            flags,words,opcode = struct.unpack_from('<HBB',mis,pos)
            if not 1 <= words <= 21 or pos+words*4 > hi:
                break
            payload = mis[pos+4:pos+words*4]
            records.append(dict(file_offset=hex(pos),raw_flags_u16=hex(flags),word_count=words,
                opcode=hex(opcode),payload_hex=payload.hex()))
            observed.add(opcode)
            if opcode == 0x25:
                text = payload.split(b'\0',1)[0].decode('ascii',errors='replace')
                comments.append(dict(file_offset=hex(pos),text=text))
            pos += words*4
        counts = collections.Counter(r['opcode'] for r in records)
        parsed.append(dict(script_offset=hex(lo),scan_upper_limit=hex(hi),first_record_offset=hex(start),
            framing_records=len(records),framing_bytes=pos-start,stop_file_offset=hex(pos),
            stop_first4_hex=mis[pos:pos+4].hex(),opcode_counts=dict(sorted(counts.items())),
            records=records,comments=comments,
            scope='Sequential valid framing prefix only, bounded by next declared script/file end. Zero/invalid word count stops the host scan. This is not original control flow, reachable instruction count, proof of padding, or a complete script semantic decompilation.'))
    dispatch = []
    table = 0xfe045a38-DGU_BASE
    for opcode in sorted(observed):
        matches = []
        for index in range(47):
            row = dgu[table+index*16:table+(index+1)*16]
            if row[0] == opcode:
                matches.append(dict(index=index,table_VA=hex(DGU_BASE+table+index*16),
                    raw16_hex=row.hex(),handler=hex(struct.unpack_from('<Q',row,8)[0])))
        assert len(matches) == 1
        dispatch.append(dict(opcode=hex(opcode),**matches[0]))
    (HERE/'MIS-record-prefix-inventory.json').write_text(json.dumps(dict(source_sha256=PINS['MIS'],
        scripts=parsed,framing_records_total=sum(x['framing_records'] for x in parsed),
        scope='Original format corroborated by original parser and observed decoded records; static prefix inventory is distinct from actual execution.'),indent=2)+'\n')
    extraction = FW/'stage2/extraction'
    reader = extraction/'read_filesystems.py'
    assert sha(reader.read_bytes()) == 'eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
    image = extraction/'nflasha3.img'
    assert sha(image.read_bytes()) == 'ca5a8c80a1883c4a72c2f40018e3d40ab43e28ff0bf6a1d89f17d0680c607568'
    sys.path.insert(0,str(extraction))
    from read_filesystems import FAT16
    fs = FAT16(image)
    entry = next(x for x in fs.walk() if x['path']=='/cxd90057.dtb')
    dtb = fs.data(entry['cluster'],entry['size'])
    props = fdt_properties(dtb)
    nodes = {}
    for path,key,value in props:
        nodes.setdefault(path,{})[key] = value
    uarts = []
    for path,p in nodes.items():
        if b'arm,pl011' not in p.get('compatible',b'').split(b'\0'):
            continue
        reg = list(struct.unpack('>'+'I'*(len(p['reg'])//4),p['reg']))
        uarts.append(dict(path=path,compatible=p['compatible'].rstrip(b'\0').decode().split('\0'),reg_u32=reg))
    assert any(x['reg_u32']==[0,0xf1000000,0,0x1000] for x in uarts)
    md = Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    listing_dir = HERE/'listings'
    listing_dir.mkdir(exist_ok=False)
    fragments = []
    for name,lo,hi in [
        ('record-framing-and-dispatch',0xfe04548c,0xfe04564c),
        ('flags-normalizer',0xfe043b98,0xfe043c74),
        ('opcode11-setup-prefix',0xfe042654,0xfe0426a8),
        ('output-port-selection',0xfe0452d4,0xfe04536c),
        ('output-register-initializer',0xfe0458a4,0xfe045974),
        ('output-byte-writer',0xfe045974,0xfe0459c8),
        ('diagnostic-magic-read',0xfe0446fc,0xfe0447a8),
    ]:
        raw = dgu[lo-DGU_BASE:hi-DGU_BASE]
        path = listing_dir/(name+'.txt')
        path.write_text('\n'.join(f'{i.address:#x}: {i.bytes.hex():8} {i.mnemonic} {i.op_str}' for i in md.disasm(raw,lo))+'\n')
        fragments.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(raw),
            original_bytes_sha256=sha(raw),listing=str(path.relative_to(HERE))))
    result = dict(source_pins=PINS,observed_opcode_dispatch_entries=dispatch,
        record_format=dict(raw_flags_u16_at=0,word_count_u8_at=2,opcode_u8_at=3,total_record_bytes='word_count*4',
            original_max_word_count=21,decoded_DGU_context_layout='opcode u8,word_count u8,raw_flags u16,payload',
            payload_copy_count='word_count-1 u32, or equivalent bytes for opcode0x25',
            raw_flags_not_a_line_or_label_number=True),
        original_DTB=dict(image=str(image),image_sha256=sha(image.read_bytes()),member='/cxd90057.dtb',
            member_bytes=len(dtb),member_sha256=sha(dtb),PL011_nodes=uarts,
            scope='Current official7.02 package DTB, not a live active-node or physical-device measurement.'),
        boundary_classification=dict(first_external_read='0xfe05fe48',purpose='Original diagnostic magic probe, not a service callback pointer',
            original_NOR_word='0x645f68637461705f',compared_magic='0x59634649cafec0da',
            enhanced_cases_next_write='0xf1020024',enhanced_cases_value='0x1',enhanced_cases_PC='0xfe045918',
            write_executed=False,downstream_selected_port_base='0xf1000000',
            inference='The original0x11 handler selects an output port and enters hardware setup; downstream0xf1000000 range matches original DTB PL011. The first0xf1020024 register is not independently named here. Not a completed DDR-init or a buffer/pixel/RAW operation.'),
        comment_findings=dict(DDR_reset_CKE_and_MCLK_comments_in_first_script=True,
            Nanya_related_ODT_comment_in_second_script=True,actual_fitted_chip_vendor_capacity_or_profile_selection_proved=False),
        source_fragments=fragments,full_ISP_or_flashable_package_recovered=False,
        device_or_native_Sony_operations=0,other_owner_files_written=False)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(framing_records=[x['framing_records'] for x in parsed],
        total=sum(x['framing_records'] for x in parsed),observed_opcodes=len(dispatch),
        DTB_PL011_nodes=len(uarts),static_windows=len(fragments))))


if __name__ == '__main__':
    main()
