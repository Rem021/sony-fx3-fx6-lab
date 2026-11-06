#!/bin/busybox sh
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
  echo 0 > /dev/cgroup/$group/cpuset.cpus
  cpu_rc=$?
  echo FX3_CPUSET_GROUP_$group=$mem_rc,$cpu_rc
  if [ "$mem_rc" != 0 ] || [ "$cpu_rc" != 0 ]; then cpuset_rc=1; fi
 done
fi
/bin/busybox cat /proc/cgroups
/bin/busybox cat /proc/mounts
/bin/busybox ls -l /dev/cgroup/cpu0_1_2_3rt/tasks
if [ "$cpuset_rc" != 0 ]; then
 echo FX3_CPUSET_NOT_READY
 echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
 while true; do /bin/busybox sleep 1; done
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
if [ "$ok" = 1 ] && [ -c /dev/uipc ]; then
 echo FX3_UIPC_ORIGINAL_NODE_PRESENT
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
  while true; do /bin/busybox sleep 1; done
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
  while true; do /bin/busybox sleep 1; done
 fi
 echo FX3_TRACE_ABI_VERIFY_BEGIN
 LD_PRELOAD=/simulation/fx3-gpe-observe-v4.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /lib/ld-linux-aarch64.so.1 --verify /usr/bin/im.elf
 verify_rc=$?
 echo FX3_TRACE_ABI_VERIFY_RC=$verify_rc
 LD_PRELOAD=/simulation/fx3-gpe-observe-v4.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /lib/ld-linux-aarch64.so.1 --library-path /lib:/usr/lib --list /usr/bin/im.elf
 list_rc=$?
 echo FX3_TRACE_ABI_LIST_RC=$list_rc
 LD_PRELOAD=/simulation/fx3-gpe-observe-v4.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /bin/busybox true
 true_rc=$?
 echo FX3_TRACE_ABI_TRUE_RC=$true_rc
 if [ "$verify_rc" != 0 ] || [ "$list_rc" != 0 ] || [ "$true_rc" != 0 ]; then
  echo FX3_TRACE_ABI_NOT_READY
  echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
  while true; do /bin/busybox sleep 1; done
 fi
 echo FX3_STREAM_BEGIN
 /bin/busybox insmod /usr/kmod/stream.ko
 echo FX3_STREAM_RC=$?
 /bin/busybox insmod /usr/kmod/stream2.ko
 echo FX3_STREAM2_RC=$?
 echo FX3_DMM_BEGIN
 /bin/busybox insmod /usr/kmod/dmm.ko DmmConfig=/setting/DmmCfg.bin
 dmm_rc=$?
 echo FX3_DMM_RC=$dmm_rc
 if [ "$dmm_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 echo FX3_GRM_MA_BEGIN
 /bin/busybox insmod /usr/kmod/grm_ma.ko
 grm_rc=$?
 echo FX3_GRM_MA_RC=$grm_rc
 if [ "$grm_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 echo FX3_DMM_PROC_BEGIN
 /bin/busybox ls -l /proc/osal /proc/udm/dmm_info
 /bin/busybox cat /proc/udm/dmm_info /proc/udm/dmm_units /proc/udm/dmm_extents /proc/udm/dmm_reserve
 echo FX3_DMM_PROC_END
 echo FX3_POWER_SEED_BEGIN
 /simulation/seed-power-on-v2 1
 seed_rc=$?
 echo FX3_POWER_SEED_RC=$seed_rc
 if [ "$seed_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 /bin/busybox insmod /usr/kmod/upm.ko
 upm_rc=$?
 echo FX3_UPM_RC=$upm_rc
 if [ "$upm_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 /bin/busybox insmod /usr/kmod/udate.ko
 echo FX3_UDATE_RC=$?
 echo FX3_DATE_CLOCK_BEGIN
 /simulation/seed-date-clock-v2
 date_rc=$?
 echo FX3_DATE_CLOCK_RC=$date_rc
 if [ "$date_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 echo FX3_AP_NATURAL_BOOTIN_BEGIN
 echo FX3_AP_ARGV_target_qemu_WITH_TRAILING_SPACE_dmode3
 LD_LIBRARY_PATH=/simulation:/usr/lib:/lib LD_PRELOAD=/simulation/fx3-gpe-observe-v4.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /usr/bin/bootin.elf 'target=qemu ' dmode=3 &
 launcher=$!
 echo FX3_AP_BOOTIN_LAUNCH_PID=$launcher
 for turn in 1 2 3; do
  /bin/busybox sleep 10
  echo FX3_AP_SNAPSHOT_${turn}_BEGIN
  /bin/busybox ps
  /bin/busybox ls -l /proc/[0-9]*/exe
  for procdir in /proc/[0-9]*; do
   if /bin/busybox grep -q '/usr/bin/im.elf' "$procdir/maps" 2>/dev/null; then
    echo FX3_AP_IM_PROCESS=${procdir##*/}
    /bin/busybox cat "$procdir/cmdline"
    echo
    /bin/busybox cat "$procdir/status" "$procdir/maps" "$procdir/wchan"
    /bin/busybox ls -l "$procdir/fd"
    for taskdir in "$procdir"/task/*; do
     echo FX3_TASK_SNAPSHOT_${taskdir##*/}_BEGIN
     /bin/busybox cat "$taskdir/status" "$taskdir/syscall" "$taskdir/stack"
     echo FX3_TASK_SNAPSHOT_${taskdir##*/}_END
    done
   fi
  done
  /bin/busybox ls -l /proc/osal /tmp /setting
  /bin/busybox cat /proc/udm/dmm_units /proc/udm/dmm_extents
  echo FX3_AP_SNAPSHOT_${turn}_END
 done
 echo FX3_AP_NATURAL_OBSERVATION_END

else
 echo FX3_UIPC_DEPENDENCY_OR_NODE_NOT_READY
fi
echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
while true; do /bin/busybox sleep 1; done
