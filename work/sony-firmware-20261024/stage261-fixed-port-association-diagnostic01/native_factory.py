"""One-shot factory. No query/staging/Terminal access merely by import."""
from pathlib import Path
from hashlib import sha256
import json,os,plistlib,re,socket,subprocess
import controller_ipc as I
import fixed_launch as P
import receipt_receiver as R
import supervisor as S
import cache_preflight as C
H=Path(__file__).resolve().parent

def preflight_query():
    from cache_parser import sanitize
    raw=subprocess.run(['/usr/sbin/ioreg','-a','-p','IOService','-r','-c','IOUSBHostDevice','-l','-w','0'],capture_output=True,check=True,timeout=15).stdout
    observed=sanitize(raw)
    probe=subprocess.run([I.build()['builds']['cache_probe']['path']],capture_output=True,text=True,timeout=8)
    port=json.loads(probe.stdout)if probe.stdout.strip()else{}
    for candidate in observed['candidates']:
        candidate['physical_port_registryID']=port.get('physical_port_registryID',0)if probe.returncode==0 and port.get('candidate_count')==1 and port.get('registryID')==candidate['registryID']else 0
    roots=plistlib.loads(raw); roots=[roots] if isinstance(roots,dict) else roots
    target=json.loads((H/'fixed-material.json').read_text())['target']
    selected=[]
    def select(nodes):
        for n in nodes:
            if n.get('IOObjectClass')=='IOUSBHostDevice' and n.get('IORegistryEntryID')==target['registryID']:
                selected.append(n)
            select(n.get('IORegistryEntryChildren',[]))
    select(roots)
    if len(selected)!=1:
        observed.update(cached_media_BSD_names=[],storage_driver_classes=[],mounted_camera_media=[],media_unknown=True,
            fixed_storage_parent_matches=len(selected),cached_IOService_and_host_mount_metadata_only=True)
        return observed
    media=[];drivers=[];unknown=[]
    def descend(n):
        cls=n.get('IOObjectClass','')
        if 'IOUSBMassStorage' in cls: drivers.append(cls)
        if cls=='IOMedia' or 'BSD Name'in n:
            name=n.get('BSD Name')
            if isinstance(name,str) and re.fullmatch(r'disk[0-9]+(?:s[0-9]+)*',name):media.append(name)
            else:unknown.append(True)
        for child in n.get('IORegistryEntryChildren',[]):descend(child)
    descend(selected[0])
    mounts=subprocess.check_output(['/sbin/mount'],text=True,timeout=5)
    mounted={m.group(1) for line in mounts.splitlines() if (m:=re.match(r'^/dev/(disk[0-9]+(?:s[0-9]+)*) on ',line))}
    observed.update(cached_media_BSD_names=sorted(set(media)),storage_driver_classes=sorted(set(drivers)),
        mounted_camera_media=sorted(mounted.intersection(media)),media_unknown=bool(unknown),
        cached_IOService_and_host_mount_metadata_only=True)
    return observed

def validate_preflight(observed,target):
    physical=json.loads((H/'fixed-material.json').read_text())['physical_port_registryID']
    try:C.validate(observed,target,physical)
    except ValueError as e:raise R.Rejected(str(e))from e

def prepare_native_session(goal):
    P.native_authority(goal)
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    if v.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise R.Rejected('wrong project volume')
    material=json.loads((H/'fixed-material.json').read_text())
    observed=preflight_query();validate_preflight(observed,material['target'])
    j=S.Job();j.ipc=I.IPC();j.vendor_fixture=False;j.mode='live';j.expected_uid=0
    j.directory=P.JOB;j.sockdir=P.JOB;j.sockpath=P.JOB/'peer.sock'
    j.directory.mkdir(mode=0o700,exist_ok=False)
    S.put(j.directory/'attempt.claim',dict(grant_id=R.GRANT_ID,scope=P.SCOPE,
          approval_bundle_sha256=sha256((H/'approval-bundle.json').read_bytes()).hexdigest(),automatic_retry=False))
    S.put(j.directory/'cached-preflight.json',observed)
    j.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);j.server.bind(str(j.sockpath))
    os.chmod(j.sockpath,0o600);j.server.listen(1);j.server.setblocking(False)
    j.frame=I.Frame(j.directory/'shared.bin',j.ipc,mode=0)
    item=j.ipc.build['builds']['native'];j.expected_digest=item['sha256'];j.expected_path=str(P.ROOT_DIR/'helper')
    source=P.private_copy(item['path'],item['sha256'],j.directory)
    permit=(H/'permit.bin').read_bytes()
    if len(permit)!=96 or sha256(permit).hexdigest()!=material['permit_sha256']:raise R.Rejected('permit source changed')
    S.raw_file(j.directory/'source-permit',permit)
    command,body=P.render_native(j.frame.nonce.hex())
    plan=json.loads((H/'fixed-plan.json').read_text())
    if sha256(command.encode()).hexdigest()!=plan['terminal_command_sha256']:raise R.Rejected('rendered command changed')
    j.command=j.directory/'SonyCommunication.command'
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
