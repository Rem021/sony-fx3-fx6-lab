"""Retain one actual Popen handle; timeouts request stop, never kill/restart."""
from pathlib import Path
from hashlib import sha256
import json
import os
import secrets
import subprocess
import sys
import time
import owner_binding as B
from shared_job import FixtureAPI,Shared,checked_build,put_once

HERE=Path(__file__).resolve().parent


def process_identity(pid):
    return subprocess.check_output(['/bin/ps','-ww','-p',str(pid),'-o','lstart=','-o','command='],text=True).strip()


class Job:
    @classmethod
    def start_fixture(cls,directory,options=None,*,work_s=1.0,total_s=3.0):
        if type(work_s) not in (int,float) or type(total_s) not in (int,float) or not 0<work_s<total_s<=10:
            raise B.Rejected('fixture deadlines invalid')
        directory=Path(directory)
        if directory.exists():raise B.Rejected('single-use job path is already consumed')
        checked_build();api=FixtureAPI()
        directory.mkdir(mode=0o700)
        nonce=secrets.token_hex(16)
        put_once(directory/'one-shot.claim',{'nonce':nonce,'consumed_before_spawn':True,'mode':'fixture'})
        shared=Shared(directory/'shared.bin',api,create=True)
        now=time.monotonic_ns()
        spec={'nonce':nonce,'mode':'fixture','shared_identity':shared.identity,'fixture':options or {},
            'work_deadline_ns':now+int(work_s*1e9),'final_deadline_ns':now+int(total_s*1e9),
            'fixture_sha256':api.fixture_sha,'build_sha256':sha256((HERE/'build-receipt.json').read_bytes()).hexdigest()}
        put_once(directory/'spec.json',spec)
        argv=[sys.executable,'-B',str(HERE/'owner_worker.py'),str(directory),nonce]
        log=open(directory/'worker-stderr.log','xb')
        try:
            process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log,
                start_new_session=True,close_fds=True)
        except BaseException:
            shared.close_terminal();raise  # Claim remains consumed; no second spawn.
        finally:log.close()
        birth=None
        if process.poll() is None:
            try:birth=process_identity(process.pid)
            except (OSError,subprocess.CalledProcessError):pass
        interpreters=sorted({str(Path(sys.executable)),str(Path(sys.executable).resolve()),
            str(Path(sys._base_executable).resolve()),str(Path(sys.base_prefix)/'Resources/Python.app/Contents/MacOS/Python')})
        put_once(directory/'process.json',{'nonce':nonce,'pid':process.pid,'birth_identity':birth,'argv':argv,
            'reviewed_interpreters':interpreters})
        self=cls();self.directory=directory;self.spec=spec;self.shared=shared;self.process=process;self.stop_recorded=False
        return self

    @classmethod
    def start_live(cls,*args,**kwargs):
        # A worker supporting only fixtures must never be selected for live I/O.
        # No directory, child, native symbol or library is created on this path.
        B.live_authority(json.loads((HERE.parent/'GOAL_STATUS.json').read_text()))
        raise B.Rejected('real worker/privileged launch and native driver acceptance remain unreleased')

    def request_stop(self):
        self.shared.stop()
        if not self.stop_recorded:
            put_once(self.directory/'stop-request.json',{'nonce':self.spec['nonce'],'requested_at_ns':time.monotonic_ns(),
                'not_native_cancellation_or_recovery_proof':True})
            self.stop_recorded=True

    def poll(self):
        try:code=self.process.poll()
        except OSError as error:
            return {'status':'OBSERVATION_ERROR_UNRESOLVED','verified_worker_alive':False,'error':type(error).__name__,
                'restarted_or_killed':False,'physical_acceptance':False}
        if code is None:
            if time.monotonic_ns()>=self.spec['work_deadline_ns']:self.request_stop()
            progress=self.shared.progress()
            return {'status':'WAITING_NATIVE_RETURN' if progress['active_native_call_phase'] else 'WORKER_RUNNING',
                'verified_worker_alive':True,'verified_by':'same Popen.poll handle','pid':self.process.pid,
                'final_deadline_passed':time.monotonic_ns()>=self.spec['final_deadline_ns'],**progress,
                'restarted_or_killed':False,'physical_acceptance':False}
        path=self.directory/'worker-result.json'
        if code!=0 or not path.is_file():
            return {'status':'UNKNOWN_TERMINAL_WITHOUT_VALID_RECEIPT','returncode':code,
                'worker_terminal_verified':True,'restarted_or_killed':False,'physical_acceptance':False}
        try:
            receipt=json.loads(path.read_text())
            valid=receipt['nonce']==self.spec['nonce'] and receipt['mode']=='fixture' and receipt['pid']==self.process.pid and \
                receipt['fixture_sha256']==self.spec['fixture_sha256'] and receipt['build_sha256']==self.spec['build_sha256'] and \
                receipt['native_function_returned'] is True and receipt['native_result_sha256']==sha256(self.shared.result_bytes()).hexdigest()
            native=self.shared.result_copy();public=B.public_result(native)
            valid=valid and native.status in (0,1,2,3) and native.active_call_pending==0 and receipt['native_return']==native.status and receipt['result']==public
            if not valid:raise B.Rejected('terminal receipt differs')
        except (KeyError,ValueError,TypeError):
            return {'status':'UNKNOWN_TERMINAL_RECEIPT_MISMATCH','returncode':code,'worker_terminal_verified':True,
                'restarted_or_killed':False,'physical_acceptance':False}
        names={0:'PROVIDER_OBSERVATION_COMPLETED',1:'PROVIDER_ABORTED_OBSERVATION',2:'UNKNOWN_PROVIDER_STATE',3:'PROVIDER_DENIED'}
        return {'status':names[native.status],'worker_terminal_verified':True,'native_function_return_verified':True,
            'returncode':code,'native':public,'calls':receipt['calls'],'restarted_or_killed':False,'physical_acceptance':False}

    def close_terminal(self):
        if self.process.poll() is None:raise B.Rejected('cannot close observer mapping while worker is alive')
        self.shared.close_terminal()


