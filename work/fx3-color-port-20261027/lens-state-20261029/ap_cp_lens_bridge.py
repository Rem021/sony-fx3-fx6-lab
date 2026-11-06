#!/usr/bin/env python3
"""Original AP lens preparation <-> original CP peer over an explicit RAM bus."""
import hashlib,json,struct,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'legacy-stream-20261029'))
from lens_header_gate_guest import Guest as HeaderGuest,UFP,TALK
from decrypt_stream_guest import View,ap_sources,DATA,R,whole_fixture,pack,crypt
from cp_lens_peer import Peer,image,PIN as CP_PIN

class Guest(HeaderGuest):
    def __init__(self,views,container,cp_raw,cp_fixture,source_id=0x011d0000):
        super().__init__(views,container);self.peer=Peer(cp_raw,cp_fixture);self.source_id=source_id
        self.u.mem_write(UFP+0x25258,struct.pack('<I',source_id));self.u.mem_write(UFP+0x252b8,b'\0'*4)
        self.allocations={};self.reply=None;self.sequence=0;self.bus=[];self.checks=[]

    def write_guard(self,u,access,address,size,value,user):
        if address==UFP+0x252b8:
            assert size==4 and value==1 and u.reg_read(R.UC_ARM64_REG_PC)==UFP+0x3020
            self.bss_writes.append(dict(address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        if UFP+0x2525c<=address and address+size<=UFP+0x25266:
            self.bss_writes.append(dict(address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        return super().write_guard(u,access,address,size,value,user)

    def code(self,u,pc,size,user):
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(5)]
            if name=='osal_valloc_msg_wait':
                assert x[0]==0x912503d0 and x[2] in [8,12,20] and x[3]==1
                self.sequence+=1;assert self.sequence<=3
                pointer=DATA+0x8000+self.sequence*0x100;u.mem_write(pointer-16,b'\0'*64);u.mem_write(x[1],struct.pack('<Q',pointer));self.allocations[pointer]=x[2]
                self.bus.append(dict(adapter='RAM AP allocation',target=hex(x[0]),bytes=x[2]));self.steps+=1;self.ret(0);return
            if name=='osal_set_msg_src':
                assert x[0] in self.allocations and x[1]==self.source_id;u.mem_write(x[0]-12,struct.pack('<I',x[1]));self.steps+=1;self.ret(0);return
            if name=='osal_snd_msg':
                assert x[0]==0x912503d0 and x[1] in self.allocations
                request=bytes(u.mem_read(x[1],self.allocations[x[1]]));source=struct.unpack('<I',u.mem_read(x[1]-12,4))[0]
                self.reply,cp=self.peer.request(request,source)
                self.bus.append(dict(adapter='RAM AP-to-CP delivery',request_hex=request.hex(),source=hex(source),cp=cp));self.steps+=1;self.ret(0);return
            if name=='osal_rcv_msg_tmo':
                assert x[0]==self.source_id and x[2]==0xffffffff
                if self.reply is None:
                    self.boundary=dict(operation='RAM_bus_no_reply_boundary',pc=hex(pc),native_wait=False);u.emu_stop();return
                pointer=DATA+0x9000+self.sequence*0x100;u.mem_write(pointer-12,struct.pack('<I',0x912503d0));u.mem_write(pointer,self.reply);u.mem_write(x[1],struct.pack('<Q',pointer))
                self.bus.append(dict(adapter='RAM CP-to-AP delivery',reply_hex=self.reply.hex()));self.reply=None;self.steps+=1;self.ret(0);return
            if name=='osal_free_msg':
                assert x[0] in [self.source_id,0x912503d0]
                self.bus.append(dict(adapter='RAM AP free',unit=hex(x[0]),pointer=hex(x[1])));self.steps+=1;self.ret(0);return
            if name=='osal_dynamic_id':
                assert x[0]==0x2a and x[1]==0x92
                self.boundary=dict(operation='before_next_dynamic_body_service',pc=hex(pc),action=hex(x[0]),category=hex(x[1]),native_call=False)
                u.emu_stop();return
        extra=[(UFP+0x184c,UFP+0x1928),(UFP+0x1dbc,UFP+0x1f64),(UFP+0x26e8,UFP+0x2728),(UFP+0x2498,UFP+0x24d4),(UFP+0x3cd0,UFP+0x3d48)]
        if any(lo<=pc<hi for lo,hi in extra):
            self.steps+=1;assert self.steps<10000
            if pc==UFP+0x26f4:
                model,region=struct.unpack('<II',u.mem_read(UFP+0x2525c,8));version=struct.unpack('<H',u.mem_read(UFP+0x25264,2))[0]
                self.checks.append(dict(result=hex(u.reg_read(R.UC_ARM64_REG_X0)),normalized_model=hex(model),normalized_region=hex(region),normalized_version=hex(version)))
            return
        return super().code(u,pc,size,user)

def main():
    views=[]
    for base,name in [(UFP,'libupdaterufp.so'),(TALK,'libupdatertalk.so')]:
        source=next(r for r in ap_sources() if Path(r['path']).name==name);views.append((base,View(source['path'],source['sha256'])))
    plain,fixture=whole_fixture();plain=bytearray(plain);struct.pack_into('<I',plain,0x24,0x91a00080);struct.pack_into('<I',plain,8,zlib.crc32(plain[12:512]))
    blocks=b''.join(pack(plain[i:i+1020],i+1020>=len(plain)) for i in range(0,len(plain),1020));key=views[1][1].read(0x11028,16);cipher=crypt(blocks,key,ecb=True)
    container=b'\x89UFU\r\n\x1a\n'+struct.pack('>I',len(cipher))+b'FDAT'+cipher;raw=image()
    fixtures=[('matching_newer',{},0x011d0000,None,'0x1'),('model_mismatch',dict(model=0x91a00081),0x011d0000,7,'0x140'),
              ('region_mismatch',dict(region=1),0x011d0000,6,'0x141'),('same_version',dict(version=0x0702),0x011d0000,5,'0x142'),
              ('same_version_with_cp_status_flag',dict(version=0x0702,error=1),0x011d0000,None,'0x1'),
              ('cp_not_ready',dict(ready=0),0x011d0000,7,'0x140'),('sender_group_mismatch',{},0x011c0000,None,None)]
    rows=[]
    for label,cp_fixture,source_id,expected,check in fixtures:
        g=Guest(views,container,raw,cp_fixture,source_id);row=g.execute();row['case']=label
        if expected is not None:assert row['returned'] and row['return_value']==expected
        elif label in ['matching_newer','same_version_with_cp_status_flag']:assert row['boundary']['operation']=='before_next_dynamic_body_service'
        else:assert row['boundary']['operation']=='RAM_bus_no_reply_boundary'
        if check is not None:assert len(g.checks)==1 and g.checks[0]['result']==check
        else:assert not g.checks
        skip=struct.unpack('<I',g.u.mem_read(UFP+0x252b8,4))[0]
        assert skip==(1 if label=='same_version_with_cp_status_flag' else 0)
        row.update(declared_cp_lens_state=g.peer.fixture,declared_ap_source=hex(source_id),original_ap_version_skip=skip,ram_bus=g.bus,cp_events=g.peer.events,cp_original_entry_counts=g.peer.entry_counts,cp_instructions=g.peer.steps,original_ap_metadata_checks=g.checks)
        rows.append(row)
    result=dict(ap_sources=[dict(path=str(v.path),sha256=hashlib.sha256(v.raw).hexdigest()) for base,v in views],cp_source_sha256=CP_PIN,ram_chunk_stream_sha256=hashlib.sha256(container).hexdigest(),cases=rows,
                scope='Original AP lens preparation, header/chunk read/AES wrappers, commands 3/1/0 and metadata comparisons execute in AArch64; actual requests are handed to a separate original CP Thumb receive loop, sender check, handler, getter/data packing, reply-size and routing code. OSAL/memcpy are a strict RAM-only bus; CP reply payloads are built by original CP instructions, not literal success fixtures. CP lens kind/state/metadata, AP source ID, media path, AES primitive and allocator success are explicit synthetic inputs. No physical lens state or actual IPC session is proven. Matching fixture stops before next dynamic body-state service, mismatch returns original converted errors, wrong sender stops with no fabricated timeout/reply. No command 2, staging/mount/crypter/process, native target load, device/USB or firmware write.')
    (HERE/'ap-cp-bridge-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_cp_replies_used=True,next_body_service_unproven=True,model_error=7,region_error=6,version_error=5,native_ipc_calls=0,camera_actions=0)))

if __name__=='__main__':main()
