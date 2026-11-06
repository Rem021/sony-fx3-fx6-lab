"""Fixed reviewed trial policy and shell staging. This module executes nothing."""
from pathlib import Path
from hashlib import sha256
import json
import shlex
import owner_binding as B

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
GRANT_ID='fx3-702-msc-owner-20261028-01'
JOB_DIR=Path('/private/tmp')/GRANT_ID
ROOT_BASE=Path('/private/var/root/fx3-owner-trials')
ROOT_DIR=ROOT_BASE/GRANT_ID
TARGET={'locationID':0x02100000,'VID':0x054c,'PID':0x0da1,'model':'ILME-FX3','firmware':'7.02'}


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
    lines=['set -eu','umask 077',
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
    body=bootstrap_body(HERE/m['path'],m['sha256'],ROOT_BASE,ROOT_DIR,JOB_DIR/'shared.bin',nonce)
    invocation='/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c '+shlex.quote(body)
    # Inline source prevents reading a mutable external .scpt at launch time.
    # JSON escaping is used only for AppleScript string encoding, never shell.
    script='do shell script '+json.dumps(invocation)+' with administrator privileges without altering line endings'
    return script,body
