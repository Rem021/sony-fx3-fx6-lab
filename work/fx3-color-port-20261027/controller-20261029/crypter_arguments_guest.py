#!/usr/bin/env python3
"""Original crypter main argument parsing, stopping at virtual Initialize."""
import hashlib,json,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources
sys.path.insert(0,str(HERE.parent/'marker-20261029'))
from keytag_factory_guest import Guest as LoaderGuest,DATA,STACK,STOP,R

ARGV=DATA+0x1000
STRINGS=DATA+0x2000
MANAGER=DATA+0x3000
VTABLE=DATA+0x3100
INITIALIZE=STOP+0x300

class Guest(LoaderGuest):
    def __init__(self,view,argv):
        super().__init__([(0,view)])
        self.view=view;self.argv=argv;self.boundary=None;self.events=[];self.global_writes=[]
        section=view.elf.get_section_by_name('.bss');self.bss=(section['sh_addr'],section['sh_size'])
        assert self.bss==(0x412088,1056)
        assert bytes(self.u.mem_read(0x412094,4))==b'\0'*4
        self.u.mem_write(0x412088,struct.pack('<Q',DATA+0x1f00)) # synthetic stderr COPY relocation fixture
        self.u.mem_write(MANAGER,struct.pack('<Q',VTABLE));self.u.mem_write(VTABLE+0x10,struct.pack('<Q',INITIALIZE))
        addresses=[];cursor=STRINGS
        for arg in argv:
            raw=arg.encode()+b'\0';assert len(raw)<512
            self.u.mem_write(cursor,raw);addresses.append(cursor);cursor+=len(raw)
        self.u.mem_write(ARGV,b''.join(struct.pack('<Q',p) for p in addresses+[0]))
        self.initializer_rows=[]

    def write_guard(self,u,access,address,size,value,user):
        lo,n=self.bss
        if lo<=address and address+size<=lo+n:
            self.global_writes.append(dict(address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        return super().write_guard(u,access,address,size,value,user)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<10000
        if pc==STOP:u.emu_stop();return
        x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(5)]
        if pc==INITIALIZE:
            assert x[0]==MANAGER
            self.boundary=dict(operation='virtual_initialize_request',file_chunk=x[1],filename=self.string(0x4120a8).decode(),pc=hex(pc),manager_initialization_executed=False)
            u.emu_stop();return
        if pc in self.plt:
            name=self.plt[pc]
            if name=='strncmp':
                assert x[2]<=16;a=self.string(x[0])[:x[2]];b=self.string(x[1])[:x[2]];self.ret(0 if a==b else -1 if a<b else 1);return
            if name=='mcmn_init':self.events.append(dict(adapter='mcmn_init no-op fixture'));self.ret(0);return
            if name=='snprintf':
                fmt=self.string(x[2]);assert fmt==b'%s' and x[1]==1024 and x[0]==0x4120a8
                value=self.string(x[3]);assert len(value)<x[1]
                u.mem_write(x[0],value+b'\0');self.events.append(dict(adapter='bounded snprintf %s',text=value.decode(),bytes=len(value)));self.ret(len(value));return
            if name=='GetCryptFileInputModeUpdater':self.events.append(dict(adapter='synthetic manager/vtable fixture'));self.ret(MANAGER);return
            if name=='fputs':
                assert x[1]==DATA+0x1f00;self.events.append(dict(adapter='discarded stderr text',text=self.string(x[0]).decode()));self.ret(0);return
            raise AssertionError(('unmodelled main import',name,hex(pc)))
        allowed=[(0x400bc0,0x400f20),(0x400a98,0x400aac),(0x400f68,0x400f7c),(0x400fb8,0x400ff8),(0x401028,0x401060)]
        assert any(lo<=pc<hi for lo,hi in allowed),('outside original main/declared executable initializers',hex(pc))

    def execute(self):
        init=next(t['d_val'] for t in self.view.elf.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag=='DT_INIT')
        array=self.view.elf.get_section_by_name('.init_array').data();assert len(array)==8
        init_array=struct.unpack('<Q',array)[0];assert [init,init_array]==[0x400a98,0x401028]
        assert bytes(self.u.mem_read(0x411fe0,8))==b'\0'*8 and self.view.read(0x411ce0,8)==b'\0'*8
        for address in [init,init_array]:
            _,steps=self.run(address,[])
            current=struct.unpack('<I',self.u.mem_read(0x412094,4))[0];assert current==0
            self.initializer_rows.append(dict(entry=hex(address),instructions=steps,file_chunk_after=current))
        self.u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);self.u.reg_write(R.UC_ARM64_REG_X30,STOP)
        self.u.reg_write(R.UC_ARM64_REG_X0,len(self.argv));self.u.reg_write(R.UC_ARM64_REG_X1,ARGV)
        self.u.emu_start(0x400bc0,STOP+4,count=10000)
        if self.boundary:assert self.u.reg_read(R.UC_ARM64_REG_PC)==INITIALIZE
        else:assert self.u.reg_read(R.UC_ARM64_REG_PC)==STOP and self.u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        return dict(argv=self.argv,boundary=self.boundary,return_value_if_returned=self.u.reg_read(R.UC_ARM64_REG_X0) if not self.boundary else None,
                    executable_initializers=self.initializer_rows,original_bss_writes=self.global_writes,host_adapters=self.events,instructions=self.steps,bss_file_chunk_before=0,bss_file_chunk_after=struct.unpack('<I',self.u.mem_read(0x412094,4))[0])

