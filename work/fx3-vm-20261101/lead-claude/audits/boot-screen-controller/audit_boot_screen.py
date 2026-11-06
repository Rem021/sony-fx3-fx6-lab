#!/usr/bin/env python3
"""Offline FX3 boot-screen audit; writes only adjacent boot-screen-proof.json."""
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
RUN = VM/'runtime/runs/ap87r2native-51e93181'
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/boot-screen-controller'
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

PINS={
 'appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'libObj.so':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae',
 'libbackup.so':'6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d',
 'backup.ko':'8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d',
 'cpapp-b.bin':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
 'serial.log':'137fdab2482a23d61a13cc2d7e248b3b9013bcd87687aefd0487fb9b6f5a85d0',
 'backup-reserved-ram.bin':'ca6075b00c6cc171f9408bb28acf80734ab47dffa7b476c4e58b52d75aa2af5b',
 'FX3-CX95900_ALLLANG-Backup.bin':'bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2'}
BLOCKS={
 'ap':[(0x237f618,0x1194),(0x2381598,0xc4c),
       (0x2323c94,0x474),(0x2324800,0x1030),
       (0x21916b0,0x2e0),(0x218fd0c,0x308),(0x218ef28,0x50),
       (0x2845900,0x130),(0x2827290,0x13c),(0x2823098,0xc0),
       (0x285c658,0x100),(0x285cff0,0x160),(0x285d238,0x7c),
       (0x29450e0,0x28),(0x2ebfea0,0xfc),(0x2ebff9c,0x100),
       (0x2b80350,0x64),(0x2a8a940,0xe8),(0x2a8ab04,0x40),(0x2a8ac20,0x38),
       (0x2d74478,0x100),(0x2dd6794,0x40),(0x2e3a19c,0xd0),
       (0x2145764,0x1b4),(0x2381050,4),(0x16f2298,0x24),
       (0x16f1998,0xb0),(0x20279b0,0x1ec)],
 'libbackup.so':[(0x237c,0x3c),(0x1a10,0x138)],
 'obj':[(0x16ea10,0xd4)],
 'cp':[(0x4986b4,0x42c),(0x4989d4,0x134),(0xa84ca0,0x90),
       (0x496cf4,0x100),(0x49750c,0x110),(0xa878d2,8)],
 'backup.ko':[(0x34d0,0x58),(0x33f0,0xd8),(0xa48,0x178),(0x878,0x1d0),
              (0x11c0,0x970),(0x73b0,0x150),(0x7aa8,0x520),
              (0x5350,0x58),(0x5468,0x90),(0x5668,0x48),(0x57a0,0x48)]}
