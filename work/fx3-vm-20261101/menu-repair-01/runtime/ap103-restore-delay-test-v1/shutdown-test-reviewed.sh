#!/bin/sh
echo FX3_RESTORE103_TEST_DELAY seconds=5 test_only=1
/bin/busybox sleep 5
echo FX3_AP100_CONTROLLED_CLEANUP_BEGIN acceptance_window_closed=1
for p in $(/bin/busybox pidof im.elf); do /bin/busybox kill -STOP "$p"; done
/bin/busybox sleep 1
/bin/busybox insmod /simulation/fx3-sync100-unbind-v1.ko
rc=$?
echo FX3_AP100_CONTROLLED_CLEANUP_END unbind_result=$rc primary_module_resident=1
exit $rc
