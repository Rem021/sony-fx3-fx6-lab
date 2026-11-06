#!/usr/bin/env python3
"""One fixed-slot offline package. No compilation, target load or runner import."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,sys
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;D=O.parent
BASE=D/'r36-fixed-slot-package';R41=D/'r41-command-entry-timing-candidate'
TOOL=D/'r15-fixed-layout-packaging/fixed_layout.py'
TOOL_SHA='b5b9bf75763b193575a007074e6701d1a1541ba9d3658ae32a164fc350eca8bc'
BASE_SHA='49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff'
CANDIDATE_SHA='0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4'
BODY_SHA='19ca7deaf570eeb68fda0036bb75dec740ab30f404f9f91bd208fd3d53c06a39'
OLD_SHA='30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4'
MEMBER='simulation/fx3-gpe-observe-v7.so';SIZE=453213884;OFFSET=451447396;SLOT=276984
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha(TOOL.read_bytes())==TOOL_SHA
sp=importlib.util.spec_from_file_location('r42_fixed_layout_readonly',TOOL)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
req=m.require
def write(p,b):
 p=m.safe_path(p);req(p.is_relative_to(O) and p!=O,'output boundary')
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def js(n,x):write(O/n,(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def match(p,h):req(m.sha_file(p)==h,'hash mismatch: '+str(p))
def slot(rows):
 a=[r for r in rows if r['name']==MEMBER];req(len(a)==1,'unique GPE slot required');r=a[0]
 req(r['payload_offset']==OFFSET and r['size']==SLOT and r['mode']==0o100755 and r['nlink']==1,'slot layout drift')
 req(len(rows)==1141 and rows[-1]['name']=='TRAILER!!!','member count/trailer drift');return r
def main():
 m.volume_check();match(BASE/'candidate.json',CANDIDATE_SHA);match(BASE/'guest.cpio',BASE_SHA)
 body=m.read_file(R41/'build/gpe-r41-fixed-slot.so');req(len(body)==129600 and sha(body)==BODY_SHA,'fixed-slot body drift')
 raw=m.read_file(R41/'build/gpe-r41-candidate.so')
 req(sha(raw)=='04ba6d561c7dfbf2c2ce294c696207547e30b1c62ea0452f9899a0d2c78aba02','raw identity drift')
 elf=m.audit_elf(raw,body);js('ELF-AUDIT.json',elf)
 c=json.loads(m.read_file(BASE/'candidate.json'));match(c['dtb']['path'],'5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b')
 req(c['memory_mib']==5120 and c['initrd_load_address']=='0x440000000','platform changed')
 with m.open_read(BASE/'guest.cpio') as f:
  rows=m.index_archive(f);r=slot(rows);f.seek(OFFSET);req(sha(f.read(SLOT))==OLD_SHA,'old actual member drift')
 req(rows==json.loads(m.read_file(BASE/'source-index.json')),'actual archive index differs from frozen index')
 padded=body+bytes(SLOT-len(body));target=O/'guest.cpio'
 js('PACKAGE-INTENT.json',dict(base=str(BASE/'guest.cpio'),source_sha256=BASE_SHA,slot=r,body_sha256=BODY_SHA,zero_tail_bytes=SLOT-len(body),no_VM=True))
 with m.open_read(BASE/'guest.cpio') as src,target.open('xb') as dst:
  st=os.fstat(src.fileno());left=OFFSET
  while left:
   b=src.read(min(left,1<<20));req(bool(b),'short source');dst.write(b);left-=len(b)
  req(sha(src.read(SLOT))==OLD_SHA,'source slot drift');dst.write(padded)
  while b:=src.read(1<<20):dst.write(b)
  dst.flush();os.fsync(dst.fileno());end=os.fstat(src.fileno())
  req((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(end.st_dev,end.st_ino,end.st_size,end.st_mtime_ns),'source identity changed')
 req(target.stat().st_size==SIZE,'output size drift')
 with m.open_read(target) as f:new=m.index_archive(f)
 req(rows==new,'headers/names/order/offsets/trailer changed');slot(new)
 comparisons=[];changed=[]
 with m.open_read(BASE/'guest.cpio') as a,m.open_read(target) as b:
  for r in rows:
   hs=[]
   for f in (a,b):
    f.seek(r['payload_offset']);left=r['size'];h=hashlib.sha256()
    while left:
     buf=f.read(min(left,1<<20));req(bool(buf),'member truncated');h.update(buf);left-=len(buf)
    hs.append(h.hexdigest())
   eq=hs[0]==hs[1]
   if not eq:changed.append(r['name'])
   comparisons.append(dict(name=r['name'],header_offset=r['header_offset'],payload_offset=r['payload_offset'],size=r['size'],source_sha256=hs[0],output_sha256=hs[1],equal=eq))
 req(changed==[MEMBER],'unexpected changed members')
 # Complete sequential comparison, including all names, headers, padding and trailer.
 count=0;pos=0;ha=hashlib.sha256();hb=hashlib.sha256()
 with m.open_read(BASE/'guest.cpio') as a,m.open_read(target) as b:
  while x:=a.read(1<<20):
   y=b.read(len(x));req(len(x)==len(y),'length changed');ha.update(x);hb.update(y)
   lo=max(0,OFFSET-pos);hi=min(len(x),OFFSET+SLOT-pos)
   if lo<hi:
    req(x[:lo]==y[:lo] and x[hi:]==y[hi:],'outside slot changed')
    count+=sum(u!=v for u,v in zip(x[lo:hi],y[lo:hi]))
   else:req(x==y,'outside slot changed')
   pos+=len(x)
  req(not b.read(1) and pos==SIZE and ha.hexdigest()==BASE_SHA,'source/size changed')
 with m.open_read(target) as f:f.seek(OFFSET);req(f.read(SLOT)==padded,'body+zero tail mismatch')
 js('source-index.json',new);js('member-comparison.json',comparisons)
 js('ARCHIVE-DIFF.json',dict(schema='r42-one-fixed-slot-diff-v1',source_sha256=ha.hexdigest(),output_sha256=hb.hexdigest(),archive_bytes=SIZE,members_including_trailer=len(rows),headers_names_order_offsets_lengths_trailer_equal=True,outside_slot_every_byte_equal=True,outside_slot_bytes=SIZE-SLOT,changed_members=changed,changed_bytes=count,body_bytes=len(body),slot_bytes=SLOT,zero_tail_bytes=SLOT-len(body),padded_slot_sha256=sha(padded),exact_body_plus_zero_tail=True,DTB_unchanged=c['dtb'],target_executed=False))
 old=copy.deepcopy(c);c['initrd']=dict(path=str(target),sha256=hb.hexdigest())
 c['r42_command_entry_timing_contract']=dict(base_candidate=dict(path=str(BASE/'candidate.json'),sha256=CANDIDATE_SHA),base_initrd_sha256=BASE_SHA,member=MEMBER,payload_offset=OFFSET,slot_bytes=SLOT,old_slot_sha256=OLD_SHA,body=dict(path=str(R41/'build/gpe-r41-fixed-slot.so'),bytes=len(body),sha256=BODY_SHA),padded_slot_sha256=sha(padded),zero_tail_bytes=SLOT-len(body),source_files={str(R41/n):m.sha_file(R41/n) for n in ['src/fx3-gpe-observe-v26-perf.c','src/fx3-complete104-observe-v1.h']},source_freeze=dict(path=str(R41/'SOURCE-FREEZE.json'),sha256=m.sha_file(R41/'SOURCE-FREEZE.json')),backend='original v26_perf/backend-v9; r41 entry clock and same CMD_RETURN suffix only',previous_contracts_are_baseline_provenance=True,supersedes_current_GPE_payload_reference_only_in=['ap105_contract'],UI_OSD_and_all_other_members_unchanged=True,compiled_in_this_task=False,runtime_validated=False,VM_authorized=False,deployed=False)
 changes=sorted(k for k in c if c[k]!=old.get(k));req(changes==['initrd','r42_command_entry_timing_contract'],'unexpected candidate changes')
 js('candidate.json',c)
 match(BASE/'guest.cpio',BASE_SHA);match(BASE/'candidate.json',CANDIDATE_SHA)
 js('PACKAGE-COMPLETE.json',dict(status='offline_package_complete',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_sha256=m.sha_file(O/'candidate.json'),cpio_sha256=hb.hexdigest(),candidate_changed_fields=changes,compiled=False,VM=False,deployed=False))
 print(json.dumps({'status':'offline_package_complete','candidate_sha256':m.sha_file(O/'candidate.json'),'cpio_sha256':hb.hexdigest(),'changed_bytes':count,'members':len(rows)}))
if __name__=='__main__':main()
