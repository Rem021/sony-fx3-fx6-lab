"""Data/process metadata only. No mmap, camera, driver or privilege API."""
from pathlib import Path
from hashlib import sha256
import ctypes as C
import errno,json,os,secrets,stat,struct
import receipt_receiver as R
HERE=Path(__file__).resolve().parent

def build():
    b=json.loads((HERE/'build-receipt.json').read_text())
    for m in b['sources']:
        if sha256((HERE/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise R.Rejected('fixed build source changed')
    for m in b['builds'].values():
        if sha256(Path(m['path']).read_bytes()).hexdigest()!=m['sha256']:raise R.Rejected('fixed binary changed')
    if b['native_build_released']is not True or b['native_helper_executed']is not False:raise R.Rejected('fixed reviewed build identity')
    return b

class Grant(C.Structure):
    _fields_=[('schema',C.c_uint32),('mode',C.c_uint32),('uid',C.c_uint32),('scope',C.c_uint32),
    ('nonce',C.c_ubyte*16),('key',C.c_ubyte*32),('tag',C.c_ubyte*32),
    ('claimed',C.c_uint32),('started',C.c_uint32),('completed',C.c_uint32),('pid',C.c_uint32),
    ('sec',C.c_uint64),('usec',C.c_uint64),('started_ns',C.c_uint64),('work_deadline',C.c_uint64),('final_deadline',C.c_uint64),
    ('result',C.c_int32),('fail',C.c_uint32),('option',C.c_uint32),('block',C.c_uint32),
    ('observed',C.c_ubyte*32),('digest',C.c_ubyte*32),('observer',C.c_uint32),('observer_sec',C.c_uint64),('observer_usec',C.c_uint64),
    ('ready',C.c_uint32),('ack',C.c_uint32)]

class IPC:
    def __init__(self):
        self.build=build();self.lib=C.CDLL(self.build['builds']['ipc']['path'],use_errno=True)
        specs={'fx3_entry_layout':(C.c_uint32,[C.c_uint32]),'fx3_ipc_layout':(C.c_uint32,[C.c_uint32]),
        'fx3_entry_init':(C.c_int,[C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p]),
        'fx3_entry_pid_info':(C.c_int,[C.c_uint32,C.POINTER(C.c_uint32),C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)]),
        'fx3_entry_pid_path':(C.c_int,[C.c_uint32,C.c_void_p,C.c_uint32]),'fx3_entry_pid_exists':(C.c_int,[C.c_uint32])}
        for n,(result,args) in specs.items():
            f=getattr(self.lib,n);f.restype=result;f.argtypes=args;setattr(self,n,f)
        self.grant_offset=self.fx3_entry_layout(1);self.gate_offset=self.fx3_ipc_layout(2)
        assert self.fx3_entry_layout(2)==C.sizeof(Grant) and self.fx3_entry_layout(4)==728

    def _identity(self,pid):
        uid=C.c_uint32();sec=C.c_uint64();usec=C.c_uint64();C.set_errno(0)
        if self.fx3_entry_pid_info(pid,C.byref(uid),C.byref(sec),C.byref(usec)):
            e=C.get_errno()
            if self.fx3_entry_pid_exists(pid)==0:return None
            raise OSError(e or errno.EIO,'process metadata unavailable; not proof of exit')
        return uid.value,sec.value,usec.value

    def probe(self,pid):
        a=self._identity(pid)
        if a is None:return None
        p=C.create_string_buffer(4096)
        if self.fx3_entry_pid_path(pid,p,4096):
            if self.fx3_entry_pid_exists(pid)==0:return None
            raise OSError(errno.EIO,'process path unavailable; not proof of exit')
        path=os.fsdecode(p.value);digest=''
        try:
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:
                st=os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or not 0<st.st_size<=8*1024*1024:raise R.Rejected('helper image file type/size')
                data=os.pread(fd,st.st_size+1,0);after=os.fstat(fd)
                if (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(data)!=st.st_size:
                    raise R.Rejected('helper image changed while reading')
                digest=sha256(data).hexdigest()
            finally:os.close(fd)
        except PermissionError:
            if a[0]!=0:raise
            # Root0500 is intentionally unreadable to501. Require its
            # self-image HELLO on the kernel-verified connection before ACK.
        if self._identity(pid)!=a:raise OSError(errno.EAGAIN,'process incarnation changed during observation')
        return R.Identity(a[0],pid,a[1],a[2],path,digest)

def native_frame_bytes(ipc):
    """Pure own RAM encoding. The factory gates any actual native job creation."""
    m=json.loads((HERE/'fixed-material.json').read_text())
    nonce=bytes.fromhex(m['nonce']);key=bytes.fromhex(m['privacy_key'])
    if os.getuid()!=501 or os.geteuid()!=501 or len(nonce)!=16 or len(key)!=32:
        raise R.Rejected('fixed native frame identity/material')
    buf=(C.c_ubyte*4096)()
    assert ipc.fx3_entry_init(buf,4096,0,501,nonce,key,bytes(32))==0
    g=Grant.from_buffer(buf,ipc.grant_offset);who=ipc.probe(os.getpid())
    if who is None:raise R.Rejected('native observer identity unavailable')
    g.observer=os.getpid();g.observer_sec=who.sec;g.observer_usec=who.usec
    return bytes(buf),nonce

class Frame:
    def __init__(self,path,ipc,*,mode=1,fail=0,option=0,block=0):
        self.path=Path(path);self.ipc=ipc;self.mode=mode
        if mode==0:
            if self.path!=Path('/private/tmp')/R.GRANT_ID/'shared.bin' or fail or option or block:
                raise R.Rejected('fixed native frame path only')
            data,self.nonce=native_frame_bytes(ipc);buf=(C.c_ubyte*4096).from_buffer_copy(data)
        elif mode==1:
            self.nonce=secrets.token_bytes(16);buf=(C.c_ubyte*4096)()
            assert ipc.fx3_entry_init(buf,4096,mode,os.getuid(),self.nonce,b'K'*32,b'A'*32)==0
        else:raise R.Rejected('frame mode')
        g=Grant.from_buffer(buf,ipc.grant_offset);identity=ipc.probe(os.getpid());assert identity
        g.observer=os.getpid();g.observer_sec=identity.sec;g.observer_usec=identity.usec
        g.fail=fail;g.option=option;g.block=block;g.observed[:]=b'A'*32 if mode==1 else bytes(32)
        self.fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.fchmod(self.fd,0o600)
        if os.write(self.fd,bytes(buf))!=4096:raise OSError('initial frame short write')
        os.fsync(self.fd);self.initial=os.fstat(self.fd)

    def snapshot(self):
        st=os.fstat(self.fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_size!=4096:
            raise R.Rejected('untrusted progress envelope invalid')
        data=os.pread(self.fd,4096,0)
        if len(data)!=4096:raise R.Rejected('short progress envelope')
        return Grant.from_buffer_copy(data,self.ipc.grant_offset)

    def word(self,offset,value):
        if value not in (0,1,2):raise R.Rejected('control value')
        if os.pwrite(self.fd,struct.pack('<I',value),offset)!=4:raise OSError('control short write')
    def ack(self):self.word(self.ipc.grant_offset+Grant.ack.offset,1)
    def stop(self):self.word(4,1)
    def fixture_gate(self,value):
        if self.mode!=1:raise R.Rejected('fixture gate unavailable for native')
        self.word(self.ipc.gate_offset,value)
    def close(self):
        if self.fd>=0:os.close(self.fd);self.fd=-1
