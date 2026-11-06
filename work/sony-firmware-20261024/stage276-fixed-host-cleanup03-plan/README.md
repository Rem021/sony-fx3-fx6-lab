# 通信03保留主机实例的单次收尾方案

本方案只处理Mac上的原helper PID29141和观察器PID12633。**已编译并核对，尚未批准、暂存或启动。** 用户已确认FX3全部USB数据线从机身侧拔下、两个数据口保持空置，电池拍摄界面和菜单正常；独立缓存未见Sony节点。整个收尾期间保持断开，本程序不打开USB判断连接。

## 为什么需要独立批准

[274固定方案](../stage274-fixed-service-access-communication03/README.md)约定“阻塞或不明保留UNKNOWN和原实例，不强杀、重置或自动重试”。本次读0在12字节头返回后进入HELD，且不满足仅preSERVICE的协作退出条件。下面是对原“不强杀”约定的一次明确例外；已消耗的274通信和270清理授权都不覆盖。

[275实际回执](../stage275-service-access-communication03-execution/actual-runtime-review.json)与[物理断开记录](../stage275-service-access-communication03-execution/physical-disconnect.json)固定了本次来源。没有固件或模块写入，正常界面检查不等于录像、正常STOP返回或救砖验收。

## 固定操作与范围

最多启动一个新管理员程序，必要时由用户完成Terminal中的sudo／Touch ID验证。程序、不可重用标记及记录暂存于Mac内置盘私有目录`/private/tmp/fx3-host-cleanup-20261101-03`和`/private/var/root/fx3-host-cleanup-20261101-03`。

1. 同时核对原helper的UID0、PID29141、出生时间1793532602.162350、固定root路径及映像SHA；原观察器UID501、PID12633、出生时间1793531837.535029、Python路径及映像SHA也须匹配。
2. 只用task-name端口读取内核audit token并核对PID版本和路径，随后释放端口；不取task控制端口，不访问进程内存或注入代码。
3. 只读原`/private/var/root/fx3-owner-trials/global-fx3-owner.journal`，核对尾部确属上述原helper，记录文件身份和完整摘要。
4. 仅对匹配的原helper发一次SIGKILL(9)，最多观察约2秒；未确认原实例消失即停，不动观察器、不追加信号。
5. helper已消失后，仅对仍匹配的原观察器发一次SIGTERM(15)，最多观察约2秒；若它已自行退出，仅记录，不向复用PID发信号。
6. 只读复核原journal身份和完整字节摘要未变。保留全部81帧、私有记录及HELD/UNKNOWN，不清日志、不写CLEAN、不放行新通信。

全部信号以内核audit PID版本绑定，不降级裸PID。任何不匹配、错误或不确定即停，不重试。不关闭其他应用，不访问USB、相机、卡、驱动或固件，不改隐私权限。root程序及收尾结果不代表原通信正常完成。

## 已完成核查与边界

实际程序SHA256：`e990a12bc9342fb3c25f31686b32b1645950667b1b419010baab6dbbbd37f136`。

[固定计划](fixed-plan.json) · [构建核查](build-and-check.json) · [批准包](approval-bundle.json)。绑定信号核心与270逐字节一致，cleanup主逻辑仅修改注释，核对忽略注释后相同；复用265的普通子进程/错误audit版本拒绝及270实际收尾证据。本次新目标、出生时间、映像、目录及构建均已固定。普通UID直接拒绝，未访问目标或发信号；依赖不含IOKit，无裸kill或task控制符号。没有为增加数量重复执行信号试验。

本次root收尾、journal读回和两个原实例退出仍未发生，必须用实际结果另验收。程序未暂存、未打开Terminal、未要求管理员验证。此包不授权新Sony认证或任何机身写入。
