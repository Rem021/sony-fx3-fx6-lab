#!/usr/bin/env python3
"""Single owner-only, zero-key diagnostic bridge observation candidate.

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
MAC=HERE.parents[7]
DONOR=HERE.parents[2]
PARENT=DONOR/'hybrid-ap-candidate'
FX3_RUNTIME=MAC/'work/fx3-vm-20261101/menu-repair-01/runtime'
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0,str(HERE.parent))
sys.path.insert(0,str(PARENT))
import run_ap_once as frozen
sys.path.insert(0,str(FX3_RUNTIME))
from gdb_sysregs104_v2 import Sysregs
from readonly_probe import sha


AP_ELF=HERE/'appFw-bridge.so'
CAP_ELF=FX3_RUNTIME/'helpers/fx3-capid-v49-touch100.so'
HISTORICAL= PARENT/'runs/fx6ap-bb7588e5/serial.log'
AP_SHA='c31bc293816db5d63cc5acf6b019bd69c9dd7b940ae0ece1ea6977ff9b944db1'
BRIDGE_SHA='b5d546eb2843c819ebdcab1cda2ce7530beb30afece48d378b470c1555b2428b'
CANDIDATE_SHA='8abed37418a0f07e8193228ca2242f185103b6b5f98959b98821bbeeb3ad3b5d'
GUEST_PROBE_SHA='6f40e30e62fde9eddd74d547da8d6f3ab0d13be59413204632a232bc1d449aec'
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

from guest_probe import Probe
from mpr_probe import choose_early_im, IM_ELF, MPR_ELF, MPR_SHA

def quit_without_guest_resume(qemu,qmp,cleanup,reason):
    """Fault/unknown cleanup: never execute BRK, threshold consumer, or unguarded Init."""
    cleanup['attempted']=True
    cleanup['reason']=reason
    cleanup['API16_restored']=False
    cleanup['API16_restore_skipped_to_preserve_fault_stop']=True
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
    if sys.argv[1:] not in (['--reviewed-run'],['--preflight']):
        raise SystemExit('Choose --preflight (no VM) or owner-approved --reviewed-run')
    if sha(HERE.parents[1]/'readonly_probe.py') != '7da87fbb920bfa6a9516421d1224813056ff991a2c950552c4ccdadc662bbade':
        raise RuntimeError('observer implementation changed; re-audit before runtime')
    if sha(HERE.parents[1]/'two_phase_identity.py') != IDENTITY_SHA:
        raise RuntimeError('two-phase identity implementation changed; re-audit before runtime')
    for p,h in [(PARENT/'run_ap_once.py',PARENT_SHA),(AP_ELF,AP_SHA),(CAP_ELF,CAP_SHA),
                (HISTORICAL,HIST_SHA),(IM_ELF,'87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec'),(MPR_ELF,MPR_SHA),(FX3_RUNTIME/'gdb_sysregs104_v2.py',SYSREG_SHA)]:
        if sha(p)!=h:raise RuntimeError('frozen input drift '+str(p))
    qsrc=FX3_RUNTIME/'qemu-display-build/sources/qemu-11.1.2/gdbstub'
    for p,h in [(qsrc/'gdbstub.c',QEMU_GDB_SHA),(qsrc/'system.c',QEMU_SYSTEM_SHA)]:
        if sha(p)!=h:raise RuntimeError('QEMU GDB protocol source drift '+str(p))
    tests=json.loads((HERE/'host-tests.json').read_text())
    if (tests.get('status')!='PASS_NO_QEMU' or tests.get('guest_probe_sha256')!=GUEST_PROBE_SHA
            or sha(HERE/'guest_probe.py')!=GUEST_PROBE_SHA):
        raise RuntimeError('host-only observer tests missing or stale')
    plan=json.loads((HERE/'static-receipt.json').read_text())
    if (plan.get('status')!='STATIC_VERIFIED_NOT_RUN' or plan.get('candidate_sha256')!=CANDIDATE_SHA
            or plan.get('bridge_sha256')!=BRIDGE_SHA
            or sha(HERE/'guest-veneer.cpio')!=CANDIDATE_SHA or sha(HERE/'libfx6diag.so')!=BRIDGE_SHA):
        raise RuntimeError('new CPIO static audit absent/stale')
    elf_audit=json.loads((HERE/'elf-audit.json').read_text())
    if (elf_audit.get('status')!='ELF_STATIC_AUDITED_NOT_LOADED'
            or elf_audit.get('bridge_sha256')!=BRIDGE_SHA
            or elf_audit.get('patched_ap_sha256')!=AP_SHA):
        raise RuntimeError('bridge ELF contract audit absent/stale')
    baseline,audit=frozen.verify() # includes UUID, full CPIO, kernel, DTB, 17 helpers and exact allowlist.
    if sys.argv[1:] == ['--preflight']:
        print(json.dumps({'status':'PREFLIGHT_NO_QEMU','old_candidate_sha256':frozen.PINS['candidate'],
                          'new_candidate_sha256':plan['candidate_sha256'],
                          'guest_probe_sha256':sha(HERE/'guest_probe.py'),
                          'runner_sha256':sha(__file__),
                          'fixed_argv_count':len(baseline['fx3_vm_command'])},indent=2))
        return 0
    held=[]
    for path in frozen.LOCKS:
        f=path.open('rb')
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            for old in held:fcntl.flock(old,fcntl.LOCK_UN);old.close()
            raise RuntimeError('fixed FX3 double lock busy; no QEMU started')
        held.append(f)
    run=HERE/'runs'/('guest-veneer-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True);run.chmod(0o700)
    args=list(baseline['fx3_vm_command']);args[20]='file:'+str(run/'serial.log')
    args[31]='loader,file='+str(HERE/'guest-veneer.cpio')+',addr=0x440000000,force-raw=on'
    frozen_args=baseline['fx3_vm_command']
    if len(args)!=34 or any(args[i]!=frozen_args[i] for i in range(34) if i not in (20,31)):
        raise RuntimeError('frozen QEMU argv mismatch')
    env=os.environ.copy();env.update(baseline['model_env'])
    (run/'command.json').write_text(json.dumps({'args':args,'cwd':str(run),'model_env':baseline['model_env'],
        'key_budget':0,'observation_seconds':120,'total_seconds':180,'fixed_delta_indices':[20,31],
        'parent_runner_sha256':PARENT_SHA,'probe_sha256':sha(HERE/'guest_probe.py')},indent=2)+'\n')
    (run/'source-sha256.json').write_text(json.dumps({
        'runner':sha(__file__),'probe':sha(HERE/'guest_probe.py'),
        'parent_runner':PARENT_SHA,'sysregs':SYSREG_SHA,'identity':IDENTITY_SHA,
        'host_tests':sha(HERE/'host-tests.json')},indent=2)+'\n')
    for name in ['run_guest_once.py','guest_probe.py']:
        shutil.copyfile(HERE/name,run/('observer-'+name))
    shutil.copyfile(HERE.parent/'mpr_probe.py',run/'observer-mpr_probe.py')
    for name in ['readonly_probe.py','two_phase_identity.py']:
        shutil.copyfile(HERE.parents[1]/name,run/('observer-'+name))
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
                        mapping=choose_early_im(serial,IM_ELF)
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
                # This first diagnostic cannot prove asynchronous thunk
                # quiescence even when Init returns zero. Never resume after
                # removing Z1. The disposable guest is stopped then quit.
                quit_without_guest_resume(qemu,qmp,cleanup,
                    'diagnostic_no_guest_resume_after_Z1_removal' if bp_cleanup['all_removed']
                    else 'unremoved_debug_breakpoint_no_guest_resume')
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
        pins={'baseline':sha(frozen.BASE),'source':sha(PARENT/'guest-three-entry.cpio'),
              'candidate':sha(HERE/'guest-veneer.cpio'),'ap':sha(AP_ELF),
              'bridge':sha(HERE/'libfx6diag.so'),'cap':sha(CAP_ELF)}
        pins_match=(pins=={'baseline':frozen.PINS['baseline'],
                           'source':frozen.PINS['candidate'],
                           'candidate':plan['candidate_sha256'],'ap':AP_SHA,
                           'bridge':plan['bridge_sha256'],'cap':CAP_SHA})
        receipt={'schema':'fx6-guest-veneer-readonly-gdb-v1','stop':stop,'host_error':error,
          'elapsed_seconds':elapsed,'qemu_exit':None if qemu is None else qemu.returncode,
          'qemu_reaped':qemu is None or qemu.poll() is not None,
          'cleanup':cleanup,'breakpoint_cleanup':bp_cleanup,'locks':free,
          'inputs_sha256_after':pins,'inputs_unchanged':pins_match,'serial':frozen.extract(run/'serial.log'),
          'health':watcher.snapshot(),'probe_stage':None if probe is None else probe.stage}
        print(json.dumps({'run':str(run),'stop':stop,'error':error,'bp_removed':bp_cleanup['all_removed'],
            'api16_restored':cleanup['API16_restored'],'elapsed':elapsed},ensure_ascii=False),flush=True)
        captured=(stop in ('ap_return_captured','unknown_callback_captured','bridge_failstop',
                           'enterrec_blocked','writer_threshold_before_record_gate')
              and error is None and probe is not None and probe.gate_installed
              and probe.records
              and bp_cleanup['all_removed'] and qemu is not None and qemu.returncode==0
              and pins_match and all(x['free'] for x in free) and elapsed<=180)
        lifecycle_ok=False # no guest resume/API16 by design in diagnostic mode
        receipt['diagnostic_captured']=bool(captured)
        receipt['lifecycle_healthy']=bool(lifecycle_ok)
        receipt['API16_restore_policy']='SKIPPED_TO_AVOID_UNGUARDED_ASYNC_BRK'
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
        result=0 if captured else 2
    return result

if __name__=='__main__':sys.exit(main())
