#!/bin/sh
set -euC
cd /
umask 077
trial_dir=/private/tmp/fx3-host-audit-20261028-01
actual=$(/usr/bin/shasum -a 256 "$trial_dir/probe")
[ "$actual" = '86ee5e828e78b1ecf41e040567c86f57449fa9e17a055e92354bfd23f3fd03c5  /private/tmp/fx3-host-audit-20261028-01/probe' ] || exit 78
"$trial_dir/probe" --user > "$trial_dir/terminal-user.json"
printf "%s\n" "仅核对本机登录与管理员进程身份，不访问相机；请在本机完成 sudo 验证。"
/usr/bin/sudo -- /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/sh -c 'set -eu
cd /
umask 077
/bin/mkdir -p -m 700 /private/var/root/fx3-host-audits
/bin/mkdir -m 700 /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01
/usr/bin/install -m 500 -o root -g wheel /private/tmp/fx3-host-audit-20261028-01/probe /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe
actual=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe)
[ "$actual" = '"'"'86ee5e828e78b1ecf41e040567c86f57449fa9e17a055e92354bfd23f3fd03c5  /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe'"'"' ] || exit 78
exec /private/var/root/fx3-host-audits/fx3-host-audit-20261028-01/probe --root
' > "$trial_dir/terminal-root.json"
printf "%s\n" "主机身份对照完成，请返回聊天。"
