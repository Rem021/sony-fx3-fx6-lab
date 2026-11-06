#!/usr/bin/env python3
"""Independent offline reader; complete GPE CMD_RETURN lines only, one scoped run."""
import argparse,collections,json,re
from pathlib import Path
TAG=b'FX3_GPE104_CMD_RETURN'
NUM=rb'([0-9]{1,20})';HEX=rb'(0x[0-9a-f]+|0)'
RE=re.compile(rb'^FX3_GPE104_CMD_RETURN tid=([0-9]{1,10}) tpidr='+HEX+rb' ns='+NUM+rb' seq=([0-9]{1,10}) op=([014]) completion_source='+HEX+rb' result=(-?[0-9]{1,11}) errno=(-?[0-9]{1,11}) call_path=adapter_return_to_original_Main unchanged=1(?: entry_ns='+NUM+rb')?$')
class Parser:
 def __init__(self,run_id):
  if not isinstance(run_id,str) or not run_id.strip():raise ValueError('explicit single run identity required')
  self.run_id=run_id;self.pending=b'';self.offset=0;self.line_start=0;self.records=[];self.barrier=0;self.discard=False;self.discard_has_tag=False;self.other_lines=0
 def bad(self,reason,raw):
  self.barrier+=1;self.records.append({'byte_offset':self.line_start,'duration_ns':None,'duration_status':'unknown','reasons':[reason],'raw_prefix':raw[:80].decode('ascii',errors='replace'),'barrier':self.barrier})
 def line(self,raw):
  if TAG not in raw:self.other_lines+=1;return
  m=RE.fullmatch(raw.rstrip(b'\r'))
  if not m:self.bad('malformed_or_interleaved_record',raw);return
  tid,tp,end,seq,op,source,result,err,entry=m.groups();r={'byte_offset':self.line_start,'tid':int(tid),'tpidr':int(tp,0),'end_ns':int(end),'seq':int(seq),'op':int(op),'completion_source':int(source,0),'result':int(result),'errno':int(err),'entry_ns':None if entry is None else int(entry),'barrier':self.barrier,'reasons':[],'duration_status':'unknown','duration_ns':None}
  if not 0<r['tid']<2**31 or not 0<r['tpidr']<2**64 or not 0<=r['seq']<2**32 or not 0<=r['completion_source']<2**32 or not -2**31<=r['result']<2**31 or not -2**31<=r['errno']<2**31:r['reasons'].append('field_range_or_thread_identity')
  if r['entry_ns'] is None:r['reasons'].append('missing_entry')
  elif r['entry_ns']==0:r['reasons'].append('zero_entry_unknown')
  elif r['entry_ns']>=2**64:r['reasons'].append('entry_range')
  if not 0<r['end_ns']<2**64:r['reasons'].append('end_unknown_or_range')
  elif r['entry_ns'] is not None and r['end_ns']<r['entry_ns']:r['reasons'].append('end_before_entry')
  self.records.append(r)
 def feed(self,data):
  # Bound a damaged line, retain its unknown boundary through the next LF.
  for part in data.splitlines(keepends=True):
   self.offset+=len(part)
   if self.discard:
    self.discard_has_tag|=TAG in part
    if part.endswith(b'\n'):
     self.bad('overlong_or_truncated_record',b'')
     self.discard=False;self.discard_has_tag=False;self.line_start=self.offset
    continue
   self.pending+=part
   if len(self.pending)>4096:
    self.discard_has_tag=TAG in self.pending;self.pending=b'';self.discard=not part.endswith(b'\n')
    if not self.discard:
     self.bad('overlong_or_truncated_record',b'')
     self.discard_has_tag=False;self.line_start=self.offset
    continue
   if part.endswith(b'\n'):
    self.line(self.pending[:-1]);self.pending=b'';self.line_start=self.offset
 def finish(self):
  if TAG in self.pending or self.pending.startswith(b'FX3_GPE') or self.discard:self.bad('incomplete_at_cutoff_or_EOF',self.pending)
  elif self.pending:self.other_lines+=1
  seen=collections.defaultdict(list)
  for r in self.records:
   if 'tid' in r:seen[(r['tid'],r['tpidr'],r['seq'])].append(r)
  for values in seen.values():
   if len(values)>1:
    for r in values:r['reasons'].append('duplicate_or_conflicting_seq_tid_op')
  previous={}
  for r in self.records:
   r.update(gap_status='unknown',previous_return_to_entry_ns=None)
   if 'tid' not in r:continue
   if not r['reasons']:r.update(duration_status='known',duration_ns=r['end_ns']-r['entry_ns'])
   key=(r['tid'],r['tpidr']);p=previous.get(key)
   r['gap_reason']='no_prior_same_thread_record'
   if p:
    r['previous_record']={'seq':p['seq'],'op':p['op'],'byte_offset':p['byte_offset']}
    if p['duration_status']!='known' or r['duration_status']!='known':r['gap_reason']='one_endpoint_unknown'
    elif r['barrier']!=p['barrier']:r['gap_reason']='damaged_record_between'
    elif r['seq']!=p['seq']+1:r['gap_reason']='nonconsecutive_or_unordered_sequence'
    elif r['entry_ns']<p['end_ns']:r['gap_reason']='overlap_or_clock_order_unknown'
    else:r.update(gap_status='known',gap_reason='consecutive_same_thread_observed_records_only',previous_return_to_entry_ns=r['entry_ns']-p['end_ns'])
   previous[key]=r
  reasons=collections.Counter(reason for r in self.records for reason in r['reasons'])
  return {'schema':'fx3-r41-command-timing-v1','run_id':self.run_id,'clock_domain':'guest CLOCK_MONOTONIC only; no guest/host conversion','bytes_consumed':self.offset,'record_count':len(self.records),'known_durations':sum(r['duration_status']=='known' for r in self.records),'known_same_thread_gaps':sum(r['gap_status']=='known' for r in self.records),'unknown_reason_counts':dict(reasons),'records':self.records,'ignored_complete_other_lines':self.other_lines,'limits':'duration is adapter entry to return-marker sample, not CPU time or prior FIFO queue time; gap may include unobserved activity and is not proven idle; no cross-thread subtraction'}
def read(path,run_id,cutoff,chunk=65536):
 p=Path(path)
 if type(cutoff) is not int or cutoff<0 or cutoff>p.stat().st_size:raise ValueError('explicit cutoff within file required')
 parser=Parser(run_id)
 with p.open('rb') as f:
  left=cutoff
  while left:
   data=f.read(min(left,chunk))
   if not data:raise ValueError('file shortened during read')
   parser.feed(data);left-=len(data)
 return parser.finish()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('serial');p.add_argument('--run-id',required=True);p.add_argument('--cutoff-byte',required=True,type=int);p.add_argument('--output',required=True);a=p.parse_args();v=read(a.serial,a.run_id,a.cutoff_byte)
 with Path(a.output).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({k:v[k] for k in ('run_id','bytes_consumed','record_count','known_durations','known_same_thread_gaps','unknown_reason_counts')}))
if __name__=='__main__':main()
