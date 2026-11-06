#!/usr/bin/env python3
"""Single owner-only, zero-key read-only FX6 AP send observation candidate.

Do not run until the coordinator allocates the existing FX3 VM window.
"""
import datetime
import fcntl
import json
import os
import resource
import shutil
import signal
import sys
import time
import uuid
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
MAC=HERE.parents[5]
DONOR=HERE.parent
PARENT=DONOR/'hybrid-ap-candidate'
FX3_RUNTIME=MAC/'work/fx3-vm-20261101/menu-repair-01/runtime'
sys.path.insert(0,str(PARENT))
import run_ap_once as frozen
sys.path.insert(0,str(FX3_RUNTIME))
from gdb_sysregs104_v2 import Sysregs
from readonly_probe import RSP, confirm_hit, sha
from two_phase_identity import choose_early_cap, target_profile, read_current_identity

AP_ELF=DONOR/'nflasha15-files/lib/appFw.so'
CAP_ELF=FX3_RUNTIME/'helpers/fx3-capid-v49-touch100.so'
HISTORICAL= PARENT/'runs/fx6ap-bb7588e5/serial.log'
AP_SHA='a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067'
CAP_SHA='cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e'
PARENT_SHA='aaa9ca518d580fde7ca9fdbf2c33bebe78545d96876f997168643f33bdf4a24a'
HIST_SHA='7fd297d60c72a1211fa44a0103ae69fabec0c72c422be6c34519c2636db3a43f'
SYSREG_SHA='55404f4a333dd8dbd89b50f2e4d8a0d9075ab77203e331bbb66d5852a3f08f73'
IDENTITY_SHA='d164c95a14e0d906083e6bbbd05facb4827cc1d4a59dbfc784830ebc2cd6de68'
QEMU_GDB_SHA='a03d5b7aa6a2188f4eebda464a6e6d7914dacfb0898136323c5c857c829cba6a'
QEMU_SYSTEM_SHA='196af474a5aacefab3394162b10537efcf9dbd55e2ec2fa291a0cbd71877352f'
MAX_HITS=2

def _lineage(serial):
    """Same TID, TLS and source from this run's native helper log, not old run."""
    import re
    dyn=re.findall(rb'FX3_GPE104_DYNAMIC_RETURN tid=(\d+) tpidr=(0x[0-9a-f]+)[^\r\n]*QID=(0x[0-9a-f]+)[^\r\n]*QID_available=1',serial)
    req=re.findall(rb'FX3_PROVIDER_REQUEST destination=0x92840747 bytes=10 source=(0x[0-9a-f]+)[^\r\n]*raw=(0d202d030a0001800000)',serial)
    for tid,tls,qid in reversed(dyn):
        if any(src==qid for src,raw in req):
            return {'tid':int(tid),'tls':int(tls,16),'source':int(qid,16),'request_count':len(req)}
    return None

