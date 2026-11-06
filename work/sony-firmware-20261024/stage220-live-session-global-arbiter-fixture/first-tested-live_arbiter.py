"""FIXTURE ONLY: live owner + inherited private worker channel.

No camera backend. The own ARM64 entry is not globally guarded on target yet.
An opaque O_EXCL fence survives this owner; it is never parsed for recovery.
"""
from pathlib import Path
from hashlib import sha256
import json,os,secrets,socket,stat,struct,subprocess,sys,threading,time

H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
OLD=B/'stage219-bound-handoff-and-request-claims'
FIXTURE=OLD/'runs-final-v2'
MODULE_SHA='be0805584b07e116d26da2ee8036a67cbd9c65801efdaedab47e995f33e3030d'
SOURCE_SHA='0bf7d4c932dc8a583aa5101bad7c8e7a8d6191c15c54479847c83b62434cc625'
MAX_FRAME=16384

class Denied(RuntimeError):pass

def wire(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    if not 0<len(raw)<=MAX_FRAME:raise Denied('frame size')
    return struct.pack('>I',len(raw))+raw

def receive(sock):
    def exact(n):
        out=b''
        while len(out)<n:
            raw=sock.recv(n-len(out))
            if not raw:raise EOFError('private fixture channel ended')
            out+=raw
        return out
    n=struct.unpack('>I',exact(4))[0]
    if not 0<n<=MAX_FRAME:raise Denied('frame size')
    return json.loads(exact(n))

def regular(path):
    flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
    fd=os.open(path,flags)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size>40_000_000:raise Denied('fixture regular file required')
        raw=b''
        while len(raw)<a.st_size:
            part=os.read(fd,min(1024*1024,a.st_size-len(raw)))
            if not part:raise Denied('fixture short read')
            raw+=part
        z=os.fstat(fd)
        if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns):raise Denied('fixture changed')
        return raw
    finally:os.close(fd)

def fixture_inputs():
    module=FIXTURE/'built/boot-module.so';source=FIXTURE/'fixture/synthetic.boot'
    if sha256(regular(module)).hexdigest()!=MODULE_SHA or sha256(regular(source)).hexdigest()!=SOURCE_SHA:raise Denied('fixed fixture differs')
    return module,source

