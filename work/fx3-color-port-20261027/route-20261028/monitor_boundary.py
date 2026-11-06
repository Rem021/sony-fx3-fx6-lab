#!/usr/bin/env python3
"""Capture original application's monitor-LUT message before transport entry."""
from hashlib import sha256
import json
import struct
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm64_const as R
from ap_cp_message import AP,AP_PIN,HERE,STACK,DATA,STOP


def main():
    b=AP.read_bytes();assert sha256(b).hexdigest()==AP_PIN
    results=[]
    for value in range(5):
        u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        for a,n in [(0x2deb000,0x1000),(0x2de7000,0x1000),(0x3963000,0x1000)]:
            u.mem_map(a,n);u.mem_write(a,b[a:a+n])
        for a,n in [(STACK,0x10000),(DATA,0x1000),(STOP,0x1000)]:u.mem_map(a,n)
        u.mem_write(DATA,struct.pack('<I',value));u.reg_write(R.UC_ARM64_REG_X0,DATA)
        u.reg_write(R.UC_ARM64_REG_X1,DATA+0x100);u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000)
        u.reg_write(R.UC_ARM64_REG_LR,STOP)
        captured=[]
        def code(u,pc,size,unused):
            if pc==0x2de70a8:
                args=[u.reg_read(x) for x in [R.UC_ARM64_REG_X0,R.UC_ARM64_REG_X1,R.UC_ARM64_REG_X2,R.UC_ARM64_REG_X3,R.UC_ARM64_REG_X4]]
                raw=bytes(u.mem_read(args[1],args[2]))
                captured.append(dict(input_enum=value,transport_message_ID=hex(args[0]),
                                     request_bytes=raw.hex(),request_size=args[2],response_size=args[4],
                                     header=[hex(x) for x in struct.unpack_from('<4H',raw)],payload=raw[8:].hex(),
                                     transport_function_entered=False))
                u.emu_stop();return
            assert 0x2debdb0<=pc<0x2debf04,hex(pc)
        def write(u,access,address,size,v,unused):assert STACK<=address and address+size<=STACK+0x10000,hex(address)
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        u.emu_start(0x2debdb0,STOP+4,count=500)
        assert len(captured)==1 and captured[0]['transport_message_ID']=='0x92840747'
        assert captured[0]['request_size']==10 and captured[0]['header']==['0x200d','0x161','0xa','0x8001']
        results.extend(captured)
    result=dict(status='PASS_ORIGINAL_MONITOR_LUT_MESSAGE_BOUNDARY',cases=results,
                function_VA='0x2debdb0',function_sha256=sha256(b[0x2debdb0:0x2debf04]).hexdigest(),
                pretty_function_string_file='0x3968e20',
                scope='This is the explicitly named monitor-LUT wrapper. No transport, receiver, output routing or pixel change is proven. CP Base Picture Setting is a separate captured message path.')
    (HERE/'monitor-boundary-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'inputs',len(results),'payloads',[x['payload'] for x in results])


if __name__=='__main__':main()
