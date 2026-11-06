#!/usr/bin/env python3
"""Original UFP chunk search and lens staging size gate with read-only inputs.

Only file-open/read/seek/close and strncmp are modelled. A payload read is a
stop boundary, never evidence of admission. No mount/write/process is allowed.
"""
from pathlib import Path
import hashlib,io,json,struct,sys
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_INVALID,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from inspect_app_crypto_calls import HERE
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources

BASE=0x20000000
DATA=0x60000000
STACK=0x70000000
STOP=0x78000000
FIRM=HERE.parents[2]/'work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT'
FIRM_PIN='f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854'

class Guest:
    def __init__(self,view,stream):
        self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);self.events=[];self.steps=0;self.stream=stream;self.boundary=None
        for seg in view.elf.iter_segments():
            if seg['p_type']!='PT_LOAD':continue
            lo=seg['p_vaddr']&-4096;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&-4096
            self.u.mem_map(BASE+lo,hi-lo);self.u.mem_write(BASE+seg['p_vaddr'],seg.data())
        # These selected functions use PC-relative data and direct PLT hooks;
        # no GOT/vtable/native dynamic loader is used or represented here.
        self.plt={BASE+a:n for a,n in view.plt.items()}
        self.u.mem_map(DATA,4096);self.u.mem_map(STACK,0x300000);self.u.mem_map(STOP,4096)
        self.u.mem_write(DATA,b'/read-only/original-or-prefix-fixture\0')
        self.u.hook_add(UC_HOOK_CODE,self.code)
        self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
        self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_guard)

    def ret(self,v=0):
        self.u.reg_write(R.UC_ARM64_REG_X0,v&0xffffffffffffffff)
        self.u.reg_write(R.UC_ARM64_REG_PC,self.u.reg_read(R.UC_ARM64_REG_X30))
    def invalid(self,u,access,a,size,value,user):raise AssertionError(('unmapped',hex(u.reg_read(R.UC_ARM64_REG_PC)),hex(a),size))
    def write_guard(self,u,access,a,size,value,user):assert STACK<=a and a+size<=STACK+0x300000,('write outside synthetic stack',hex(a),size)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<10000
        if pc==STOP:u.emu_stop();return
        if pc==BASE+0x3c14:
            address=u.reg_read(R.UC_ARM64_REG_X29)+0x34
            self.events.append(dict(operation='original_parser_length',value=struct.unpack('<I',u.mem_read(address,4))[0]))
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if name=='Fsys_Open':
                assert x[2]==1;self.stream.seek(0);u.mem_write(x[1],struct.pack('<Q',1));self.events.append(dict(operation='read_only_open_fixture'));self.ret();return
            if name=='udtr_cmd_search_chank':u.reg_write(R.UC_ARM64_REG_PC,BASE+0x3a00);return
            if name=='Fsys_Seek':
                assert x[0]==1 and x[2]==1
                before=self.stream.tell();after=self.stream.seek(x[1],1)
                u.mem_write(x[3],struct.pack('<Q',after));self.events.append(dict(operation='relative_seek',before=before,amount=x[1],after=after));self.ret();return
            if name=='Fsys_Read':
                assert x[0]==1
                if x[2]>16:
                    self.boundary=dict(operation='payload_read_boundary',requested_bytes=x[2],file_offset=self.stream.tell())
                    self.events.append(self.boundary);u.emu_stop();return
                before=self.stream.tell();data=self.stream.read(x[2]);u.mem_write(x[1],data)
                self.events.append(dict(operation='read',offset=before,requested_bytes=x[2],actual_bytes=len(data)))
                self.ret(len(data));return
            if name=='Fsys_Close':assert x[0]==1;self.events.append(dict(operation='read_only_close_fixture'));self.ret();return
            if name=='strncmp':
                assert x[2]==4;a=bytes(u.mem_read(x[0],4));b=bytes(u.mem_read(x[1],4));self.ret(0 if a==b else -1 if a<b else 1);return
            raise AssertionError(('unmodelled boundary',name,hex(pc)))
        assert any(a<=pc<b for a,b in [(BASE+0x3a00,BASE+0x3afc),(BASE+0x3bcc,BASE+0x3cd0)]),('outside selected original code',hex(pc))

    def run(self,null=False):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        initial_sp=STACK+0x2ff000
        u.reg_write(R.UC_ARM64_REG_SP,initial_sp);u.reg_write(R.UC_ARM64_REG_X0,0 if null else DATA);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        u.emu_start(BASE+0x3bcc,STOP+4,count=10000)
        returned=u.reg_read(R.UC_ARM64_REG_PC)==STOP
        if returned:
            assert u.reg_read(R.UC_ARM64_REG_SP)==initial_sp
            assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return dict(returned=returned,result=u.reg_read(R.UC_ARM64_REG_X0) if returned else None,boundary=self.boundary,events=self.events,instructions=self.steps)

def main():
    source=next(s for s in sources() if Path(s['path']).name=='libupdaterufp.so');view=View(source['path'],source['sha256'])
    with FIRM.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==FIRM_PIN
        real=Guest(view,stream).run()
    assert real['returned'] and real['result']==3 and real['boundary'] is None
    rows=[dict(case='original_7_02',source_sha256=FIRM_PIN,**real)]
    for length in [0x200000,0x200001]:
        # Sixteen bytes describe the first FDAT chunk length. There is no
        # payload, signature or complete firmware fixture, and no file output.
        prefix=b'\x89UFU\r\n\x1a\n'+struct.pack('>I',length)+b'FDAT'
        row=Guest(view,io.BytesIO(prefix)).run()
        if length==0x200000:assert not row['returned'] and row['boundary']['requested_bytes']==length
        else:assert row['returned'] and row['result']==3 and row['boundary'] is None
        rows.append(dict(case='length_prefix_only',declared_length=length,prefix_bytes=len(prefix),prefix_sha256=hashlib.sha256(prefix).hexdigest(),**row))
    null=Guest(view,io.BytesIO(b'')).run(null=True);assert null['returned'] and null['result']==3
    rows.append(dict(case='null_input',**null))
    result=dict(source_sha256=source['sha256'],original_functions=['0x3a00 udtr_cmd_search_chank','0x3bcc udtr_write_firm_from_media'],cases=rows,
                scope='Original chunk search and staging size test in synthetic Unicorn RAM. Fsys is read-only host I/O; fixtures are sixteen-byte length prefixes only. Payload reads stop execution, all native mounts/writes/process/device calls are unmodelled and forbidden. The 2 MiB staging gate is the lens/media helper, not the normal body update route or the separate MSC upload callback. This is neither whole-container validation nor a flash test.')
    (HERE/'media-length-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_7_02_rejected_before_payload_read=True,staging_limit=0x200000,camera_actions=0)))

if __name__=='__main__':main()
