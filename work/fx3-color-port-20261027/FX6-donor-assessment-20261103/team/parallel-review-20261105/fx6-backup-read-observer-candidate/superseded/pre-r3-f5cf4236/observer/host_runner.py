#!/usr/bin/env python3
"""Default-disabled host runner for the two-key read observer.

The class is fully dependency-injected for fake end-to-end tests.  The real
entry is disabled unless an explicit token is supplied AND a reviewed caller
constructs it; no QEMU is started by this file during preparation.
"""
import argparse,fcntl,hashlib,json,os,plistlib,queue,signal,socket,subprocess,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import baseline_binding,observer_core
from rsp_readonly import RSP
TOKEN='APPROVE_GRMREAL46_TWO_KEYS_0214_0218';TOTAL=180.0;OBS=150.0

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class Deadline:
    def __init__(self,clock):self.clock=clock;self.start=clock();self.total=self.start+TOTAL;self.observe=self.start+OBS
    def left(self):return max(0.0,min(self.total,self.observe)-self.clock())
    def check(self): 
        if self.clock()>=self.total:raise TimeoutError('total hard deadline')
        if self.clock()>=self.observe:raise TimeoutError('observation deadline')
    def clamp(self,value):return max(0.001,min(value,self.left()))

class HostRunner:
    def __init__(self,deps):
        self.d=deps;self.clock=deps.get('clock',time.monotonic);self.deadline=None;self.run_root=None;self.args=None;self.env=None
        self.qemu=None;self.qmp=None;self.rsp=None;self.observer=None;self.locks=None;self.lock_released=False;self._cleanup_done=False;self.cleanup_receipt=None;self.error=None;self.status='unstarted';self.records=[]
    def uuid_guard(self):
        if self.d.get('uuid_checker'):
            if not self.d['uuid_checker']():raise RuntimeError('volume UUID/mount mismatch')
            return
        try:
            v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
            if v.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('volume UUID mismatch')
        except Exception as e:raise RuntimeError('volume UUID/mount check failed: '+repr(e))
    def prepare(self):
        self.d.get('verify_artifacts',baseline_binding.verify_artifacts)()
        base=json.loads(baseline_binding.BASE.read_text());base_args=list(base['fx3_vm_command']);base_env=dict(base['model_env'])
        if len(base_args)!=34:raise RuntimeError('baseline argv count')
        old_serial=base_args[20];old_initrd=base_args[31]
        if 'guest.cpio' not in old_initrd:raise RuntimeError('baseline index31 not loader')
        target=baseline_binding.TARGET;target_loader='loader,file='+str(target)+',addr=0x440000000,force-raw=on'
        hc=self.d.get('hash_checker',sha)
        if hc(target)!=baseline_binding.TARGET_SHA or target.stat().st_size!=baseline_binding.TARGET_BYTES:raise RuntimeError('target CPIO path/hash/size drift')
        app=baseline_binding.APP
        if hc(app)!=baseline_binding.APP_SHA or app.stat().st_size!=baseline_binding.APP_BYTES:raise RuntimeError('APP ELF hash drift')
        run_root=Path(self.d['run_root'])
        if run_root.exists() and any(run_root.iterdir()):raise RuntimeError('run root not new')
        run_root.mkdir(parents=True,exist_ok=True);run_root.chmod(0o700);serial=run_root/'serial.log'
        if serial.exists():raise RuntimeError('serial already exists')
        with serial.open('x'):pass
        args=list(base_args);args[20]='file:'+str(serial);args[31]=target_loader
        if any(args[i]!=base_args[i] for i in range(34) if i not in (20,31)):raise RuntimeError('non-private baseline argv delta')
        if args[20]==old_serial or str(serial)==old_serial:raise RuntimeError('old serial reused')
        if any(base_args[i] in (args[20],str(serial)) for i in range(34) if i!=20):raise RuntimeError('serial path collides with argv')
        if len(base_env)!=5:raise RuntimeError('model_env must be exactly five baseline keys')
        self.run_root=run_root;self.args=args;self.env=base_env;self.serial=serial
        (run_root/'command.json').write_text(json.dumps({'args':args,'env':base_env,'cwd':str(run_root),'serial':str(serial),'target_cpio':str(target),'old_serial':old_serial,'policy':'one start; zero keys; private output; no guest writes by observer'},indent=2)+'\n')
    def acquire_locks(self):
        self.locks=self.d['lock_factory']();self.locks.acquire();self.locks_acquired=True
    def start(self):
        self.deadline.check();self.uuid_guard();self.prepare();self.deadline.check();self.acquire_locks()
        self.qemu=self.d['launcher'](self.args,self.env,str(self.run_root));self.status='launched'
        self.qmp=self.d['qmp_factory'](self.run_root);self.rsp=self.d['rsp_factory'](self.run_root);self.status='connected'
        mapping=self.d['mapping_provider'](self.serial,self.deadline)
        self.observer=observer_core.Observer(mapping,self.rsp,self.d['tls_reader'],clock=self.clock)
        self.qmp.call('stop');st=self.qmp.call('query-status')
        if st.get('status')!='paused':raise RuntimeError('QMP does not report paused')
        self.stop_confirmed=True;self.observer.arm();self.qmp.call('cont');self.status='observing'
    def observe(self):
        while len(self.observer.done)<2:
            self.deadline.check();remain=self.deadline.left()
            if remain<=0:raise TimeoutError('no hit before deadline')
            stop=self.rsp.poll_stop(min(0.1,remain))
            if stop is None:
                self.d.get('sleep',time.sleep)(min(0.01,remain));continue
            self.observer.on_stop(stop);self.records=self.observer.records
            if len(self.observer.done)==2:break
        self.status='observed'
    def run(self):
        self.deadline=Deadline(self.clock)
        try:
            self.start();self.observe();return self.finalize('observed')
        except BaseException as e:
            self.error=repr(e);return self.finalize('error')
        finally:self.cleanup()
    def _own_wait(self,proc,timeout):
        try:proc.wait(timeout=timeout);return True
        except Exception:return False
    def cleanup(self):
        if self._cleanup_done:return self.cleanup_receipt
        self._cleanup_done=True
        out={'stop_confirmed':False,'breakpoints':None,'inherited':'not_applicable','qemu_reaped':False,'lock_released':False,'clean':False,'errors':[],'status':'cleanup_incomplete'}
        # stop is best-effort but must be confirmed, never assumed
        try:
            if self.qmp is not None:
                self.qmp.call('stop');st=self.qmp.call('query-status');out['stop_confirmed']=st.get('status')=='paused'
        except Exception as e:out['errors'].append('qmp_stop_or_query:'+repr(e))
        # remove breakpoints (possibly-installed), even if observer arm failed
        try:
            if self.observer is not None:bp=self.observer.cleanup()
            elif hasattr(self,'possibly'):bp={'all_removed':False,'residual':[hex(x) for x in self.possibly]}
            else:bp={'all_removed':True,'residual':[]}
        except Exception as e:bp={'all_removed':False,'residual':['observer_cleanup_exception'],'error':repr(e)};out['errors'].append('observer_cleanup:'+repr(e))
        out['breakpoints']=bp
        bp_ok=bool(bp.get('all_removed'))
        # inherited cleanup only if breakpoints are gone; exact contract required
        if bp_ok and self.status=='observed' and self.d.get('inherited_cleanup'):
            try:
                q=queue.Queue()
                def work():
                    try:q.put(('ok',self.d['inherited_cleanup'](self.qmp,self.run_root,self.records)))
                    except BaseException as exc:q.put(('err',repr(exc)))
                t=threading.Thread(target=work,daemon=True);t.start()
                wait=min(20.0,max(.05,self.deadline.left() if self.deadline else .05))
                t.join(min(wait,float(self.d.get('callback_timeout',20.0))))
                if t.is_alive():raise TimeoutError('inherited callback timeout')
                kind,r=q.get_nowait()
                if kind=='err':raise RuntimeError(r)
                ok=isinstance(r,dict) and r.get('passed') is True and r.get('API16_restored') is True and r.get('original_bytes_verified') is True and r.get('ack_seen') is True
                out['inherited']={'result':r,'contract_ok':ok}
                if not ok:out['errors'].append('inherited_contract_not_satisfied')
            except Exception as e:out['inherited']={'error':repr(e),'contract_ok':False};out['errors'].append('inherited_exception:'+repr(e))
        elif not bp_ok:out['inherited']='not_run_residual_breakpoint'
        elif self.status!='observed':out['inherited']='not_applicable_unobserved'
        else:out['inherited']='required_callback_missing';out['errors'].append('inherited_callback_missing')
        # own process only: bounded wait, then terminate/kill own process group, re-wait.
        if self.qemu is not None:
            if self._own_wait(self.qemu,5.0):out['qemu_reaped']=True
            else:
                out['errors'].append('qemu_wait_timeout')
                try:
                    if hasattr(self.qemu,'terminate'):self.qemu.terminate()
                    if self._own_wait(self.qemu,3.0):out['qemu_reaped']=True
                    elif hasattr(self.qemu,'kill'):self.qemu.kill();out['qemu_reaped']=self._own_wait(self.qemu,3.0)
                except Exception as e:out['errors'].append('qemu_terminate:'+repr(e))
        else:out['qemu_reaped']=True
        # quit after stop; failures are recorded, not ignored
        try:
            if self.qmp is not None:self.qmp.call('quit')
        except Exception as e:out['errors'].append('qmp_quit:'+repr(e))
        # locks are released only if no own child may still be alive/unknown.
        if out['qemu_reaped'] and self.locks is not None:
            try:self.locks.release();self.lock_released=True
            except Exception as e:out['errors'].append('lock_release:'+repr(e))
        elif self.locks is not None:out['errors'].append('lock_retained_child_alive_or_unknown')
        inherited_ok=isinstance(out['inherited'],dict) and out['inherited'].get('contract_ok') is True
        out['clean']=all([self.status=='observed',out['stop_confirmed'],bp_ok,inherited_ok,out['qemu_reaped'],self.lock_released,not out['errors']])
        out['status']='clean' if out['clean'] else 'unclean'
        self.cleanup_receipt=out
        return out
    def finalize(self,status):
        c=self.cleanup()
        return {'schema':'fx6-observer-run-v1','status':status,'run_root':str(self.run_root) if self.run_root else None,'error':self.error,'records':self.records,'cleanup':c,'clean':c['clean'],'runtime_evidence':False}