CHECKS={
 'ap':{0x2380778:'ldr w2, [x1, #8]',0x2380780:'movk w1, #3, lsl #16',
       0x2380794:'bl #0x237fe28',0x237fb78:'mov w2, #0x2c',
       0x237fbdc:'cbz w1, #0x237fb88',0x237fbe0:'bl #0x237f8fc',
       0x237fbf8:'bl #0x27f7cfc',0x237fc04:'mov w0, #0x2ae',
       0x237fa78:'mov w0, #0x2af',0x237fb34:'bl #0x237f74c',
       0x238030c:'bl #0x2827348',0x2380310:'strb w0, [x22, #0xc3]',
       0x2380320:'cbz w0, #0x238034c',0x2380334:'ldp x21, x22, [sp, #0x20]',
       0x2827324:'bl #0x2823098',0x28230dc:'mov w1, #3',
       0x28230ec:'bl #0x27de614',0x2381c50:'bl #0x285d238',
       0x285d27c:'bl #0x285c658',0x285d034:'bl #0x29450e0',
       0x285d118:'mov w0, #1',0x285d11c:'bl #0x2ebfea0',
       0x285d120:'mov w0, #4',0x285d124:'bl #0x2ebfea0',
       0x2ebfef0:'b #0x1592dc0',0x2ebff94:'mov w21, #1',
       0x23815c4:'ldr x0, [x0, #0xf50]',0x23815d0:'blr x1',
       0x2191914:'ldr x2, [x1, #0x88]',0x219191c:'blr x2',
       0x218ffe4:'blr x2',0x218fff0:'bl #0x2172bac',
       0x2a8aa10:'mov w0, #0x2c',0x2a8aa20:'bl #0x27381b8',
       0x2d74504:'bl #0x2dd6794',0x2dd67bc:'bl #0x2e3a19c',
       0x2e3a250:'movk w0, #0x9003, lsl #16',0x2e3a254:'bl #0x2e2fb90',
       0x2380468:'cmp w0, #2',0x2380470:'orr w23, w25, w23',
       0x2380620:'mov w0, #0x2e1',0x23806c0:'mov w0, #0x178',
       0x2381050:'ret',0x2145844:'bl #0x2381050'},
 'backup.ko':{0x34e4:'bl #0x34e4',0x34f0:'mov w6, w19',0x34fc:'mov x7, #1',
       0x3500:'mov x5, #0',0x3504:'mov x4, #2',0x3508:'mov w3, #4',
       0x350c:'mov w2, #0x33',0x3514:'bl #0x11c0',
       0x12b8:'orr w21, w1, w21, lsl #28',0x13a0:'stp w26, wzr, [x23]',
       0x13b0:'stp w0, w27, [x23, #0x10]',0x13bc:'stp w19, w24, [x23, #0x18]',
       0x14f4:'bl #0x14f4',0x151c:'mov w2, #-1',0x1520:'bl #0x1520',
       0x154c:'ldr w0, [x19, #4]',0x1550:'str w0, [x1]',
       0x19fc:'mov w23, #0x28',0x1a04:'str w19, [x29, #0x1b8]',
       0x1a08:'str w1, [x29, #0x1bc]',0x7df8:'bl #0x7df8',
       0x74f0:'bl #0x74f0',0x8b8:'tst w0, w1',0x900:'bl #0x900'},
 'cp':{0x4986e8:'sub.w r0, r3, #0x27',0x4986f2:'tbb [pc, r0]',
       0x4988ac:'cmp r3, #2',0x498962:'ldr r0, [r4, #0x24]',
       0x498964:'bl #0xa84ca0',0x498976:'strb r0, [r1], #2',
       0x4989de:'movw r4, #0x811',0x4989ea:'movt r4, #0x3e',
       0x4989f8:'mov.w r2, #0x1000',0x4989fe:'blx #0x558400',
       0x498a06:'bl #0xa878d2',0x498a24:'bl #0x49f140',
       0x498ab6:'mov.w r2, #0x1000',0x498ac2:'bl #0x49f80c',
       0x498ade:'orr.w r5, sl, sb, lsl #16',0x498ae2:'bl #0x49f908',
       0xa84cea:'bl #0x496cf4',0x496d98:'ands r1, r0, #0x40',
       0x496dbc:'ands r0, r0, #4',0x49755a:'blx #0x558400',0xa878d2:'str r1, [r0, #-0xc]'},
 'libbackup.so':{0x2394:'mov w2, #0x15',0x23a8:'bl #0x1530',
                 0x1ae0:'bl #0x15d0',0x1ae8:'ldr w0, [x19, #4]'}}

def u32(b,o=0): return struct.unpack_from('<I',b,o)[0]
def backup_entries(b):
    addr,cookie,flags,rev,ns,np,start,size,checksum=struct.unpack_from('<III4s5I',b)
    assert cookie==0xaaaaaaaa and rev==b'BK4\0' and ns<=1024
    assert start+size<=len(b) and 256+6*(ns+np)<=start
    out={}
    for sid in range(ns):
        cnt,idx=struct.unpack_from('<HI',b,256+sid*6);assert idx+cnt<=np
        for pid in range(cnt):
            p=256+6*ns+(idx+pid)*6
            attr,ptr=struct.unpack_from('<HI',b,p)
            if ptr==0xffffffff:continue
            n,o=ptr>>24,ptr&0xffffff;mx=0
            if n==255:n=struct.unpack_from('<H',b,o)[0];o+=2
            elif n==0:n,mx=struct.unpack_from('<HH',b,o);o+=4;assert n<=mx
            assert start<=o and o+n<=start+size
            out[(sid<<16)|pid]={'attribute':attr,'offset':o,'size':n,'max_size':mx,'entry':p}
    return {'address_word':hex(addr),'flags':hex(flags),'ns':ns,'np':np,'start':start,'size':size,'end':start+size,'stored_checksum':checksum},out

