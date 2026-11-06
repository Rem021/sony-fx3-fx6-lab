set -eu
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261028-02/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02/helper)
[ "$actual" = '1182295ad4405fc30773673467ae2d6b1bb8b3ca26343a6e02c76a1dc9fd9e0b  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-02/helper /private/tmp/fx3-702-msc-owner-20261028-02/shared.bin 00000000000000000000000000000000
