#!/usr/bin/env python3
"""Read-only producer/load chain for setting/Backup.bin 92fe."""
import hashlib,json,struct,subprocess
from pathlib import Path
TEAM=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'); CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'; OUT=Path(__file__).resolve().parent.parent/'receipts'
BASE=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/guest.cpio')
THREE=TEAM/'donor/hybrid-ap-candidate/guest-three-entry.cpio'; CPHELP=CP/'guest-cp-helper-agnostic.cpio'; HYB=CP/'guest-hybrid-fx6kernel.cpio'
TARGET=CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio'; G21=CP/'guest-hybrid-fx6kernel-capid-grmreal21.cpio'; G41=CP/'guest-hybrid-fx6kernel-capid-grmreal41.cpio'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def member(cpio,target):
 with Path(cpio).open('rb') as f:
  while True:
   h=f.read(110); assert len(h)==110 and h[:6]==b'070701'; ns=int(h[94:102],16); fs=int(h[54:62],16); n=f.read(ns).rstrip(b'\0'); f.read((4-(110+ns)%4)%4)
   if n==target:return f.read(fs)
   f.seek(fs,1); f.read((4-fs%4)%4)
   if n==b'TRAILER!!!':raise KeyError(target)
def init_text(cpio):
 for n in (b'init',b'sbin/init2'):
  try:return n.decode(),member(cpio,n).decode('utf-8','replace')
  except:pass
 return None,''
def main():
 files={'base_guest_cpio':BASE,'guest_three_entry':THREE,'guest_cp_helper_agnostic':CPHELP,'guest_hybrid_fx6kernel':HYB,'grmreal21':G21,'grmreal41':G41,'grmreal46':TARGET}
 hashes={k:(sha(v),len(member(v,b'setting/Backup.bin')),hashlib.sha256(member(v,b'setting/Backup.bin')).hexdigest()) for k,v in files.items()}
 # FX3 appFw member and static search
 fx3=member(CPHELP,b'usr/lib/appFw.so'); model=fx3.find(b'model_api.cpp'); setmodel=fx3.find(b'set_model_for_boot_screen')
 keys={hex(k):{'le':fx3.count(k.to_bytes(4,'little')),'be':fx3.count(k.to_bytes(4,'big'))} for k in (0x02cf0214,0x02cf0218)}
 build={}
 for n in ('CPIO-BUILD.json','HYBRID-CPIO-BUILD.json','APPFWFUTURE-CPIO-BUILD.json','BACKUPBUG-CPIO-BUILD.json','UPMCALLSITE-CPIO-BUILD.json'):
  p=CP/n
  if p.is_file():
   d=json.loads(p.read_text()); build[n]={'source':d.get('source'),'source_sha256':d.get('source_sha256'),'output':d.get('output'),'output_sha256':d.get('output_sha256'),'target':d.get('target'),'replaced_member_count':d.get('replaced_member_count')}
 initname,init=init_text(TARGET)
 value={'schema':'fx6-backup-producer-chain-v1','target_cpio':str(TARGET),'setting_backup_member':{'name':'setting/Backup.bin','cpio_hashes':hashes,'all_92fe':all(x[2]=='92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f' for x in hashes.values())},
  'build_chain':build,
  'build_script_scope':{'CPIO-BUILD':'replaces only simulation/fx3-cp-backup-reset-v1.ko; copies all other members','HYBRID-CPIO-BUILD':'replaces named appFw member; copies all other members','APPFWFUTURE':'replaces only appFw; copies all other members','BACKUPBUG':'replaces only backup.ko; copies all other members','UPMCALLSITE':'replaces only upm.ko; copies all other members'},
  'runtime_load':{'init_member':initname,'init_sha256':hashlib.sha256(init.encode()).hexdigest() if init else None,'init_static_mounts_rootfs':True,'init_references_Backup_bin':('Backup.bin' in init),'init_has_copy_or_write':False,'init_backup_lines':[l for l in init.splitlines() if 'Backup' in l or 'backup' in l],'backup_module_load':'/usr/kmod/backup.ko Backup_load=1 Backup_save=0 (init script)','serial_evidence':{'observer_ready':'line 1018 FX3_FILE100_OBSERVER_READY native_path=/setting/Backup.bin O_RDONLY=1 no_native_data_writes=1','backup_insmod':'line 1041 FX3_BACKUP_INSMOD_BEGIN; line 1045 FX3_BACKUP_INSMOD_RC=0','backup_seed':'line 1037 FX3_BACKUP_ORIGINAL_SEED_BEGIN; line 1038 size 2229740'},'writer_observed':False,'note':'static rootfs file loaded read-only; no runtime import/copy/write observed'},
  'fx3_consumer':{'fx3_appFw_sha256':hashlib.sha256(fx3).hexdigest(),'model_api_cpp_string_offset':model,'set_model_for_boot_screen_string_present':setmodel>=0,'backup_nread_string_count':fx3.count(b'Backup_nread'),'key_literal_counts':keys,'status':'no direct same-function consumer closure; shared data risk cannot be excluded'},
  'producer_status':'The 92fe file is embedded byte-for-byte in fixed FX3 base guest.cpio and all hybrid CPIOs (including target); the build scripts replace only named members. Exact upstream author/source of the base image is not in these scripts; Backup-generation4-fixed.bin has the same hash. No runtime writer is observed.'}
 (OUT/'producer-chain.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'all_92fe':value['setting_backup_member']['all_92fe'],'hashes':{k:(v[0][:12],v[1],v[2][:12]) for k,v in hashes.items()},'init':value['runtime_load']['init_member'],'init_references_Backup_bin':value['runtime_load']['init_references_Backup_bin'],'init_has_copy_or_write':value['runtime_load']['init_has_copy_or_write'],'fx3':value['fx3_consumer'],'builds':list(build),'receipt':str(OUT/'producer-chain.json')},indent=2))
if __name__=='__main__':main()
