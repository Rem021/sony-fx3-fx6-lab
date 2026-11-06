#!/usr/bin/env python3
"""Independent offline strict byte parser. No runner import or live interface.

Feed only bytes consumed before a caller supplied End cutoff. Never join across
End, tolerate a malformed/interleaved record, or promote absent suffixes to zero.
"""
import re,struct,json,argparse,hashlib
ABI=0x35010058; SOURCE=0x52333501
BASE=(rb'FX3_UI_GATE_SAMPLE id=(\d+) n=(\d+) tid=(\d+) pc=(0x[0-9a-f]+|0) object=(0x[0-9a-f]+|0) a18=(\d+) a12=(\d+) a13=(\d+) r0=(0x[0-9a-f]+|0) decision_a18=(\d+) elapsed=(\d+) old_time=(\d+) new_time=(\d+) message=(0x[0-9a-f]+|0) type=(0x[0-9a-f]+|0) source=(0x[0-9a-f]+|0) observed_only=1')
LINE=re.compile(BASE+rb' r35v1=([0-9a-f]{176});\r?\n')
def fnv(w):
 h=2166136261
 for b in struct.pack('<21I',*w[:21]):h=((h^b)*16777619)&0xffffffff
 return h
def packet(hexbytes):
 w=[int(hexbytes[i:i+8],16) for i in range(0,176,8)]
 if w[0]!=ABI or w[1]!=SOURCE or w[21]!=fnv(w):raise ValueError('abi_source_or_integrity')
 flag=w[20]&127
 if flag not in (1,2,3,4,5) or w[20] not in (flag,flag|128):raise ValueError('flags')
 if not 1<=w[18]<=7 or w[19]!=w[18]*184 or w[14] not in (0,1) or w[20]&128!=(128 if w[18]==7 else 0):raise ValueError('budget_or_loss')
 if not w[15] or not (w[16]|w[17]):raise ValueError('ui_identity_unknown')
 if flag==1:
  if w[3]!=1 or w[2]!=w[15] or not(w[4]|w[5]) or w[6] not in (0,1,2) or w[9] not in (0,1,2):raise ValueError('collector_identity_or_phase')
  if (w[6]==0 and (w[7] or w[8])) or (w[6] and w[7] not in (0x1003,0x1005)) or (w[6]==1 and w[8]):raise ValueError('publication_range')
  signed=lambda n:n if n<0x80000000 else n-0x100000000
  brc=signed(w[10]);magic=w[12]|(w[13]<<32)
  if w[9]!=2 and any(w[10:14]):raise ValueError('unfinished_bind_fields')
  if w[9]==2:
   if brc not in (0,-1,-2,-3,-4):raise ValueError('bind_rc')
   if brc==0 and (w[11]!=3 or magic!=0x32474e495244534f):raise ValueError('bind_success_without_original_magic')
   if brc in (-1,-2,-3) and (w[11] or magic):raise ValueError('failed_before_mapping')
   if brc==-4 and (w[11] not in (1,2) or magic):raise ValueError('mapping_failure')
  pub='no_captured_attempt_as_of_log' if w[6]==0 else 'captured_attempt_return_unknown' if w[6]==1 else 'original_send_failed' if signed(w[8]) else 'original_send_returned_zero'
  bind='no_captured_bind_as_of_log' if w[9]==0 else 'captured_bind_unfinished' if w[9]==1 else 'original_bind_failed' if brc else 'original_bind_succeeded_magic_observed'
 else:pub=bind={2:'exporter_unbound',3:'collector_unready',4:'snapshot_contended',5:'identity_rejected'}[flag]
 return {'words':w,'identity':(w[15],w[16],w[17],w[2],w[4],w[5]),'publication':pub,'bind':bind,'capture_loss':bool(w[14]),'budget_terminal':bool(w[20]&128),'ordinal':w[18]}
