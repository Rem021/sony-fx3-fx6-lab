"""Single approved owner-status factory. Importing does not stage or launch."""
from pathlib import Path
from hashlib import sha256
import json,os,socket,subprocess
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
import supervisor as S
H=Path(__file__).resolve().parent

def preflight_query():
    # Only reached after exact new owner-status approval. No interface access.
    from cache_parser import sanitize
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-p','IOUSB','-l','-w','0'],capture_output=True,check=True,timeout=15).stdout
    return sanitize(raw)

def prepare_native_session(goal):
    bundle=P.native_authority(goal)  # no query, staging or sudo before this
    material=json.loads((H/'fixed-material.json').read_text());target=material['target']
    observed=preflight_query()
    if observed.get('candidate_count')!=1:raise R.Rejected('unique current target cache required')
    actual=observed['candidates'][0]
    if any(actual.get(k)!=target[k] for k in ('VID','PID','locationID','registryID','model')):
        raise R.Rejected('cached target changed; do not stage, retarget or retry this package')
    if P.JOB.exists():raise R.Rejected('one-time job already exists')
    j=S.Job();j.ipc=I.IPC();j.vendor_fixture=False;j.mode='live';j.expected_uid=0
    j.directory=P.JOB;j.sockdir=P.JOB;j.sockpath=P.JOB/'peer.sock'
    j.directory.mkdir(mode=0o700,exist_ok=False)
    S.put(j.directory/'attempt.claim',dict(grant_id=R.GRANT_ID,scope='MSC_OWNER_STATUS_ONLY',
          approval_bundle_sha256=sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),automatic_retry=False))
    S.put(j.directory/'cached-preflight.json',observed)
    j.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);j.server.bind(str(j.sockpath))
    os.chmod(j.sockpath,0o600);j.server.listen(1);j.server.setblocking(False)
    j.frame=I.Frame(j.directory/'shared.bin',j.ipc,mode=0)
    item=j.ipc.build['builds']['native'];j.expected_digest=item['sha256'];j.expected_path=str(P.ROOT_DIR/'helper')
    source=P.private_copy(item['path'],item['sha256'],j.directory)
    permit=(H/'permit.bin').read_bytes()
    if len(permit)!=96 or sha256(permit).hexdigest()!=material['permit_sha256']:raise R.Rejected('permit source changed')
    fd=os.open(j.directory/'source-permit',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        if os.write(fd,permit)!=len(permit):raise OSError('short permit copy')
        os.fsync(fd)
    finally:os.close(fd)
    body=P.bootstrap(source,item['sha256'],j.expected_path,j.frame.path,j.frame.nonce.hex())
    command=P.command(body,j.directory,j.frame.nonce.hex())
    plan=json.loads((H/'fixed-plan.json').read_text())
    if sha256(command.encode()).hexdigest()!=plan['terminal_command_sha256']:raise R.Rejected('rendered command changed')
    j.command=j.directory/'OwnerStatus.command'
    fd=os.open(j.command,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o700)
    with os.fdopen(fd,'w') as f:f.write(command)
    S.put(j.directory/'spec.json',plan)
    j.err=os.fdopen(os.open(j.directory/'open-stderr.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
    j.out=os.fdopen(os.open(j.directory/'open-stdout.txt',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')
    j.verified=None;j.conn=None;j.receiver=None;j.buffer=bytearray();j.total_bytes=0
    j.responses=[];j.receipt=None;j.error=None;j.stream_eof=False;j.hello=None;j.ops=[]
    j.runner=None;j.relay=None
    return j

def launch_native_session(goal):
    j=prepare_native_session(goal)
    j.runner=subprocess.Popen(['/usr/bin/open','-a','Terminal',str(j.command)],stdin=subprocess.DEVNULL,
                              stdout=j.out,stderr=j.err,close_fds=True)
    j.relay=j.runner
    S.put(j.directory/'launch-request.json',dict(pid=j.runner.pid,role='Terminal request, not helper identity',automatic_retry=False))
    return j
