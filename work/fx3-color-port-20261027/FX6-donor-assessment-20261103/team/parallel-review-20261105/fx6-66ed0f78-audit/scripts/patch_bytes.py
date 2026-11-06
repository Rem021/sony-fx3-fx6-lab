#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'
def member_bytes(cpio,target):
 with Path(cpio).open('rb') as f:
  while True:
   h=f.read(110); assert len(h)==110 and h[:6]==b'070701'
   ns=int(h[94:102],16); fs=int(h[54:62],16); n=f.read(ns).rstrip(b'\0'); f.read((4-(110+ns)%4)%4)
   p=f.tell()
   if n==target:
    b=f.read(fs); return b
   f.seek(fs,1); f.read((4-fs%4)%4)
   if n==b'TRAILER!!!':raise KeyError(target)
def main():
 target=member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'usr/lib/appFw.so')
 donor=(TEAM/'donor/nflasha15-files/lib/appFw.so').read_bytes()
 btarget=member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'usr/kmod/backup.ko')
 bsource=member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal19.cpio',b'usr/kmod/backup.ko')
 def sl(b,off,n):return b[off:off+n].hex()
 def ranges(a,b):
  d=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]; out=[]
  for i in d:
   if out and i==out[-1][1]+1: out[-1][1]=i
   else: out.append([i,i])
  return [{'start':hex(x),'end':hex(y),'target':a[x:y+1].hex(),'baseline':b[x:y+1].hex()} for x,y in out[:10]]
 value={'schema':'fx6-r50-patch-bytes-audit-v1',
  'appFw':{'offset_claim':'0x2159c50','target_hex':sl(target,0x2159c50,8),'donor_hex':sl(donor,0x2159c50,8),'target_sha256':hashlib.sha256(target).hexdigest(),'donor_sha256':hashlib.sha256(donor).hexdigest(),'claim':'future::get helper -> mov w0,#0; ret','claim_offset_changed':sl(target,0x2159c50,8)!=sl(donor,0x2159c50,8),'diff_ranges':ranges(target,donor)[:5]},
  'backup':{'claim_section_offset':'0x75c','text_sh_offset':'0x68','text_sh_addr':'0x0','file_offset_for_claim':'0x7c4','target_hex_at_section':'e9ffff17','source_grmreal19_hex_at_section':'007d20d4','claim_supported':True,'target_branch_target_section':'0x700','source_brk_imm':'0x3e8','initial_audit_error_withdrawn':'Initial audit compared section offset 0x75c to file offset 0x75c; .text sh_offset=0x68 makes file offset 0x7c4. The claim is supported in section-offset terms.'},
  'helper':{'target_sha256':hashlib.sha256(member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'simulation/fx3-cp-backup-reset-v1.ko')).hexdigest(),'source_ko_sha256':hashlib.sha256((CP/'fx6-cp-backup-sync100-agnostic-g0.ko').read_bytes()).hexdigest()},
  'upm':{'target_sha256':hashlib.sha256(member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'usr/kmod/upm.ko')).hexdigest(),'modified_file_sha256':hashlib.sha256((CP/'grm-fbinit/upm-callsite-skip.ko').read_bytes()).hexdigest(),'note':'offset-level upm disassembly not performed; provenance/hash matches modified file'}}
 (OUT/'patch-bytes-audit.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value,indent=2))
if __name__=='__main__':main()
