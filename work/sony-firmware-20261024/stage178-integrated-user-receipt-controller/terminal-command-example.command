#!/bin/sh
set -euC
cd /
umask 077
/bin/mkdir -m 700 /private/tmp/fx3-702-msc-owner-20261029-06/terminal-command.once
printf "%s\n" '固定单次诊断；如需 sudo 验证，请在本机完成。'
if /usr/bin/sudo -- /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c 'set -euC
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261029-06/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper)
[ "$actual" = '"'"'aea5b9c76d0c2a55f09d56706164e8ce6a5a413f9c0875cb6c30a93ea5015703  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper'"'"' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-06/helper /private/tmp/fx3-702-msc-owner-20261029-06/shared.bin 00000000000000000000000000000000 2>&1
' > /private/tmp/fx3-702-msc-owner-20261029-06/relay-stdout.txt; then
    code=0
else
    code=$?
fi
printf '{"schema":1,"grant_id":"fx3-702-msc-owner-20261029-06","nonce":"00000000000000000000000000000000","returncode":%s}
' "$code" > /private/tmp/fx3-702-msc-owner-20261029-06/terminal-command-result.json
exit "$code"