class Parser:
 def __init__(self):self.buf=b'';self.offset=0;self.records=[];self.unknown=[];self.identity=None;self.last=0;self.closed=False;self.discard=False;self.previous=None
 def feed(self,b):
  if self.closed:raise ValueError('feed_after_End')
  if self.discard:
   if b'\n' not in b:self.offset+=len(b);return
   skip,b=b.split(b'\n',1);self.offset+=len(skip)+1;self.discard=False
  self.buf+=b
  while b'\n' in self.buf:
   line,self.buf=self.buf.split(b'\n',1);line+=b'\n';at=self.offset;self.offset+=len(line)
   if len(line)>16384:self.unknown.append({'offset':at,'reason':'overlong_complete_line'});continue
   if b'r35v1=' not in line:continue
   m=LINE.fullmatch(line)
   if not m:self.unknown.append({'offset':at,'reason':'incomplete_interleaved_or_noncanonical_line'});continue
   try:
    ns=[int(x) for x in m.groups()[:3]]
    fields=m.groups()[:16]
    for i,v in enumerate(fields):
     n=int(v,16) if v.startswith(b'0x') else int(v)
     limit=255 if i in (6,7) else 2**32-1 if i in (2,9,14,15) else 2**64-1
     if n>limit:raise ValueError('original_field_out_of_range')
    if not 0<=ns[0]<12 or not 0<ns[1]<2**64 or not 0<ns[2]<2**32 or not(ns[1]<=50 or ns[1]%1000==0):raise ValueError('original_selected_condition_or_range')
    r=packet(m.group(17))
    # Unknown collector observations have independent UI identity. Once ready,
    # all subsequent ready observations must retain full collector identity.
    ui=r['identity'][:3]
    identity=self.identity if self.identity is not None else (ui,None)
    if ui!=identity[0]:raise ValueError('process_or_UI_instance_changed')
    if r['words'][20]&127==1:
     ci=r['identity'][3:]
     if identity[1] is None:identity=(ui,ci)
     if ci!=identity[1]:raise ValueError('collector_instance_changed')
    if r['ordinal']<=self.last:raise ValueError('duplicate_or_out_of_order')
    if r['ordinal']!=self.last+1:self.unknown.append({'offset':at,'reason':'export_record_gap'})
    if self.previous is not None and r['words'][20]&127==1:
     a=self.previous;w=r['words']
     if w[6]<a[6] or w[9]<a[9] or w[14]<a[14]:raise ValueError('phase_or_loss_regressed')
     if a[6] and w[7]!=a[7] or a[6]==2 and w[8]!=a[8]:raise ValueError('first_publication_replaced')
     if a[9]==2 and w[10:14]!=a[10:14]:raise ValueError('first_bind_replaced')
    self.identity=identity;self.last=r['ordinal'];r['offset']=at;self.records.append(r)
    if r['words'][20]&127==1:self.previous=r['words']
   except ValueError as e:self.unknown.append({'offset':at,'reason':str(e)})
  # Bound memory on malformed serial lines. Do not recover a suffix within it.
  if len(self.buf)>16384:self.unknown.append({'offset':self.offset,'reason':'overlong_line'});self.offset+=len(self.buf);self.buf=b'';self.discard=True
 def end(self):
  if self.buf or self.discard:self.unknown.append({'offset':self.offset,'reason':'partial_line_at_End'})
  self.closed=True
  return {'scope':'as_of_each_complete_original_log_only_not_End_state','records':self.records,'unknown':self.unknown,'overall':'observations_available' if self.records else 'no_complete_export_unknown'}
def main():
 p=argparse.ArgumentParser();p.add_argument('serial');p.add_argument('--run-id',required=True);p.add_argument('--end-byte',required=True,type=int);a=p.parse_args();b=open(a.serial,'rb').read();assert 0<=a.end_byte<=len(b);q=Parser()
 for i in range(0,a.end_byte,4096):q.feed(b[i:min(i+4096,a.end_byte)])
 result=q.end();result.update({'host_run_id':a.run_id,'serial_sha256':hashlib.sha256(b).hexdigest(),'end_byte':a.end_byte,'identity_scope':'caller supplied single host run; wire PID/init instances are not global runID'});print(json.dumps(result,indent=2))
if __name__=='__main__':main()
