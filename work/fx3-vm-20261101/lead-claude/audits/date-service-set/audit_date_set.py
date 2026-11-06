#!/usr/bin/env python3
"""Read-only FX3 date service audit; only adjacent date-set-proof.json is written."""
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
RUN = VM/'runtime/runs/ap97r2alpha600-cd3c48f7'
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/date-service-set'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

class Image:
    def __init__(self, name):
        self.name=name
        self.path=(ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin' if name=='cp' else VM/'original-uipc/original-modules'/name if name.endswith('.ko') else LIB/({'ap':'appFw.so','udate':'libosal_udate.so','uipc':'libosal_uipc.so'}.get(name,name)))
        self.raw=self.path.read_bytes()
        if name=='cp':
            self.rel=False;self.cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB);self.cs.skipdata=True
            self.sym={};self.ptrs={};self.plt={};self.relocs={};return
        self.elf=ELFFile(io.BytesIO(self.raw))
        self.rel=self.elf['e_type']=='ET_REL'
        self.segs=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
        self.cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM); self.cs.skipdata=True
        self.ptrs={};self.plt={};self.relocs={}
        sy=self.elf.get_section_by_name('.symtab' if self.rel else '.dynsym')
        self.sym={s.name:(s['st_value'],s['st_size'],s['st_shndx']) for s in sy.iter_symbols()} if sy else {}
        rel=self.elf.get_section_by_name('.rela.plt')
        if rel:
            sy=self.elf.get_section(rel['sh_link']); pv=self.elf.get_section_by_name('.plt')['sh_addr']
            self.plt={pv+32+16*n:sy.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations())}
        for sec in self.elf.iter_sections():
            if sec['sh_type']!='SHT_RELA':continue
            sy=self.elf.get_section(sec['sh_link'])
            for r in sec.iter_relocations():
                i=r['r_info_sym'];s=sy.get_symbol(i) if i else None
                if self.rel:
                    sn=s.name if s else ''
                    if s and not sn and isinstance(s['st_shndx'],int):sn=self.elf.get_section(s['st_shndx']).name
                    self.relocs[(self.elf.get_section(sec['sh_info']).name,r['r_offset'])]={'symbol':sn,'addend':r['r_addend'],'type':r['r_info_type']}
                else:self.ptrs[r['r_offset']]=(s['st_value'] if s else 0)+r['r_addend']
    def offset(self,a,n=1,section='.text'):
        if self.name=='cp':assert a>=0x108000 and a+n<=0x108000+len(self.raw);return a-0x108000
        if self.rel:
            s=self.elf.get_section_by_name(section);assert a+n<=s['sh_size'];return s['sh_offset']+a
        s=next(s for s in self.segs if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
        return s['p_offset']+a-s['p_vaddr']
    def read(self,a,n,section='.text'):
        o=self.offset(a,n,section);return self.raw[o:o+n]
    def dis(self,a,n):
        rows=[]
        for i in self.cs.disasm(self.read(a,n),a):
            row={'va':hex(i.address),'raw':i.bytes.hex(),'asm':(i.mnemonic+' '+i.op_str).strip()}
            if self.rel and ('.text',i.address) in self.relocs:row['relocation']=self.relocs[('.text',i.address)]
            if i.mnemonic in ('b','bl') and i.op_str.startswith('#'):row['symbol']=self.plt.get(int(i.op_str[1:],16),'')
            rows.append(row)
        return rows
    def strings(self,pattern):
        out=[]
        for m in re.finditer(rb'[ -~]{5,}',self.raw):
            t=m.group().decode()
            if not re.search(pattern,t,re.I):continue
            if self.rel:
                s=next((s for s in self.elf.iter_sections() if s['sh_offset']<=m.start()<s['sh_offset']+s['sh_size']),None)
                if s is not None:out.append({'section':s.name,'offset':hex(m.start()-s['sh_offset']),'file_offset':hex(m.start()),'text':t})
            else:
                s=next((s for s in self.segs if s['p_offset']<=m.start()<s['p_offset']+s['p_filesz']),None)
                if s is not None:out.append({'va':hex(s['p_vaddr']+m.start()-s['p_offset']),'text':t})
        return out
    def xrefs(self,target):
        out=[]
        for sec in self.elf.iter_sections():
            if not sec['sh_flags']&4:continue
            b=sec.data();base=sec['sh_addr']
            for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
                a=base+4*k
                if w&0x7c000000==0x14000000:
                    imm=w&0x3ffffff
                    if imm&(1<<25):imm-=1<<26
                    if a+4*imm==target:out.append(hex(a))
        return {'branch':out,'pointers':[hex(k) for k,v in self.ptrs.items() if v==target]}

BLOCKS={
 'ap':[(0x1b40854,0x50),(0x23c16c4,0x90),(0x23c1398,0x48),(0x27d38d0,0x1fc),
       (0x27d3acc,0xe0),(0x273e100,0xb0),(0x271b130,0x58),
       (0x2717874,0x2c),(0x2c38d40,0x140),(0x2c390e8,0x60),
       (0x2b72168,0x98),(0x2b7250c,0x228),(0x2b72754,0x1a0),
       (0x2b728f4,0x16c),(0x2b72c58,0xa8),(0x2b73510,0xcc),
       (0x2f72354,0x1c8),(0x2f71fa0,0x60),(0x2d7e5dc,0x200),
       (0x2380580,0x20),(0x276de30,0xa0),(0x2a69a68,0x3c),
       (0x2ab9028,0x2c),(0x2b2372c,0xc),(0x2ebfd30,0x5c)],
 'udate':[(0x2ef4,0xc8),(0x2fbc,0x80),(0x3c44,0x2d0),
          (0x3f64,0x2b0),(0x4a80,0x1c8),(0x4c48,0x244),
          (0x4e8c,0x1ac)],
 'udate.ko':[(0,0xfc),(0x258,0x1c4),(0x450,0x208),(0x668,0x88),
             (0x940,0xdc),(0xa28,0x470),(0x15a8,0x1b8),(0x17c8,0x84),
             (0x1988,0x1e4),(0x1b98,0xdc),(0x1c98,0x60),
             (0x1d00,0x20c),(0x2390,0x21c),(0x25f8,0x11c),(0x2740,0xbc)],
 'uipc':[(0x3a98,0x13c),(0x61e8,0x160),(0x6390,0x20),(0x6458,0xc)],
 'cp':[(0x49cc44,0x260),(0x49cf24,0x8e),(0x49d090,0x114),
       (0x49d434,0xbe),(0x49d57c,0x70),(0xa86288,0x1b0),
       (0xa864f6,0x76)]}

CHECKS=[
 ('ap',0x1b40890,'ldr x0, [x0, #0xa68]'),
 ('ap',0x23c1744,'bl #0x27d3acc'),('ap',0x27d3b74,'bl #0x27d38d0'),
 ('ap',0x27d3a9c,'str wzr, [x29, #0x70]'),('ap',0x27d3aac,'bl #0x273e100'),
 ('ap',0x271b158,'mov w1, #0x63'),('ap',0x273e158,'bl #0x271b130'),
 ('ap',0x271789c,'b #0x2c390e8'),('ap',0x2c3911c,'bl #0x2c38d40'),
 ('ap',0x2c38d70,'str w0, [x19, #0x1b8]'),
 ('ap',0x2b7354c,'bl #0x2b725c8'),('ap',0x2b73580,'bl #0x2b72754'),
 ('ap',0x2b72680,'bl #0x2f724ec'),('ap',0x2b72684,'cbnz w0, #0x2b7273c'),
 ('ap',0x2b726b8,'mov w1, #0'),('ap',0x2b726bc,'bl #0x2b72520'),
 ('ap',0x2b726c4,'bl #0x2b7250c'),('ap',0x2b721dc,'mov w0, #0x1098'),
 ('ap',0x2b72554,'strb w0, [x1]'),('ap',0x2b7255c,'strb w0, [x1]'),
 ('ap',0x2b72518,'b #0x275aadc'),('ap',0x2b727c0,'bl #0x2f7251c'),
 ('ap',0x2b72808,'bl #0x2f724ec'),('ap',0x2b7280c,'cbnz w0, #0x2b728dc'),
 ('ap',0x2b72848,'mov w1, #1'),('ap',0x2380590,'bl #0x276de54'),
 ('ap',0x276de34,'mov w1, #1'),('ap',0x276de48,'bl #0x273e100'),
 ('ap',0x2f72440,'mov w2, #0x20'),('ap',0x2f72444,'movk w0, #0x8090, lsl #16'),
 ('ap',0x2f72494,'bl #0x1593de0'),('ap',0x2f724a0,'ldrsh w19, [x21, #2]'),
 ('ap',0x2f724b0,'bl #0x15943d0'),('ap',0x2d7e6f4,'mov w19, w0'),
 ('ap',0x2d7e6f8,'cbnz w0, #0x2d7e658'),
 ('ap',0x2ab902c,'mov w0, #5'),('ap',0x2b23730,'bl #0x2ebfd30'),
 ('ap',0x2ebfd58,'bl #0x1592f80'),('ap',0x2ebfd6c,'bl #0x1592f80'),
 ('udate',0x2f58,'bl #0x2a20'),('udate',0x2f5c,'strh w0, [x19, #2]'),
 ('udate',0x2fe4,'bl #0x2c00'),('udate',0x3eb8,'bl #0x28c0'),
 ('udate',0x3ec4,'ldrsh w19, [x29, #0x72]'),
 ('udate',0x3ef0,'bl #0x28f0'),('udate',0x3f04,'bl #0x2b00'),
 ('udate',0x3f0c,'bl #0x2a30'),('udate',0x40c0,'mov w1, #-1'),
 ('udate',0x418c,'mov w2, #0x3e8'),('udate',0x41e8,'bl #0x2880'),
 ('udate.ko',0x34,'stp x0, x1, [x19]'),
 ('udate.ko',0x44,'str x1, [x19, #0x18]'),
 ('udate.ko',0x6ac,'bl #0'),('udate.ko',0x6d8,'bl #0x6d8'),
 ('udate.ko',0xc84,'bl #0x668'),('udate.ko',0x1624,'strh w0, [x19, #2]'),
 ('udate.ko',0x1df4,'ubfx x1, x27, #0x1c, #3'),
 ('udate.ko',0x2664,'mov w1, #-1'),('udate.ko',0x2600,'cmp w0, #4'),
 ('udate.ko',0x2748,'cmp w0, #4'),('udate.ko',0x27b8,'bl #0x27b8'),
 ('cp',0x49cc8c,'movs r2, #0x2c'),('cp',0x49cd18,'str r0, [sp, #0x24]'),
 ('cp',0x49cd28,'add r3, sp, #0x48'),('cp',0x49cd86,'cmp r4, #4'),
 ('cp',0x49cde0,'movs r0, #4'),('cp',0x49cde6,'strh r4, [r1, #0x28]'),
 ('cp',0x49d0dc,'str.w r0, [fp, #0xc]'),
 ('cp',0x49d118,'mov.w r2, #-1'),('cp',0xa863ba,'stm r0!, {r1, r2, r3, r4}')]

def newc_members(raw):
    off=0; out={}
    while True:
        h=raw[off:off+110];assert h[:6] in (b'070701',b'070702')
        f=[int(h[6+i*8:14+i*8],16) for i in range(13)]
        name=raw[off+110:off+110+f[11]-1].decode()
        off=(off+110+f[11]+3)&~3
        if name=='TRAILER!!!':return out
        assert name not in out and not name.startswith('/') and '..' not in Path(name).parts
        out[name]=raw[off:off+f[6]];assert len(out[name])==f[6]
        off=(off+f[6]+3)&~3

def backup_key(b,key):
    ns,np,start,size=struct.unpack_from('<4I',b,16)
    assert b[12:16]==b'BK4\0'
    count,idx=struct.unpack_from('<HI',b,256+(key>>16)*6)
    assert key&65535<count and idx+count<=np
    pos=256+ns*6+(idx+(key&65535))*6
    attr,ptr=struct.unpack_from('<HI',b,pos);assert ptr!=0xffffffff
    n,off=ptr>>24,ptr&0xffffff
    if n==255:n=struct.unpack_from('<H',b,off)[0];off+=2
    elif n==0:n,m=struct.unpack_from('<HH',b,off);off+=4;assert n<=m
    assert start<=off and off+n<=start+size
    return {'key':f'{key:08x}','entry_offset':hex(pos),'attribute':hex(attr),'file_offset':hex(off),'raw':b[off:off+n].hex()}

def rebuild(check=False):
    proof={'schema':1,'scope':'offline static extraction plus frozen AP97-r2; no QEMU or guest execution',
       'line_convention':'one-based bytes split at LF only, CR stripped after counting',
       'sources':{},'code':{},'instruction_checks':[]}
    def source(path,pin=None):
        b=path.read_bytes();sha=hashlib.sha256(b).hexdigest()
        if pin:assert sha==pin,(str(path),sha)
        proof['sources'][str(path.relative_to(ROOT))]={'bytes':len(b),'sha256':sha}
        return b
    pins={'ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
      'udate':'5a61d80cc95fbda9496bf3424c4a58fb77a3085f494e2401ba0eda91397a8df9',
      'udate.ko':'a3cbb9977915259a5a9d5e16e49adbb58f26c43d2ad2c63381c60e1103d205bb',
      'uipc':'09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3',
      'cp':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'}
    images={name:Image(name) for name in BLOCKS}
    for name,im in images.items():
        source(im.path,pins.get(name))
        proof['code'][name]=[{'va':hex(v),'length':n,'file_offset':hex(im.offset(v,n)),
           'raw':im.read(v,n).hex(),'disassembly':im.dis(v,n)} for v,n in BLOCKS[name]]
    for name,v,expected in CHECKS:
        rows=images[name].dis(v,4);assert rows[0]['asm']==expected,(name,hex(v),rows,expected)
        proof['instruction_checks'].append({'image':name,**rows[0]})
    ap,usr,kern,cp=(images[x] for x in ['ap','udate','udate.ko','cp'])
    def signed_table(im,a,n,base,scale=4,section='.text'):
        return [hex(base+scale*x) for x in struct.unpack(f'{n}b',im.read(a,n,section))]
    proof['dispatch_tables']={
      'user_op0_to_5':signed_table(usr,0x5048,6,0x2f28),
      'clock_option0_to_7':signed_table(ap,0x391d698,8,0x2b73548),
      'kernel_fact1_to_8_with_timezone':signed_table(kern,0,8,0xb7c,section='.rodata'),
      'kernel_fact1_to_8_without_timezone':signed_table(kern,8,8,0xd28,section='.rodata'),
      'kernel_distribution_type1_to_6':signed_table(kern,0x128,6,0x1db0,section='.rodata'),
      'CP_distribution_type1_to_6':[hex(0x49ce5e+2*x) for x in cp.read(0x49ce5e,6)]}
    assert proof['dispatch_tables']['user_op0_to_5']==['0x2f6c','0x2fac','0x2fb4','0x2fb4','0x2f28','0x2f74']
    assert proof['dispatch_tables']['kernel_distribution_type1_to_6']==['0x1e90','0x1e40','0x1e00','0x1df0','0x1de0','0x1db0']
    assert proof['dispatch_tables']['CP_distribution_type1_to_6']==['0x49ce8c','0x49ce7a','0x49ce78','0x49ce6c','0x49ce64','0x49ce8e']
    assert kern.read(0x1b8,16,'.data')==bytes(8)+struct.pack('<II',1,0)
    proof['kernel_initial_distribution_peers']={'section':'.data','offset':'0x1b8','raw':kern.read(0x1b8,16,'.data').hex(),'slots':[{'chip':0,'semaphore':0},{'chip':1,'semaphore':0}]}
    proof['metadata']={}
    for label,v,n in [('clock_RTTI',0x391d6a0,32),('remote_RTTI',0x394b880,64),('clock_initial_method',0x391dab8,80),('UI_date_controller_method',0x313c6a8,128)]:
        proof['metadata'][label]={'va':hex(v),'text':ap.read(v,n).split(b'\0')[0].decode()}
    ptrs={0x4737a68:0x23c16c4,0x47aa4c8:0x46e59d0,0x46e59f0:0x2b73510,
       0x46ee198:0x2d7e5dc,0x4029590:0x2717874,0x46e3478:0x2a69a68}
    for v,target in ptrs.items():assert ap.ptrs[v]==target
    proof['metadata']['relocated_pointers']={hex(v):hex(ap.ptrs[v]) for v in ptrs}
    proof['ABI']={
      'AP_user_set_request':{'bytes':32,'destination':'0x80900141','reply':'same caller-owned allocation; transport return plus s16 at +2; caller frees once',
       'fields':[{'offset':o,'size':n,'field':f} for o,n,f in [(0,2,'operation:0 synchronous set; 4 synchronous set plus user type5 distribution/Backup sync'),(2,2,'s16 status initially0; callback overwrites'),(4,2,'year LE'),(6,1,'month'),(7,1,'day'),(8,1,'hour'),(9,1,'minute'),(10,1,'second'),(11,1,'datetime reserved byte0'),(12,2,'milliseconds; callback forces0'),(14,2,'datetime reserved bytes0'),(16,1,'time type:0 local civil,1 UTC running,2 not set,3 omit'),(17,3,'datetime reserved bytes0'),(20,2,'signed TD minutes'),(22,2,'signed DST minutes'),(24,2,'timezone discriminator:0 valid,1 omit'),(26,2,'timezone reserved'),(28,2,'set reason/fact1 for app wrapper'),(30,2,'trailing reserved: builder does not explicitly initialize')]]},
      'kernel_direct':{'service':'0x0090013d','bytes':48,'prefix':[0,16],'operation_at':16,'status_s16_at':18,'datetime_at':20,'timezone_at':36,'reason_u16_at':44,'set_op':0,'get_op':2,'initial_op':3},
      'distribution':{'bytes':44,'AP_receive_queue':'0x009005c5','AP_source':'0x809005c5','CP_destination':'0x909005c5','CP_source':'0x909005c5',
       'fields':[{'offset':o,'size':n,'field':f} for o,n,f in [(0,4,'type1 ready /2 get clock /3 native Backup flag operation /4 done /5 Backup sync /6 exit'),(4,4,'s32 service result on type2 response'),(8,4,'reply requested flag'),(12,4,'dynamic reply Q for type2; never use as source chipID'),(16,16,'datetime on type2 response'),(32,8,'timezone on type2 response'),(40,2,'reason/fact copied from ready'),(42,2,'padding, not read by done receiver')]]},
      'success':{'AP_transport':0,'AP_s16_status':0,'CP_type2_s32_status':0,'CP_type4_has_status_field':False,'type4_matching':'reason !=4 plus source chipID bits28..30 must match outstanding peer semaphore; no original generation token'}}
    # Static schema illustration only; not a recovered AP97 request.
    sample=bytearray(32);struct.pack_into('<H',sample,4,2021);sample[6:11]=bytes([1,1,0,0,0]);struct.pack_into('<h',sample,20,540);struct.pack_into('<H',sample,28,1)
    proof['ABI']['static_example_only']={'raw':sample.hex(),'byte_offsets':[{'offset':i,'hex':f'{v:02x}'} for i,v in enumerate(sample)],'not_observed_on_wire':True,'padding_zeroed_for_illustration_only':True}
    # Freeze candidate, actual original members, and the original run receipts.
    cpio=VM/'runtime/ap97-r2-const-alpha-date-observe/guest.cpio'
    members=newc_members(source(cpio,'5dd10e134d8bd3a947d259f12269744fbef9361a8f94b61382ebae2e04cb52c7'))
    proof['guest_member_identity']={}
    for n in ['usr/kmod/udate.ko','usr/lib/libosal_udate.so','simulation/seed-date-clock-v3',
              'simulation/fx3-cp-backup-reset-v1.ko','simulation/fx3-preset-context-v2-screen.so']:
        b=members[n];proof['guest_member_identity'][n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    assert members['usr/kmod/udate.ko']==kern.raw and members['usr/lib/libosal_udate.so']==usr.raw
    init=members['init'];proof['guest_init_lines']=[{'line':n,'text':l.decode()} for n,l in enumerate(init.split(b'\n'),1) if any(x in l for x in [b'insmod /simulation/fx3-cp-backup',b'insmod /usr/kmod/udate',b'/simulation/seed-date-clock',b'Backup_load='])]
    helpers=VM/'runtime/helpers'
    for n in ['seed-date-clock-v3.c','fx3-date-observe97r2.h','fx3-preset-context-v3-date97.c','fx3-cp-backup-reset-v1.c']:
        source(helpers/n)
    for local,member in [('seed-date-clock-v3','simulation/seed-date-clock-v3'),('fx3-preset-context-v3-date97.so','simulation/fx3-preset-context-v2-screen.so'),('fx3-cp-backup-reset-v1.ko','simulation/fx3-cp-backup-reset-v1.ko')]:
        assert source(helpers/local)==members[member],local
    receipt=json.loads(source(RUN/'receipt.json'));assert receipt['qemu_exit']==0 and receipt['inputs_unchanged']
    acc=json.loads(source(VM/'runtime/ap97r2alpha600-cd3c48f7-acceptance.json'))
    proof['acceptance_selected']={k:acc[k] for k in ['process_lifecycle_pass','native_assert_count','strict_health_pass','strict_missing_markers','all_missing_are_untriggered_date_point','date_records']}
    log=source(RUN/'serial.log');lines=log.split(b'\n');proof['serial_LF_segments']=len(lines)
    patterns=[b'FX3_UDATE_RC',b'DATE_CLOCK_',b'FX3_DATE97_',b'909005c5',b'udate_set_resource()',
      b'udate_wait_for_distribution_done+',b'udate_get_localtime+',b'udate_set_date+',b'udate_proc_read_clock+',
      b'FX3_PRESET_CONTEXT_BOUND',b'FX3_TASK_SNAPSHOT_427_BEGIN',b'FX3_TASK_SNAPSHOT_427_END',b'FX3_AP89_SCREEN_OPEN_ENTER']
    proof['serial_evidence']=[{'LF_line':n,'text':l.rstrip(b'\r').decode(errors='replace')} for n,l in enumerate(lines,1) if any(p in l for p in patterns)]
    points=[l for l in lines if b'FX3_DATE97_POINT' in l];sync=[l for l in lines if b'FX3_DATE97_SYNC' in l]
    assert len(points)==0 and len(sync)==1 and b'captured=0' in sync[0] and b'phase=before' in sync[0]
    proof['observer_limits']={'point_count':len(points),'sync_count':len(sync),'captured_body_count':0,
      'no_after_marker':True,'no_inference_that_request_is_remote':True,
      'acceptance_line_number_mismatch':'acceptance date_records says14139; raw LF recomputation says14137; use recomputed raw LF'}
    backup=source(RUN/'backup-after-setup.bin')
    proof['backup_keys']=[backup_key(backup,k) for k in [0x02cf0014,0x01070140,0x02cf01b4,0x02cf0000]]
    assert [x['raw'] for x in proof['backup_keys'][:2]]==['01','01']
    proof['runtime_stack_mapping']=[{'symbol_text':s,'actual_text_return':hex(a),'meaning':m} for s,a,m in [
      ('udate_wait_for_distribution_done+0x74',0x266c,'after osal_wai_sem_tmo(timeout=-1)'),
      ('udate_get_localtime+0x28c',0x6dc,'unnamed commit helper after wait_for_distribution_done; not a get_localtime wait'),
      ('udate_set_date+0x260',0xc88,'set reason1/2 commit helper return'),
      ('udate_proc_read_clock+0x4a0',0x1620,'unnamed original direct service callback after udate_set_date')]]
    proof['findings']=[
      {'grade':'A','finding':'2d7e6f4 belongs to remote date sequence, not UI sequence_clock; probe absence alone does not show UI set was never queued','evidence':['appFw RTTI394b880','vtable46ee198','clock run2b73510']},
      {'grade':'A','finding':'native kernel clock set service exists and advances after BY_BOOT; current failing queue is waiting native cross-chip distribution completion','evidence':['serial1105..1123','serial26232..26235','serial54464..54467','serial81524..81527','.text+2664']},
      {'grade':'B strong','finding':'early request likely boot force-setting option1 queued from2380590; it blocks later UI option0/2 on SeqQueueCommon','evidence':['2380590','276de30','2b73580','serial14137','serial26232..26235'],'limit':'no user stack, task identity, or captured32B request; exact early caller not proved'},
      {'grade':'A','finding':'public software CP owner returns0 for unhandled909005c5, provides no receiver completion; boot ready44B observed but only40B captured','evidence':['serial1114..1115','fx3-cp-backup-reset-v1.c:19','.text+2390..25a8']},
      {'grade':'U','finding':'exact pending peer semaphore/reason and UI transaction generations are not sampled; no date success or persistence success claimed','evidence':['captured=0','force keys01','no POINT markers']}]
    proof['minimal_contract']=[
      'Keep original AP kernel/user udate, original running UTC+TD+DST clock and native setters; do not return synthetic success at80900141 or clear1098.',
      'Extend the existing single CP public owner for destination909005c5 with a bounded, serialized software remote-clock consumer; no second public registration.',
      'Accept native44B type1 with actual source/reason, preserve input ownership, request type2 snapshot to actual AP source with native dynamic replyQ; never block reentrantly in the public send hook.',
      'Validate native type2 response result0/date/timezone, convert local civil to UTC, maintain advancing remote clock from original monotonic time, commit/readback before type4; invalid or unsupported input never receives success.',
      'For reason!=4 send freshly allocated44B type4, echo reason at40, source909005c5, destination actual AP source; zero unused software slack explicitly, preserve actual allocation/free rules and no duplicate completion.',
      'For BY_BOOT reason4 preserve original special no-type4 semantics; support type2 responses and type3 native Backup flags/type5 sync only to the proven software scope, never claim physical RTC or CP firmware execution.',
      'Observe kernel2740 peer-match/sem signal→266c wait return→1624 status0→user3ec4→2f72498→manual2b72684 or2b7298c; remote2d7e6f4 only if remote sequence was actually selected.',
      'Observe native1098 change→type5 daemon→both Backup_write returns→native key readback0; RAM export and real file persistence are separate acceptance gates.']
    proof['unproven']=[
      'Actual AP97 early caller/task/user stack, exact32B contents and pending reason/peer semaphore; later UI queue membership.',
      'Full runtime44B type1 reason and native CP transport ownership/canary sizes; only boot40B prefix captured.',
      'Runtime receipt that original CP thread is bound to the inferred909005c5 queue; CP functions are only statically examined.',
      'A functioning new remote-clock consumer, its semaphore completion, native manual return0, force0 and daemon writes; no implementation or VM run in this audit.',
      'Original Backup disk-save, reboot persistence, host RTC precision, CP hardware RTC, camera or sensor acceptance.']
    proof['method_source']={'checked_date':'2026-11-02','url':'https://www.capstone-engine.org/lang_python.html','limit':'API documentation supports disassembly method only; private Sony semantics are derived from pinned originals'}
    encoded=json.dumps(proof,ensure_ascii=False,indent=2)+'\n';target=OUT/'date-set-proof.json'
    if check:assert target.read_text()==encoded,'saved proof differs from independent rebuild'
    else:target.write_text(encoded)
    print(f'PASS date-set audit: {len(CHECKS)} instruction checks; native set/distribution, corrected manual/remote paths, AP97 stack+CP owner; runtime implementation remains untested')

def main():
    if len(sys.argv)==1:return rebuild()
    if sys.argv[1]=='--check':return rebuild(True)
    mode,name,*args=sys.argv[1:];im=Image(name)
    if mode=='dis':
        for r in im.dis(int(args[0],16),int(args[1],16)):print(r['va'],r['asm'],r.get('symbol',''),r.get('relocation',''))
    elif mode=='sym':
        for name,(a,n,s) in im.sym.items():
            if re.search(args[0],name,re.I):print(hex(a),hex(n),s,name)
    elif mode=='strings':
        for r in im.strings(args[0]):print(r)
    elif mode=='xref':
        for a in args:print(a,im.xrefs(int(a,16)))
    elif mode=='ptr':
        for a in range(int(args[0],16),int(args[0],16)+int(args[1],16),8):print(hex(a),hex(im.ptrs.get(a,struct.unpack('<Q',im.read(a,8))[0])))
    else:raise ValueError(mode)
if __name__=='__main__':main()
