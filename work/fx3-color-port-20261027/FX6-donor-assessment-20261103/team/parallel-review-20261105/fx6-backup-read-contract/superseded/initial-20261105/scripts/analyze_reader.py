#!/usr/bin/env python3
"""Read-only actual Backup_nread implementation audit (target CPIO member bytes)."""
import hashlib,json,struct,subprocess
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'; OD='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-objdump'; NM='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-nm'
B=CP/'grm-fbinit/backup-bug-skip.ko'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def member(cpio,target):
 with Path(cpio).open('rb') as f:
  while True:
   h=f.read(110); assert len(h)==110 and h[:6]==b'070701'; ns=int(h[94:102],16); fs=int(h[54:62],16); n=f.read(ns).rstrip(b'\0'); f.read((4-(110+ns)%4)%4)
   if n==target:return f.read(fs)
   f.seek(fs,1); f.read((4-fs%4)%4)
   if n==b'TRAILER!!!':raise KeyError(target)
def disasm(start,end,out):
 s=subprocess.run([OD,'-d','--no-show-raw-insn',f'--start-address={start}',f'--stop-address={end}',str(B)],capture_output=True,text=True,check=True).stdout
 Path(out).write_text(s);return s
def main():
 target_member=member(CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio',b'usr/kmod/backup.ko')
 assert hashlib.sha256(target_member).hexdigest()==sha(B),'local backup module is not target member'
 outer=disasm('0x1eb8','0x1f28',OUT/'disasm-backup-nread-outer.txt');inner=disasm('0x760','0x910',OUT/'disasm-backup-nread-inner.txt')
 rel=subprocess.run([OD,'-r',str(B)],capture_output=True,text=True,check=True).stdout
 rels=[l for l in rel.splitlines() if any(x in l for x in ('0000000000000788','0000000000000794','00000000000007cc','0000000000001ee8','0000000000001f08'))]
 (OUT/'relocs-backup-nread.txt').write_text('\n'.join(rels)+'\n')
 syms=subprocess.run([NM,'-n',str(B)],capture_output=True,text=True,check=True).stdout
 sym={}
 for l in syms.splitlines():
  p=l.split()
  if len(p)>=3 and p[2] in ('Backup_nread','Backup_read','Backup_read_4Byte'):sym[p[2]]=p[0]
 assert sym.get('Backup_nread')=='0000000000001eb8',sym
 sem={
  'schema':'fx6-backup-nread-semantics-v1','target_cpio_member_sha256':hashlib.sha256(target_member).hexdigest(),'local_module_sha256':sha(B),'module_symbols':sym,
  'outer':{'addr':'0x1eb8','file':'0x1f20','relocs':['0x1ee8 down_read','0x1f08 up_read'],'return':'returns inner w0; no buffer clearing'},
  'inner':{'addr':'0x760','file':'0x7c8','no_symbol':'local helper; called only from outer Backup_nread in this path','data_search':'0x788 Data_SearchId','data_size':'0x794 Data_GetSize','memcpy':'0x7cc memcpy','capacity_arg':'w24=w2','actual_size':'w22=Data_GetSize(desc)','return':'w0=w22','missing':'0x868 w22=-1 -> 0x7d0 return -1; buffer untouched','copy_len':'w19=w22 actual size; w2=w19 at memcpy; NOT capacity'},
  'cases':{
   'capacity4_record1':{'actual':1,'compare':'1 < 4 -> 0x7ac copy path','bytes_written':1,'high3':'untouched; caller initialized 4-byte 1 => bytes 01 00 00 00; low byte becomes 00/01, high3 stay 00','return':1},
   'capacity4_record4':{'actual':4,'compare':'4 == 4 -> b.eq 0x848 (diagnostic/check), then b 0x7ac','bytes_written':4,'high3':'overwritten by record tail','return':4},
   'missing_id':{'actual':None,'compare':'Data_SearchId returns 0 -> 0x868','bytes_written':0,'buffer':'untouched; caller initial 1 remains','return':-1},
   'zero_length':{'actual':0,'bytes_written':0,'buffer':'untouched','return':0,'note':'Data_GetSize=0 path, if observed'}},
  'appfw_caller':{'buffer_init':'0x11f675c [b0]=0; 0x11f6760-0x11f6768 stp w0,w0 sets each 4-byte slot to 1 (high3=00)','thunks':'0x2169784 key0x02cf0214, 0x21697d4 key0x02cf0218, w2=4','return_ignored':True},
  'single_byte_claim':{'claim':'single-byte 00/01 read remains legal','holds_for_this_appfw_caller':True,'condition':'only because caller initialized high3 to 00 and inner copies actual size 1; not a generic uninitialized-buffer or arbitrary-value guarantee','target_actual':'record is length4 16/19, so copies 4 bytes and overwrites high3; assert input is not 0/1'},
  'unknowns':['actual size>capacity path not exercised; 0x848 then w19=actual, no safe truncation inference','endianness assumed AArch64 little endian for this ELF/guest'],
  'evidence_files':['receipts/disasm-backup-nread-outer.txt','receipts/disasm-backup-nread-inner.txt','receipts/relocs-backup-nread.txt']}
 (OUT/'reader-semantics.json').write_text(json.dumps(sem,indent=2)+'\n')
 print(json.dumps({'module':sem['target_cpio_member_sha256'],'outer':sem['outer'],'inner':sem['inner'],'cases':sem['cases'],'claim':sem['single_byte_claim'],'receipt':str(OUT/'reader-semantics.json')},indent=2))
if __name__=='__main__':main()
