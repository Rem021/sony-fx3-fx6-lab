#!/usr/bin/env python3
"""Focused test for an interleaved printk marker; never runs a VM."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trial_log_v3_usability import FullLogMonitor

lines = {
 'worker': 'FX3_DATE99_WORKER_READY serialized=1 native_OSAL_waitable_thread=1\n',
 'date98': 'FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=0x909005c5\n',
 'owner': 'FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=0\n',
 'accept': 'FX3_DATE99_ACCEPT transaction=1 reason=4 source=0x809005c5 original_request_queue_owned=1\n',
 'commit': 'FX3_DATE99_CLOCK_COMMIT transaction=1 generation=1 reason=4 valid_UTC=1 AP_type=0 UTC_base_ms=1 mono_basis_ns=2 now_ns=3 RTT_ns=1 readback_UTC_ms=1 software_clock_advances=1\n',
 'retired': 'FX3_DATE99_RETIRED transaction=1 reason=4 result=0 native_request_free=0 type4_sent=0 generation=1\n',
}
def check(parts, expected, fail=False):
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/'serial.log'; p.touch()
  m=FullLogMonitor(p,['FX3_DATE99_CONSUMER_BOUND'])
  for part in parts:
   with p.open('a') as f: f.write(part)
   m.poll()
  assert m.markers['FX3_DATE99_CONSUMER_BOUND'] == expected, (m.markers,m.marker_evidence)
  assert bool(m.failure) == fail, m.failure
  return m.marker_evidence['FX3_DATE99_CONSUMER_BOUND']

alltext=''.join(lines.values())
assert check([alltext],True)['method']=='semantic_after_interleaved_literal'
for missing in lines:
 check([''.join(v for k,v in lines.items() if k!=missing)],False)
check([alltext.replace('result=0 native_request_free=0','result=-1 native_request_free=0')],False)
check([alltext.replace('result=0\n','result=-1\n')],False)
check([alltext.replace('software_clock_advances=1','software_clock_advances=')],False)
check([alltext.replace('transaction=1 generation=1 reason=4','transaction=2 generation=1 reason=4')],False)
check([alltext+'FX3_DATE99_REJECT reason=transaction_failed\n'],False,True)
split=[alltext[:i] for i in []]
segments=[alltext[i:i+7] for i in range(0,len(alltext),7)]
assert check(segments,True)['transaction']==1
print('DATE99 semantic positive, six missing-field negatives, failure/mismatch negatives, and cross-poll fragmented positive PASS')
