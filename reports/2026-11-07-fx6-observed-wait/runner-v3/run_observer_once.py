#!/usr/bin/env python3
"""One locked observer run; one QMP owner, Unix GDB gate, explicit delivery limits."""
import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import socket
import subprocess
import sys
import time
import uuid

UUID = 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
BASE_SHA = 'fd945eaa7ba97f297f0a8073f0072416add4fb0af480efe8e28e6b5d76c9dcef'
PARENT_OBSERVER_SHA = 'd5732c03c54f76f676a5fbf42fd2256715ae2afce42f9f6ddbf4e537d6c954fe'
PARENT_CPIO_SHA = 'd02c7909458dcf8dff73fdf426953d07034cb386f8c8bd0bbd40a9440d32569e'
PARENT_PROOF_SHA = '849a5e4d1cce49002481678dd880ea64c7c24e2ab409b399efe34740528529d3'
CP = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''): h.update(block)
    return h.hexdigest()


def normalize_gdb_argv(argv):
    """Remove only a terminal duplicate -s; retain the existing Unix key gate."""
    result = list(argv)
    if '-s' in result:
        if result.count('-s') != 1 or result[-1] != '-s':
            raise RuntimeError('unexpected nonterminal/repeated -s')
        result.pop()
    if result.count('-gdb') != 1 or result[result.index('-gdb')+1] != 'chardev:keygate93':
        raise RuntimeError('expected the original Unix GDB gate')
    if result.count('socket,path=g,server=on,wait=off,id=keygate93') != 1:
        raise RuntimeError('expected the original Unix g chardev')
    return result


def runtime_argv(saved, run):
    argv = normalize_gdb_argv(saved['candidate_argv_before_observer_serial_retarget'])
    argv[argv.index('-serial')+1] = 'file:'+str(run/'serial.log')
    return argv