def main():
    source=next(r for r in sources() if Path(r['path']).name=='crypter.elf');v=View(source['path'],source['sha256'])
    original_ufp=next(r for r in sources() if Path(r['path']).name=='libupdaterufp.so');ufp=View(original_ufp['path'],original_ufp['sha256'])
    table=ufp.read(0x151b8,24);pointers=struct.unpack('<QQQ',table);assert pointers[2]==0
    ufp_argv=[ufp.read(pointer,128).split(b'\0',1)[0].decode() for pointer in pointers[:2]]
    assert ufp_argv==['/usr/bin/crypter.elf','/tmp_updater/Firm.dat']
    cases=[('ufp_exact_arguments',ufp_argv,0),
           ('explicit_full',['/usr/bin/crypter.elf','chunk=full','/tmp_updater/Firm.dat'],1),
           ('explicit_fdat',['/usr/bin/crypter.elf','chunk=fdat','/tmp_updater/Firm.dat'],0),
           ('no_filename',['/usr/bin/crypter.elf'],None)]
    rows=[]
    for label,case_argv,expected in cases:
        row=Guest(v,case_argv).execute();row['case']=label
        if expected is None:assert row['boundary'] is None and row['return_value_if_returned']==1
        else:assert row['boundary']['file_chunk']==expected and row['boundary']['filename']=='/tmp_updater/Firm.dat'
        rows.append(row)
    result=dict(source=source['path'],source_sha256=source['sha256'],original_ufp_argv_table=dict(source=original_ufp['path'],source_sha256=original_ufp['sha256'],va='0x151b8',bytes=24,sha256=hashlib.sha256(table).hexdigest(),pointers=[hex(p) for p in pointers],argv=ufp_argv),cases=rows,
                scope='Original crypter executable DT_INIT and its single init-array function execute with declared zero weak gmon/JCR bindings; both leave FILE_CHUNK zero. Original main then parses declared argv using ELF PT_LOAD segments and zero-initialized BSS in Unicorn. Exact bounded original BSS writes are permitted and logged; stderr COPY binding is synthetic. mcmn_init is a no-op, snprintf/strncmp and logging are bounded host adapters; the manager factory returns a synthetic object/vtable so execution stops at virtual Initialize before original manager initialization or file access. No full dynamic-loader/dependency startup, actual process, live process globals, complete decryption/CRC/admission, input file, native target library, USB or camera is proven. The normal UFP argument vector is the previously pinned parameter-table value, not an observed real camera invocation.')
    (HERE/'crypter-arguments-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ufp_fixture_file_chunk=0,explicit_full=1,no_filename_rejected=True,camera_actions=0)))

if __name__=='__main__':main()
