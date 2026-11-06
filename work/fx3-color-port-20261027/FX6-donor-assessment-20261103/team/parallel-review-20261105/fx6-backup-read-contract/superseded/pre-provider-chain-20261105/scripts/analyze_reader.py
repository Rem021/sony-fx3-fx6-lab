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
 ccmp=json.loads((OUT/'ccmp-host-test.json').read_text()); assert ccmp['all_match'] and any(x['actual']==4 and x['capacity']==4 and x['flag']==1 and x['beq']==0 for x in ccmp['cases']) and any(x['actual']==5 and x['capacity']==4 and x['flag']==1 and x['beq']==1 for x in ccmp['cases'])
 sem={
  'schema':'fx6-backup-nread-semantics-v1','target_cpio_member_sha256':hashlib.sha256(target_member).hexdigest(),'local_module_sha256':sha(B),'module_symbols':sym,
  'outer':{'addr':'0x1eb8','file':'0x1f20','relocs':['0x1ee8 down_read','0x1f08 up_read'],'return':'returns inner w0; no buffer clearing'},
  'inner':{'addr':'0x760','file':'0x7c8','no_symbol':'local helper; called only from outer Backup_nread in this path','data_search':'0x788 Data_SearchId','data_size':'0x794 Data_GetSize','capacity_arg':'w24=w2','actual_size':'w22=Data_GetSize(desc)','branch':'0x79c cmp w22,w24; 0x7a4 ccmp w23,#1,#0,gt; 0x7a8 b.eq 0x848','ccmp_semantics':'actual==capacity => GT false => CCMP sets NZCV=0 => Z=0 => b.eq NOT taken. Only actual>capacity && w23==1 enters 0x848.','copy_len':'w19=w22 actual size; at 0x7c4 w2=w19; NOT capacity','return':'w0=w22 actual, or -1 missing'},
  'ccmp_host_test':{'receipt':'receipts/ccmp-host-test.json','all_match':ccmp['all_match'],'cases':ccmp['cases'],'note':'Apple arm64 finite integer test; no firmware/VM'},
  'cases':{
   'capacity4_record1':{'actual':1,'branch':'cmp 1,4 -> LT; CCMP condition GT false -> NZCV=0; b.eq false; 0x7ac','copy_path':'pointer-dependent: user 0x7f0 (access check + __arch_copy_to_user) or kernel 0x7cc memcpy','bytes_written':'actual 1 if user copy succeeds; 0 if access check fails; return still 1','high3':'untouched; caller initialized 4-byte 1 => 01 00 00 00; low byte 00/01, high3 00','return':1},
   'capacity4_record4':{'actual':4,'branch':'4==4 -> GT false; CCMP sets NZCV=0; Z=0; b.eq false; 0x7ac (NOT 0x848)','copy_path':'pointer-dependent user/kernel; actual 4','bytes_written':'4 if copy succeeds; 0 if access check fails; return still 4','high3':'overwritten by record tail on successful copy','return':4},
   'capacity4_record5_flag1':{'actual':5,'branch':'5>4 -> GT true; CCMP w23(1),#1 -> Z=1; b.eq 0x848','then':'0x848 diagnostic/0x6d8 then b 0x7ac; w19 remains actual 5; no safe truncation inferred','return':5,'not_target':True},
   'capacity4_record5_flag0':{'actual':5,'branch':'5>4 GT true; CCMP w23(0),#1 -> Z=0; b.eq false; 0x7ac','copy_len':'actual 5 > capacity 4; no truncation','not_target':True},
   'missing_id':{'actual':None,'branch':'Data_SearchId returns 0 -> 0x868 w22=-1 -> 0x7d0','bytes_written':0,'buffer':'untouched; caller initial 1 remains','return':-1},
   'zero_length':{'actual':0,'branch':'0<4 -> CCMP false -> 0x7ac; w2=0','bytes_written':0,'buffer':'untouched','return':0,'note':'not observed on target IDs'}},
  'pointer_paths':{'threshold':'0x7fffffffff','user':'x20 <= threshold -> 0x7f0: Data_GetDataPt; range/access check; if check fails 0x7d0 returns actual WITHOUT copy; if passes 0x824 __arch_copy_to_user; return value of copy is not inspected; 0x828 sets w0=actual','kernel':'x20 > threshold -> 0x7bc Data_GetDataPt; 0x7cc memcpy actual; return actual','appfw':'appFw buffer is a local stack slot; no runtime pointer capture; code selects by x20, so path/actual write count is not proven. Do not assume memcpy path.','return_vs_write':'return actual != guaranteed bytes written on user path (access-check skip or copy failure still returns actual).'},
  'appfw_caller':{'buffer_init':'0x11f675c [b0]=0; 0x11f6760-0x11f6768 stp w0,w0 sets each 4-byte slot to 1 (high3=00)','thunks':'0x2169784 key0x02cf0214, 0x21697d4 key0x02cf0218, w2=4','return_ignored':True},
  'single_byte_claim':{'claim':'single-byte 00/01 read remains legal','holds_for_this_appfw_caller':'conditional: only if high3 initialized 00 and the 1-byte user copy succeeds or is skipped without changing low byte; buffer remains a valid 0/1','not_generic':'not a guarantee for arbitrary buffers, failed user copy, or arbitrary values','target_actual':'target record is length4 16/19; if user copy succeeds it overwrites 4 bytes and is invalid; if access check fails, buffer remains 1 and this assertion may not fire. No runtime pointer/value capture; static+serial supports the invalid-value path but does not prove write count.'},
  'unknowns':['actual appFw x20 path/user-copy success not captured','actual size>capacity semantics; no truncation claim','kernel vs user pointer selected at runtime','endianness assumed AArch64 little-endian'],
  'evidence_files':['receipts/disasm-backup-nread-outer.txt','receipts/disasm-backup-nread-inner.txt','receipts/relocs-backup-nread.txt','receipts/ccmp-host-test.json']}
 (OUT/'reader-semantics.json').write_text(json.dumps(sem,indent=2)+'\n')
 print(json.dumps({'module':sem['target_cpio_member_sha256'],'inner':sem['inner'],'ccmp':sem['ccmp_host_test'],'cases':sem['cases'],'pointer_paths':sem['pointer_paths'],'claim':sem['single_byte_claim'],'receipt':str(OUT/'reader-semantics.json')},indent=2))
if __name__=='__main__':main()
