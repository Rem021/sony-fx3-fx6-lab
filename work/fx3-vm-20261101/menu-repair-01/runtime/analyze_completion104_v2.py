"""Read-only AP104 trace analysis; output is outside immutable runs."""
from pathlib import Path
import json,collections,struct,argparse,hashlib
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists();assert not a.output.resolve().is_relative_to(a.run.resolve());rows=[];truncated=0
for line in(a.run/'ap104-observations.jsonl').read_text().splitlines():
 try:rows.append(json.loads(line))
 except json.JSONDecodeError:truncated+=1
byindex={r['index']:r for r in rows};targets={r['destination_QID']for r in rows if r['point']['label']=='original_SendDrawComp_enter'};targets.update(r['destination_QID']for r in rows if r['point']['label']=='first_unfetched_return');lifetime=[];sends=[];epochs={};pending=[];first=None
for r in rows:
 label=r['point']['label'];qid=r.get('destination_QID');claim=r.get('new_observation_epoch');release=r.get('released_observation_epoch')
 if claim and claim['expected_published_QID']in targets:
  epochs[(claim['expected_published_QID'],claim['observation_epoch'])]={'identity':claim,'claim':r['index'],'release':None,'native_SendDrawComp_entries':[]};lifetime.append(r)
 if release and release['expected_published_QID']in targets:
  e=epochs.setdefault((release['expected_published_QID'],release['observation_epoch']),{'identity':release,'claim':None,'release':None,'native_SendDrawComp_entries':[]});e['release']=r['index'];lifetime.append(r)
 if qid in targets:
  lifetime.append(r)
  if label=='original_SendDrawComp_enter':
   entry={'record':r['index'],'call_path':r['call_path'],'status_raw':r.get('status_raw'),'owner_epoch':r.get('observed_owner_epoch'),'native_tid_mapping':r.get('thread'),'caller_PC':r.get('caller_PC')};sends.append(entry);ep=entry['owner_epoch']
   if ep:epochs.setdefault((ep['expected_published_QID'],ep['observation_epoch']),{'identity':ep,'claim':None,'release':None,'native_SendDrawComp_entries':[]})['native_SendDrawComp_entries'].append(entry)
  if label=='first_unfetched_return':first=r
# Decode the saved original caller link and module where supplied by original FP frame.
for r in lifetime:
 f=r.get('original_frame_module8c_and_saved_link80',{});raw=f.get('raw')
 if raw and len(bytes.fromhex(raw))==16:
  b=bytes.fromhex(raw);r['decoded_saved_original_caller_PC']=hex(struct.unpack_from('<Q',b)[0]);r['decoded_original_module_w']=hex(struct.unpack_from('<I',b,12)[0])
lines=(a.run/'serial.log').read_text(errors='replace').splitlines();adapter=[x for x in lines if x.startswith('FX3_GPE104_')and any(t in x for t in ['COMPLETE_','CB_','CMD_RETURN'])];complete=(a.run/'receipt.json').exists()
v={'run':str(a.run.resolve()),'immutable_run_receipt_exists':complete,'rows_read':len(rows),'partial_JSONL_rows_ignored':truncated,'scope':'Native instruction observation order; debug stepping changes scheduling. UART sequence alone is not cross-thread happens-before. observation_epoch counts original claim stores, not a new firmware generation field.','target_QIDs_observed_from_actual_SendDrawComp_or_error':sorted(targets),'native_point_counts':dict(collections.Counter(r['point']['label']for r in rows)),'target_owner_epochs':{str(k):v for k,v in epochs.items()},'native_SendDrawComp_entries':sends,'multiple_native_SendDrawComp_entries_in_one_observed_owner_epoch':[e for e in epochs.values()if len(e['native_SendDrawComp_entries'])>1],'first_unfetched':first,'target_lifetime_rows':lifetime,'passive_adapter_log_lines':adapter,'no_completion_semantics_modified':True};a.output.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'output':str(a.output),'rows':len(rows),'target_epochs':len(epochs),'native_sends':len(sends),'multiple_send_epochs':len(v['multiple_native_SendDrawComp_entries_in_one_observed_owner_epoch']),'first_unfetched':None if first is None else first['index']}))
