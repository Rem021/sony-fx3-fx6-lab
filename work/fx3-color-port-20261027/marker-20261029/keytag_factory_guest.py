#!/usr/bin/env python3
"""Original KeyTagFactory with original StringHandler, entirely in synthetic RAM."""
from pathlib import Path
import hashlib,json,struct,sys
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from inspect_body_policy import HERE,PATH,PIN,View

DATA=0x50000000
HEAP=0x51000000
STACK=0x60000000
STOP=0x70000000

class Guest:
    def __init__(self,views):
        self.views=views;self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.pages=set();self.plt={};self.definitions={};self.vtables={};self.steps=0;self.heap=HEAP;self.allocations=[];self.extra_permitted_names=[]
        for base,view in views:
            for symbol in view.symbols:
                if symbol['st_shndx']!='SHN_UNDEF' and symbol['st_value']:
                    self.definitions.setdefault(symbol.name,base+symbol['st_value'])
                    if symbol.name.startswith('_ZTV'):self.vtables[base+symbol['st_value']+16]=view.names[symbol.name]
            for seg in view.elf.iter_segments():
                if seg['p_type']!='PT_LOAD':continue
                lo=seg['p_vaddr']&-4096;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&-4096
                for page in range(base+lo,base+hi,4096):
                    if page not in self.pages:self.u.mem_map(page,4096);self.pages.add(page)
                self.u.mem_write(base+seg['p_vaddr'],seg.data())
            section=view.elf.get_section_by_name('.plt');rels=view.elf.get_section_by_name('.rela.plt')
            for i,r in enumerate(rels.iter_relocations()):self.plt[base+section['sh_addr']+32+16*i]=view.symbols[r['r_info_sym']].name
        for base,view in views:
            for rel in view.elf.get_section_by_name('.rela.dyn').iter_relocations():
                typ=rel['r_info_type'];symbol=view.symbols[rel['r_info_sym']]
                if typ==1027:value=base+rel['r_addend']
                elif typ in [257,1025] and symbol.name in self.definitions:value=self.definitions[symbol.name]+rel['r_addend']
                else:continue
                self.u.mem_write(base+rel['r_offset'],struct.pack('<Q',value))
        for address,size in [(DATA,0x10000),(HEAP,0x100000),(STACK,0x10000),(STOP,4096)]:self.u.mem_map(address,size)
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_guard)

    def invalid(self,u,access,a,size,value,user):raise AssertionError(('unmapped',hex(u.reg_read(R.UC_ARM64_REG_PC)),hex(a),size))
    def write_guard(self,u,access,a,size,value,user):assert any(lo<=a and a+size<=hi for lo,hi in [(DATA,DATA+0x10000),(HEAP,HEAP+0x100000),(STACK,STACK+0x10000)]),('outside synthetic RAM',hex(a),size)
    def ret(self,value=0):self.u.reg_write(R.UC_ARM64_REG_X0,value&0xffffffffffffffff);self.u.reg_write(R.UC_ARM64_REG_PC,self.u.reg_read(R.UC_ARM64_REG_X30))
    def allocate(self,count):
        assert 0<count<=0x10000;address=self.heap;self.heap+=(count+15)&-16;assert self.heap<=HEAP+0x100000;self.allocations.append((address,count));return address
    def string(self,address):
        out=bytearray()
        for i in range(2048):
            b=bytes(self.u.mem_read(address+i,1))
            if b==b'\0':return bytes(out)
            out+=b
        raise AssertionError('unterminated guest string')

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<50000
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if name in self.definitions:u.reg_write(R.UC_ARM64_REG_PC,self.definitions[name]);return
            if name in ['_Znwm','_Znam','malloc']:self.ret(self.allocate(x[0]));return
            if name in ['_ZdlPv','_ZdaPv','_ZdlPvm','_ZdaPvm','free']:self.ret();return
            if name=='strlen':self.ret(len(self.string(x[0])));return
            if name in ['memcpy','memmove']:
                assert x[2]<=0x10000;u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
            if name=='memset':assert x[2]<=0x10000;u.mem_write(x[0],bytes([x[1]&255])*x[2]);self.ret(x[0]);return
            if name=='memcmp':
                assert x[2]<=0x10000;a=bytes(u.mem_read(x[0],x[2]));b=bytes(u.mem_read(x[1],x[2]));self.ret(0 if a==b else -1 if a<b else 1);return
            if name in ['strcmp','strncmp']:
                a=self.string(x[0]);b=self.string(x[1])
                if name=='strncmp':a=a[:x[2]];b=b[:x[2]]
                self.ret(0 if a==b else -1 if a<b else 1);return
            raise AssertionError(('unmodelled import',name,hex(pc)))
        permitted=False
        for base,view in self.views:
            if base+0x1335c<=pc<base+0x1369c and view.path.name=='libupdaterbody.so':permitted=True
            for address,n in view.sizes.items():
                if base+address<=pc<base+address+n and any(t in view.labels.get(address,'') for t in ['StringHandler::','BaseKeyTag::BaseKeyTag']+self.extra_permitted_names):permitted=True;break
        assert permitted,('outside selected original factory/string functions',hex(pc))

    def run(self,entry,args):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        for i,value in enumerate(args):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),value)
        before=self.steps;u.emu_start(entry,STOP+4,count=50000)
        assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return u.reg_read(R.UC_ARM64_REG_X0),self.steps-before

def main():
    ap=HERE.parent/'ap-input-20261029';source=next(r for r in json.loads((ap/'additional-source-members.json').read_text()) if r['original_path']=='/lib/libupdatercommon.so')
    body=View(PATH,PIN);common=View(ap/source['output'],source['sha256']);bases=[(0x10000000,body),(0x20000000,common)];rows=[]
    ctor=next(s.name for s in common.symbols if s.name.startswith('_ZN7Updater13StringHandlerC1E'))
    setter=next(s.name for s in common.symbols if s.name=='_ZN7Updater13StringHandler9SetStringEPKc')
    for text in ['0100_config','0700_part_image','9999_program','9999_unknown','config','part_image','program','unknown']:
        g=Guest(bases);g.u.mem_write(DATA+0x1000,text.encode()+b'\0');g.run(g.definitions[ctor],[DATA]);g.run(g.definitions[setter],[DATA,DATA+0x1000]);pointer,instructions=g.run(0x1001335c,[0x9999,DATA])
        vptr=struct.unpack('<Q',g.u.mem_read(pointer,8))[0];assert vptr in g.vtables
        rows.append(dict(input_key=text,declared_index=0x9999,result_type=g.vtables[vptr],instructions=instructions,total_instructions=g.steps))
    assert next(r for r in rows if r['input_key']=='config')['result_type']=='vtable for Updater::ConfigKeyTag'
    assert next(r for r in rows if r['input_key']=='part_image')['result_type']=='vtable for Updater::PartitionImageKeyTag'
    result=dict(body_library_sha256=PIN,common_library_sha256=source['sha256'],cases=rows,
                scope='Original KeyTagFactory plus original StringHandler methods and BaseKeyTag construction run with resolved source ELF relocations in synthetic RAM. Host shims are memory allocation and bounded libc byte/string operations only. These are direct key-string inputs, not tar parsing, mode-6 file extraction, XML execution, process launch, normal external admission or a flash test.')
    (HERE/'keytag-factory-guest-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
