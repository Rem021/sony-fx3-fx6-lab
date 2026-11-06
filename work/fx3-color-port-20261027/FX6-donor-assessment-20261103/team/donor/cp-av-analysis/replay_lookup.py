#!/usr/bin/env python3
"""Bounded CPU-only replay of original FX6 AV look-record lookup (no firmware boot)."""
import hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R

OUT=pathlib.Path(__file__).resolve().parent
AV=OUT.parent/'fat-files/nflasha3/av-cam.bin'
PIN='56684d830eab1e304868548746d8275188a925f9e4ab9354560180c31b4a93cf'
BASE=0xffffffc001000000
ENTRY=0x2a650c
END=0x2a659c
TABLE=0x36fdf8
STACK=0x50000000
OUTPUT=0x51000000
STOP=0x60000000

def main():
 b=AV.read_bytes();assert hashlib.sha256(b).hexdigest()==PIN
 assert struct.unpack_from('<Q',b)[0]-0x58==BASE
 code_sha=hashlib.sha256(b[ENTRY:END]).hexdigest()
 cases=[]
 for value in [-1,0,1,16,22,29,30]:
  u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
  u.mem_map(BASE,(len(b)+4095)&~4095)
  u.mem_write(BASE,b)
  for addr,size in [(STACK,0x10000),(OUTPUT,0x1000),(STOP,0x1000)]:u.mem_map(addr,size)
  u.mem_write(OUTPUT,b'\x5a'*64)
  u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000)
  u.reg_write(R.UC_ARM64_REG_LR,STOP)
  u.reg_write(R.UC_ARM64_REG_X0,value&0xffffffff)
  u.reg_write(R.UC_ARM64_REG_X1,OUTPUT+16)
  pcs=[];writes=[]
  def code(uc,pc,size,_):
   if pc==STOP:uc.emu_stop();return
   assert BASE+ENTRY<=pc<BASE+END,hex(pc)
   pcs.append(pc-BASE)
  def write(uc,access,addr,size,v,_):
   assert (OUTPUT+16<=addr and addr+size<=OUTPUT+48) or (STACK<=addr and addr+size<=STACK+0x10000),(hex(addr),size)
   writes.append([hex(addr),size])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(BASE+ENTRY,STOP+4,count=2000)
  assert u.reg_read(R.UC_ARM64_REG_PC)==STOP
  raw=bytes(u.mem_read(OUTPUT,64));assert raw[:16]==raw[48:]==b'\x5a'*16
  assert u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
  ret=u.reg_read(R.UC_ARM64_REG_X0)
  expected=b[TABLE+(value-1)*32:TABLE+value*32] if 1<=value<=29 else b'\x5a'*32
  assert raw[16:48]==expected
  assert ret==(1 if 1<=value<=29 else 0)
  case={'input':value,'returned':ret,'instructions':len(pcs),'output_sha256':hashlib.sha256(raw[16:48]).hexdigest(),
        'matches_original_table_record':1<=value<=29,'write_count':len(writes),'pc_range':[hex(min(pcs)),hex(max(pcs))]}
  if ret:
   idx,ptr,count,name=struct.unpack('<4Q',expected);no=name-BASE
   case.update(index=idx,descriptor_array_offset=hex(ptr-BASE),descriptor_count=count,
               name=b[no:b.index(0,no)].decode())
  cases.append(case)
 result={'source_sha256':PIN,'entry_offset':hex(ENTRY),'entry_va':hex(BASE+ENTRY),
         'function_original_bytes_sha256':code_sha,'scope':'isolated ARM64 CPU function, original FX6 bytes, bounded PC and memory writes; no VM/OS/ISP/DMA/camera',
         'cases':cases,'result':'PASS'}
 (OUT/'cpu-replay.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'result':'PASS','cases':len(cases),'entry_offset':hex(ENTRY),'code_sha256':code_sha}))
if __name__=='__main__':main()
