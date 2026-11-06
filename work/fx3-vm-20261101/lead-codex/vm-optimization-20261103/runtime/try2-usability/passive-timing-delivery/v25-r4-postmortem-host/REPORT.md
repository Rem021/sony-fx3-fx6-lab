# v25-r4 故障后离线诊断候选（未运行 QEMU）

## 结论与边界

本候选修正了 v25-r3 故障收尾的宿主证据顺序：先确认 QMP 暂停并完整读取 16 MiB OSD 环，再保存当前帧，随后独立尝试任务和 vCPU 快照，最后才恢复 API16、quit、reap。`query-cpus-fast`、HMP 错误响应、错误文本和接收超时均有独立失败边界；不能让可选寄存器查询遮蔽核心环或跳过清理。QMP 发送若超时或报错，可能已经发送部分 JSON，因此传输标记 `send_unknown`，不追加下一条命令或重发；此时 API16 可能无法恢复，必须如实失败并走 QEMU 进程回收，绝不声称完成。

固定 r3 guest 没有故障时的 task 身份快照通道。独立构建的 **r4e 只读 `/proc` 诊断 CPIO** 仅供审查；runner 默认仍固定 r3，只有显式 `--review-procdiag-r4e` 才会选择新 CPIO。本轮没有 guest 实跑，既没有证明卡顿根因，也没有修复真实停滞或通过 API16 生命周期门。

## 已有故障证据与待区分项

真实 v25-r3 轮的第 16 次 DOWN 宿主控制字写入并读回，但 guest 没有该步 KEY96 轮询、native down/up 或 done。最后帧 3718 的宿主提交观察比请求早 22.237 秒；该键不是已证实的冻结原因。最后 KEY96 TID343 的 guest 轮询和 PROC97 PID237 状态早于故障，不能代表故障时的线程状态；FILE100 PID148 的 `restore_seen=0` 只说明 `system(fx3-sync100-shutdown.sh)` 未返回或前一阶段未走到该处。详情见 `../../runs/v25diag-web-r3-91001f82/MANUAL-BROWSER-DIAGNOSTIC-RESULT.md`。仍须分辨 Backup 双读阻塞、shutdown 子进程阻塞、进程组停止和其他等待；历史 group-stop 材料只是线索。

## 原始身份来源和新采集

- 原 KEY96 输入挂点 `menu-repair-01/runtime/helpers/fx3-rm-key-gate-v5-diag96.inc:18` 将 AArch64 `getpid/gettid` 写到 `/tmp/fx3-keyworker96.identity`；同文件要求 `memrsv=0x00010000@0x41df00000:uc`，只在 64 KiB 头部发布输入控制。新 helper 读这两个数，再读对应 `/proc/PID/task/TID`。内存分区按冻结 runner 的只读快照配置审计：date98 用 KEY93+0x1000..0x7000，date99 用 +0x8000..0x9000；诊断仅写 +0x9000 的 4 KiB 头与 +0xa000..+0x10000 的 24 KiB 槽。源码搜索未发现其他对该尾部的写者，但尚未做 guest 装载验证。
- 原 FILE100 observer `menu-repair-01/runtime/helpers/fx3-file100-observer-v2.c:14` 将 `F100FILE_READY_V2 PID` 写到 `/tmp/fx3-file100-ready-v2`。新解析要求完整前缀、严格十进制 PID 与行尾；定向测试排除了误把标记中的 `100` 当 PID 的旧实现。
- 原 r3 `/init` 的 `FX3_BACKUP_CP_LIVE_OBSERVER_PID=$!` 只打印 PID。派生 `/init` 在该唯一锚点增加同一 `$!` 的临时身份文件，再启动诊断 helper。`proc97_child` 来自 `/proc/PID/task/PID/children`，与 shell 身份来源单独标记；最多四个子 PID。`mainim` 使用 KEY96 标记的同进程主 TID=PID，不把 vCPU PC 当 guest TID。
- 每个已确认身份分别读 `cmdline/status/wchan/syscall/stack/stat`；每个文件由本 helper 自己 fork 的子进程隔离，100 ms 单文件上限、3 秒单快照总上限、最多 24 个未回收子进程，超时、截断、打开失败、读取失败、未回收均明确记录。只有完整数据包才允许后续同一路径读取；完整写包但子进程尚未退出时只登记回收，不误判该路径仍阻塞。未读到文件、线程消失、`/proc` 不支持 children 或权限不够，均保留 unknown。
- 仅在真实输入 pending 时 1 秒后开始被动采样，此后距前次完成至少 2 秒，单键最多 16 次；一个 24 KiB 槽覆盖写，序号、长度、guest `CLOCK_MONOTONIC`、FNV 和尾序号校验。若 guest 采样子进程自身阻塞，最后样本会变旧，不能把旧内容当作暂停瞬间。宿主在同一 QMP 暂停窗口保存完整 KEY93 64 KiB、环和寄存器；只以**guest 同钟**比较 helper 时间与 ring 事件。原 r3 无该 magic 时回执为 `diagnostic_not_loaded_or_no_capture`，不推断线程正常。

