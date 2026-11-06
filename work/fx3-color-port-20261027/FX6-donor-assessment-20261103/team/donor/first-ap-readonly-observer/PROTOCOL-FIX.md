# GDB resume 与 T05 分包修复

本阶段只改 host 观察器；此前两轮 run、各自源码快照、三入口 CPIO、客体 `/init`、17 helpers、FX3 Image/DTB/QEMU/环境均不改。精确差分见 [`protocol-fix.diff`](protocol-fix.diff)，旧端点取第二轮 `runs/ap-ro-c714785a/observer-{run_once,readonly_probe}.py`。13 项既有身份测试加 4 项协议测试共 17 项由 `python3 -B test_host.py` 复算，`python3 -B audit.py` 复核完整固定平台及原指令/ELF；两者仅为无 QEMU 主机证据。

修复仅在安装 `Z1` 且全机已暂停后，发无地址 RSP `$c#63`。固定 QEMU 11.1.2 源 `gdbstub/gdbstub.c` SHA `a03d5b7aa6a2188f4eebda464a6e6d7914dacfb0898136323c5c857c829cba6a`：997 行按命令设置 `allow_stop_reply`，1085–1093 行 `handle_continue` 只有带地址才改 PC，2085–2094 行的 `c` 描述符许可 stop；2332–2369 行说明运行中接收入站字节会暂停 VM，因此传输 ACK 后不再向 GDB 发查询或 keepalive。`gdbstub/system.c` SHA `196af474a5aacefab3394162b10537efcf9dbd55e2ec2fa291a0cbd71877352f`：123–215 行仅 flag 有效才发 `T…thread`，542–549 行的 `gdb_continue` 执行 `vm_start`。官方 [GDB 协议概览](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Overview.html)、[Packets](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html)、[Stop Reply Packets](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Stop-Reply-Packets.html)区分立即 `+` ACK 和 all-stop 完成后才返回的 T05。固定 QEMU 原文用于本次确切版本判断；文档不是本机运行回执。

`send_continue` 最多 2 秒等 ACK，若超时、断连、NACK 或 stop 早于 ACK，立即失败且不重发；ACK 后只读等待异步 T05。QMP `query-status` 独立记录 `running/debug` 转变；若到 `debug` 后 0.5 秒仍无 RSP stop，记录明确失败，不能称命中。命中时原 `T05thread`、QMP `debug`、当前 CPU 原指令、ELF/PHDR、动态 maps/TLS/同一 10B 请求和帧链门完全保留。只在停顿阶段执行寄存器和内存读取及断点替换；没有 `?`、`Z0`、单步、寄存器写、客体指令/数据写。正常清理仍逐个 `z1` 并确认后才执行原 API16 8B 软件关闭控制、原字 readback、退出/回收/双锁复核；`z1` 失败时不恢复客体。

无 QEMU 测试覆盖：ACK 与 T05 合并一次 `sendall`，分片及运行中出站静默，T05 延迟 2.1 秒超过旧普通命令 2 秒等待、超时/立即断连/NACK/错误顺序不重发、QMP `debug` 无 T05 的显式拒绝；旧 13 项中另有 checksum、映射、当前镜像、TLS/帧链、未知 CPU 和残余断点清理反例。当前阶段的主机测试不能预言实际 Z1 是否命中、model/owner 或 AP `w0`。

协调端审核后，本阶段获唯一运行授权。单轮命令为 `python3 -B run_once.py`；只有 runner SHA `6c0986e232858dd64dcbcb2045b19b77bf46831b46e49033ce6edd08015b1761`、probe SHA `d8f3887aac7af4d256f787ea8a554c5f230fe4988c7b602b94714c32118962a0`、identity SHA `d164c95a14e0d906083e6bbbd05facb4827cc1d4a59dbfc784830ebc2cd6de68` 完全一致，基线/CPIO/锁复核通过时才执行一次。脚本零键、观察 120 秒/总 180 秒、最多两次已识别断点停顿，run 输出进入新的私有目录且绝不覆盖历史。
