set -eu
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01
/usr/bin/install -m 500 -o root -g wheel /Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage156-hardened-owner-launch-and-ack/artifacts/owner-native-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper)
[ "$actual" = 'c07ea1ba2f0bf98e57de8f3a578080ef3ed6b8ef60a3c27749ffa8a107fd9fcd  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-01/helper /private/tmp/fx3-702-msc-owner-20261028-01/shared.bin 00000000000000000000000000000000
