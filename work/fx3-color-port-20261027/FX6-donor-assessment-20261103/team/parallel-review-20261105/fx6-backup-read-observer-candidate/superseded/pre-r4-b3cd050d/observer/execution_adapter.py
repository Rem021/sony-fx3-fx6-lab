#!/usr/bin/env python3
"""Offline-testable lifecycle adapter. It never starts or connects to a VM here."""
import hashlib,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import baseline_binding
TOTAL_SECONDS=180; OBSERVE_SECONDS=150
class Adapter:
    def __init__(self,plan,run_root,qmp,qemu,rsp,locks,observer,inherited_cleanup=None,clock=time.monotonic):
        self.plan=plan;self.run_root=Path(run_root);self.qmp=qmp;self.qemu=qemu;self.rsp=rsp;self.locks=locks;self.observer=observer
        self.inherited_cleanup=inherited_cleanup;self.clock=clock;self.start_time=None;self.observe_deadline=None;self.calls=[]
    def prepare(self):
        baseline_binding.verify_artifacts()
        if hashlib.sha256(Path(self.plan['appfw_path']).read_bytes()).hexdigest()!=self.plan['appfw_sha256']:raise RuntimeError('APP_ELF hash drift')
        if hashlib.sha256(Path(self.plan['target_cpio_path']).read_bytes()).hexdigest()!=self.plan['target_cpio_sha256']:raise RuntimeError('target CPIO hash drift')
        if self.plan.get('baseline_sha256')!='854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669':raise RuntimeError('baseline hash drift')
        if self.run_root.exists() and any(self.run_root.iterdir()):raise RuntimeError('run root must be new/private')
        self.run_root.mkdir(parents=True,exist_ok=True);self.run_root.chmod(0o700)
        serial=self.run_root/'serial.log'
        with serial.open('x'):pass
        args=list(self.plan['qemu_argv']);old=list(args)
        args[20]='file:'+str(serial);args[31]=self.plan['new_initrd']
        if len(args)!=34:raise RuntimeError('argv count')
        if any(args[i]!=old[i] for i in range(34) if i not in (20,31)):raise RuntimeError('non-private argv delta')
        if args[20]==old[20] or str(serial)==self.plan.get('old_serial'):raise RuntimeError('old serial reused')
        self.args=args;(self.run_root/'command.json').write_text(json.dumps({'args':args,'cwd':str(self.run_root),'private_serial':str(serial),'target_cpio':self.plan.get('target_cpio_sha256'),'policy':'zero keys; one start; no guest write'},indent=2)+'\n')
        return {'args':args,'serial':str(serial),'run_root':str(self.run_root)}
    def arm(self):
        self.start_time=self.clock();self.observe_deadline=self.start_time+OBSERVE_SECONDS
        self.qmp.call('stop');st=self.qmp.call('query-status')
        if st.get('status')!='paused':raise RuntimeError('QMP did not pause all CPUs')
        self.calls.append('qmp_stop_confirmed');self.observer.arm();self.calls.append('z1_armed')
    def consume(self,stop):
        if self.clock()>self.observe_deadline:raise TimeoutError('observation window exceeded')
        if self.start_time is None or self.clock()>self.start_time+TOTAL_SECONDS:raise TimeoutError('total hard deadline exceeded')
        return self.observer.on_stop(stop)
    def cleanup(self,reason='end'):
        out={'reason':reason,'guest_resumed':False,'inherited_cleanup':'not_called','residual':[]}
        try:self.qmp.call('stop');self.qmp.call('query-status');out['stopped']=True
        except Exception as e:out['stop_error']=repr(e);out['stopped']=False
        try:bp=self.observer.cleanup()
        except Exception as e:bp={'all_removed':False,'results':[],'residual':['cleanup_exception'],'error':repr(e)}
        out['breakpoints']=bp;out['residual']=bp.get('residual',[])
        if not bp.get('all_removed'):
            out['status']='stopped_with_residual';out['inherited_cleanup']='not_called_residual'
            self._finish_own();return out
        if self.inherited_cleanup is None:
            out['status']='inherited_cleanup_required';out['inherited_cleanup']='required_missing'
            self._finish_own();return out
        try:
            res=self.inherited_cleanup(self.qmp,self.run_root,self.observer.records)
            ok=isinstance(res,dict) and res.get('passed') is True and res.get('API16_restored') is True and res.get('original_bytes_verified') is True and res.get('ack_seen') is True
            out['inherited_result']=res;out['inherited_cleanup']='completed' if ok else 'contract_not_satisfied'
            if not ok:out['status']='unclean';out['error']='inherited_contract_not_satisfied';self._finish_own();return out
        except Exception as e:
            out['status']='inherited_cleanup_failed';out['inherited_cleanup']='exception';out['inherited_error']=repr(e);self._finish_own();return out
        self._finish_own(out);out['clean']=bool(out.get('qemu_reaped') and out.get('lock_released'));out['status']='clean' if out['clean'] else 'unclean';out['inherited_cleanup']='completed';return out
    def _finish_own(self,out=None):
        out=out if out is not None else {}
        try:self.qmp.call('quit');self.calls.append('qmp_quit')
        except Exception as e:out['quit_error']=repr(e);self.calls.append('qmp_quit_error:'+repr(e))
        reaped=False
        try:self.qemu.wait(timeout=5);reaped=True;self.calls.append('qemu_reaped')
        except Exception as e:
            out['wait_error']=repr(e);self.calls.append('qemu_reap_error:'+repr(e))
            try:
                if hasattr(self.qemu,'terminate'):self.qemu.terminate()
                self.qemu.wait(timeout=3);reaped=True;self.calls.append('qemu_reaped_after_terminate')
            except Exception as e2:out['terminate_error']=repr(e2)
        out['qemu_reaped']=reaped
        released=False
        if reaped:
            try:self.locks.release();released=True;self.calls.append('locks_released')
            except Exception as e:out['release_error']=repr(e);self.calls.append('locks_release_error:'+repr(e))
        else:out['lock_error']='child_alive_or_unknown_lock_retained'
        out['lock_released']=released;out['clean']=bool(out.get('clean') or (out.get('status')=='clean')) and reaped and released
        self.calls.append('no_guest_resume')
        return out
