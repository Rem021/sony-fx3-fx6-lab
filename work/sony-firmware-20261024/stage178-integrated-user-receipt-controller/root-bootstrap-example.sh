set -euC
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261029-06/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper)
[ "$actual" = 'aea5b9c76d0c2a55f09d56706164e8ce6a5a413f9c0875cb6c30a93ea5015703  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper /private/tmp/fx3-702-msc-owner-20261029-06/shared.bin 00000000000000000000000000000000 2>&1
