set -eu
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-host-audits
/bin/mkdir -m 700 /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-host-audit-20261028-01/probe /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe)
[ "$actual" = '86ee5e828e78b1ecf41e040567c86f57449fa9e17a055e92354bfd23f3fd03c5  /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe' ] || exit 78
exec /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe --root
