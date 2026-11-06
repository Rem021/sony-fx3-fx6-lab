#!/usr/bin/env python3
"""No-QEMU host preflight, serial and cleanup tests for run_ap_once.py."""
import json
import tempfile
from pathlib import Path
import run_ap_once as r

HERE=Path(__file__).resolve().parent

class FakeQemu:
    pid=123456789
    def __init__(self):self.returncode=None;self.waited=[]
    def poll(self):return self.returncode
    def wait(self,timeout):self.waited.append(timeout);self.returncode=0;return 0

class FakeQMP:
    def __init__(self):self.calls=[];self.closed=False
    def call(self,name):self.calls.append(name);return {}
    def close(self):self.closed=True

class FakeSocket:
    def __init__(self):self.closed=False
    def close(self):self.closed=True

class FakeGate:
    def __init__(self):self.sock=FakeSocket()

def main():
    rows={}
    baseline,report=r.verify()
    assert report['member_count']==1140 and report['all_other_members_compared']==1137
    assert report['baseline_ELF_changed_or_missing']==['usr/bin/bootin.elf','usr/bin/im.elf']
    assert set(report['exact_full_cpio_allowlist'])=={'usr/bin/bootin.elf','usr/bin/im.elf','usr/lib/appFw.so'}
    rows['exact_preflight']={'passed':True,'identity_20_ELF_rejects':2,'full_CPIO_exceptions':3}
    original=r.PINS['candidate']
    try:
        r.PINS['candidate']='0'*64
        try:r.verify()
        except RuntimeError as exc:assert 'candidate SHA mismatch' in str(exc)
        else:raise AssertionError('wrong candidate pin accepted')
    finally:r.PINS['candidate']=original
    rows['wrong_candidate_denied']={'passed':True}
    with tempfile.TemporaryDirectory(prefix='host-test-',dir=HERE) as folder:
        serial=Path(folder)/'serial.log';watch=r.APHealthMonitor(serial)
        serial.write_bytes(b'FX3_TRACE_ABI_VERIFY_RC=0\nFX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word\nFX3_TRACE_ABI_VERIFY_RC=0 FX3_TRACE_ABI_VERIFY_RC=-')
        watch.poll();assert watch.failure is None and len(watch.diagnostics)==1
        with serial.open('ab') as f:f.write(b'7\n')
        watch.poll();assert watch.failure['kind']=='loader_nonzero'
        assert [x['value'] for x in watch.loader_observations['verify']]==[0,0,-7]
        rows['incremental_repeated_RC']={'passed':True,'values':[0,0,-7]}
        tail=Path(folder)/'tail.log';tail.write_bytes(b'program: symbol lookup error: missing')
        watch_tail=r.APHealthMonitor(tail);watch_tail.poll();assert watch_tail.failure is None
        watch_tail.finish();assert watch_tail.failure['kind']=='real_fault_or_unproven_guard'
        rows['unterminated_tail_fault']={'passed':True}
        q=FakeQemu();mp=FakeQMP();gate=FakeGate();receipt={'attempted':False,'API16_restored':False,'quit_sent':False}
        r.cleanup_owned(q,mp,gate,Path(folder),receipt,
                        restore_fn=lambda call,g,run,timeout:{'passed':True,'timeout':timeout})
        assert mp.calls==['stop','quit'] and q.waited==[5] and q.returncode==0
        assert receipt['API16_restored'] and receipt['quit_sent'] and mp.closed and gate.sock.closed
        rows['cleanup_success_fake']={'passed':True,'QMP':mp.calls,'own_process_reaped':True}
        q=FakeQemu();mp=FakeQMP();gate=FakeGate();receipt={'attempted':False,'API16_restored':False,'quit_sent':False}
        def reject(call,g,run,timeout):raise RuntimeError('restore failure fixture')
        r.cleanup_owned(q,mp,gate,Path(folder),receipt,restore_fn=reject)
        assert not receipt['API16_restored'] and 'restore_error' in receipt
        assert receipt['quit_sent'] and q.returncode==0 and mp.closed and gate.sock.closed
        rows['cleanup_restore_failure_fake']={'passed':True,'restore_gate_stays_false':True,'own_process_reaped':True}
    assert r.MAX_TOTAL<=180 and r.OBSERVE_LIMIT<=120 and len(r.LOCKS)==2
    assert 'ipc_send' not in r.MARKER_PATTERNS
    rows['budget_and_no_FX3_IPC_success_marker']={'passed':True}
    rows['classifier_fixtures']={'passed':True,'count':len(r.classify_serial.fixtures())}
    out={'status':'NO_QEMU_HOST_TESTS_PASS','cases':rows,'qemu_started':False,
         'candidate_sha256':original,'runner_sha256':r.sha(r.__file__)}
    (HERE/'host-tests.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'cases':len(rows),'qemu_started':False},indent=2))

if __name__=='__main__':main()
