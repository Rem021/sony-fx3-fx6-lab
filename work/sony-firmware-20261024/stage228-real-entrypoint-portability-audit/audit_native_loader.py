"""Static bytes only. Pin ordinary thread/IMDB loading edges, never call Sony."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage183-request-consumer-and-early-entry/evidence/usb-main-dependency'
IM=B/'stage218-fixed-shell-process-filter/originals/im.elf'
raw=IM.read_bytes();assert len(raw)==40920 and sha256(raw).hexdigest()=='5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91'
e=ELFFile(io.BytesIO(raw));md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(va,n):
 for s in e.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n]
 raise ValueError((va,n))
def word(va):return struct.unpack('<I',read(va,4))[0]
def branch(pc):
 w=word(pc);assert w&0x7c000000==0x14000000;imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return pc+imm*4
def address(adrp,add,reg):
 w=word(adrp);assert w&0x9f00001f==0x90000000|reg;imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
 if imm&(1<<20):imm-=1<<21
 page=(adrp&~4095)+(imm<<12);w=word(add);assert w&0xffc003ff==0x91000000|(reg<<5)|reg
 return page+((w>>10)&4095)
checks=[]
for pc,target in [(0x403bc0,0x402010),(0x403be4,0x403b90),(0x403c00,0x403b90),(0x403c1c,0x403b90),(0x403c38,0x403b90),(0x403028,0x4064fc),(0x403074,0x4064fc),(0x403100,0x4064fc),(0x40314c,0x4064fc),(0x4065f0,0x406374),(0x4064a0,0x4061ec),(0x40626c,0x405f5c),(0x406284,0x405e24)]:
 assert branch(pc)==target;ins=list(md.disasm(read(pc,4),pc));assert len(ins)==1 and ins[0].mnemonic in ('b','bl') and int(ins[0].op_str[1:],16)==target
 checks.append(dict(pc=hex(pc),raw=read(pc,4).hex(),target=hex(target),instruction=ins[0].mnemonic+' '+ins[0].op_str))
assert address(0x403bd0,0x403bd8,1)==0x4030a8
for a,z in [(0x403bec,0x403bf4),(0x403c08,0x403c10),(0x403c24,0x403c2c)]:assert address(a,z,1)==0x402f94
dyn=e.get_section_by_name('.dynsym');base=e.get_section_by_name('.plt')['sh_addr'];plt={base+32+i*16:dyn.get_symbol(x['r_info_sym']).name for i,x in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())};assert plt[0x402010]=='osal_create_waitable_thread'
slices=[]
for a,z,meaning in [(0x403b90,0x403c3c,'thread attributes carry callbacks4030a8/402f94 into osal_create_waitable_thread'),(0x402f94,0x4030a8,'infra callback enters IMDB initializer dispatcher'),(0x4030a8,0x403180,'app callback enters IMDB initializer dispatcher'),(0x4064fc,0x40661c,'IMDB_get_entries; indexed72B rows; conditional dispatch to406374'),(0x406464,0x4064a4,'selected fresh row path enters4061ec'),(0x40625c,0x40628c,'typed loader selection')]:
 data=read(a,z-a);instructions=list(md.disasm(data,a));assert len(instructions)*4==len(data)
 slices.append(dict(VA=hex(a),end=hex(z),sha256=sha256(data).hexdigest(),raw=data.hex(),meaning=meaning,instructions=[dict(pc=hex(i.address),asm=i.mnemonic+' '+i.op_str) for i in instructions]))
lib=P/'originals/lib/libIMDB.so';lraw=lib.read_bytes();le=ELFFile(io.BytesIO(lraw))
def lread(va,n):
 for s in le.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   at=s['p_offset']+va-s['p_vaddr'];return lraw[at:at+n]
 raise ValueError((va,n))
rows=json.loads((P/'imdb-table-raw.json').read_text());types=Counter();named=[]
for row in rows:
 data=lread(int(row['va'],16),72);assert data.hex()==row['raw'];types[hex(struct.unpack_from('<I',data)[0])]+=1
 for p in row['pointers']:
  if p.get('text') and ('fx3_bootstrap' in p['text'] or '/tmp_wbshd' in p['text']):named.append(p['text'])
assert not named
report=dict(schema='fx3-stage228-native-loader-reachability-static-v1',im=dict(path=str(IM.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()),IMDB=dict(path=str(lib.relative_to(R)),bytes=len(lraw),sha256=sha256(lraw).hexdigest(),saved_rows_rebound=len(rows),type_counts=dict(types)),manual_instruction_checks=checks,source_slices=slices,ordinary_app_callback='0x4030a8',ordinary_infra_callback='0x402f94',callbacks_registered_as_waitable_threads=True,bootstrap227_requires_main_thread=True,ordinary_app_infra_path_proves_main_thread_eligibility=False,inspected_saved_rows_have_candidate_path_or_exports=False,
 conclusion='The ordinary observed app/infra initialization routes are registered as waitable thread callbacks and consume existing IMDB rows. They do not establish main-thread execution or registration of the227step/status exports. A zero-argument ABI bridge alone is insufficient; do not relax the main-thread guard or modify IMDB/preload to claim reachability.',
 limits=['Static conditional paths only, not execution traces; thread creation success and actual TIDs unobserved.','This is not an exhaustive proof that no other main-thread, indirect, service or alternate loader exists.','No authenticated request controls these descriptors or repeatedly schedules own step in evidence.','No actual source backup, update acceptance or independent recovery established.'],original_Sony_or_Linux_executed=False,new_camera_operations=0,first_flash_released=False)
(H/'native-loader-audit.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='ORDINARY_THREAD_LOAD_ROUTE_DOES_NOT_SATISFY_CURRENT_BOOTSTRAP',manual_checks=len(checks),slices=len(slices),saved_IMDB_rows=len(rows),new_camera_operations=0)))
