#!/usr/bin/env python3
"""Original CP lens receive loop/handler/reply path on a strict RAM-only bus."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID
from unicorn import arm_const as R
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'route-20261028'))
from cp_look_route import image,BASE,PIN

RAM=0x50000000
STACK=0x60000000
MSG=RAM+0x1000
REPLY=RAM+0x1200
RECEIVE=0x49f9b0

def lens_bytes(version,model,region):
    model_bytes=bytearray(struct.pack('>I',model));model_bytes[2],model_bytes[3]=model_bytes[3],model_bytes[2]
    return struct.pack('<H',version)+bytes(model_bytes)+struct.pack('>I',region)

class Peer:
    def __init__(self,raw,fixture):
        assert hashlib.sha256(raw).hexdigest()==PIN
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);self.u.mem_map(BASE,(len(raw)+4095)&-4096);self.u.mem_write(BASE,raw)
        for lo,n in [(RAM,0x10000),(STACK,0x10000),(0x1169000,4096),(0x1479000,4096)]:self.u.mem_map(lo,n)
        # Explicit synthetic CP lens-state inputs. No actual lens identity is read.
        state=dict(kind=2,ready=1,error=0,present=1,special=0,version=0x0701,model=0x91a00080,region=0)
        state.update(fixture);self.fixture=state
        self.u.mem_write(0xf12978,struct.pack('<I',state['kind']))
        self.u.mem_write(0x1169b50,lens_bytes(state['version'],state['model'],state['region']))
        for address,key in [(0x1479504,'ready'),(0x1479513,'error'),(0x1479514,'present'),(0x1479515,'special')]:self.u.mem_write(address,bytes([state[key]]))
        self.u.mem_write(0x100d972,b'\0')
        self.pending=None;self.reply=None;self.waiting=False;self.started=False;self.steps=0;self.events=[];self.entry_counts={}
        self.allowed=[(0x391b54,0x391bb2),(0x38dddc,0x38e0d0),(0x38e144,0x38e178),(0x391c60,0x391cb4),
                      (0xa878d2,0xa878de),(0x94cfea,0x94cff6),(0x94aaa2,0x94aad6),(0x94e7fc,0x94e81e),
                      (0x948538,0x948566),(0x9484c0,0x9484cc)]
        self.entries={0x391b54:'receive_thread',0x38dddc:'lens_handler',0x38e144:'reply_size_and_route',0x391c60:'reply_allocation_and_send',0x94cfea:'lens_kind_getter',0x94e7fc:'ready_path',0x94aaa2:'error_path'}
        self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_guard);self.u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
        self.u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000)

    def invalid(self,u,access,address,size,value,user):raise AssertionError(('unmapped CP access',hex(u.reg_read(R.UC_ARM_REG_PC)),hex(address),size))
    def write_guard(self,u,access,address,size,value,user):assert RAM<=address and address+size<=RAM+0x10000 or STACK<=address and address+size<=STACK+0x10000,('CP write outside declared RAM',hex(address),size)
    def ret(self,value=0):self.u.reg_write(R.UC_ARM_REG_R0,value&0xffffffff);self.u.reg_write(R.UC_ARM_REG_PC,self.u.reg_read(R.UC_ARM_REG_LR))

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<20000
        if pc in [RECEIVE,0x49f80c,0x49f140,0x49f908,0x558400,0x9e6684]:
            r=[u.reg_read(getattr(R,f'UC_ARM_REG_R{i}')) for i in range(4)]
            if pc==RECEIVE:
                assert r[0]==0x912503d0 and r[2]==0xffffffff
                if self.pending is None:self.waiting=True;u.emu_stop();return
                payload,source=self.pending;self.pending=None
                u.mem_write(MSG-12,struct.pack('<I',source));u.mem_write(MSG,payload+b'\0'*(40-len(payload)));u.mem_write(r[1],struct.pack('<I',MSG))
                self.events.append(dict(adapter='RAM receive',source=hex(source),request_hex=payload.hex()));self.ret(0);return
            if pc==0x49f80c:
                assert r[0]==self.request_source and r[2] in [8,12,20,40] and r[3]==1
                u.mem_write(REPLY-16,b'\0'*64);u.mem_write(r[1],struct.pack('<I',REPLY));self.reply_size=r[2]
                self.events.append(dict(adapter='RAM reply allocation',target=hex(r[0]),bytes=r[2]));self.ret(0);return
            if pc==0x558400:
                assert r[0]==REPLY and r[1]==MSG and r[2]==self.reply_size
                u.mem_write(r[0],bytes(u.mem_read(r[1],r[2])));self.ret(r[0]);return
            if pc==0x49f140:
                assert r[0]==self.request_source and r[1]==REPLY
                source=struct.unpack('<I',u.mem_read(REPLY-12,4))[0];assert source==0x912503d0
                self.reply=bytes(u.mem_read(REPLY,self.reply_size))
                self.events.append(dict(adapter='RAM send reply',source=hex(source),target=hex(r[0]),reply_hex=self.reply.hex()));self.ret(0);return
            if pc==0x49f908:assert r[0]==0x912503d0 and r[1]==MSG;self.events.append(dict(adapter='RAM free input'));self.ret(0);return
            self.events.append(dict(adapter='discarded CP log',address=hex(r[0])));self.ret(0);return
        assert any(lo<=pc<hi for lo,hi in self.allowed),('outside selected CP lens source',hex(pc))
        if pc in self.entries:
            label=self.entries[pc];self.entry_counts[label]=self.entry_counts.get(label,0)+1

    def request(self,payload,source=0x011d0000):
        assert len(payload) in [8,12,20] and struct.unpack_from('<I',payload)[0] in [0,1,3]
        assert self.pending is None and (not self.started or self.waiting)
        self.pending=(payload,source);self.request_source=source;self.reply=None;self.waiting=False
        before=self.steps;start=RECEIVE if self.started else 0x391b54;self.started=True
        self.u.emu_start(start|1,0,count=20000)
        assert self.waiting and self.u.reg_read(R.UC_ARM_REG_PC)==RECEIVE
        assert STACK<=self.u.reg_read(R.UC_ARM_REG_SP)<STACK+0x10000
        return self.reply,dict(instructions=self.steps-before,reply_hex=self.reply.hex() if self.reply is not None else None)

def main():
    raw=image();rows=[]
    for command,size in [(3,8),(1,12),(0,20)]:
        peer=Peer(raw,{})
        reply,meta=peer.request(struct.pack('<I',command)+b'\0'*(size-4));assert reply is not None and len(reply)==size
        assert struct.unpack_from('<I',reply,4)[0]==0
        rows.append(dict(command=command,request_bytes=size,**meta,original_entries=peer.entry_counts,events=peer.events,declared_cp_lens_state=peer.fixture))
    peer=Peer(raw,{});reply,meta=peer.request(b'\0'*20,0x011c0000);assert reply is None
    rows.append(dict(case='sender_group_mismatch',**meta,original_entries=peer.entry_counts,events=peer.events,declared_cp_lens_state=peer.fixture))
    result=dict(source_sha256=PIN,cases=rows,scope='Original CP receive loop, sender-header check, commands 0/1/3, lens-type/ready/error getters, data-field packing, reply size table, reply allocation wrapper, original header accessors and source routing execute in Thumb. Lens kind/state/metadata are explicit synthetic RAM inputs; no MMIO or hardware getter is stubbed to return success. OSAL allocation/receive/send/free, memcpy and logs are a strict RAM-only bus. Command 2 and actual update-data paths are forbidden. No real peer state, service session, IPC/device, firmware write or native target execution.')
    (HERE/'cp-peer-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_replies=[8,12,20],wrong_sender_has_no_reply=True,native_ipc_calls=0,camera_actions=0)))

if __name__=='__main__':main()
