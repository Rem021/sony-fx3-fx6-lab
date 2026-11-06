"""Offline AArch64 instruction work estimate; Unicorn is NOT QEMU/TCG timing."""
from pathlib import Path
import json,struct,collections
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_BLOCK
from unicorn.arm64_const import UC_ARM64_REG_SP,UC_ARM64_REG_LR,UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_PC
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
ROOT=Path(__file__).resolve().parent
PARAM=0x4000000;DEST=0x5000000;SRC=0x6000000;STACK=0x9000000;STOP=0x100000
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def execute(version,op,raw):
 uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
 with (ROOT/f'build/probe-v{version}.elf').open('rb') as f:
  elf=ELFFile(f);pages=set()
  for seg in elf.iter_segments():
   if seg['p_type']!='PT_LOAD':continue
   base=seg['p_vaddr'];start=base&~4095;end=(base+seg['p_memsz']+4095)&~4095
   for page in range(start,end,4096):
    if page not in pages:uc.mem_map(page,4096);pages.add(page)
   uc.mem_write(base,seg.data())
  entry=next(s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name=='probe')
 uc.mem_map(PARAM,4096);uc.mem_map(DEST,2*1024*1024);uc.mem_map(SRC,16*1024*1024);uc.mem_map(STACK,2*1024*1024);uc.mem_map(STOP,4096)
 uc.mem_write(PARAM,raw);texture=(ROOT/'build/textures.bin').read_bytes();uc.mem_write(SRC,texture)
 # Nonzero destination; all initialized bytes identical for v8/v9.
 uc.mem_write(DEST,bytes((i*37+97)&255 for i in range(640*480*4)))
 uc.reg_write(UC_ARM64_REG_SP,STACK+2*1024*1024-16);uc.reg_write(UC_ARM64_REG_LR,STOP)
 for reg,val in [(UC_ARM64_REG_X0,op),(UC_ARM64_REG_X1,PARAM),(UC_ARM64_REG_X2,DEST),(UC_ARM64_REG_X3,SRC)]:uc.reg_write(reg,val)
 counts=collections.Counter();blocks={}
 def hook(machine,addr,size,user):
  key=(addr,size)
  if key not in blocks:
   c=collections.Counter()
   for i in md.disasm(machine.mem_read(addr,size),addr):
    m=i.mnemonic;c['instructions']+=1
    if m in ('udiv','sdiv'):c['divide']+=1
    elif m.startswith(('ld','st')):c['load_store']+=1
    # Weight Advanced SIMD work conservatively; category approximate.
    elif any(x in i.op_str for x in ('v0.','v1.','v2.','v3.','v4.','v5.','v6.','v7.')):c['simd']+=1
   blocks[key]=c
  counts.update(blocks[key])
 uc.hook_add(UC_HOOK_BLOCK,hook)
 uc.emu_start(entry,STOP,count=15000000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP
 assert uc.reg_read(UC_ARM64_REG_X0)==0
 result=bytes(uc.mem_read(DEST,640*480*4))
 # Sensitivity band: uniform instructions vs division/NEON/load-store weights.
 counts['weighted_work']=counts['instructions']+7*counts['divide']+counts['load_store']+3*counts['simd']
 return dict(counts),result

def main():
 records=json.loads((ROOT/'build/vectors.json').read_text())[-10:];rows=[]
 for row in records:
  b=bytearray.fromhex(row['raw']);op=row['op']
  if not op:
   struct.pack_into('<2I',b,16,64,4)
  else:
   tile=b[116];stretch=row['name'].startswith('nearest')
   for off,val in [(16,64),(20,4),(32,64),(36,4),(48,64),(72,16 if tile else 32 if stretch else 64),(76,16 if tile else 2 if stretch else 4),(88,64)]:struct.pack_into('<I',b,off,val)
  a,da=execute(8,op,bytes(b));z,dz=execute(9,op,bytes(b));assert da==dz
  rows.append({'class':row['name'],'geometry':'64x4 target; source scaled analogously; tile16x16','v8':a,'v9':z,'instruction_ratio':a['instructions']/z['instructions'],'weighted_work_ratio':a['weighted_work']/z['weighted_work'],'byte_exact':True})
 report={'method':'Unicorn offline dynamic AArch64 -O2 instruction count, not QEMU execution or elapsed time','libc_model':'freestanding auto-vectorized C memcpy/memset; guest glibc and MMU/TLB/syscall/scheduling costs not modeled','weights':{'scalar':1,'divide':8,'load_store':2,'simd':4},'tcg_speedup_claim':'work estimate only; not a verified TCG speedup nor proof of 5000ms completion','rows':rows}
 (ROOT/'build/tcg-estimate.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps([{'class':r['class'],'instruction_ratio':round(r['instruction_ratio'],2),'weighted_ratio':round(r['weighted_work_ratio'],2)} for r in rows]))
if __name__=='__main__':main()
