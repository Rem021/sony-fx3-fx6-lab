"""Supervise the actual helper independently of its administrator relay.

Never kill, retry, unmount, reset or interpret missing observations as recovery.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import argparse
import json
import os
import secrets
import subprocess
import time
import entry_binding as E
import launch_policy as P
import cache_observer as Cache

HERE=Path(__file__).resolve().parent


def put(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def clock_ns():return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def observe_recorded(directory):
    """No spawn or ACK. Recheck the previously verified actual PID incarnation.

    This reports process lifetime and result consistency only; it does not add
    independent driver acceptance or claim that a live root trial succeeded.
    """
    directory=Path(directory);spec=json.loads((directory/'spec.json').read_text())
    proof_path=directory/'verified-helper.json'
    if not proof_path.exists():return {'status':'UNKNOWN_ENTRY_NEVER_VERIFIED','verified_helper_alive':False,'restarted':False}
    proof=json.loads(proof_path.read_text());ipc=E.IPC();frame=E.Frame.attach(directory/'shared.bin',ipc)
    try:
        if proof['nonce']!=spec['nonce'] or frame.nonce.hex()!=spec['nonce'] or proof['grant_id']!=spec['grant_id']:
            return {'status':'UNKNOWN_RECORDED_IDENTITY_MISMATCH','verified_helper_alive':False,'restarted':False}
        try:current=ipc.identity(proof['identity']['pid'])
        except OSError:return {'status':'OBSERVATION_ERROR_UNRESOLVED','verified_helper_alive':False,'restarted':False}
        if current is not None:
            same=current==proof['identity']
            return {'status':'RECORDED_HELPER_LIVE' if same else 'UNKNOWN_PID_IDENTITY_DIFFERS',
                'verified_helper_alive':same,'verified_by':'current kernel PID, UID, birth and executable path' if same else None,
                'active_native_call_phase':frame.pending(),'restarted':False,'physical_acceptance':False}
        value={'status':'RECORDED_HELPER_TERMINAL_RESULT_UNKNOWN','helper_terminal_verified':True,
            'verified_helper_alive':False,'restarted':False,'physical_acceptance':False}
        if not frame.completed():return value
        try:
            path=directory/'relay-stdout.txt'
            if path.stat().st_size>16384:raise ValueError('receipt exceeds bound')
            receipt=json.loads(path.read_text());result=frame.result();identity=proof['identity']
            valid=receipt['schema']==2 and receipt['mode']==spec['mode'] and receipt['grant_id']==spec['grant_id'] and \
                receipt['nonce']==spec['nonce'] and receipt['pid']==identity['pid'] and \
                (receipt['birth_sec'],receipt['birth_usec'])==(identity['birth_sec'],identity['birth_usec']) and \
                receipt['result_sha256']==bytes(frame.grant.result_sha256).hex()==sha256(frame.result_bytes()).hexdigest() and \
                receipt['native_return']==frame.grant.native_return==result.status and result.abi==3 and result.active_call_pending==0
            if valid:value.update(status='RECORDED_HELPER_TERMINAL_RESULT_CONSISTENT',native=E.B.public_result(result))
        except (OSError,KeyError,ValueError,TypeError):pass
        return value
    finally:
        # This observer has no native call; helper owns its separate mapping.
        frame.terminal=True;frame.close_terminal()


class Job:
    @classmethod
    def _spawn(cls,directory,frame,argv,expected_path,*,mode,before=None,key=None,goal=None):
        self=cls();self.directory=Path(directory);self.frame=frame;self.expected_path=str(expected_path)
        self.mode=mode;self.before=before;self.key=key;self.goal=goal;self.identity=None;self.final=None
        self.ack_sent=False;self.after_collected=False
        self.out_path=self.directory/'relay-stdout.txt';self.err_path=self.directory/'relay-stderr.txt'
        put(self.directory/'spec.json',{'schema':2,'grant_id':P.GRANT_ID,'mode':mode,'nonce':frame.nonce.hex(),
            'expected_path':self.expected_path,'expected_uid':os.getuid() if mode=='fixture' else 0,
            'clock_domain':'CLOCK_MONOTONIC','created_utc':datetime.now(timezone.utc).isoformat()})
        with self.out_path.open('xb') as out,self.err_path.open('xb') as err:
            self.relay=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
        put(self.directory/'relay-process.json',{'pid':self.relay.pid,'nonce':frame.nonce.hex(),
            'role':'relay; not accepted as helper identity','argv':argv if mode=='fixture' else ['/usr/bin/osascript','-e','fixed inline reviewed source']})
        return self

    @classmethod
    def start_fixture(cls,directory,*,block_phase=0,expected_tag=None,observed_tag=None,expected_path=None,bad_digest=False,stage_dir=None):
        build=P.checked_build();directory=Path(directory);directory.mkdir(mode=0o700,exist_ok=False)
        put(directory/'physical-grant-attempt.claim',{'fixture':True,'single_attempt':True})
        ipc=E.IPC();frame=E.Frame(directory/'shared.bin',ipc,block_phase=block_phase,expected_tag=expected_tag,observed_tag=observed_tag)
        stage=Path(stage_dir) if stage_dir is not None else directory/'staged-grant'
        m=build['fixture'];body=P.bootstrap_body(HERE/m['path'],'00'*32 if bad_digest else m['sha256'],
            stage.parent,stage,frame.path,frame.nonce.hex(),fixture=True,lease=stage/'entry.once')
        argv=['/usr/bin/env','-i','PATH=/usr/bin:/bin:/usr/sbin:/sbin','/bin/sh','-c',body]
        return cls._spawn(directory,frame,argv,expected_path or stage/'helper',mode='fixture')

    @classmethod
    def start_live(cls):
        goal=json.loads((HERE.parent/'GOAL_STATUS.json').read_text())
        P.live_authority(goal) # Before a frame, cache query, process or prompt.
        build=P.checked_build()
        put(HERE/'physical-grant-attempt.claim',{'grant_id':P.GRANT_ID,'bundle_sha256':goal['authorization']['Mac_owner_trial_bundle_sha256'],
            'consumed_before_preflight_or_prompt':True})
        # Fixed internal temporary directory; no camera volume is unmounted.
        P.JOB_DIR.mkdir(mode=0o700,exist_ok=False)
        key=secrets.token_bytes(32);before=Cache.collect(Cache.TARGET,key,goal)
        put(P.JOB_DIR/'cache-before.json',before)
        if before['selected_count']!=1:raise E.B.Rejected('cached target missing or ambiguous')
        selected=before['selected'][0]
        if not selected['cached_identity_usable'] or not selected['MSC_interface0_observed'] or not selected['storage_driver_classes']:
            raise E.B.Rejected('cached body, MSC or baseline driver unavailable')
        ipc=E.IPC();frame=E.Frame(P.JOB_DIR/'shared.bin',ipc,mode=0,key=key,expected_tag=bytes.fromhex(selected['body_tag']))
        script,body=P.native_applescript(frame.nonce.hex())
        put(P.JOB_DIR/'launch-review.json',{'native_sha256':build['native']['sha256'],'grant_id':P.GRANT_ID,
            'script_sha256':sha256(script.encode()).hexdigest(),'bootstrap_sha256':sha256(body.encode()).hexdigest()})
        return cls._spawn(P.JOB_DIR,frame,['/usr/bin/osascript','-e',script],P.ROOT_DIR/'helper',mode='live',before=before,key=key,goal=goal)

    def request_stop(self):
        self.frame.stop()
        p=self.directory/'stop-request.json'
        if not p.exists():put(p,{'nonce':self.frame.nonce.hex(),'at_ns':clock_ns(),'native_cancellation_or_recovery':False})

    def _identity(self):
        g=self.frame.grant
        current=self.frame.ipc.identity(g.native_pid)
        expected={'pid':g.native_pid,'uid':os.getuid() if self.mode=='fixture' else 0,
            'birth_sec':g.birth_sec,'birth_usec':g.birth_usec,'path':self.expected_path}
        return current,expected

    def poll(self,*,allow_ack=True):
        if self.final is not None:return self.final
        try:relay_code=self.relay.poll()
        except OSError:
            return {'status':'OBSERVATION_ERROR_UNRESOLVED','restarted_or_killed':False,'physical_acceptance':False}
        g=self.frame.grant;helper_alive=False
        if self.frame.ready():
            try:current,expected=self._identity()
            except OSError:
                return {'status':'HELPER_OBSERVATION_ERROR_UNRESOLVED','relay_alive':relay_code is None,
                    'verified_helper_alive':False,'restarted_or_killed':False,'physical_acceptance':False}
            if current is not None:
                if current!=expected or (self.identity is not None and current!=self.identity):
                    self.request_stop()
                    return {'status':'HELPER_IDENTITY_DIFFERS_UNKNOWN','verified_helper_alive':False,
                        'relay_alive':relay_code is None,'restarted_or_killed':False,'physical_acceptance':False}
                helper_alive=True
                if self.identity is None:
                    self.identity=current
                    put(self.directory/'verified-helper.json',{'nonce':self.frame.nonce.hex(),'grant_id':P.GRANT_ID,'identity':current})
                if allow_ack and not self.ack_sent:
                    self.frame.ack();self.ack_sent=True
        if g.started_ns and clock_ns()>=g.work_deadline_ns:self.request_stop()
        if helper_alive or relay_code is None:
            return {'status':'HELPER_RUNNING' if helper_alive else 'RELAY_RUNNING_HELPER_UNCONFIRMED',
                'verified_helper_alive':helper_alive,'relay_alive':relay_code is None,
                'verified_by':'current kernel PID, UID, birth and executable path' if helper_alive else 'same relay Popen handle only',
                'native_started':bool(g.native_started),'native_function_completed':self.frame.completed(),
                'parent_ack_sent':self.ack_sent,'active_native_call_phase':self.frame.pending(),
                'final_deadline_passed':bool(g.final_deadline_ns and clock_ns()>=g.final_deadline_ns),
                'restarted_or_killed':False,'physical_acceptance':False}
        # The relay is terminal and no matching helper is observed. Root state
        # is still UNKNOWN without a previously verified helper and final data.
        if self.identity is None or not self.frame.completed():
            if self.mode=='fixture' or self.identity is not None:self.frame.terminal=True
            return {'status':'UNKNOWN_TERMINAL_WITHOUT_VERIFIED_HELPER_RECEIPT','relay_returncode':relay_code,
                'helper_terminal_verified':self.identity is not None,'restarted_or_killed':False,'physical_acceptance':False}
        self.frame.terminal=True
        try:
            if self.out_path.stat().st_size>16384:raise ValueError('relay receipt exceeds bound')
            r=json.loads(self.out_path.read_text());result=self.frame.result()
            same=relay_code==0 and r['schema']==2 and r['grant_id']==P.GRANT_ID and r['mode']==self.mode and \
                r['nonce']==self.frame.nonce.hex() and r['pid']==self.identity['pid'] and \
                (r['birth_sec'],r['birth_usec'])==(self.identity['birth_sec'],self.identity['birth_usec']) and \
                r['native_return']==g.native_return==result.status and result.abi==3 and result.event_count<=64 and \
                result.active_call_pending==0 and r['result_sha256']==bytes(g.result_sha256).hex()==sha256(self.frame.result_bytes()).hexdigest()
            if not same:raise ValueError('receipt mismatch')
        except (KeyError,ValueError,TypeError):
            return {'status':'UNKNOWN_TERMINAL_RECEIPT_MISMATCH','helper_terminal_verified':True,
                'restarted_or_killed':False,'physical_acceptance':False}
        self.frame.terminal=True
        status={0:'PROVIDER_OBSERVATION_COMPLETED',1:'PROVIDER_ABORTED_OBSERVATION',2:'UNKNOWN_PROVIDER_STATE',3:'PROVIDER_DENIED'}.get(result.status,'UNKNOWN_PROVIDER_STATE')
        value={'status':status,'helper_terminal_verified':True,'helper_identity':self.identity,'relay_returncode':relay_code,
            'native':E.B.public_result(result),'receipt':r,'restarted_or_killed':False,'physical_acceptance':False}
        if self.mode=='live' and not self.after_collected:
            self.after_collected=True
            try:
                after=Cache.collect(Cache.TARGET,self.key,self.goal);put(self.directory/'cache-after.json',after)
                comparison=Cache.compare(self.before,after,bytes(result.before.body_tag).hex(),bytes(result.after.body_tag).hex())
                put(self.directory/'independent-cache-comparison.json',comparison);value['independent_cache']=comparison
                if not comparison['same_cached_body_and_driver_association_observed']:value['status']='UNKNOWN_INDEPENDENT_DRIVER_ASSOCIATION'
            except (OSError,ValueError,subprocess.SubprocessError):value['status']='UNKNOWN_INDEPENDENT_CACHE_OBSERVATION'
        put(self.directory/'supervisor-result.json',value);self.final=value
        return value

    def close_terminal(self):self.frame.close_terminal()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-live',action='store_true');args=p.parse_args()
    if not args.run_live:
        print(json.dumps({'state':'PLAN_ONLY','grant_id':P.GRANT_ID,'new_device_operations':0}));return
    job=Job.start_live()
    try:
        while True:
            state=job.poll()
            if state.get('helper_terminal_verified'):print(json.dumps(state));job.close_terminal();return
            # An uncertain exit cannot be silently converted into retry/cleanup.
            if state['status'].startswith('UNKNOWN_TERMINAL'):
                print(json.dumps(state));return
            time.sleep(.02)
    except (KeyboardInterrupt,SystemExit):
        job.request_stop()
        while True:
            state=job.poll(allow_ack=False)
            if state.get('helper_terminal_verified'):job.close_terminal();return
            if state['status'].startswith('UNKNOWN_TERMINAL'):return
            time.sleep(.02)


if __name__=='__main__':main()
