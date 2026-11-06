#!/usr/bin/env python3
"""Rebuild a read-only original FX3 UI image loading audit. No guest execution."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from io import BytesIO
import argparse, collections, hashlib, json, plistlib, re, struct, subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / 'menu-repair-01').is_dir())
AP = ROOT / 'menu-repair-01/original-uipc/ap-projection'
REG = AP / 'regular-files'
RUN = ROOT / 'menu-repair-01/runtime/runs/ap102v3observe600-10fbf756'
CS = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
CS.detail = True

def sha(b):
    return hashlib.sha256(b).hexdigest()

def receipt(path):
    b = path.read_bytes()
    return {'path': str(path), 'bytes': len(b), 'sha256': sha(b)}

def identity():
    v = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    assert v.get('VolumeUUID', '').upper() == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    return v['VolumeUUID']

class Image:
    def __init__(self, path):
        self.path = Path(path)
        self.b = self.path.read_bytes()
        self.e = ELFFile(BytesIO(self.b))
        self.syms = self.e.get_section_by_name('.dynsym') or self.e.get_section_by_name('.symtab')
        self.symbols = list(self.syms.iter_symbols())
        self.names = subprocess.check_output(['c++filt'], input='\n'.join(s.name for s in self.symbols), text=True).splitlines()
        self.byaddr = {s['st_value']: d for s, d in zip(self.symbols, self.names) if s['st_value'] and s['st_info']['type'] == 'STT_FUNC'}
        self.plt = {}
        p, r = self.e.get_section_by_name('.plt'), self.e.get_section_by_name('.rela.plt')
        if p and r:
            self.plt = {p['sh_addr']+32+i*16: self.syms.get_symbol(x['r_info_sym']).name for i, x in enumerate(r.iter_relocations())}
        rd = self.e.get_section_by_name('.rela.dyn')
        self.reloc = list(rd.iter_relocations()) if rd else []
    def read(self, va, n):
        for s in self.e.iter_segments():
            if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= va and va+n <= s['p_vaddr']+s['p_filesz']:
                o = s['p_offset']+va-s['p_vaddr']
                return self.b[o:o+n]
        raise ValueError(hex(va))
    def string(self, va):
        out = bytearray()
        for a in range(va, va+400):
            c = self.read(a, 1)
            if c == b'\0': break
            out.extend(c)
        return out.decode('utf-8', 'replace')
    def block(self, a, n):
        rows = []
        for i in CS.disasm(self.read(a, n), a):
            d = {'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic+' '+i.op_str}
            if i.mnemonic in ('b', 'bl') and i.operands[0].type == ARM64_OP_IMM:
                t = i.operands[0].imm
                if t in self.plt or t in self.byaddr: d['callee'] = self.plt.get(t, self.byaddr.get(t))
            rows.append(d)
        return rows
    def show(self, a, n):
        print(self.path.name, hex(a), self.byaddr.get(a, 'private'))
        for r in self.block(a, n): print(r['va'], r['asm'], r.get('callee', ''))

def table_entries(b, t):
    """Literal 1213fc..121500 integer indexing, with bounds/missing checks."""
    w, = struct.unpack_from('<I', b, t+4)
    count, header, kind = w & 0x1fff, b[t] & 0x7c, b[t] & 3
    data_base = t+header+((w >> 11) & 0x7ffc)
    out, missing = [], []
    for index in range(count):
        if kind == 1:
            offset, = struct.unpack_from('<I', b, t+header+4*index)
        else:
            assert kind in (0, 3)
            cutoff = struct.unpack_from('<H', b, t+8)[0] if kind == 3 else count
            slot = index if index <= cutoff else 2*index-cutoff
            pos = t+header+2*slot
            encoded, = struct.unpack_from('<H', b, pos)
            if encoded == 0xffff:
                missing.append(index)
                continue
            if kind == 3 and encoded & 0x8000:
                encoded = ((encoded & 0x7fff) << 16) | struct.unpack_from('<H', b, pos+2)[0]
            offset = encoded*4
        if offset == 0xffffffff:
            missing.append(index)
            continue
        at = data_base+offset
        assert 0 <= at < len(b), (index, hex(at), len(b))
        out.append((index, at))
    return {'table_offset': hex(t), 'kind': kind, 'count': count, 'header_bytes': header,
            'data_base': hex(data_base), 'missing': missing}, out

def image_inventory(cpio):
    bypath = {m['path'].lstrip('/'): m for m in cpio['members']}
    paths = sorted((REG/'usr/share/app').glob('image_*.uxc'))
    assert len(paths) == 9
    result = {'files': [], 'uxb_png_groups': [], 'global_xdb_references': []}
    total = 0
    for p in paths:
        b = p.read_bytes()
        assert b[:4] == b'uxd\x07'
        member = bypath[str(p.relative_to(REG))]
        assert (len(b), sha(b)) == (member['bytes'], member['sha256'])
        meta, rows = table_entries(b, 8)
        enc, fmt, tags, dimensions = (collections.Counter() for _ in range(4))
        ledger, samples = [], []
        preferred = set()
        for index, r in rows:
            tag, word = struct.unpack_from('<II', b, r)
            width, height = struct.unpack_from('<HH', b, r+8)
            encoding, pixel = (word >> 28) & 7, (word >> 16) & 0x3f
            # Type 6 is the mapped-file offset/length descriptor handled at 114294.
            assert (tag >> 26) & 0x1f == 6
            # 1134d4: optional variable metadata before the offset/length pair.
            # Bit31 is preserved as a flag; it is not assumed to mean "external".
            footer = r+4+(12+8*b[r+12] if word & (1 << 27) else 8)
            length, relative = struct.unpack_from('<II', b, footer)
            start, end = r+4+relative, r+4+relative+length
            assert start >= footer+8 and length > 0 and end <= len(b)
            assert width > 0 and height > 0
            enc[encoding] += 1; fmt[pixel] += 1; tags[(tag >> 26) & 31] += 1
            dimensions[(width, height)] += 1
            item = {'index': index, 'record_offset': hex(r), 'record_tag': hex(tag),
                    'encoding': encoding, 'resource_pixel_format': pixel, 'header_word':hex(word),
                    'length_offset_descriptor':hex(footer),
                    'width': width, 'height': height, 'source_bytes': length,
                    'source_offset': hex(start)}
            ledger.append(item)
            dim = (width, height)
            if index == rows[0][0] or dim in ((320, 52), (640, 384), (70, 60)) and dim not in preferred:
                preferred.add(dim)
                samples.append({**item, 'descriptor': b[r:footer+8].hex(),
                                'source_header32': b[start:start+32].hex(),
                                'source_sha256': sha(b[start:end]),
                                'padded_output_bytes': ((width+15)&~15)*height*2,
                                'records_4KiB': ((((width+15)&~15)*height*2)+4095)//4096})
        assert enc == {4: len(rows)} and fmt == {0: len(rows)}
        total += len(rows)
        result['files'].append({**receipt(p), 'cpio_member': member, 'table': meta,
                                'valid_records': len(rows), 'encodings': dict(enc),
                                'resource_pixel_formats': dict(fmt), 'record_types': dict(tags),
                                'all_payload_spans_valid': True,
                                'all_payloads_nonzero': all(any(b[int(z['source_offset'],16):int(z['source_offset'],16)+z['source_bytes']]) for z in ledger),
                                'metadata_ledger_sha256': sha(json.dumps(ledger, sort_keys=True).encode()),
                                'dimension_match_counts': {f'{w}x{h}': dimensions[(w,h)] for w,h in ((320,52),(640,384),(70,60))},
                                'samples': samples})
    assert total == 51642
    result['uxd_total_valid_records'] = total
    for name in ('image.uxb', 'style.uxb', 'color.uxb', 'global.xdb'):
        p = REG/'usr/share/app'/name; b = p.read_bytes(); m = bypath[str(p.relative_to(REG))]
        assert (len(b), sha(b)) == (m['bytes'], m['sha256'])
        result.setdefault('other_files', []).append({**receipt(p), 'header32': b[:32].hex(), 'cpio_member': m})
    b = (REG/'usr/share/app/image.uxb').read_bytes()
    _, roots = table_entries(b, 8)
    for bank, at in roots:
        meta, rows = table_entries(b, at)
        assert len(rows) == 277
        samples = []
        for index, r in rows:
            tag, word = struct.unpack_from('<II', b, r)
            width, height = struct.unpack_from('<HH', b, r+8)
            assert (tag >> 26) & 31 == 4 and (word >> 28) & 7 == 1
            footer = r+4+(10+8*b[r+12] if word & (1 << 27) else 8)
            length, = struct.unpack_from('<I', b, footer)
            start = footer+4
            assert b[start:start+8] == b'\x89PNG\r\n\x1a\n' and start+length <= len(b)
            assert struct.unpack_from('>II',b,start+16) == (width,height)
            if len(samples) < 2:
                samples.append({'index': index, 'record_offset': hex(r), 'source_offset': hex(start),
                                'width': width, 'height': height, 'bytes': length,
                                'sha256': sha(b[start:start+length])})
        result['uxb_png_groups'].append({'root_index': bank, 'table': meta,
                                         'records': len(rows), 'encoding': 1, 'samples': samples})
    assert sum(x['records'] for x in result['uxb_png_groups']) == 831
    b = (REG/'usr/share/app/global.xdb').read_bytes()
    for x in re.finditer(rb'[ -~]{5,}\x00', b):
        s = x.group()[:-1].decode()
        if any(n in s for n in ('image_', 'image.uxb', 'style.uxb', 'color.uxb')):
            result['global_xdb_references'].append({'file_offset': hex(x.start()), 'string': s})
    result['global_xdb_literal_image_uxb_reference'] = b'image.uxb' in b
    return result

def original_evidence(obj):
    assert sha(obj.b) == 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'
    ranges = [(0x16ec6c,0x38),(0x1188fc,0x30),(0x11e2ac,0x4c),
              (0x11e520,0x64),(0x11e7c4,0x30),(0x11e818,0x54),
              (0x1213fc,0x110),(0x121590,0x118),(0x1216a8,0x110),
              (0x1218a8,0x30c),(0x121d08,0x78),(0x121e84,0x138),
              (0x122298,0x150),
              (0x117068,0xe8),(0x116d24,0x10),(0x12e164,0xb4),
              (0x113470,0x2d8),(0x113c80,0x294),(0x113fa0,0x1d0),
              (0x114170,0x210),(0x134600,0xc),(0x15bfe8,0x4c),
              (0x15c460,0x22c),(0x15c6a0,0x128),(0x154f18,0xd0),
              (0x154c40,0x2d8),(0x155078,0x80),(0x155198,0x200),
              (0x15f458,0x284),(0x1167c8,0x6c),(0x116834,0x7c),(0x12b414,0x24),
              (0xeecf8,0x44),(0xeef60,0x40),(0x15c1bc,0xb4),
              (0x153d08,0x70),(0x111020,0x20),(0x12fa04,0xb4),
              (0x1550f8,0xa0),(0x15ea44,0xe8),(0x101c74,0x38)]
    blocks = {hex(a): {'bytes': n, 'instructions': obj.block(a,n)} for a,n in ranges}
    anchors = {0x154c78:'mov w1, #2',0x154c80:'bl #0x55c10',
               0x154c98:'mov w0, #0',0x154e84:'bl #0x56560',
               0x15c6e4:'b.ne #0x15c770',0x15c6fc:'bl #0x154f18',
               0x15c680:'bl #0x15f1e0',0x113724:'ubfx x0, x0, #0x1c, #3'}
    for a, want in anchors.items(): assert obj.block(a,4)[0]['asm'] == want
    assert struct.unpack('<I',obj.read(0x1e3b48,4))[0]==7
    assert obj.read(0x2648f0+7*24+4,1)==b'\x10'
    strings = []
    for x in re.finditer(rb'[ -~]{6,}\x00',obj.b):
        if 0x1e3d89 <= x.start() < 0x1e4620 or 0x1e77c8 <= x.start() < 0x1e7a00 or 0x1e7ea0 <= x.start() < 0x1e8270:
            strings.append({'va':hex(x.start()),'value':x.group()[:-1].decode()})
    rtti=[]
    for name, ti, vt, count in [('Lz77Decoder',0x25cc80,0x25cca8,4),
                               ('RawDecoder',0x25ccc8,0x25ccf0,4),
                               ('PngDecoder',0x25d7c8,0x25d7f0,4),
                               ('DevDecoderFactory',0x25d4e0,0x25d508,8),
                               ('DecodeImageCommand',0x257450,0x257478,8),
                               ('ImageBufferAdapter',0x257608,0x257620,13)]:
        # Relocations, not a raw non-relocated vtable pointer read.
        rr={r['r_offset']:r['r_addend'] for r in obj.reloc if r['r_info_type']==1027}
        assert vt-8 in rr
        rtti.append({'class':name,'typeinfo_address':hex(rr[vt-8]),'vptr_address_point':hex(vt),
                     'slots':{hex(i*8):hex(rr[vt+i*8]) for i in range(count) if vt+i*8 in rr}})
    exports=[{'va':hex(s['st_value']),'bytes':s['st_size'],'name':d}
             for s,d in zip(obj.symbols,obj.names)
             if s['st_shndx']!='SHN_UNDEF' and any(t in d for t in ('libra::','ResourceManager::','setImageLoadCallback'))]
    return {**receipt(obj.path), 'blocks':blocks,'rtti':rtti,'strings':strings,'exported_symbols':exports,
            'format_map_111030': list(struct.unpack('<8I',obj.read(0x1e3b48,32))),
            'resource_bytes_per_pixel_111020':obj.read(0x1e3b68,8).hex(),
            'system_format7_description_264998':obj.read(0x2648f0+7*24,24).hex(),
            'ux_log_mask_initial_264c08':obj.read(0x264c08,4).hex(),
            'anchors_checked':{hex(k):v for k,v in anchors.items()}}

def kernel_evidence():
    p=AP/'full-v4/regular-files/usr/kmod/ldec.ko';b=p.read_bytes()
    assert sha(b)=='7663d3437220722858edfe024e75928648e40cd9345b0d6ee5ff3bf359c62f7e'
    e=ELFFile(BytesIO(b));sy=e.get_section_by_name('.symtab')
    result={**receipt(p),'address_convention':'ET_REL section plus offset; not runtime VA','sections':{}}
    for name in ('.text','.init.text','.exit.text'):
        sec=e.get_section_by_name(name)
        if not sec:continue
        relsec=e.get_section_by_name('.rela'+name)
        rr={r['r_offset']:{'symbol':sy.get_symbol(r['r_info_sym']).name,'addend':r['r_addend'],'type':r['r_info_type']} for r in relsec.iter_relocations()} if relsec else {}
        rows=[]
        for offset in range(0,len(sec.data()),4):
            ins=list(CS.disasm(sec.data()[offset:offset+4],offset))
            rows.append({'offset':hex(offset),'bytes':sec.data()[offset:offset+4].hex(),
                         'asm':ins[0].mnemonic+' '+ins[0].op_str if ins else '.word (not decoded)',
                         **({'relocation':rr[offset]} if offset in rr else {})})
        result['sections'][name]={'sha256':sha(sec.data()),'bytes':len(sec.data()),'instructions':rows}
    result['functions']=[{'name':s.name,'section':e.get_section(s['st_shndx']).name,
                          'offset':hex(s['st_value']),'bytes':s['st_size']}
                         for s in sy.iter_symbols() if s['st_info']['type']=='STT_FUNC' and isinstance(s['st_shndx'],int)]
    result['undefined_imports']=[s.name for s in sy.iter_symbols() if s['st_shndx']=='SHN_UNDEF' and s.name]
    result['strings']=[{'file_offset':hex(x.start()),'value':x.group()[:-1].decode()}
                       for x in re.finditer(rb'[ -~]{6,}\x00',b) if any(v in x.group().lower() for v in (b'ldec',b'decompress',b'lz77',b'dma'))]
    return result

def runtime_evidence(cpio, graphics):
    raw=(RUN/'serial.log').read_bytes();assert sha(raw)==graphics['serial_sha256']
    lines=raw.decode('utf-8','replace').split('\n')
    snippets=[];counts=collections.Counter();zero=collections.Counter();nonzero=collections.Counter();targets=[]
    target_counts=collections.Counter()
    pools=[('Heap',0x410524000,0x410924000),('Heap2',0x410924000,0x410c64000),('TextHeap',0x410c64000,0x410e64000)]
    for seq, obs in graphics['texture_observations'].items():
        before=obs.get('before',{});f=before.get('fields',{});addr=int(f.get('raw_source','0'),0)
        pool=next((n for n,a,b in pools if a<=addr<b),'other');counts[pool]+=1
        hs=obs.get('histograms',{})
        valid=obs.get('four_complete_channel_histograms') and obs.get('all_histograms_match_crop_pixel_count')
        allzero=bool(valid) and all(all(int(k)==0 or int(v)==0 for k,v in h['counts'].items()) for h in hs.values())
        if allzero:zero[pool]+=1
        elif valid:nonzero[pool]+=1
        if addr in (0x410977d00,0x41059c400,0x41096aa40,0x41092c540,0x41096bb00):
            target_counts[hex(addr)]+=1
            if target_counts[hex(addr)]<=3:
                targets.append({'sequence':seq,'before_line':before.get('line'),'source':hex(addr),
                                'fields':f,'four_channel_complete':bool(valid),'all_channels_only_bin_zero':allzero,
                                'histograms':hs})
    keep_count=collections.Counter()
    for n,l in enumerate(lines,1):
        kind=None
        if '/usr/share/app/image_' in l and '.uxc' in l:kind='mapped_image_files'
        elif any(s in l for s in ('mpMemoryHeap','mpTextHeap')):kind='heap_logs'
        elif re.match(r'^[A-Za-z_][A-Za-z_0-9]* \d+ \d+ ',l):kind='module_snapshot'
        elif 'ldec' in l.lower():kind='ldec_literal'
        if kind and keep_count[kind]<40:
            snippets.append({'kind':kind,'line':n,'text':l.rstrip('\r')});keep_count[kind]+=1
    result={**receipt(RUN/'serial.log'),'lf_line_count':len(lines),
            'texture_graphics_receipt':receipt(ROOT/'menu-repair-01/runtime/ap102v3observe600-10fbf756-graphics102-v1.json'),
            'observations_by_pool':dict(counts),'complete_all_channels_zero_by_pool':dict(zero),
            'complete_nonzero_by_pool':dict(nonzero),'selected_texture_observations':targets,
            'selected_source_observation_counts':dict(target_counts),
            'serial_snippets':snippets,'serial_ldec_literal_count':sum('ldec' in l.lower() for l in lines),
            'cpio_audit':receipt(RUN/'cpio-audit.json'),
            'cpio_safe_to_unpack':cpio['safe_to_unpack'],
            'candidate_cpio_sha256':cpio['candidate_cpio_sha256'],
            'init_insmod_lines':[{'line':n,'text':l} for n,l in enumerate(cpio['init_text'].split('\n'),1) if 'insmod' in l],
            'init_devtmpfs_lines':[{'line':n,'text':l} for n,l in enumerate(cpio['init_text'].split('\n'),1) if 'devtmpfs' in l],
            'ldec_cpio_members':[m for m in cpio['members'] if 'ldec' in m['path']],
            'init_mentions_ldec': 'ldec' in cpio['init_text']}
    assert result['ldec_cpio_members'][0]['path']=='usr/kmod/ldec.ko'
    assert not result['init_mentions_ldec']
    assert sum(zero.values())>0 and nonzero.get('TextHeap',0)>0
    return result

def replay_open_failure(obj):
    """Execute only original 154c40 open-failure control flow in isolated Unicorn."""
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC
    u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
    for seg in obj.e.iter_segments():
        if seg['p_type']!='PT_LOAD':continue
        lo=seg['p_vaddr']&~4095;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095
        u.mem_map(lo,hi-lo);u.mem_write(seg['p_vaddr'],seg.data())
    mem,stack,stop=0x10000000,0x11000000,0x12000000
    u.mem_map(mem,0x2000);u.mem_map(stack,0x10000);u.mem_map(stop,0x1000)
    u.mem_write(mem+0x10,struct.pack('<Q',mem+0x100));u.mem_write(mem+0x1000,b'\xa5'*4096)
    u.reg_write(UC_ARM64_REG_X0,mem);u.reg_write(UC_ARM64_REG_X30,stop);u.reg_write(UC_ARM64_REG_SP,stack+0xf000)
    visited=[];calls=[]
    def hook(uc,a,n,_):
        visited.append(a)
        if a==stop:uc.emu_stop();return
        if a==0x15ea44:
            calls.append({'callee':'UX log helper (intercepted)','severity':hex(uc.reg_read(UC_ARM64_REG_X0)&0xffffffff),
                          'string':obj.string(uc.reg_read(UC_ARM64_REG_X1))})
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
        elif a==0x55c10:
            calls.append({'callee':'open (stubbed failure)','path':obj.string(uc.reg_read(UC_ARM64_REG_X0)),
                          'flags':uc.reg_read(UC_ARM64_REG_X1),'return':-1})
            uc.reg_write(UC_ARM64_REG_X0,0xffffffffffffffff)
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x154c40,stop+4,count=1000)
    status=u.reg_read(UC_ARM64_REG_X0)&0xffffffff
    assert status==0 and visited[-1]==stop and 0x154c98 in visited
    assert 0x154e84 not in visited and u.mem_read(mem+0x1000,4096)==b'\xa5'*4096
    return {'scope':'Isolated original open-failure branch only; intercepted open/log; no real I/O or pixel decode',
            'return_bool':status,'calls':calls,'visited_VA':[hex(a) for a in visited],
            'ioctl_reached':False,'guard_buffer_unchanged':True,
            'does_not_prove':'AP102 actually called open or its errno; decoded pixels or hardware behavior'}

def main():
    identity()
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump', nargs=2, metavar=('VA', 'BYTES'))
    parser.add_argument('--library', default='libObj.so')
    args = parser.parse_args()
    p = REG/'usr/lib'/args.library
    if args.library.endswith('.ko'): p = AP/'full-v4/regular-files/usr/kmod'/args.library
    obj = Image(p)
    if args.dump:
        obj.show(*(int(x, 0) for x in args.dump))
        return
    cpio=json.loads((RUN/'cpio-audit.json').read_text())
    graphics=json.loads((ROOT/'menu-repair-01/runtime/ap102v3observe600-10fbf756-graphics102-v1.json').read_text())
    proof={'scope':'Read-only original firmware static extraction, saved AP102 v3 evidence and isolated failure-branch replay; no QEMU/device operation',
           'volume_uuid':identity(),'audit_script':receipt(Path(__file__).resolve()),
           'resources':image_inventory(cpio),'original_libObj':original_evidence(obj),
           'original_ldec':kernel_evidence(),'runtime':runtime_evidence(cpio,graphics),
           'open_failure_original_replay':replay_open_failure(obj),
           'ldec_ioctl_ABI':{'command':1,'bytes':32,'fields':[
               {'offset':0,'type':'u64','name':'source_virtual'},
               {'offset':8,'type':'u32','name':'source_bytes'},
               {'offset':12,'type':'u32','name':'destination_native_p32'},
               {'offset':16,'type':'u32','name':'destination_bytes'},
               {'offset':20,'type':'u32','name':'records_ceil_destination_bytes_over_4096'},
               {'offset':24,'type':'u32','name':'DMA_channel','observed_constructor_value':8},
               {'offset':28,'type':'u8','name':'source_cache_bypass','value':0},
               {'offset':29,'type':'u8','name':'destination_cache_bypass','value':1},
               {'offset':30,'type':'u8[2]','name':'reserved','value':'0000'}]},
           'findings':[
               {'level':'A1','finding':'All 51642 valid uxd records are encoding4, resource pixel format0; factory selects hardware Lz77Decoder for encoding4/6.'},
               {'level':'A1','finding':'image.uxb also contains 831 inline PNG encoding1 records; generic software PNG branch exists, runtime binding to these records unproven.'},
               {'level':'A2','finding':'All image files match AP102 v3 CPIO entries; retained maps/FD lines demonstrate three _43 uxd files were opened/mapped.'},
               {'level':'B-strong','finding':'Missing LDEC device/provider is the leading failure: packaged module is not in init insmod list; saved serial lacks any LDEC record; source textures are zero.'},
               {'level':'A1','finding':'open(/dev/ldec,O_RDWR) failure returns false before acquiring output bits or submitting ioctl; there is no software fallback in this branch.'},
               {'level':'A1','finding':'FX3 ioctl is 32 bytes, native p32 destination at +12; driver uses DMA330 and synchronous hardware IRQ wait, not CP/UIPC/ICDT.'}],
           'unproven':[
               'Actual AP102 Lz77Decoder entry, open return and errno, ioctl return, current log mask and every active preload interposition.' ,
               'Exact resource ID/object identity for observed highlighter/panel/icon source addresses; dimension matches alone are not identity.',
               'Full LZ77 token grammar, history window, block/dictionary reset rules, byte order and malformed stream behavior; cannot yet implement bit-exact software decompression.',
               'No decoded original image pixels, software backend, new guest run, visual/interaction repair or camera/hardware acceptance is supplied.',
               'Whether failed DecodeImageCommand is cached or propagated further in the worker/UI; local false return is proven, global error swallowing is not.',
               'image.uxb literal path is absent from global.xdb; file presence and embedded PNGs do not prove current use.'],
           'reference':{'url':'https://www.capstone-engine.org/lang_python.html','used_for':'Disassembly API only; all Sony semantics are original local bytes.'}}
    dest=OUT/'ui-image-load-proof.json'
    dest.write_text(json.dumps(proof,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print('PASS: rebuilt',dest)
    print('uxd_records=51642 inline_PNG_records=831', 'texture_zero_counts='+str(proof['runtime']['complete_all_channels_zero_by_pool']))

if __name__ == '__main__':
    main()
