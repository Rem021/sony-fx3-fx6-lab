set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-03 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-03 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-03
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-03/source-helper /private/var/root/fx3-host-cleanup-20261101-03/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-03/helper)
[ "$cleanup_digest" = 'e990a12bc9342fb3c25f31686b32b1645950667b1b419010baab6dbbbd37f136  /private/var/root/fx3-host-cleanup-20261101-03/helper' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-03/helper --confirmed-camera-USB-physically-disconnected
