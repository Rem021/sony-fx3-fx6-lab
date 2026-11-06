#!/usr/bin/env python3
"""AP89 read-only audit: original command routing, text-mask and allocation evidence.

Only writes adjacent gpe-fmt2-proof.json. No QEMU, device, guest syscall, or pixel
backend executes. Unicorn replays isolated original descriptor generators, stopping
before their submission. Proposed pixels are explicitly synthetic, not an oracle.
"""
from pathlib import Path
from io import BytesIO
import collections
import hashlib
import json
import plistlib
import re
import runpy
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
from unicorn import arm64_const as ar

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'menu-repair-01').is_dir())
AP = ROOT / 'menu-repair-01/original-uipc/ap-projection'
RUN = ROOT / 'menu-repair-01/runtime/runs/ap89r2replay-a55f292d'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
CS = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
PINS = {
    'audit_gpe_blend.py':'88effc3d0cf05c7027d30e1b7a505e88cad96ba001e55815c9300a422dff0bc1',
    'grm_ma.ko':'6b579c7632bb90a6fe8c97d037abe24f5eb6b840823aa3a0ac8fdbed61ceee12',
    'dmm.ko':'1e28a4921b36cd8866330a6670d72627d347c556dbea8568cd5b3ab60853e65a',
    'appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'serial.log':'897dd55e283097e38fa70d286a3dce1bbd252d225c48cf78a5fb515d07ea1c5d',
    'ap89-gpe-command-statistics.json':'21e7b9e002f6b683b34539b1f8a8e36cf6b2fb9f20cc127b6609d789e584b2fe',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def original(p, expected=None):
    h = sha(p)
    if expected:
        assert h == expected, (str(p), h)
    return {'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': h}


class ELF:
    def __init__(self, path):
        self.path = path
        self.raw = path.read_bytes()
        self.elf = ELFFile(BytesIO(self.raw))
        self.loads = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        self.rel = {}
        for s in self.elf.iter_sections():
            if s['sh_type'] == 'SHT_RELA':
                for r in s.iter_relocations():
                    self.rel[(s.name, r['r_offset'])] = r

    def read(self, va, size):
        s = next(s for s in self.loads if s['p_vaddr'] <= va and
                 va + size <= s['p_vaddr'] + s['p_filesz'])
        o = s['p_offset'] + va - s['p_vaddr']
        return self.raw[o:o + size]

    def block(self, a, b, section=None):
        raw = self.read(a, b-a) if section is None else self.elf.get_section_by_name(section).data()[a:b]
        out = []
        sy = self.elf.get_section_by_name('.symtab')
        for i in CS.disasm(raw, a):
            row = {'va': hex(i.address), 'bytes': i.bytes.hex(), 'asm': i.mnemonic+' '+i.op_str}
            r = self.rel.get(('.rela'+section, i.address)) if section else None
            if r:
                s = sy.get_symbol(r['r_info_sym'])
                row['relocation'] = {'symbol': s.name, 'addend': hex(r['r_addend']),
                                     'section': str(s['st_shndx'])}
            out.append(row)
        return {'start': hex(a), 'end_exclusive': hex(b), 'section': section,
                'raw_sha256': hashlib.sha256(raw).hexdigest(), 'instructions': out}


def u32(p, o):
    return struct.unpack_from('<I', p, o)[0]


def u64(p, o):
    return struct.unpack_from('<Q', p, o)[0]


def decode(p):
    q = {'dst_phys': hex(u64(p, 0)), 'src_phys': hex(u64(p, 0x38)),
         'dst_fmt': u32(p, 0x34), 'src_fmt': u32(p, 0x5c),
         'selector_70': p[0x70], 'conversion_71': p[0x71], 'alpha_72': p[0x72],
         'color_6c_6f': list(p[0x6c:0x70]), 'flags_73_78': list(p[0x73:0x79]),
         'async_79': p[0x79], 'callback': hex(u64(p, 0x80)),
         'callback_argument': hex(u64(p, 0x88)), 'raw_hex': p.hex()}
    for name, off in [('dst_xy', 8), ('dst_wh', 0x10), ('clip_xy', 0x18),
                      ('clip_wh', 0x20), ('dst_adjust', 0x28), ('src_xy', 0x40),
                      ('src_wh', 0x48), ('src_adjust', 0x50)]:
        q[name] = list(struct.unpack_from('<2I', p, off))
    q['dst_stride_pixels'], q['src_stride_pixels'] = u32(p, 0x30), u32(p, 0x58)
    q['scale_raw'] = [hex(u32(p, o)) for o in (0x60, 0x64)]
    q['scale_float'] = list(struct.unpack_from('<2f', p, 0x60))
    q['rotation_68'] = u32(p, 0x68)
    return q


def route(p):
    """Independent translation of cf2c..d144, compared with original replay."""
    if p[0x70] == 2:
        return 'error_selector2'
    if u32(p, 0x68):
        return '0xc878'
    if p[0x10:0x18] != p[0x48:0x50]:
        sx, sy = struct.unpack_from('<2f', p, 0x60)
        eps = struct.unpack('<f', gpe.read(0x15134, 4))[0]
        if not p[0x74] or not (abs(sx-1) < eps and abs(sy-1) < eps):
            return '0xc878'
        return '0xbbcc'
    if any(p[0x73:0x79]):
        return '0xbbcc'
    s, d = u32(p, 0x5c), u32(p, 0x34)
    if p[0x70] == 0 and p[0x72] == 255:
        return '0xb578' if s == d or (s <= 1 and d <= 2) or (s == 3 and d == 1) else '0xbbcc'
    return '0xb234' if s == d and d <= 1 else '0xbbcc'


def synthetic_pixel(mask, color, dst, k=255):
    """Proposed A8 mask extension of Lead straight_over_v1; NOT Sony pixels."""
    rnd = lambda n: (n+127)//255
    a = rnd(rnd(mask*color[3])*k)
    rgb = [rnd(color[c]*a + dst[c]*(255-a)) for c in range(3)]
    out = rgb+[a+rnd(dst[3]*(255-a))]
    n = [min(15, (v+8)//17) for v in out]
    return {'a8': a, 'output8': out, 'fmt0_value': hex(sum(v << (12-4*i) for i,v in enumerate(n)))}


def main():
    global gpe
    info = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert info.get('VolumeUUID') == UUID and info.get('MountPoint') == '/Volumes/KAFU2T'
    provider_path = HERE.parent / 'gpe-blend-p3/audit_gpe_blend.py'
    original(provider_path, PINS[provider_path.name])
    # Reuse the prior bounded harness read-only. run_path does not run its main().
    provider = runpy.run_path(str(provider_path), run_name='fmt2_readonly_provider')
    gpe = provider['Image']('libgpe.so')
    obj = provider['Image']('libObj.so')
    BaseReplay = provider['Replay']

    class Replay(BaseReplay):
        def hook(self, uc, address, size, arg):
            name = self.image.plt.get(address, '')
            if 'StretchRotateBlit' in name:
                # Original public entry, original stack/arguments, no patch.
                uc.reg_write(ar.UC_ARM64_REG_PC, 0xc878)
                return
            if name in ('cslMakeZoomSprite', 'cslMakeZoomRotateSprite'):
                self.other.append({'kind': name, 'caller_va': hex(self.reg(30)-4),
                    'dst_x': self.reg(1)&0xffffffff, 'dst_y': self.reg(2)&0xffffffff,
                    'src_struct40': bytes(uc.mem_read(self.reg(0), 40)).hex(),
                    'scale_float': [struct.unpack('<f', struct.pack('<I',uc.reg_read(r)&0xffffffff))[0]
                                    for r in (ar.UC_ARM64_REG_S0, ar.UC_ARM64_REG_S1)]})
                self.ret()
                return
            super().hook(uc, address, size, arg)

    replay = Replay(gpe)
    serial = (RUN/'serial.log').read_bytes()
    lines = serial.split(b'\n')  # LF lines, matching coordinator statistics; never split CR.
    records, cmd, evidence = [], [], []
    for n, line in enumerate(lines, 1):
        if b'FX3_GPE_CMD op=' in line:
            cmd.append({'serial_LF_line': n, 'text': line.decode(errors='replace')})
        if any(v in line for v in (b'mpMemoryHeap', b'mpTextHeap', b'MOUNT_ERR_EXTMEDIA_SLOT1',
                                  b'open screen: scr0099', b'open screen:', b'FX3_GRM_MA_RC')):
            evidence.append({'serial_LF_line': n, 'text': line.decode(errors='replace')})
        m = re.search(rb'FX3_GPE_REJECT_PARAMS op=BitBlit seq=(\d+) read=1 len=144 raw_hex=([0-9a-f]{288})(?![0-9a-f])', line)
        if not m:
            continue
        p = bytes.fromhex(m[2].decode())
        q = decode(p)
        q.update(sequence=int(m[1]), serial_LF_line=n)
        q['original_replay'] = replay.run(0xcf2c, p)
        q['dispatch'] = route(p)
        assert q['original_replay']['status'] == 'submission_intercepted'
        assert q['original_replay']['route'] == [q['dispatch']]
        records.append(q)
    assert len(records) == 73
    assert collections.Counter(q['dispatch'] for q in records) == {'0xbbcc':37,'0xc878':36}
    assert collections.Counter(q['src_fmt'] for q in records) == {0:64,2:9}
    assert all(q['dst_fmt']==0 and q['flags_73_78'][0]==1 and q['selector_70']==1 and
               q['conversion_71']==0 and q['alpha_72']==255 for q in records)
    assert all(q['flags_73_78'] == [1,0,14 if q['src_fmt']==2 else 0,0,0,0] for q in records)
    assert all(q['color_6c_6f'] == ([221,221,221,255] if q['src_fmt']==2 else [0,0,0,0]) for q in records)
    groups = collections.Counter((q['src_fmt'],q['dst_fmt'],q['dispatch'],
                                 tuple(q['flags_73_78']),tuple(q['color_6c_6f'])) for q in records)

    # Preserve all original extent and unit rows. type != id != unit handle.
    ext, units = [], []
    er = re.compile(rb'^([0-9a-f]{4})\s+([0-9a-f]{4})\s+([0-9a-f]{8})\s+([0-9a-f]{8})\s+([0-9a-f]{8})\s+([0-9a-f]{8})\s+([0-9a-f]{8})\s+([0-9a-f]{8})\s+([0-9a-f]+)\s+\(([0-9a-f]+)\+([0-9a-f]+)\)\s+([0-9a-f]+)')
    names = ['id','parent','attr','type','table','pict_id','relation','serial','address','base','offset','size']
    for n, line in enumerate(lines,1):
        m = er.match(line)
        if m:
            v = dict(zip(names,[int(x,16) for x in m.groups()]))
            assert v['address']==v['base']+v['offset']
            ext.append({'serial_LF_line':n,'text':line.decode(),**{k:hex(x) for k,x in v.items()}})
        if re.match(rb'[0-9a-f]{4}\s+',line) and b' < ' in line:
            units.append({'serial_LF_line':n,'text':line.decode(errors='replace')})
    assert ext
    heaps=[]
    for x in evidence:
        m = re.search(r'(mpMemoryHeap2?|mpTextHeap) on (0x[0-9a-fA-F]+)-(0x[0-9a-fA-F]+) \((\d+)\)',x['text'])
        if m:
            lo,hi=int(m[2],16),int(m[3],16)
            assert hi-lo==int(m[4])
            heaps.append({'name':m[1],'base':hex(lo),'end_exclusive':hex(hi),'bytes':hi-lo,
                          'serial_LF_line':x['serial_LF_line'],'actual_handle':'unproven',
                          'matching_saved_extents':[z for z in ext if int(z['address'],16)<=lo and hi<=int(z['address'],16)+int(z['size'],16)]})
    assert len(heaps)==3 and all(not h['matching_saved_extents'] for h in heaps)
    source_groups=[]
    for address,count in sorted(collections.Counter(q['src_phys'] for q in records).items()):
        a=int(address,16)
        owner=[h for h in heaps if int(h['base'],16)<=a<int(h['end_exclusive'],16)]
        assert len(owner)==1
        source_groups.append({'physical':address,'count':count,'heap':owner[0]['name'],
                              'heap_offset':hex(a-int(owner[0]['base'],16)),
                              'matching_saved_extents':[z for z in ext if int(z['address'],16)<=a<int(z['address'],16)+int(z['size'],16)]})
    grm = ELF(AP/'full-v4/regular-files/usr/kmod/grm_ma.ko')
    dmm = ELF(AP/'full-v4/regular-files/usr/kmod/dmm.ko')
    app = ELF(AP/'regular-files/usr/lib/appFw.so')
    ranges_gpe = [(0xcf2c,0xd148),(0xbbcc,0xc154),(0xc878,0xcf2c),(0xb1f4,0xb234),(0xb234,0xb578)]
    ranges_obj = [(0x101970,0x101d20),(0x10e750,0x10eaf0),(0x133644,0x133660),
                  (0x15ab5c,0x15ac1c),(0x5c474,0x5c820),(0x5f970,0x5fa4c),
                  (0x15e920,0x15e9a0),(0x16af88,0x16b044),
                  (0x101d84,0x101e2c),(0x102394,0x102434),(0x1031b0,0x1032f4),
                  (0xf96f4,0xf97f0),(0x103454,0x103550),(0x103550,0x10374c),
                  (0x102b98,0x102c08),(0x102c08,0x102cc0),(0x151284,0x1514e8)]
    kernel_ranges = {'grm_ma.ko':[(0x1d0,0x2dc),(0x4a8,0x570),(0x5c0,0x65c),(0x6a0,0x744),
                                  (0xa30,0xb10),(0xb50,0xbe4),
                                  (0x11e0,0x12c8),(0x1428,0x1520),(0x1708,0x18f0)],
                     'dmm.ko':[(0x5d0,0x8f0),(0xb5f0,0xb680),(0xb768,0xb7a0)]}
    vectors=[]
    for mask in (0,1,15,16,127,128,254,255):
        for c,d in [([221,221,221,255],[0,0,0,255]),([253,31,199,128],[17,85,153,68])]:
            vectors.append({'mask':mask,'color':c,'dst8':d,'K':255,
                            **synthetic_pixel(mask,c,d)})
    stats_path=ROOT/'menu-repair-01/runtime/ap89-gpe-command-statistics.json'
    stats=json.loads(stats_path.read_text())
    stats_blits = [q for q in stats['rejected_full_raw'] if q['op']=='BitBlit']
    assert [(int(q['seq']),q['raw_hex']) for q in stats_blits] == [(q['sequence'],q['raw_hex']) for q in records]
    fmt2_regs=[r for q in records if q['src_fmt']==2 for r in q['original_replay']['register_writes']]
    assert any(r['reg']=='0x464' and r['value']==0x21 for r in fmt2_regs)
    assert any(r['reg']=='0x740' and r['value']==14 for r in fmt2_regs)
    assert any(r['reg']=='0x741' and r['value']==0xddddddff for r in fmt2_regs)
    doc={'schema':1,'scope':'static original bytes, bounded descriptor replay, saved AP89 LF lines; no QEMU or device',
         'volume_uuid':UUID,'script':original(Path(__file__).resolve()),
         'inputs':{p.name:original(p,PINS.get(p.name)) for p in [provider_path, gpe.path,obj.path,grm.path,dmm.path,app.path,RUN/'serial.log',stats_path]},
         'counts':{'complete_rejected_blits':len(records),'source_formats':{'0':64,'2':9},
                   'routes':{'generic_bbcc':37,'stretch_c878':36,'fast_b234':0,'convert_b578':0},
                   'groups':[{'src_fmt':k[0],'dst_fmt':k[1],'route':k[2],'flags':list(k[3]),'color':list(k[4]),'count':v} for k,v in sorted(groups.items())]},
         'runtime_evidence':evidence,'gpe_cmd_markers':cmd,'commands':records,
         'resource_heaps':heaps,'source_addresses':source_groups,'saved_proc_extents':ext,'saved_proc_units':units,
         'gpe_original':[{'range':[hex(a),hex(b)],'instructions':gpe.block(a,b)} for a,b in ranges_gpe],
         'obj_original':[{'range':[hex(a),hex(b)],'instructions':obj.block(a,b)} for a,b in ranges_obj],
         'kernel_original':{name:[im.block(a,b,'.text') for a,b in kernel_ranges[name]] for name,im in [('grm_ma.ko',grm),('dmm.ko',dmm)]},
         'kernel_proc_strings':{name:im.elf.get_section_by_name('.rodata.str1.8').data().hex() for name,im in [('grm_ma.ko',grm),('dmm.ko',dmm)]},
         'dialog_static':{'rtti_name_va':'0x3035b40','rtti_name':app.read(0x3035b40,28).split(b'\0')[0].decode(),
                          'rtti_va':'0x42b6a20','vtable_va':'0x42b6d08',
                          'controller_methods':app.block(0x1c9bc78,0x1c9bdd4)},
         'proposed_mask_formula':{'level':'B semantics / U hardware arithmetic; explicit approximation only',
             'name':'a8_color_straight_over_v1_candidate','round255':'(n+127)//255',
             'source':'Cs=color[0:3], As=round255(mask*color[3]); then Lead straight_over_v1',
             'warning':'Not proof of reg740 opcode14 or hardware format0x21 channel semantics',
             'synthetic_vectors':vectors},
         'unproven':['hardware fmt2 general A8/L8 semantics and opcode14 pixel operation',
                     'hardware source-over factors, gamma, rounding, 4-bit quantization',
                     'stretch reg467=1 sampling filter and source coordinate rules',
                     'exact resource DMM handles/types/generations absent from saved proc extents',
                     'allocation/free interception or read lease is not implemented or guest-tested',
                     'dialog exact localized text/resource ID and menu visual/input acceptance'],
         'external_reference':{'url':'https://docs.kernel.org/core-api/dma-api.html',
             'use':'General lifetime terminology only; does not define proprietary Sony DMM or proc schema'}}
    out=HERE/'gpe-fmt2-proof.json'
    out.write_text(json.dumps(doc,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'exit':0,'proof':str(out),'replayed':len(records),'routes':doc['counts']['routes'],
                      'fmt2':9,'resource_heaps':len(heaps),'saved_extent_rows':len(ext),
                      'unknown_resource_handles':True,'synthetic_pixel_vectors':len(vectors)},ensure_ascii=False))


if __name__ == '__main__':
    main()
