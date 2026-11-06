#!/usr/bin/env python3
"""ELF64 .text section audit for backup claim; existing bytes only."""
import hashlib,json,struct
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'
def member_bytes(cpio,target):
 with Path(cpio).open('rb') as f:
  while True:
   h=f.read(110); assert len(h)==110 and h[:6]==b'070701'; ns=int(h[94:102],16); fs=int(h[54:62],16); n=f.read(ns).rstrip(b'\0'); f.read((4-(110+ns)%4)%4)
   if n==target:return f.read(fs)
   f.seek(fs,1); f.read((4-fs%4)%4)
   if n==b'TRAILER!!!':raise KeyError(target)
def sections(b):
 assert b[:4]==b'\x7fELF' and b[4]==2 and b[5]==1
 shoff=struct.unpack_from('<Q',b,0x28)[0]; shentsize=struct.unpack_from('<H',b,0x3a)[0]; shnum=struct.unpack_from('<H',b,0x3c)[0]; shstrndx=struct.unpack_from('<H',b,0x3e)[0]
 def sh(i):
  o=shoff+i*shentsize; name,typ=struct.unpack_from('<II',b,o); flags,addr=struct.unpack_from('<QQ',b,o+8); off,size=struct.unpack_from('<QQ',b,o+24); return {'i':i,'name_off':name,'type':typ,'flags':flags,'addr':addr,'offset':off,'size':size}
 tab=[sh(i) for i in range(shnum)]; st=tab[shstrndx]; names=b[st['offset']:st['offset']+st['size']]
 for x in tab:x['name']=names[x['name_off']:names.find(b'\0',x['name_off'])].decode('ascii','replace')
 return tab
def main():
 t=member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'usr/kmod/backup.ko'); s=member_bytes(CP/'guest-hybrid-fx6kernel-capid-grmreal19.cpio',b'usr/kmod/backup.ko')
 ts=sections(t); ss=sections(s); tt=next(x for x in ts if x['name']=='.text'); st=next(x for x in ss if x['name']=='.text')
 claim_section=0x75c; file_offset=tt['offset']+claim_section; assert tt['addr']==0,tt['addr']; assert st['addr']==0
 tb=t[file_offset:file_offset+4]; sb=s[file_offset:file_offset+4]
 ti=int.from_bytes(tb,'little'); si=int.from_bytes(sb,'little')
 imm=ti&0x03ffffff; imm=imm-(1<<26) if imm&(1<<25) else imm; target=(claim_section+imm*4)&0xffffffffffffffff
 brk=(si>>5)&0xffff
 value={'schema':'fx6-r50-backup-section-audit-v1','target_member_sha256':hashlib.sha256(t).hexdigest(),'source_grmreal19_sha256':hashlib.sha256(s).hexdigest(),
  'target_text_section':tt,'source_text_section':st,'claim_section_offset':hex(claim_section),'file_offset_for_claim':hex(file_offset),
  'target_hex':tb.hex(),'source_hex':sb.hex(),'target_instruction':hex(ti),'target_branch_target_section':hex(target),'source_instruction':hex(si),'source_brk_imm':hex(brk),
  'claim':'0x75c brk #0x3e8 -> b 0x700','claim_supported':tb.hex()=='e9ffff17' and target==0x700 and sb.hex()=='007d20d4' and brk==0x3e8,
  'correction':'Initial audit compared claim section offset 0x75c with file offset 0x75c; with .text sh_offset=0x68/sh_addr=0 the file location is 0x7c4. The claim is supported in section-offset terms; initial "offset mismatch" conclusion is withdrawn.',
  'scope':'existing bytes only; no patch design/execution'}
 (OUT/'backup-section-audit.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value,indent=2))
if __name__=='__main__':main()
