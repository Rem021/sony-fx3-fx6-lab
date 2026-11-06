set -euC
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261029-05/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper)
[ "$actual" = 'fa7b5da122b67f25349551edb1870fbe93dd870c7043721cb0a46e735346625d  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper /private/tmp/fx3-702-msc-owner-20261029-05/shared.bin 00000000000000000000000000000000 > /private/tmp/fx3-702-msc-owner-20261029-05/relay-stdout.txt 2> /private/tmp/fx3-702-msc-owner-20261029-05/relay-stderr.txt
