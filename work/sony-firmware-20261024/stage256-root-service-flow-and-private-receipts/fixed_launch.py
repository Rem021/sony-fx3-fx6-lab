"""Render fixed shell launch; only explicit fixture APIs execute it elsewhere."""
from pathlib import Path
from hashlib import sha256
import json,os,shlex,stat
import receipt_receiver as R
import controller_ipc as I
HERE=Path(__file__).resolve().parent
JOB=Path('/private/tmp')/R.GRANT_ID
ROOT_BASE=Path('/private/var/root/fx3-owner-trials')
ROOT_DIR=ROOT_BASE/R.GRANT_ID
TARGET={'locationID':0x01100000,'VID':0x054c,'PID':0x0da1,'model':'ILME-FX3','firmware':'7.02'}

def private_copy(source,expected,directory):
    directory=Path(directory)
    st=directory.lstat()
    if directory.resolve()!=directory or not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:
        raise R.Rejected('private copy directory identity')
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or not 0<st.st_size<=8*1024*1024:raise R.Rejected('source type/links/size')
        data=os.pread(fd,st.st_size+1,0)
        if len(data)!=st.st_size or sha256(data).hexdigest()!=expected:raise R.Rejected('source digest')
    finally:os.close(fd)
    out=directory/'source-helper';fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o500)
    try:
        at=0
        while at<len(data):
            n=os.write(fd,data[at:])
            if n<=0:raise OSError('source copy short write')
            at+=n
        os.fchmod(fd,0o500);os.fsync(fd)
    finally:os.close(fd)
    if sha256(out.read_bytes()).hexdigest()!=expected:raise R.Rejected('private copy digest')
    return out

def bootstrap(source,expected,installed,frame,nonce,*,fixture=False,socket_path=None,guard=None):
    q=lambda x:shlex.quote(str(x))
    if len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected) or len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):
        raise R.Rejected('fixed digest/nonce shape')
    installed=Path(installed);frame=Path(frame);source=Path(source)
    lines=['set -euC','cd /','umask 077']
    if fixture:
        if not installed.is_relative_to(HERE/'runs') or not frame.is_relative_to(HERE/'runs'):raise R.Rejected('fixture paths')
    else:
        if (source,installed,frame)!=(JOB/'source-helper',ROOT_DIR/'helper',JOB/'shared.bin') or socket_path is not None or guard is not None:
            raise R.Rejected('fixed native paths only')
        lines+=['[ "$(/usr/bin/id -u)" = 0 ] || exit 77',
        'if [ ! -e '+q(ROOT_BASE)+' ]; then /bin/mkdir -m 700 '+q(ROOT_BASE)+'; fi',
        '[ ! -L '+q(ROOT_BASE)+' ] && [ -d '+q(ROOT_BASE)+' ] || exit 78',
        '[ "$(/usr/bin/stat -f %u:%Lp '+q(ROOT_BASE)+')" = 0:700 ] || exit 78']
    lines+=['/bin/mkdir -m 700 '+q(installed.parent),
    '/usr/bin/install -m 500 '+q(source)+' '+q(installed),
    'actual=$(/usr/bin/shasum -a 256 '+q(installed)+')',
    '[ "$actual" = '+q(expected+'  '+str(installed))+' ] || exit 78']
    if not fixture:
        permit=json.loads((HERE/'fixed-material.json').read_text())['permit_sha256']
        lines+=['/usr/bin/install -m 400 '+q(JOB/'source-permit')+' '+q(ROOT_DIR/'permit.bin'),
                'actual=$(/usr/bin/shasum -a 256 '+q(ROOT_DIR/'permit.bin')+')',
                '[ "$actual" = '+q(permit+'  '+str(ROOT_DIR/'permit.bin'))+' ] || exit 78']
    argv=[installed,frame,nonce]
    if fixture:
        if socket_path is None or guard is None:raise R.Rejected('fixture socket/guard required')
        argv+=[installed.parent/'entry.once',socket_path,guard]
    lines+=['exec '+' '.join(map(q,argv))+' 2>&1']
    return '\n'.join(lines)+'\n'

def command(body,directory,nonce,*,fixture=False):
    directory=Path(directory);q=lambda x:shlex.quote(str(x))
    if (not fixture and directory!=JOB) or (fixture and not directory.is_relative_to(HERE/'runs')):raise R.Rejected('fixed command directory')
    invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+q(body)
    if not fixture:invocation='/usr/bin/sudo -- '+invocation
    status=json.dumps({'schema':1,'grant_id':R.GRANT_ID,'nonce':nonce,'relay_returncode':'CODE'},separators=(',',':')).replace('"CODE"','%s')+'\n'
    return '\n'.join(['#!/bin/sh','set -euC','cd /','umask 077',
    '/bin/mkdir -m 700 '+q(directory/'terminal-command.once'),
    'if '+invocation+' > '+q(directory/'relay-stdout.txt')+'; then code=0; else code=$?; fi',
    'printf '+q(status)+' "$code" > '+q(directory/'terminal-marker.json'),'exit "$code"',''])

def render_native(nonce):
    raise R.Rejected("native service launch rendering remains closed")
    b=I.build();digest=b['builds']['native']['sha256']
    body=bootstrap(JOB/'source-helper',digest,ROOT_DIR/'helper',JOB/'shared.bin',nonce)
    return command(body,JOB,nonce),body

def native_authority(goal):
    raise R.Rejected("service candidate has no fixed profile or new live approval; no staging")
    # Preserved old renderer is unreachable.
    raw=(HERE/'approval-bundle.json').read_bytes();b=json.loads(raw);digest=sha256(raw).hexdigest()
    if os.getuid()!=501 or os.geteuid()!=501 or b['grant_id']!=R.GRANT_ID or b['scope']!='MSC_OWNER_STATUS_ONLY' or \
       type(b.get('maximum_helper_invocations')) is not int or b.get('maximum_helper_invocations')!=1:
        raise R.Rejected('fixed native authority context')
    expected={'authorized':True,'grant_id':R.GRANT_ID,'bundle_sha256':digest,
      'scope':'MSC_OWNER_STATUS_ONLY','maximum_helper_invocations':1,
      'usb_capture_and_return':True,'sony_vendor_or_file_commands':False}
    given=goal.get('authorization',{}).get('Mac_owner_status12',{})
    if given!=expected or given.get('authorized') is not True or type(given.get('maximum_helper_invocations')) is not int or \
       given.get('usb_capture_and_return') is not True or given.get('sony_vendor_or_file_commands') is not False:
        raise R.Rejected('new exact status-only administrator and USB approval required')
    if goal.get('authorization_consumption',{}).get('Mac_owner_status12',{}).get('consumed'):
        raise R.Rejected('status-only grant consumed')
    for x in b['files']:
        p=HERE/x['path'];data=p.read_bytes()
        if len(data)!=x['bytes'] or sha256(data).hexdigest()!=x['sha256']:raise R.Rejected('approval member changed')
    if JOB.exists():raise R.Rejected('fixed status-only attempt already staged; no retry')
    return b
