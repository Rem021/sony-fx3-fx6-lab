set -eu
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261028-04/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04/helper)
[ "$actual" = '661e679e725a6b5cc9431c63b747fb1d15412b05856663461bb856c232b00651  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04/helper /private/tmp/fx3-702-msc-owner-20261028-04/shared.bin 00000000000000000000000000000000
