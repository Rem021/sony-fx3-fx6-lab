#!/usr/bin/env python3
"""Original app wrapper -> original RPC marshaller -> original UFP receiver.

Everything executes in synthetic Unicorn RAM. OSAL registration, allocation,
logging, preparation, backup, process launch and power operations are explicit
host fixtures; no Sony native program, system command or device is run.
"""
from pathlib import Path
import hashlib,json,struct,sys
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC
from unicorn import arm64_const as R
from inspect_app_crypto_calls import PATH,PIN,HERE
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources

UFP=0x20000000
DATA=0x60000000
STACK=0x70000000
STOP=0x78000000
BRIDGE=STOP+4

class Guest:
    def __init__(self,app,ufp,fixture):
        self.app=app;self.ufp=ufp;self.fixture=fixture;self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.pages=set();self.events=[];self.steps=0;self.bridge_return=None
        self.allowed=[(0x2eae880,0x2eaeaf0),(0x2eacf18,0x2ead070),(0x2eadbb0,0x2eadcf4),(0x2eadaec,0x2eadbb0),(UFP+0x3034,UFP+0x3174)]
        self.hooks={a:n for a,n in app.plt.items() if n in ['osal_valloc_msg_wait','osal_set_msg_src','osal_snd_sync_msg','osal_free_msg','memcpy']}
        self.hooks.update({a:'log' for a in [0x2f6ff0c,0x2f6fe3c,0x2f6be48]})
        for start,end in self.allowed[:4]:self.map_source(app,start,end-start)
        for a in self.hooks:self.map_source(app,a,4)
        # Original nine-byte status jump table, referenced at app PC 0x2eaea04.
        # This is file-backed source, not guessed RAM or an omitted WBI page.
        self.map_source(app,0x399f5ec,9)
        self.u.mem_protect(0x399f000,4096,UC_PROT_READ)
        for seg in ufp.elf.iter_segments():
            if seg['p_type']!='PT_LOAD':continue
            lo=seg['p_vaddr']&-4096;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&-4096
            for page in range(lo,hi,4096):self.map_page(UFP+page)
            self.u.mem_write(UFP+seg['p_vaddr'],seg.data())
        for r in ufp.elf.get_section_by_name('.rela.dyn').iter_relocations():
            typ=r['r_info_type'];s=ufp.symbols[r['r_info_sym']]
            if typ==1027:value=UFP+r['r_addend']
            elif typ in [257,1025] and s['st_shndx']!='SHN_UNDEF':value=UFP+s['st_value']+r['r_addend']
            else:continue
            self.u.mem_write(UFP+r['r_offset'],struct.pack('<Q',value))
        self.hooks.update({UFP+a:n for a,n in ufp.plt.items()})
        self.hooks.update({UFP+a:n for a,n in [(0x2728,'prepare_body'),(0x2f48,'prepare_lens'),(0x22e0,'legacy_extract'),(0x1f64,'post_1f64'),(0x1ffc,'post_1ffc'),(0x2094,'post_2094')]})
        for address,size in [(DATA,0x10000),(STACK,0x10000),(STOP,4096),(0x9ab0000,4096)]:
            for page in range(address,address+size,4096):self.map_page(page)
        self.write32(0x9ab0bc8,0x1234) # Declared wrapper unit identity, not device state.
        self.write32(UFP+0x252b8,fixture.get('version_skip',0))
        self.write32(UFP+0x151f4,0)
        self.u.hook_add(UC_HOOK_CODE,self.code)
        self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_guard)

    def map_page(self,page):
        assert page%4096==0
        if page not in self.pages:self.u.mem_map(page,4096);self.pages.add(page)

    def map_source(self,view,va,n):
        for page in range(va&-4096,(va+n+4095)&-4096,4096):
            if page in self.pages:continue
            self.map_page(page);self.u.mem_write(page,view.read(page,4096))

    def write32(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
    def qword(self,a):return struct.unpack('<Q',self.u.mem_read(a,8))[0]
    def ret(self,v=0):self.u.reg_write(R.UC_ARM64_REG_X0,v&0xffffffffffffffff);self.u.reg_write(R.UC_ARM64_REG_PC,self.u.reg_read(R.UC_ARM64_REG_X30))
    def invalid(self,u,access,a,size,value,user):raise AssertionError(('unmapped',hex(u.reg_read(R.UC_ARM64_REG_PC)),hex(a),size))
    def write_guard(self,u,access,a,size,value,user):
        assert any(lo<=a and a+size<=hi for lo,hi in [(DATA,DATA+0x10000),(STACK,STACK+0x10000),(0x9ab0000,0x9ab1000),(UFP+0x14000,UFP+0x26000)]),('write outside declared RAM',hex(a),size)
    def string(self,a):
        b=bytearray()
        for i in range(256):
            x=bytes(self.u.mem_read(a+i,1))
            if x==b'\0':return b.decode()
            b+=x
        raise AssertionError('unbounded string')

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<10000
        if pc==STOP:u.emu_stop();return
        if pc==BRIDGE:
            assert self.bridge_return is not None
            u.reg_write(R.UC_ARM64_REG_PC,self.bridge_return);u.reg_write(R.UC_ARM64_REG_X0,0);self.bridge_return=None;return
        if pc in self.hooks:
            name=self.hooks[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(5)]
            if name=='log':self.ret();return
            if name=='osal_valloc_msg_wait':
                assert x[2] in [8,16]
                u.mem_write(x[1],struct.pack('<Q',DATA+0x4000));u.mem_write(DATA+0x4000,bytes(64));self.ret();return
            if name=='osal_set_msg_src':self.events.append(dict(operation='declared_source_id',value=hex(x[1])));self.ret();return
            if name=='memcpy':
                assert x[2]<=64 and any(lo<=x[0] and x[0]+x[2]<=hi for lo,hi in [(DATA,DATA+0x10000),(STACK,STACK+0x10000)])
                u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
            if name=='osal_snd_sync_msg':
                if x[0]==0x0094016a:
                    words=list(struct.unpack('<4I',u.mem_read(x[1],16)));self.events.append(dict(operation='mock_registration',request_words=words))
                    self.write32(x[1]+4,0);self.ret();return
                assert x[0]==0x004b0233 and self.bridge_return is None
                command=struct.unpack('<I',u.mem_read(x[1],4))[0]
                self.events.append(dict(operation='original_ufp_dispatch',service=hex(x[0]),command=command))
                self.bridge_return=u.reg_read(R.UC_ARM64_REG_X30)
                u.reg_write(R.UC_ARM64_REG_X0,x[1]);u.reg_write(R.UC_ARM64_REG_X30,BRIDGE);u.reg_write(R.UC_ARM64_REG_PC,UFP+0x3034);return
            if name=='osal_free_msg':self.ret();return
            if name in ['prepare_body','prepare_lens','legacy_extract']:
                result=self.fixture.get(name,0);self.events.append(dict(operation=name,declared_result=result));self.ret(result);return
            if name=='Backup_write':
                result=self.fixture.get('backup_write',1);self.events.append(dict(operation=name,declared_result=result));self.ret(result);return
            if name=='Backup_sync_subsystem':self.events.append(dict(operation=name));self.ret();return
            if name=='stm_system':
                argv=[self.qword(x[1]+i*8) for i in range(x[2])]
                args=[self.string(a) if a else None for a in argv]
                self.events.append(dict(operation='process_launch_record_only',program=self.string(x[0]),argv=args,declared_result=self.fixture.get('stm_system',0)))
                self.ret(self.fixture.get('stm_system',0));return
            if name.startswith('post_'):self.events.append(dict(operation=name));self.ret();return
            raise AssertionError(('unmodeled boundary',name,hex(pc)))
        assert any(a<=pc<b for a,b in self.allowed),('code outside declared spans',hex(pc))

    def run(self,mode):
        u=self.u;self.write32(DATA,mode);self.write32(DATA+0x100,0xcccccccc)
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X0,DATA);u.reg_write(R.UC_ARM64_REG_X1,DATA+0x100);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        u.emu_start(0x2eae880,STOP+8,count=10000)
        assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        result=struct.unpack('<I',u.mem_read(DATA+0x100,4))[0]
        return dict(mode=mode,fixture=self.fixture,typed_result=result,events=self.events,instructions=self.steps)


