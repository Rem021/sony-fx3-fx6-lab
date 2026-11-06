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
    def remaining_total(self):return max(0.0,self.total-self.clock())
    def remaining_observation(self):return max(0.0,min(self.observe,self.total)-self.clock())
    def check(self):
        if self.clock()>=self.total:raise TimeoutError('total hard deadline')
        if self.clock()>=self.observe:raise TimeoutError('observation deadline')
    def clamp_total(self,value):return max(.001,min(value,self.remaining_total()))
    def clamp_observation(self,value):return max(.001,min(value,self.remaining_observation()))

class HostRunner:
    def __init__(self,deps):
        self.d=deps;self.clock=deps.get('clock',time.monotonic);self.deadline=None;self.run_root=None;self.args=None;self.env=None
        self.stop_only=bool(deps.get('stop_only',False));self.qemu=None;self.qmp=None;self.rsp=None;self.observer=None;self.locks=None;self.possibly=set();self.lock_released=False;self._cleanup_done=False;self.cleanup_receipt=None;self.error=None;self.status='unstarted';self.records=[]
    def uuid_guard(self):
        if self.d.get('uuid_checker'):
            if not self.d['uuid_checker']():raise RuntimeError('volume UUID/mount mismatch')
            return
        try:
            v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
            if v.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise RuntimeError('volume UUID mismatch')
        except Exception as e:raise RuntimeError('volume UUID/mount check failed: '+repr(e))
    def preflight(self):
        # Host preflight is explicitly outside the launch->reap 180s budget.
        self.uuid_guard();self.d.get('verify_artifacts',baseline_binding.verify_artifacts)()
        hc=self.d.get('hash_checker',sha)
        if baseline_binding.TARGET.stat().st_size!=baseline_binding.TARGET_BYTES or baseline_binding.APP.stat().st_size!=baseline_binding.APP_BYTES:raise RuntimeError('preflight size drift')
        self.pre_hashes={'target_cpio':hc(baseline_binding.TARGET),'appfw':hc(baseline_binding.APP)}
        if self.pre_hashes['target_cpio']!=baseline_binding.TARGET_SHA:raise RuntimeError('target CPIO prehash drift')
        if self.pre_hashes['appfw']!=baseline_binding.APP_SHA:raise RuntimeError('APP_ELF prehash drift')
        self.hash_source='actual' if self.d.get('runtime_evidence',False) else 'fake_injected'
        return self.pre_hashes
    def postflight(self):
        try:
            hc=self.d.get('post_hash_checker',self.d.get('hash_checker',sha));after={'target_cpio':hc(baseline_binding.TARGET),'appfw':hc(baseline_binding.APP)}
            return {'after':after,'input_unchanged':after==self.pre_hashes,'error':None}
        except Exception as e:return {'after':None,'input_unchanged':None,'error':repr(e)}
    def prepare(self):
        base=json.loads(baseline_binding.BASE.read_text());base_args=list(base['fx3_vm_command']);base_env=dict(base['model_env'])
        if len(base_args)!=34:raise RuntimeError('baseline argv count')
        old_serial=base_args[20];old_initrd=base_args[31]
        if 'guest.cpio' not in old_initrd:raise RuntimeError('baseline index31 not loader')
        target=baseline_binding.TARGET;target_loader='loader,file='+str(target)+',addr=0x440000000,force-raw=on'
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
    def _qcall(self,cmd,args=None):
        return self.qmp.call(cmd,args,deadline=self.deadline) if args is not None else self.qmp.call(cmd,deadline=self.deadline)
    def start(self):
        self.deadline.check();self.prepare();self.deadline.check();self.acquire_locks()
        self.qemu=self.d['launcher'](self.args,self.env,str(self.run_root));self.status='launched';self.runtime_command_written=True
        self.qmp=self.d['qmp_factory'](self.run_root,deadline=self.deadline)
        if hasattr(self.qmp,'set_deadline'):self.qmp.set_deadline(self.deadline)
        st=self._qcall('query-status')
        if not ((st.get('status')=='prelaunch' or st.get('status')=='paused') and st.get('running') is False):
            raise RuntimeError('initial QMP not prelaunch/paused with running=false: '+repr(st))
        self.prelaunch_state=st.get('status');self.prelaunch_paused=True
        # -S keeps guest paused.  Allow the original boot resume before waiting for maps.
        self._qcall('cont');self.status='boot_resumed'
        mapping=self.d['mapping_provider'](self.serial,self.deadline)
        self._qcall('stop');st=self._qcall('query-status')
        if st.get('status')!='paused':raise RuntimeError('post-map QMP not paused')
        self.stop_confirmed=True
        self.rsp=self.d['rsp_factory'](self.run_root,deadline=self.deadline)
        if hasattr(self.rsp,'set_phase'):self.rsp.set_phase('observation')
        self.status='connected'
        self.observer=observer_core.Observer(mapping,self.rsp,self.d['tls_reader'],clock=self.clock)
        self.possibly=set(getattr(self.observer,'possibly',set()))
        self.observer.arm();self.possibly=set(getattr(self.observer,'possibly',set()));self.status='armed'
        # GDB addressless c sets allow_stop_reply; no QMP-only resume from here.
        self.rsp.send_continue(timeout=self.deadline.clamp_observation(2.0));self.status='observing'
    def observe(self):
        while len(self.observer.done)<2:
            self.deadline.check();remain=self.deadline.remaining_observation()
            if remain<=0:raise TimeoutError('no hit before observation deadline')
            stop=self.rsp.poll_stop(min(.1,remain))
            if stop is None:
                self.d.get('sleep',time.sleep)(min(.01,remain));continue
            self.observer.on_stop(stop);self.records=self.observer.records
            if len(self.observer.done)==2:break
            # Every stop (entry or return) needs its own addressless c to reach the next stop.
            self.rsp.send_continue(timeout=self.deadline.clamp_observation(2.0))
        self.status='observed'
    def run(self):
        try:
            self.preflight()
            self.deadline=Deadline(self.clock)
            return self._run_after_preflight()
        except BaseException as e:
            self.error=repr(e);return self.finalize('preflight_error')
    def _run_after_preflight(self):
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
        out={'stop_confirmed':False,'breakpoints':None,'inherited':'unknown_not_attempted','qemu_reaped':False,'qemu_exit':None,'lock_released':False,'clean':False,'errors':[],'status':'cleanup_incomplete'}
        # Stop/query must be confirmed before any operation requiring stopped state.
        try:
            if self.qmp is not None:
                self._qcall('stop');st=self._qcall('query-status');out['stop_confirmed']=st.get('status')=='paused'
        except Exception as e:out['errors'].append('qmp_stop_or_query:'+repr(e))
        if out['stop_confirmed']:
            # Observation budget may already be exhausted while total remains:
            # switch the actual RSP deadline before any z1 business command.
            if self.rsp is not None and hasattr(self.rsp,'set_phase'):
                try:self.rsp.set_phase('cleanup')
                except Exception as e:out['errors'].append('rsp_phase:'+repr(e))
            try:
                if self.observer is not None:bp=self.observer.cleanup()
                else:
                    pos=getattr(self.observer,'possibly',self.possibly)
                    bp={'all_removed':not pos,'residual':[hex(x) for x in pos]}
            except Exception as e:bp={'all_removed':False,'residual':['observer_cleanup_exception'],'error':repr(e)};out['errors'].append('observer_cleanup:'+repr(e))
        else:
            # Cannot safely read/write breakpoints while pause is unconfirmed.
            bp={'all_removed':False,'residual':[hex(x) for x in getattr(self.observer,'possibly',set())] or ['stop_unconfirmed'],'not_attempted':True}
            out['errors'].append('breakpoints_not_removed_stop_unconfirmed')
        out['breakpoints']=bp;bp_ok=bool(bp.get('all_removed'))
        # Close observer RSP before any guest recovery/quit; never keep using it.
        try:
            if self.rsp is not None:
                self.rsp.close()
        except Exception as e:out['errors'].append('rsp_close:'+repr(e))
        self.rsp=None
        inherited_ok=False
        if self.stop_only:
            out['inherited']='not_attempted_stop_only';out['guest_restore_status']='unknown_not_attempted'
        elif bp_ok and out['stop_confirmed'] and self.status=='observed' and self.d.get('inherited_cleanup'):
            if not self.d.get('callback_cancellable',False):
                out['inherited']='callback_not_cancellable_not_run';out['errors'].append('inherited_callback_not_cancellable')
            else:
                try:
                    r=self.d['inherited_cleanup'](self.qmp,self.run_root,self.records)
                    inherited_ok=isinstance(r,dict) and r.get('passed') is True and r.get('API16_restored') is True and r.get('original_bytes_verified') is True and r.get('ack_seen') is True
                    out['inherited']={'result':r,'contract_ok':inherited_ok};out['errors']+=[] if inherited_ok else ['inherited_contract_not_satisfied']
                except Exception as e:out['inherited']={'error':repr(e),'contract_ok':False};out['errors'].append('inherited_exception:'+repr(e))
        elif not bp_ok:out['inherited']='not_run_residual_breakpoint'
        elif not out['stop_confirmed']:out['inherited']='unknown_stop_unconfirmed'
        elif self.status!='observed':out['inherited']='unknown_not_observed'
        else:out['inherited']='required_callback_missing';out['errors'].append('inherited_callback_missing')
        # Normal order: quit first, then bounded wait/reap.  Paused QEMU cannot exit before quit.
        try:
            if self.qmp is not None:self._qcall('quit')
        except Exception as e:out['errors'].append('qmp_quit:'+repr(e))
        if self.qmp is not None:
            try:self.qmp.close()
            except Exception as e:out['errors'].append('qmp_close:'+repr(e))
        if self.qemu is not None:
            wait=self.deadline.clamp_total(5.0) if self.deadline else 5.0
            if self._own_wait(self.qemu,wait):out['qemu_reaped']=True
            else:
                out['errors'].append('qemu_wait_timeout')
                try:
                    if hasattr(self.qemu,'terminate'):self.qemu.terminate()
                    if self._own_wait(self.qemu,self.deadline.clamp_total(3.0) if self.deadline else 3.0):out['qemu_reaped']=True
                    elif hasattr(self.qemu,'kill'):self.qemu.kill();out['qemu_reaped']=self._own_wait(self.qemu,self.deadline.clamp_total(3.0) if self.deadline else 3.0)
                except Exception as e:out['errors'].append('qemu_terminate:'+repr(e))
            try:out['qemu_exit']=getattr(self.qemu,'returncode',None)
            except Exception:out['qemu_exit']=None
            if out['qemu_exit'] not in (None,0):out['errors'].append('qemu_nonzero_exit:'+repr(out['qemu_exit']))
        else:out['qemu_reaped']=True
        if out['qemu_reaped'] and self.locks is not None:
            try:self.locks.release();self.lock_released=True;out['lock_released']=True
            except Exception as e:out['errors'].append('lock_release:'+repr(e))
        elif self.locks is not None:out['errors'].append('lock_retained_child_alive_or_unknown')
        host_ok=all([out['stop_confirmed'],bp_ok,out['qemu_reaped'],out['qemu_exit']==0,self.lock_released,not out['errors']])
        out['two_keys_observed']=self.status=='observed'
        out['host_cleanup_complete']=host_ok
        out['guest_restore_status']=out.get('guest_restore_status','unknown_not_attempted' if self.stop_only else 'unknown_not_attempted')
        out['boot_menu_passed']=False
        out['clean']=all([self.status=='observed',out['stop_confirmed'],bp_ok,inherited_ok,out['qemu_reaped'],out['qemu_exit']==0,self.lock_released,not out['errors']]) and not self.stop_only
        out['status']='clean' if out['clean'] else 'unclean';self.cleanup_receipt=out;return out
    def finalize(self,status):
        c=self.cleanup()
        post=self.postflight() if hasattr(self,'pre_hashes') else {'after':None,'input_unchanged':None,'error':'no_preflight'}
        rec={'schema':'fx6-observer-run-v1','status':status,'run_root':str(self.run_root) if self.run_root else None,'error':self.error,'records':self.records,'cleanup':c,'clean':c['clean'],'runtime_evidence':bool(self.d.get('runtime_evidence',False)),'command_sha256':(sha(self.run_root/'command.json') if self.run_root and (self.run_root/'command.json').is_file() else None),'target_cpio_sha256':baseline_binding.TARGET_SHA,'appfw_sha256':baseline_binding.APP_SHA,'preflight':getattr(self,'pre_hashes',None),'postflight':post,'hash_source':getattr(self,'hash_source','unknown'),'input_unchanged_after':post.get('input_unchanged'),'actual_target_cpio_sha256':(post.get('after') or {}).get('target_cpio'),'actual_appfw_sha256':(post.get('after') or {}).get('appfw'),'postflight_error':post.get('error'),'verification_failed':not (post.get('error') is None and post.get('input_unchanged') is True),'serial_sha256':(sha(self.serial) if hasattr(self,'serial') and self.serial.is_file() else None),'locks_released':bool(c.get('lock_released')),'qemu_exit':c.get('qemu_exit'),'two_keys_observed':c.get('two_keys_observed',False),'host_cleanup_complete':c.get('host_cleanup_complete',False),'guest_restore_status':c.get('guest_restore_status','unknown_not_attempted'),'boot_menu_passed':False}
        if self.run_root and (self.run_root/'command.json').is_file():
            rec['command']=json.loads((self.run_root/'command.json').read_text())
            (self.run_root/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
        return rec
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
    def __init__(self,run=None,sock=None,deadline=None):
        self.sock=sock;self.deadline=deadline;self.buf=b'';self.seq=0;self.events=[]
        if self.sock is None:
            if run is None:raise RuntimeError('QMP run path required')
            end=(deadline.total if deadline else time.monotonic()+4)
            last=None
            while time.monotonic()<end:
                try:
                    self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(max(.05,min(.25,end-time.monotonic())))
                    old=Path.cwd()
                    try:os.chdir(run);self.sock.connect('q')
                    finally:os.chdir(old)
                    break
                except Exception as exc:
                    last=exc
                    try:self.sock.close()
                    except Exception:pass
                    self.sock=None;time.sleep(.02)
            if self.sock is None:raise TimeoutError('QMP connect: '+repr(last))
        try:
            self.greeting=json.loads(self._line(self._limit(deadline)))
            if 'QMP' not in self.greeting:raise RuntimeError('QMP greeting')
            # Real QMP requires capabilities negotiation before any command.
            self.call('qmp_capabilities',deadline=self._limit(deadline))
        except BaseException:
            self.close();raise
    def _limit(self,deadline=None):
        if deadline is None:deadline=self.deadline
        if deadline is None:return time.monotonic()+2
        if hasattr(deadline,'remaining_total'):return time.monotonic()+max(.001,deadline.remaining_total())
        return deadline
    def _line(self,deadline):
        end=self._limit(deadline)
        while b'\n' not in self.buf:
            left=end-time.monotonic()
            if left<=0:raise TimeoutError('QMP readline timeout')
            self.sock.settimeout(max(.001,min(.25,left)))
            try:chunk=self.sock.recv(4096)
            except socket.timeout:continue
            if not chunk:raise ConnectionError('QMP EOF')
            self.buf+=chunk
            if len(self.buf)>1048576:raise ValueError('QMP oversized line')
        line,self.buf=self.buf.split(b'\n',1)
        return line.decode()
    def set_deadline(self,d):self.deadline=d
    def call(self,cmd,args=None,deadline=None):
        self.seq+=1;tok='host-'+str(self.seq);p={'execute':cmd,'id':tok}
        if args is not None:p['arguments']=args
        self.sock.sendall((json.dumps(p)+'\n').encode())
        end=self._limit(deadline)
        while True:
            line=self._line(end);row=json.loads(line)
            if row.get('id')==tok:
                if 'error' in row:raise RuntimeError('QMP '+cmd+': '+repr(row['error']))
                return row.get('return')
            if 'event' in row:self.events.append(row);continue
            if 'return' in row or 'error' in row:continue
            raise ValueError('QMP unmatched packet '+line[:80])
    def close(self):
        try:self.sock.close()
        except Exception:pass


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
    def rsp_factory(run,deadline=None):
        r=RSP.connect(run,deadline);box['rsp']=r;return r
    def launcher(args,env,cwd):
        out=open(Path(cwd)/'host-stdout.log','wb');err=open(Path(cwd)/'host-stderr.log','wb')
        try:p=subprocess.Popen(args,cwd=cwd,env=env,start_new_session=True,stdout=out,stderr=err)
        finally:out.close();err.close()
        return p
    return {'uuid_checker':None,'run_root':str(run_root),'lock_factory':FileLocks,'launcher':launcher,'qmp_factory':lambda run,deadline=None:QMP(run,deadline=deadline),'rsp_factory':rsp_factory,'mapping_provider':mapping_provider,'tls_reader':tls_reader,'inherited_cleanup':None,'clock':time.monotonic,'runtime_evidence':True}
