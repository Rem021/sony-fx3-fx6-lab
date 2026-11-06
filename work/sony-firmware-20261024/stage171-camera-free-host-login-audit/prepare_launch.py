"""Prepare one fixed host-only audit; never inherit camera-trial permission."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import os
import stat
import subprocess

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
GRANT='fx3-host-audit-20261028-01'
JOB=Path('/private/tmp')/GRANT


def put(path,data,mode=0o600):
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write(data);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())


def authorized_payloads():
    goal=json.loads((BASE/'GOAL_STATUS.json').read_text());a=goal['authorization']
    if a.get('Mac_host_login_audit_authorized') is not True or a.get('Mac_host_login_audit_grant_id')!=GRANT:
        raise ValueError('host-only administrator audit lacks its own explicit authorization')
    if os.getuid()!=501 or os.geteuid()!=501:
        raise ValueError('only reviewed console user501 may prepare this audit')
    raw=(HERE/'release-bundle.json').read_bytes()
    if sha256(raw).hexdigest()!=a.get('Mac_host_login_audit_bundle_sha256'):
        raise ValueError('host approval is not bound to this exact bundle')
    payloads={}
    for item in json.loads(raw)['files']:
        data=(HERE/item['path']).read_bytes()
        if sha256(data).hexdigest()!=item['sha256']:raise ValueError('fixed host payload changed')
        payloads[item['path']]=data
    return payloads


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--prepare',action='store_true');g.add_argument('--run-authorized',action='store_true');a=p.parse_args()
    if not (a.prepare or a.run_authorized):
        print(json.dumps({'state':'PLAN_ONLY','grant_id':GRANT,'root_or_camera_operations':0}));return
    data=authorized_payloads() # Before claim, temporary directory or app launch.
    put(HERE/'host-grant-attempt.claim',(json.dumps({'grant_id':GRANT,'one_attempt_consumed_before_staging':True})+'\n').encode())
    JOB.mkdir(mode=0o700,exist_ok=False)
    ds=JOB.lstat()
    if JOB.resolve()!=JOB or ds.st_uid!=501 or stat.S_IMODE(ds.st_mode)!=0o700:
        raise ValueError('private host directory differs')
    put(JOB/'probe',data['artifacts/host-login-probe'],0o500)
    put(JOB/'HostLoginAudit.command',data['HostLoginAudit.command'],0o700)
    for destination,source in [('probe','artifacts/host-login-probe'),('HostLoginAudit.command','HostLoginAudit.command')]:
        if sha256((JOB/destination).read_bytes()).digest()!=sha256(data[source]).digest():
            raise ValueError('internal host copy differs; keep consumed claim')
    put(JOB/'staging-receipt.json',(json.dumps({'grant_id':GRANT,'source_sha256':sha256(data['artifacts/host-login-probe']).hexdigest(),
        'command_sha256':sha256(data['HostLoginAudit.command']).hexdigest(),'camera_operations':0,'privacy_changes':0})+'\n').encode())
    if a.run_authorized:
        # open is only a launch request, never proof of administrator completion.
        result=subprocess.run(['/usr/bin/open','-a','Terminal',str(JOB/'HostLoginAudit.command')],capture_output=True,text=True)
        put(JOB/'terminal-launch-request.json',(json.dumps({'returncode':result.returncode,'stdout':result.stdout[:1024],
            'stderr':result.stderr[:1024],'not_proof_of_root_execution':True})+'\n').encode())
    print(json.dumps({'state':'HOST_AUDIT_STAGED','terminal_requested':a.run_authorized,'grant_id':GRANT,
        'result_directory':str(JOB),'root_completion_not_claimed':True,'camera_operations':0}))


if __name__=='__main__':main()