def fixture_projection(blob):
    root,_=backup_entries(blob);base=(root['end']+4095)&~4095
    bank=blob[base:];head,items=backup_entries(bank)
    c=items[0x3e000c];assert c['size']==1
    count=bank[c['offset']]+1
    result={'bank_offset':hex(base),'header':head,'repeat_key':'0x3e000c','repeat_raw':bank[c['offset']:c['offset']+1].hex(),'repeat_count':count,'resets':[]}
    state=bytearray(bank[:head['end']])
    for flag,mask in [(1,0x40),(4,4)]:
        chosen=[];before=hashlib.sha256(state).hexdigest()
        for key,r in items.items():
            attr,o,n,mx=r['attribute'],r['offset'],r['size'],r['max_size']
            if not attr&mask:continue
            assert not mx,'Selected variable capacity needs separate contract'
            repeat=count if attr&0x80 else 1
            assert n%repeat==0
            unit=n//repeat
            # Original reset default starts after total data capacity, not each repeated slot.
            default=bank[o+n:o+n+unit];assert len(default)==unit and o+n+unit<=head['end']
            copies=repeat if flag==1 else 1
            old=bytes(state[o:o+unit*copies]);new=default*copies
            chosen.append({'key':hex(key),'attribute':hex(attr),'offset':hex(o),'size':n,'repeat':repeat,'unit':unit,'copies_written':copies,'default_offset':hex(o+n),'changed':old!=new})
            state[o:o+len(new)]=new
        result['resets'].append({'flag':flag,'attribute_mask':hex(mask),'selected':len(chosen),'repeat_items':sum(x['repeat']>1 for x in chosen),'changed':sum(x['changed'] for x in chosen),'before_sha256':before,'after_sha256':hashlib.sha256(state).hexdigest(),'items':chosen})
    result['scope']='Pure bytearray projection from frozen AP reserved second BK4; no CP address binding or live backend established.'
    assert base==0xd2000 and count==4
    assert [(r['selected'],r['repeat_items'],r['changed']) for r in result['resets']]==[(317,2,0),(2,0,0)]
    return result

