#!/usr/bin/env python3
"""Read-only FX3 setting save-trigger audit. Writes only adjacent proof; never executes firmware."""
import sys
sys.dont_write_bytecode = True
import hashlib, io, json, plistlib, re, struct, subprocess, tarfile
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM, CS_ARCH_ARM, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
VM = ROOT/'work/fx3-vm-20261101/menu-repair-01'
LIB = VM/'original-uipc/ap-projection/regular-files/usr/lib'
OUT = Path(__file__).resolve().parent
assert OUT == ROOT/'work/fx3-vm-20261101/lead-claude/audits/backup-save-trigger'
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
    def __init__(self, name="backup"):
        self.path=VM/("original-uipc/original-modules/"+name+".ko")
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


PINS = {'libObj.so':'c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae','libInfraMediaCommon.so':'1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b','libbkdmn.so':'cc0888d68d602468c26c6668aa2af964c86b12ddc447f83fe2fdb9035029838d','ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f',
 'backup':'8a8d8c949699c130c116d0006806d8b7f92b20869c92a72876529a2001d60c4d',
 'upm':'ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e',
 'libbackup.so':'6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d'}
# VA ranges are deliberately complete functions or explicit bounded windows.
BLOCKS = {'ap':[(0x2a69974,0x3c),(0x2ac0ec0,0x54),(0x29390e0,0x28),(0x2af9598,0x44),(0x2ab90a4,0x24),(0x2ab8e04,0x94),
 (0x2ec0548,0x1bc),(0x2ec0744,0x1f0),(0x2b22a6c,0x380),(0x2b2372c,0x1b4),
 (0x2b04380,0xe0),(0x2b04634,0x1dc),(0x2ab83d4,0xd4),(0x27395e8,0x50),
 (0x2a6dc04,0x40),(0x2b03ffc,0x174),(0x16f0a20,0xac),(0x16f0bd0,0x18),
 (0x292d5ec,0x1c),(0x292d6a8,0x20),(0x2ebf650,0x34),
 (0x2380464,0x8c),(0x2b726d8,0x58),(0x2d7e6ec,0xf0),
 (0x2381a60,0x20c),(0x285c658,0xae0),(0x2d412ec,0x1960),
 (0x2d43bfc,0x2f4),(0x2dae7a0,0x36c),(0x2dd6794,0x40),(0x2e3a19c,0xb8),
 (0x2dcfbd4,0x40),(0x2dd0094,0x40),(0x2df5090,0x390),(0x2df3d08,0x1b0),
 (0x2b7d224,0x94),(0x2dcef54,0x54),(0x2773c68,0x38)],
 'backup':[(0x0,0xb0),(0xd8,0x318),(0x3f0,0x2e8),(0x2728,0x18),
 (0x2ca0,0x6c),(0x2ea0,0x70),(0x3010,0x128),(0x3138,0xa8),
 (0x6800,0x288),(0x6a88,0x300),(0x8fd8,0x2c0),(0x7aa8,0xf8),(0x7e40,0x40)],
 'upm':[(0x7040,0x298),(0x7ba8,0x598),(0x8178,0x23c),(0xb270,0x6c)],
 'libbkdmn.so':[(0x22c0,0x84),(0x23cc,0xa0),(0x27ec,0x84),(0x28f0,0x58)],
 'libInfraMediaCommon.so':[(0x475d4,0x28)],'libObj.so':[(0x198820,0xc)],
 'libbackup.so':[(0x1ff0,0x48),(0x225c,0x6c)]}

def image(name):return Module(name) if name in ('backup','upm') else Image(name)
def sha(b):return hashlib.sha256(b).hexdigest()
def window(im,a,n):
 return {'start':hex(a),'bytes':n,'file_offset':hex(offset(im,a)),
  'raw':(im.elf.get_section_by_name('.text').data()[a:a+n] if isinstance(im,Module) else im.read(a,n)).hex(),
  'instructions':im.dis(a,n)}
