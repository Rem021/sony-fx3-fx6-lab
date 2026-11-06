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
GRANT_ID='fx3-702-msc-owner-20261028-04'
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


def native_applescript(nonce):
    build=checked_build();m=build['native']
    body=bootstrap_body(LOCAL_SOURCE,m['sha256'],ROOT_BASE,ROOT_DIR,JOB_DIR/'shared.bin',nonce)
    invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+shlex.quote(body)
    # Inline source prevents reading a mutable external .scpt at launch time.
    # JSON escaping is used only for AppleScript string encoding, never shell.
    script='do shell script '+json.dumps(invocation)+' with administrator privileges without altering line endings'
    return script,body
