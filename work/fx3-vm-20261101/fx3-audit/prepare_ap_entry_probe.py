#!/usr/bin/env python3
from pathlib import Path
import json,struct,stat,hashlib,plistlib,subprocess
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit')
v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
src=ROOT/'fx3-original-app-loader-probe.cpio';b=src.read_bytes();o=0;files={}
while True:
 assert b[o:o+6]==b'070701';vals=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];o+=110
 ln=vals[11];name=b[o:o+ln-1].decode();assert b[o+ln-1]==0;o=(o+ln+3)&~3
 data=b[o:o+vals[6]];o=(o+vals[6]+3)&~3
 if name=='TRAILER!!!':break
 files[name]=(data,vals[1],vals[9],vals[10])
assert all(not any(s in n.lower() for s in ['updater','jiritsu','libjit','preload']) for n in files)
init=b'''#!/bin/busybox sh
echo FX3_AP_ENTRY_PROBE_BEGIN
/bin/busybox uname -a
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t debugfs debugfs /sys/kernel/debug
tr=/sys/kernel/debug/tracing
/bin/busybox sh -c 'kill -STOP $$; exec /usr/bin/im.elf target=qemu' </dev/null &
ap_pid=$!
echo FX3_AP_ENTRY_EXEC_PID=$ap_pid
/bin/busybox sleep 1
if [ -d "$tr/events/syscalls" ]; then
 echo 0 > "$tr/tracing_on"
 echo > "$tr/trace"
 for ev in sys_enter_openat sys_exit_openat sys_enter_open sys_exit_open sys_enter_ioctl sys_exit_ioctl; do
  if [ -d "$tr/events/syscalls/$ev" ]; then
   echo "common_pid == $ap_pid" > "$tr/events/syscalls/$ev/filter"
   echo 1 > "$tr/events/syscalls/$ev/enable"
  fi
 done
 echo 1 > "$tr/tracing_on"
 echo FX3_AP_SYSCALL_TRACE_ENABLED
else
 echo FX3_AP_SYSCALL_TRACE_UNAVAILABLE
fi
kill -CONT $ap_pid
/bin/busybox sleep 2
if kill -0 $ap_pid 2>/dev/null; then
 echo FX3_AP_STILL_ALIVE_AT_BOUND
 /bin/busybox cat /proc/$ap_pid/maps
 /bin/busybox cat /proc/$ap_pid/wchan
 kill -TERM $ap_pid
 /bin/busybox sleep 1
 kill -KILL $ap_pid 2>/dev/null
else
 echo FX3_AP_EXITED_BEFORE_BOUND
fi
wait $ap_pid
rc=$?
echo FX3_AP_WAIT_RC=$rc
if [ -d "$tr/events/syscalls" ]; then
 echo 0 > "$tr/tracing_on"
 echo FX3_AP_SYSCALL_TRACE_BEGIN
 /bin/busybox cat "$tr/trace"
 echo FX3_AP_SYSCALL_TRACE_END
fi
echo FX3_AP_ENTRY_PROBE_END
while true; do /bin/busybox sleep 1; done
'''
files['init']=(init,stat.S_IFREG|0o755,0,0)
for n in ['sys/kernel','sys/kernel/debug']:files[n]=(b'',stat.S_IFDIR|0o755,0,0)
for n,ma,mi in [('dev/null',1,3),('dev/zero',1,5),('dev/tty',5,0)]:files[n]=(b'',stat.S_IFCHR|0o666,ma,mi)
def ent(n,d,m,ma,mi,i):
 nb=n.encode()+b'\0';vals=[i,m,0,0,1,0,len(d),0,0,ma,mi,len(nb),0];r=b'070701'+''.join(f'{v:08x}' for v in vals).encode()+nb;r+=b'\0'*((-len(r))%4);r+=d;r+=b'\0'*((-len(r))%4);return r
names=sorted(files,key=lambda n:(n.count('/'),0 if stat.S_ISDIR(files[n][1]) else 1,n));cpio=b''.join(ent(n,*files[n],i+1) for i,n in enumerate(names))+ent('TRAILER!!!',b'',0,0,0,999)
p=ROOT/'fx3-original-im-entry-probe.cpio';assert not p.exists();p.write_bytes(cpio)
# Independent exact identity: all original regular non-init members unchanged from loader-only cpio.
original=json.loads((ROOT/'application-loader-probe.json').read_text())['original_elfs']
for r in original:
 name=r['guest_path'].lstrip('/');assert hashlib.sha256(files[name][0]).hexdigest()==r['sha256']
rec={'path':str(p),'bytes':len(cpio),'sha256':hashlib.sha256(cpio).hexdigest(),'source_loader_cpio_sha256':hashlib.sha256(b).hexdigest(),'original_elfs_unchanged':len(original),'executable_command':['/usr/bin/im.elf','target=qemu'],'child_protocol':'Original busybox shell stops before exec. Guest parent optionally enables original-kernel syscall tracing for that PID, resumes, waits2s then terminates. Host QMP lifetime remains independently bounded.','guest_standard_filesystems':['proc','sysfs','debugfs'],'host_files_disks_usb_network_exposed':False,'original_init_updater_service_loader_included':False,'contains_updater_jiritsu_preload_worker':False,'custom_init':init.decode(),'scope':'Separate AP entry investigation only; does not change successful core/loader profiles or claim UI/capture.'}
(ROOT/'ap-entry-probe.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:rec[k] for k in ['path','bytes','sha256','original_elfs_unchanged','executable_command']},indent=2))
