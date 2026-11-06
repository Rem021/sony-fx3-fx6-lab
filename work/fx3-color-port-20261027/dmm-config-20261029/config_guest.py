#!/usr/bin/env python3
"""Original DMM configuration parser over explicit original-file read adapter.

No boot parameter producer, physical mapping, image allocation, reply or kernel
result is supplied. This proves parsing of candidate file bytes, not runtime use.
"""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
sys.path.insert(0,str(TASK/'route-20261028'))
from cp_look_route import image,BASE,PIN
STACK=0x50000000;STOP=0x60000000;DATA=0x51000000
THUMB=[(0xab8b70,0xab8e9a),(0xaba7b6,0xaba842),(0xab60ae,0xab60c0),
       (0xab9830,0xab988e),(0xaba836,0xaba842)]
ARM=[(0x558400,0x558ae4),(0x558af4,0x558c30)]

def words(u,at,n):return list(struct.unpack('<'+'I'*n,u.mem_read(at,n*4)))

class Guest:
    def __init__(self,raw,source):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.source=source;self.offset=0;self.reads=[];self.entries=[];self.boundary=None
        self.instructions=0;self.writes=0;u=self.u
        u.mem_map(BASE,(len(raw)+0xfff)&~0xfff);u.mem_write(BASE,raw)
        for at,n in [(STACK,0x10000),(DATA,0x1000),(STOP,0x1000),(0x13f8000,0x2000),
                     (0x147e000,0x1000),(0x1199000,0x1000),(0x1da7000,0x230000)]:u.mem_map(at,n)
        u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
    def ret(self,value):
        self.u.reg_write(R.UC_ARM_REG_R0,value);self.u.reg_write(R.UC_ARM_REG_PC,self.u.reg_read(R.UC_ARM_REG_LR))
    def write(self,u,access,at,size,value,user):
        assert (STACK<=at and at+size<=STACK+0x10000 or DATA<=at and at+size<=DATA+0x1000 or
                0x13f8000<=at and at+size<=0x13fa000 or 0x147e000<=at and at+size<=0x147f000 or
                0x1199000<=at and at+size<=0x119a000 or 0x1da7000<=at and at+size<=0x1fd7000),(hex(u.reg_read(R.UC_ARM_REG_PC)),hex(at))
        self.writes+=1
    def code(self,u,pc,size,user):
        if pc==STOP:u.emu_stop();return
        if pc==0x4d7a84:
            p=u.reg_read(R.UC_ARM_REG_R0);n=u.reg_read(R.UC_ARM_REG_R1)
            assert n<=0x1000 and self.offset+n<=len(self.source),(hex(self.offset),n,len(self.source))
            b=self.source[self.offset:self.offset+n]
            self.reads.append(dict(original_call_lr=hex(u.reg_read(R.UC_ARM_REG_LR)),file_offset=hex(self.offset),
                                   destination=hex(p),bytes=n,sha256=hashlib.sha256(b).hexdigest(),adapter=True))
            u.mem_write(p,b);self.offset+=n;self.ret(0);return
        if pc in [0xab8a14,0xab8a5e,0xab9a5c]:
            self.boundary=dict(pc=hex(pc),registers=[hex(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))) for i in range(4)],
                               slot_or_image_allocation_executed=False,provider_reply_supplied=False)
            u.emu_stop();return
        assert any(a<=pc<z for a,z in THUMB+ARM),hex(pc)
        if pc in [0xab8b70,0xaba7b6,0xab9830,0xaba836]:self.entries.append(dict(pc=hex(pc),file_offset=hex(self.offset)))
        self.instructions+=1
    def call(self,va,args=()):
        u=self.u;self.boundary=None
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),args[i] if i<len(args) else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start(va|1,STOP+4,count=700000)
        if not self.boundary:
            assert u.reg_read(R.UC_ARM_REG_PC)==STOP,hex(u.reg_read(R.UC_ARM_REG_PC))
            assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        return dict(returned=self.boundary is None,raw_r0=hex(u.reg_read(R.UC_ARM_REG_R0)),boundary=self.boundary,file_offset=hex(self.offset))
    def unit_table(self):
        u=self.u;p=words(u,0x13f8ff4,1)[0];rows=[]
        for i in range(1025):
            key,ptr=words(u,p+i*8,2)
            if key==0xffffffff:
                assert ptr==0;return rows
            ids=[]
            for j in range(3074):
                v=words(u,ptr+j*4,1)[0]
                if v==0xffffffff:break
                ids.append(hex(v))
            else:raise AssertionError('extent ID list unbounded')
            rows.append(dict(key=hex(key),record=hex(p+i*8),list_pointer=hex(ptr),extent_IDs=ids))
        raise AssertionError('unit key table unbounded')

def main():
    target=HERE/'config-guest-results.json';assert not target.exists()
    f=HERE/'original-files/DmmCfg.bin';b=f.read_bytes();assert hashlib.sha256(b).hexdigest()=='820dc02b6a001636b93fff51d90baaced1ba75cf9bbaa90600dfc7fd7a705166'
    g=Guest(image(),b);common=g.call(0xab8b70);assert common['returned'] and common['raw_r0']=='0x0'
    units=g.call(0xaba7b6);assert units['returned'] and units['raw_r0']=='0x0'
    table=g.unit_table();selected=[r for r in table if r['key']=='0x4af'];assert len(selected)==1
    slot=g.call(0xab9830,[0x4af,1,DATA]);assert slot['boundary']['pc']=='0xab9a5c'
    g.u.mem_write(DATA,b'\xa7'*4);missing=g.call(0xab9830,[0xfffffffe,1,DATA])
    assert missing['returned'] and missing['raw_r0']=='0xfffffffd' and words(g.u,DATA,1)==[0xffffffff]
    out=dict(cp_sha256=PIN,original_file_sha256=hashlib.sha256(b).hexdigest(),original_file_bytes=len(b),
             common_configuration_parser=common,unit_list_parser=units,selected_unit=selected[0],all_units=table,
             selected_unit_lookup=slot,missing_unit_lookup=missing,file_reads=g.reads,entries=g.entries,
             instructions=g.instructions,original_writes=g.writes,parsed_bytes=g.offset,trailing_bytes=len(b)-g.offset,
             scope='Original CP common configuration and unit-list parsers execute over an explicit sequential original-file adapter. It replaces GetConfigData reads only and is not proof of boot filename/parameter binding. No context/kernel adapters, physical mapping, image allocation, provider reply, real buffer or MAIN pixels. Key0x4af lookup stops before original slot allocation.')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(common=common,units=units,unit_count=len(table),selected_unit=selected[0],parsed_bytes=g.offset,trailing_bytes=len(b)-g.offset)))

if __name__=='__main__':main()
