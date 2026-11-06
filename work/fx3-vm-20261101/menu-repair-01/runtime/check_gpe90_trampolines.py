from pathlib import Path
import json,hashlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM
from unicorn.arm64_const import *
R=Path(__file__).resolve().parent;v=json.loads((R/'ap90-rebuilt-proof.json').read_text());results=[]
for offset in [0x1031b0,0x103454,0x103550,0x10364c]:
 rows=next(b['instructions'] for b in v['obj_original'] if int(b['range'][0],16)<=offset<int(b['range'][1],16));prefix=b''.join(bytes.fromhex(i['bytes']) for i in rows if offset<=int(i['va'],16)<offset+16);assert len(prefix)==16
 base=0x1000000;target=base+offset;tr=0x4000000;stack=0x5000000
 def run(at,code):
  u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(target&~4095,4096);u.mem_write(target,prefix);u.mem_map(tr,4096);u.mem_write(tr,code);u.mem_map(stack,4096)
  for i in range(29):u.reg_write(UC_ARM64_REG_X0+i,0x1100+i*0x30)
  u.reg_write(UC_ARM64_REG_X29,0x1234567);u.reg_write(UC_ARM64_REG_X30,0x7654321);u.reg_write(UC_ARM64_REG_SP,stack+4096)
  u.emu_start(at,target+16,count=8)
  assert u.reg_read(UC_ARM64_REG_PC)==target+16
  return [u.reg_read(UC_ARM64_REG_X0+i) for i in range(29)]+[u.reg_read(UC_ARM64_REG_X29),u.reg_read(UC_ARM64_REG_X30),u.reg_read(UC_ARM64_REG_SP)],bytes(u.mem_read(stack,4096))
 direct,sd=run(target,prefix);code=prefix+struct.pack('<IIQ',0x58000050,0xd61f0200,target+16);via,sv=run(tr,code)
 for i in range(len(direct)):
  if i!=16:assert direct[i]==via[i],(hex(offset),i)
 assert sd==sv and via[16]==target+16
 results.append({'offset':hex(offset),'prefix':prefix.hex(),'same_GPR_except_ABI_scratch_X16':True,'same_stack':True,'branch_exact_original_plus16':True})
(R/'ap90-trampoline-host-check.json').write_text(json.dumps({'bounded_original_prefix_Unicorn':results,'native_full_body_executed':False},indent=2)+'\n');print('AP90 trampoline originalprefixes4 direct/relocated GPR/stack equal; X16 ABI scratch only')
