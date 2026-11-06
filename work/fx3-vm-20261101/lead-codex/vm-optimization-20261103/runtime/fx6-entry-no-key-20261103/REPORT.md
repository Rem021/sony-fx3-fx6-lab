# 固定 FX3 平台 FX6 双入口零键实验：有界入口证据与资源回执

2026-11-03。**授权的补测已取得 guest loader 三项 RC=0、自然 bootin 入口、`im.elf` 映射和首条原 FX3 AP 发送观察；这不是完整 FX6 系统、FX6 菜单或 IPC 完成证明。** 候选是供体静态审核通过的 `guest-two-entry.cpio` SHA256 `ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40`，只变更 `bootin.elf` 与 `im.elf` 两个等长成员；后者 PT_LOAD 与 FX3 逐字相同。实验保持固定 FX3 内核、完整 DTB、QEMU、CPU×4、5120MiB、GICv2、五项 model_env、原 `/init`、17 个预载和 Backup，原命令只允许 serial 与 CPIO 路径变化。原 `cpio_audit.audit()` 实际返回 1140 成员、20 个原 ELF、两个精确身份差异、父目录顺序错误为 0、`safe_to_unpack=false`；隔离放行同时匹配独立 donor `review.py` 的两个 SHA/字节数，不放松其余拒绝条件。

首次宿主预检产生 `runs/fx6entry-e5cd066a/preflight-failure.json`：误将允许变化的 CPIO 文件名也与冻结命令比较，故在 QEMU 创建前拒绝。修正为只比较 loader 地址与 `force-raw` 尾项后，独立离线测试确认实际变更索引仅 `[20,31]`，完整 DTB/内核未变。该预检不算 guest 轮。

唯一实际 QEMU 轮 `runs/fx6entry-b3256731/receipt.json`：PID 30381，5.554 秒，`-S` 停在初始暂停态，宿主 `QMP` 用过长绝对 AF_UNIX 路径导致 `OSError('AF_UNIX path too long')`，在 `cont` 前终止。serial 文件 0 字节 SHA256 `e3b0c442…`，三个 loader RC、自然 bootin、IM maps 和首个 IPC 全部 **unknown/未观察**；零键、零合成事件。QEMU exit 0、reaped、PID absent，输入 SHA 未变，两把原锁 free；本轮未能经 QMP 核验 API16，`API16_restored=false`，不能称生命周期通过。旧 runner 源在该 run 的 `observer-source.py`，原始错误保留。

新 runner 离线修复为与原 runner 同样先临时切到 run cwd、以短名 `q` 连接、再恢复 cwd；本地 mock AF_UNIX 服务器验证握手、`qmp_capabilities`/`cont` 两条 QMP 响应以及 cwd 还原通过，修正后 runner SHA256 `3bdc9121ac331a947fc157fc5aa1455a531140a0d2700dd1fed77f9db1f37a5e`。以上首次报告原文另存 [REPORT-first-attempt.md](REPORT-first-attempt.md)，不将失败轮改写为成功。

## 协调者额外授权的一次补测

- 实际运行 `runs/fx6entry-a39715a8/`，`receipt.json` 与单写者 `serial.log` 原件保留。启动前重核卷 UUID、双锁/PID空闲、候选 SHA、固定五项 model_env 与 argv 仅索引 **20(serial)、31(CPIO)** 改变；完整 DTB 索引33、原 FX3 kernel 索引29、CPU/RAM/GIC/MTTCG 和 loader 地址不变。无 QEMU 并行、无键、无人工 IPC。候选全包 SHA 和其他输入在退出后仍不变。源脚本快照 `observer-source.py` 和依赖 SHA 见 `source-sha256.json`。
- 32.380 秒达到 `bounded_entry_evidence` 后即停，低于180秒总预算；serial 1,972,058 字节 SHA256 `caecd00446ad09840606d63d199978683787ebf0fe276476ffac12e36f41a23c`。原 serial 字节范围分别为 `VERIFY_RC=0` [84965,84990)、`LIST_RC=0` [86523,86546)、`TRUE_RC=0` [86548,86571)、`FX3_AP_NATURAL_BOOTIN_BEGIN` [97249,97276)、首条 `/usr/bin/im.elf` 可执行映射 [224848,224936)、首条 `FX3_BOOT_QUEUE_SEND` [1930901,1931075)。运行日志另有 `FX3_AP_EARLY_MAPS_237_1_BEGIN` 与 `FX3_UIPC_RECV_BEGIN tid=227 name=bootin.elf`；自然进程/映射存在，但未证明 FX6 bootin 的哪条差异指令实际执行。首发送 `tid=241, source=0x830128, raw=00001500…`，标 `passive=1 completion_not_assumed=1`，只能归为原 FX3 AP 发送观察，不能称内核消费或 FX6 IPC 语义通过。`FX3_TRACE_ABI_NOT_READY` 未见，串口健康监视未报首错。
- QEMU PID31748 exit0/reaped/absent；20秒上限的 guest ack/API16 复原实际 1.312 秒完成，`restore_seen=1,restore_status=0`、最后 API16 等于原字 `000b00b4fd7bbba9fd030091f35301a9`，`quit_sent=true`。原输入 SHA 未变，`FX3_SYNTH_KEY` 计数0，用户操作0，双锁在退出时均 free。未动原 firmware/seed/旧候选、FX6 平台或用户 TRY2 入口。

**仍未验**：FX6 bootin 差异指令的动态调用归属、IM 新逻辑（其 PT_LOAD 本就相同）、FX6 AP/AV/CP、完整系统稳定性、菜单与任何视觉/网页或相机行为。本次仅给固定 FX3 硬件与原 FX3 AP 环境中的两入口有限运行证据，不提升默认入口或 TRY2。
