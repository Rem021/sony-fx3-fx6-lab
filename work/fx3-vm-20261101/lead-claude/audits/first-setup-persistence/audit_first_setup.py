#!/usr/bin/env python3
"""Offline first-setup persistence audit. Writes only adjacent proof JSON; never runs firmware."""
import sys
sys.dont_write_bytecode = True
import hashlib, io, json, plistlib, re, struct, subprocess
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
LIB = VM/'original-uipc/ap-projection/regular-files/usr/lib'
OUT = Path(__file__).resolve().parent
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/first-setup-persistence'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
class Image:
    def __init__(self,name):
        self.name=name; self.path=(ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin' if name=='cp' else LIB/({'ap':'appFw.so','obj':'libObj.so'}.get(name,name)))
        self.raw=self.path.read_bytes()
        self.ptrs={}; self.plt={}; self.sym={}
        self.cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if name=='cp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
        self.cs.skipdata=True
        if name=='cp': return
        self.elf=ELFFile(io.BytesIO(self.raw))
        self.segs=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM); self.cs.skipdata=True
        self.ptrs={}; self.plt={}
        sy=self.elf.get_section_by_name('.dynsym')
        self.sym={s.name:(s['st_value'],s['st_size']) for s in sy.iter_symbols()} if sy else {}
        rel=self.elf.get_section_by_name('.rela.plt')
        if rel:
            sy=self.elf.get_section(rel['sh_link']); pv=self.elf.get_section_by_name('.plt')['sh_addr']
            self.plt={pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
        for sec in self.elf.iter_sections():
            if sec['sh_type']!='SHT_RELA': continue
            sy=self.elf.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                i=r['r_info_sym']; s=sy.get_symbol(i) if i else None
                self.ptrs[r['r_offset']]=(s['st_value'] if s else 0)+r['r_addend']
    def read(self,a,n):
        if self.name=='cp': return self.raw[a-0x108000:a-0x108000+n]
        s=next(s for s in self.segs if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        o=s['p_offset']+a-s['p_vaddr']; return self.raw[o:o+n]
    def string(self,a): return self.read(a,512).split(b'\0',1)[0].decode(errors='replace')
    def dis(self,a,n):
        rows=[]
        for i in self.cs.disasm(self.read(a,n),a):
            row={'va':hex(i.address),'raw':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#'): row['symbol']=self.plt.get(int(i.op_str[1:],16),'')
            rows.append(row)
        return rows
    def strings(self,pattern):
        rx=re.compile(pattern,re.I); out=[]
        for m in re.finditer(rb'[ -~]{5,}',self.raw):
            t=m.group().decode()
            if not rx.search(t): continue
            if self.name=='cp':
                out.append({'va':hex(m.start()+0x108000),'text':t}); continue
            seg=next((s for s in self.segs if s['p_offset']<=m.start()<s['p_offset']+s['p_filesz']),None)
            if seg is not None: out.append({'va':hex(seg['p_vaddr']+m.start()-seg['p_offset']),'text':t})
        return out
    def xrefs(self,target):
        out=[]
        for sec in self.elf.iter_sections():
            if not sec['sh_flags']&4: continue
            b=sec.data(); base=sec['sh_addr']
            for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
                a=base+4*k
                if w&0x7c000000==0x14000000:
                    imm=w&0x3ffffff
                    if imm&(1<<25): imm-=1<<26
                    if a+4*imm==target: out.append({'va':hex(a),'kind':'branch'})
                if w&0x9f000000==0x90000000:
                    imm=((w>>5)&0x7ffff)<<2|((w>>29)&3)
                    if imm&(1<<20): imm-=1<<21
                    page=(a&~4095)+(imm<<12); rd=w&31
                    if page!=target&~4095: continue
                    for j in range(1,7):
                        if k*4+j*4+4>len(b): break
                        v=struct.unpack_from('<I',b,(k+j)*4)[0]
                        if v&0x7f000000==0x11000000 and (v>>5)&31==rd:
                            addr=page+((v>>10)&4095)*(4096 if v&(1<<22) else 1)
                            if addr==target: out.append({'va':hex(a+j*4),'kind':'adrp-add','start':hex(a)})
        return {'code':out,'pointers':[hex(k) for k,v in self.ptrs.items() if v==target]}

class Module:
    def __init__(self):
        self.path=VM/'original-uipc/original-modules/backup.ko'
        self.raw=self.path.read_bytes(); self.elf=ELFFile(io.BytesIO(self.raw))
        sy=self.elf.get_section_by_name('.symtab')
        self.sym={s.name:s for s in sy.iter_symbols() if s.name}
        self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM); self.cs.skipdata=True; self.reloc={}
        rel=self.elf.get_section_by_name('.rela.text')
        for r in rel.iter_relocations():
            sym=sy.get_symbol(r['r_info_sym'])
            self.reloc[r['r_offset']]={'symbol':sym.name,'section':sym['st_shndx'],'value':hex(sym['st_value']),'addend':r['r_addend'],'type':r['r_info_type']}
    def dis(self,a,n):
        rows=[]
        raw=self.elf.get_section_by_name('.text').data()[a:a+n]
        for i in self.cs.disasm(raw,a):
            r={'va':hex(i.address),'raw':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            if i.address in self.reloc:r['relocation']=self.reloc[i.address]
            rows.append(r)
        return rows

def offset(im, va):
    if isinstance(im, Module):
        return im.elf.get_section_by_name('.text')['sh_offset'] + va
    if im.name == 'cp': return va - 0x108000
    s = next(s for s in im.segs if s['p_vaddr'] <= va < s['p_vaddr']+s['p_filesz'])
    return s['p_offset'] + va - s['p_vaddr']

def entries(blob, base=0):
    b=blob[base:]
    addr,cookie,flags,rev,ns,np,start,size,stored=struct.unpack_from('<III4s5I',b)
    assert cookie==0xaaaaaaaa and rev==b'BK4\0' and ns<=1024
    end=start+size
    assert end<=len(b) and 256+6*(ns+np)<=start
    items={}
    for sid in range(ns):
        count,index=struct.unpack_from('<HI',b,256+6*sid)
        assert index+count<=np
        for pid in range(count):
            at=256+6*ns+6*(index+pid)
            attr,ptr=struct.unpack_from('<HI',b,at)
            if ptr==0xffffffff: continue
            n,o=ptr>>24,ptr&0xffffff
            max_size=0
            if n==255: n=struct.unpack_from('<H',b,o)[0];o+=2
            elif n==0:
                n,max_size=struct.unpack_from('<HH',b,o);o+=4
                assert n<=max_size
            assert start<=o and o+n<=end
            items[(sid<<16)|pid]={'attribute':hex(attr),'index_file_offset':hex(base+at),
                'file_offset':hex(base+o),'bank_offset':hex(o),'bytes':n,'max_bytes':max_size,
                'raw':b[o:o+n].hex(),'value_le':int.from_bytes(b[o:o+n],'little')}
    # Original Data_CalChecksum temporarily zeroes header+0x20 and handles reserved sums.
    total=(sum(b[:32])+sum(b[36:end]))&0xffffffff
    calculated=total if 1<=total<=0xfffffffd else 1
    return {'base':hex(base),'address_word':hex(addr),'flags_word8':hex(flags),
        'write_complete_byte8':b[8],'suspend_complete_byte9':b[9],
        'subsystems':ns,'parameter_slots':np,'data_start':hex(start),'data_bytes':hex(size),
        'end_in_bank':hex(end),'stored_checksum':stored,'calculated_checksum':calculated,
        'checksum_matches':stored==calculated,'sha256':hashlib.sha256(b[:end]).hexdigest()},items

PINS={
    'appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
    'libbackup.so':'6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d',
    'backup.ko':'8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d',
    'FX3-CX95900_ALLLANG-Backup.bin':'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2',
}
BLOCKS={
 'ap':[
    (0x237f71c,0x30),(0x237fc44,0x1e4),(0x237fe28,0x980),
    (0x2827290,0x13c),(0x2930b9c,0x28),(0x29489e4,0x28),
    (0x29390e0,0x28),(0x294e134,0x28),(0x294bed4,0x28),
    (0x2ec0548,0x1fc),(0x2ec0744,0x160),
    (0x2a6be40,0x80),(0x2ebfd1c,0x70),(0x2a6b564,0x88),
    (0x2a70a40,0xb0),(0x2a69974,0x3c),(0x2a69a68,0x3c),
    (0x2ab9028,0x2c),(0x2ab90a4,0x24),(0x2b22cc8,0x28),
    (0x2b2372c,0x2c),(0x2b22cb8,0x10),(0x2ebf650,0x34),
    (0x2d7e5e8,0x1f0),(0x2f72354,0x1cc),(0x2b63908,0xb0),(0x2b63c2c,0x18),
    (0x23af5d4,0x15c),(0x2324800,0x82c),
 ],
 'libbackup.so':[(0x1ff0,0x44),(0x24b0,0x44),(0x2258,0x70)],
 'backup.ko':[
    (0x760,0x118),(0x1eb8,0x68),(0x2728,0x18),(0x24a0,0x110),
    (0x4ef8,0x68),(0x5350,0x4c),(0x57d8,0x14),(0x5880,0x80),
    (0x5920,0x64),(0x5988,0x5c),(0x6540,0xd4),(0x6618,0x80),
    (0x66a8,0xf4),(0x6800,0x26c),(0x7030,0x90),(0x2ba8,0xf8),
    (0x3010,0x110),(0x5d40,0xf0),
 ]}
CHECKS=[
 ('ap',0x238030c,'bl #0x2827348'),('ap',0x2380320,'cbz w0, #0x238034c'),
 ('ap',0x2380468,'cmp w0, #2'),('ap',0x2380470,'orr w23, w25, w23'),
 ('ap',0x2380474,'cbz w23, #0x2380620'),('ap',0x238047c,'bl #0x237fd94'),
 ('ap',0x2380484,'cbnz w24, #0x2380620'),('ap',0x2380488,'cbnz w25, #0x23804ec'),
 ('ap',0x23804b8,'mov w1, #0x1098'),('ap',0x2380620,'mov w0, #0x2e1'),
 ('ap',0x2380628,'mov w0, #0x270'),('ap',0x2380634,'b.eq #0x238064c'),
 ('ap',0x2380644,'mov w0, #0xfa'),('ap',0x2380648,'b #0x23803dc'),
 ('ap',0x2ec0564,'mov w0, #0x2cf0000'),('ap',0x2ec056c,'bl #0x15927e0'),
 ('ap',0x2ec0788,'mov w1, #0x2cf0000'),('ap',0x2ec0790,'bl #0x1592f80'),
 ('ap',0x2ebfd20,'mov w0, #0x14'),('ap',0x2ebfd28,'movk w0, #0x2cf, lsl #16'),
 ('ap',0x2ebfd2c,'b #0x15927e0'),('ap',0x2ebfd40,'mov w20, #0x14'),
 ('ap',0x2ebfd58,'bl #0x1592f80'),('ap',0x2ebfd60,'mov w1, #0x140'),
 ('ap',0x2ebfd64,'movk w1, #0x107, lsl #16'),('ap',0x2ebfd6c,'bl #0x1592f80'),
 ('ap',0x2a6b580,'bl #0x2ebfd1c'),('ap',0x2a6b5b0,'mov w1, #0x1098'),
 ('ap',0x2a69a80,'bl #0x29489e4'),('ap',0x2a69a8c,'bl #0x2ab9028'),
 ('ap',0x2ab902c,'mov w0, #5'),('ap',0x2ab9048,'bl #0x2ab8e04'),
 ('ap',0x2b23730,'bl #0x2ebfd30'),('ap',0x2b23754,'bl #0x2ec0744'),
 ('ap',0x2d7e6f8,'cbnz w0, #0x2d7e658'),('ap',0x2d7e730,'strb wzr, [x3, #-0x49]!'),
 ('ap',0x2d7e73c,'strb w0, [x24]'),('ap',0x2d7e740,'strb w0, [x25]'),
 ('ap',0x2d7e770,'mov w1, #0x187'),('ap',0x2d7e774,'str wzr, [x3, #-0x40]!'),
 ('backup.ko',0x593c,'ldr w5, [x0, #0x20]'),('backup.ko',0x5940,'str wzr, [x0, #0x20]'),
 ('backup.ko',0x5970,'str w5, [x0, #0x20]'),('backup.ko',0x6594,'bl #0x6594'),
 ('backup.ko',0x65a8,'cmp w21, #1'),('backup.ko',0x65ac,'b.eq #0x65e8'),
 ('backup.ko',0x59ac,'and x0, x0, #0xfffffffffffff000'),
]

def rebuild(check=False):
    proof={'scope':'Offline original-code and frozen-input audit; no QEMU, guest API, device or source mutation.',
           'grades':{'A':'original bytes / stored input / saved direct observation',
                     'B':'constrained inference; register or writer observation incomplete',
                     'U':'not established'},'sources':{},'code':{},'instruction_checks':[]}
    def source(p,pin=None,lf_prefix=None):
        b=p.read_bytes()
        if lf_prefix is not None:
            lines=b.split(b'\n');assert len(lines)>lf_prefix
            b=b'\n'.join(lines[:lf_prefix])+b'\n'
        sha=hashlib.sha256(b).hexdigest()
        if pin is not None: assert sha==pin,(str(p),sha)
        proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(b),'sha256':sha,
            **({'first_LF_lines_only':lf_prefix,'later_appends_ignored':True} if lf_prefix else {})}
        return b
    images={n:(Module() if n=='backup.ko' else Image(n)) for n in BLOCKS}
    # No import of previous audit builders: evidence is extracted from original inputs here.
    for n,im in images.items():
        source(im.path,PINS[im.path.name]);proof['code'][n]=[]
        for va,length in BLOCKS[n]:
            off=offset(im,va);raw=im.raw[off:off+length]
            proof['code'][n].append({'va':hex(va),'ET_REL_text_offset':hex(va) if n=='backup.ko' else None,
                'file_offset':hex(off),'length':length,'raw':raw.hex(),'disassembly':im.dis(va,length)})
    for name,va,want in CHECKS:
        im=images[name];row=im.dis(va,4)[0]
        assert row['asm']==want,(name,hex(va),row,want)
        proof['instruction_checks'].append({'image':name,'file_offset':hex(offset(im,va)),**row})
    a=images['ap'];k=images['backup.ko']
    proof['metadata']={}
    for label,va,n in [('date187_to_backup',0x40f92c8,40),('force1098_extern_name',0x418d760,24),
                      ('language_BKID_name_only',0x414a6f0,16),
                      ('force1098_backup_callback',0x46e3468,24),('scr0099_vtable',0x45764c0,0xa8)]:
        proof['metadata'][label]={'va':hex(va),'file_offset':hex(offset(a,va)),
            'raw':a.read(va,n).hex(),'relocated_pointers':{hex(p):hex(v) for p,v in a.ptrs.items() if va<=p<va+n}}
    assert struct.unpack('<I',a.read(0x46e3468,4))[0]==0x1098
    assert a.ptrs[0x46e3478]==0x2a69a68
    assert a.ptrs[0x45764c8]==0x45761d8 and a.ptrs[0x45761e0]==0x313aed8
    assert a.string(0x313aed8)=='23scr0099_0001_controller'
    assert a.ptrs[0x45764d0+0x10]==0x23af5d4
    assert struct.unpack('<I',a.read(0x40f92c8,4))[0]==0x187
    assert struct.unpack('<I',a.read(0x40f92d4,4))[0]==0x02cf01b4
    assert struct.unpack('<I',a.read(0x414a6f0,4))[0]==0x3fe
    assert a.string(a.ptrs[0x414a6f8])=='BKID_APP_setting_language'
    proof['date_status_enums']=[a.string(a.ptrs[0x41359e0+8*i]) for i in range(4)]
    assert proof['date_status_enums'][2]=='VAL_date_time_set_status_DATE_TIME_NOT_SET'
    proof['screen_names']=[]
    wanted={0xfa,0x2ae,0x2e1,0x178,0x18e,0x192,0x193,0x407}
    for p,v in sorted(a.ptrs.items()):
        if not 0x4157000<p<0x415e000:continue
        ident,n=struct.unpack('<II',a.read(p-8,8))
        if ident in wanted and n<100:
            proof['screen_names'].append({'row_va':hex(p-8),'id':hex(ident),'name':a.string(v)})
    proof['original_strings']={hex(v):a.string(v) for v in [0x31358f6,0x313aed8,
        0x39a5cb0,0x39a5d38,0x3b4f782,0x3b4f7a8,0x3c2a7ed,0x3908878]}
    proof['language_conversion']=[]
    for raw in range(34):
        jump=struct.unpack('<b',a.read(0x39a5ac8+raw,1))[0]
        target=0x2ec0594+jump*4;row=a.dis(target,4)[0]
        value=0 if row['asm']=='str wzr, [x19]' else int(re.fullmatch(r'mov w0, #(0x[0-9a-f]+|[0-9]+)',row['asm']).group(1),0)
        assert value==raw
        proof['language_conversion'].append({'stored':raw,'target':hex(target),'model_language54e':value,'asm':row['asm']})
    proof['backup_daemon_switch']=[]
    for typ,want in [(5,0x2b2372c),(8,0x2b23750)]:
        slot=0x3806ad0+2*(typ-1);val=struct.unpack('<h',a.read(slot,2))[0]
        target=0x2b22cf0+val*4;assert target==want
        proof['backup_daemon_switch'].append({'type':typ,'slot_va':hex(slot),'raw':a.read(slot,2).hex(),'target':hex(target)})
    r=VM/'runtime';r95=r/'runs/ap95v6r3ui600-3715c225';r96=r/'runs/ap96v1replaydiag-0f72a1e0'
    paths={
        'seed':VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin',
        'AP95_before':r/'runs/ap88cpr4-e71668cb/backup-after-shutdown.bin',
        'AP95_after':r95/'backup-after-setup.bin',
        'AP96_pre_AP_readback':r96/'ap89-input-before-AP.bin',
    }
    pins={'seed':PINS[paths['seed'].name],
          'AP95_before':'38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f',
          'AP95_after':'191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc',
          'AP96_pre_AP_readback':'191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc'}
    blobs={name:source(path,pins[name]) for name,path in paths.items()}
    relevant={0x2cf0000:'language actual storage',0x2cf0014:'clock_force_settled',
              0x1070140:'clock_force_settled mirror written by native setter',
              0x2cf01b4:'date_time_set_status',0x2cf1840:'separate native key; not force',
              0x2cf1841:'UUD current version',0x2cf1842:'UUD required version',
              0x2cf03fe:'not language storage despite BKID_APP name index 3fe'}
    banks={};all_items={};proof['backups']={}
    for name,b in blobs.items():
        assert len(b)==0x221000 or name=='seed'
        head,items=entries(b);second_base=(int(head['end_in_bank'],16)+4095)&~4095
        assert second_base==0xd2000
        h2,e2=entries(b,second_base);banks[name]=(head,h2);all_items[name]=items
        proof['backups'][name]={'source':str(paths[name].relative_to(ROOT)),
            'AP_primary':head,'CP_snapshot_in_AP_reserved_area':h2,
            'selected_keys':{hex(key):{'meaning':meaning,**items[key],
                'physical_in_AP_reserved':hex(0x404000000+int(items[key]['file_offset'],16)),
                'exists_in_second_bank':key in e2} for key,meaning in relevant.items()}}
    assert blobs['AP95_after']==blobs['AP96_pre_AP_readback']
    assert banks['seed'][0]['checksum_matches'] and banks['seed'][1]['checksum_matches']
    assert not banks['AP95_after'][0]['checksum_matches'] and banks['AP95_after'][1]['checksum_matches']
    before,after=all_items['AP95_before'],all_items['AP95_after']
    diff=[{'key':hex(key),'before':before[key],'after':after[key]}
          for key in sorted(before) if before[key]['raw']!=after[key]['raw']]
    published=json.loads(source(r/'ap95v6r3ui600-3715c225-backup-after-setup-keys.json'))
    assert {x['key'] for x in diff}=={x['key'] for x in published['AP_changed_parameters']}
    assert len(diff)==20
    for row in published['AP_changed_parameters']:
        key=int(row['key'],16)
        assert row['before']['raw']==before[key]['raw'] and row['after']['raw']==after[key]['raw']
    proof['AP95_parameter_diff_recomputed']=diff
    proof['AP95_before_origin']={'SHA_verified_original_replay_profile':pins['AP95_before'],
       'scope':'AP88 exported state used as AP95 boot input, NOT a direct AP95 pre-setup runtime sample; difference includes boot and setup.'}
    for key,want in [(0x2cf0000,0),(0x2cf0014,1),(0x1070140,1),(0x2cf01b4,0),(0x2cf1841,4),(0x2cf1842,4)]:
        assert after[key]['value_le']==want
    cp_start=0xd2000;cp_end=cp_start+int(banks['seed'][1]['end_in_bank'],16)
    assert blobs['AP95_after'][cp_start:cp_end]==blobs['seed'][cp_start:cp_end]
    proof['CP_snapshot_unchanged_from_seed']=True
    # Checksum-only repair cannot change either boot predicate. No modified binary is written.
    state=bytearray(blobs['AP95_after']);struct.pack_into('<I',state,32,banks['AP95_after'][0]['calculated_checksum'])
    assert entries(state)[0]['checksum_matches']
    proof['checksum_only_counterfactual']={'scope':'in-memory bytearray only; no binary saved',
        'checksum_after':entries(state)[0]['calculated_checksum'],
        'force_still_1':entries(state)[1][0x2cf0014]['value_le']==1,
        'does_not_remove_setup_predicate':True}
    proof['boot_gate_projection']=[{'date187':d,'force1098':f,'date2_OR_force':bool(d==2 or f),
        'next_if_no_special_boot_or_product_exception':'0x2380478' if d==2 or f else '0x2380620 -> rep_boot 0x2e1'}
        for d,f in [(0,1),(0,0),(2,0),(2,1)]]
    # Stable log prefixes make --check independent of later appends to AP96.
    logs={'AP95':source(r95/'serial.log',lf_prefix=160625),'AP96':source(r96/'serial.log',lf_prefix=13520)}
    proof['runtime_receipts']={}
    patterns=[b'FX3_AP89_BACKUP_REPLAY_',b'FX3_UUD_BACKUP_COMPARE',b'FX3_AP89_UUD_DECISION',
              b'FX3_AP89_SCREEN_OPEN_ENTER',b'DATE_CLOCK_READY',b'FX3_DATE_CLOCK_BYTES op=2']
    for name,b in logs.items():
        proof['runtime_receipts'][name]=[{'LF_line':i,'text':line.replace(b'\r',b'').decode(errors='replace')}
            for i,line in enumerate(b.split(b'\n'),1) if any(p in line for p in patterns)]
    s96=logs['AP96']
    assert b'id1841=4 id1842=4' in s96 and b'native_update_return=0' in s96
    assert b'id1=0x2ae id2=0xfa id3=0x2ae' in s96
    assert b'FX3_AP89_BACKUP_REPLAY_VERIFIED' in s96
    receipt=json.loads(source(r96/'ap89-host-input-readback.json'))
    assert receipt['verified'] and receipt['before_AP_bootin_marker'] and receipt['sha256']==pins['AP95_after']
    proof['AP96_host_input_SHA_receipt']=receipt
    proof['AP95_export_limit']=json.loads(source(r95/'ap95-backup-after-setup.json'))
    init=source(r/'ap96-v1-setup-replay-input-diag/init-review.sh').decode()
    assert init.index('insmod /usr/kmod/backup.ko Backup_load=1 Backup_save=0')<init.index('/simulation/fx3-backup-replay-v1')<init.index("/usr/bin/bootin.elf 'target=qemu '")
    proof['init_order']={'Backup_load':1,'Backup_save':0,'module_before_replay_before_AP':True,
       'lines':[{'line':i,'text':l.strip()} for i,l in enumerate(init.splitlines(),1)
                if any(t in l for t in ['insmod /usr/kmod/backup.ko','/simulation/fx3-backup-replay-v1','FX3_AP_NATURAL_BOOTIN_BEGIN'])]}
    for p in [r95/'ap95-before-menu-current.png',r96/'ap96-phaseA-before-SETUP.png',
              r/'helpers/fx3-backup-replay-v2-setup96.c',r/'helpers/seed-date-clock-v3.c']:
        source(p)
    proof['visual_observation']={'AP96_phaseA':'Title Language and English first list entry, inspected by worker; image SHA recorded. No independent register read of 54e/1098.',
        'AP95_saved_snapshot':'receipt itself says settled Creators App information frame and standby unverified; screen0 request is not commit/persistence receipt.'}
    # Record exact native on-disk name and sections, without claiming a flash write occurred.
    proof['native_Backup_files']=[]
    for n in ['Backup_pri_file','Backup_sec_file','Backup_save']:
        sym=k.sym[n];sec=k.elf.get_section(sym['st_shndx']);at=sym['st_value'];raw=sec.data()[at:at+sym['st_size']]
        proof['native_Backup_files'].append({'symbol':n,'section':sec.name,'offset':hex(at),
           'file_offset':hex(sec['sh_offset']+at),'raw':raw.hex(),
           'string':raw.split(b'\0')[0].decode(errors='replace') if n!='Backup_save' else None})
    proof['findings']=[
      {'grade':'A','claim':'Language uses AP primary key 02cf0000, model54e; snapshot/replay raw00 is English. BKID_APP index3fe is not this key.'},
      {'grade':'A','claim':'force1098 is initialized from AP primary02cf0014 and native persistence setter also writes01070140; both remain01 in AP95 snapshot and exact AP96 pre-AP input.'},
      {'grade':'A','claim':'boot date2 OR force is a setup gate; false branches to rep_boot. Eligible true path plus feature270 selects fa scr0099_0001.'},
      {'grade':'A','claim':'AP96 original UUD getter reads4/4 and returns false; exact pre-AP input survives byte replay. No evidence for whole-bank rejection.'},
      {'grade':'B','claim':'Uncleared force flag is the direct storage-side explanation for repeated language wizard; exact 1098/date187 registers at2380464 were not captured.'},
      {'grade':'A','claim':'AP95 native success path for set datetime clears live force1098 and date187, but exported persisted force is still1. Screen0 and menu-freeze do not prove that path/callback/daemon completed.'},
      {'grade':'U','claim':'Why AP95 did not persist force0: date transaction failure vs pending callback/daemon vs save timing cannot be distinguished with saved evidence.'},
    ]
    proof['minimal_plan']=[
       'First instrument original date transaction return2d7e6f4 and live writes2d7e73c/740, callback2a69a68, queue type5 and daemon2b23730; do not manufacture a completion event.',
       'After original successful date confirmation and daemon writes, read back02cf0014=0 and01070140=0 with native Backup_nread, date187=0 and clock type0; export AP reserved state only then.',
       'For RAM replay keep current after-original-module-load/before-AP timing; second boot must read exact keys and show no fa branch at2380644. Checksum-only correction cannot clear the setup predicate.',
       'If using a storage-file profile instead of RAM replay, preserve native cookie/count/complete flags and checksum algorithm and complete original save/readback; merely renaming live RAM Backup.bin is not valid persistence.',
    ]
    proof['unproven']=[
       'AP96 post-start native Backup_nread return bytes for02cf0000/02cf0014 and registers at2380464; only pre-AP bytes plus native UUD read and selected screen are saved.',
       'AP95 model1098 actual0/write return and daemon type5 consumed; all snapshots still persist1.',
       'All rep_boot product-dependent paths and privacy/network/home settings; no single global setup-complete bit was established.',
       'Native shutdown/save completion, flash/file durability, CP primary backing address ownership, full hardware CP and physical camera acceptance.',
       'Whether all unchanged full-bank bytes were stable while AP95 was saved; host receipt provides read-only dump SHA, not original application-wide quiescence.',
    ]
    encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
    path=OUT/'first-setup-proof.json'
    if check:
        assert path.read_text()==encoded,'Proof drift: rebuild and inspect differences'
        print('PASS: independently rebuilt proof matches; original byte checks, both banks, 20 parameter differences, replay receipt and bounded logs verified.')
    else:
        path.write_text(encoded)
        print('PASS: first-setup-proof.json rebuilt; static/recorded evidence only, no firmware executed.')

if __name__ == '__main__':
    kind=sys.argv[1] if len(sys.argv)>1 else 'proof'
    if kind in ('dis','str','xref','sym'):
        name=sys.argv[2];im=Module() if name=='backup.ko' else Image(name)
        if kind=='dis':
            for row in im.dis(int(sys.argv[3],16),int(sys.argv[4],16)):print(json.dumps({'file_offset':hex(offset(im,int(row['va'],16))),**row},ensure_ascii=False))
        elif kind=='str':print(json.dumps(im.strings(sys.argv[3]),ensure_ascii=False,indent=2))
        elif kind=='xref':print(json.dumps(im.xrefs(int(sys.argv[3],16)),indent=2))
        elif kind=='sym':
            for n,v in im.sym.items():
                if re.search(sys.argv[3],n,re.I):print(n,str(v))
    else:
        assert kind in ('proof','--check'),kind
        rebuild(check=kind=='--check')