class Probe:
    def __init__(self,run,qmp,mapping):
        self.run=run;self.qmp=qmp;self.mapping=mapping;self.rsp=None;self.sysregs=None
        self.breakpoints=set();self.records=[];self.stage='unarmed';self.audio=None
        self.cap_entry=mapping['cap']['bias']+0x1e730
        self.ap_return=None
        self.resume_acks=[];self.qmp_statuses=[];self.last_qmp_check=0.0
    def save(self):
        clean=[]
        for x in self.records:
            clean.append({k:v for k,v in x.items() if k!='regs'})
        (self.run/'readonly-observation.json').write_text(json.dumps({
            'stage':self.stage,'mapping':self.mapping,'breakpoints_still_installed':[hex(x) for x in self.breakpoints],
            'records':clean,'linux_process_attribution': 'requires live TLS+request+same AP mapping; unknown until captured',
            'resume_acks':self.resume_acks,'qmp_statuses':self.qmp_statuses,
            'policy':'RSP addressless c after Z1, Z1/z1 and stopped-only g/p/m/XML; no guest write, no Z0, no keys',
        },indent=2)+'\n')
    def resume(self):
        ack=self.rsp.send_continue()
        self.resume_acks.append({'stage':self.stage,**ack})
        self.save()
    def check_qmp_without_rsp(self):
        now=time.monotonic()
        if now-self.last_qmp_check<.25:return None
        self.last_qmp_check=now
        status=self.qmp.call('query-status').get('status')
        if not self.qmp_statuses or status!=self.qmp_statuses[-1]['status']:
            self.qmp_statuses.append({'stage':self.stage,'status':status})
            self.save()
        if status=='running':return None
        # A stop packet can be in flight when QMP first reports debug.
        event=self.rsp.poll_stop(.5)
        if event:return event
        self.stage='qmp_'+str(status)+'_without_rsp_stop'
        self.save()
        raise RuntimeError('QMP '+str(status)+' without RSP stop packet')
    def arm(self):
        self.qmp.call('stop')
        status=self.qmp.call('query-status')
        if status.get('status')!='paused':raise RuntimeError('QMP did not quiesce all CPUs before Z1')
        self.qmp_statuses.append({'stage':'arm','status':status['status']})
        self.rsp=RSP.connect(self.run)
        if self.rsp.command('Qqemu.PhyMemMode:1')!='OK' or self.rsp.command('qqemu.PhyMemMode')!='1':
            raise RuntimeError('GDB physical mode baseline unavailable')
        # Resolve register numbers from this exact QEMU target XML. No guessed pN.
        self.sysregs=Sysregs(self.rsp,self.run)
        if self.rsp.command(f'Z1,{self.cap_entry:x},4')!='OK':raise RuntimeError('TCG Z1 rejected')
        self.breakpoints.add(self.cap_entry);self.stage='await_audio_entry';self.save()
        # Do not use '?' here: QEMU's system stub removes breakpoints on query.
        # A paused initial GDB stop is not evidence of our Z1 hit.
        while True:
            initial=self.rsp.poll_stop(0)
            if initial is None:break
            if not initial.startswith(('T02','S02')):
                raise RuntimeError('unexpected pre-resume RSP stop '+initial)
        while self.rsp.stops:
            stale=self.rsp.stops.popleft()
            if not stale.startswith(('T02','S02')):raise RuntimeError('unexpected startup RSP stop '+stale)
        self.resume()
    def read(self,addr,n):return self.rsp.virtual_read(addr,n)
    def ap_frame_anchor(self,fp):
        """Find the native call frame whose saved LR is this AP send return PC."""
        frames=[]
        for _ in range(16):
            if fp==0 or fp&15 or fp>=0x800000000000:break
            try:raw=self.read(fp,16)
            except Exception:break
            previous=int.from_bytes(raw[:8],'little');lr=int.from_bytes(raw[8:],'little')
            frames.append({'fp':hex(fp),'previous_fp':hex(previous),'saved_lr':hex(lr)})
            if lr==self.ap_return and previous>fp and previous-fp<=0x100000:
                return previous,frames
            if previous<=fp or previous-fp>0x100000:break
            fp=previous
        return None,frames
    def process_stop(self,stop,serial):
        if len(self.records)>=MAX_HITS:raise RuntimeError('hit budget exceeded')
        qmp_status=self.qmp.call('query-status').get('status')
        self.qmp_statuses.append({'stage':self.stage,'status':qmp_status,'rsp_stop':stop})
        self.save()
        if qmp_status!='debug':raise RuntimeError('RSP stop/QMP status mismatch')
        expected=self.cap_entry if self.stage=='await_audio_entry' else self.ap_return
        origin='cap' if self.stage=='await_audio_entry' else 'ap'
        row=confirm_hit(self.rsp,stop,self.mapping,expected,origin)
        regs=row['regs'];tls=self.sysregs.read('TPIDR_EL0')
        native=_lineage(serial)
        row['tpidr_el0']=hex(tls)
        row['native_lineage']=native
        if self.stage=='await_audio_entry':
            req=self.read(regs[0],10).hex()
            row['request_pointer']=hex(regs[0]);row['request_raw']=req
            if req!='0d202d030a0001800000' or native is None or tls!=native['tls']:
                row['attribution']='unknown_or_wrong_hit';self.records.append(row);self.stage='unknown_hit_stop';self.save();return True
            # The early CAP map alone permits a breakpoint, but not model
            # interpretation. Prove both pinned images in the current vCPU
            # address space before reading any CAP model field.
            try:
                profile=target_profile(serial,native,AP_ELF)
                ap_bias=profile['bias'];self.ap_return=ap_bias+0x20ef7a0
                row['target_native_profile']=profile
                row['current_cap_identity']=read_current_identity(self.rsp,self.mapping['cap']['bias'],CAP_ELF,
                                                                   [0x1840c,0x1e730,0x1e754,0x1e764])
                row['current_ap_identity']=read_current_identity(self.rsp,ap_bias,AP_ELF,
                                                                  [0x20ef79c,0x20ef7a0,0x20ef7b4,0x20ef7c8])
            except Exception as exc:
                row['identity_error']=repr(exc);row['attribution']='unknown_image_or_profile_identity'
                self.records.append(row);self.stage='unknown_hit_stop';self.save();return True
            self.mapping['ap']={'bias':ap_bias,'source':'same-TID native dladdr profile plus current CPU ELF/PHDR/code',
                                'proc_vma_observed':False}
            frame,chain=self.ap_frame_anchor(regs[29]);row['bounded_fp_chain']=chain
            row['ap_frame_anchor']=None if frame is None else hex(frame)
            if frame is None:
                row['attribution']='unknown_missing_original_saved_LR';self.records.append(row);self.stage='unknown_hit_stop';self.save();return True
            row['model_initialized']=int.from_bytes(self.read(self.mapping['cap']['bias']+0x45bc0,4),'little')
            row['model_process_owner']=int.from_bytes(self.read(self.mapping['cap']['bias']+0x45b08,8),'little')
            row['attribution']='same_live_TID_TLS_source_request_AP_mapping_and_saved_LR; TGID from serial map only'
            self.audio=row;self.records.append(row)
            if self.rsp.command(f'Z1,{self.ap_return:x},4')!='OK':raise RuntimeError('AP return Z1 rejected')
            self.breakpoints.add(self.ap_return)
            if self.rsp.command(f'z1,{self.cap_entry:x},4')!='OK':raise RuntimeError('audio entry z1 rejected')
            self.breakpoints.remove(self.cap_entry)
            self.stage='await_same_call_return';self.save();self.resume();return False
        if (self.audio is None or native is None or hex(tls)!=self.audio['tpidr_el0']
                or regs[29]!=int(self.audio['ap_frame_anchor'],16)):
            row['attribution']='unknown_return_TID';self.records.append(row);self.stage='unknown_hit_stop';self.save();return True
        ptr=int.from_bytes(self.read(regs[29]+0x58,8),'little')
        raw=self.read(ptr,10).hex()
        row['frame_request_pointer']=hex(ptr);row['frame_request_raw']=raw
        row['send_w0_signed32']=int.from_bytes(regs[0].to_bytes(8,'little')[:4],'little',signed=True)
        if ptr!=int(self.audio['request_pointer'],16) or raw!=self.audio['request_raw']:
            row['attribution']='unknown_return_call';self.records.append(row);self.stage='unknown_hit_stop';self.save();return True
        row['attribution']='same_request_pointer_raw_and_TLS_as_audio_entry'
        row['assert_branch_will_fire']=row['send_w0_signed32']!=0
        self.records.append(row);self.stage='same_call_return_captured';self.save();return True
    def remove_all(self):
        if not self.rsp:return {'attempted':False,'all_removed':True}
        results=[]
        for addr in sorted(self.breakpoints):
            try:reply=self.rsp.command(f'z1,{addr:x},4')
            except Exception as exc:reply=repr(exc)
            results.append({'address':hex(addr),'reply':reply})
            if reply=='OK':self.breakpoints.remove(addr)
        self.stage+=';cleanup'
        self.save()
        return {'attempted':True,'results':results,'all_removed':not self.breakpoints,
                'unremoved':[hex(addr) for addr in sorted(self.breakpoints)]}

