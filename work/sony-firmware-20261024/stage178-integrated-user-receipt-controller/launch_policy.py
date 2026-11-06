"""Fixed reviewed trial policy and shell staging. This module executes nothing."""
from pathlib import Path
from hashlib import sha256
import json
import os
import shlex
import stat
import owner_binding as B

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
GRANT_ID='fx3-702-msc-owner-20261029-06'
JOB_DIR=Path('/private/tmp')/GRANT_ID
LOCAL_SOURCE=JOB_DIR/'source-helper'
ROOT_BASE=Path('/private/var/root/fx3-owner-trials')
ROOT_DIR=ROOT_BASE/GRANT_ID
TARGET={'locationID':0x02100000,'VID':0x054c,'PID':0x0da1,'model':'ILME-FX3','firmware':'7.02'}


def stage_source(source,digest,directory):
    """User-only, exclusive internal copy. Never execute or remove a failed copy.

    The administrator must still verify its own installed copy independently.
    """
    if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise B.Rejected('invalid source digest')
    directory=Path(directory)
    if directory.resolve(strict=True)!=directory or not directory.is_relative_to(Path('/private/tmp')):
        raise B.Rejected('literal private internal directory required')
    parent=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        ds=os.fstat(parent)
        if not stat.S_ISDIR(ds.st_mode) or ds.st_uid!=os.getuid() or stat.S_IMODE(ds.st_mode)!=0o700:
            raise B.Rejected('private directory owner or permissions differ')
        source_fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            ss=os.fstat(source_fd)
            if not stat.S_ISREG(ss.st_mode) or ss.st_nlink!=1 or not 0<ss.st_size<=8*1024*1024:
                raise B.Rejected('source type, links or size rejected')
            data=bytearray()
            while len(data)<=ss.st_size:
                chunk=os.read(source_fd,min(65536,ss.st_size+1-len(data)))
                if not chunk:break
                data.extend(chunk)
            if len(data)!=ss.st_size or sha256(data).hexdigest()!=digest:
                raise B.Rejected('source digest differs before private copy')
        finally:os.close(source_fd)
        fd=os.open('source-helper',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        try:
            at=0
            while at<len(data):
                n=os.write(fd,memoryview(data)[at:])
                if n<=0:raise OSError('short private-stage write')
                at+=n
            os.fchmod(fd,0o500);os.fsync(fd)
            saved=os.fstat(fd);os.lseek(fd,0,os.SEEK_SET)
            copied=bytearray()
            while len(copied)<len(data):
                chunk=os.read(fd,min(65536,len(data)-len(copied)))
                if not chunk:break
                copied.extend(chunk)
            if not stat.S_ISREG(saved.st_mode) or saved.st_uid!=os.getuid() or saved.st_nlink!=1 or \
                    stat.S_IMODE(saved.st_mode)!=0o500 or saved.st_size!=len(data) or sha256(copied).hexdigest()!=digest:
                raise B.Rejected('private copy identity or digest differs')
        finally:os.close(fd)
    finally:os.close(parent)
    return {'path':str(directory/'source-helper'),'sha256':digest,'bytes':len(data),
        'uid':os.getuid(),'directory_mode':'0700','file_mode':'0500',
        'exclusive_no_follow_copy':True,'native_executed':False}


def checked_build():
    build=json.loads((HERE/'helper-build-receipt.json').read_text())
    for m in build['sources']:
        if sha256((HERE/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise B.Rejected('source differs from fixed build')
    for k in ['native','fixture','ipc']:
        m=build[k]
        if sha256((HERE/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise B.Rejected('compiled artifact differs')
    return build


def live_authority(goal):
    a,p=goal['authorization'],goal['prepared_first_device_trial']
    if os.getuid()!=501 or os.geteuid()!=501:
        raise B.Rejected('reviewed console user501 required')
    if a.get('Mac_owner_trial_terminal_launch_authorized') is not True:
        raise B.Rejected('new fixed Terminal/sudo camera launch lacks its own explicit authorization')
    if not all(a.get(k) is True for k in ['Mac_owner_trial_authorized','Mac_owner_trial_admin_launch_authorized','driver_change']):
        raise B.Rejected('no separate device/driver/administrator trial authorization')
    if p.get('Mac_owner_trial_released') is not True or a.get('Mac_owner_trial_grant_id')!=GRANT_ID or a.get('Mac_owner_trial_target')!=TARGET:
        raise B.Rejected('fixed trial release, grant or target missing')
    raw=(HERE/'release-bundle.json').read_bytes()
    if a.get('Mac_owner_trial_bundle_sha256')!=sha256(raw).hexdigest():raise B.Rejected('approval is not tied to the reviewed bundle')
    bundle=json.loads(raw)
    for m in bundle['files']:
        if sha256((HERE/m['path']).read_bytes()).hexdigest()!=m['sha256']:raise B.Rejected('reviewed release member changed')
    checked_build()


def bootstrap_body(source,digest,root_base,root_dir,frame,nonce,*,fixture=False,lease=None):
    # The fixture branch is only a non-IOKit shell fixture. Actual native calls
    # have fixed paths and the exact compiled SHA from the released build.
    if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise B.Rejected('invalid executable digest')
    if len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):raise B.Rejected('invalid nonce')
    q=lambda p:shlex.quote(str(p))
    executable=Path(root_dir)/'helper'
    install=['/usr/bin/install','-m','500']
    if not fixture:install+=['-o','root','-g','wheel']
    lines=['set -eu','cd /','umask 077',
        '/bin/mkdir -p -m 700 '+q(root_base),
        '/bin/mkdir -m 700 '+q(root_dir),
        ' '.join(map(q,install+[source,executable])),
        'actual=$(/usr/bin/shasum -a 256 '+q(executable)+')',
        '[ "$actual" = '+q(digest+'  '+str(executable))+' ] || exit 78']
    args=[executable,frame,nonce]
    if fixture:
        if lease is None:raise B.Rejected('fixture lease required')
        args.append(lease)
    lines.append('exec '+' '.join(map(q,args)))
    return '\n'.join(lines)+'\n'


def render_terminal_command(nonce,body,directory,*,fixture=False):
    if len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):
        raise B.Rejected('invalid nonce')
    directory=Path(directory)
    if fixture:
        if not directory.is_relative_to(HERE/'runs'):
            raise B.Rejected('own fixture directory required')
    elif directory!=JOB_DIR:raise B.Rejected('fixed native job required')
    q=lambda value:shlex.quote(str(value))
    invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+q(body)
    if not fixture:invocation='/usr/bin/sudo -- '+invocation
    status_format=json.dumps({'schema':1,'grant_id':GRANT_ID,'nonce':nonce,'returncode':'CODE'},separators=(',',':')).replace('"CODE"','%s')+'\n'
    return '\n'.join(['#!/bin/sh','set -euC','cd /','umask 077',
        '/bin/mkdir -m 700 '+q(directory/'terminal-command.once'),
        'printf "%s\\n" '+q('固定单次诊断；如需 sudo 验证，请在本机完成。' if not fixture else 'Own user fixture only.'),
        'if '+invocation+' > '+q(directory/'relay-stdout.txt')+'; then',
        '    code=0','else','    code=$?','fi',
        'printf '+q(status_format)+' "$code" > '+q(directory/'terminal-command-result.json'),
        'exit "$code"',''])


def native_terminal(nonce):
    """Only stdout is redirected by the user shell; sudo verification stays on TTY.

    The helper stderr joins its inherited stdout inside the fixed bootstrap.
    This preserves user501/0600 result ownership without chmod/chown or new
    privacy permissions. Non-JSON errors remain unknown, never successful data.
    """
    build=checked_build();m=build['native']
    body=bootstrap_body(LOCAL_SOURCE,m['sha256'],ROOT_BASE,ROOT_DIR,JOB_DIR/'shared.bin',nonce)
    body=body.replace('set -eu\n','set -euC\n',1).rstrip()+' 2>&1\n'
    return render_terminal_command(nonce,body,JOB_DIR),body


def stage_terminal_command(command,directory):
    directory=Path(directory);st=directory.lstat()
    if directory!=JOB_DIR or directory.resolve()!=directory or not stat.S_ISDIR(st.st_mode) or \
            st.st_uid!=501 or stat.S_IMODE(st.st_mode)!=0o700:
        raise B.Rejected('fixed private Terminal job directory required')
    data=command.encode('utf-8');path=directory/'OwnerTrial.command'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(data);f.flush();os.fchmod(f.fileno(),0o700);os.fsync(f.fileno())
    if sha256(path.read_bytes()).digest()!=sha256(data).digest():
        raise B.Rejected('private Terminal command copy differs')
    return path


def terminal_returncode(directory,nonce):
    """Read a bounded completion marker, never Terminal UI or credentials."""
    path=Path(directory)/'terminal-command-result.json'
    try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:return None
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1 or \
                stat.S_IMODE(st.st_mode)!=0o600 or not 0<st.st_size<=2048:
            raise OSError('Terminal completion marker identity/size differs; outcome unknown')
        data=f.read(2049)
    try:r=json.loads(data)
    except (ValueError,UnicodeError) as error:raise OSError('Terminal completion marker incomplete; outcome unknown') from error
    if type(r) is not dict or set(r)!={'schema','grant_id','nonce','returncode'} or \
            type(r['schema']) is not int or r['schema']!=1 or r['grant_id']!=GRANT_ID or r['nonce']!=nonce or \
            type(r['returncode']) is not int or not 0<=r['returncode']<=255:
        raise OSError('Terminal completion marker grant/nonce/result differs; outcome unknown')
    return r['returncode']


def valid_host_login(r):
    try:
        integers=['schema','getauid_return','getaudit_return','security_session_return','audit_uid',
                  'audit_record_uid','audit_session_id','security_session_id','security_session_attributes']
        return type(r) is dict and all(type(r[k]) is int for k in integers) and r['schema']==1 and \
            r['getauid_return']==r['getaudit_return']==r['security_session_return']==0 and \
            r['audit_uid']==r['audit_record_uid']==501 and \
            0<r['audit_session_id']<0xffffffff and r['audit_session_id']==r['security_session_id'] and \
            r['has_graphic_access'] is True and r['has_tty'] is True and r['is_remote'] is False
    except (KeyError,TypeError):return False


class ReceiptRejected(ValueError):
    def __init__(self,category,**metadata):
        self.category=category;self.metadata=metadata
        super().__init__(category)


def receipt_error_info(error):
    return {'category':getattr(error,'category','receipt_fields_or_read_error'),
        'exception_type':type(error).__name__,'errno':getattr(error,'errno',None),
        'metadata':getattr(error,'metadata',{})}


def read_helper_receipt(directory):
    """Read a single private user-owned result; never broaden read permissions."""
    path=Path(directory)/'relay-stdout.txt';initial=path.lstat()
    if not stat.S_ISREG(initial.st_mode) or initial.st_uid!=os.getuid() or initial.st_nlink!=1 or \
            stat.S_IMODE(initial.st_mode)!=0o600 or not 0<initial.st_size<=16384:
        raise ReceiptRejected('helper_receipt_file_identity_or_size',uid=initial.st_uid,
            mode=oct(stat.S_IMODE(initial.st_mode)),bytes=initial.st_size)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        checked=os.fstat(f.fileno())
        identity=lambda s:(s.st_dev,s.st_ino,s.st_uid,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns)
        if identity(checked)!=identity(initial):raise ReceiptRejected('helper_receipt_changed_before_read')
        data=f.read(16385);after=os.fstat(f.fileno())
        if identity(after)!=identity(checked) or len(data)!=checked.st_size:
            raise ReceiptRejected('helper_receipt_changed_during_read')
    try:r=json.loads(data)
    except (ValueError,UnicodeError) as error:raise ReceiptRejected('helper_receipt_not_JSON') from error
    if type(r) is not dict:raise ReceiptRejected('helper_receipt_not_object')
    return r


