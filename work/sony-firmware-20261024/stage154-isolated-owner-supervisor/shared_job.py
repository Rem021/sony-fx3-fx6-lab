"""IPC and pinned own-fixture loading. No real IOKit library is loaded here."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import json
import mmap
import os
import stat
import time
import owner_binding as B

HERE=Path(__file__).resolve().parent
BLOCK_BYTES=4096


def native_clock_ns():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def put_once(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())


def checked_build():
    build=json.loads((HERE/'build-receipt.json').read_text())
    for item in build['sources']:
        assert digest(HERE/item['path'])==item['sha256'],item['path']
    return build


class FixtureAPI:
    def __init__(self):
        build=checked_build();item=build['fixture']
        path=HERE/item['path']
        if digest(path)!=item['sha256']:raise B.Rejected('own fixture DSO hash mismatch')
        self.library=C.CDLL(str(path))
        self.run=B.from_fixture(self.library)
        specs={
            'fx3_ipc_layout':([C.c_uint32],C.c_uint32),
            'fx3_ipc_init':([C.c_void_p,C.c_size_t],C.c_int),
            'fx3_ipc_stop':([C.c_void_p],None),
            'fx3_ipc_stop_requested':([C.c_void_p],C.c_uint32),
            'fx3_ipc_pending':([C.c_void_p],C.c_uint32),
            'fx3_ipc_fixture_release':([C.c_void_p],None),
            'fx3_ipc_fixture_entered':([C.c_void_p],C.c_uint32),
            'fx3_ipc_install_handlers':([C.c_void_p],C.c_int),
            'fx3_ipc_remove_handlers':([],None),
            'fx3_owner_fixture_reset':([C.c_uint32]*3,None),
            'fx3_owner_fixture_block':([C.c_uint32,C.POINTER(B.FixtureGate)],None),
            'fx3_owner_fixture_calls':([C.c_uint32],C.c_uint32)}
        for name,(args,result) in specs.items():
            fn=getattr(self.library,name);fn.argtypes=args;fn.restype=result;setattr(self,name,fn)
        self.frame_size,self.result_offset,self.gate_offset,cs,rs,gs=[self.fx3_ipc_layout(n) for n in range(6)]
        assert (cs,rs,gs)==(C.sizeof(B.Control),C.sizeof(B.Result),C.sizeof(B.FixtureGate))
        assert self.frame_size<=BLOCK_BYTES and self.result_offset%8==0 and self.gate_offset%4==0
        self.fixture_sha=item['sha256']


class Shared:
    def __init__(self,path,api,*,create=False,expected_identity=None):
        flags=os.O_RDWR|os.O_NOFOLLOW
        if create:flags|=os.O_CREAT|os.O_EXCL
        fd=os.open(path,flags,0o600)
        try:
            if create:os.ftruncate(fd,BLOCK_BYTES)
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1 or st.st_size!=BLOCK_BYTES:
                raise B.Rejected('shared block identity/size/mode differs')
            self.identity=[st.st_dev,st.st_ino]
            if expected_identity is not None and self.identity!=expected_identity:raise B.Rejected('shared block was replaced')
            self.mapping=mmap.mmap(fd,BLOCK_BYTES,access=mmap.ACCESS_WRITE)
        finally:os.close(fd)
        self.api=api;self.view=(C.c_ubyte*BLOCK_BYTES).from_buffer(self.mapping)
        self.address=C.addressof(self.view)
        if create and api.fx3_ipc_init(self.address,BLOCK_BYTES)!=0:raise B.Rejected('IPC init rejected')

    def progress(self):
        return {'active_native_call_phase':self.api.fx3_ipc_pending(self.address),
            'stop_requested':bool(self.api.fx3_ipc_stop_requested(self.address)),
            'fixture_gate_entered':self.api.fx3_ipc_fixture_entered(self.address)}

    def stop(self):self.api.fx3_ipc_stop(self.address)
    def release_fixture(self):self.api.fx3_ipc_fixture_release(self.address)

    def result_bytes(self):
        return self.mapping[self.api.result_offset:self.api.result_offset+C.sizeof(B.Result)]

    def result_copy(self):return B.Result.from_buffer_copy(self.result_bytes())

    def close_terminal(self):
        del self.view
        self.mapping.close()