def branches(im,targets):
 out={hex(t):[] for t in targets}
 for sec in im.elf.iter_sections():
  if not sec['sh_flags']&4:continue
  b=sec.data()
  for k,(w,) in enumerate(struct.iter_unpack('<I',b[:len(b)//4*4])):
   va=sec['sh_addr']+4*k
   if w&0x7c000000!=0x14000000:continue
   imm=w&0x3ffffff;imm=imm-(1<<26) if imm&(1<<25) else imm;t=va+4*imm
   if t in targets:out[hex(t)].append({'va':hex(va),'instruction':im.dis(va,4)[0]})
 return out

def rebuild(check=False):
 ims={n:image(n) for n in BLOCKS};a=ims['ap'];b=ims['backup']
 proof={'schema':1,'scope':'static original-byte audit and frozen AP101-r4 observations only; no QEMU or firmware execution',
 'address_domains':{'ap':'ELF image VA','backup/upm':'ET_REL .text offset (not fixed runtime VA)'},'sources':{}}
 for n,im in ims.items():
  digest=sha(im.raw);assert digest==PINS[n],('input drift',n,digest)
  proof['sources'][n]={'path':str(im.path),'bytes':len(im.raw),'sha256':digest}
 proof['code']={n:[window(im,x,z) for x,z in rows] for n,rows in BLOCKS.items() for im in [ims[n]]}
 proof['direct_branch_xrefs']=branches(a,{0x2b04738,0x2b04674,0x2b04634,0x2ab8470,0x2ebf66c,0x15936e0,0x2a69974})
 assert [r['va'] for r in proof['direct_branch_xrefs']['0x2ab8470']]==[
 '0x23804e8','0x2b7270c','0x2b72894','0x2b72a18','0x2b72eb0','0x2b73198','0x2b734a0','0x2d7e7c8']
 assert [r['va'] for r in proof['direct_branch_xrefs']['0x2b04738']]==['0x2739620']
 assert a.ptrs[0x46e34d8]==0x2a69974 and struct.unpack('<I',a.read(0x46e34c8,4))[0]==0x54e
 proof['instruction_checks']=[]
 expected={'ap':{
  0x2a6998c:'bl #0x29390f4',0x2a69998:'bl #0x2ab90a4',0x2ab90a8:'mov w0, #8',
  0x2ab90bc:'bl #0x2ab8e04',0x2b23754:'bl #0x2ec0744',0x2ec0788:'mov w1, #0x2cf0000',
  0x2ec0790:'bl #0x1592f80',0x2b22b24:'mov x26, #0x9400',0x2b22b2c:'movk x26, #0x7735, lsl #16',
  0x2b22b80:'bl #0x1592770',0x2b22c84:'cbnz w0, #0x2b22ae4',0x2b22cc0:'bl #0x2ebf650',
  0x2b04740:'cbz w2, #0x2b0480c',0x2b0474c:'strb wzr, [x1, #0xc38]',
  0x2b04798:'mov w1, #0xe',0x2ab8490:'strb w1, [x0, #0xc38]',0x2739620:'bl #0x2b04738',
  0x2b23844:'str wzr, [x23, #0xf24]',0x2b23870:'str w0, [x23, #0xf24]',
  0x2b03ffc:'stp x29, x30, [sp, #-0xb0]!',0x2b04054:'ldr w0, [x19, #0xa58]',
  0x2d43c80:'bl #0x2dcfbd4',0x2d43ce4:'bl #0x2dd0094'},
 'backup':{0x40:'bl #0x40',0x3170:'mov w0, #0',0x3174:'bl #0x3174',
  0x40c:'mov w1, #0x400000',0x428:'bl #0x428',0x610:'bl #0x610',
  0x90dc:'mov w2, #0xea60',0x907c:'mov w4, #0x3917',0x9084:'movk w4, #0x1a, lsl #16',
  0x3080:'mov w3, w0',0x30f0:'bl #0x30f0',0x2734:'bl #0xd8'}}
 for n,checks in expected.items():
  for va,want in checks.items():
   row=ims[n].dis(va,4)[0];assert row['asm']==want,(n,hex(va),row,want)
   proof['instruction_checks'].append({'image':n,**row})
 for va,nm in {0x40:'backupfile_save',0x428:'backup_senser_malloc',0x460:'backupfile_load_file',
  0x500:'Temporary_Data_init',0x508:'Overwrite_Data_init',0x5ac:'memcpy',0x610:'backupfile_save_file',
  0x2ed8:'__backup_sync_subsystem_mp',0x3174:'backupfile_save',0x90b4:'osal_snd_msg',
  0x90e0:'osal_rcv_msg_tmo'}.items():assert b.reloc[va]['symbol']==nm,(hex(va),nm)
 proof['language_callback_registration']={'va':'0x46e34c8','raw':a.read(0x46e34c8,24).hex(),
  'parameter':'0x54e','callback':'0x2a69974','callback_slot':'0x46e34d8'}
 raw=a.read(0x3806ad0,34);targets={str(i+1):hex(0x2b22cf0+4*v) for i,v in enumerate(struct.unpack('<17h',raw))}
 assert targets['8']=='0x2b23750' and targets['14']=='0x2b23804' and targets['15']=='0x2b23828' and targets['16']=='0x2b23850'
 proof['daemon_switch']={'va':'0x3806ad0','raw':raw.hex(),'targets':targets}
 table=a.read(0x2f99ab0,9);prod=[]
 for i,v in enumerate(table):
  target=0x16f0a70+4*v;row=a.dis(target,4)[0]
  index=0 if i==8 else int(row['asm'].split('#')[1],0)
  prod.append({'product_enum':i,'target':hex(target),'index':index,
   'idle_sync_skip_value':struct.unpack('<I',a.read(0x2f99f88+4*index,4))[0]})
 assert prod[4]['index']==6 and prod[4]['idle_sync_skip_value']==0
 assert a.ptrs[0x4174858]==0x3c20b57 and a.string(0x3c20b57)=='PRODUCT_MODEL_ALCIN_UUD'
 proof['product_sync_gate']={'source_getter':'0x292d5ec','index_global':'0x47ce0a8',
  'mapping_table_va':'0x2f99ab0','mapping_raw':table.hex(),'skip_table_va':'0x2f99f88',
  'skip_table_raw_9_values':a.read(0x2f99f88,36).hex(),'products':prod,
  'ALCIN_UUD_enum_record':{'va':'0x4174850','raw':a.read(0x4174850,16).hex(),'name':a.string(0x3c20b57)},
  'runtime_gate_value':'not captured; product-derived gate zero does not prove actual daemon call'}
 proof['idle_deadline']={'nanoseconds':(0x7735<<16)|0x9400,'seconds':2,
  'evidence':'0x2b22b24..b80 adds 2000000000 to system_clock::now, divides by 1000000000, calls pthread_cond_timedwait'}
 assert proof['idle_deadline']['nanoseconds']==2000000000
 proof['kernel_save_relocations']=[{'text_offset':hex(x),**r} for x,r in b.reloc.items() if re.search('backupfile_save|Backup_sync_all|Backup_save',r['symbol'])]
 proof['backup_shutdown_callback']={'handler_text_offset':'0x28','registration':[]}
 for sec in b.elf.iter_sections():
  if sec['sh_type']!='SHT_RELA':continue
  sy=b.elf.get_section(sec['sh_link'])
  for r in sec.iter_relocations():
   sm=sy.get_symbol(r['r_info_sym']);val=sm['st_value']+r['r_addend']
   if sm['st_shndx']==2 and val==0x28:
    proof['backup_shutdown_callback']['registration'].append({'section':sec.name,'offset':hex(r['r_offset']),'target':hex(val)})
 assert {'section':'.rela.data','offset':'0x3f0','target':'0x28'} in proof['backup_shutdown_callback']['registration']
 # Bind current ops table to named public ABI fields. No extraction.
 archive=ROOT/'work/sony-firmware-20261024/stage65-windows-cache-and-runtime-readiness/work/vendor-source-reference/range-resume-20261026/linux-kernel.complete.tar.gz'
 member='linux-kernel/include/linux/udif/driver.h'
 with tarfile.open(archive,'r:gz') as tf:hdr=tf.extractfile(member).read()
 assert sha(hdr)=='a2bde770cf31d79f7cf22d28ec91ac00934cc2713394a351733ec09539efd38e'
 typ=hdr.decode().split('typedef struct UDIF_DRIVER_OPS {',1)[1].split('} UDIF_DRIVER_OPS;',1)[0]
 fields=re.findall(r'const UDIF_MODULE(?:_INIT)?_CB\s+(\w+);',typ)
 assert fields==['init','exit','probe','remove','suspend','resume','shutdown']
 sy=b.elf.get_section_by_name('.symtab');dr={}
 for rel in b.elf.get_section_by_name('.rela.data').iter_relocations():
  sm=sy.get_symbol(rel['r_info_sym'])
  dr[rel['r_offset']]={'symbol':sm.name,'section':sm['st_shndx'],'target_offset':sm['st_value']+rel['r_addend']}
 assert dr[0x378]['target_offset']==0x3c0
 assert dr[0x3e0]['target_offset']==0x20 and dr[0x3f0]['target_offset']==0x28
 proof['native_driver_ops']={'GPL_reference_only':{'archive':str(archive),'member':member,'sha256':sha(hdr),'declaration':typ},
  'ops_pointer_data_offset':'0x378','ops_pointer_relocation':dr[0x378],'ops_data_offset':'0x3c0',
  'ops_raw':b.elf.get_section_by_name('.data').data()[0x3c0:0x3f8].hex(),
  'fields':{name:{'data_offset':hex(0x3c0+8*i),'relocation':dr.get(0x3c0+8*i)} for i,name in enumerate(fields)},
  'suspend':'text+20 returns0, no file save','shutdown':'text+28 checks Backup_bin_start and calls backupfile_save(0)',
  'boundary':'current module relocation/ABI binding; platform caller and complete shutdown not executed'}
 rr=b.reloc[0x7fc8];at=int(rr['value'],16)+rr['addend'];raw=b.elf.get_section(rr['section']).data()[at:at+114]
 jt={hex(i-1):hex(0x7b1c+4*v) for i,v in enumerate(struct.unpack('<57h',raw))}
 assert jt['0x35']=='0x7b70'
 proof['backup_command_dispatch']={'literal_text_offset':'0x7fc8','table_relocation':rr,'raw':raw.hex(),'targets':jt,
  'command35':'text+7b70 calls Backup_sync_all_for_suspend; this is not a hardware power-switch packet'}
 assert a.ptrs[0x46eb2a8]==0x46eb270 and a.ptrs[0x46eb278]==0x393add0 and a.ptrs[0x46eb2c0]==0x2d412ec
 ui,=struct.unpack('<I',a.read(0x4164dc8,4));assert ui==1 and a.ptrs[0x4164dd0]==0x3baf57b
 assert struct.unpack('<II',a.read(0x2f8f8e0,8))==(1,2)
 proof['metadata']={'power_sequence':{'typeinfo':'0x46eb270','name':a.string(0x393add0),
   'vtable_header':'0x46eb2a0','run_slot':'0x46eb2c0','run':'0x2d412ec'},
  'tact_power':{'enum_record_va':'0x4164dc8','enum_record_raw':a.read(0x4164dc8,16).hex(),
   'name':a.string(0x3baf57b),'pair_va':'0x2f8f8e0','pair_raw':a.read(0x2f8f8e0,8).hex(),
   'UI':1,'InfraInput':2,'main_slide_switch_equivalence':'unproven'},
  'language_getter_jump_table':{'va':'0x39a5ac8','raw':a.read(0x39a5ac8,34).hex()},
  'language_setter_jump_table':{'va':'0x39a5aec','raw':a.read(0x39a5aec,34).hex()}}
 proof['external_timer_boundary']={'library':'libbkdmn.so','bkdmn_write':'0x27ec',
  'write_then_timer':'0x2814 Backup_write ->0x2838 bkdmn_timer_set',
  'timer_set':'0x23cc..2468: requires +18==0, flags bit3 clear and bit2 set; delay is configured +20 times1000000, not fixed here',
  'sync':'0x22d0 reads registered subsystem u16 +4 ->0x22d8 Backup_sync_subsystem',
  'language_connection':'not established; language type8 calls Backup_write directly',
  'app_imports_bkdmn':sorted(n for n,v in a.sym.items() if n.startswith('bkdmn_'))}
 assert not proof['external_timer_boundary']['app_imports_bkdmn']
 proof['media_sync_boundary']={'library':'libInfraMediaCommon.so','callsite':'0x475f0',
  'subsystem':0xd5,'cannot_substitute_for_APP_language_subsystem':0x2cf}
 proof['model_sync_flag']={'address':'0x8e5dc38','setter':'0x2ab8470','set_instruction':'0x2ab8490',
  'test':'0x2b0473c','clear_before_wait':'0x2b0474c','type':14,
  'scope':'all direct immediate branch callers of setter enumerated; arbitrary indirect stores/calls not globally excluded'}
 # Frozen, already terminated run: no live guest queries.
 run=VM/'runtime/runs/ap101r4tile600-be9996d0';snapshots={}
 for fn in ['Backup-native-file-native-load-before-AP.bin','Backup-native-file-final-before-shutdown.bin','backup-reserved-ram.bin']:
  path=run/fn;data=path.read_bytes();h,it=entries(data)
  fixed={'Backup-native-file-native-load-before-AP.bin':'552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e',
   'Backup-native-file-final-before-shutdown.bin':'eb70e888c27766b52d4e27f4353bc73d63fac325c6bb545d478bd156f588b26e',
   'backup-reserved-ram.bin':'a20f0c92a790c0f911c443fab1eee204316f443ddb764d75e19d97eeea992fd6'}
  assert sha(data)==fixed[fn],('snapshot drift',fn)
  snapshots[fn]={'path' :str(path),'bytes':len(data),'sha256':sha(data),'AP_bank':h,
   'language':it[0x2cf0000],'force':it[0x2cf0014]}
 assert snapshots['backup-reserved-ram.bin']['language']['raw']=='00'
 assert snapshots['Backup-native-file-final-before-shutdown.bin']['language']['raw']=='20'
 proof['AP101_saved_language_RAM_vs_file']=snapshots
 readbacks=run/'ap101-native-file-readbacks.json';rb=readbacks.read_bytes()
 assert sha(rb)=='6453fe325a5752546b363d48e3e190e895160e467ef981a97bfd75a327ee9b5d'
 proof['sources']['readbacks']={'path':str(readbacks),'bytes':len(rb),'sha256':sha(rb)}
 proof['file_readbacks']=json.loads(rb)
 proof['verified_file_readbacks']=[]
 for r in proof['file_readbacks']:
  path=Path(r['path']);data=path.read_bytes();assert sha(data)==r['sha256']
  assert data[0x8dd85]==0x20
  proof['verified_file_readbacks'].append({'label':r['label'],'sha256':sha(data),
   'bytes':len(data),'generation':r['generation'],'host_monotonic':r['host_monotonic'],
   'language_raw':'20','path':str(path)})
 gate=run/'ap101-host-input-gate.json';gb=gate.read_bytes()
 assert sha(gb)=='ec7d6a473c275ed6c9faca2a37f48579a9c900ad85e99557349eaf58691dfe1b'
 steps=json.loads(gb);proof['host_input_timing']={'path':str(gate),'sha256':sha(gb),
  'step10_confirm_sent':steps[9]['host_monotonic'],'step11_English_observed_MENU_sent':steps[10]['host_monotonic'],
  'last_file_readback':proof['file_readbacks'][-2]['host_monotonic'],
  'seconds_after_confirm_send':proof['file_readbacks'][-2]['host_monotonic']-steps[9]['host_monotonic'],
  'seconds_after_English_observed_MENU_send':proof['file_readbacks'][-2]['host_monotonic']-steps[10]['host_monotonic'],
  'caution':'host send/readback timestamps; not exact guest parameter commit time and not guest printk seconds'}

 proof['unproven']=[
 'Exact AP101-r4 daemon gate/f24/w19 and native Backup_sync_subsystem return; no runtime hook on this path was installed.',
 'Whether idle subsystem file save failed allocation/file load/selection or sync was disabled; do not call no-op30 evidence a missing full-sync defect.',
 'Full MENU-close/mode/battery/media event graph and all indirect function-pointer paths are not exhausted.',
 'Complete physical main switch -> CP/SysCon/UPM input payload and current VM support for that event.',
 'Native shutdown/poweroff reaching backup .text+28 or explicit suspend-save .text+3174 in this VM, all peripheral callbacks, and physical durability.',
 'UI date reconfirmation, input power key 2, or shutdown candidate actually causing a new persisted language generation; no execution performed.']
 out=json.dumps(proof,ensure_ascii=False,indent=2)+'\n';dest=OUT/'save-trigger-proof.json'
 if check:assert dest.read_text()==out,'proof drift';print('PASS: independently rebuilt proof matches; static and frozen saved evidence only')
 else:dest.write_text(out);print('PASS: save-trigger-proof.json rebuilt; no QEMU/firmware execution')

if __name__=='__main__':
 kind=sys.argv[1] if len(sys.argv)>1 else 'proof'
 if kind=='dis':
  im=image(sys.argv[2])
  for r in im.dis(int(sys.argv[3],16),int(sys.argv[4],16)):print(json.dumps(r,ensure_ascii=False))
 elif kind=='xref':print(json.dumps(image(sys.argv[2]).xrefs(int(sys.argv[3],16)),indent=2))
 else:assert kind in ('proof','--check');rebuild(kind=='--check')
