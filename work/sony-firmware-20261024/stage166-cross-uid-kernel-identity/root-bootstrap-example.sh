set -eu
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261028-03/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03/helper)
[ "$actual" = 'bcbdf155ae928c88d909166b5598c66757402c4be93041706e1ac21e1a63d441  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-03/helper /private/tmp/fx3-702-msc-owner-20261028-03/shared.bin 00000000000000000000000000000000
