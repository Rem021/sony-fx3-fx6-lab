"""Dispatch the already approved fixed package once; retain its live observer."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess,sys,time
H=Path(__file__).resolve().parent;B=H.parent;ROOT=B.parents[1]
P=B/'stage268-fixed-manual-recovered-communication02'
sys.path.insert(0,str(P))
import native_factory as N
import fixed_launch as L
import supervisor as S
import receipt_receiver as Q
GP=B/'GOAL_STATUS.json'
DIGEST='6fd06531682f9a34c53626bd9bbc5b7ce7f50c6d35ae4b6a182cefe9747ae8e0'
def now():return datetime.now(timezone.utc).isoformat()
def save(name,value):S.put(H/name,value)
def canonical_update(before,value):
    if GP.read_bytes()!=before:raise RuntimeError('canonical changed concurrently; no overwrite')
    temporary=B/('goal-stage269-'+str(os.getpid())+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb')as f:
        f.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
    if GP.read_bytes()!=before:raise RuntimeError('canonical changed before replace')
    os.replace(temporary,GP)
if __name__=='__main__':
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    assert sha256((P/'approval-bundle.json').read_bytes()).hexdigest()==DIGEST
    before=GP.read_bytes();g=json.loads(before);assert len(g['requirements'])==16
    save('goal-status-before-staging.json',g)
    try:job=N.prepare_native_session(g)
    except Exception as e:
        save('prepare-denied.json',dict(recorded_utc=now(),error=repr(e),job_exists=L.JOB.exists(),
            Terminal_started=False,automatic_retry=False,new_root_or_USB_operations=0))
        if L.JOB.exists():
            g['authorization_consumption'][L.AUTH_KEY]=dict(consumed=True,grant_id=Q.GRANT_ID,bundle_sha256=DIGEST,
                consumed_at='partial host staging; no retry',root_helper_not_started=True)
            canonical_update(before,g)
        print(json.dumps(dict(status='PREPARE_DENIED_NO_LAUNCH',error=repr(e))),flush=True);raise SystemExit(2)
    observer=job.ipc.probe(os.getpid());assert observer
    S.put(job.directory/'observer-identity.json',dict(identity=observer.__dict__,snapshot_only_after_restart=True))
    g['updated_utc']=now();g['latest_stage']=H.name
    g['authorization_consumption'][L.AUTH_KEY]=dict(consumed=True,
        consumed_at='host job creation; root entry independently one-shot',grant_id=Q.GRANT_ID,
        bundle_sha256=DIGEST,automatic_retry=False,root_helper_execution_not_yet_observed=True)
    g['recovered_communication02_execution']=dict(stage=str(H.relative_to(ROOT)),job=str(job.directory),
        observer=observer.__dict__,status='STAGED_BEFORE_TERMINAL',root_helper_not_yet_observed=True,firmware_write=False)
    g['fixed_manual_recovered_communication_268'].update(authorized=True,consumed=True,actual_job_staged=True)
    canonical_update(before,g);save('goal-status-after-staging.json',g)
    save('staging-receipt.json',dict(recorded_utc=now(),job=str(job.directory),observer=observer.__dict__,
        cached_preflight=json.loads((job.directory/'cached-preflight.json').read_text()),
        fixed_bundle_sha256=DIGEST,automatic_retry=False))
    job.runner=subprocess.Popen(['/usr/bin/open','-a','Terminal',str(job.command)],stdin=subprocess.DEVNULL,
        stdout=job.out,stderr=job.err,close_fds=True)
    job.relay=job.runner
    launch=dict(recorded_utc=now(),pid=job.runner.pid,role='Terminal request, not helper identity',automatic_retry=False)
    S.put(job.directory/'launch-request.json',launch);save('launch-request.json',launch)
    print(json.dumps(dict(status='TERMINAL_REQUESTED',job=str(job.directory),observer_pid=os.getpid())),flush=True)
    last=None;unresolved=False
    while True:
        result=job.step();frames=len(getattr(job,'flow_frames',[]))
        key=json.dumps(dict(result=result,flow_frames=frames),sort_keys=True)
        if key!=last:
            print(json.dumps(dict(recorded_utc=now(),flow_frames=frames,**result)),flush=True);last=key
        if result.get('helper_terminal_observed')or result.get('observer_may_finish'):
            S.put(job.directory/'live-final-summary.json',result)
            save('live-final-summary.json',dict(recorded_utc=now(),flow_frames=frames,**result))
            job.close_observer();break
        if result.get('status')in('OWNER_RETAINED','UNKNOWN_OBSERVER_ERROR','UNKNOWN_PROCESS_OBSERVATION_ERROR','UNKNOWN_PROCESS_IDENTITY_CHANGE')and not unresolved:
            S.put(job.directory/'unresolved-summary.json',result)
            save('unresolved-summary.json',dict(recorded_utc=now(),**result));unresolved=True
        time.sleep(.02)