class LiveArbiter:
    """One live Python owner mediates its own child fixtures, never target code.

    IDLE can return only from the original live child's private, bound result,
    observed normal exit, local byte validation and this owner's private state.
    No restart receipt, JSON result file or PID disappearance can resume it.
    """
    def __init__(self,directory,*,fixture_only=False,writer=os.write):
        if fixture_only is not True:raise Denied('no native or camera backend')
        self.directory=Path(directory);self.directory.mkdir(mode=0o700)
        self.fence=self.directory/'global-source-session.v1.held'
        self.session=secrets.token_hex(32);self.state='HELD_UNKNOWN'
        self.current=None;self.history=[];self.mutex=threading.Lock();self.children=[]
        raw=wire(dict(schema='fx3-FIXTURE-live-owner-v1',pid=os.getpid(),nonce=self.session,state='RESERVED_NEVER_RESTART_AUTHORITY'))
        fd=os.open(self.fence,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        try:
            if writer(fd,raw)!=len(raw):raise Denied('partial fence retained')
            os.fsync(fd);s=os.fstat(fd)
            self.identity=(s.st_dev,s.st_ino,s.st_size,sha256(raw).hexdigest())
        finally:os.close(fd)
        self.state='IDLE'

    @classmethod
    def attach(cls,directory,**kwargs):
        """No recovery path, even if a previous file says COMPLETE."""
        directory=Path(directory)
        if directory.exists():
            raise Denied('existing owner directory held; no restart inference')
        return cls(directory,**kwargs)

    def _identity(self):
        s=self.fence.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1 or stat.S_IMODE(s.st_mode)!=0o600:raise Denied('fence metadata drift')
        if (s.st_dev,s.st_ino,s.st_size,sha256(regular(self.fence)).hexdigest())!=self.identity:raise Denied('fence content drift')

    def start(self,request,run,shared,*,mode='normal',deadline_seconds=30,capacity=None):
        if not self.mutex.acquire(False):raise Denied('owner transition busy')
        try:
            if self.state!='IDLE':raise Denied('source owner '+self.state)
            self.state='HELD_UNKNOWN'
            self._identity();module,source=fixture_inputs()
            if type(request) is not bytes or len(request)!=128:raise Denied('fixed request bytes required')
            capacity=(int.from_bytes(request[48:56],'little') or 131072) if capacity is None else capacity
            if type(capacity) is not int or not 131072<=capacity<=33423360 or capacity%131072:raise Denied('fixture capacity')
            if mode not in ('normal','block','post-done-wait','crash-before-done','bad-nonce','bad-module','extra-frame'):raise Denied('fixture mode')
            if type(deadline_seconds) not in (int,float) or not 0<deadline_seconds<=60:raise Denied('fixture deadline')
            run=Path(run);run.mkdir(mode=0o700);shared=Path(shared)
            nonce=secrets.token_hex(32)
            binding=dict(session=self.session,nonce=nonce,request_sha256=sha256(request).hexdigest(),module_sha256=MODULE_SHA)
            parent,child=socket.socketpair();parent.setblocking(False)
            # Only this socket end is inherited; stdout/files are diagnostics.
            out=(run/'stdout.txt').open('x');err=(run/'stderr.txt').open('x')
            try:
                argv=[sys.executable,'-B',str(H/'model_worker.py'),'--fixture-only','--fd',str(child.fileno()),'--run',str(run),'--shared',str(shared)]
                p=subprocess.Popen(argv,pass_fds=(child.fileno(),),stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True)
            except BaseException:
                parent.close();raise
            finally:child.close();out.close();err.close()
            job=dict(process=p,socket=parent,run=run,shared=shared,binding=binding,request=request,
                     capacity=capacity,deadline=time.monotonic()+deadline_seconds,buffer=b'',frames=[],eof=False,done=None,ready=False,entered=False,reasons=[])
            self.current=job;self.children.append(job);self.state='RUNNING'
            # Small fixed local frame. Failure leaves the original process held.
            try:parent.sendall(wire(dict(kind='RUN',binding=binding,request=request.hex(),mode=mode,capacity=capacity)))
            except BaseException:
                self.state='HELD_UNKNOWN';job['reasons'].append('initial private send failed');raise
            return p.pid
        finally:self.mutex.release()

    def poll(self):
        with self.mutex:
            j=self.current
            if j is None:return dict(state=self.state,pid=None,live=False)
            p=j['process'];error=None
            try:
                self._identity()
                while not j['eof']:
                    try:raw=j['socket'].recv(65536)
                    except BlockingIOError:break
                    if not raw:j['eof']=True;break
                    j['buffer']+=raw
                    if len(j['buffer'])>2*MAX_FRAME:raise Denied('private stream bound')
                    while len(j['buffer'])>=4:
                        n=struct.unpack('>I',j['buffer'][:4])[0]
                        if not 0<n<=MAX_FRAME:raise Denied('private stream size')
                        if len(j['buffer'])<n+4:break
                        msg=json.loads(j['buffer'][4:n+4]);j['buffer']=j['buffer'][n+4:]
                        if not isinstance(msg,dict) or msg.get('binding')!=j['binding'] or msg.get('pid')!=p.pid:raise Denied('private result binding')
                        kind=msg.get('kind')
                        if kind=='READY' and not j['frames']:j['ready']=True
                        elif kind=='ENTERED' and j['ready'] and not j['entered'] and j['done'] is None:j['entered']=True
                        elif kind=='DONE' and j['ready'] and j['done'] is None:
                            if set(msg)!=set(('kind','binding','pid','result','source_reads','fds_closed','errors','output')):raise Denied('completion fields')
                            if type(msg['result']) is not int or type(msg['source_reads']) is not int:raise Denied('completion type')
                            j['done']=msg
                        else:raise Denied('unexpected/duplicate private frame')
                        j['frames'].append(kind)
                        if len(j['frames'])>3:raise Denied('private event limit')
            except Exception as e:error=type(e).__name__+': '+str(e)
            code=p.poll();live=code is None
            if error:j['reasons'].append(error);self.state='HELD_UNKNOWN'
            if time.monotonic()>=j['deadline']:
                self.state='HELD_UNKNOWN'
                if 'deadline exceeded' not in j['reasons']:j['reasons'].append('deadline exceeded')
            if not live and j['eof']:
                d=j['done']
                try:
                    if self.state!='RUNNING' or code!=0 or j['buffer'] or not d or d['result']!=0 or d['fds_closed'] is not True or d['errors']!=[]:raise Denied('no clean private completion and normal exit')
                    # Independent existing decoder; diagnostics never release.
                    sys.path.insert(0,str(R/'outputs/fx3-recovery-adapter'))
                    from fx3_recovery import boot_worker as W
                    role,window=struct.unpack_from('<II',j['request'],36)
                    output=j['run']/'kernel'/('fx3-boot-'+j['request'][16:32].hex()+'-b'+str(role)+'-w'+str(window)+'-v1')
                    data,info=W.decode_window(output,d['result'])
                    if d['output']!=str(output) or info['capture_id']!=j['request'][16:32].hex() or info['target']!='boot'+str(role) or info['window']!=window:raise Denied('decoded request binding')
                    if info['total_bytes']!=j['capacity']:raise Denied('fixture capacity binding')
                    first,count=W.shape(info['total_bytes'],window)
                    expected=regular(FIXTURE/'fixture/synthetic.boot')[first*W.BLOCK:(first+count)*W.BLOCK]
                    if data!=expected or d['source_reads']!=count:raise Denied('fixture bytes differ')
                    self._identity()
                    if time.monotonic()>=j['deadline']:raise Denied('late completion validation')
                    self.state='IDLE'
                except Exception as e:
                    self.state='HELD_UNKNOWN';j['reasons'].append(type(e).__name__+': '+str(e))
                j['socket'].close()
                self.history.append(dict(pid=p.pid,exit=code,state=self.state,frames=j['frames'],reasons=j['reasons'],done=d))
                self.current=None
            return dict(state=self.state,pid=p.pid,live=live,entered=j['entered'],done_received=j['done'] is not None,
                        exit=code,reasons=list(j['reasons']))

    def release_cooperative_fixture(self):
        """Only releases our artificial wait; no kill, reset or native API."""
        with self.mutex:
            if self.current is None or self.current['process'].poll() is not None:raise Denied('no live fixture')
            self.current['socket'].sendall(wire({'kind':'RELEASE_OWN_FIXTURE'}))

    def close(self):
        with self.mutex:
            if self.current is not None and self.current['process'].poll() is None:raise Denied('live process retained')
            self.state='CLOSED'
            # The fence and all artifacts are deliberately retained.

