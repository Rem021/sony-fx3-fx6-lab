#!/usr/bin/env python3
"""Original lens preparation/header reader; no fabricated OSAL reply or launch."""
import hashlib,io,json,struct,zlib
from decrypt_stream_guest import HERE,TASK,View,ap_sources,LoaderGuest,DATA,STACK,STOP,R,AesPrimitive,whole_fixture,pack,crypt

UFP=0x40000000
TALK=0x20000000

class Guest(LoaderGuest):
    def __init__(self,views,container):
        super().__init__(views);self.views=views;self.stream=io.BytesIO(container);self.events=[];self.boundary=None;self.aes=AesPrimitive();self.bss_writes=[]
        self.u.mem_write(UFP+0x15218,b'/fixture\0')
        self.defs={base+s['st_value']:v.names.get(s.name,s.name) for base,v in views for s in v.symbols if s['st_value'] and s['st_size']}
        self.key_address=TALK+0x11028;self.key_context=TALK+0x11050

    def write_guard(self,u,access,address,size,value,user):
        if any(lo<=address and address+size<=hi for lo,hi in [(UFP+0x15208,UFP+0x15212),(UFP+0x151f4,UFP+0x151f8)]):
            self.bss_writes.append(dict(address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        return super().write_guard(u,access,address,size,value,user)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<10000
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            name=self.plt[pc]
            if name in self.definitions:u.reg_write(R.UC_ARM64_REG_PC,self.definitions[name]);return
            x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(6)]
            if name=='memset':assert STACK<=x[0] and x[0]+x[2]<=STACK+0x10000;u.mem_write(x[0],bytes([x[1]&255])*x[2]);self.ret(x[0]);return
            if name=='memcpy':assert STACK<=x[0] and x[0]+x[2]<=STACK+0x10000 and x[2]==516;u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.ret(x[0]);return
            if name=='snprintf':
                assert self.string(x[2])==b'%s/%s' and x[1]==255
                text=self.string(x[3])+b'/'+self.string(x[4]);assert text==b'/fixture/LENSDATA.DAT'
                u.mem_write(x[0],text+b'\0');self.ret(len(text));return
            if name=='Fsys_Open':
                assert self.string(x[0])==b'/fixture/LENSDATA.DAT' and x[2]==1
                self.stream.seek(0);u.mem_write(x[1],struct.pack('<Q',1));self.events.append(dict(adapter='RAM readonly Fsys_Open'));self.ret(0);return
            if name=='Fsys_Read':
                assert x[0]==1 and 0<x[2]<=516
                before=self.stream.tell();data=self.stream.read(x[2]);u.mem_write(x[1],data)
                self.events.append(dict(adapter='RAM Fsys_Read',offset=before,requested=x[2],returned=len(data)));self.ret(len(data));return
            if name=='Fsys_Seek':
                assert x[0]==1 and x[2]==1
                after=self.stream.seek(x[1],1);u.mem_write(x[3],struct.pack('<Q',after));self.events.append(dict(adapter='RAM relative seek',amount=x[1],after=after));self.ret(0);return
            if name=='Fsys_Close':assert x[0]==1;self.events.append(dict(adapter='RAM Fsys_Close'));self.ret(0);return
            if name=='strncmp':
                assert x[2]==4;a=bytes(u.mem_read(x[0],4));b=bytes(u.mem_read(x[1],4));self.ret(0 if a==b else -1 if a<b else 1);return
            if name=='AES_set_decrypt_key':
                assert x[0]==self.key_address and x[1]==128 and x[2]==self.key_context;self.aes.set_key(bytes(u.mem_read(x[0],16)));self.ret(0);return
            if name=='AES_decrypt':
                assert x[2]==self.key_context and STACK<=x[0]<STACK+0x10000 and STACK<=x[1]<STACK+0x10000
                u.mem_write(x[1],self.aes.decrypt(bytes(u.mem_read(x[0],16))));self.ret(0);return
            if name=='osal_valloc_msg_wait':
                self.boundary=dict(operation='before_OSAL_allocation',pc=hex(pc),service=hex(x[0]),requested_message_bytes=x[2],original_request_command=u.reg_read(R.UC_ARM64_REG_X21),native_allocation=False)
                assert self.boundary['service']=='0x912503d0' and x[2]==8 and self.boundary['original_request_command']==3
                u.emu_stop();return
            raise AssertionError(('unmodelled lens prep import',name,hex(pc)))
        allowed=[(UFP+0x2f48,UFP+0x3034),(UFP+0x3a00,UFP+0x3bcc),(UFP+0x1928,UFP+0x19f8),(TALK+0x8c0,TALK+0x90c)]
        assert any(lo<=pc<hi for lo,hi in allowed),('outside original lens prep selection',hex(pc))

    def execute(self):
        self.run(TALK+0x8c0,[])
        self.u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);self.u.reg_write(R.UC_ARM64_REG_X30,STOP)
        self.u.emu_start(UFP+0x2f48,STOP+4,count=10000)
        if self.boundary:assert self.u.reg_read(R.UC_ARM64_REG_PC)==int(self.boundary['pc'],16)
        else:assert self.u.reg_read(R.UC_ARM64_REG_PC)==STOP and self.u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
        return dict(returned=self.boundary is None,return_value=self.u.reg_read(R.UC_ARM64_REG_X0) if self.boundary is None else None,boundary=self.boundary,
                    copied_model_word=hex(struct.unpack('<I',self.u.mem_read(UFP+0x15208,4))[0]),file_cursor=self.stream.tell(),file_events=self.events,original_global_writes=self.bss_writes,instructions=self.steps)

