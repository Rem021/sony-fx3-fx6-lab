#!/usr/bin/env python3
"""Owner-only, locked FX6 Image substitution on the frozen FX3 platform."""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import plistlib
import re
import resource
import signal
import socket
import subprocess
import time
import uuid
from pathlib import Path

from fixed_platform import main as fixed_platform, HERE

MANIFEST=HERE/'fixed-kernel-candidate.json'
MANIFEST_SHA='42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c'
LOCKS=[HERE.parents[6]/'outputs/fx3-vm/.run.lock',HERE.parents[6]/'work/fx3-vm-20261101/menu-repair-01/runtime/.run.lock']
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def check():
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if volume.get('VolumeUUID')!=UUID:raise RuntimeError('wrong or unmounted external volume')
    if sha(MANIFEST)!=MANIFEST_SHA:raise RuntimeError('candidate manifest changed')
    saved=json.loads(MANIFEST.read_text())
    if saved!=fixed_platform():raise RuntimeError('candidate no longer matches runtime owner baseline')
    if saved['platform_changes'] or saved['other_firmware_payload_changes'] or len(saved['firmware_payload_changes'])!=1:
        raise RuntimeError('unreviewed platform or payload change')
    for path in LOCKS:
        if not path.is_file() or path.is_symlink():raise RuntimeError('missing shared runtime lock')
    args=saved['candidate_argv_before_observer_serial_retarget']
    if args[args.index('-kernel')+1]!=saved['firmware_payload_changes'][0]['to_path']:
        raise RuntimeError('unexpected kernel path')
    if args[args.index('-device')+1].split(',')[0] != 'loader':raise RuntimeError('unexpected loader')
    return saved


def qmp_send(sock,reader,cmd,id,arguments=None):
    request={'execute':cmd,'id':id}
    if arguments is not None:request['arguments']=arguments
    sock.sendall((json.dumps(request)+'\n').encode())
    while True:
        line=reader.readline()
        if not line:raise RuntimeError('QMP closed')
        data=json.loads(line)
        if data.get('id')==id:
            if 'error' in data:raise RuntimeError('QMP '+repr(data['error']))
            return data


def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024*1024,64*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def acquire():
    held=[]
    try:
        for path in LOCKS:
            stream=path.open('rb')
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                stream.close()
                raise RuntimeError('FX3 runtime lock occupied; no QEMU process started')
            held.append(stream)
        return held
    except BaseException:
        for stream in held:
            fcntl.flock(stream,fcntl.LOCK_UN);stream.close()
        raise


def connect_relative(sock,run_dir):
    previous_cwd=Path.cwd()
    try:
        os.chdir(run_dir)
        sock.connect('q')
    finally:
        os.chdir(previous_cwd)


def serial_observation(data):
    content=data.decode('utf-8','replace')
    lines=content.splitlines()
    version=next((line for line in lines if 'Linux version ' in line),None)
    faults=[marker for marker in ('Kernel panic','Oops:','Unable to handle kernel','Internal error:','SError Interrupt') if marker in content]
    completed=[line.rstrip('\r\n') for line in content.splitlines(keepends=True) if line.endswith('\n')]
    init_line=next((line for line in completed if re.fullmatch(r'FX3_DEVTMPFS_RC=-?\d+',line)),None)
    return {'first_line':lines[0] if lines else None,'linux_version_line':version,'fault_markers':faults,'init_boundary_line':init_line,'init_boundary_rc':int(init_line.split('=')[1]) if init_line else None,'ap_guard':'FX3_AP_NATURAL_BOOTIN_BEGIN' in content}


