set -eu
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01
/usr/bin/install -m 500 -o root -g wheel /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage156-hardened-owner-launch-and-ack/artifacts/owner-native-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper)
[ "$actual" = 'c7ea25dc0889c67cfb9a8c306bc9eb7a9c0c8b418ac81e1178f86f6c25bd2c98  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper /private/tmp/fx3-702-msc-owner-20261028-01/shared.bin 00000000000000000000000000000000
