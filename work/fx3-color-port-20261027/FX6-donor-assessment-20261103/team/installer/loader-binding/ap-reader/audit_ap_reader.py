#!/usr/bin/env python3
"""Read-only original ELF relocation/branch audit for FX3 im -> appFw loader."""
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101')
IM=ROOT/'fx3-audit/original-members/nflasha15/bin/im.elf'
DB=ROOT/'menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libIMDB.so'
APP=ROOT/'fx3-audit/original-members/nflasha15/lib/appFw.so'
VM=ROOT/'menu-repair-01/runtime/runs/ap94r3center-f3bba0ba/serial.log'
EXPECTED={IM:'5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91',
          DB:'6ceaea432bc7c4645897c2f1272941b33b0c04115ec62ffa000b37faf3d8517d',
          APP:'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'}

class ELF:
    def __init__(self,path):
        self.path=path;self.b=path.read_bytes()
        assert self.b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',self.b,18)[0]==183
        phoff=struct.unpack_from('<Q',self.b,32)[0];phentsz,phnum=struct.unpack_from('<HH',self.b,54)
        self.loads=[]
        for i in range(phnum):
            p_type,flags,off,va,_,filesz,memsz,_=struct.unpack_from('<IIQQQQQQ',self.b,phoff+i*phentsz)
            if p_type==1:self.loads.append((va,off,filesz))
        shoff=struct.unpack_from('<Q',self.b,40)[0];shentsz,shnum,shstr=struct.unpack_from('<HHH',self.b,58)
        sh=[struct.unpack_from('<IIQQQQIIQQ',self.b,shoff+i*shentsz) for i in range(shnum)]
        names=self.b[sh[shstr][4]:sh[shstr][4]+sh[shstr][5]]
        self.sec={names[s[0]:].split(b'\0')[0].decode():s for s in sh}
    def fileoff(self,va,n=1):
        for base,off,size in self.loads:
            if base<=va and va+n<=base+size:return off+va-base
        raise ValueError(f'unmapped VA {va:#x}')
    def raw(self,va,n):
        o=self.fileoff(va,n);return self.b[o:o+n]
    def relocs(self,name):
        s=self.sec[name];return [struct.unpack_from('<QQq',self.b,s[4]+i) for i in range(0,s[5],24)]
    def sym_name(self,index):
        sy=self.sec['.dynsym'];st=self.sec['.dynstr'];ent=sy[9]
        name=struct.unpack_from('<I',self.b,sy[4]+index*ent)[0]
        return self.b[st[4]+name:].split(b'\0')[0].decode()
    def needed(self):
        dy=self.sec['.dynamic'];st=self.sec['.dynstr'];result=[]
        for i in range(0,dy[5],16):
            tag,val=struct.unpack_from('<QQ',self.b,dy[4]+i)
            if tag==1:result.append(self.b[st[4]+val:].split(b'\0')[0].decode())
        return result

def bl_target(e,va):
    w=struct.unpack('<I',e.raw(va,4))[0]
    assert w>>26==0b100101,hex(w)
    imm=w&0x3ffffff
    if imm&(1<<25):imm-=1<<26
    return va+4*imm

im=ELF(IM);db=ELF(DB)
for p,expected in EXPECTED.items():
    actual=hashlib.sha256(p.read_bytes()).hexdigest()
    assert actual==expected,(str(p),actual)
assert {'libIMDB.so','libdl.so.2'}<=set(im.needed())
raw_base=0x1cd38;entry_va=raw_base+0x100+143*0x48
assert entry_va==0x1f670
entry=db.raw(entry_va,0x48)
kind,order,mask,field12,flag=struct.unpack_from('<IIIHH',entry,0)
assert (kind,order,mask,field12,flag)==(0x20000004,1,0xffffff9f,0x83,0)
path_ptr,init_ptr=struct.unpack_from('<QQ',entry,0x10)
assert (path_ptr,init_ptr)==(0xb95c,0xb965)
assert db.raw(path_ptr,9)==b'appFw.so\0'
assert db.raw(init_ptr,24)==b'Application_System_Init\0'
rel_db={off:(info,addend) for off,info,addend in db.relocs('.rela.dyn')}
for off,add in ((entry_va+0x10,path_ptr),(entry_va+0x18,init_ptr)):
    assert rel_db[off]==(1027,add)