def quit_without_guest_resume(qemu,qmp,cleanup):
    """Fail closed when a Z1 remains: never resume into a stale breakpoint."""
    cleanup['attempted']=True
    cleanup['reason']='unremoved_debug_breakpoint; no_API16_resume'
    if qemu is not None and qemu.poll() is None:
        if qmp is not None:
            try:qmp.call('stop');cleanup['guest_stopped']=True
            except Exception as exc:cleanup['stop_error']=repr(exc)
            try:qmp.call('quit');cleanup['quit_sent']=True
            except Exception as exc:cleanup['quit_error']=repr(exc)
        try:qemu.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(qemu.pid,signal.SIGTERM)
            try:qemu.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(qemu.pid,signal.SIGKILL);qemu.wait(timeout=3)
                cleanup['forced_own_process_kill']=True
    if qmp is not None:qmp.close()

def main():
    if sha(HERE/'readonly_probe.py') != '7da87fbb920bfa6a9516421d1224813056ff991a2c950552c4ccdadc662bbade':
        raise RuntimeError('observer implementation changed; re-audit before runtime')
    if sha(HERE/'two_phase_identity.py') != IDENTITY_SHA:
        raise RuntimeError('two-phase identity implementation changed; re-audit before runtime')
    for p,h in [(PARENT/'run_ap_once.py',PARENT_SHA),(AP_ELF,AP_SHA),(CAP_ELF,CAP_SHA),
                (HISTORICAL,HIST_SHA),(FX3_RUNTIME/'gdb_sysregs104_v2.py',SYSREG_SHA)]:
        if sha(p)!=h:raise RuntimeError('frozen input drift '+str(p))
    qsrc=FX3_RUNTIME/'qemu-display-build/sources/qemu-11.1.2/gdbstub'
    for p,h in [(qsrc/'gdbstub.c',QEMU_GDB_SHA),(qsrc/'system.c',QEMU_SYSTEM_SHA)]:
        if sha(p)!=h:raise RuntimeError('QEMU GDB protocol source drift '+str(p))
    tests=json.loads((HERE/'host-tests.json').read_text())
    if (tests.get('status')!='PASS_NO_QEMU' or tests.get('observer_sha256')!=sha(HERE/'readonly_probe.py')
            or tests.get('identity_sha256')!=IDENTITY_SHA or tests.get('runner_sha256')!=sha(__file__)):
        raise RuntimeError('host-only parser tests missing or stale')
    baseline,audit=frozen.verify() # includes UUID, full CPIO, kernel, DTB, 17 helpers and exact allowlist.
    held=[]
    for path in frozen.LOCKS:
        f=path.open('rb')
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            for old in held:fcntl.flock(old,fcntl.LOCK_UN);old.close()
            raise RuntimeError('fixed FX3 double lock busy; no QEMU started')
        held.append(f)
    run=HERE/'runs'/('ap-ro-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True);run.chmod(0o700)
    args=list(baseline['fx3_vm_command']);args[20]='file:'+str(run/'serial.log')
    args[31]='loader,file='+str(PARENT/'guest-three-entry.cpio')+',addr=0x440000000,force-raw=on'
    frozen_args=baseline['fx3_vm_command']
    if len(args)!=34 or any(args[i]!=frozen_args[i] for i in range(34) if i not in (20,31)):
        raise RuntimeError('frozen QEMU argv mismatch')
    env=os.environ.copy();env.update(baseline['model_env'])
    (run/'command.json').write_text(json.dumps({'args':args,'cwd':str(run),'model_env':baseline['model_env'],
        'key_budget':0,'observation_seconds':120,'total_seconds':180,'fixed_delta_indices':[20,31],
        'parent_runner_sha256':PARENT_SHA,'probe_sha256':sha(HERE/'readonly_probe.py')},indent=2)+'\n')
    (run/'source-sha256.json').write_text(json.dumps({
        'runner':sha(__file__),'probe':sha(HERE/'readonly_probe.py'),
        'parent_runner':PARENT_SHA,'sysregs':SYSREG_SHA,'identity':IDENTITY_SHA,
        'host_tests':sha(HERE/'host-tests.json')},indent=2)+'\n')
    for name in ['run_once.py','readonly_probe.py','two_phase_identity.py']:
        shutil.copyfile(HERE/name,run/('observer-'+name))
    qemu=qmp=probe=None;start=time.monotonic();stop=None;error=None
    cleanup={'attempted':False,'API16_restored':False,'quit_sent':False};bp_cleanup={'attempted':False,'all_removed':True}
    watcher=frozen.APHealthMonitor(run/'serial.log')
    old_sig=signal.getsignal(signal.SIGINT);interrupted={'yes':False}
    def interrupt(_signum,_frame):interrupted['yes']=True
    signal.signal(signal.SIGINT,interrupt)
    try:
        with (run/'host-stdout.log').open('wb') as out,(run/'host-stderr.log').open('wb') as err:
            try:
                def limits():
                    resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
                qemu=subprocess.Popen(args,cwd=run,env=env,stdout=out,stderr=err,
                                      start_new_session=True,preexec_fn=limits)
                (run/'pid.json').write_text(json.dumps({'qemu_pid':qemu.pid,'owner_pid':os.getpid()})+'\n')
                while not (run/'q').exists() and qemu.poll() is None and time.monotonic()-start<10:time.sleep(.05)
                if not (run/'q').exists() or qemu.poll() is not None:raise RuntimeError('QEMU QMP bind failed')
                qmp=frozen.QMP(run);qmp.call('qmp_capabilities');qmp.call('cont')
                while time.monotonic()-start<120:
                    watcher.poll()
                    if watcher.failure:stop='first_health_fault';break
                    if qemu.poll() is not None:stop='qemu_early_exit';break
                    if interrupted['yes']:stop='operator_interrupt';break
                    if probe is None:
                        serial=(run/'serial.log').read_bytes() if (run/'serial.log').exists() else b''
                        mapping=choose_early_cap(serial,CAP_ELF)
                        if mapping:
                            probe=Probe(run,qmp,mapping);probe.arm()
                    else:
                        event=probe.rsp.poll_stop(.05)
                        if event is None:event=probe.check_qmp_without_rsp()
                        if event:
                            serial=(run/'serial.log').read_bytes()
                            if probe.process_stop(event,serial):stop=probe.stage;break
                    time.sleep(.025)
                stop=stop or 'observation_budget_end'
            except Exception as exc:
                error=repr(exc);stop=stop or 'host_exception'
            finally:
                if probe and probe.rsp:
                    try:
                        if qemu is not None and qemu.poll() is None and qmp is not None:qmp.call('stop')
                        bp_cleanup=probe.remove_all()
                    except Exception as exc:
                        bp_cleanup={'attempted':True,'all_removed':False,'error':repr(exc)}
                    finally:probe.rsp.close()
                # This existing shutdown path may write only the 8-byte
                # software observer control request; it never patches code.
                if bp_cleanup['all_removed']:
                    frozen.cleanup_owned(qemu,qmp,frozen.InputGate(run),run,cleanup)
                else:
                    quit_without_guest_resume(qemu,qmp,cleanup)
    finally:
        signal.signal(signal.SIGINT,old_sig);watcher.finish()
        elapsed=time.monotonic()-start
        for f in held:fcntl.flock(f,fcntl.LOCK_UN);f.close()
        free=[]
        for path in frozen.LOCKS:
            with path.open('rb') as f:
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);ok=True;fcntl.flock(f,fcntl.LOCK_UN)
                except BlockingIOError:ok=False
            free.append({'path':str(path),'free':ok})
        pins={'baseline':sha(frozen.BASE),'candidate':sha(PARENT/'guest-three-entry.cpio'),
              'ap':sha(AP_ELF),'cap':sha(CAP_ELF)}
        pins_match=(pins=={'baseline':frozen.PINS['baseline'],'candidate':frozen.PINS['candidate'],
                           'ap':AP_SHA,'cap':CAP_SHA})
        receipt={'schema':'fx6-ap-readonly-gdb-v1','stop':stop,'host_error':error,
          'elapsed_seconds':elapsed,'qemu_exit':None if qemu is None else qemu.returncode,
          'qemu_reaped':qemu is None or qemu.poll() is not None,
          'cleanup':cleanup,'breakpoint_cleanup':bp_cleanup,'locks':free,
          'inputs_sha256_after':pins,'inputs_unchanged':pins_match,'serial':frozen.extract(run/'serial.log'),
          'health':watcher.snapshot(),'probe_stage':None if probe is None else probe.stage}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'run':str(run),'stop':stop,'error':error,'bp_removed':bp_cleanup['all_removed'],
            'api16_restored':cleanup['API16_restored'],'elapsed':elapsed},ensure_ascii=False),flush=True)
        good=(stop=='same_call_return_captured' and error is None and bp_cleanup['all_removed']
              and cleanup['API16_restored'] and qemu is not None and qemu.returncode==0
              and pins_match and all(x['free'] for x in free) and elapsed<=180)
        result=0 if good else 2
    return result

if __name__=='__main__':sys.exit(main())
