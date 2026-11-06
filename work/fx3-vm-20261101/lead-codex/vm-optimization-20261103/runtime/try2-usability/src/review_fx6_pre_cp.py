#!/usr/bin/env python3
"""Read-only verification of the one owner-run FX6 pre-CP receipt."""
import fcntl
import hashlib
import json
import os
from pathlib import Path

ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac')
RUN=ROOT/'work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/runs/fixed-fx3-4571c53b'
OUT=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx6-precp-first-result-review.json'
LOCKS=[ROOT/'outputs/fx3-vm/.run.lock',ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/.run.lock']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rec=json.loads((RUN/'run-receipt.json').read_text())
    serial=(RUN/'serial.log').read_bytes()
    assert sha(RUN/'serial.log')==rec['logs']['serial.log']['sha256']
    assert rec['mode']=='pre-cp-first-result' and rec['reason']=='cp_helper_insmod_rc'
    assert rec['serial_observation']['cp_helper_rc']==7
    assert rec['qemu_exit']==0 and rec['process_reaped'] and rec['locks_released']
    for literal in (b'FX3_FILE103_READY_CONFIRMED',b'FX3_BACKUP_CP_INSMOD_BEGIN',b'FX3_SYNC100_DISABLED reason=binding_failure',b'FX3_BACKUP_CP_INSMOD_RC=7',b'FX3_BACKUP_CP_OWNER_FAILED'):
        assert literal in serial,literal
    locks=[]
    for path in LOCKS:
        with path.open('rb') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
            except BlockingIOError:free=False
            if free:fcntl.flock(f,fcntl.LOCK_UN)
        locks.append({'path':str(path),'free':free,'bytes':path.stat().st_size,'sha256':sha(path)})
    pid=rec['qemu_pid']
    try:os.kill(pid,0);pid_absent=False
    except ProcessLookupError:pid_absent=True
    out={'schema':'fx6-fixed-platform-pre-cp-owner-review-v1','run':str(RUN),'receipt_sha256':sha(RUN/'run-receipt.json'),'serial_sha256':sha(RUN/'serial.log'),'serial_bytes':len(serial),'runner_sha256':sha(RUN.parent.parent/'fixed_runner.py'),'stop_reason':rec['reason'],'cp_helper_rc':7,'original_kernel_result':'first_modules_and_pre_cp_helper_refusal_only','fx6_cp_ap_av_result':'NOT_TESTED','qemu_pid':pid,'qemu_exit':rec['qemu_exit'],'process_reaped':rec['process_reaped'],'pid_absent':pid_absent,'locks':locks,'polling_is_not_CPU_breakpoint':True}
    assert pid_absent and all(x['free'] for x in locks)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(OUT)
if __name__=='__main__':main()
