#!/bin/busybox sh
# FX6 appFw explicit launcher at init start
ln -sf /usr/share/app/fontlist.dat /TEXTRM_FONT_LIST
FX6_PRELOAD=/usr/lib/libgrm-fbinit9.so:/usr/lib/libgpe.so:/usr/lib/libgrm.so:/usr/lib/libux_core.so:/usr/lib/libuxengine.so:/usr/lib/libtestcmd.so:/usr/lib/libInfraIndctr.so:/usr/lib/libadjchkstub.so:/usr/lib/libInfraTp.so:/usr/lib/libcrypto.so.3:/usr/lib/libssl.so.3:/usr/lib/libmpr.so:/usr/lib/libicryptstub.so:/usr/lib/libInfraInterchipDatatrans.so:/usr/lib/libuxstub.so:/usr/lib/libInfraDial.so:/usr/lib/libInfraKikiLogGenerator.so:/usr/lib/libInfraRemote.so:/usr/lib/libInfraAccessLog.so
echo FX6_APPFW_DEFERRED_UNTIL_MODULES
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
/bin/busybox mount -t proc proc /proc
/bin/busybox mount -t sysfs sysfs /sys
/bin/busybox mount -t devtmpfs devtmpfs /dev
echo FX3_DEVTMPFS_RC=$?
echo FX3_CPUSET_INIT_BEGIN
/bin/busybox mkdir -p /dev/cgroup
/bin/busybox mount -t cgroup -o cpuset nodev /dev/cgroup
cpuset_rc=$?
echo FX3_CPUSET_MOUNT_RC=$cpuset_rc
if [ "$cpuset_rc" = 0 ]; then
 for group in cpu0 cpu1 cpu2 cpu3rt cpu0_1 cpu0_1_2 cpu0_1_2_3rt; do
  /bin/busybox mkdir -p /dev/cgroup/$group
  echo 0 > /dev/cgroup/$group/cpuset.mems
  mem_rc=$?
  case "$group" in
   cpu0) cpu_mask=0;; cpu1) cpu_mask=1;; cpu2) cpu_mask=2;; cpu3rt) cpu_mask=3;;
   cpu0_1) cpu_mask=0,1;; cpu0_1_2) cpu_mask=0-2;; cpu0_1_2_3rt) cpu_mask=0-3;;
  esac
  echo "$cpu_mask" > /dev/cgroup/$group/cpuset.cpus
  cpu_rc=$?
  echo FX3_CPUSET_GROUP_$group=$mem_rc,$cpu_rc
  if [ "$mem_rc" != 0 ] || [ "$cpu_rc" != 0 ]; then cpuset_rc=1; fi
 done
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
/bin/busybox cat /proc/cgroups
/bin/busybox cat /proc/mounts
/bin/busybox ls -l /dev/cgroup/cpu0_1_2_3rt/tasks
if [ "$cpuset_rc" != 0 ]; then
 echo FX3_CPUSET_NOT_READY
 echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
 # FX6 appFw explicit launcher (before the blocking monitor loop)
/usr/bin/appfw-launch > /tmp/appfw-launch.log 2>&1 &
sleep 5; cat /tmp/appfw-launch.log

while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 if [ -r /tmp/fx3-keyworker96.identity ]; then
  read key96_pid key96_tid < /tmp/fx3-keyworker96.identity
  echo FX3_KEY96_THREAD_BEGIN pid=$key96_pid tid=$key96_tid
  /bin/busybox cat /proc/uptime
  if [ -r /proc/$key96_pid/task/$key96_tid/status ]; then
   /bin/busybox grep -E '^(Name|State|Tgid|Pid|PPid|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' /proc/$key96_pid/task/$key96_tid/status
   echo FX3_KEY96_THREAD_WCHAN
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/wchan
   echo FX3_KEY96_THREAD_STACK
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/stack
  else echo FX3_KEY96_THREAD_ABSENT; fi
  echo FX3_KEY96_THREAD_END
 fi
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
fi
echo FX3_CPUSET_READY
echo FX3_UIPC_ORIGINAL_MODULE_PROBE04_BEGIN
/bin/busybox uname -a
/bin/busybox ls -l /kmod/devno.ko /usr/kmod/osal_utm.ko /usr/kmod/osal_uipc.ko /dev/null
ok=1
for mod in /kmod/devno.ko /usr/kmod/osal_utm.ko /usr/kmod/osal_uipc.ko; do
 echo FX3_INSMOD_BEGIN_$mod
 /bin/busybox insmod "$mod"
 rc=$?
 echo FX3_INSMOD_RC_$mod=$rc
 if [ "$rc" != 0 ]; then ok=0; break; fi
