#!/bin/sh
set -euC
cd /
umask 077
cleanup_digest=$(/usr/bin/shasum -a 256 /private/tmp/fx3-host-cleanup-20261101-03/source-helper)
[ "$cleanup_digest" = 'e990a12bc9342fb3c25f31686b32b1645950667b1b419010baab6dbbbd37f136  /private/tmp/fx3-host-cleanup-20261101-03/source-helper' ] || exit 78
: > /private/tmp/fx3-host-cleanup-20261101-03/launch.once
cleanup_status=0
/usr/bin/sudo -- /bin/sh -c 'set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-03 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-03 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-03
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-03/source-helper /private/var/root/fx3-host-cleanup-20261101-03/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-03/helper)
[ "$cleanup_digest" = '"'"'e990a12bc9342fb3c25f31686b32b1645950667b1b419010baab6dbbbd37f136  /private/var/root/fx3-host-cleanup-20261101-03/helper'"'"' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-03/helper --confirmed-camera-USB-physically-disconnected
' > /private/tmp/fx3-host-cleanup-20261101-03/root-stdout.log 2> /private/tmp/fx3-host-cleanup-20261101-03/root-stderr.log || cleanup_status=$?
/usr/bin/printf '{"launcher_exit":%s,"new_camera_trial":false}
' "$cleanup_status" > /private/tmp/fx3-host-cleanup-20261101-03/launcher-result.json
exit "$cleanup_status"
