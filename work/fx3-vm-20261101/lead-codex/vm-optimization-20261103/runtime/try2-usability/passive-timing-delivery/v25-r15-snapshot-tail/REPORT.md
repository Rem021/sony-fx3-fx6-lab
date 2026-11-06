# r15 按请求不可变统计快照：离线候选

**结果：N1/N64 交叉构建、实际 C 受控序列、宿主接线定向测试和静态 ABI 审计通过；未构建 CPIO、未启动 VM、未部署。** 本候选只为后续有界对照准备。原 r13/r14、固定 r3 runner manifest、FX3 平台、原固件、5000ms 与 API16 恢复合同未改。新 ELF 保留调试符号；可装入原槽位的派生与审计由另一独立任务处理。

## 输入与修改

- r14 C `f1bd05b39ac054e4ffef74f4821858ee3a7f2f241689f28b68ff6c039be4212a`，r13 runner `ae0ed0b45dd748db94979e126dfef5ea8232c99001799fac9cd5836619b54cc6`；协议依据为 `../r14-snapshot-protocol-review/DECISION.md` SHA `05cff9f1aa5edc2945c339cde0f52a00e9bb1a968c67e1950fe48d4d12dc37a5`。精确改动见 `r14-to-r15-guest.diff` 和 `r13-to-r15-host-runner.diff`。
- guest 的原普通 RAM `st`、原子计数与锁保留。原 60 组 offset/word/register 表及汇编逐字节一致，汇编 SHA `b82a530c86ad3d37e06ba37828c72942c3c9188d904ed2b3a3bee89ebf9f62a1`；旧统计仍逐次精确更新，仅原 r14 N1/N64 bank 发布频率有别。
- 在已预留 64KiB 中使用 request `+0x3000..3040`、ready/ACK `+0x3040..3100`、98Q payload `+0x3100..3410`；boot 区始于 `+0x4000`。`:uc` 映射只做对齐 32bit 普通 load/store 与 `dmb sy`；trylock、完成位、原统计原子都留在进程普通 RAM，不在 `:uc` 上做 exclusive/RMW。
- boot 与普通 probe 都在本次原统计之后检查请求。无请求普通热路径不新增 gettid syscall；拿到 writer 并验证 request 后才读取 TID。BSS trylock 忙立即返回；一个 run 的首个有效 nonce 提交后不重用 slot。payload 逐字段原子 load，不宣称事务一致；记录 guest `CLOCK_MONOTONIC` id1 的 copy 起止。errno、原返回和原寄存器保存路径未改；此处是静态及 native C 证据，非 guest 汇编执行验收。

## 宿主尾段合同

`--snapshot-tail` 默认关闭。r15 runner 仅在原 End stop 已完整读回 16MiB ring、原 optional/frame/native-file 读取尝试结束后，且 API16 restore 之前调用新 helper。ring 全零但字节读回完整时，tail 可独立尝试，原 ring 解析失败和 health 失败标记仍保留；原读回不完整则尾段标 `not_attempted`。默认关闭不增加 QMP 命令，PAGE、key、确认、4096 键上限及浏览器协议原字节不变。

helper 先以原 QMP 传输重证 paused，再核新版 v5 ready、旧 UI 身份、PID/root/区域，使用 host launch UUID 的 SHA256 低 64bit **回显 tag**及随机 nonce；guest 没有独立识别 host UUID 的能力。先写 request 前 60B、读回，再写 commit4B、读回。共享采集绝对预算 2s 尚余时才 `cont` 一次；运行态只等待完整串口 ACK 行，支持 CRLF 及分片，不用运行态 GDB 轮询。随后有界 `query-status`、必要时 `stop`、再次证明 paused；在独立最多 5s 的尾段停止/可选 slot 预算内读同一不可变 0x3d0B slot 两次，核身份、nonce、长度、commit、FNV 与两次字节一致。迟到文件读不能标有效。

诊断 GDB 借用唯一连接，恢复原 timeout；半包、未知回复或新连接物理模式未证时关闭该流，原恢复路径须新连并重新核物理模式，旧迟到回复不会被误认为 API 恢复回复。`cont` 回复丢失仍视可能已运行；尾段尝试停机并复核，runner 若仍未证 paused，在诊断预算外做必要的有限停机复核，无法证明暂停则不做不安全的 API16 写入，仍走原 quit/reap 资源回收。QMP `send_unknown` 不盲重发。tail 的诊断失败不覆盖原 ring/health 结果。

`snapshot_is_end_state=false`：ACK 之后到实际停机仍可能有自然事件，后续计数未知；本次额外 cont 时间也不并入首帧或性能窗口。若请求已写而未 cont，原恢复阶段可能让 guest 晚些服务它，不能把那种晚结果算作 End checkpoint。一次 checkpoint 不能证明镜像发布成本导致了卡顿。

## 离线回执与限制

- `BUILD.json`：N1/N64 使用原 Zig/guest SDK 命令交叉编译 exit0，未定义符号集合与原 v11 相同；产物 SHA 分别为 N1 `5faeb996c4c7386383a9e07ab5cc9f65c5e9e80217e5e777f15df7d26b9c8dbc`、N64 `ea47aa2d2b437700f00e64d8f3c0db7cf164c2c81f90bdedfb528a0430784574`。
- `AUDIT.json`：原指令表、汇编、98Q 尾部、布局及 ELF 依赖通过。`test_guest_snapshot_actual.c` 在 host ARM64 直接包含实际 r15 C，N1/N64 各测普通、boot、多 producer；无请求路径不多发 TID syscall，错误版本/PID/root/长度/nonce不提交，完整 98Q/FNV/原 errno 与成功后不可变通过。测试桩代替 guest loader/assembly，不能代表 guest GPR/SIMD/NZCV 或真实调度。
- `HOST-TEST.txt`：12 个宿主测试通过，执行实际 helper 和 runner 收尾源码摘取；包括默认关闭、零 ring 解析失败仍独立捕获、无请求/超期不 cont、丢失 cont 回复重证暂停、send_unknown 禁止重发、半写/错 nonce/两读差异/晚读不标 valid、CRLF 与分片完整行、GDB 迟到流隔离及新连接物理模式失败隔离。mock 不等于 QEMU runtime 验收。
- 限制：磁盘读写不能硬中断；超时结果按单调时钟标 unknown，原恢复/退出预算与尾段预算分开。后续需由独立审查把新 ELF 装进**新的**固定平台 CPIO 候选、审核 source pins，再授权单次真实 guest 运行；旧 r3 CPIO 不含 v5 ready，直接开启此 flag 会安全失败而非得到快照。

源码清单在 `SOURCE-FREEZE.json`，全交付校验在 `SHA256SUMS`。本报告只证明离线候选，不宣称渲染、生命周期或用户可用性通过。
