# 第二次唯一窗口：CAP Z1 已安装，GDB 停顿回包未到达

原始目录 [`runs/ap-ro-c714785a/`](runs/ap-ro-c714785a/) 保存本轮不可覆盖的 `command.json`、PID、串口、源码拷贝、`readonly-observation.json`、API16 原字与 [`receipt.json`](runs/ap-ro-c714785a/receipt.json)。运行前独立复核卷 UUID、双锁 free、无 QEMU、13 项 host-test pins；固定 runner SHA `928306a009abaaf596cd4f90fa515e66f991a8b41620ab1906ba8966554068e4`、probe `fec9ce951a078522b73766dbc7e0390563a5d1a581d9caa451b7c92de87b2a0c`、identity `d164c95a14e0d906083e6bbbd05facb4827cc1d4a59dbfc784830ebc2cd6de68`，均与 run 内源码快照相同。QEMU PID69033、owner PID69031；零键且没有额外 MPR 断点。

## 实际范围

原程序运行得到 PID237 的完整第一轮 `FX3_AP_EARLY_MAPS`，CAPID 原 ELF 的七条同 inode 映射计算 bias `0x7f973f0000`，runner 按该次动态 VA `0x7f9740e730` 安装一个 `Z1` 并进入 `await_audio_entry`。`readonly-observation.json` 最终 `records=[]`：**没有 GDB T05 停顿回包，没有当前 CPU ELF/PHDR/原指令/TLS/请求/调用帧的读取，也没有 CAPID model/owner 或 AP `w0`。** 清理时该断点 `z1` 回复 `OK`，残余断点集合空。

120 秒观察预算自然结束，含清理共 121.432901 秒，`host_error=null`，`stop=observation_budget_end`。串口 SHA `564eb0c28480197ca28d0b0031d1dbe6b93a05a855f8a9093d60ba62a69959c9`：目标 10B 原请求位于字节 1876269，原 1075 行断言位于 1876405，受控清理标记位于 1876680；本轮运行中只读轮询在串口长度 1876405 时尚无 assert，之后最终串口才有断言。这与暂停在两者之间、清理后再继续一致，但本 runner **没有持久化清理前 QMP `debug` 状态或 GDB 命中包，不能据此声称 Z1 确实命中，更不能填 `-1021`**。本次断言发生的路径也不能当作已确认的 `audio_dispatch` 返回。

API16 清理原字 readback：初始 `5000005800021fd6bcfc4d0080ffffff`，软件 observer 8B shutdown 请求后客体 ack、最终 `000b00b4fd7bbba9fd030091f35301a9`；[`restore103-receipt.json`](runs/ap-ro-c714785a/restore103-receipt.json) 保留每次采样。QEMU `exit=0` 且已回收，两个 PID 均不在、双锁 free，平台/CPIO/AP/CAP 输入 SHA 前后匹配。正常清理成功不等于服务/硬件验收。

## 首个确定的观察协议错误

新 [`rsp-stop-audit.py`](rsp_stop_audit.py) 固定运行串口/回执/源码及本地 QEMU 11.1.2 源 SHA，复算 [`rsp-stop-audit.json`](rsp-stop-audit.json)，状态 `HOST_ONLY_GDB_STOP_REPLY_GATE_IDENTIFIED_RUNTIME_HIT_UNPROVEN`。本地 `gdbstub/gdbstub.c` SHA `a03d5b7a…` 在 997 行把接收命令的 `allow_stop_reply` 写入全局；`c`/`vCont` 命令描述符允许停顿回包，接收新字节时先清 flag。`gdbstub/system.c` SHA `196af474…` 的 `gdb_vm_state_change` 在约 144 行遇 flag=false 直接返回，只有 flag=true 才在约 211 行发送 `T…thread`。本轮 runner 在 `Z1` 后及两断点间仅用 QMP `cont` 恢复，**没有向 GDB stub 发 `c`/`vCont;c`**，所以即便 CPU 停在断点，也不能期待异步 `T05` 包；静态代码解释了 `await_audio_entry` 的停滞，不单独证明真实 CPU 停顿。`?` 不能用作补救：同一 QEMU 源会在查询时移除断点。

下一最小工程修正是**仅在 host runner** 使用有界 GDB resume packet 建立回包许可，严格分别处理发送 ACK 与稍后异步 `T05thread`，并与 QMP `debug` 状态交叉核；原 QMP stop、CPU/ELF/TLS/请求/帧链身份门、`z1` 清理和 API16 恢复不放宽。该修正还需要单独的无 QEMU 协议测试、SHA 冻结、协调审核及新的唯一 VM 窗口。**本任务只运行上述一次，不自动重跑。**
