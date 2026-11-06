"""Stage once after fresh preflight, consume exact grant, retain original observer."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import json,os,plistlib,subprocess,sys,time
H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1];P=B/'stage261-fixed-port-association-diagnostic01'
sys.path.insert(0,str(P))
import native_factory as N
import fixed_launch as L
import supervisor as S
import receipt_receiver as Q
GP=B/'GOAL_STATUS.json'
def now():return datetime.now(timezone.utc).isoformat()
def save(name,value):S.put(H/name,value)
def canonical_update(before,g):
    if GP.read_bytes()!=before:raise RuntimeError('canonical changed concurrently; no overwrite')
    raw=(json.dumps(g,ensure_ascii=False,indent=2)+'\n').encode();temp=B/('goal-stage262-'+str(os.getpid())+'.tmp')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
    if GP.read_bytes()!=before:raise RuntimeError('canonical changed before replace')
    os.replace(temp,GP)
if __name__=='__main__':
    volume=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    manifest=(P/'final-receipt.json').read_bytes();assert sha256(manifest).hexdigest()=='3ca0cf852646dd35ef943a0ee8f72d6ad8cef9642ecb98b06af17df4a8a9fccb'
    for member in json.loads(manifest)['files']:
        raw=(R/member['path']).read_bytes();assert len(raw)==member['bytes']and sha256(raw).hexdigest()==member['sha256'],member['path']
    before=GP.read_bytes();g=json.loads(before);assert g['latest_stage']==P.name and len(g['requirements'])==16
    save('goal-status-before.json',g)
    try:job=N.prepare_native_session(g)
    except Exception as e:
        save('preflight-denied.json',dict(observed_utc=now(),error=repr(e),Terminal_started=False,root_or_USB_commands=0,automatic_retry=False))
        print(json.dumps(dict(status='PREFLIGHT_DENIED_NO_LAUNCH',error=repr(e))),flush=True);raise SystemExit(2)
    observer=job.ipc.probe(os.getpid());assert observer
    S.put(job.directory/'observer-identity.json',dict(identity=observer.__dict__,snapshot_only_after_restart=True))
    g['updated_utc']=now();g['latest_stage']=H.name
    g['authorization_consumption'][L.AUTH_KEY]=dict(consumed=True,consumed_at='host job creation; root entry lease still independently required',
        grant_id=Q.GRANT_ID,bundle_sha256=g['authorization'][L.AUTH_KEY]['bundle_sha256'],automatic_retry=False,executed_root_helper_count_not_yet_proven=True)
    g['port_association_diagnostic01_execution']=dict(stage=str(H.relative_to(R)),job=str(job.directory),observer=observer.__dict__,
        status='STAGED_BEFORE_TERMINAL',actual_root_or_USB_not_yet_observed=True,firmware_write=False)
    g['research_activity']='Fixed diagnostic01 passed fresh target/physical-port/ejected-volume cached preflight; one host job staged and grant consumed for this attempt. Original observer retained; Terminal/native authentication next. No firmware write; actual Sony progress must come from authenticated stream and independent observations.'
    canonical_update(before,g);save('goal-status-after-staging.json',g)
    save('staging-receipt.json',dict(observed_utc=now(),job=str(job.directory),observer=observer.__dict__,
        cached_preflight=json.loads((job.directory/'cached-preflight.json').read_text()),root_helper_not_yet_verified=True,automatic_retry=False))
    job.runner=subprocess.Popen(['/usr/bin/open','-a','Terminal',str(job.command)],stdin=subprocess.DEVNULL,stdout=job.out,stderr=job.err,close_fds=True)
    job.relay=job.runner
    launch=dict(observed_utc=now(),pid=job.runner.pid,role='Terminal request, not helper identity',automatic_retry=False)
    S.put(job.directory/'launch-request.json',launch);save('launch-request.json',launch)
    print(json.dumps(dict(status='TERMINAL_REQUESTED',job=str(job.directory),observer_pid=os.getpid())),flush=True)
    last=None;unresolved=False
    while True:
        result=job.step();key=json.dumps(result,sort_keys=True)
        if key!=last:
            print(json.dumps(dict(observed_utc=now(),**result)),flush=True);last=key
        if result.get('helper_terminal_observed')or result.get('observer_may_finish'):
            S.put(job.directory/'live-final-summary.json',result);save('live-final-summary.json',dict(observed_utc=now(),**result));job.close_observer();break
        if result.get('status')in('OWNER_RETAINED','UNKNOWN_OBSERVER_ERROR','UNKNOWN_PROCESS_OBSERVATION','UNKNOWN_PROCESS_IDENTITY_CHANGE')and not unresolved:
            S.put(job.directory/'unresolved-summary.json',result);save('unresolved-summary.json',dict(observed_utc=now(),**result));unresolved=True
        time.sleep(.02)