def run(saved,seconds,mode):
    extra=sorted(key for key in os.environ if key.startswith('FX3_VM_') and key not in saved['model_env'])
    if extra:raise RuntimeError('unreviewed inherited FX3_VM_* model variables: '+','.join(extra))
    held=acquire()  # same two locks and order as TRY2; refuse before run-dir creation
    process=None;sock=None;reader=None
    run_dir=HERE/'runs'/('fixed-fx3-'+uuid.uuid4().hex[:8])
    start=time.monotonic();reason='not_started';error=None;startup_probe={};first_serial_at=None
    try:
        run_dir.mkdir(parents=True,mode=0o700)
        args=saved['candidate_argv_before_observer_serial_retarget'].copy()
        args[args.index('-serial')+1]='file:'+str(run_dir/'serial.log')
        base=json.loads(Path(saved['owner_baseline']['path']).read_text())['fx3_vm_command']
        expected=base.copy()
        expected[expected.index('-kernel')+1]=saved['firmware_payload_changes'][0]['to_path']
        expected[expected.index('-serial')+1]='file:'+str(run_dir/'serial.log')
        if args!=expected:raise RuntimeError('argv differs beyond kernel payload and serial sink')
        env=os.environ.copy();env.update(saved['model_env'])
        (run_dir/'command.json').write_text(json.dumps({'argv':args,'model_env':saved['model_env'],'manifest_sha256':MANIFEST_SHA,'runtime_owner_only':True},indent=2)+'\n')
        with (run_dir/'host-stdout.log').open('wb') as stdout,(run_dir/'host-stderr.log').open('wb') as stderr:
            process=subprocess.Popen(args,cwd=run_dir,env=env,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
            deadline=time.monotonic()+seconds
            while not (run_dir/'q').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            if process.poll() is not None:raise RuntimeError('QEMU exited before QMP setup')
            if time.monotonic()>=deadline:raise TimeoutError('QMP setup timeout')
            sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(3)
            connect_relative(sock,run_dir)  # relative path, as in pinned TRY2
            reader=sock.makefile('rb');json.loads(reader.readline())
            qmp_send(sock,reader,'qmp_capabilities',1)
            # Match the original TRY2 startup QMP sequence, including pre-cont
            # register/CPU inspection. QEMU's unchanged boot stub initializes PC/x0.
            regs=qmp_send(sock,reader,'human-monitor-command',2,{'command-line':'info registers'}).get('return','')
            startup_probe['registers']=regs
            if 'PC=0000000400000000' not in regs or 'X00=0000000000000000' not in regs:
                raise RuntimeError('pre-cont PC/x0 differs from pinned historical QMP startup')
            cpus=qmp_send(sock,reader,'query-cpus-fast',3).get('return',[])
            startup_probe['cpu_count']=len(cpus)
            if len(cpus)!=saved['fx3_platform']['smp'] or any(x.get('qom-type')!='cortex-a35-arm-cpu' for x in cpus):
                raise RuntimeError('pre-cont CPU topology differs from baseline')
            qmp_send(sock,reader,'cont',4)
            reason='wall_timeout'
            while time.monotonic()<deadline:
                if process.poll() is not None:reason='qemu_exited';break
                serial=(run_dir/'serial.log').read_bytes() if (run_dir/'serial.log').exists() else b''
                obs=serial_observation(serial)
                if obs['fault_markers']:
                    reason='kernel_fault_marker';break
                if obs['ap_guard']:
                    reason='ap_guard_observed_stop';break
                if mode=='init-boundary' and obs['init_boundary_line']:
                    reason='guest_init_boundary';break
                if mode=='first-serial':
                    if obs['linux_version_line']:
                        reason='linux_version_marker';break
                    if serial and first_serial_at is None:first_serial_at=time.monotonic()
                    if first_serial_at is not None and time.monotonic()-first_serial_at>=2:
                        reason='first_serial_without_version';break
                time.sleep(.025)
    except BaseException as exc:
        error=repr(exc)
        if isinstance(exc,KeyboardInterrupt):reason='interrupted'
        elif isinstance(exc,TimeoutError):reason='wall_timeout'
        else:reason='error'
    finally:
        if sock is not None and reader is not None:
            try:qmp_send(sock,reader,'quit',5)
            except Exception:pass
        if process is not None:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=3)
        if reader is not None:reader.close()
        if sock is not None:sock.close()
        for stream in reversed(held):fcntl.flock(stream,fcntl.LOCK_UN);stream.close()
    logs={name:{'bytes':(run_dir/name).stat().st_size,'sha256':sha(run_dir/name)} for name in ('serial.log','host-stdout.log','host-stderr.log') if (run_dir/name).exists()}
    final_serial=(run_dir/'serial.log').read_bytes() if (run_dir/'serial.log').exists() else b''
    observed=serial_observation(final_serial)
    result={'schema':'fx6-image-only-frozen-fx3-run-v2','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'manifest_sha256':MANIFEST_SHA,'mode':mode,'reason':reason,'serial_observation':observed,'linux_version_marker':bool(observed['linux_version_line']),'startup_probe':startup_probe,'elapsed_seconds':time.monotonic()-start,'maximum_seconds':seconds,'qemu_pid':None if process is None else process.pid,'qemu_exit':None if process is None else process.returncode,'process_reaped':process is None or process.poll() is not None,'locks_released':True,'logs':logs,'error':error,'firmware_AP_CP_AV_result':'NOT_TESTED','polling_is_not_CPU_breakpoint':True}
    (run_dir/'run-receipt.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    return result


def main():
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true',help='hash and command audit only; no locks or QEMU')
    group.add_argument('--run',action='store_true',help='runtime owner only; acquire shared locks and run')
    ap.add_argument('--seconds',type=int,default=180)
    ap.add_argument('--mode',choices=['first-serial','init-boundary'],default='first-serial',help='host-only serial polling stop rule')
    ns=ap.parse_args()
    if not 1<=ns.seconds<=180:ap.error('seconds must be 1..180')
    saved=check()
    if ns.check:
        print(json.dumps({'status':'PASS_OFFLINE_FIXED_PLATFORM_ONLY','owner_baseline_sha256':saved['owner_baseline']['sha256'],'platform_changes':saved['platform_changes'],'payload_changes':saved['firmware_payload_changes'],'runtime_started':False},indent=2))
    else:
        print(json.dumps(run(saved,ns.seconds,ns.mode),indent=2,ensure_ascii=False))


if __name__=='__main__':main()
