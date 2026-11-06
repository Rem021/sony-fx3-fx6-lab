#!/bin/sh

. /usr/bin/common.src

ud_pd_firmup.elf b || { echo "[ERROR] beets reset"; getledval.elf $ERROR_SYSTEM ; exit $? ; }
ud_reboot.elf      || { echo "[ERROR] reboot"     ; getledval.elf $ERROR_SYSTEM ; exit $? ; }

exit 0
