# 通信04保留主机实例单次收尾修正包（`fx3-host-cleanup-20261101-04-r2`）

本方案修正了 Stage 281 `HostCleanup.command` 第 17 行因 Python 字符串拼接吞掉单引号导致普通 `/bin/sh` 在调用 `sudo` 前直接语法报错退出的问题（Stage 281 未执行 `sudo`、未启动 root helper、未发信号）。本包通过 `/bin/sh -n` 静态语法检查，绑定原根助手 `PID 37860`（`1793546568.487337`）与已退出观察器 `PID 36633`（`1793546063.372013`）。

- **授权标识（Grant ID）**：`fx3-host-cleanup-20261101-04-r2`
- **实际清理程序 SHA256**：`873581fd102696faee363d066b2bb42cbed34b66eee6d044459966c1eb47571d`
- **固定文件**：[`fixed-plan.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/fixed-plan.json) · [`build-and-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/build-and-check.json) · [`approval-bundle.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/approval-bundle.json)
