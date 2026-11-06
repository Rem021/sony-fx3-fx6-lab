"""Fixed host-only plan generation. Import/render does not execute anything."""
from pathlib import Path
from hashlib import sha256
import json,os,shlex,stat
import controller_ipc as I
import receipt_receiver as R
HERE=Path(__file__).resolve().parent
JOB=Path('/private/tmp')/R.GRANT_ID
BASE=Path('/private/var/root/fx3-host-validation')
PROTECTED=BASE/R.GRANT_ID

def copy_source(source,digest,directory):
    directory=Path(directory);st=directory.lstat()
    if directory.resolve()!=directory or not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:
        raise R.Rejected('source copy private directory')
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or not 0<st.st_size<=8*1024*1024:raise R.Rejected('source file type/size/links')
        data=os.pread(fd,st.st_size+1,0)
    finally:os.close(fd)
    if len(data)!=st.st_size or sha256(data).hexdigest()!=digest:raise R.Rejected('source hash')
    path=directory/'source-helper';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o500)
    try:
        at=0
        while at<len(data):
            n=os.write(fd,data[at:])
            if n<=0:raise OSError('source copy short write')
            at+=n
        os.fchmod(fd,0o500);os.fsync(fd)
    finally:os.close(fd)
    if sha256(path.read_bytes()).hexdigest()!=digest:raise R.Rejected('staged source hash')
    return path

def body(source,digest,job,protected,nonces,sockets,*,fixture=False):
    job=Path(job);protected=Path(protected);q=lambda x:shlex.quote(str(x))
    if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest) or len(nonces)!=2 or nonces[0]==nonces[1] or any(len(n)!=32 or any(c not in '0123456789abcdef' for c in n) for n in nonces):raise R.Rejected('plan digest/nonces')
    if fixture:
        if not job.is_relative_to(HERE/'runs') or protected!=job/'protected':raise R.Rejected('fixture plan paths')
    elif job!=JOB or protected!=PROTECTED or Path(source)!=JOB/'source-helper' or list(map(Path,sockets))!=[JOB/'trial.sock',JOB/'query.sock']:
        raise R.Rejected('fixed root plan paths')
    lines=['set -euC','cd /','umask 077']
    if not fixture:lines+=[
        '[ "$(/usr/bin/id -u)" = 0 ] || exit 77',
        'if [ ! -e '+q(BASE)+' ]; then /bin/mkdir -m 700 '+q(BASE)+'; fi',
        '[ ! -L '+q(BASE)+' ] && [ -d '+q(BASE)+' ] || exit 78',
        '[ "$(/usr/bin/stat -f %u:%Lp '+q(BASE)+')" = 0:700 ] || exit 78']
    lines+=['/bin/mkdir -m 700 '+q(protected),'/usr/bin/install -m 500 '+q(source)+' '+q(protected/'helper'),
        'actual=$(/usr/bin/shasum -a 256 '+q(protected/'helper')+')',
        '[ "$actual" = '+q(digest+'  '+str(protected/'helper'))+' ] || exit 78']
    for mode,frame,n,sock in zip(('trial','readback'),('trial.bin','query.bin'),nonces,sockets):
        argv=[protected/'helper',mode,job/frame,n,sock]
        if fixture:argv.append(protected)
        lines.append(' '.join(map(q,argv))+' 2>&1')
    return '\n'.join(lines)+'\n'

def command(script,job,*,fixture=False):
    job=Path(job);q=lambda x:shlex.quote(str(x))
    if (fixture and not job.is_relative_to(HERE/'runs')) or (not fixture and job!=JOB):raise R.Rejected('command job path')
    invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+q(script)
    if not fixture:invocation='/usr/bin/sudo -- '+invocation
    return '\n'.join(['#!/bin/sh','set -euC','cd /','umask 077',
        '/bin/mkdir -m 700 '+q(job/'command.once'),
        'if '+invocation+' > '+q(job/'relay-stdout.txt')+'; then code=0; else code=$?; fi',
        'printf \'{"relay_returncode":%s,"host_only":true}\\n\' "$code" > '+q(job/'relay-marker.json'),
        'exit "$code"',''])

def checked_bundle():
    raw=(HERE/'approval-bundle.json').read_bytes();bundle=json.loads(raw)
    if bundle['grant_id']!=R.GRANT_ID or bundle['scope']!='HOST_ONLY' or bundle['maximum_helper_invocations']!=2:raise R.Rejected('host approval bundle identity')
    for e in bundle['files']:
        p=HERE/e['path']
        if sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise R.Rejected('host approval member changed')
    I.build()
    return bundle,sha256(raw).hexdigest()

def authority(goal):
    bundle,digest=checked_bundle();a=goal.get('authorization',{}).get('Mac_root_host01',{})
    if os.getuid()!=501 or os.geteuid()!=501:raise R.Rejected('plain console user501 required')
    if a.get('authorized') is not True or type(a.get('maximum_helper_invocations')) is not int or a!={'authorized':True,'grant_id':R.GRANT_ID,'bundle_sha256':digest,'scope':'HOST_ONLY','maximum_helper_invocations':2}:
        raise R.Rejected('new exact host-only approval required; old host/device grants cannot substitute')
    return bundle
