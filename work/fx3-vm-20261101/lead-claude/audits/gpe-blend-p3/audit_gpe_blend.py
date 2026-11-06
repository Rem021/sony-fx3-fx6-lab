#!/usr/bin/env python3
"""Read-only, bounded original-code descriptor audit; never runs QEMU or hardware.

Only writes adjacent gpe-blend-proof.json. Unicorn executes isolated AArch64
arithmetic/control flow; every external service and hardware submission is hooked.
This is evidence of register PROGRAMMING, not of the device's pixel arithmetic.
"""
from pathlib import Path
from io import BytesIO
import hashlib
import itertools
import json
import plistlib
import re
import struct
import subprocess

import capstone
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm64_const as ar

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'menu-repair-01').is_dir())
AP = ROOT / 'menu-repair-01/original-uipc/ap-projection/regular-files'
UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
PIN = {
    'libgpe.so': '363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464',
    'libObj.so': 'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
}
CS = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)


class Image:
    def __init__(self, name):
        self.path = AP / 'usr/lib' / name
        self.data = self.path.read_bytes()
        self.sha = hashlib.sha256(self.data).hexdigest()
        assert self.sha == PIN[name], (name, 'different original build', self.sha)
        self.elf = ELFFile(BytesIO(self.data))
        self.segments = [s for s in self.elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        ds = self.elf.get_section_by_name('.dynsym')
        plt = self.elf.get_section_by_name('.plt')
        self.plt = {
            plt['sh_addr'] + 32 + 16 * n: ds.get_symbol(r['r_info_sym']).name
            for n, r in enumerate(self.elf.get_section_by_name('.rela.plt').iter_relocations())
        }
        self.exports = {s.name: (s['st_value'], s['st_size']) for s in ds.iter_symbols()
                        if s['st_shndx'] != 'SHN_UNDEF'}

    def read(self, va, size):
        s = next(s for s in self.segments if s['p_vaddr'] <= va and
                 va + size <= s['p_vaddr'] + s['p_filesz'])
        off = s['p_offset'] + va - s['p_vaddr']
        return self.data[off:off + size]

    def block(self, start, end):
        result = []
        for i in CS.disasm(self.read(start, end-start), start):
            row = {'va': hex(i.address), 'bytes': i.bytes.hex(),
                   'asm': i.mnemonic + ' ' + i.op_str}
            if i.mnemonic in ('bl', 'b') and i.op_str.startswith('#'):
                target = int(i.op_str[1:], 16)
                if target in self.plt:
                    row['callee'] = self.plt[target]
            result.append(row)
        assert len(result) * 4 == end - start
        return result


class Replay:
    """Isolated original-code execution; no OS syscalls, DMM or framebuffer.

    Code, constants and a synthetic parameter/stack are the only memory mapped.
    All register descriptors are captured BEFORE csl/hardware transmission.
    No AArch64 original instruction bytes are patched.
    """
    STACK, PARAM, STOP = 0x3000000, 0x4000000, 0x5000000

    def __init__(self, image):
        self.image = image
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        end = max(s['p_vaddr']+s['p_memsz'] for s in image.segments)
        self.uc.mem_map(0, (end+4095)//4096*4096)
        for s in image.segments:
            self.uc.mem_write(s['p_vaddr'], image.data[s['p_offset']:s['p_offset']+s['p_filesz']])
        for address, size in [(self.STACK, 0x20000), (self.PARAM, 0x10000), (self.STOP, 0x1000)]:
            self.uc.mem_map(address, size)
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def reg(self, n):
        return self.uc.reg_read(getattr(ar, 'UC_ARM64_REG_X'+str(n)))

    def ret(self, value=0):
        self.uc.reg_write(ar.UC_ARM64_REG_X0, value)
        self.uc.reg_write(ar.UC_ARM64_REG_PC, self.reg(30))

    def hook(self, uc, address, size, _):
        self.steps += 1
        if address == self.STOP:
            self.status = 'returned'
            uc.emu_stop()
        elif self.image.path.name == 'libgpe.so':
            if address in (0xb234, 0xb578, 0xbbcc, 0xc878):
                self.route.append(hex(address))
            if address == 0xadac:
                self.writes.append({'reg': hex(self.reg(0)&0xffff),
                                    'value': self.reg(1)&0xffffffff,
                                    'caller_va': hex(self.reg(30)-4)})
                self.ret()
            elif address in (0xae14,):
                self.other.append({'kind': 'special_register', 'reg': self.reg(0),
                                   'value': self.reg(1)&0xffffffff,
                                   'caller_va': hex(self.reg(30)-4)})
                self.ret()
            elif address == 0xaf30:
                self.status = 'submission_intercepted'
                uc.emu_stop()
            elif address in (0xaddc, 0xaf08):
                self.ret()  # completion bookkeeping only, never delivers a message
            elif address in self.image.plt:
                name = self.image.plt[address]
                if name == '__assert_fail':
                    self.status = 'original_assert'
                    self.assert_va = hex(self.reg(30)-4)
                    uc.emu_stop()
                elif name.startswith('gpe_blog_'):
                    self.ret()
                elif name in ('cslClearSat', 'cslClearSrc'):
                    n = self.reg(1) * (64 if name == 'cslClearSat' else 38)
                    assert n <= 0x10000
                    uc.mem_write(self.reg(0), bytes(n))
                    self.ret()
                elif name == 'cslMakeSimpleSprite':
                    self.other.append({'kind': name, 'x': self.reg(1)&0xffffffff,
                                       'y': self.reg(2)&0xffffffff,
                                       'src_struct40': bytes(uc.mem_read(self.reg(0),40)).hex(),
                                       'caller_va': hex(self.reg(30)-4)})
                    self.ret()
                elif name == 'cslChangeHVFlip':
                    self.other.append({'kind': name, 'h': self.reg(1)&255,
                                       'v': self.reg(2)&255,
                                       'caller_va': hex(self.reg(30)-4)})
                    self.ret()
                elif 'StretchRotateBlit' in name:
                    self.status = 'out_of_scope_stretch_rotate'
                    uc.emu_stop()
                else:
                    raise AssertionError(('unexpected external call', hex(address), name))
        elif address in self.image.plt:
            raise AssertionError(('unexpected libObj external call', hex(address), self.image.plt[address]))

    def run(self, entry, raw=b'', args=None):
        self.writes, self.other, self.route = [], [], []
        self.steps, self.status, self.assert_va = 0, None, None
        self.uc.mem_write(self.STACK, bytes(0x20000))
        self.uc.mem_write(self.PARAM, bytes(0x10000))
        self.uc.mem_write(self.PARAM, bytes(raw))
        for n in range(31):
            self.uc.reg_write(getattr(ar, 'UC_ARM64_REG_X'+str(n)), 0)
        self.uc.reg_write(ar.UC_ARM64_REG_SP, self.STACK+0x1f000)
        self.uc.reg_write(ar.UC_ARM64_REG_X30, self.STOP)
        self.uc.reg_write(ar.UC_ARM64_REG_NZCV, 0)
        values = [0, 0, 7, 9, self.PARAM] if args is None else args
        for n, value in enumerate(values):
            self.uc.reg_write(getattr(ar, 'UC_ARM64_REG_X'+str(n)), value)
        self.uc.emu_start(entry, self.STOP+4, count=20000)
        assert self.status is not None, ('instruction budget reached', hex(entry))
        return {'status': self.status, 'return_x0': self.reg(0), 'route': self.route[:],
                'register_writes': self.writes[:], 'other_descriptors': self.other[:],
                **({'assert_caller_va': self.assert_va} if self.assert_va else {})}


def fill_param(fmt, selector, alpha):
    p = bytearray(56)
    struct.pack_into('<Q6I', p, 0, 0x410000100, 2, 3, 8, 8, 16, fmt)
    p[0x20:0x24] = bytes.fromhex('12345678')
    p[0x24:0x27] = bytes([selector, alpha, 1])
    return p


def blit_param(dst=1, src=1, selector=0, alpha=255, flags=None, conversion=0):
    p = bytearray(144)
    for off, value in [(0x00, 0x410000100), (0x38, 0x420000200)]:
        struct.pack_into('<Q', p, off, value)
    for off, value in [(8,2),(12,3),(16,8),(20,8),(24,0),(28,0),(32,64),(36,64),
                       (0x30,16),(0x34,dst),(0x40,1),(0x44,2),(0x48,8),(0x4c,8),
                       (0x58,16),(0x5c,src)]:
        struct.pack_into('<I', p, off, value)
    p[0x6c:0x70] = bytes.fromhex('12345678')
    p[0x70:0x73] = bytes([selector,conversion,alpha])
    if flags:
        for offset,value in flags.items(): p[offset] = value
    p[0x79] = 1
    return p


def values(result, start, end):
    return [(int(w['reg'],16),w['value']) for w in result['register_writes']
            if start <= int(w['reg'],16) <= end]


def expected_blend(selector, alpha, base, fill=False):
    # Independent recovered branch specification, checked against original instructions.
    # base b01 or generic 760; generic 770/771/772/773/774 correspond to b02..b06.
    r = lambda n: (base+n if base==0xb01 else {0:0x760,1:0x770,2:0x771,3:0x772,4:0x773,5:0x774}[n])
    if selector == 0:
        if alpha == 255: return [(r(0),0)]
        return [(r(0),1),(r(1),0x09080901),(r(2),0),(r(3),alpha),(r(4),alpha)]
    if selector == 2 and fill:
        return [(r(0),1),(r(1),0x0c000100),(r(2),0),(r(4),alpha*0x01010100)]
    out = [(r(0),1 if alpha == 255 else 3)]
    if alpha != 255: out.append((r(5),alpha))
    return out+[(r(1),0x05040501),(r(2),0)]


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume.get('VolumeUUID','').upper() == UUID, 'Target volume identity mismatch'
    gpe, obj = Image('libgpe.so'), Image('libObj.so')
    libraries = {}
    blocks = {
        'libgpe.so': [(0xadac,0xae50),(0xaf98,0xb074),(0xb1f4,0xb234),
                      (0xb234,0xb810),(0xbbcc,0xc154),(0xc30c,0xc760),(0xcf2c,0xd148)],
        'libObj.so': [(0xfb4dc,0xfb594),(0x1017ac,0x101d20),(0x1528b8,0x152960),
                      (0x1535e4,0x153714),(0x153860,0x153940),
                      (0x13364c,0x133820),(0x160134,0x16053c),
                      (0x1606d8,0x16096c),(0x161ee4,0x161ef4),(0x162370,0x1623b0),
                      (0x172840,0x172860)]
    }
    for image in (gpe,obj):
        libraries[image.path.name] = {'path':str(image.path),'sha256':image.sha,
            'blocks':{hex(a):image.block(a,z) for a,z in blocks[image.path.name]}}
    # Preserve the actual low-level flag modifier too (not merely its name).
    for name in ['cslChangeHVFlip','cslMakeSimpleSprite','cslClearSrc']:
        a,n = gpe.exports[name]
        libraries['libgpe.so']['blocks'][hex(a)] = gpe.block(a,a+n)
    tables = {}
    for a,n in [(0x15130,4),(0x151f8,4),(0x15200,4),(0x15208,3),(0x15210,4),
                (0x15228,56),(0x15260,56),(0x15298,56)]:
        raw = gpe.read(a,n)
        tables[hex(a)] = {'bytes':raw.hex(), 'u8':list(raw)}
        if n==56:
            pairs = list(struct.iter_unpack('<II',raw))
            tables[hex(a)]['register_pairs'] = [[hex(r),v] for r,v in pairs]
            tables[hex(a)]['signed_11bit_candidate'] = [v-2048 if v&1024 else v for _,v in pairs]
    obj_tables = {hex(a):obj.read(a,8).hex() for a in (0x1e220c,0x1e2214,0x1e221c)}
    obj_tables['0x1e5be0_stella_Color_ZERO'] = obj.read(0x1e5be0,4).hex()
    relocations = {}
    for relocation in obj.elf.get_section_by_name('.rela.dyn').iter_relocations():
        if relocation['r_offset'] in (0x262718,0x262838,0x262e88,0x2621a0):
            assert relocation['r_info_type']==1027  # R_AARCH64_RELATIVE
            relocations[hex(relocation['r_offset'])] = hex(relocation['r_addend'])
    assert relocations=={'0x262718':'0x160134','0x262838':'0x16031c',
                         '0x262e88':'0x160224','0x2621a0':'0x160414'}
    replay = Replay(gpe)
    checks, cases = 0, []
    alphas = [0,1,15,16,127,128,254,255]
    for fmt,selector,alpha in itertools.product(range(5),range(4),alphas):
        result = replay.run(0xc30c,fill_param(fmt,selector,alpha))
        valid = (selector==0 and fmt<=3) or (selector in (1,2) and fmt<=1)
        assert (result['status']=='submission_intercepted')==valid, (fmt,selector,alpha,result)
        if valid:
            assert values(result,0xb01,0xb06)==expected_blend(selector,alpha,0xb01,True)
            b10 = [0xe1,0xe0,0xe2,0xe1][fmt] if selector==0 else [0xe3,0xe1][fmt]
            assert values(result,0xb10,0xb10)==[(0xb10,b10)]
            c = 0x1357 if fmt==0 else 0x12345678 if fmt==1 else 0
            assert values(result,0xb07,0xb07)==[(0xb07,c)]
        checks += 1
        cases.append({'op':'FillRect','format':fmt,'selector':selector,'alpha':alpha,**result})
    # Cover natural BitBlit dispatcher, including unsupported selector 2 and
    # noncanonical selector 3/255 (the original treats them like selector 1).
    for dst,src,selector,alpha in itertools.product(range(5),range(5),[0,1,2,3,255],[0,127,255]):
        conversion = 1 if src==3 else 0
        result = replay.run(0xcf2c,blit_param(dst,src,selector,alpha,conversion=conversion))
        if selector==2:
            assert result['status']=='returned' and result['return_x0']==1
        else:
            pure = selector==0 and alpha==255
            expected = (0xb578 if pure and (dst==src or (src<=1 and dst<=2) or (src==3 and dst==1))
                        else 0xb234 if not pure and src==dst and dst<=1 else 0xbbcc)
            assert result['route']==[hex(expected)],(dst,src,selector,alpha,result)
            if expected==0xb578:
                allowed = (dst==0 and src<=1) or (dst==1 and src in (0,1,3)) or (dst==2 and src<=2)
                assert (result['status']=='submission_intercepted')==allowed
                if allowed:
                    code = {(0,0):1,(0,1):8,(1,0):24,(1,1):0,(1,3):40,
                            (2,0):29,(2,1):11,(2,2):2}[(dst,src)]
                    assert values(result,0xb01,0xb01)==[(0xb01,0)]
                    assert values(result,0xb10,0xb10)==[(0xb10,code)]
            elif expected==0xb234:
                assert values(result,0xb01,0xb06)==expected_blend(selector,alpha,0xb01)
                assert values(result,0xb10,0xb10)==[(0xb10,3 if dst==0 else 1)]
            else:
                assert values(result,0x760,0x774)==expected_blend(selector,alpha,0x760),(dst,src,selector,alpha,result)
        checks += 1
        cases.append({'op':'BitBlit','dst_format':dst,'src_format':src,
                      'selector':selector,'alpha':alpha,'conversion':conversion,**result})
    flag_cases = []
    for offset,value,selector,alpha in itertools.product(range(0x73,0x79),[1,2,15,16,255],[0,1],[127,255]):
        result = replay.run(0xcf2c,blit_param(selector=selector,alpha=alpha,flags={offset:value}))
        assert result['route']==['0xbbcc']
        assert values(result,0x760,0x774)==expected_blend(selector,alpha,0x760)
        if offset==0x75: assert values(result,0x740,0x740)==[(0x740,value&15)]
        if offset==0x76: assert values(result,0x730,0x730)==[(0x730,value&15)]
        assert values(result,0x741,0x741)==[(0x741,0x12345678)]
        checks += 1
        flag_cases.append({'offset':hex(offset),'value':value,'selector':selector,'alpha':alpha,**result})
    conversion_cases = []
    for mode in range(6):
        result = replay.run(0xaf98,args=[mode,Replay.PARAM+0x1000])
        if mode in range(1,5):
            assert result['status']=='returned' and result['return_x0']==8
            table = {1:0x15260,2:0x15228,3:0x15298,4:0x15298}[mode]
            want = [(0x900,0x00d80001 if mode in (2,3) else 0x00d80000)]
            want += list(struct.iter_unpack('<II',gpe.read(table,56)))
            assert values(result,0x900,0x918)==want
        else:
            assert result['status']=='original_assert'
        checks += 1
        conversion_cases.append({'mode':mode,**result})
    # Full u8 alpha sweep checks unquantized programming, without a huge repeated
    # JSON trace. Digest is a receipt for the exact descriptor streams checked.
    sweep_hash = hashlib.sha256()
    sweep_cases = 0
    for fmt,selector,alpha in itertools.product(range(2),range(3),range(256)):
        result = replay.run(0xc30c,fill_param(fmt,selector,alpha))
        assert result['status']=='submission_intercepted'
        assert values(result,0xb01,0xb06)==expected_blend(selector,alpha,0xb01,True)
        sweep_hash.update(json.dumps([fmt,selector,alpha,result],sort_keys=True).encode())
        checks += 1
        sweep_cases += 1
    for fmt,selector,alpha,generic in itertools.product(range(2),range(2),range(256),[False,True]):
        result = replay.run(0xcf2c,blit_param(fmt,fmt,selector,alpha,flags={0x73:1} if generic else None))
        assert result['status']=='submission_intercepted'
        if generic:
            assert result['route']==['0xbbcc']
            assert values(result,0x760,0x774)==expected_blend(selector,alpha,0x760)
        elif selector==0 and alpha==255:
            assert result['route']==['0xb578'] and values(result,0xb01,0xb01)==[(0xb01,0)]
        else:
            assert result['route']==['0xb234']
            assert values(result,0xb01,0xb06)==expected_blend(selector,alpha,0xb01)
        sweep_hash.update(json.dumps([fmt,selector,alpha,generic,result],sort_keys=True).encode())
        checks += 1
        sweep_cases += 1
    # Actual cslChangeHVFlip leaf execution proves ==1 rather than !=0 semantics.
    flip_cases = []
    flip_va = gpe.exports['cslChangeHVFlip'][0]
    for h,v in itertools.product([0,1,2,15,16,255],repeat=2):
        raw = struct.pack('<H',0x13ff)
        result = replay.run(flip_va,raw,args=[replay.PARAM,h,v])
        assert result['status']=='returned'
        got = struct.unpack('<H',replay.uc.mem_read(replay.PARAM,2))[0]
        expected = (0x13ff&~12)|((h==1)<<3)|((v==1)<<2)
        assert got==expected
        flip_cases.append({'h':h,'v':v,'initial':hex(0x13ff),'result':hex(got),'entry_va':hex(flip_va)})
        checks += 1
    # CPU PNG transforms execute original instructions, with one synthetic row.
    # Their arithmetic is proven for THESE callbacks, never a GPE hardware oracle.
    oreplay = Replay(obj)
    png_cases = []
    row = bytes.fromhex('12345678 90abcdef fedcba98')
    for entry,channels,formula in [(0x160414,4,'RGBA8888 bytes -> LE32 0xRRGGBBAA'),
                                  (0x16031c,4,'RGBA bytes -> LE16 0xRGBA high-nibble truncation'),
                                  (0x160224,4,'RGBA bytes -> LE16 0xARGB high-nibble truncation'),
                                  (0x160134,3,'RGB bytes -> LE16 RGB565 high-bit truncation')]:
        data = bytearray(0x3000)
        struct.pack_into('<I',data,0x1000,3)
        data[0x1011:0x1013]=bytes([8,channels])
        raw = row if channels==4 else bytes.fromhex('123456 90abcd fedcba')
        data[0x2000:0x2000+len(raw)]=raw
        result = oreplay.run(entry,data,args=[oreplay.PARAM,oreplay.PARAM+0x1000,oreplay.PARAM+0x2000])
        assert result['status']=='returned'
        got = bytes(oreplay.uc.mem_read(oreplay.PARAM+0x2000,12 if entry==0x160414 else 6))
        expected = b''
        for k in range(3):
            rgb = raw[channels*k:channels*(k+1)]
            if entry==0x160414: expected += rgb[::-1]
            elif entry==0x16031c: expected += struct.pack('<H',sum((v>>4)<<(12-4*j) for j,v in enumerate(rgb)))
            elif entry==0x160224: expected += struct.pack('<H',(rgb[3]>>4)<<12|(rgb[0]>>4)<<8|(rgb[1]>>4)<<4|rgb[2]>>4)
            else: expected += struct.pack('<H',(rgb[0]>>3)<<11|(rgb[1]>>2)<<5|rgb[2]>>3)
        assert got==expected,(hex(entry),got.hex(),expected.hex())
        checks += 1
        png_cases.append({'entry_va':hex(entry),'input':raw.hex(),'output':got.hex(),'formula':formula})
    # Table mappings are independent facts, do not identify two unrelated enum domains.
    mapping = {}
    for key,a,base in [('fill',0x1e220c,0x1018b8),('blit_src',0x1e2214,0x101b3c),
                       ('blit_dst',0x1e221c,0x101b74)]:
        mapping[key] = {str(n+1):hex(base+struct.unpack('b',bytes([v]))[0]*4)
                        for n,v in enumerate(obj.read(a,8))}
    resource_headers=[]
    for name in ('color.uxb','image.uxb','image_00_32.uxc','image_00_43.uxc'):
        p=AP/'usr/share/app'/name
        b=p.read_bytes()
        resource_headers.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
                                 'header64':b[:64].hex(),'pixel_codec':'unconfirmed'})
    log=ROOT/'menu-repair-01/runtime/runs/ap81skd-b9850378/serial.log'
    # Only exact command markers, never giant binary lines or private log context.
    serial=log.read_bytes()
    markers=[m.group().decode('ascii') for m in re.finditer(rb'(?m)^FX3_GPE_CMD [^\r\n\x00]*',serial)]
    proof = {
        'schema':1,'scope':'Read-only original-code descriptor audit; isolated CPU replay; no QEMU/device/firmware changes',
        'volume_uuid':UUID,'tool_versions':{'capstone':capstone.__version__,'unicorn':unicorn.__version__},
        'libraries':libraries,'tables':tables,'libObj_jump_tables_and_constant':obj_tables,
        'libObj_png_callback_relative_relocations':relocations,
        'libObj_format_branch_targets':mapping,'resources':resource_headers,
        'replay_contract':{'instruction_budget_per_case':20000,'synthetic_memory_only':True,
            'gpe_external_calls_hooked':True,'hardware_submission_intercepted_at':'0xaf30',
            'register_writer_intercepted_at':'0xadac','special_writer_intercepted_at':'0xae14',
            'completion_helpers_intercepted':['0xaddc','0xaf08'],
            'csl_operations_hooked':['cslClearSat','cslClearSrc','cslMakeSimpleSprite','cslChangeHVFlip'],
            'pixel_engine_emulated':False,'no_register_reset_assumption':True},
        'checks':{'passed':checks,'fill_cases':len([c for c in cases if c['op']=='FillRect']),
                  'blit_cases':len([c for c in cases if c['op']=='BitBlit']),
                  'flag_cases':len(flag_cases),'conversion_cases':len(conversion_cases),
                  'png_cpu_cases':len(png_cases),'flip_cpu_cases':len(flip_cases),
                  'full_u8_alpha_sweep':sweep_cases,'result':'passed'},
        'cases':cases,'flag_cases':flag_cases,'conversion_cases':conversion_cases,'png_cpu_cases':png_cases,
        'flip_cpu_cases':flip_cases,
        'full_u8_alpha_sweep':{'cases':sweep_cases,'stream_sha256':sweep_hash.hexdigest(),
                              'scope':'fmt0/1 Fill selectors0/1/2 and fast/generic BitBlit selectors0/1; all K=0..255'},
        'p3_implementation_gate':{
            'verified_baseline':['Fill fmt0/1 selector0 K255 original packing',
                                 'BitBlit fmt0/1 same-format no flags selector0 K255 existing P2 copy'],
            'raw_register_programming':'fully specified for in-scope branches; not a pixel oracle',
            'hardware_pixel_formula':None,
            'reject_until_pixel_oracle':['Any blending enabled', 'Any cross-format conversion',
                                         'Formats2/3/4', 'Any unimplemented generic primitive/flag'],
            'candidate_only_formulas':{
                'constant_lerp':'Q((K*S+(L-K)*D)/L); L and Q unconfirmed',
                'straight_source_over':'a=Q(As*K/L); C=Q(Cs*a+Cd*(1-a)); alpha equation unconfirmed',
                'premultiplied_source_over':'a=Q(As*K/L); C=Q(Cs*K/L+Cd*(1-a)); not proven',
                'factor_code_mapping':'No public/device evidence assigns nibble 0/1/4/5/8/9/c to named factors'}},
        'runtime_observation':{'path':str(log),'sha256':hashlib.sha256(serial).hexdigest(),
                               'markers':markers,'meaning':'observed existing log only; no run started'},
        'unconfirmed':[
            'Factor selector nibble meanings (0/1/4/5/8/9/c); source/destination operand attribution.',
            'Hardware straight/premultiplied math, destination alpha equation, denominator 255/256/15/16.',
            'Rounding, saturation, dithering, intermediate precision and 4-to-8 expansion.',
            'Blend control bit 1 exact effect and ordering of texture/filter/conversion/blend/quantization.',
            'Format2/3/4 channel meaning; format3 coefficient tables suggest YCbCr but are not a datasheet.',
            'Resource uxd decompression/pixel format and palette interpretation remain unbound.',
            'P3 has no pixel-output oracle; no alpha or conversion path is hardware-equivalence certified.'],
        'references':[
            'https://www.capstone-engine.org/lang_python.html',
            'https://www.unicorn-engine.org/docs/tutorial.html',
            'https://www.libpng.org/pub/png/libpng-manual.txt']
    }
    target=HERE/'gpe-blend-proof.json'
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS: {checks} bounded original-code cases; rebuilt {target}')


if __name__ == '__main__':
    main()
