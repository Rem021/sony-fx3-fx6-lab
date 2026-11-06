"""Load only data/process IPC. Own fixture and live frames share a typed ABI."""
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
        ('fixture_observed_tag',C.c_uint8*32),('result_sha256',C.c_uint8*32),('observer_pid',C.c_uint32),
        ('observer_birth_sec',C.c_uint64),('observer_birth_usec',C.c_uint64),('helper_ready',C.c_uint32),('parent_ack',C.c_uint32)]


class IPC:
    def __init__(self):
        build=json.loads((HERE/'helper-build-receipt.json').read_text())
        for m in build['sources']:assert sha256((HERE/m['path']).read_bytes()).hexdigest()==m['sha256']
        p=HERE/build['ipc']['path'];assert sha256(p.read_bytes()).hexdigest()==build['ipc']['sha256']
        self.library=C.CDLL(str(p))
        specs={'fx3_entry_layout':([C.c_uint32],C.c_uint32),'fx3_ipc_layout':([C.c_uint32],C.c_uint32),
            'fx3_entry_init':([C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p],C.c_int),
            'fx3_ipc_stop':([C.c_void_p],None),'fx3_ipc_pending':([C.c_void_p],C.c_uint32),
            'fx3_entry_ready':([C.c_void_p],C.c_uint32),'fx3_entry_ack':([C.c_void_p],None),
            'fx3_ipc_fixture_release':([C.c_void_p],None),'fx3_ipc_fixture_entered':([C.c_void_p],C.c_uint32),
            'fx3_entry_pid_info':([C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)],C.c_int),
            'fx3_entry_pid_path':([C.c_uint32,C.c_void_p,C.c_uint32],C.c_int)}
        for n,(args,restype) in specs.items():
            f=getattr(self.library,n);f.argtypes=args;f.restype=restype;setattr(self,n,f)
        size,self.grant_offset,gs,cs,rs,cts=[self.fx3_entry_layout(n) for n in range(6)]
        assert size<=4096 and gs==C.sizeof(Grant) and (cs,rs,cts)==(C.sizeof(B.Config),C.sizeof(B.Result),C.sizeof(B.Control))
        self.result_offset=self.fx3_ipc_layout(1)

    def identity(self,pid):
        uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64();path=C.create_string_buffer(4096)
        if self.fx3_entry_pid_info(pid,C.byref(uid),C.byref(sec),C.byref(usec)):
            return None
        if self.fx3_entry_pid_path(pid,path,4096):return None
        return {'pid':pid,'uid':uid.value,'birth_sec':sec.value,'birth_usec':usec.value,'path':os.fsdecode(path.value)}


class Frame:
    def __init__(self,path,ipc,*,mode=1,key=None,expected_tag=None,observed_tag=None,block_phase=0):
        self.path=Path(path);self.ipc=ipc;self.terminal=False
        key=secrets.token_bytes(32) if key is None else key
        tag=bytes([0x41])*32 if expected_tag is None else expected_tag
        if type(key) is not bytes or len(key)!=32 or type(tag) is not bytes or len(tag)!=32:
            raise B.Rejected('32-byte privacy key and body tag required')
        if mode not in (0,1) or (mode==0 and (block_phase or observed_tag is not None)):
            raise B.Rejected('fixture controls forbidden for native mode')
        self.nonce=secrets.token_bytes(16)
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
        os.ftruncate(fd,4096);self.mapping=mmap.mmap(fd,4096,access=mmap.ACCESS_WRITE);os.close(fd)
        self.view=(C.c_uint8*4096).from_buffer(self.mapping);self.address=C.addressof(self.view)
        assert ipc.fx3_entry_init(self.address,4096,mode,os.getuid(),self.nonce,key,tag)==0
        self.grant=Grant.from_buffer(self.mapping,ipc.grant_offset)
        observer=ipc.identity(os.getpid());assert observer
        self.grant.observer_pid=observer['pid'];self.grant.observer_birth_sec=observer['birth_sec'];self.grant.observer_birth_usec=observer['birth_usec']
        if mode==1:self.grant.fixture_observed_tag[:]=bytes([0x41])*32 if observed_tag is None else observed_tag
        self.grant.fixture_block=block_phase;self.mapping.flush()

    def stop(self):self.ipc.fx3_ipc_stop(self.address)
    def ack(self):self.ipc.fx3_entry_ack(self.address)
    def ready(self):return bool(self.ipc.fx3_entry_ready(self.address))
    def release_fixture(self):self.ipc.fx3_ipc_fixture_release(self.address)
    def pending(self):return self.ipc.fx3_ipc_pending(self.address)
    def entered(self):return self.ipc.fx3_ipc_fixture_entered(self.address)
    def result(self):return B.Result.from_buffer_copy(self.result_bytes())
    def result_bytes(self):return self.mapping[self.ipc.result_offset:self.ipc.result_offset+C.sizeof(B.Result)]
    def close_terminal(self):
        if not self.terminal:raise B.Rejected('terminal process state is required before closing mapping')
        del self.grant;del self.view;self.mapping.close()
