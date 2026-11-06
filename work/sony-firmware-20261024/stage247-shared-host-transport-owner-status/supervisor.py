"""Supervise fixed fake-owner launches; native render is closed.

Helper lifetime comes from kernel PID/birth/path, not launch relay status.
Observation timeouts preserve this instance and its incremental stream buffer.
No kill/reset/retry, driver, Sony, camera, cache query or administrator API.
"""
from pathlib import Path
from hashlib import sha256
import array,json,os,plistlib,secrets,select,socket,stat,struct,subprocess,time
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SOCKET_ROOT=Path('/private/tmp/fx3-fixture-ipc247')

def put(path,value):
    data=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        if os.write(fd,data)!=len(data):raise OSError('short evidence write')
        os.fsync(fd)
    finally:os.close(fd)

def raw_file(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        if os.write(fd,data)!=len(data):raise OSError('short private evidence write')
        os.fsync(fd)
    finally:os.close(fd)

class Job:
    @classmethod
    def fixture(cls,*,name=None,block=0,fail=0,vendor_fixture=False,bad_digest=False,early_relay=False,guard=None,fixture_option=0):
        if os.getuid()!=os.geteuid() or os.getuid()==0:raise R.Rejected('unprivileged fixture only')
        v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
        if v['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise R.Rejected('wrong external volume')
        self=cls();self.ipc=I.IPC();self.vendor_fixture=bool(vendor_fixture)
        self.directory=HERE/'runs'/(name or secrets.token_hex(8))
        if self.directory.parent!=HERE/'runs':raise R.Rejected('fixture directory boundary')
        self.directory.mkdir(mode=0o700,parents=True,exist_ok=False)
        SOCKET_ROOT.mkdir(mode=0o700,exist_ok=True);self.sockdir=SOCKET_ROOT/secrets.token_hex(5);self.sockdir.mkdir(mode=0o700)
        self.sockpath=self.sockdir/'s';assert len(os.fsencode(self.sockpath))<104
        self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.server.bind(str(self.sockpath));os.chmod(self.sockpath,0o600);self.server.listen(1);self.server.setblocking(False)
        self.frame=I.Frame(self.directory/'shared.bin',self.ipc,block=block,fail=fail,option=(4096 if vendor_fixture else 0)|fixture_option)
        m=self.ipc.build['builds']['fixture'];self.expected_digest=m['sha256'];self.expected_path=str(self.directory/'installed/helper')
        source=P.private_copy(m['path'],m['sha256'],self.directory)
        self.guard=Path(guard) if guard is not None else self.directory/'global.journal'
        if not self.guard.is_relative_to(HERE/'runs'):raise R.Rejected('fixture journal boundary')
        body=P.bootstrap(source,'0'*64 if bad_digest else m['sha256'],self.expected_path,self.frame.path,self.frame.nonce.hex(),fixture=True,socket_path=self.sockpath,guard=self.guard)
        command=P.command(body,self.directory,self.frame.nonce.hex(),fixture=True)
        self.command=self.directory/'Fixture.command';self.command.write_text(command);os.chmod(self.command,0o700)
        put(self.directory/'spec.json',{'schema':1,'grant_id':R.GRANT_ID,'mode':'fixture','nonce':self.frame.nonce.hex(),
            'expected_path':self.expected_path,'expected_digest':m['sha256'],'camera_or_root_operations':0})
        self.err=os.fdopen(os.open(self.directory/'runner-stderr.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
        self.out=os.fdopen(os.open(self.directory/'runner-stdout.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
        self.runner=subprocess.Popen(['/bin/sh',str(self.command)],stdin=subprocess.DEVNULL,stdout=self.out,stderr=self.err,start_new_session=True,close_fds=True)
        self.relay=subprocess.Popen(['/usr/bin/true']) if early_relay else self.runner
        self.verified=None;self.conn=None;self.receiver=None;self.buffer=bytearray();self.total_bytes=0
        self.responses=[];self.receipt=None;self.error=None;self.stream_eof=False;self.hello=None;self.ops=[];self.mode='fixture'
        return self

    def _fail(self,error):
        if self.error is None:
            self.error=repr(error)
            put(self.directory/'observer-error.json',{'error':self.error,'automatic_retry':False,'status':'UNKNOWN'})
            try:self.frame.stop()
            except OSError:pass

    def _entry(self):
        if self.verified is not None:return
        g=self.frame.snapshot()
        if not g.ready:return
        verified=R.capture_helper(g.pid,os.getuid(),self.expected_path,self.expected_digest,self.ipc.probe,mode='fixture')
        if (g.sec,g.usec)!=(verified.identity.sec,verified.identity.usec):raise R.Rejected('shared birth disagrees with kernel')
        self.verified=verified
        put(self.directory/'verified-helper.json',{'identity':verified.identity.__dict__,'nonce':self.frame.nonce.hex(),
            'relay_pid':self.relay.pid,'snapshot_only_after_restart':True})
        self.entry_ack_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC);self.frame.ack()

    def _hello(self,data):
        self.hello=self.receiver.accept_hello(data)
        raw_file(self.directory/'live-self-image.bin',data)
        put(self.directory/'live-self-image.json',self.hello)
        self.receiver.acknowledge()
        self.ops=[(1,b''),(6,b''),(5,b'')]
        if self.vendor_fixture:self.ops=[(1,b''),(2,bytes.fromhex('4301ff37aad70000')),(5,b'')]
        self.conn.settimeout(.2)
        try:
            for i,(op,payload) in enumerate(self.ops,1):
                packet=struct.pack('<IIQQQII16s',0x31385146,1,i,17,self.entry_ack_ns+500_000_000,op,len(payload),self.frame.nonce)+payload.ljust(516,b'\0')
                self.conn.sendall(struct.pack('<I',572)+packet)
        finally:self.conn.setblocking(False)

    def _message(self,data):
        if self.receipt is not None:raise R.Rejected('bytes after final record')
        if self.hello is None:
            if len(data)!=160:raise R.Rejected('self-image HELLO required first')
            self._hello(data);return
        if len(data)==676:
            number=len(self.responses)+1
            if number>len(self.ops) or struct.unpack_from('<IIQ',data)!=(0x52385146,1,number) or data[48:64]!=self.frame.nonce or struct.unpack_from('<I',data,40)[0]:
                raise R.Rejected('operation response identity/proof')
            status,flags=struct.unpack_from('<II',data,16)
            if status>8 or (not self.vendor_fixture and flags&(1|2|32)):raise R.Rejected('unreleased vendor response')
            self.responses.append({'id':number,'status':status,'flags':flags});return
        if len(data)!=1024:raise R.Rejected('unknown final frame')
        value=R.decode_record(data,self.verified.identity,self.frame.nonce)
        value['transport_peer_verified']=True
        if value['native_return']==0 and (len(self.responses)!=len(self.ops) or any(r['status'] for r in self.responses)):
            raise R.Rejected('clean result lacks expected observe/end responses')
        self.receipt=value
        raw_file(self.directory/'private-record.bin',data)
        put(self.directory/'private-record.json',{k:v for k,v in value.items() if k!='result_bytes'})

    def _network(self,seconds):
        if self.conn is None:
            try:self.conn,_=self.server.accept()
            except BlockingIOError:return
            self.conn.setblocking(False)
            self.receiver=R.Receiver(self.conn,self.verified,self.frame.nonce)
        if self.stream_eof:return
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            ready,_,_=select.select([self.conn],[],[],max(0,min(.005,deadline-time.monotonic())))
            if not ready:return
            try:data,anc,flags,_=self.conn.recvmsg(1,socket.CMSG_SPACE(512*4),socket.MSG_DONTWAIT)
            except (BlockingIOError,InterruptedError):continue
            for level,kind,raw in anc:
                if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                    fds=array.array('i');fds.frombytes(raw[:len(raw)//fds.itemsize*fds.itemsize])
                    for fd in fds:
                        if fd>=0:os.close(fd)
            if anc or flags&(socket.MSG_CTRUNC|socket.MSG_TRUNC):raise R.Rejected('ancillary stream data rejected')
            if not data:
                self.stream_eof=True
                if self.buffer or self.receipt is None:raise EOFError('incomplete owner stream')
                return
            self.total_bytes+=len(data)
            if self.total_bytes>8192:raise R.Rejected('host stream budget')
            self.buffer.extend(data)
            if len(self.buffer)<4:continue
            count=struct.unpack_from('<I',self.buffer)[0]
            if count not in (160,676,1024):raise R.Rejected('host stream frame length')
            if len(self.buffer)==count+4:
                message=bytes(self.buffer[4:]);self.buffer.clear();self._message(message)

    def step(self,seconds=.02):
        if not 0<seconds<=.1:raise R.Rejected('bounded observation interval required')
        self.runner.poll();self.relay.poll()
        if self.error is None:
            try:
                self._entry()
                if self.verified is not None:self._network(seconds)
            except (OSError,ValueError,EOFError) as e:self._fail(e)
        state={'status':'OWNER_ALIVE_UNRESOLVED' if self.verified else 'UNKNOWN_ENTRY_NOT_VERIFIED',
               'helper_terminal_observed':False,'physical_camera_acceptance':False,'automatic_retry':False,'new_trial_authorized':False,
               'relay_returncode':self.relay.poll(),'relay_is_not_helper_identity':True}
        if self.error:return dict(state,status='UNKNOWN_OBSERVER_ERROR',error=self.error)
        if self.receipt:
            state.update(R.observe_completion(self.receipt,self.verified,self.ipc.probe))
        return state

    def wait(self,seconds=3):
        until=time.monotonic()+seconds;value=None
        while time.monotonic()<until:
            value=self.step(min(.02,max(.001,until-time.monotonic())))
            if value['helper_terminal_observed'] or value['status']=='OWNER_RETAINED' or self.error:return value
            if self.verified is None and self.runner.poll() is not None:return value
            time.sleep(.003)
        return value or self.step(.001) # no launch/restart on timeout

    def request_stop(self):self.frame.stop()

    def close_observer(self):
        """Only close our own host descriptors. Never terminate a helper."""
        if self.conn:self.conn.close();self.conn=None
        self.server.close();self.frame.close();self.out.close();self.err.close()
        if self.sockpath.exists():self.sockpath.unlink()
        self.sockdir.rmdir()

def recorded_observation(directory):
    """Saved user files cannot recreate the previous live peer proof."""
    directory=Path(directory)
    if not directory.is_relative_to(HERE/'runs'):raise R.Rejected('own recorded directory required')
    result={'status':'UNKNOWN_RECORDED_CONTEXT','authenticated_completion':False,'automatic_retry':False,
            'new_trial_authorized':False,'physical_camera_acceptance':False}
    p=directory/'verified-helper.json'
    if not p.exists():return result
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or not 0<st.st_size<=8192:raise R.Rejected('recorded proof envelope')
        data=os.pread(fd,8193,0)
    finally:os.close(fd)
    saved=json.loads(data);i=saved['identity'];probe=I.IPC().probe(i['pid'])
    result['current_process_matches_untrusted_record']=bool(probe and (probe.uid,probe.sec,probe.usec,probe.path)==(i['uid'],i['sec'],i['usec'],i['path']))
    return result