class FileLocks:
    def __init__(self):
        self.paths=[];self.files=[]
    def acquire(self):
        import fcntl
        for row in json.loads(baseline_binding.BASE.read_text())['locks']:
            f=open(row['path'],'rb')
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                f.close()
                for x in self.files:fcntl.flock(x,fcntl.LOCK_UN);x.close()
                raise RuntimeError('fixed FX3 lock busy')
            self.files.append(f);self.paths.append(row['path'])
    def release(self):
        import fcntl
        for f in self.files:
            try:fcntl.flock(f,fcntl.LOCK_UN)
            finally:f.close()
        self.files=[]

class QMP:
    def __init__(self,run):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);old=Path.cwd()
        try:os.chdir(run);self.sock.connect('q')
        finally:os.chdir(old)
        self.stream=self.sock.makefile('rb');self.greeting=json.loads(self.stream.readline());self.seq=0
    def call(self,cmd,args=None):
        self.seq+=1;tok='host-'+str(self.seq);p={'execute':cmd,'id':tok}
        if args is not None:p['arguments']=args
        self.sock.sendall((json.dumps(p)+'\n').encode())
        while True:
            line=self.stream.readline()
            if not line:raise RuntimeError('QMP closed')
            row=json.loads(line)
            if row.get('id')==tok:
                if 'error' in row:raise RuntimeError('QMP '+cmd+': '+repr(row['error']))
                return row.get('return')
    def close(self):self.stream.close();self.sock.close()

