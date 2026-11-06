set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-04-r2 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04-r2 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04-r2
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04-r2/source-helper /private/var/root/fx3-host-cleanup-20261101-04-r2/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04-r2/helper)
[ "$cleanup_digest" = '873581fd102696faee363d066b2bb42cbed34b66eee6d044459966c1eb47571d  /private/var/root/fx3-host-cleanup-20261101-04-r2/helper' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-04-r2/helper --confirmed-camera-USB-physically-disconnected
