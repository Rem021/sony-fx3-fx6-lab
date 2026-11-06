#!/usr/bin/env python3
"""Original AP -> CP lens metadata -> kernel UPM power-state RAM bridge."""
import hashlib, json, struct, sys, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
TASK = HERE.parent
sys.path.insert(0,str(TASK/'lens-state-20261029'))
from ap_cp_lens_bridge import Guest as LensGuest, UFP, TALK, View, ap_sources, DATA, R, whole_fixture, pack, crypt, image
from upm_power_peer import Peer as PowerPeer

DYNAMIC = 0x0192002a

class Guest(LensGuest):
    def __init__(self,views,container,cp_raw,power_state,cp_state=None):
        super().__init__(views,container,cp_raw,cp_state or {})
        self.power_peer=PowerPeer(power_state);self.power_reply=None;self.power_bus=[];self.power_result=None
        self.dynamic_allocated=False;self.dynamic_released=False

    def write_guard(self,u,access,at,size,value,user):
        if at==UFP+0x151f0:
            assert size==4 and value==1 and u.reg_read(R.UC_ARM64_REG_PC)==UFP+0x2588
            self.bss_writes.append(dict(address=hex(at),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        return super().write_guard(u,access,at,size,value,user)

    def code(self,u,pc,size,user):
        if pc in self.plt:
            name=self.plt[pc];x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(5)]
            if name=='osal_dynamic_id':
                assert x[1] in [0x92,0]
                if x[0]==0x2a:
                    assert x[1]==0x92 and not self.dynamic_allocated
                    self.dynamic_allocated=True;u.mem_write(x[2],struct.pack('<I',DYNAMIC))
                    self.power_bus.append(dict(adapter='RAM declared dynamic channel allocation',channel=hex(DYNAMIC)))
                else:
                    assert x[0]==0x4a and x[1]==0 and x[2]==DYNAMIC and self.dynamic_allocated and not self.dynamic_released
                    self.dynamic_released=True;self.power_bus.append(dict(adapter='RAM dynamic channel release',channel=hex(DYNAMIC)))
                self.steps+=1;self.ret();return
            if name=='osal_valloc_msg_wait' and x[0]==0x80920871:
                assert x[2]==208 and x[3]==1
                p=DATA+0xc000;u.mem_write(p-16,b'\0'*224);u.mem_write(x[1],struct.pack('<Q',p))
                self.power_bus.append(dict(adapter='RAM AP power request allocation',bytes=208));self.steps+=1;self.ret();return
            if name=='memcpy' and x[2] in [152,156,208]:
                assert any(lo<=x[0] and x[0]+x[2]<=lo+0x10000 for lo in [DATA,0x60000000])
                u.mem_write(x[0],bytes(u.mem_read(x[1],x[2])));self.steps+=1;self.ret(x[0]);return
            if name=='osal_snd_msg' and x[0]==0x80920871:
                assert x[1]==DATA+0xc000 and self.dynamic_allocated
                request=bytes(u.mem_read(x[1],208));assert struct.unpack_from('<I',request)[0]==3 and struct.unpack_from('<I',request,8)[0]==7
                assert struct.unpack_from('<I',request,0xa4)[0]==DYNAMIC
                self.power_reply,self.power_result=self.power_peer.request(request,self.source_id)
                self.power_bus.append(dict(adapter='RAM AP-to-UPM delivery',request_hex=request.hex(),source=hex(self.source_id)));self.steps+=1;self.ret();return
            if name=='osal_rcv_msg_tmo' and x[0]==DYNAMIC:
                assert x[2]==0xffffffff and self.power_reply is not None
                p=DATA+0xd000;u.mem_write(p-12,struct.pack('<I',0x80920021));u.mem_write(p,self.power_reply);u.mem_write(x[1],struct.pack('<Q',p))
                self.power_bus.append(dict(adapter='RAM UPM-to-AP delivery',source='0x80920021',reply_hex=self.power_reply.hex()));self.power_reply=None;self.steps+=1;self.ret();return
            if name=='osal_free_msg' and x[0] in [DYNAMIC,0x80920871]:
                assert x[1] in [DATA+0xc000,DATA+0xd000]
                self.power_bus.append(dict(adapter='RAM AP power message free',unit=hex(x[0])));self.steps+=1;self.ret();return
            if name=='Backup_read':
                assert x[0]==0x00920017
                self.boundary=dict(operation='before_native_Backup_read',pc=hex(pc),item=hex(x[0]),native_call=False)
                u.emu_stop();return
        if UFP+0x2498<=pc<UFP+0x26e8:
            self.steps+=1;assert self.steps<10000;return
        return super().code(u,pc,size,user)

def main():
    views=[]
    for base,name in [(UFP,'libupdaterufp.so'),(TALK,'libupdatertalk.so')]:
        source=next(r for r in ap_sources() if Path(r['path']).name==name)
        views.append((base,View(source['path'],source['sha256'])))
    plain,fixture=whole_fixture();plain=bytearray(plain);struct.pack_into('<I',plain,0x24,0x91a00080);struct.pack_into('<I',plain,8,zlib.crc32(plain[12:512]))
    blocks=b''.join(pack(plain[i:i+1020],i+1020>=len(plain)) for i in range(0,len(plain),1020))
    cipher=crypt(blocks,views[1][1].read(0x11028,16),ecb=True)
    container=b'\x89UFU\r\n\x1a\n'+struct.pack('>I',len(cipher))+b'FDAT'+cipher
    raw=image();rows=[]
    fixtures=[('ac_connected',{}, {},0),('battery',dict(type=2,jack=2),{},None),
              ('ac_jack_ng',dict(type=1,jack=2),{},None),('model_mismatch_before_power',{},dict(model=0x91a00081),7)]
    for label,power,cp,expected in fixtures:
        guest=Guest(views,container,raw,power,cp);row=guest.execute()
        if expected is None:
            assert row['boundary']['operation']=='before_native_Backup_read' and guest.dynamic_released
        else:
            assert row['returned'] and row['return_value']==expected
        flag=struct.unpack('<I',guest.u.mem_read(UFP+0x151f0,4))[0]
        assert flag==(1 if label=='ac_connected' else 0)
        if label=='model_mismatch_before_power':assert guest.power_result is None and not guest.dynamic_allocated
        else:
            assert guest.power_result['entries']['factor7_power_copy']==1 and guest.dynamic_released
        row.update(case=label,declared_cp_state=guest.peer.fixture,declared_upm_power_cache=guest.power_peer.fixture,
                   original_ap_power_flag=flag,original_ap_metadata_checks=guest.checks,cp_entry_counts=guest.peer.entry_counts,cp_ram_bus=guest.bus,
                   power_ram_bus=guest.power_bus,upm_execution=guest.power_result)
        rows.append(row)
    result=dict(ap_sources=[dict(path=str(v.path),sha256=hashlib.sha256(v.raw).hexdigest()) for base,v in views],upm_sha256=guest.power_peer.source_sha256,
                ram_container_sha256=hashlib.sha256(container).hexdigest(),cases=rows,
                scope='Three independent guest CPUs execute original AP lens-preparation/checks, original CP lens replies, and original UPM kernel receiver/command3/factor7/reply code. Original UPM cached-state bytes reach original AP power comparisons; type1/jack1 follows original flag store and converted prepare return0. Synthetic lens identity/state, framework power cache, dynamic channel, memory message transport and allocation success remain explicit inputs. No real device state, kernel initialization, IPC/session, file admission, native module/target code, staging, crypter execution or flash is proven. Other power cases stop before Backup_read without fabricated backup bytes. This is lens prepare only, not body update or a modified firmware package.')
    (HERE/'ap-upm-bridge-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),original_prepare_return0_in_synthetic_ac_case=True,backup_bytes_fabricated=False,camera_actions=0)))

if __name__=='__main__':main()
