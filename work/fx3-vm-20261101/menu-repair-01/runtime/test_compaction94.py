from pathlib import Path
import json,hashlib
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
R=Path(__file__).resolve().parent;p=R/'helpers/fx3-gpe-observe-v19-child-stretch.so';out=[]
with p.open('rb') as f:
 e=ELFFile(f);sy={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()};segments=[(x['p_vaddr'],x['p_memsz'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD']
for n in range(7):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0,0x200000);u.mem_map(0x400000,0x20000)
 for a,size,data in segments:u.mem_write(a,data)
 stop=0x100000;u.mem_write(sy[f'fx3_compaction_tramp_{n}'],stop.to_bytes(8,'little'))
 gr=[UC_ARM64_REG_X0+i for i in range(29)]+[UC_ARM64_REG_X29,UC_ARM64_REG_X30]
 initial=[0x12340000+i*17 for i in range(31)]
 for r,v in zip(gr,initial):u.reg_write(r,v)
 for i in range(32):u.reg_write(UC_ARM64_REG_Q0+i,int.from_bytes(bytes([i+1])*16,'little'))
 u.reg_write(UC_ARM64_REG_SP,0x410000);u.reg_write(UC_ARM64_REG_NZCV,0xa0000000);u.reg_write(UC_ARM64_REG_FPCR,0x400000);u.reg_write(UC_ARM64_REG_FPSR,0x10)
 observed=[]
 def hook(u,a,size,_):
  if a==sy['fx3_compaction_event']:
   lr=u.reg_read(UC_ARM64_REG_LR);observed.append((u.reg_read(UC_ARM64_REG_X0),u.reg_read(UC_ARM64_REG_X1)))
   for r in gr:u.reg_write(r,0x77777777)
   for i in range(32):u.reg_write(UC_ARM64_REG_Q0+i,0)
   u.reg_write(UC_ARM64_REG_NZCV,0);u.reg_write(UC_ARM64_REG_FPCR,0);u.reg_write(UC_ARM64_REG_FPSR,0);u.reg_write(UC_ARM64_REG_PC,lr)
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(sy[f'fx3_compaction_probe_{n}'],stop,count=300)
 assert u.reg_read(UC_ARM64_REG_PC)==stop and len(observed)==1
 for i,r in enumerate(gr):assert u.reg_read(r)==(stop if i==16 else initial[i]),(n,i)
 for i in range(32):assert u.reg_read(UC_ARM64_REG_Q0+i)==int.from_bytes(bytes([i+1])*16,'little')
 for r,v in [(UC_ARM64_REG_SP,0x410000),(UC_ARM64_REG_NZCV,0xa0000000),(UC_ARM64_REG_FPCR,0x400000),(UC_ARM64_REG_FPSR,0x10)]:assert u.reg_read(r)==v
 out.append({'point':hex(observed[0][0]),'passed':True,'GPR_except_ABI_scratch_x16_preserved':True,'SIMD32_NZCV_FPCR_FPSR_SP_LR_preserved':True,'original_trampoline_tail_reached':True})
(R/'ap94-compaction-probe-host-check.json').write_text(json.dumps({'ELF_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'Unicorn_tests':out,'marker_body_stub_deliberately_clobbers_all_registers':True,'scope':'assembly preservation only; not compaction hardware/runtime acceptance'},indent=2)+'\n');print('PASS 7 compaction assembly probes fullregister preservation')