def main():
    app=View(PATH,PIN);source=next(s for s in sources() if Path(s['path']).name=='libupdaterufp.so');ufp=View(source['path'],source['sha256'])
    cases=[('mode0',0,{},0),('mode1',1,{},0),('mode2',2,{},0),('mode0_version_skip',0,{'version_skip':1},0),
           ('body_preparation_failure',1,{'prepare_body':2},None),('backup_write_failure',1,{'backup_write':0},None),
           ('lens_preparation_failure',2,{'prepare_lens':2},None),('lens_extract_failure',2,{'legacy_extract':2},None),('process_failure_not_propagated',1,{'stm_system':-1},0)]
    rows=[]
    for label,mode,fixture,expected in cases:
        row=Guest(app,ufp,fixture).run(mode);row['case']=label
        if expected is None:assert row['typed_result']!=0,(label,row)
        else:assert row['typed_result']==expected,(label,row)
        dispatch=[e for e in row['events'] if e['operation']=='original_ufp_dispatch'];assert len(dispatch)==1 and dispatch[0]['command']=={0:3,1:9,2:12}[mode]
        rows.append(row)
    result=dict(app_source_sha256=PIN,ufp_source_sha256=source['sha256'],cases=rows,
        scope='Original app execute_update, original common RPC packing/copying, and original UFP callback run in a single bounded synthetic guest. Registration response, preparation results, backups, process requests and follow-up actions are explicit fixtures; no original file parser, auth server, shell, dlopen, reboot, USB or camera execution. Passing typed result is not update admission.')
    (HERE/'execute-update-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'mode_commands':{'0':3,'1':9,'2':12},'declared_process_failure_still_returns_success':True,'camera_actions':0}))

if __name__=='__main__':main()
