"""Kernel-bound host-only trial/readback. No device/native-camera launcher."""
from pathlib import Path
from hashlib import sha256
import array,json,os,plistlib,secrets,select,socket,struct,subprocess,time
import controller_ipc as I
import host_plan as P
import receipt_receiver as R
import host_records as H
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SOCKET_ROOT=ROOT/'work/ipc195'

def put(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        if os.write(fd,raw)!=len(raw):raise OSError('short host evidence write')
        os.fsync(fd)
    finally:os.close(fd)

class Stage:
    def __init__(self,session,mode,frame,listener):
        self.session=session;self.mode=mode;self.frame=frame;self.listener=listener;self.verified=None;self.receiver=None;self.conn=None
        self.buffer=bytearray();self.hello=False;self.record=None;self.raw=None;self.error=None;self.eof=False
    def step(self,seconds=.02):
        if self.error or self.record:return
        try:
            if self.verified is None:
                g=self.frame.snapshot()
                if not g.ready:return
                self.verified=R.capture_helper(g.pid,self.session.expected_uid,self.session.expected_path,self.session.digest,
                    self.session.ipc.probe,mode='fixture' if self.session.fixture else 'host-root')
                if (g.sec,g.usec)!=(self.verified.identity.sec,self.verified.identity.usec):raise R.Rejected('host shared birth mismatch')
                put(self.session.directory/(self.mode+'-kernel.json'),{'identity':self.verified.identity.__dict__,'nonce':self.frame.nonce.hex(),'snapshot_only':True})
                self.frame.ack()
            if self.conn is None:
                try:self.conn,_=self.listener.accept()
                except BlockingIOError:return
                self.conn.setblocking(False);self.receiver=R.Receiver(self.conn,self.verified,self.frame.nonce)
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                ready,_,_=select.select([self.conn],[],[],max(0,min(.005,until-time.monotonic())))
                if not ready:return
                try:data,anc,flags,_=self.conn.recvmsg(1,socket.CMSG_SPACE(512*4),socket.MSG_DONTWAIT)
                except (BlockingIOError,InterruptedError):continue
                for level,kind,raw in anc:
                    if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                        fds=array.array('i');fds.frombytes(raw[:len(raw)//fds.itemsize*fds.itemsize])
                        for fd in fds:
                            if fd>=0:os.close(fd)
                if anc or flags&(socket.MSG_CTRUNC|socket.MSG_TRUNC):raise R.Rejected('host ancillary data')
                if not data:raise EOFError('host result incomplete')
                self.buffer.extend(data)
                if len(self.buffer)<4:continue
                size=struct.unpack_from('<I',self.buffer)[0]
                expected=160 if not self.hello else 256 if self.mode=='trial' else 384
                if size!=expected:raise R.Rejected('host result frame size')
                if len(self.buffer)==size+4:
                    raw=bytes(self.buffer[4:]);self.buffer.clear()
                    if not self.hello:
                        self.receiver.accept_hello(raw);self.receiver.acknowledge();self.hello=True;continue
                    if self.mode=='trial':value=H.trial(raw,identity=self.verified.identity,nonce=self.frame.nonce,root_login_required=not self.session.fixture)
                    else:value=H.readback(raw,self.verified.identity,self.frame.nonce,self.session.trial.frame.nonce,root_login_required=not self.session.fixture)
                    value['transport_authenticated']=True;self.raw=raw;self.record=value
                    put(self.session.directory/(self.mode+'-live-record.json'),value)
                    fd=os.open(self.session.directory/(self.mode+'-live-record.bin'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    try:
                        if os.write(fd,raw)!=len(raw):raise OSError('short private record')
                        os.fsync(fd)
                    finally:os.close(fd)
                    return
        except (OSError,ValueError,EOFError) as e:
            self.error=repr(e);put(self.session.directory/(self.mode+'-error.json'),{'status':'UNKNOWN','error':self.error,'automatic_retry':False})
            try:self.frame.stop()
            except OSError:pass

class Session:
    @classmethod
    def fixture_session(cls,*,name=None,bad_digest=False):
        if os.getuid()!=os.geteuid() or not os.getuid():raise R.Rejected('ordinary user fixture required')
        self=cls();self.fixture=True;self.ipc=I.IPC();self.expected_uid=os.getuid();self.digest=self.ipc.build['builds']['fixture']['sha256']
        self.directory=HERE/'runs'/(name or secrets.token_hex(8))
        if self.directory.parent!=HERE/'runs':raise R.Rejected('fixture boundary')
        self.directory.mkdir(mode=0o700);self.protected=self.directory/'protected';self.expected_path=str(self.protected/'helper')
        SOCKET_ROOT.mkdir(mode=0o700,exist_ok=True);self.sockdir=SOCKET_ROOT/secrets.token_hex(5);self.sockdir.mkdir(mode=0o700)
        self._stages();source=P.copy_source(self.ipc.build['builds']['fixture']['path'],self.digest,self.directory)
        body=P.body(source,'0'*64 if bad_digest else self.digest,self.directory,self.protected,
            [self.trial.frame.nonce.hex(),self.query.frame.nonce.hex()],self.sockpaths,fixture=True)
        cmd=P.command(body,self.directory,fixture=True);self.command=self.directory/'Fixture.command';self.command.write_text(cmd);os.chmod(self.command,0o700)
        self.stdout=os.fdopen(os.open(self.directory/'launcher-stdout.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
        self.stderr=os.fdopen(os.open(self.directory/'launcher-stderr.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
        self.runner=subprocess.Popen(['/bin/sh',str(self.command)],stdin=subprocess.DEVNULL,stdout=self.stdout,stderr=self.stderr,start_new_session=True,close_fds=True)
        return self

    def _stages(self,nonces=None):
        self.sockpaths=[];self.stages=[]
        for index,(mode,file) in enumerate((('trial','trial.bin'),('readback','query.bin'))):
            frame=I.Frame(self.directory/file,self.ipc,nonce=None if nonces is None else bytes.fromhex(nonces[index]))
            path=self.sockdir/('trial.sock' if mode=='trial' else 'query.sock');listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(str(path));os.chmod(path,0o600);listener.listen(1);listener.setblocking(False)
            self.sockpaths.append(path);self.stages.append(Stage(self,mode,frame,listener))
        self.trial,self.query=self.stages

    def step(self):
        self.runner.poll()
        for stage in self.stages:stage.step()
        return self.status()
    def status(self):
        if any(s.error for s in self.stages):return {'status':'UNKNOWN_HOST_TEST','errors':[s.error for s in self.stages],'root_or_camera_recovery_proven':False}
        if self.query.record:
            value={'status':'HOST_READBACK_AUTHENTICATED_PROCESS_PRESENT','device_operations':0,'physical_camera_acceptance':False,'automatic_retry':False}
            for s in self.stages:
                if s.verified:
                    try:current=self.ipc.probe(s.verified.identity.pid)
                    except OSError:return dict(value,status='UNKNOWN_PROCESS_OBSERVATION')
                    if current==s.verified.identity:return value
                    if current and (current.sec,current.usec)==(s.verified.identity.sec,s.verified.identity.usec):return dict(value,status='UNKNOWN_PROCESS_IDENTITY_CHANGE')
            return dict(value,status='HOST_TRIAL_AND_READBACK_COMPLETE')
        return {'status':'HOST_TEST_IN_PROGRESS' if any(s.verified for s in self.stages) else 'UNKNOWN_ENTRY_NOT_VERIFIED','device_operations':0,'physical_camera_acceptance':False,'automatic_retry':False}
    def wait(self,seconds=5):
        end=time.monotonic()+seconds;value=None
        while time.monotonic()<end:
            value=self.step()
            if value['status'] in ('HOST_TRIAL_AND_READBACK_COMPLETE','UNKNOWN_HOST_TEST'):return value
            if self.fixture and self.runner.poll() is not None and self.query.record is None:return value
            time.sleep(.003)
        return value or self.status()
    def close_observer(self):
        for stage in self.stages:
            if stage.conn:stage.conn.close()
            stage.listener.close();stage.frame.close()
        self.stdout.close();self.stderr.close()
        for p in self.sockpaths:
            if p.exists():p.unlink()
        if self.fixture:self.sockdir.rmdir()

def prepare_root_session(goal):
    """Approval gate is evaluated before private staging or a root request.

    This does not launch Terminal or sudo. It creates only the approved new
    user-owned fixed job; all existing/failed files are preserved, never reused.
    """
    bundle=P.authority(goal)
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if v['VolumeUUID']!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise R.Rejected('wrong project volume')
    plan=json.loads((HERE/'fixed-plan.json').read_text())
    self=Session();self.fixture=False;self.ipc=I.IPC();self.expected_uid=0
    self.directory=P.JOB;self.sockdir=P.JOB;self.protected=P.PROTECTED;self.expected_path=str(P.PROTECTED/'helper')
    self.digest=self.ipc.build['builds']['root_host']['sha256']
    self.directory.mkdir(mode=0o700,exist_ok=False)
    put(self.directory/'attempt.claim',{'grant_id':R.GRANT_ID,'scope':'HOST_ONLY','single_attempt':True,
        'bundle_sha256':sha256((HERE/'approval-bundle.json').read_bytes()).hexdigest()})
    self._stages(plan['nonces'])
    source=P.copy_source(self.ipc.build['builds']['root_host']['path'],self.digest,self.directory)
    script=P.body(source,self.digest,self.directory,self.protected,plan['nonces'],self.sockpaths)
    command=P.command(script,self.directory)
    if sha256(command.encode()).hexdigest()!=plan['terminal_command_sha256']:raise R.Rejected('fixed root command differs')
    self.command=self.directory/'HostValidation.command';self.command.write_text(command);os.chmod(self.command,0o700)
    put(self.directory/'spec.json',plan)
    self.stdout=os.fdopen(os.open(self.directory/'open-stdout.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
    self.stderr=os.fdopen(os.open(self.directory/'open-stderr.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
    self.runner=None
    return self

def launch_root_session(goal):
    self=prepare_root_session(goal)
    self.runner=subprocess.Popen(['/usr/bin/open','-a','Terminal',str(self.command)],stdin=subprocess.DEVNULL,
        stdout=self.stdout,stderr=self.stderr,close_fds=True)
    put(self.directory/'launch-request.json',{'pid':self.runner.pid,'role':'Terminal open request only; not helper lifetime','no_automatic_retry':True})
    return self
