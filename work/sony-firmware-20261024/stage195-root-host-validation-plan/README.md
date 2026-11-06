# FX3研究：独立root仅主机对照01固定方案

2026-10-29。**这是待单独批准的主机试验，不是相机试验或刷写批准。** 两种程序已编译；已执行的均为普通用户版本。root版本从未运行，root专属目录和固定/private/tmp作业均未创建。

## 待批准的具体动作

编号 `fx3-host-root-20261029-01`。在当前Mac、用户501的图形登录会话中，创建一个新作业并打开Terminal。必要时由用户本人完成一次原生sudo/Touch ID验证。一次sudo启动链最多运行固定程序两次：

1. `trial`：验证root真实/有效UID、当前console用户、audit/GUI/TTY归属、固定路径和root0500程序身份；经内核身份＋出生时间＋程序自读摘要握手后，校验64字节本机内存，写下自己的私有回执。
2. `readback`：用另一个nonce和新的进程握手，从同一受保护目录读取刚保存的回执并返回。试验、回读各有一个不可复用记录，失败不删除、不重试。

Root程序不包含、也不链接IOKit/USB/MSC/固件后端，没有相机、驱动、分区、IP网络、Sony认证或刷写动作。唯一 `/dev` 路径用于 `stat("/dev/console")` 的登录归属检查，不对该设备进行读写。相机无需连接、推出卷、切换模式或配合操作。不会申请/修改完全磁盘访问、可移动卷、输入监控或审计身份权限。

新增文件范围固定如下，不修改旧05或真实设备排他记录：

| 路径 | 内容与权限 |
| --- | --- |
| `/private/tmp/fx3-host-root-20261029-01/` | 用户501的0700作业；两份4096字节600数据页、600 Unix socket、500程序预复制、700 Terminal脚本及600记录 |
| `/private/var/root/fx3-host-validation/` | 若不存在则新建为root0700；已存在时只核对，不自动改权限 |
| 上述目录下的 `fx3-host-root-20261029-01/` | 全新root0700目录；500 helper、400 trial/readback一次记录、600 host-only.journal和256字节host-result.bin |

安装前后核对固定SHA256，清空继承环境；Helper自身再次核对固定安装位置、属主和0500权限。Root数据只通过已核对的本地Unix连接传递。程序及完整参数、两份nonce、精确摘要见[固定计划](fixed-plan.json)、[批准包](approval-bundle.json)、[仅生成未执行的Terminal命令](RootHostValidation.command.txt)。批准对象是批准包的完整SHA256；旧的单次主机/相机授权不能代替此01方案。

## 已完成的本地验证

[15项普通用户检查](host-test-results.json)覆盖实际可执行程序的两次进程握手、私有归档与新nonce回读；清除第一次存活证明后的查询；文件解析不等于认证；坏权限、短文件、坏摘要、symlink、hardlink、文件缺失；安装摘要拒绝、双层一次性限制、停止请求、HOST作用域/身份/nonce及特殊shell路径。

其中“丢失上下文”是在同一观察者进程中清掉第一次证明的明确模型，不等于实际Orca重启。普通用户版本的保护目录也不是root隔离边界。root→501、root0500读取和真实受保护文件行为仍需本次对照。批准边界与模板语法的附加检查见[边界回执](approval-boundary-results.json)。

[构建回执](build-receipt.json)保留依赖与未解析符号清单。root程序不包含owner核心、IOKit wire、MSC会话或原固件；普通用户可执行版本启用ASan/UBSan。读写与回读实现见[主机程序](host_trial.c)、[主机监督器](host_supervisor.py)、[记录解码](host_records.py)。

## 判定与限制

成功仅表示这套主机身份、文件和回执链路通过root实测；绝不表示FX3备份/恢复、硬件模拟或刷写安全已经成立。Root私有文件的fsync、摘要及当前回读不是断电持久性、APFS故障或相机救砖证明。用户目录的JSON/bin仍不能单独充作认证回执。

当前[监督器入口](run_approved_host.py)在新方案未获精确批准时拒绝准备/启动。超时保留同一实例与数据，不强杀、不重置、不自动重试；如果本机文件调用阻塞，只记录UNKNOWN。任何额外回读、重试或不同编号均不自动获得批准。

本轮没有管理员或设备操作。原有全部16项、恢复优先与MAIN HD 29.97/30 HEVC目标不变，`goal_complete=false`、`persistent_write_release=false`。本方案执行前仍须新增一次具体确认；此前相关管理员试验授权均为单次，已经用完。
