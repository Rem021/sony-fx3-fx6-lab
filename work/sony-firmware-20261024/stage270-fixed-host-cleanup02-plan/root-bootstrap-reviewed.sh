set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-02 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-02 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-02
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-02/source-helper /private/var/root/fx3-host-cleanup-20261101-02/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-02/helper)
[ "$cleanup_digest" = 'a926996757e6d90474830d9bf7ae2977917221da72645baedec1caa9453db9ff  /private/var/root/fx3-host-cleanup-20261101-02/helper' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-02/helper --confirmed-camera-USB-physically-disconnected
