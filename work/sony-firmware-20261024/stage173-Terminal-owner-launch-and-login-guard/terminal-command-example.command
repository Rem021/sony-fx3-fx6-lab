#!/bin/sh
set -euC
cd /
umask 077
/bin/mkdir -m 700 /private/tmp/fx3-702-msc-owner-20261029-05/terminal-command.once
printf "%s\n" '仅执行已批准的 FX3 单次接管与归还诊断；不认证、不读卡、不刷写。请在本机完成 sudo 验证。'
if /usr/bin/sudo -- /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c 'set -euC
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-owner-trials
/bin/mkdir -m 700 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-702-msc-owner-20261029-05/source-helper /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper)
[ "$actual" = '"'"'fa7b5da122b67f25349551edb1870fbe93dd870c7043721cb0a46e735346625d  /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper'"'"' ] || exit 78
exec /private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261029-05/helper /private/tmp/fx3-702-msc-owner-20261029-05/shared.bin 00000000000000000000000000000000 > /private/tmp/fx3-702-msc-owner-20261029-05/relay-stdout.txt 2> /private/tmp/fx3-702-msc-owner-20261029-05/relay-stderr.txt
'; then
    code=0
else
    code=$?
fi
printf '{"schema":1,"grant_id":"fx3-702-msc-owner-20261029-05","nonce":"00000000000000000000000000000000","returncode":%s}
' "$code" > /private/tmp/fx3-702-msc-owner-20261029-05/terminal-command-result.json
printf "%s\n" '本次命令已返回，请回到聊天核对结果；不要重复运行。'
exit "$code"
