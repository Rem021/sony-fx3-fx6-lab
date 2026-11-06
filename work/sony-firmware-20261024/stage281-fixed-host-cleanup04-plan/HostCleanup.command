#!/bin/sh
set -euC
cd /
umask 077
cleanup_digest=$(/usr/bin/shasum -a 256 /private/tmp/fx3-host-cleanup-20261101-04/source-helper)
[ "$cleanup_digest" = 'db39253a9e1edc3a6c759264afd78d55c251d842b4b3fbf4b6f51a18d0fdfb27  /private/tmp/fx3-host-cleanup-20261101-04/source-helper' ] || exit 78
: > /private/tmp/fx3-host-cleanup-20261101-04/launch.once
cleanup_status=0
/usr/bin/sudo -- /bin/sh -c 'set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-04 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04/source-helper /private/var/root/fx3-host-cleanup-20261101-04/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04/helper)
[ "$cleanup_digest" = '"'"db39253a9e1edc3a6c759264afd78d55c251d842b4b3fbf4b6f51a18d0fdfb27  /private/var/root/fx3-host-cleanup-20261101-04/helper'"'" ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-04/helper --confirmed-camera-USB-physically-disconnected
' > /private/tmp/fx3-host-cleanup-20261101-04/root-stdout.log 2> /private/tmp/fx3-host-cleanup-20261101-04/root-stderr.log || cleanup_status=$?
/usr/bin/printf '{"launcher_exit":%s,"new_camera_trial":false}\n' "$cleanup_status" > /private/tmp/fx3-host-cleanup-20261101-04/launcher-result.json
exit "$cleanup_status"