def rebuild(check=False):
    ims={n:Module() if n=='backup.ko' else Image(n) for n in BLOCKS}
    proof={'schema':1,'scope':'FX3 AP87-r2 frozen boot/shutdown/rep state and remote Backup reset audit; no firmware execution','sources':{},'code':{},'instruction_checks':[]}
    def source(p):
        raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
        if p.name in PINS:assert h==PINS[p.name],f'input drift: {p}'
        proof['sources'][str(p.relative_to(ROOT))]={'bytes':len(raw),'sha256':h}
        return raw
    for n,im in ims.items():
        source(im.path);proof['code'][n]={}
        for va,length in BLOCKS[n]:
            rows=im.dis(va,length)
            assert sum(len(bytes.fromhex(r['raw'])) for r in rows)==length,(n,hex(va),'incomplete decode')
            proof['code'][n][hex(va)]=rows
        for va,asm in CHECKS.get(n,{}).items():
            r=im.dis(va,4)[0]
            # Thumb may be 2B with the following instruction; compare first only.
            assert r['asm']==asm,(n,hex(va),r['asm'],asm)
            proof['instruction_checks'].append({'image':n,**r})
    a,c,k=ims['ap'],ims['cp'],ims['backup.ko']
    ptr=lambda p:a.ptrs.get(p,struct.unpack('<Q',a.read(p,8))[0])
    proof['vtables']={}
    for name,header,ti,expected in [('boot',0x455b220,0x455af38,0x2380778),('shutdown',0x455bb60,0x455b878,0x23815a4),('rep_boot',0x4530818,0x4530530,0x1c97f48)]:
        assert ptr(header)==0 and ptr(header+8)==ti
        assert ptr(header+0x98)==expected
        proof['vtables'][name]={'header':hex(header),'rtti':a.string(ptr(ti+8)),'slots_from_vptr':{hex(off):hex(ptr(header+16+off)) for off in (0x10,0x18,0x78,0x80,0x88,0x90)}}
    proof['screen_registry']={}
    registry=ptr(0x46f62e8)
    for id in (0x2ae,0x2af,0x2e1):
        row=registry+id*0x58
        proof['screen_registry'][hex(id)]={'row':hex(row),'presenter_factory':hex(ptr(row)),'controller_factory':hex(ptr(row+8)),'raw':a.read(row,0x58).hex()}
    proof['event_names']={}
    for ev,row in [(0x3002c,0x41719e0),(0x3002d,0x41719f0),(0x3002e,0x4171a00),(0x30072,0x4171e40),(0x30074,0x4171e60),(0x30086,0x4171f80),(0x300ad,0x41721f0)]:
        assert u32(a.read(row,4))==ev
        proof['event_names'][hex(ev)]={'row':hex(row),'name':a.string(ptr(row+8))}
    table=a.read(0x39a5ab8,4)
    proof['backup_reset_enum_map']={}
    for index,v in enumerate(table):
        target=0x2ebfed8+struct.unpack('b',bytes([v]))[0]*4
        first=a.dis(target,4)[0];assert first['asm'].startswith('mov w21, #')
        proof['backup_reset_enum_map'][str(index+1)]={'table_byte':v,'target':hex(target),'native_flag':int(first['asm'].split('#')[1],0)}
    assert [r['native_flag'] for r in proof['backup_reset_enum_map'].values()]==[1,2,3,4]
    jt=k.reloc[0x1b10];tbl=k.elf.get_section(jt['section']).data();off=jt['addend']
    entry=struct.unpack_from('<h',tbl,off+2*(0x33-0x29))[0];target=0x138c+4*entry
    assert target==0x16b4
    cp_targets={hex(0x27+i):hex(0x4986f6+2*v) for i,v in enumerate(c.read(0x4986f6,14))}
    assert cp_targets['0x33']=='0x49889c'
    assert k.reloc[0x34e4]['symbol']=='Backup_reset_all_subsystems'
    assert k.reloc[0x1520]['symbol']=='osal_rcv_msg_tmo'
    assert k.reloc[0x7df8]['symbol']=='Backup_reset_all'
    assert k.reloc[0x74f0]['symbol']=='backup_osal_call_func'
    proof['backup_dispatch']={'kernel_jump_entry':entry,'kernel_target':hex(target),'CP_TBB':cp_targets,'kernel_text_base_from_stack':'0xffffff80004e9000','wait_return_offset':'0x1524','actual_callback_offset':'0x74e8','misleading_kallsyms_label':'backup_put_cp_wt_data+0x23c lies beyond exported function size0xdc; callback74e8 calls7aa8'}
    for fn in ('Backup_reset_all','backup_osal_call_func','backup_put_cp_wt_data'):
        s=k.sym[fn];proof['backup_dispatch'][fn]={'text_offset':hex(s['st_value']),'bytes':s['st_size']}
    raw=source(RUN/'serial.log');lines=raw.split(b'\n')
    def hits(pattern):
        rx=re.compile(pattern)
        return [{'line':i+1,'text':l.decode(errors='replace')} for i,l in enumerate(lines) if rx.search(l)]
    proof['serial']={
     'line_convention':'LF bytes split; CR and NUL retained in source',
     '30086':hits(rb'DELETE_FACE_(COMPLETE_SEND_POINT|MANAGER_RECEIVE)|raw=86000300'),
     'power_off':hits(rb'raw=2c000300'),
     'power_on':hits(rb'raw=2d000300'),
     'power_off_cancel':hits(rb'raw=2e000300'),
     'power_off_comp':hits(rb'raw=74000300'),
     'screen_open':hits(rb'FX3_AP87_SCREEN_OPEN_ENTER|open screen:'),
     'UUD':hits(rb'FX3_AP87_UUD_DECISION'),
     'scenes':hits(rb'FX3_AP87_SCENE'),
     'backup_skip':hits(rb'Skip snd to 0x811'),
     'GPE':hits(rb'FX3_GPE_CMD'),
     'widget':hits(rb'FX3_DISPLAY_WIDGET'),
     'dirty':hits(rb'FX3_DISPLAY_GRM_DIRTY'),
     'visibility':hits(rb'FX3_DISPLAY_VISIBILITY_CALL'),
     'sys_request54':hits(rb'FX3_AP87_TASK_EVENT.*run_relative=0x2d74344'),
     'appfw_stack':[]}
    for i,l in enumerate(lines):
        if b'Backup_reset_all+0x48/0x58' in l:
            proof['serial']['appfw_stack'].append({'line':i-4+1,'lines':[{'line':j+1,'text':lines[j].decode(errors='replace')} for j in range(i-4,i+12)]})
    assert len(proof['serial']['appfw_stack'])==3
    assert len(proof['serial']['backup_skip'])==1 and proof['serial']['backup_skip'][0]['line']==20359
    assert len(proof['serial']['power_off'])==1 and proof['serial']['power_off'][0]['line']==18806
    assert not proof['serial']['power_off_cancel'] and not proof['serial']['power_off_comp']
    opens=[r for r in proof['serial']['screen_open'] if 'SCREEN_OPEN_ENTER' in r['text']]
    assert len(opens)==2 and 'id1=0x2ae id2=0x2af id3=0x2ae' in opens[1]['text']
    assert not proof['serial']['GPE'] and not proof['serial']['widget'] and not proof['serial']['dirty']
    maps=hits(rb'^[0-9a-f]+-[0-9a-f]+ r-xp 00000000 .* /usr/lib/appFw.so')
    bases=sorted({int(r['text'].split('-')[0],16) for r in maps});assert len(bases)==1
    proof['runtime_VA_derived_only']={'appFw_base':hex(bases[0]),'reset_e85_current':hex(bases[0]+0x83618dc),'reset_e85_next':hex(bases[0]+0x83618e0),'not_sampled':True}
    seed=source(VM/'original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin')
    ram=source(RUN/'backup-reserved-ram.bin')
    projection=fixture_projection(ram);seed_projection=fixture_projection(seed)
    b=0xd2000;end=b+projection['header']['end']
    assert ram[b:end]==seed[b:end]
    proof['CP_Backup_fixture']={'projection':projection,'seed_same_bank_sha256':hashlib.sha256(seed[b:end]).hexdigest(),'RAM_second_bank_unchanged_from_seed':True,'original_seed_checksum_verified':sum(seed[b:b+32])+sum(seed[b+36:end])==projection['header']['stored_checksum']}
    assert proof['CP_Backup_fixture']['original_seed_checksum_verified']
    proof['request_schema']={'source':'kernel native wrapper; not captured raw inAP87-r2','destination':'0x903e0811','length':40,'words':{'00':'0x33','04':'0','08':'0x903e0811','0c':'Q = actual dynamic reply queue','10':'1','14':'1 page','18':'2 scalar args','1c':'0 pointer args','20':'2 = reset_all','24':'F = actual reset flag'},'predicted_UUD_flags':[1,4],'current_first_request_flag':'B strong:1; needs raw sampling','wait_timeout':-1}
    proof['reply_schema']={'original_CP_source':'0x003e0811','destination':'request+0x0c','allocation_and_copy_bytes':4096,'logical_status_offset':4,'success':0,'original_flow':['4986b4 dispatch','49889c selector2','498964->a84ca0 reset','498972 status+4','498ac2 alloc4096','4989fe copy4096','498a06 setsource003e0811','498a24 send(request+0c)','498ae2 free incoming'],'honest_software_boundary':'Validate only actual initialized40B and capacity before reading. Independent4096B reply may zero unused tail and copy initialized40B; record deviation fromCP4096B opaque copy. No ACK before actual declaredCP backend reset and readback.'}
    proof['findings']=[
     {'grade':'A','claim':'30086 is face cleanup completion. Boot message slot88 only acts on30072; POWER_OFF3002c was separately enqueued at18806.'},
     {'grade':'A','claim':'20105 is one open_screen_ii call with3 args, not3 calls. Only2 SCREEN_OPEN_ENTER markers exist in whole saved run.'},
     {'grade':'B strong','claim':'Observed native UUD path sets e85=3 and predicts reset flag1 then4; raw reset request and e85 memory were not captured.'},
     {'grade':'A','claim':'AppFw3 saved kernel stacks wait at backup.text1524 inside Backup_reset_all, matching Skip snd0x811. Kernel callback74e8 is mislabeled by nearest exported symbol.'},
     {'grade':'A','claim':'Same-model AP kernel Backup only handles local reset before remote CP transaction; userspace capid preload does not intercept kernel-internalosal_snd_msg.'},
     {'grade':'A static / U runtime','claim':'boot/shutdown handlers define poweron/off/cancel and business gates; neither arbitrary battery/lens-ready nor repeated30072 is justified by saved evidence.'},
     {'grade':'U','claim':'No complete boot Widget resource/layout/visible tree or Sony-logo asset route was established. AP87-r2 has zeroGPE, zeroWidget, zeroGRMdirty observer records; absence does not mean dirty=0.'}]
    proof['sampling_plan']=[
     {'where':'backup.ko .text14e8/14f4/1520/154c','read':'full initialized40B, page allocation capacity, source,dest,Q; actualF; replylen/status/free; keep originals'},
     {'where':'appFw285d034/285d118/285d120','read':'e85 current83618dc,next83618e0,first/second reset arguments and returns'},
     {'where':'appFw21916b0/237fb50/237f8fc','read':'message category,event,boot flag110c2,shutdown info179/17a,controller identity'},
     {'where':'appFw218fd0c/218ffe4/218fff0/2381bbc/2381c50','read':'three referenceIDs separately,newcontrollerptr,new init return,presenter creation; old scene sample is notlatecontrollerreadback'},
     {'where':'appFw2380778/237fe28/2380310/2380464/23803f4','read':'native30072 occurrence,flag110c3,UUDreturn,date187,force1098,final3screenIDs'},
     {'where':'appFw2324800/2323ff8/2324068','read':'rep pending IDs+110c4/+110c8,admission result2323eb0,actualsettingpage'},
     {'where':'CP-backend state','read':'separate primarybank identity,current/default data,317+2 reset entries,repeatcount4; before/after digest and rollback'},
     {'where':'libObj16ea10/16ea60,appFw16f1a1c','read':'dirty result,visible/active/resource roots and actualdraw; do not infer fromlayerpointer'}]
    proof['unproven']=[
      'Full raw kernel CP reset request/reply, actualQ/currentF and senderownership path are notcaptured.',
      'No liveCP Backup endpoint/backing/address mapping/reply consumption or reset return was implemented or tested.',
      'POWER_OFF attribution toUUD sequence_sys_request(tag+1b8=54,wire4022) is Bstrong; exactUPM kernel notification payload and factor/type/nextboot notsampled.',
      'Last scene is before open-screen initialization; lateactivecontroller and completed shutdown->boot reopen notproved.',
      'Manager specialpower std::function-to-vtable90 binding, boot-specific Sony-logo resource, complete first-visible Widget tree and allshared/generated event subscriptions unclosed.',
      'rep_boot exactproduct-specific pageorder, post-reset originalpowerOn handshake and finalfirstscreen remainunverified.',
      'No originalmenu pixels/inputfeedback/CP execution/physical poweroff/camera acceptance.' ]
    proof['method_reference']='https://www.capstone-engine.org/lang_python.html (checked2026-11-02; toolAPI only; Sony semantics frompinnedlocalbytes)'
    target=OUT/'boot-screen-proof.json';encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n'
    if check:assert target.read_text()==encoded,'proof differs from offline rebuild'
    else:target.write_text(encoded)
    print(f"PASS boot-screen audit: {len(proof['instruction_checks'])} instructions;2 screen calls;3 Backup waits;CP reset fixture317+2; explicitU gates")


def main():
    if len(sys.argv)==1:return rebuild()
    if sys.argv[1]=='--check':return rebuild(True)
    mode,name,*args=sys.argv[1:]
    im=Module() if name=='backup.ko' else Image(name)
    if mode=='dis':
        for r in im.dis(int(args[0],16),int(args[1],16)):print(r['va'],r['asm'],r.get('symbol',''),json.dumps(r.get('relocation',{})))
    elif mode=='str':
        for a in args:print(a,im.string(int(a,16)))
    elif mode=='strings':
        for r in im.strings(args[0]):print(r['va'],r['text'])
    elif mode=='xref':
        for a in args:print(a,json.dumps(im.xrefs(int(a,16))))
    elif mode=='sym':
        for name,s in im.sym.items():
            if re.search(args[0],name,re.I): print(name, dict(s.entry) if hasattr(s,'entry') else s)
    elif mode=='ptr':
        a,n=int(args[0],16),int(args[1],16)
        for v in range(a,a+n,8):print(hex(v),hex(im.ptrs.get(v,struct.unpack('<Q',im.read(v,8))[0])))
    else:raise ValueError(mode)
if __name__=='__main__':main()