def observe_recorded(directory):
    """An existing record alone is insufficient; confirm current PID incarnation."""
    directory=Path(directory)
    spec=json.loads((directory/'spec.json').read_text());process=json.loads((directory/'process.json').read_text())
    if process['nonce']!=spec['nonce'] or not process['birth_identity']:
        return {'status':'UNRESOLVED_PROCESS_IDENTITY','verified_worker_alive':False,'restarted':False}
    try:current=process_identity(process['pid'])
    except subprocess.CalledProcessError:
        return {'status':'RECORDED_PROCESS_MISSING_ACCEPTANCE_UNKNOWN','verified_worker_alive':False,'restarted':False}
    except OSError:
        return {'status':'OBSERVATION_ERROR_UNRESOLVED','verified_worker_alive':False,'restarted':False}
    first=process['birth_identity'].split(maxsplit=5);now=current.split(maxsplit=5)
    if len(first)!=6 or len(now)!=6:
        return {'status':'UNRESOLVED_PROCESS_IDENTITY','verified_worker_alive':False,'restarted':False}
    expected_tail=' '.join(process['argv'][1:])
    allowed_commands=[interpreter+' '+expected_tail for interpreter in process.get('reviewed_interpreters',[])]
    matching=first[:5]==now[:5] and now[5] in allowed_commands and process['argv'][-1]==spec['nonce'] and \
        process['argv'][2]==str(HERE/'owner_worker.py') and process['argv'][3]==str(directory)
    return {'status':'RECORDED_WORKER_LIVE' if matching else 'PROCESS_IDENTITY_DIFFERS',
        'verified_worker_alive':matching,'verified_by':'current ps birth and full argv including nonce' if matching else None,
        'pid':process['pid'],'restarted':False,'physical_acceptance':False}
