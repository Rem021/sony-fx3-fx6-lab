#!/usr/bin/env python3
"""Read-only, byte-oriented inspection of pinned historical windows."""
from pathlib import Path
import json,re,struct,hashlib
HERE=Path(__file__).resolve().parent;DEL=HERE.parent
BASE=0x41dc00000;END=BASE+0x10000

def records(raw,cut):
 # Strict complete LF records only: never borrow LF from after End/window cut.
 data=raw[:cut];start=0
 for m in re.finditer(b'\n',data):
  end=m.end();yield start,data[start:end];start=end

def main():
 result={}
 for tag in ['r31','r28','r26','r26b']:
  old=json.loads((DEL/'r32-zero-ring-causal-review'/(tag+'-ANALYSIS.json')).read_text());run=Path(old['run']);raw=(run/'serial.log').read_bytes();w=old['windows']['comparison'];cut=w['cut'];found=[]
  for at,line in records(raw,cut):
   if b'FX3_GPE_RESOURCE_REGISTER ' not in line:continue
   if not line.startswith(b'FX3_GPE_RESOURCE_REGISTER '):continue
   fields={k.decode():v.decode(errors='replace') for k,v in re.findall(rb'([A-Za-z0-9_]+)=([^\s]+)',line)}
   lo=int(fields['phys'],0);n=int(fields['bytes'],0)
   found.append(dict(offset=at,fields=fields,ui_overlap=lo<END and BASE<lo+n))
  head=(run/'ui-gate-counters.bin').read_bytes()[:64];q=struct.unpack('<8Q',head)
  result[tag]=dict(run=str(run),cut=cut,scope=w['scope'],NUL_bytes_full=raw.count(b'\0'),registered_records=len(found),ui_overlapping_registered_records=sum(x['ui_overlap'] for x in found),records=found,post_End_header_qwords=[hex(x) for x in q],post_End_UI_pid=q[4],no_record_is_NOT_proof_of_impossible_range=True)
 (HERE/'HISTORICAL-WRITERS.json').write_text(json.dumps(result,indent=2)+'\n')
 # Isolated parser check: a token completed after cut cannot qualify its record.
 assert list(records(b'FX3_GPE_RESOURCE_REGISTER phys=0x41dc00000 bytes=0x10000\n',20))==[]
 assert len(list(records(b'good\npartial',12)))==1
 print(json.dumps({k:{'registered_records':v['registered_records'],'UI_overlaps':v['ui_overlapping_registered_records'],'post_End_UI_pid':v['post_End_UI_pid'],'cut':v['cut']} for k,v in result.items()},indent=2))
if __name__=='__main__':main()
