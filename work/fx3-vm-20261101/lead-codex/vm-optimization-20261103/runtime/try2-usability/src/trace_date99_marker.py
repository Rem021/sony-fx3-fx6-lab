#!/usr/bin/env python3
"""Pin narrow raw serial ranges; no log rewriting."""
import json,re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
runs=['try2gapinternal-13b47129','try2gapinternal-47e2924a']
patterns={
 'literal_consumer_bound':rb'FX3_DATE99_CONSUMER_BOUND',
 'worker':rb'FX3_DATE99_WORKER_READY serialized=1[^\r\n]*',
 'registered_branch':rb'FX3_DATE98_KERNEL_OBSERVE_READY consumer99_replaces_passive_target=[^\r\n]*',
 'owner_result_zero':rb'FX3_BACKUP_CP_PUBLIC_OWNER exact_reset33=1 F1_then_F4_once=1 result=0[^\r\n]*',
 'accept_transaction1':rb'FX3_DATE99_ACCEPT transaction=1 reason=4 source=0x809005c5[^\r\n]*',
 'commit_transaction1':rb'FX3_DATE99_CLOCK_COMMIT transaction=1 generation=1 reason=4 valid_UTC=1[^\r\n]*',
 'retired_transaction1':rb'FX3_DATE99_RETIRED transaction=1 reason=4 result=0 native_request_free=0[^\r\n]*',
 'reject':rb'FX3_DATE99_REJECT[^\r\n]*',
}
result={}
for run in runs:
 p=root/'runs'/run/'serial.log'; data=p.read_bytes(); rows={}
 for key,pattern in patterns.items():
  m=re.search(pattern,data)
  rows[key]=None if m is None else {'byte_range':[m.start(),m.end()],'raw':m[0].decode(errors='replace')}
 target=b'FX3_DATFX3_BACKUP_CP_INSMOD_RC=0E9'
 pos=data.find(target)
 if pos>=0: rows['interleaved_raw']={'byte_range':[pos,pos+160],'raw':data[pos:pos+160].decode(errors='replace')}
 result[run]={'serial':str(p),'source_causal_files':['helpers/fx3-cp-backup-v4-sync100.c:51','helpers/fx3-date99-consumer-v1.h:18-32'],
              'literal_present':rows['literal_consumer_bound'] is not None,'evidence':rows}
(root/'date99-marker-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(root/'date99-marker-evidence.json')