calls={0x406564:0x402470, # IMDB_get_entries@plt
       0x4065f0:0x406374, # entry activation
       0x40639c:0x402330, # IMDB_find_entry@plt
       0x4064a0:0x4061ec, # dispatch retrieved entry
       0x406284:0x405e24, # 0x20000004 handler
       0x405eac:0x402150, # dlopen@plt
       0x405f0c:0x402080} # dlsym@plt
for va,target in calls.items():assert bl_target(im,va)==target,(hex(va),hex(bl_target(im,va)))
rel_im={off:(info,addend) for off,info,addend in im.relocs('.rela.plt')}
symbols={}
for slot,name in ((0x4190f0,'dlopen'),(0x419088,'dlsym')):
    info,_=rel_im[slot];sym=info>>32;typ=info&0xffffffff
    assert typ==1026 and im.sym_name(sym)==name
    symbols[name]={'jump_slot_va':hex(slot),'relocation':'R_AARCH64_JUMP_SLOT','dynsym_index':sym}
assert im.raw(0x405e3c,4).hex()=='140840f9' # ldr x20,[x0,#0x10]
assert im.raw(0x405ea8,4).hex()=='80029f9a' # csel x0,x20,xzr,eq
assert im.raw(0x406278,4).hex()=='0300a472' # movk w3,#0x2000,lsl#16
vm_line=next((line for line in VM.read_text(errors='replace').splitlines()
              if 'FX3_PROVIDER_CALLER module=/usr/lib/appFw.so' in line),None)
assert vm_line
print(json.dumps({'schema':'fx3-im-appfw-static-edge-v1','originals':
      {p.name:{'path':str(p),'bytes':p.stat().st_size,'sha256':h} for p,h in EXPECTED.items()},
      'im_needed':sorted(set(im.needed())&{'libIMDB.so','libdl.so.2'}),
      'imdb':{'raw_symbol_va':hex(raw_base),'entry_index':143,'entry_va':hex(entry_va),
              'entry_file_offset':hex(db.fileoff(entry_va,0x48)),'entry_hex':entry.hex(),
              'kind':hex(kind),'target_mask':hex(mask),'path':db.raw(path_ptr,9).decode().rstrip('\0'),
              'init_symbol':db.raw(init_ptr,24).decode().rstrip('\0'),
              'relocations':[{'place_va':hex(entry_va+k),'target_va':hex(v),'type':'R_AARCH64_RELATIVE'}
                             for k,v in ((0x10,path_ptr),(0x18,init_ptr))]},
      'im_calls':[{'caller_va':hex(va),'file_offset':hex(im.fileoff(va,4)),
                   'instruction_le':im.raw(va,4).hex(),'target_va':hex(target)}
                  for va,target in calls.items()],
      'dynamic_relocations':symbols,
      'key_instruction':{'va':'0x405e3c','file_offset':hex(im.fileoff(0x405e3c,4)),
                         'bytes_le':im.raw(0x405e3c,4).hex(),'meaning':'x20 <- descriptor+0x10 (library name)'},
      'existing_vm_observation':{'path':str(VM),'line':vm_line,
                                 'limit':'VM log only; no live camera/cold-start identity'},
      'conclusion':'static original descriptor -> im loader dispatch -> dlopen@plt edge verified',
      'unknown':['exact cold-start selection on camera','live camera file and memory hashes',
                 'WBI image identity','application init success on real hardware']},ensure_ascii=False,indent=2))
