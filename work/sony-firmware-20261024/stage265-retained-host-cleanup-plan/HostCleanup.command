#!/bin/sh
set -euC
cd /
umask 077
cleanup_digest=$(/usr/bin/shasum -a 256 /private/tmp/fx3-host-cleanup-20261101-01/source-helper)
[ "$cleanup_digest" = '89dc2a57132d474fc178c271c8e11feda5aa7bd32dac83dd70301bd6843e02eb  /private/tmp/fx3-host-cleanup-20261101-01/source-helper' ] || exit 78
: > /private/tmp/fx3-host-cleanup-20261101-01/launch.once
cleanup_status=0
/usr/bin/sudo -- /bin/sh -c 'set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-01 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-01 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-01
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-01/source-helper /private/var/root/fx3-host-cleanup-20261101-01/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-01/helper)
[ "$cleanup_digest" = '"'"'89dc2a57132d474fc178c271c8e11feda5aa7bd32dac83dd70301bd6843e02eb  /private/var/root/fx3-host-cleanup-20261101-01/helper'"'"' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-01/helper --confirmed-camera-USB-physically-disconnected
' > /private/tmp/fx3-host-cleanup-20261101-01/root-stdout.log 2> /private/tmp/fx3-host-cleanup-20261101-01/root-stderr.log || cleanup_status=$?
/usr/bin/printf '{"launcher_exit":%s,"new_camera_trial":false}\n' "$cleanup_status" > /private/tmp/fx3-host-cleanup-20261101-01/launcher-result.json
exit "$cleanup_status"
