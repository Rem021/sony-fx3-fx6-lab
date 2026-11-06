#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util,json,hashlib,gzip,stat,subprocess,plistlib
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac');OUT=ROOT/'work/fx3-vm-20261101/fx3-audit';SRC=ROOT/'work/sony-firmware-20261024/stage2/extraction'
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
spec=importlib.util.spec_from_file_location('fs_ro',SRC/'read_filesystems.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
f=m.Ext2(SRC/'nflasha7.img');idx={x['path']:x for x in json.loads((SRC/'nflasha7-files.json').read_text())['files']};crypt=f.data(idx['/lib/libcrypt-2.25.so']['inode']);(OUT/'original-members/nflasha7/lib/libcrypt-2.25.so').write_bytes(crypt)
files={'bin':(b'',stat.S_IFDIR|0o755),'lib':(b'',stat.S_IFDIR|0o755),'dev':(b'',stat.S_IFDIR|0o755),'proc':(b'',stat.S_IFDIR|0o755),'sys':(b'',stat.S_IFDIR|0o755)}
for n in ['bin/busybox','lib/ld-2.25.so','lib/libc-2.25.so','lib/libcrypt-2.25.so']:
 files[n]=((OUT/'original-members/nflasha7'/n).read_bytes(),stat.S_IFREG|0o755)
for n,t in [('lib/ld-linux-aarch64.so.1','ld-2.25.so'),('lib/libc.so.6','libc-2.25.so'),('lib/libcrypt.so.1','libcrypt-2.25.so'),('bin/sh','busybox')]:files[n]=(t.encode(),stat.S_IFLNK|0o777)
files['init']=(b'#!/bin/busybox sh\necho FX3_ORIGINAL_BUSYBOX_REACHED\n/bin/busybox uname -a\n/bin/busybox echo FX3_VM_PROBE_END\nwhile true; do /bin/busybox sleep 1; done\n',stat.S_IFREG|0o755)
files['dev/console']=(b'',stat.S_IFCHR|0o600)
def ent(name,data,mode,ino):
 nb=name.encode()+b'\0';vals=[ino,mode,0,0,1,0,len(data),0,0,5 if name=='dev/console' else 0,1 if name=='dev/console' else 0,len(nb),0];r=b'070701'+''.join(f'{x:08x}' for x in vals).encode()+nb;r+=b'\0'*((-len(r))%4);r+=data;r+=b'\0'*((-len(r))%4);return r
cpio=b''.join(ent(n,d,m,i+1) for i,(n,(d,m)) in enumerate(files.items()))+ent('TRAILER!!!',b'',0,999)
p=OUT/'fx3-minimal-original-userspace-v2.cpio.gz';assert not p.exists();p.write_bytes(gzip.compress(cpio,mtime=0));sha=lambda b:hashlib.sha256(b).hexdigest()
rec={'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'v1_status':'not executed; dependency audit found missing libcrypt; v2 contains both busybox DT_NEEDED dependencies','unmodified_original_members':[{'path':n,'sha256':sha(d),'bytes':len(d)} for n,(d,m) in files.items() if stat.S_ISREG(m) and n!='init'],'custom_init':files['init'][0].decode(),'no_original_init_or_updater':True,'no_block_disk_or_real_device':True}
(OUT/'minimal-probe-v2.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
