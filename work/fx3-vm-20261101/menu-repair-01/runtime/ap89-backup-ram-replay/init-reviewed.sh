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
 while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
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
if [ "$ok" = 1 ] && [ -c /dev/uipc ]; then
 echo FX3_UIPC_ORIGINAL_NODE_PRESENT
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
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
 fi
 echo FX3_TRACE_ABI_VERIFY_BEGIN
 LD_PRELOAD=/simulation/fx3-skd-hw-unavailable-v1.so:/simulation/fx3-capid-v1.so:/simulation/fx3-osd-headless-v5.so:/simulation/fx3-osd-lifetime-v2.so:/simulation/fx3-preset-context-v2-screen.so:/simulation/fx3-timecode-capture-v1.so:/simulation/fx3-gpe-observe-v7.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /lib/ld-linux-aarch64.so.1 --verify /usr/bin/im.elf
 verify_rc=$?
 echo FX3_TRACE_ABI_VERIFY_RC=$verify_rc
 LD_PRELOAD=/simulation/fx3-skd-hw-unavailable-v1.so:/simulation/fx3-capid-v1.so:/simulation/fx3-osd-headless-v5.so:/simulation/fx3-osd-lifetime-v2.so:/simulation/fx3-preset-context-v2-screen.so:/simulation/fx3-timecode-capture-v1.so:/simulation/fx3-gpe-observe-v7.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /lib/ld-linux-aarch64.so.1 --library-path /lib:/usr/lib --list /usr/bin/im.elf
 list_rc=$?
 echo FX3_TRACE_ABI_LIST_RC=$list_rc
 LD_PRELOAD=/simulation/fx3-skd-hw-unavailable-v1.so:/simulation/fx3-capid-v1.so:/simulation/fx3-osd-headless-v5.so:/simulation/fx3-osd-lifetime-v2.so:/simulation/fx3-preset-context-v2-screen.so:/simulation/fx3-timecode-capture-v1.so:/simulation/fx3-gpe-observe-v7.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so /bin/busybox true
 true_rc=$?
 echo FX3_TRACE_ABI_TRUE_RC=$true_rc
 if [ "$verify_rc" != 0 ] || [ "$list_rc" != 0 ] || [ "$true_rc" != 0 ]; then
  echo FX3_TRACE_ABI_NOT_READY
  echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
  while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
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
 /simulation/seed-date-clock-v3
 date_rc=$?
 echo FX3_DATE_CLOCK_RC=$date_rc
 if [ "$date_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 echo FX3_BT_EMPTY_RECORDS_BEGIN
 /bin/busybox ls -l /setting/bt_conf.cnf
 /bin/busybox insmod /usr/kmod/kikilog.ko
 kiki_rc=$?
 echo FX3_KIKILOG_RC=$kiki_rc
 if [ "$kiki_rc" != 0 ]; then while true; do /bin/busybox sleep 1; done; fi
 /bin/busybox cat /proc/iomem
 echo FX3_OSAL_UIPC_BSS=$(/bin/busybox cat /sys/module/osal_uipc/sections/.bss)
 echo FX3_AP89_BACKUP_REPLAY_BEGIN physical=0x404000000 bytes=0x221000 original_seed_load_finished=1 AP_not_started=1 raw_RAM_input=1 not_storage_file=1
 /bin/busybox sha256sum /simulation/ap89-backup-ram.bin
 /bin/busybox dd if=/simulation/ap89-backup-ram.bin of=/dev/mem bs=4096 seek=4210688 count=545 conv=notrunc
 replay_rc=$?
 echo FX3_AP89_BACKUP_REPLAY_WRITE_RC=$replay_rc
 if [ "$replay_rc" != 0 ]; then echo FX3_AP89_REPLAY_FAILED; while true; do /bin/busybox sleep 1; done; fi
 replay_sha=$(/bin/busybox dd if=/dev/mem bs=4096 skip=4210688 count=545 2>/dev/null | /bin/busybox sha256sum)
 echo FX3_AP89_BACKUP_REPLAY_READBACK="$replay_sha"
 case "$replay_sha" in
  "38cf44637c44d3f47d7b8541dddf7ecc443e262f40dec3aec59f7b94d5b8b38f "*) echo FX3_AP89_BACKUP_REPLAY_VERIFIED;;
  *) echo FX3_AP89_REPLAY_FAILED; while true; do /bin/busybox sleep 1; done;;
 esac
 echo FX3_AP_NATURAL_BOOTIN_BEGIN
 echo FX3_AP_ARGV_target_qemu_WITH_TRAILING_SPACE_dmode3
 FX3_OSD_QUEUE_OWNER=native-receiver-v1 FX3_DISPLAY_OBSERVE=passive-v1 FX3_SYS_UUD=audited-run-preset-v1 FX3_SYS_TCMODE=headless-mode0-v1 FX3_OSD_LIFETIME=observe-v1 FX3_PEAKING=headless-config-v1 FX3_OSD_HEADLESS=software-ring-v1 FX3_CAPID_STORAGE=reserved-v1 FX3_BOOT_TAIL=audited-panel-hdmi-v1 FX3_HDMI_BOOT=disconnected-inactive-v1 FX3_SKD_HW=unavailable-rom-v1 FX3_PANEL_CONFIG=captured-enum2-consumer-v1 FX3_DIGITAL_LEVEL=disabled-sensor-op3-v1 FX3_BOOT_DEFERRED=muted-path3-v1 FX3_PIN_GRAPH=empty-owned-mode1-v1 FX3_BOOT_REPLY=timecode-getfunc-muted-v1 FX3_ADF_FILE=muted-user-v1 FX3_ADF_MUTED=silent-storage-v1 FX3_LCD_OSD=captured-v1 FX3_RELEASE_INHIBIT=idle-only-v1 FX3_MONITOR_LUT=inactive-identity-v1 FX3_CEC_POWER=software-disconnected-v1 FX3_HDMI_TC=inactive-disabled-v1 FX3_SA_ADDRESS=source-ranges-v1 FX3_VDF_OBSERVE=1 FX3_HDMI_AUDIO=inactive-format-v1 FX3_HDMI_PHOTO=inactive-preset-v1 FX3_REMOTE_DMM=two-slot-storage-v1 FX3_DISPLAY_INFO=software-640x480-v1 FX3_VDF_CONFIG=acceptance-shadow-v1 FX3_VDF_PLANE=double-cache-v1 FX3_HDMI_REGISTRATION=software-v1 FX3_CP_VERSION_TRANSPORT=unavailable-v1 LD_LIBRARY_PATH=/simulation:/usr/lib:/lib LD_PRELOAD=/simulation/fx3-skd-hw-unavailable-v1.so:/simulation/fx3-capid-v1.so:/simulation/fx3-osd-headless-v5.so:/simulation/fx3-osd-lifetime-v2.so:/simulation/fx3-preset-context-v2-screen.so:/simulation/fx3-timecode-capture-v1.so:/simulation/fx3-hdmi-registration-v1.so:/simulation/fx3-gpe-observe-v7.so:/simulation/signal-observe-v2.so:/simulation/ioctl-trace.so:/simulation/fx3-icrypt-observe-v1.so:/simulation/fx3-timer-observe-v1.so:/simulation/fx3-ui-gate-v1.so:/usr/lib/libInfraCrypt.so:/simulation/fx3-backup-return-v1.so /usr/bin/bootin.elf 'target=qemu ' dmode=3 &
 launcher=$!
 echo FX3_AP_BOOTIN_LAUNCH_PID=$launcher
 (while true; do
  for im_pid in $(/bin/busybox pidof im.elf); do
   echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
   /bin/busybox cat /proc/uptime
   /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
   echo FX3_AP_IM_ENDMAPS_${im_pid}_END
  done
  /bin/busybox sleep 1
 done) &
 echo FX3_BACKUP_CP_LIVE_OBSERVER_PID=$!

 for early in 1 2 3 4 5; do
  /bin/busybox sleep 1
  for im_pid in $(/bin/busybox pidof im.elf); do
   echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_BEGIN
   /bin/busybox cat /proc/uptime /proc/$im_pid/maps
   echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_END
  done
 done
 for turn in 1 2 3; do
  /bin/busybox sleep 10
  echo FX3_AP_SNAPSHOT_${turn}_BEGIN
  echo FX3_GUEST_UPTIME_SNAPSHOT; /bin/busybox cat /proc/uptime
  echo FX3_CPU_ONLINE_SNAPSHOT; /bin/busybox cat /sys/devices/system/cpu/online
  for cpu_group in cpu0 cpu1 cpu2 cpu3rt cpu0_1 cpu0_1_2 cpu0_1_2_3rt; do
   echo FX3_CPUSET_ACTUAL_${cpu_group}_BEGIN
   /bin/busybox cat /dev/cgroup/$cpu_group/cpuset.cpus /dev/cgroup/$cpu_group/cpuset.mems /dev/cgroup/$cpu_group/cpuset.cpus_migratable /dev/cgroup/$cpu_group/tasks
   echo FX3_CPUSET_ACTUAL_${cpu_group}_END
  done
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
     echo FX3_TASK_AFFINITY_${taskdir##*/}_BEGIN
     /bin/busybox cat "$taskdir/stat" "$taskdir/cgroup"
     echo FX3_TASK_AFFINITY_${taskdir##*/}_END
     echo FX3_TASK_SNAPSHOT_${taskdir##*/}_END
    done
   fi
  done
  /bin/busybox ls -l /proc/osal /tmp /setting
  /bin/busybox cat /proc/udm/dmm_units /proc/udm/dmm_extents
  echo FX3_AP_SNAPSHOT_${turn}_END
 done
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 echo FX3_AP_NATURAL_OBSERVATION_END

else
 echo FX3_UIPC_DEPENDENCY_OR_NODE_NOT_READY
fi
echo FX3_UIPC_ORIGINAL_MODULE_PROBE_END
while true; do
 /bin/busybox cat /tmp/fx3-send-stats-* /tmp/fx3-timer-stats-* 2>/dev/null
 for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
 done
 /bin/busybox sleep 1
done