done
echo FX3_PROC_MODULES_BEGIN
/bin/busybox cat /proc/modules
echo FX3_PROC_DEVICES_BEGIN
/bin/busybox cat /proc/devices
echo FX3_UDM_DRIVERS_BEGIN
/bin/busybox cat /proc/udm/drivers
/bin/busybox ls -l /dev/uipc
if [ "$ok" = 1 ] && [ ! -c /dev/uipc ]; then
 uipc_minor=$(/bin/busybox awk '$2=="uipc"{print $1}' /proc/misc)
 echo FX3_UIPC_MKNOD_MINOR=$uipc_minor
 if [ -n "$uipc_minor" ]; then /bin/busybox mknod /dev/uipc c 10 "$uipc_minor"; fi
fi
if [ "$ok" = 1 ] && [ -c /dev/uipc ]; then
 echo FX3_UIPC_ORIGINAL_NODE_PRESENT

 echo FX3_LDEC103_INIT_BEGIN
 /bin/busybox insmod /simulation/fx3-ldec-soft103-v1.ko
 ldec_rc=$?
 echo FX3_LDEC103_INSMOD_RC=$ldec_rc
 if [ "$ldec_rc" = 0 ] && [ ! -c /dev/ldec ]; then /bin/busybox mknod /dev/ldec c 251 205; fi
 /bin/busybox ls -l /dev/ldec
 if [ "$ldec_rc" != 0 ] || [ ! -c /dev/ldec ]; then echo FX3_LDEC103_INIT_FAILED; while true; do /bin/busybox sleep 1; done; fi
 /simulation/fx3-ldec-ioctl103-test-v2
 ldec_test_rc=$?
 echo FX3_LDEC103_SELFTEST_RC=$ldec_test_rc
 if [ "$ldec_test_rc" != 0 ]; then echo FX3_LDEC103_SELFTEST_FAILED; while true; do /bin/busybox sleep 1; done; fi
 /simulation/fx3-file100-observer-v2 &
 file103_pid=$!
 echo FX3_FILE100_OBSERVER_PID=$file103_pid
 file103_ready=0
 file103_wait=0
 while [ "$file103_wait" -lt 200 ]; do
  if [ -r /tmp/fx3-file100-ready-v2 ]; then
   if read file103_signature file103_ready_pid < /tmp/fx3-file100-ready-v2 && [ "$file103_signature" = F100FILE_READY_V2 ] && [ "$file103_ready_pid" = "$file103_pid" ] && /bin/busybox kill -0 "$file103_pid"; then file103_ready=1; break; fi
  fi
  if ! /bin/busybox kill -0 "$file103_pid"; then break; fi
  /bin/busybox sleep 0.05
  file103_wait=$((file103_wait + 1))
 done
 if [ "$file103_ready" != 1 ]; then echo FX3_FILE103_READY_FAILED before_CP_API_bind=1; while true; do /bin/busybox sleep 1; done; fi
 echo FX3_FILE103_READY_CONFIRMED pid=$file103_pid before_CP_API_bind=1
 echo FX3_BACKUP_CP_INSMOD_BEGIN
 /bin/busybox insmod /simulation/fx3-cp-backup-reset-v1.ko
 backup_cp_rc=$?
 echo FX3_BACKUP_CP_INSMOD_RC=$backup_cp_rc
 if [ "$backup_cp_rc" != 0 ]; then echo FX3_BACKUP_CP_OWNER_FAILED; while true; do /bin/busybox sleep 1; done; fi
 echo FX3_UTIMER_BEGIN
 /bin/busybox insmod /usr/kmod/utimer.ko
 timer_rc=$?
 echo FX3_UTIMER_RC=$timer_rc
 if [ "$timer_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 echo FX3_BACKUP_ORIGINAL_SEED_BEGIN
 /bin/busybox ls -l /setting/Backup.bin /usr/kmod/backup.ko
 /bin/busybox sha256sum /setting/Backup.bin /usr/kmod/backup.ko
 echo FX3_BACKUP_INSMOD_BEGIN
 /bin/busybox insmod /usr/kmod/backup.ko Backup_load=1 Backup_save=0
 backup_rc=$?
 echo FX3_BACKUP_INSMOD_RC=$backup_rc
 /bin/busybox cat /proc/modules
 /bin/busybox ls -l /dev/backup
 echo FX3_BACKUP_PARAMETERS_BEGIN
 /bin/busybox ls -l /sys/module/backup/parameters
 /bin/busybox cat /sys/module/backup/parameters/Backup_load /sys/module/backup/parameters/Backup_save
 /bin/busybox cat /proc/devices
 echo FX3_BACKUP_PARAMETERS_END
 /bin/busybox sha256sum /setting/Backup.bin
 if [ "$backup_rc" != 0 ]; then
  echo FX3_BACKUP_ORIGINAL_NOT_READY
  echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
  while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 if [ -r /tmp/fx3-keyworker96.identity ]; then
  read key96_pid key96_tid < /tmp/fx3-keyworker96.identity
  echo FX3_KEY96_THREAD_BEGIN pid=$key96_pid tid=$key96_tid
  /bin/busybox cat /proc/uptime
  if [ -r /proc/$key96_pid/task/$key96_tid/status ]; then
   /bin/busybox grep -E '^(Name|State|Tgid|Pid|PPid|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' /proc/$key96_pid/task/$key96_tid/status
   echo FX3_KEY96_THREAD_WCHAN
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/wchan
   echo FX3_KEY96_THREAD_STACK
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/stack
  else echo FX3_KEY96_THREAD_ABSENT; fi
  echo FX3_KEY96_THREAD_END
 fi
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
 fi
 echo FX3_ULOGIO_ORIGINAL_BEGIN
 /bin/busybox sha256sum /usr/kmod/osal_ulogio.ko /setting/ulogio.bin
 /bin/busybox insmod /usr/kmod/osal_ulogio.ko ulogio_initfile=/setting/ulogio.bin
 ulogio_rc=$?
 echo FX3_ULOGIO_INSMOD_RC=$ulogio_rc
 /bin/busybox cat /proc/modules
 /bin/busybox ls -l /sys/module/osal_ulogio/parameters
 /bin/busybox cat /sys/module/osal_ulogio/parameters/ulogio_initfile
 if [ "$ulogio_rc" != 0 ]; then
  echo FX3_ULOGIO_ORIGINAL_NOT_READY
  echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
  while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 if [ -r /tmp/fx3-keyworker96.identity ]; then
  read key96_pid key96_tid < /tmp/fx3-keyworker96.identity
  echo FX3_KEY96_THREAD_BEGIN pid=$key96_pid tid=$key96_tid
  /bin/busybox cat /proc/uptime
  if [ -r /proc/$key96_pid/task/$key96_tid/status ]; then
   /bin/busybox grep -E '^(Name|State|Tgid|Pid|PPid|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches):' /proc/$key96_pid/task/$key96_tid/status
   echo FX3_KEY96_THREAD_WCHAN
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/wchan
   echo FX3_KEY96_THREAD_STACK
   /bin/busybox cat /proc/$key96_pid/task/$key96_tid/stack
  else echo FX3_KEY96_THREAD_ABSENT; fi
  echo FX3_KEY96_THREAD_END
 fi
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
 fi
fi

echo FX6_NATIVE_BOOT_BEGIN
for m in /usr/kmod/stream.ko /usr/kmod/stream2.ko /usr/kmod/dmm.ko /usr/kmod/grm_ma.ko; do
 echo FX6_NATIVE_INSMOD_BEGIN_$m
 if [ "$m" = "/usr/kmod/dmm.ko" ]; then
  /bin/busybox insmod "$m" DmmConfig=/setting/DmmCfg.bin
 else
  /bin/busybox insmod "$m"
 fi
 echo FX6_NATIVE_INSMOD_RC_$m=$?
done
/simulation/seed-power-on-v2 1
echo FX6_NATIVE_SEED_POWER_RC=$?
/bin/busybox insmod /usr/kmod/upm.ko
echo FX6_NATIVE_UPM_RC=$?
/bin/busybox insmod /usr/kmod/udate.ko
echo FX6_NATIVE_UDATE_RC=$?
/simulation/seed-date-clock-v3
echo FX6_NATIVE_SEED_DATE_RC=$?
/bin/busybox insmod /usr/kmod/kikilog.ko
echo FX6_NATIVE_KIKILOG_RC=$?
mkdir -p /setting/mode
echo 3 > /setting/mode/dmode
: > /setting/mode/preload
LD_PRELOAD=/usr/lib/libgrm-fbinit9.so /usr/bin/bootin.elf 'target=qemu ' dmode=3 > /dev/console 2>&1 &

appfw_pid=$!
echo FX6_NATIVE_APPFW_PID=$appfw_pid
while true; do
 for t in /proc/$appfw_pid/task/*; do
  [ -d "$t" ] || continue
  echo FX6_NATIVE_THREAD_BEGIN_${t##*/}
  /bin/busybox cat "$t/wchan" 2>/dev/null
  echo
  echo FX6_NATIVE_THREAD_END_${t##*/}
 done
 /bin/busybox sleep 3
done