def main():
    selected=[]
    for base,name in [(UFP,'libupdaterufp.so'),(TALK,'libupdatertalk.so')]:
        s=next(r for r in ap_sources() if __import__('pathlib').Path(r['path']).name==name);selected.append((base,View(s['path'],s['sha256'])))
    talk=selected[1][1];key=talk.read(0x11028,16);plain,fixture=whole_fixture();original=struct.unpack_from('<I',plain,0x24)[0]
    rows=[]
    for name,word in [('camera_model_word',original),('synthetic_accessory_class_word',(original&~0xff0000)|0xa00000)]:
        data=bytearray(plain);struct.pack_into('<I',data,0x24,word);struct.pack_into('<I',data,8,zlib.crc32(data[12:512]))
        blocks=b''.join(pack(data[i:i+1020],i+1020>=len(data)) for i in range(0,len(data),1020));cipher=crypt(blocks,key,ecb=True)
        container=b'\x89UFU\r\n\x1a\n'+struct.pack('>I',len(cipher))+b'FDAT'+cipher
        row=Guest(selected,container).execute();row.update(case=name,declared_model_word=hex(word),ram_chunk_stream_bytes=len(container),ram_chunk_stream_sha256=hashlib.sha256(container).hexdigest())
        assert row['copied_model_word']==hex(word)
        if name=='camera_model_word':assert row['returned'] and row['return_value']==2 and row['boundary'] is None
        else:assert not row['returned'] and row['boundary']['operation']=='before_OSAL_allocation'
        rows.append(row)
    result=dict(sources=[dict(path=str(v.path),sha256=hashlib.sha256(v.raw).hexdigest()) for base,v in selected],cases=rows,
                scope='Original private lens-preparation window 0x2f48..0x3034, original UFU chunk search/header info helper, talk AES wrappers and first original OSAL helper execute with RAM readonly Fsys and AES math adapters. Media root and original AES setup are explicit fixtures. Original camera model word is rejected before any IPC; changing only the class byte in a synthetic inert fixture advances to OSAL allocation and stops without response fabrication. The RAM input has a UFU signature plus FDAT chunk, no claim of a complete official UFU with CRC/footer admission. No native startup/service/IPC, file staging, mount, process launch, hardware, USB, complete firmware acceptance, flash package or device action.')
    (HERE/'lens-header-gate-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=2,camera_header_rejected_before_ipc=True,synthetic_class_stops_at_osal=True,native_ipc_calls=0,camera_actions=0)))

if __name__=='__main__':main()