def verify_artifact(ref, label, pinned_sha=None):
    if not isinstance(ref, dict) or not all(k in ref for k in ('path','bytes','sha256')):
        raise RuntimeError(label+' reference missing fields')
    if not isinstance(ref['path'], str) or not isinstance(ref['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}',ref['sha256']):
        raise RuntimeError(label+' reference invalid')
    if type(ref['bytes']) is not int or ref['bytes'] < 0:
        raise RuntimeError(label+' byte size invalid')
    if pinned_sha is not None and ref['sha256'] != pinned_sha:
        raise RuntimeError(label+' pinned SHA mismatch')
    path = Path(ref['path'])
    if path.stat().st_size != ref['bytes'] or sha(path) != ref['sha256']:
        raise RuntimeError(label+' actual file changed')
    return path


def same_artifact(a, b, label):
    for ref in (a,b):
        if not isinstance(ref,dict) or not all(k in ref for k in ('path','bytes','sha256')):
            raise RuntimeError(label+' reference missing fields')
    if (Path(a['path']).resolve(),a['bytes'],a['sha256']) != (Path(b['path']).resolve(),b['bytes'],b['sha256']):
        raise RuntimeError(label+' references disagree')


def require_flags(diff, fields, label):
    if not all(diff.get(k) is True for k in fields):
        raise RuntimeError(label+' required proof flags missing/false')


def frozen_fields(saved, base, label):
    for key in ('kernel','dtb','backup','fx3_platform','model_env','owner_baseline'):
        if saved.get(key) != base[key]:
            raise RuntimeError(label+' unexpected baseline change: '+key)


def verify_observer_proof(saved, base, diff):
    if diff.get('schema') != 'fx6-observer-only-member-diff-v1':
        raise RuntimeError('unknown observer member proof schema')
    require_flags(diff,('all_other_payloads_and_headers_identical','original_order_preserved',
                       'original_post_trailer_records_preserved'),'observer')
    same_artifact(diff.get('baseline'),base['initrd'],'observer baseline CPIO')
    same_artifact(diff.get('candidate'),saved['initrd'],'observer derived CPIO')
    verify_artifact(diff['baseline'],'observer baseline CPIO')
    verify_artifact(diff['candidate'],'observer derived CPIO')


def verify_member_proof(saved, base):
    proof_path = verify_artifact(saved.get('input_member_diff_verification'),'member diff proof')
    diff = json.loads(proof_path.read_text())
    schema = diff.get('schema')
    if schema == 'fx6-observer-only-member-diff-v1':
        verify_observer_proof(saved,base,diff)
        return
    if schema != 'fx6-wait-snapshot-member-diff-v1':
        raise RuntimeError('unknown member proof schema')
    require_flags(diff,('all_other_raw_records_byte_identical','original_order_preserved',
        'both_original_trailer_records_byte_identical','appfw_launcher_observer_shim_backup_unchanged'),'snapshot')
    same_artifact(diff.get('derived_cpio'),saved['initrd'],'snapshot derived CPIO')
    verify_artifact(diff['derived_cpio'],'snapshot derived CPIO')
    parent_path = verify_artifact(saved.get('parent_observer_manifest'),'parent observer manifest',PARENT_OBSERVER_SHA)
    parent = json.loads(parent_path.read_text())
    frozen_fields(parent,base,'parent observer')
    same_artifact(parent.get('baseline_manifest'),saved.get('baseline_manifest'),'parent 295 manifest')
    same_artifact(parent.get('baseline_initrd'),base['initrd'],'parent 295 CPIO')
    same_artifact(diff.get('parent_observer_cpio'),saved.get('parent_observer_initrd'),'snapshot parent CPIO')
    same_artifact(diff['parent_observer_cpio'],parent.get('initrd'),'parent manifest CPIO')
    verify_artifact(diff['parent_observer_cpio'],'parent observer CPIO',PARENT_CPIO_SHA)
    parent_proof_path = verify_artifact(parent.get('input_member_diff_verification'),'parent observer proof',PARENT_PROOF_SHA)
    verify_observer_proof(parent,base,json.loads(parent_proof_path.read_text()))


def check(path, expected):
    v = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', '/Volumes/KAFU2T']))
    if v.get('VolumeUUID') != UUID: raise RuntimeError('wrong external volume')
    if sha(path) != expected: raise RuntimeError('candidate manifest changed')
    saved = json.loads(path.read_text())
    base_path = CP/'vm-candidate-gpecap25-295.json'
    if sha(base_path) != BASE_SHA: raise RuntimeError('295 baseline changed')
    base = json.loads(base_path.read_text())
    frozen_fields(saved,base,'candidate')
    base_ref = {'path':str(base_path),'bytes':base_path.stat().st_size,'sha256':BASE_SHA}
    same_artifact(saved.get('baseline_manifest'),base_ref,'candidate 295 manifest')
    same_artifact(saved.get('baseline_initrd'),base['initrd'],'candidate 295 CPIO')
    verify_member_proof(saved,base)
    for key in ('kernel', 'dtb', 'backup', 'initrd'):
        if sha(saved[key]['path']) != saved[key]['sha256']: raise RuntimeError(key+' input changed')
    owner = saved['owner_baseline']
    if sha(owner['path']) != owner['sha256']: raise RuntimeError('platform baseline changed')
    platform = json.loads(Path(owner['path']).read_text())
    qemu = platform['sha256']['qemu_binary']
    if sha(qemu['path']) != qemu['sha256']: raise RuntimeError('QEMU changed')
    expected_argv = base['candidate_argv_before_observer_serial_retarget'].copy()
    for i, value in enumerate(expected_argv):
        if value.startswith('loader,file=') and base['initrd']['path'] in value:
            expected_argv[i] = value.replace(base['initrd']['path'], saved['initrd']['path'])
    if normalize_gdb_argv(expected_argv) != normalize_gdb_argv(saved['candidate_argv_before_observer_serial_retarget']):
        raise RuntimeError('argv differs beyond the new initrd')
    if expected_argv[0] != qemu['path']: raise RuntimeError('wrong QEMU argv')
    return saved, base


class QMP:
    def __init__(self, run):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        previous = Path.cwd()
        try:
            os.chdir(run); self.sock.connect('q')
        finally: os.chdir(previous)
        self.reader = self.sock.makefile('rb')
        if 'QMP' not in json.loads(self.reader.readline()): raise RuntimeError('bad QMP greeting')
        self.number = 0

    def call(self, command, arguments=None):
        self.number += 1
        request = {'execute': command, 'id': self.number}
        if arguments is not None: request['arguments'] = arguments
        self.sock.sendall((json.dumps(request)+'\n').encode())
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            self.sock.settimeout(max(.05, min(3, deadline-time.monotonic())))
            line = self.reader.readline()
            if not line: raise RuntimeError('QMP closed')
            item = json.loads(line)
            if item.get('id') == self.number:
                if 'error' in item: raise RuntimeError('QMP '+repr(item['error']))
                return item.get('return')
        raise TimeoutError('QMP reply deadline')

    def close(self):
        self.reader.close(); self.sock.close()


def execute(manifest, manifest_sha, saved, base):
    sys.path.insert(0, str(CP.parent))
    import fixed_runner as fr
    held = fr.acquire()  # Existing two owner locks; never steal or recreate them.
    proc, qmp, gate = None, None, None
    run = manifest.parent/'runs'/('observer-'+uuid.uuid4().hex[:10])
    receipt = {'schema': 'fx6-observer-owned-run-v2', 'manifest_sha256': manifest_sha,
        'baseline_manifest_sha256': BASE_SHA, 'manifest': str(manifest),
        'maximum_seconds': 120, 'runner_sha256': sha(__file__), 'fixed_runner_sha256': sha(fr.__file__),
        'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'key_operations': [], 'key_attempts': [], 'captures': [],
        'gdb_endpoint': 'unix:g via chardev:keygate93; terminal duplicate -s removed',
        'key_evidence_scope': 'software gate write/readback only; guest consumption and native UI response unproven'}
    start = time.monotonic()
    reason, error = 'not_started', None
    try:
        once = manifest.parent/('.started-'+manifest_sha)
        fd = os.open(once, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f: json.dump({'run': str(run), 'manifest_sha256': manifest_sha}, f)
        run.mkdir(parents=True, mode=0o700)
        argv = runtime_argv(saved, run)
        env = os.environ.copy(); env.update(saved['model_env'])
        (run/'command.json').write_text(json.dumps({'argv': argv, 'model_env': saved['model_env'],
            'manifest_sha256': manifest_sha, 'authorization': 'user requested continuing repair; bounded diagnostic derived295'}, indent=2)+'\n')
        with (run/'host-stdout.log').open('wb') as out, (run/'host-stderr.log').open('wb') as err:
            proc = subprocess.Popen(argv, cwd=run, env=env, stdout=out, stderr=err,
                                    start_new_session=True, preexec_fn=fr.limits)
        start = time.monotonic(); deadline = start+120
        while not (run/'q').exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        if proc.poll() is not None: raise RuntimeError('QEMU exited before QMP')
        qmp = QMP(run); qmp.call('qmp_capabilities')
        regs = qmp.call('human-monitor-command', {'command-line': 'info registers'})
        cpus = qmp.call('query-cpus-fast')
        receipt['startup_probe'] = {'registers': regs, 'cpus': cpus}
        if 'PC=0000000400000000' not in regs or 'X00=0000000000000000' not in regs:
            raise RuntimeError('frozen startup PC/x0 mismatch')
        if len(cpus) != 4 or any(x.get('qom-type') != 'cortex-a35-arm-cpu' for x in cpus):
            raise RuntimeError('frozen CPU mismatch')
        qmp.call('cont'); reason = 'wall_timeout'
        print(json.dumps({'started': str(run), 'pid': proc.pid}), flush=True)
        keys = [(1,0x1ab),(2,0x30),(3,0x1ac),(4,0x1af)]
        key_index, capture_done, serial_offset, text = 0, False, 0, ''
        key_failed = False
        cp_begin_at = None
        while time.monotonic() < deadline and proc.poll() is None:
            serial = run/'serial.log'
            if serial.exists():
                with serial.open('rb') as f:
                    f.seek(serial_offset); chunk=f.read(); serial_offset=f.tell()
                text += chunk.decode('utf-8', 'replace')
            if any(m in text for m in ('Kernel panic','Oops:','Unable to handle kernel','Internal error:','SError Interrupt')):
                reason='kernel_fault_marker'; break
            obs = fr.serial_observation(text.encode('utf-8'))
            if obs['cpuset_not_ready']:
                reason='cpuset_not_ready'; break
            if obs['pre_cp_first_negative_line']:
                reason='pre_cp_first_negative'; break
            if obs['cp_helper_rc'] is not None and obs['cp_helper_rc'] != 0:
                reason='cp_helper_insmod_rc'; break
            if obs['cp_helper_begin'] and cp_begin_at is None:
                cp_begin_at=time.monotonic()
            if cp_begin_at is not None and obs['cp_helper_rc'] is None and 'FX3_BACKUP_CP_INSMOD_RC=0' not in text and time.monotonic()-cp_begin_at >= 40:
                reason='cp_helper_no_rc_40s'; break
            if not key_failed and key_index < len(keys) and time.monotonic()-start >= 35+key_index*3:
                step, key = keys[key_index]
                try:
                    if gate is None:
                        sys.path.insert(0, '/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime')
                        from gate_input96 import InputGate
                        gate = InputGate(run)
                    qmp.call('stop')
                    try: item=gate.command(step,key,100,'native-screen-unverified',
                                          'bounded diagnostic key sequence; no verified native menu')
                    finally: qmp.call('cont')
                    (run/f'keyinject-step{step}.json').write_text(json.dumps(item,indent=2)+'\n')
                    receipt['key_operations'].append({'step':step,'recorded':True,
                        'delivery':'software_gate_write_readback','guest_consumption':'unproven','native_ui_response':'unverified'})
                    receipt['key_attempts'].append({'step':step,'key':hex(key),
                        'delivery':'software_gate_write_readback','guest_consumption':'unproven','retry_suppressed':True})
                except Exception as exc:
                    key_failed=True; (run/'keyinject-error.txt').write_text(repr(exc)+'\n')
                    # A failure may follow an accepted write. Preserve unknown delivery and
                    # stop the sequence; never retry this or a later step in this run.
                    receipt['key_attempts'].append({'step':step,'key':hex(key),'delivery':'unknown',
                        'error':repr(exc),'retry_suppressed':True,'subsequent_steps_suppressed':True})
                key_index += 1
            if not capture_done and time.monotonic()-start >= 70:
                capture_done=True
                resources=re.findall(r'FX3_GPE_RESOURCE_REGISTER[^\n]*type=0x403[^\n]*logical=(0x[0-9a-f]+)[^\n]*phys=(0x[0-9a-f]+)[^\n]*bytes=(0x[0-9a-f]+)',text)
                if not resources: (run/'gpe-capture-error.txt').write_text('no GPE resource\n')
                else:
                    regions=[(f'gpe{i}',int(p,16),int(n,16)) for i,(_,p,n) in enumerate(resources)]
                    regions += [('dmm0400',0x4805a1000,0x800000),('dmm0403',0x429550000,0x12d000)]
                    for label,phys,size in regions:
                        if not 0<size<=16*1024*1024: raise RuntimeError('capture size outside bound')
                        qmp.call('stop')
                        try: reply=qmp.call('human-monitor-command',{'command-line':f'pmemsave 0x{phys:x} 0x{size:x} {label}.bin'})
                        finally: qmp.call('cont')
                        receipt['captures'].append({'label':label,'phys':hex(phys),'bytes':size,'reply':reply})
            time.sleep(.1)
        if proc.poll() is not None: reason='qemu_exited'
    except BaseException as exc:
        error=repr(exc); reason='interrupted' if isinstance(exc,(KeyboardInterrupt,SystemExit)) else 'error'
    finally:
        if qmp:
            try: qmp.call('quit')
            except Exception: pass
        if proc:
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                for sig, seconds in [(signal.SIGTERM,3),(signal.SIGKILL,3)]:
                    if proc.poll() is None:
                        try: os.killpg(proc.pid,sig)
                        except ProcessLookupError: pass
                        try: proc.wait(timeout=seconds)
                        except subprocess.TimeoutExpired: continue
        if qmp:
            try: qmp.close()
            except Exception: pass
        for lock in reversed(held): fcntl.flock(lock,fcntl.LOCK_UN); lock.close()
    receipt.update(reason=reason,error=error,elapsed_seconds=time.monotonic()-start,
        process_reaped=proc is None or proc.poll() is not None,locks_released=True,
        qemu_pid=None if proc is None else proc.pid,qemu_exit=None if proc is None else proc.returncode)
    if run.exists():
        receipt['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in run.iterdir() if p.is_file()}
        text=(run/'serial.log').read_text(errors='replace') if (run/'serial.log').exists() else ''
        receipt['observations']={'receive_entries':text.count('FX6_QUEUE_OBS_ENTER'),
            'receive_exits':text.count('FX6_QUEUE_OBS_EXIT'),'native_asserts':len(re.findall(r'assert at|Assertion .*failed',text)),
            'appfw_segv':text.count('APPFW_SEGV'),'menu_proven':False}
        (run/'run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--manifest-sha',required=True)
    group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--check',action='store_true');group.add_argument('--run',action='store_true')
    args=ap.parse_args();path=args.manifest.resolve();saved,base=check(path,args.manifest_sha)
    if args.check: print(json.dumps({'check':'passed','manifest_sha256':args.manifest_sha,'guest_started':False,
        'gdb_endpoint':'unix:g via chardev:keygate93','effective_argv':runtime_argv(saved,path.parent/'runs'/'CHECK_ONLY')}));return
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    result=execute(path,args.manifest_sha,saved,base);print(json.dumps(result,indent=2))
    if result['error']: raise SystemExit(1)


if __name__=='__main__': main()