## CPIO 与安全差异

源 r3 候选 SHA256 `a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`，源 CPIO `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`，原 `/init` `8ad0be3aec240977060e25ba1193ad80f6ef596ffe47392e3d5b5b79c0ee4a05`。最终新候选为 `vmopt-20261104-v25-procdiag-r4e/`，manifest `ced1644fbcecc542c3d90f16be2a461876e7f3af92ff639c793742f090136d22`，CPIO `439f9089d3e36b6a5ee0d3f16a170a608761f315a4a2169d1d859cb0f66952db`，helper ELF `057249b011acfd22a7f49885e9c6f802147099ee85dad0488f653a57dc28473a`。独立 newc 审计：1140→1141 成员，仅 `init` 和新增 `simulation/fx3-procdiag-v1` 内容不同；父目录先于子文件，无重复/不安全名称，DTB 与 Backup manifest 完全相同。`init-procdiag.diff` 仅三行插入；原 kernel、QEMU、5000 ms 超时、AP 状态、省电设置与默认入口均未改。早期试构建 r4/r4b/r4c/r4d 留作历史，其中 r4d 误占 date98/date99 的既有观察内存，严禁使用；**只有 r4e 是本报告候选**。

## 宿主测试与下一轮最小观察

`test_qmp_line_transport.py` 使用真实 socketpair 复现迟到旧 ID、分段行、异步事件、事件洪泛截止、EOF、超长行和部分发送后拒绝继续；通过。`test_quiesced_diag_readback.py` 覆盖完整环优先、寄存器/HMP 错误和例外、活态拒绝；通过。`test_procdiag_readback.py` 覆盖 magic 缺失、序号/FNV/尾序号和暂停态可选读取失败；通过。`test_procdiag_core.c` 在宿主用临时文件/FIFO 验证严格身份解析、100 ms 有界读取、未回收子进程识别；通过。`test_input_deadline_classification.py`、`py_compile`、runner `--help` 通过。以上均为**离线验证**，不等于 guest、浏览器或 API16 通过。全部文件哈希见 `SOURCE-FREEZE.json`；宿主与前一候选差异见两份 `r3-postmortem-to-r4-*.diff`。

待另行批准一轮真实网页与 guest：复核卷 UUID、双锁、进程、固定哈希，先看最新完整 PNG，再发一键。首次 unknown ACK 或原生错误立即停键，先暂停读取环/当前帧/KEY93 任务快照/vCPU，再按原 20 秒 guest ACK、API16 原字、quit/reap 和双锁收尾。对比 KEY96、FILE100、mainim、observer shell/child 的 PID/TID、状态、wchan、stack 与采样时间；未命中同一时刻或采样丢失只能报告 unknown。`--review-procdiag-r4e` **不代表已获下一轮 QEMU 授权**，默认入口保持旧版。
