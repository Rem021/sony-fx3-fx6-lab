from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap84a-four-core-native-cpuset-r2';assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';assert not D.exists();D.mkdir();base=R/'ap84a-four-core-mttcg/candidate84a.json';v=json.loads(base.read_text());b=Path(v['initrd']['path']).read_bytes();sha=lambda q:hashlib.sha256(q).hexdigest();assert sha(b)==v['initrd']['sha256'];entries=[];o=0;changed=[]
while True:
 assert b[o:o+6]==b'070701';f=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];name=b[o+110:o+110+f[11]-1].decode();o=(o+110+f[11]+3)&~3;data=b[o:o+f[6]];o=(o+f[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='init':
  s=data.decode();needle='  echo 0 > /dev/cgroup/$group/cpuset.cpus';repl='  case "$group" in\n   cpu0) cpu_mask=0;; cpu1) cpu_mask=1;; cpu2) cpu_mask=2;; cpu3rt) cpu_mask=3;;\n   cpu0_1) cpu_mask=0,1;; cpu0_1_2) cpu_mask=0-2;; cpu0_1_2_3rt) cpu_mask=0-3;;\n  esac\n  echo "$cpu_mask" > /dev/cgroup/$group/cpuset.cpus';assert needle in s;s=s.replace(needle,repl);needle=' done\nfi\n/bin/busybox cat /proc/cgroups';repl=''' done
 # Original setup_cpuset_CPU3/shielding policy, not a flattened all-core substitute.
 echo 0-2 > /dev/cgroup/cpu0_1_2_3rt/cpuset.cpus_migratable
 migrate_rc=$?
 echo $$ > /dev/cgroup/cpu0_1_2_3rt/tasks
 parent_rc=$?
 kernel_parent=$(/bin/busybox pidof kthreadd)
 echo "$kernel_parent" > /dev/cgroup/cpu0_1_2_3rt/tasks
 kernel_rc=$?
 echo FX3_NATIVE_CPUSET_POLICY_RC=$migrate_rc,$parent_rc,$kernel_rc
 if [ "$migrate_rc" != 0 ] || [ "$parent_rc" != 0 ] || [ "$kernel_rc" != 0 ]; then cpuset_rc=1; fi
fi
/bin/busybox cat /proc/cgroups''';assert needle in s;s=s.replace(needle,repl);needle='  echo FX3_GUEST_UPTIME_SNAPSHOT; /bin/busybox cat /proc/uptime';repl=needle+'''
  echo FX3_CPU_ONLINE_SNAPSHOT; /bin/busybox cat /sys/devices/system/cpu/online
  for cpu_group in cpu0 cpu1 cpu2 cpu3rt cpu0_1 cpu0_1_2 cpu0_1_2_3rt; do
   echo FX3_CPUSET_ACTUAL_${cpu_group}_BEGIN
   /bin/busybox cat /dev/cgroup/$cpu_group/cpuset.cpus /dev/cgroup/$cpu_group/cpuset.mems /dev/cgroup/$cpu_group/cpuset.cpus_migratable /dev/cgroup/$cpu_group/tasks
   echo FX3_CPUSET_ACTUAL_${cpu_group}_END
  done''';assert needle in s;s=s.replace(needle,repl);needle='     /bin/busybox cat "$taskdir/status" "$taskdir/syscall" "$taskdir/stack"';repl=needle+'''
     echo FX3_TASK_AFFINITY_${taskdir##*/}_BEGIN
     /bin/busybox cat "$taskdir/stat" "$taskdir/cgroup"
     echo FX3_TASK_AFFINITY_${taskdir##*/}_END''';assert needle in s;s=s.replace(needle,repl);data=s.encode();changed.append(name);(D/'init-reviewed.sh').write_text(s)
 entries.append((name,f,data))
assert changed==['init'];out=bytearray()
def add(n,f,b,ino):
 f=f.copy();name=n.encode()+b'\0';f[0]=ino;f[6]=len(b);f[11]=len(name);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+name);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);spec=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);t,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in t['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(p[0],struct.pack('>Q',0x440000000+len(out))) if k=='prop' and p[0]=='linux,initrd-end' else p) for k,p in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(t,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt.read_bytes())};v['initrd']={'path':str(cp),'sha256':sha(out)};v['scope']+=' AP84a-r2 restores original seven cpuset maps and full.cpus_migratable0-2, init/kthreadd full-group placement per original setup_shielding; no application/scheduler/threshold patches. Adds read-only CPUonline/threadstat/cgroup snapshots.';v['required_markers']+=['FX3_NATIVE_CPUSET_POLICY_RC=0,0,0','FX3_CPU_ONLINE_SNAPSHOT'];(D/'candidate84a-r2.json').write_text(json.dumps(v,indent=2)+'\n');O=R.parent/'original-uipc/ap-projection/full-v4/regular-files/sbin';sources=[O/'init2',O/'initrc/setup_shielding',O/'initrc/setup_cpuset_CPU3',R.parent/'original-uipc/prepare_uipc_module_probe09.py'];(D/'cpuset-source-receipt.json').write_text(json.dumps({'only_CPIO_member_changed':'init','all_helpers_original_ELFs_and_other_members_unchanged':True,'DTB_only_change':'linux,initrd-end','original_source_sha256':{str(p):sha(p.read_bytes()) for p in sources},'policy':{'cpu0':'0','cpu1':'1','cpu2':'2','cpu3rt':'3','cpu0_1':'0,1','cpu0_1_2':'0-2','cpu0_1_2_3rt':'0-3','full.cpus_migratable':'0-2','init_and_kthreadd_group':'cpu0_1_2_3rt'},'harness_origin':'prepare_uipc_module_probe09.py explicit one online CPU profile, all seven cpu masks0','current_smp_only_AppFw_status':'Actual Cpus_allowed_list0-3, despite group files0; not enough to claim the process was CPU0-bound','read_only_observation_additions':['online','threadstat processor field','threadcgroup','allnativecpusets']},indent=2)+'\n');print(D/'candidate84a-r2.json')
