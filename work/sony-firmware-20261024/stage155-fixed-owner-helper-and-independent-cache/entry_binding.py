"""Bindings for device-free entry IPC only; native helper has no DSO loader."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import json
import mmap
import os
import secrets
import owner_binding as B

HERE=Path(__file__).resolve().parent


class Grant(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ['schema','mode','owner_uid','scope']]+[
        ('nonce',C.c_uint8*16),('privacy_key',C.c_uint8*32),('expected_body_tag',C.c_uint8*32)]+[
        (n,C.c_uint32) for n in ['attempt_claimed','native_started','native_completed','native_pid']]+[
        (n,C.c_uint64) for n in ['birth_sec','birth_usec','started_ns','work_deadline_ns','final_deadline_ns']]+[
        ('native_return',C.c_int32),('fixture_fail',C.c_uint32),('fixture_option',C.c_uint32),('fixture_block',C.c_uint32),
        ('fixture_observed_tag',C.c_uint8*32),('result_sha256',C.c_uint8*32)]


class IPC:
    def __init__(self):
        build=json.loads((HERE/'helper-build-receipt.json').read_text())
        for m in build['sources']:assert sha256((HERE/m['path']).read_bytes()).hexdigest()==m['sha256']
        p=HERE/build['ipc']['path'];assert sha256(p.read_bytes()).hexdigest()==build['ipc']['sha256']
        self.library=C.CDLL(str(p))
        specs={'fx3_entry_layout':([C.c_uint32],C.c_uint32),'fx3_ipc_layout':([C.c_uint32],C.c_uint32),
            'fx3_entry_init':([C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p],C.c_int),
            'fx3_ipc_stop':([C.c_void_p],None),'fx3_ipc_pending':([C.c_void_p],C.c_uint32),
            'fx3_ipc_fixture_release':([C.c_void_p],None),'fx3_ipc_fixture_entered':([C.c_void_p],C.c_uint32),
            'fx3_entry_pid_info':([C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)],C.c_int)}
        for n,(args,restype) in specs.items():
            f=getattr(self.library,n);f.argtypes=args;f.restype=restype;setattr(self,n,f)
        size,self.grant_offset,gs,cs,rs,cts=[self.fx3_entry_layout(n) for n in range(6)]
        assert size<=4096 and gs==C.sizeof(Grant) and (cs,rs,cts)==(C.sizeof(B.Config),C.sizeof(B.Result),C.sizeof(B.Control))
        self.result_offset=self.fx3_ipc_layout(1)


class Frame:
    def __init__(self,path,ipc,*,expected_tag=None,observed_tag=None,block_phase=0):
        self.path=Path(path);self.ipc=ipc
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
        os.ftruncate(fd,4096);self.mapping=mmap.mmap(fd,4096,access=mmap.ACCESS_WRITE);os.close(fd)
        self.view=(C.c_uint8*4096).from_buffer(self.mapping);self.address=C.addressof(self.view)
        self.nonce=secrets.token_bytes(16);key=secrets.token_bytes(32);tag=expected_tag or bytes([0x41])*32
        assert ipc.fx3_entry_init(self.address,4096,1,os.getuid(),self.nonce,key,tag)==0
        self.grant=Grant.from_buffer(self.mapping,ipc.grant_offset)
        self.grant.fixture_observed_tag[:]=observed_tag or bytes([0x41])*32
        self.grant.fixture_block=block_phase;self.mapping.flush()

    def stop(self):self.ipc.fx3_ipc_stop(self.address)
    def release_fixture(self):self.ipc.fx3_ipc_fixture_release(self.address)
    def pending(self):return self.ipc.fx3_ipc_pending(self.address)
    def entered(self):return self.ipc.fx3_ipc_fixture_entered(self.address)
    def result(self):return B.Result.from_buffer_copy(self.mapping[self.ipc.result_offset:self.ipc.result_offset+C.sizeof(B.Result)])
    def result_bytes(self):return self.mapping[self.ipc.result_offset:self.ipc.result_offset+C.sizeof(B.Result)]

    def close(self):
        del self.grant;del self.view;self.mapping.close()