def real_deps(run_root):
    box={}
    def mapping_provider(serial,deadline):
        import time
        while time.monotonic()<deadline.total:
            try:return observer_core.choose_appfw(serial.read_bytes(),observer_core.APP_ELF)
            except Exception:
                if time.monotonic()>=deadline.observe:raise TimeoutError('no current complete AppFw map before observation deadline')
                time.sleep(0.05)
        raise TimeoutError('no map')
    def tls_reader():
        from sys import path as sp
        sp.insert(0,'/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime')
        from gdb_sysregs104_v2 import Sysregs
        box['sysregs']=box.get('sysregs') or Sysregs(box['rsp'],run_root);return box['sysregs'].read('TPIDR_EL0')
    def rsp_factory(run):
        r=RSP.connect(run);box['rsp']=r;return r
    def launcher(args,env,cwd):
        out=open(Path(cwd)/'host-stdout.log','wb');err=open(Path(cwd)/'host-stderr.log','wb')
        return subprocess.Popen(args,cwd=cwd,env=env,start_new_session=True,stdout=out,stderr=err)
    return {'uuid_checker':None,'run_root':str(run_root),'lock_factory':FileLocks,'launcher':launcher,'qmp_factory':QMP,'rsp_factory':rsp_factory,'mapping_provider':mapping_provider,'tls_reader':tls_reader,'inherited_cleanup':None,'clock':time.monotonic}
